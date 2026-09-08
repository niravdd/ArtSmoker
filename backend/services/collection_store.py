"""Collection store — persistence for the Collections (Set Generation) feature.

See SPEC §18. A Collection is the umbrella tier above the existing Batch/Job
model:

    Collection  →  Batch (one roster subject)  →  Job (one image)

ID strategy (SPEC §18.6, decided by audit): each roster subject generates its own
ordinary ``batch_id`` and the Collection simply GROUPS N of them. There is NO
asset-id-format change — a collection's Jobs keep the normal
``{batch_id}_o{n}_v{m}`` id, and membership rides in each Job's metadata
(``collection_id`` etc.), exactly the way ``batch_id`` already does.

Each Collection lives in its OWN top-level directory,
``data/collections/{collection_id}/``, holding two files (no images — a Job's
pixels stay in ``data/generated/{asset_id}/``):

* ``metadata.json`` — the MASTER RECORD: authored design + user choices (name,
  raw ask, overarching art-direction + edit trail, the roster of Batches with
  their model-agnostic prompts and per-Batch ``selected_version``, knobs, the LLM
  cost ledger, cost estimate/actual, status). SOURCE OF TRUTH.
* ``summary.json`` — the DERIVED index the Gallery lists cheaply WITHOUT parsing
  any Job or the heavy master record: per-Batch cover thumb, status, job count,
  has-3D, plus a collection cover. A pure projection — rebuildable at any time.

Consistency is EAGER live-update (SPEC §18.7): the same discipline the per-asset
``metadata.json`` already uses — RMW under a lock on every change, no
rev/dirty machinery. Member-Job changes (select a version, produce a 3D model,
edit/delete a Batch) are serial and user-paced, so
``refresh_collection_summary`` patches the affected Batch immediately. The one
concurrent burst — initial generation — is handled by refreshing once per Batch
completion plus one wholesale ``rebuild_collection_summary`` at the end.
``rebuild_collection_summary`` also self-heals a missing/corrupt index on read.

All writes are ``atomic_write_text`` under ``collection_write_lock`` (§17).
Write-ordering rule: a member-Job's own metadata write commits FIRST under its
``asset_write_lock`` and RELEASES before a refresh takes ``collection_write_lock``
— the two locks are never nested.
"""

from __future__ import annotations

import json
import logging
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from backend.config import settings
from backend.services.safe_write import atomic_write_text, named_write_lock
from backend.storage.local_store import store

logger = logging.getLogger(__name__)

_MASTER = "metadata.json"
_SUMMARY = "summary.json"


# ── IDs, paths, lock ─────────────────────────────────────────────────────────

def new_collection_id() -> str:
    """Mint a fresh collection id (own namespace, distinct from batch ids)."""
    return str(uuid.uuid4())


def collection_dir(collection_id: str) -> Path:
    d = settings.collections_dir / collection_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def collection_write_lock(collection_id: str):
    """Process/thread-safe lock for a Collection's files (master + index).

    Reuses ``named_write_lock`` (SPEC §17) — no new primitive. Usable as a
    context manager or via acquire()/release(); reentrant for the same thread."""
    return named_write_lock(f"collection:{collection_id}")


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Master record schema ─────────────────────────────────────────────────────

def new_collection_record(
    *,
    collection_id: str,
    name: str,
    raw_ask: str,
    overarching_art_direction: str = "",
    roster: list[dict] | None = None,
    knobs: dict | None = None,
    status: str = "designing",
) -> dict:
    """Build a fresh master-record dict (SPEC §18.7(a)).

    A roster entry = one Batch:
      {batch_id, name, slug, concept, model_agnostic_prompt,
       locked, per_model_prompts{}, selected_version, three_d?}
    ``batch_id`` is empty until that Batch generates.
    """
    now = _utcnow()
    return {
        "collection_id": collection_id,
        "name": name,
        "raw_ask": raw_ask,
        "created_at": now,
        "updated_at": now,
        "overarching_art_direction": overarching_art_direction,
        "art_direction_trail": [],       # append-only edit trail (Phase M)
        "roster": roster or [],
        "knobs": knobs or {},
        "llm_cost_ledger": [],           # per-step design-cost entries (§18.9)
        "cost_estimate": None,
        "cost_actual": None,
        "status": status,
        "design_history": [],            # light provenance trail (Phase M)
    }


