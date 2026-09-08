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

import json
import logging
import queue
import random
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.models.generation_request import AssetType, GenerationRequest
from backend.storage.local_store import store

logger = logging.getLogger(__name__)

_SEED_MAX = 2 ** 31 - 1

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


# ── Generation (SPEC §18.4/§18.7 — orchestrate per-Batch, reuse generate.py) ──

class GenerateCollectionRequest(BaseModel):
    collection_id: str                  # minted at decompose; the client holds it
    name: str
    raw_ask: str = ""
    art_direction: dict = {}            # structured + flat "text"
    roster: list[dict]                 # [{name, slug, concept, model_agnostic_prompt}]
    image_model: str = "sd35_large"
    asset_type: str = "game_asset"
    style_id: str | None = None
    num_options: int = 3
    num_variations: int = 2
    seed: int | None = None            # collection base seed (None → random per Batch)
    cohesion_mode: str = "prompt"


def _stamp_collection_lineage(batch_id: str, collection_id: str, entry: dict) -> None:
    """After a Batch generates, stamp collection lineage onto each of its Jobs'
    metadata (SPEC §18.7(c)). Post-hoc so the single-asset generation path stays
    byte-identical. RMW under asset_write_lock (its own metadata write already
    committed + released by _run_generation, so no nested collection lock)."""
    from backend.services.asset_locks import asset_write_lock
    for aid in store.list_generated_ids():
        if not aid.startswith(batch_id + "_"):
            continue
        with asset_write_lock(aid):
            meta = store.load_generation_metadata(aid)
            if not meta or meta.get("batch_id") != batch_id:
                continue
            meta["collection_id"] = collection_id
            meta["batch_name"] = entry.get("name", "")
            meta["batch_slug"] = entry.get("slug", "")
            meta["model_agnostic_prompt"] = entry.get("model_agnostic_prompt", "")
            store.save_generation_metadata(aid, meta)


@router.post("/generate")
async def generate_collection(body: GenerateCollectionRequest):
    """Generate a whole Collection: one Batch per roster subject (each reusing the
    existing generation pipeline verbatim from its model-agnostic prompt), writing
    the master record at start and refreshing the Gallery index as each finishes.

    Streams SSE: collection_started, batch_started, (per-Batch progress relabeled),
    batch_complete, batch_error, collection_complete.
    """
    from backend.routers.generate import _run_generation
    from backend.services.cost_tracker import get_total_cost
    from backend.services import collection_store as cstore
    from backend.services.telemetry import track_aux_llm_cost

    roster = [e for e in body.roster if e.get("model_agnostic_prompt")]
    if not roster:
        raise HTTPException(400, detail="Collection has no Batches with prompts to generate.")

    cid = body.collection_id
    asset_type = _asset_enum(body.asset_type)
    n_opts = max(1, min(5, body.num_options))
    n_vars = max(1, min(5, body.num_variations))
    base_seed = body.seed if body.seed is not None else random.randint(0, _SEED_MAX - len(roster) * n_opts * n_vars)

    # Write the master record at generation start (SPEC §18.2 — no pre-gen persistence).
    record = cstore.new_collection_record(
        collection_id=cid, name=body.name, raw_ask=body.raw_ask,
        overarching_art_direction=(body.art_direction or {}).get("text", ""),
        roster=[cstore.new_roster_entry(
            name=e.get("name", ""), slug=e.get("slug", ""), concept=e.get("concept", ""),
            model_agnostic_prompt=e.get("model_agnostic_prompt", ""),
        ) for e in roster],
        knobs={"N": len(roster), "O": n_opts, "V": n_vars, "models": [body.image_model],
               "cohesion_mode": body.cohesion_mode, "seed": base_seed},
        status="generating",
    )
    record["art_direction_structured"] = body.art_direction or {}
    cstore.save_collection(cid, record)

    event_queue: queue.Queue = queue.Queue()

    def sse(data: dict) -> str:
        return f"data: {json.dumps(data, default=str)}\n\n"

    def run_all():
        total_batches = len(roster)
        gen_cost = 0.0
        completed_batches = 0
        for idx, entry in enumerate(roster):
            name = entry.get("name", f"Batch {idx + 1}")
            event_queue.put({"type": "batch_started", "batch_index": idx,
                             "batch_name": name, "total_batches": total_batches})

            def cb(ev, _idx=idx, _name=name):
                ev["collection_batch_index"] = _idx
                ev["collection_batch_name"] = _name
                if ev.get("type") == "complete":
                    ev["type"] = "batch_complete"
                event_queue.put(ev)

            prompt = entry["model_agnostic_prompt"]
            sub = GenerationRequest(
                prompt=prompt,
                asset_type=asset_type,
                image_model=body.image_model,
                style_id=body.style_id,
                num_options=n_opts,
                num_variations=n_vars,
                seed=base_seed + idx * n_opts * n_vars,
                # Reuse the verbatim "saved concepts" path — the model-agnostic
                # prompt IS every option's concept (no re-fan; §18.4 faithful reuse).
                saved_concept_prompts={body.image_model: [prompt] * n_opts},
            )
            try:
                result = _run_generation(sub, cb)
                bid = result.id
                entry["batch_id"] = bid
                gen_cost += get_total_cost()          # _run_generation reset+tracked this Batch
                _stamp_collection_lineage(bid, cid, entry)
                # Record the Batch id on the master record + refresh the index.
                def _set_bid(rec, _i=idx, _b=bid):
                    if _i < len(rec.get("roster", [])):
                        rec["roster"][_i]["batch_id"] = _b
                cstore.update_collection(cid, _set_bid)
                cstore.refresh_collection_summary(cid, bid)
                completed_batches += 1
            except Exception as exc:
                logger.exception("Collection %s batch %d (%s) failed", cid, idx, name)
                event_queue.put({"type": "batch_error", "batch_index": idx,
                                 "batch_name": name, "error": str(exc)})

        # Finalize the master record + index.
        def _finalize(rec):
            rec["status"] = "complete" if completed_batches == total_batches else "partial"
            rec["cost_actual"] = round(gen_cost, 6)
        cstore.update_collection(cid, _finalize)
        cstore.rebuild_collection_summary(cid)
        try:
            track_aux_llm_cost("collection_generation", round(gen_cost, 6))
        except Exception:
            pass
        event_queue.put({"type": "collection_complete", "collection_id": cid,
                         "completed_batches": completed_batches, "total_batches": total_batches,
                         "cost_actual": round(gen_cost, 6)})

    def stream():
        event_queue.put({"type": "collection_started", "collection_id": cid,
                         "name": body.name, "total_batches": len(roster),
                         "num_options": n_opts, "num_variations": n_vars})
        with ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(run_all)
            while not future.done():
                try:
                    yield sse(event_queue.get(timeout=0.5))
                except queue.Empty:
                    yield ": keepalive\n\n"
            while not event_queue.empty():
                yield sse(event_queue.get_nowait())
            exc = future.exception()
            if exc:
                yield sse({"type": "error", "detail": str(exc)})

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ── 3D set handoff (SPEC §18, Phase N — reuse the existing image-to-3D path) ──

