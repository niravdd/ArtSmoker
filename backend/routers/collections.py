"""Collections (Set Generation) API — SPEC §18.

Design-time endpoints (decompose / recompose / regenerate) turn ONE brief into a
shared art direction + a roster of distinct, in-theme Batches, each with its own
model-agnostic prompt. The design is held IN-MEMORY by the client (like the
single-asset Prompt Designer) — no pre-generation persistence; the Collection
record is written at generation start (see routers/generate.py). Read endpoints
(list / get / delete) serve the Gallery + Collection Asset Viewer from the store.

Every design LLM round-trip is costed: reset_costs() at entry, a per-step ledger
built from get_total_cost() deltas, and track_aux_llm_cost() in finally (§18.9).
"""

import logging
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.models.generation_request import AssetType
from backend.storage.local_store import store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/collections", tags=["collections"])

# Bounded fan-out for per-Batch prompt generation — parallel for speed, capped to
# respect Bedrock/Mantle throttle (the sanity-harness lesson).
_BATCH_PROMPT_WORKERS = 4


def _asset_enum(value: str | None) -> AssetType:
    try:
        return AssetType(value)
    except (ValueError, TypeError):
        return AssetType.GAME_ASSET


def _load_style_profile(style_id: str | None):
    if not style_id:
        return None
    data = store.load_style_profile(style_id)
    if not data:
        return None
    from backend.models.style_profile import StyleProfile
    return StyleProfile(**data)


def _derive_name(ask: str, art_direction: dict) -> str:
    """A short human title for the collection card (free — no extra LLM call)."""
    ask = (ask or "").strip()
    if ask:
        words = ask.split()
        name = " ".join(words[:8])
        return (name[:60] + "…") if len(name) > 60 else name.title()
    return (art_direction.get("world") or "Collection")[:60]


# ── Request models ───────────────────────────────────────────────────────────

class DecomposeCollectionRequest(BaseModel):
    prompt: str
    image_model: str | None = None
    asset_type: str = "game_asset"
    style_id: str | None = None
    count: int | None = None            # None → infer natural count


class RecomposeBatchRequest(BaseModel):
    art_direction: str                  # flat art-direction text
    name: str
    concept: str = ""
    image_model: str | None = None
    asset_type: str = "game_asset"


class RegenerateRosterRequest(BaseModel):
    prompt: str
    art_direction: str
    count: int | None = None
    locked: list[dict] = []             # entries to preserve verbatim
    image_model: str | None = None
    asset_type: str = "game_asset"
    style_id: str | None = None


class RecomposeAllRequest(BaseModel):
    art_direction: str                  # EDITED flat art-direction text
    roster: list[dict]                  # [{name, slug, concept}, …]
    image_model: str | None = None
    asset_type: str = "game_asset"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _gen_batch_prompts(roster: list[dict], art_direction_text: str, asset_type: AssetType,
                      image_model: str | None) -> None:
    """Fill each roster entry's `model_agnostic_prompt` in place, in parallel,
    sharing the request's cost accumulator with the worker threads."""
    from backend.services.prompt_engineer import generate_batch_prompt
    from backend.services.cost_tracker import share_accumulator_with_thread, install_shared_accumulator

    acc = share_accumulator_with_thread()

    def _one(entry: dict):
        install_shared_accumulator(acc)  # accrue this thread's LLM cost to the request
        entry["model_agnostic_prompt"] = generate_batch_prompt(
            art_direction_text, entry.get("name", ""), entry.get("concept", ""),
            asset_type, image_model,
        )

    if not roster:
        return
    with ThreadPoolExecutor(max_workers=min(_BATCH_PROMPT_WORKERS, len(roster))) as ex:
        list(ex.map(_one, roster))


# ── Design endpoints ─────────────────────────────────────────────────────────