def new_roster_entry(
    *,
    name: str,
    slug: str,
    concept: str = "",
    model_agnostic_prompt: str = "",
    locked: bool = False,
) -> dict:
    """Build a fresh roster entry (one Batch) for the master record."""
    return {
        "batch_id": "",                  # assigned when this Batch generates
        "name": name,
        "slug": slug,
        "concept": concept,
        "model_agnostic_prompt": model_agnostic_prompt,
        "locked": locked,
        "per_model_prompts": {},
        "selected_version": None,        # None → use each Job's current_version
        "three_d": None,                 # populated by the Phase-N 3D handoff
    }


# ── Master record CRUD ───────────────────────────────────────────────────────

def _master_path(collection_id: str) -> Path:
    return collection_dir(collection_id) / _MASTER


def _summary_path(collection_id: str) -> Path:
    return collection_dir(collection_id) / _SUMMARY


def load_collection(collection_id: str) -> dict | None:
    """Load the master record, or None if the Collection doesn't exist."""
    path = _master_path(collection_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Collection master record unreadable (%s): %r", collection_id, exc)
        return None


def save_collection(collection_id: str, record: dict) -> Path:
    """Atomically persist the master record (under the collection lock)."""
    record["updated_at"] = _utcnow()
    with collection_write_lock(collection_id):
        path = _master_path(collection_id)
        atomic_write_text(path, json.dumps(record, indent=2, default=str))
    return path


def update_collection(collection_id: str, mutator: Callable[[dict], None]) -> dict | None:
    """Read-modify-write the master record under the lock (SPEC §17).

    Fresh-read → ``mutator(record)`` mutates in place → atomic-write. Returns the
    updated record, or None if the Collection is missing. The lock is reentrant,
    so ``mutator`` may itself call other locked collection writers.
    """
    with collection_write_lock(collection_id):
        record = load_collection(collection_id)
        if record is None:
            return None
        mutator(record)
        record["updated_at"] = _utcnow()
        atomic_write_text(_master_path(collection_id), json.dumps(record, indent=2, default=str))
        return record


def list_collection_ids() -> list[str]:
    """All collection ids that have a master record."""
    base = settings.collections_dir
    if not base.exists():
        return []
    return sorted(
        d.name for d in base.iterdir()
        if d.is_dir() and (d / _MASTER).exists()
    )


def delete_collection(collection_id: str) -> bool:
    """Delete the whole Collection directory (master + index). Member Job assets
    are deleted separately by the caller (Gallery DELETE) — this only removes the
    collection-level files."""
    with collection_write_lock(collection_id):
        d = settings.collections_dir / collection_id
        if d.exists() and d.is_dir():
            shutil.rmtree(d)
            return True
    return False


# ── Derived index (summary.json) ─────────────────────────────────────────────

def _member_jobs(batch_id: str) -> list[dict]:
    """All Job metadatas belonging to a Batch — mirrors gallery.get_batch's scan
    (prefix filter + authoritative ``batch_id`` equality). Empty if none yet."""
    if not batch_id:
        return []
    jobs: list[dict] = []
    for aid in store.list_generated_ids():
        if not aid.startswith(batch_id + "_"):
            continue
        meta = store.load_generation_metadata(aid)
        if meta and meta.get("batch_id") == batch_id:
            jobs.append(meta)
    jobs.sort(key=lambda m: (m.get("option_index", 0), m.get("variant_index", 0)))
    return jobs


def _project_batch(entry: dict) -> dict:
    """Project one roster Batch into its lean summary form (derived state only)."""
    batch_id = entry.get("batch_id", "")
    jobs = _member_jobs(batch_id)

    # Status: any pending → generating; any complete → complete/partial; else the
    # authored status. Derived purely from the Jobs' async_status.
    statuses = [j.get("async_status") for j in jobs]
    if not jobs:
        status = "pending"
    elif any(s == "pending" for s in statuses):
        status = "generating"
    elif any(s == "failed" for s in statuses):
        status = "partial" if any(s in (None, "complete") for s in statuses) else "failed"
    else:
        status = "complete"

    # Thumb: the first Job (lowest option/variation) — the Batch's representative
    # image. selected_version is authored on the entry (None → the Job's current).
    thumb_asset_id = jobs[0]["id"] if jobs else None
    selected_version = entry.get("selected_version")
    if selected_version is None and jobs:
        selected_version = jobs[0].get("current_version", 1)
    thumb_path = f"/api/gallery/{thumb_asset_id}/png" if thumb_asset_id else None

    three_d = entry.get("three_d") or {}
    has_3d = bool(three_d.get("status") == "complete")

    return {
        "batch_id": batch_id,
        "name": entry.get("name", ""),
        "slug": entry.get("slug", ""),
        "selected_version": selected_version,
        "thumb_asset_id": thumb_asset_id,
        "thumb_path": thumb_path,
        "status": status,
        "job_count": len(jobs),
        "has_3d": has_3d,
    }


def _project_summary(record: dict) -> dict:
    """Full projection of the master record → the lean Gallery index."""
    batches = [_project_batch(e) for e in record.get("roster", [])]
    # Cover: first Batch that has a thumb.
    cover = None
    for p in batches:
        if p.get("thumb_asset_id"):
            cover = {
                "asset_id": p["thumb_asset_id"],
                "version": p.get("selected_version"),
                "thumb_path": p["thumb_path"],
            }
            break
    knobs = record.get("knobs", {})
    return {
        "collection_id": record.get("collection_id"),
        "name": record.get("name", ""),
        "status": record.get("status", ""),
        "updated_at": record.get("updated_at"),
        "batch_count": len(batches),
        "models": knobs.get("models", []),
        "cost_estimate": record.get("cost_estimate"),
        "cost_actual": record.get("cost_actual"),
        "cover": cover,
        "batches": batches,
    }


def rebuild_collection_summary(collection_id: str) -> dict | None:
    """Wholesale reproject ``summary.json`` from the master record + member Job
    metas. Used at collection-completion and as the self-heal on a
    missing/corrupt index. Returns the summary, or None if the master is gone."""
    with collection_write_lock(collection_id):
        record = load_collection(collection_id)
        if record is None:
            return None
        summary = _project_summary(record)
        atomic_write_text(_summary_path(collection_id), json.dumps(summary, indent=2, default=str))
        return summary


def refresh_collection_summary(collection_id: str, changed_batch_id: str | None = None) -> dict | None:
    """Eager live-update of the index after a member change (SPEC §18.7).

    ``changed_batch_id`` re-projects just that one Batch (targeted patch) on top
    of the existing index; None re-projects everything. Falls back to a full
    rebuild if the index is missing/corrupt. Under the collection lock.
    """
    with collection_write_lock(collection_id):
        record = load_collection(collection_id)
        if record is None:
            return None

        if changed_batch_id is None:
            summary = _project_summary(record)
            atomic_write_text(_summary_path(collection_id), json.dumps(summary, indent=2, default=str))
            return summary

        # Targeted patch: load the existing index (rebuild if absent), then
        # replace only the changed Batch + recompute the cover.
        path = _summary_path(collection_id)
        summary: dict | None = None
        if path.exists():
            try:
                summary = json.loads(path.read_text())
            except (json.JSONDecodeError, OSError):
                summary = None
        if summary is None:
            summary = _project_summary(record)  # missing/corrupt → full rebuild
            atomic_write_text(path, json.dumps(summary, indent=2, default=str))
            return summary

        entry = next((e for e in record.get("roster", []) if e.get("batch_id") == changed_batch_id), None)
        batches = summary.get("batches", [])
        if entry is not None:
            projected = _project_batch(entry)
            for i, p in enumerate(batches):
                if p.get("batch_id") == changed_batch_id:
                    batches[i] = projected
                    break
            else:
                batches.append(projected)
        else:
            # Batch no longer in the roster (deleted/emptied) — drop it.
            batches = [p for p in batches if p.get("batch_id") != changed_batch_id]

        summary["batches"] = batches
        summary["batch_count"] = len(batches)
        summary["status"] = record.get("status", summary.get("status", ""))
        summary["updated_at"] = record.get("updated_at")
        summary["cost_actual"] = record.get("cost_actual")
        summary["cover"] = next(
            ({"asset_id": p["thumb_asset_id"], "version": p.get("selected_version"),
              "thumb_path": p["thumb_path"]}
             for p in batches if p.get("thumb_asset_id")),
            None,
        )
        atomic_write_text(path, json.dumps(summary, indent=2, default=str))
        return summary


def read_summary(collection_id: str) -> dict | None:
    """Gallery fast-path: serve ``summary.json`` directly; if missing/unparseable,
    rebuild once (self-heal) then serve. None if the Collection doesn't exist."""
    path = _summary_path(collection_id)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            pass  # corrupt → fall through to rebuild
    return rebuild_collection_summary(collection_id)