def _resolve_batch_source(collection_id: str, batch_id: str):
    """Resolve a Batch to its representative Job + selected/latest version for 3D
    (SPEC §18 Phase N). Returns (asset_id, version) or (None, None). The Phase-M
    `selected_version` pointer wins; else the Job's current_version — so a 3D run
    always picks up the newest chosen image, never a stale v1."""
    from backend.services import collection_store as cstore
    rec = cstore.load_collection(collection_id) or {}
    entry = next((e for e in rec.get("roster", []) if e.get("batch_id") == batch_id), None)
    jobs = cstore._member_jobs(batch_id)
    if not jobs:
        return None, None
    rep = jobs[0]  # o0_v0 — the Batch's representative image
    version = (entry or {}).get("selected_version") or rep.get("current_version", 1)
    return rep["id"], version


@router.post("/{collection_id}/generate-3d")
async def generate_collection_3d(collection_id: str, model_key: str | None = None):
    """3D the whole set: submit an image-to-3D job for each Batch's selected image,
    reusing the existing /api/generate/3d pipeline. Best-effort per Batch."""
    from backend.services import collection_store as cstore
    from backend.routers.generate_3d import generate_3d, ThreeDGenerateRequest

    rec = cstore.load_collection(collection_id)
    if rec is None:
        raise HTTPException(404, detail=f"Collection '{collection_id}' not found.")

    submitted, failures = [], []
    for entry in rec.get("roster", []):
        bid = entry.get("batch_id")
        if not bid:
            continue
        asset_id, version = _resolve_batch_source(collection_id, bid)
        if not asset_id:
            failures.append({"batch": entry.get("name"), "error": "no image"})
            continue
        try:
            res = await generate_3d(ThreeDGenerateRequest(asset_id=asset_id, version=version, model_key=model_key))
            job_id = res.get("job_id") if isinstance(res, dict) else None
            def _set(rc, _b=bid, _a=asset_id, _v=version, _j=job_id):
                e = next((x for x in rc.get("roster", []) if x.get("batch_id") == _b), None)
                if e is not None:
                    e["three_d"] = {"source_version": _v, "source_asset_id": _a, "job_id": _j, "status": "submitted"}
            cstore.update_collection(collection_id, _set)
            submitted.append({"batch": entry.get("name"), "asset_id": asset_id, "version": version, "job_id": job_id})
        except HTTPException as he:
            failures.append({"batch": entry.get("name"), "error": he.detail})
        except Exception as exc:
            logger.exception("Collection 3D submit failed for batch %s", bid)
            failures.append({"batch": entry.get("name"), "error": str(exc)})

    cstore.refresh_collection_summary(collection_id)
    try:
        from backend.services.telemetry import _track
        _track("collection_3d_handoff", batches=len(submitted))
    except Exception:
        pass
    if not submitted and failures:
        raise HTTPException(400, detail=failures[0].get("error", "3D submission failed."))
    return {"submitted": submitted, "failures": failures}


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