@router.post("/decompose")
async def decompose_collection(body: DecomposeCollectionRequest):
    """Toggle → one brief becomes {art direction, roster of Batches, per-Batch
    model-agnostic prompts} + a running LLM cost ledger (SPEC §18.4/§18.9)."""
    from backend.services.prompt_engineer import generate_art_direction, generate_roster
    from backend.services.cost_tracker import reset_costs, get_total_cost
    from backend.services.telemetry import track_aux_llm_cost
    from backend.services import collection_store as cstore

    reset_costs()
    ledger: list[dict] = []
    try:
        style_profile = _load_style_profile(body.style_id)
        asset_type = _asset_enum(body.asset_type)

        art = generate_art_direction(body.prompt, style_profile)
        c1 = get_total_cost()
        ledger.append({"step": "art_direction", "cost": round(c1, 6)})

        roster = generate_roster(body.prompt, art.get("text", ""), body.count, style_profile)
        if not roster:
            raise HTTPException(502, detail="Could not generate a roster for this brief.")
        c2 = get_total_cost()
        ledger.append({"step": "roster", "cost": round(c2 - c1, 6)})

        _gen_batch_prompts(roster, art.get("text", ""), asset_type, body.image_model)
        c3 = get_total_cost()
        ledger.append({"step": "batch_prompts", "cost": round(c3 - c2, 6)})

        collection_id = cstore.new_collection_id()
        return {
            "collection_id": collection_id,
            "name": _derive_name(body.prompt, art),
            "art_direction": art,          # structured dict + flat "text"
            "roster": roster,             # [{name, slug, concept, model_agnostic_prompt}]
            "llm_cost_ledger": ledger,
            "cost": round(get_total_cost(), 6),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Collection decompose failed")
        raise HTTPException(502, detail=f"Collection design failed: {exc}")
    finally:
        track_aux_llm_cost("collection_decompose", get_total_cost())


@router.post("/recompose-batch")
async def recompose_batch(body: RecomposeBatchRequest):
    """Regenerate ONE Batch's model-agnostic prompt (keep the rest)."""
    from backend.services.prompt_engineer import generate_batch_prompt
    from backend.services.cost_tracker import reset_costs, get_total_cost
    from backend.services.telemetry import track_aux_llm_cost

    reset_costs()
    try:
        text = generate_batch_prompt(
            body.art_direction, body.name, body.concept,
            _asset_enum(body.asset_type), body.image_model,
        )
        return {"model_agnostic_prompt": text, "cost": round(get_total_cost(), 6)}
    except Exception as exc:
        logger.exception("Collection recompose-batch failed")
        raise HTTPException(502, detail=f"Batch prompt failed: {exc}")
    finally:
        track_aux_llm_cost("collection_recompose_batch", get_total_cost())


@router.post("/regenerate-roster")
async def regenerate_roster(body: RegenerateRosterRequest):
    """Re-fan the roster, PRESERVING locked entries; fill new Batches' prompts."""
    from backend.services.prompt_engineer import generate_roster, _resolve_slug_collisions
    from backend.services.cost_tracker import reset_costs, get_total_cost
    from backend.services.telemetry import track_aux_llm_cost

    reset_costs()
    try:
        asset_type = _asset_enum(body.asset_type)
        style_profile = _load_style_profile(body.style_id)
        locked = [dict(e) for e in body.locked]
        locked_names = {str(e.get("name", "")).lower() for e in locked}

        # How many NEW Batches to fan (keep the target count stable if given).
        want = (body.count - len(locked)) if body.count else None
        fresh = generate_roster(body.prompt, body.art_direction, want, style_profile)
        fresh = [e for e in fresh if str(e.get("name", "")).lower() not in locked_names]

        c1 = get_total_cost()
        _gen_batch_prompts(fresh, body.art_direction, asset_type, body.image_model)

        roster = locked + fresh
        _resolve_slug_collisions(roster)
        return {"roster": roster, "cost": round(get_total_cost(), 6),
                "llm_cost_ledger": [
                    {"step": "roster", "cost": round(c1, 6)},
                    {"step": "batch_prompts", "cost": round(get_total_cost() - c1, 6)},
                ]}
    except Exception as exc:
        logger.exception("Collection regenerate-roster failed")
        raise HTTPException(502, detail=f"Roster regeneration failed: {exc}")
    finally:
        track_aux_llm_cost("collection_regenerate_roster", get_total_cost())


@router.post("/recompose-all")
async def recompose_all(body: RecomposeAllRequest):
    """Art direction edited → recompose EVERY Batch's model-agnostic prompt so the
    whole set re-aligns to the new direction (SPEC §18.3)."""
    from backend.services.cost_tracker import reset_costs, get_total_cost
    from backend.services.telemetry import track_aux_llm_cost

    reset_costs()
    try:
        roster = [dict(e) for e in body.roster]
        _gen_batch_prompts(roster, body.art_direction, _asset_enum(body.asset_type), body.image_model)
        return {"roster": roster, "cost": round(get_total_cost(), 6)}
    except Exception as exc:
        logger.exception("Collection recompose-all failed")
        raise HTTPException(502, detail=f"Recompose failed: {exc}")
    finally:
        track_aux_llm_cost("collection_recompose_all", get_total_cost())


# ── Read / delete endpoints (Gallery + Collection Asset Viewer) ──────────────

@router.get("")
async def list_collections():
    """Lean list for the Gallery — one summary per collection (no Job parsing)."""
    from backend.services import collection_store as cstore
    out = []
    for cid in cstore.list_collection_ids():
        s = cstore.read_summary(cid)
        if s:
            out.append(s)
    out.sort(key=lambda s: s.get("updated_at") or "", reverse=True)
    return {"collections": out}


@router.get("/{collection_id}")
async def get_collection(collection_id: str):
    """Full Collection Asset Viewer view: master record + per-Batch reconstruction."""
    from backend.services import collection_store as cstore
    from backend.routers.gallery import get_batch

    record = cstore.load_collection(collection_id)
    if record is None:
        raise HTTPException(404, detail=f"Collection '{collection_id}' not found.")

    batches = []
    for entry in record.get("roster", []):
        bid = entry.get("batch_id")
        batch = None
        if bid:
            try:
                batch = await get_batch(bid)
            except HTTPException:
                batch = None
        batches.append({"roster_entry": entry, "batch": batch})

    return {"record": record, "summary": cstore.read_summary(collection_id), "batches": batches}


@router.delete("/{collection_id}")
async def delete_collection(collection_id: str, delete_assets: bool = True):
    """Delete the collection record + index, and (default) its member Job assets."""
    from backend.services import collection_store as cstore

    record = cstore.load_collection(collection_id)
    if record is None:
        raise HTTPException(404, detail=f"Collection '{collection_id}' not found.")

    removed_assets = 0
    if delete_assets:
        member_batch_ids = {e.get("batch_id") for e in record.get("roster", []) if e.get("batch_id")}
        for aid in store.list_generated_ids():
            meta = store.load_generation_metadata(aid)
            if meta and (meta.get("collection_id") == collection_id
                         or meta.get("batch_id") in member_batch_ids):
                if store.delete_generated_asset(aid):
                    removed_assets += 1

    cstore.delete_collection(collection_id)
    return {"deleted": True, "collection_id": collection_id, "removed_assets": removed_assets}
