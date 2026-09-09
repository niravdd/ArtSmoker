#!/usr/bin/env python3
"""
ArtSmoker end-to-end sanity harness — drives the REAL backend HTTP endpoints
exactly as the browser does (no instrumentation, no service-layer shortcuts) and
validates that chat, image, and video generation work for the models the
registry actually exposes, in the regions the registry says they're available.

DESIGN
------
- 100% registry-driven. Nothing about specific models/providers/regions is
  hard-coded; the matrix is derived from backend/model_registry.json and the same
  live API the frontend calls. Tune the knobs below, not the code.
- Faithful to a real user: every generation goes through the public endpoints
  (POST /api/chat/stream, /api/generate/stream, /api/video/generate) with the same
  request bodies the frontend sends, including per-region selection (Chat Studio's
  region picker → `region`; Video Studio → `region_override`).
- Verifies at every stage: after each invocation it reads the NEW lines appended
  to logs/artsmoker.log, fails the step if any ERROR/CRITICAL/Traceback appears,
  and captures the excerpt so you can confirm the action was recorded.

SELECTION (matches the agreed scope; all configurable)
- chat  : per provider, the top N tiers × top N newest versions each (default 2×2),
          excluding non-text modalities (rerank / vision-only / audio / video-understanding).
- image : Stability "SD" text-to-image models only.
- video : every enabled video model.
Region scope: every region a model is available in ("all"), or its pinned region only.

USAGE
  python3 tools/sanity_test.py                         # all stages, all regions
  python3 tools/sanity_test.py --stages chat           # one stage
  python3 tools/sanity_test.py --region-scope pinned   # pinned region only
  python3 tools/sanity_test.py --tiers 2 --versions 2  # selection depth
  python3 tools/sanity_test.py --limit 5               # smoke-test the harness itself
  python3 tools/sanity_test.py --base-url http://127.0.0.1:8000

Requires the server to be running (start it the usual way). Read-only w.r.t. code;
it only creates the gallery assets any real generation would.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = ROOT / "backend" / "model_registry.json"
USER_REGISTRY_PATH = ROOT / "backend" / "model_registry.user.json"
LOG_PATH = ROOT / "logs" / "artsmoker.log"  # overridable via --log-path

# Non-text-generation modalities that live in chat_models but can't take a plain
# text prompt (rerank/embedding, vision-only, audio, video-understanding). Excluded
# from the chat test — a failure there wouldn't be a real chat-wiring bug. This is
# about MODALITY, not specific model names; extend if new modalities appear.
NON_CHAT_PATTERNS = ("rerank", "embed", "pegasus", "voxtral", "palmyra-vision")

# Log lines matching these are errors that fail the step.
LOG_ERROR_MARKERS = ("ERROR", "CRITICAL", "Traceback (most recent call last)", "Exception")
# ...but these are benign/expected and must NOT fail a step (they're not caused by us).
LOG_ERROR_IGNORE = (
    "not offered in this Region",          # regional API availability (residency fix)
    "[CLIENT]",                            # browser-reported client errors
)

GEO_PREFIXES = ("us.", "eu.", "apac.", "in.", "global.")


# ── HTTP helpers (stdlib only) ──────────────────────────────────────────────
def _req(url: str, payload=None, method="GET", accept="application/json", timeout=120):
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Accept": accept}
    if data is not None:
        headers["Content-Type"] = "application/json"
    return urllib.request.Request(url, data=data, headers=headers, method=method)


def get_json(base, path, timeout=60):
    with urllib.request.urlopen(_req(base + path, timeout=timeout), timeout=timeout) as r:
        return json.loads(r.read().decode())


def post_json(base, path, payload, timeout=120):
    with urllib.request.urlopen(_req(base + path, payload, "POST", timeout=timeout), timeout=timeout) as r:
        return json.loads(r.read().decode())


def post_sse(base, path, payload, timeout=300):
    """POST and consume an SSE stream; return the list of parsed `data:` event dicts."""
    events = []
    req = _req(base + path, payload, "POST", accept="text/event-stream", timeout=timeout)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        for raw in r:
            line = raw.decode("utf-8", "replace").strip()
            if line.startswith("data:"):
                body = line[5:].strip()
                if not body:
                    continue
                try:
                    events.append(json.loads(body))
                except json.JSONDecodeError:
                    pass
    return events


# ── Log verification ────────────────────────────────────────────────────────
def log_offset() -> int:
    try:
        return LOG_PATH.stat().st_size
    except OSError:
        return 0


def log_since(offset: int):
    """(new_text, error_lines) appended to the log since `offset`."""
    try:
        with open(LOG_PATH, "rb") as f:
            f.seek(offset)
            text = f.read().decode("utf-8", "replace")
    except OSError:
        return "", []
    errors = []
    for ln in text.splitlines():
        if any(m in ln for m in LOG_ERROR_MARKERS) and not any(ig in ln for ig in LOG_ERROR_IGNORE):
            errors.append(ln.strip())
    return text, errors


# ── Registry-driven selection ───────────────────────────────────────────────
def load_registry() -> dict:
    reg = json.loads(REGISTRY_PATH.read_text())
    # Overlay user.json per-model overrides (enabled/region) so selection matches
    # what a user actually sees (base doesn't persist enabled=True).
    if USER_REGISTRY_PATH.exists():
        try:
            user = json.loads(USER_REGISTRY_PATH.read_text())
            for section in ("chat_models", "image_models", "video_models"):
                for k, ov in (user.get(section, {}) or {}).items():
                    if isinstance(ov, dict):
                        reg.setdefault(section, {}).setdefault(k, {}).update(ov)
        except Exception:
            pass
    return reg


def _strip_geo(mid: str) -> str:
    for p in GEO_PREFIXES:
        if mid.startswith(p):
            return mid[len(p):]
    return mid


# Non-native (self-deployed) model sources — excluded by default (--include-custom).
_CUSTOM_SOURCES = {"custom_hosted", "custom", "imported"}


def _is_native(cfg: dict) -> bool:
    return (cfg.get("model_source") or "foundation") not in _CUSTOM_SOURCES


_VARIANT_TOKENS = {"instruct", "preview", "it", "pt", "thinking", "flash",
                   "chat", "base", "fp8", "bf16", "v"}


def _tier_key(model_id: str) -> str:
    """Generic 'model line' key: provider + the ALPHABETIC family stems, with all
    version / date / size / param / variant tokens dropped — so different VERSIONS
    of a tier collapse together (claude-opus-5 & -4-8 → 'anthropic:claude-opus')
    while distinct tiers stay separate (nova-pro vs nova-lite). Family names that
    carry a trailing digit keep their stem (llama4 → 'llama', qwen3 → 'qwen');
    short version markers (k2, m2, 17b, v1) are dropped. No hard-coded names."""
    s = _strip_geo(model_id).lower().split(":")[0]
    prov, _, rest = s.partition(".")
    rest = rest or s
    keep = []
    for t in re.split(r"[-.]", rest):
        if not t or t in _VARIANT_TOKENS:
            continue
        if any(c.isdigit() for c in t):
            stem = re.match(r"^([a-z]+)", t)
            stem = stem.group(1) if stem else ""
            if len(stem) >= 3:          # llama4 → llama, gemma3 → gemma
                keep.append(stem)
            # else drop pure version/size markers: k2, m2, 17b, 8x7b, a35b, v1, 2507
        else:
            keep.append(t)
    return f"{prov}:{'-'.join(keep) or prov}"


def _version_tuple(model_id: str) -> tuple:
    """Numeric version of a model_id for recency sorting, IGNORING sizes (120b, 8x7b,
    a35b) and dates (6-8 digit). So gpt-5.6 > gpt-5.4, opus-5 > opus-4-8, and a big
    param count never masquerades as a high version."""
    s = _strip_geo(model_id).lower().split(":")[0]
    prov, _, rest = s.partition(".")
    rest = rest or s
    nums = []
    for t in re.split(r"[-.]", rest):
        if re.fullmatch(r"\d+", t):
            if len(t) >= 6:             # date (20250929)
                continue
            nums.append(int(t))
        # tokens like 120b / 8x7b / a35b / 17b (letters+digits) are sizes → skipped
    return tuple(nums[:4])


def _recency(cfg: dict) -> tuple:
    """Sortable recency (higher = newer): ACTIVE first, then numeric version. Uses
    the version tuple, NOT the label — some Mantle entries label themselves with
    their lowercase model_id, which would skew any string-based ranking."""
    active = 1 if (cfg.get("lifecycle_status") or "ACTIVE").upper() == "ACTIVE" else 0
    return (active, _version_tuple(cfg.get("model_id", "")))


def select_chat_models(reg: dict, tiers: int, versions: int, include_custom: bool = False) -> list[dict]:
    from collections import defaultdict
    cand = []
    for key, c in reg.get("chat_models", {}).items():
        if c.get("enabled") is False:
            continue
        if not include_custom and not _is_native(c):
            continue
        if (c.get("lifecycle_status") or "ACTIVE").upper() != "ACTIVE":
            continue
        blob = (c.get("model_id", "") + " " + c.get("label", "")).lower()
        if any(p in blob for p in NON_CHAT_PATTERNS):
            continue
        if not c.get("model_id") or not (c.get("available_regions") or c.get("region")):
            continue
        cand.append({**c, "key": key})
    # group by provider → tier → members
    by_prov = defaultdict(lambda: defaultdict(list))
    for c in cand:
        by_prov[c.get("provider", "?")][_tier_key(c["model_id"])].append(c)
    selected = []
    for prov, tier_map in by_prov.items():
        ranked_tiers = sorted(tier_map.items(),
                              key=lambda kv: (max(_recency(m) for m in kv[1]), kv[0]), reverse=True)
        for _tier, members in ranked_tiers[:tiers]:
            for c in sorted(members, key=_recency, reverse=True)[:versions]:
                selected.append(c)
    return selected


def select_image_models(reg: dict, include_custom: bool = False) -> list[dict]:
    """Native scope = Stability 'SD' text-to-image models (the agreed image scope).
    With include_custom, ALSO the self-deployed custom image models (note: those
    invoke via the SageMaker async path — a real generation still lands in the
    gallery, but may complete after the stream returns)."""
    out = []
    for key, c in reg.get("image_models", {}).items():
        if c.get("enabled") is False:
            continue
        if c.get("model_purpose") not in (None, "text_to_image"):
            continue
        prov = (c.get("provider") or "").lower()
        mid = (c.get("model_id") or "").lower()
        is_sd = _is_native(c) and ("stability" in prov or "sd3" in mid
                                   or "stable-image" in mid or "stable-diffusion" in mid)
        is_custom = not _is_native(c)
        if is_sd or (include_custom and is_custom):
            out.append({**c, "key": key})
    return out


def select_video_models(reg: dict, include_custom: bool = False) -> list[dict]:
    out = []
    for key, c in reg.get("video_models", {}).items():
        if c.get("enabled") is False:
            continue
        if not include_custom and not _is_native(c):
            continue
        if not c.get("model_id"):
            continue
        out.append({**c, "key": key})
    return out


def regions_for(cfg: dict, scope: str) -> list[str]:
    if scope == "pinned":
        return [cfg.get("region")] if cfg.get("region") else (cfg.get("available_regions") or [])[:1]
    regs = cfg.get("available_regions") or ([cfg["region"]] if cfg.get("region") else [])
    return sorted(set(regs))


# ── Stage runners (drive the real endpoints) ─────────────────────────────────
CHAT_PROMPT = [{"role": "user", "content": "Reply with exactly one word: OK"}]
IMAGE_PROMPT = "a single red apple on a plain white background, product photo"
VIDEO_PROMPT = "a calm ocean wave rolling onto a sandy beach at sunrise"


def preflight_concurrency(base, want, probe_model, probe_region):
    """Measure the running server's real parallelism so we can advise (cross-platform)
    whether it needs restarting with more workers BEFORE hammering it. Fires one warm
    request for a baseline latency, then `n` identical requests concurrently: a server
    that parallelizes finishes in ~baseline; one that serializes takes ~n×baseline.
    Returns (baseline_s, parallel_s, factor) where factor≈n is ideal, ≈1 is serialized.
    """
    def one():
        t = time.time()
        run_chat(base, probe_model, probe_region, 16, timeout=30)
        return time.time() - t
    baseline = one()                      # warm + baseline
    n = max(2, min(want, 8))
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=n) as ex:
        list(ex.map(lambda _: one(), range(n)))
    parallel = time.time() - t0
    factor = (n * baseline) / parallel if parallel > 0 else 0.0
    return baseline, parallel, factor, n


def _restart_recommendation(base, want):
    port = base.rsplit(":", 1)[-1] if ":" in base else "8000"
    workers = max(2, min(8, (want + 2) // 3))
    return (
        f"  The server appears to serialize requests — concurrent testing will be slow.\n"
        f"  Restart it with multiple workers so it can process ~{want} requests in parallel:\n\n"
        f"    # macOS / Linux (no extra deps):\n"
        f"    uvicorn backend.main:app --workers {workers} --port {port}\n\n"
        f"    # or, if gunicorn is installed (cross-platform prod):\n"
        f"    gunicorn backend.main:app -w {workers} -k uvicorn.workers.UvicornWorker "
        f"--bind 0.0.0.0:{port} --timeout 300\n\n"
        f"    # Windows: uvicorn --workers uses multiprocessing (spawn) and works;\n"
        f"    #          gunicorn is not supported on Windows — prefer uvicorn --workers.\n"
        f"  (Writes are cross-process safe — SPEC §17 — so multi-worker is safe.)\n"
        f"  Then re-run this test. To proceed anyway at reduced speed, pass --skip-server-check."
    )


def run_chat(base, model, region, max_tokens, timeout=45):
    # 45s (not 25) so slow REASONING models (grok, kimi-thinking) that legitimately
    # take ~20-40s aren't flagged as cross-geo hangs.
    payload = {
        "model_id": model["model_id"], "region": region, "messages": CHAT_PROMPT,
        "system_prompt": "", "temperature": 0.7, "max_tokens": max_tokens,
    }
    try:
        events = post_sse(base, "/api/chat/stream", payload, timeout=timeout)
    except (TimeoutError, OSError) as e:
        # A geo-pinned id sent to a non-matching region often HANGS (Bedrock accepts
        # but never responds) rather than erroring — bound it and report clearly.
        return False, f"timeout/no-response after {timeout}s ({type(e).__name__}) — region likely can't serve this id"
    err = next((e for e in events if e.get("type") == "error"), None)
    blocked = next((e for e in events if e.get("type") == "content_blocked"), None)
    text = "".join(e.get("text", "") for e in events if e.get("type") == "delta")
    got_stop = any(e.get("type") == "stop" for e in events)
    if err:
        return False, f"error: {err.get('detail', '')[:120]}"
    if blocked:
        return False, "content_blocked"
    if text.strip() or got_stop:
        return True, (text.strip()[:60] or "(stop, no text)")
    return False, f"no output ({len(events)} events)"


def run_image(base, model, region):
    payload = {
        "prompt": IMAGE_PROMPT, "pre_composed": True, "image_model": model["key"],
        "region": region, "num_options": 1, "num_variations": 1,
        "remove_background": False, "generate_svg": False, "upscale": False,
    }
    events = post_sse(base, "/api/generate/stream", payload, timeout=300)
    err = next((e for e in events if e.get("type") == "error"), None)
    done = [e for e in events if e.get("type") == "image_done"]
    complete = next((e for e in events if e.get("type") == "complete"), None)
    if err:
        return False, f"error: {err.get('detail', '')[:120]}", None
    if done or complete:
        asset = (done[0].get("asset_id") or done[0].get("id")) if done else None
        return True, f"{len(done)} image(s)" + (f", asset={asset}" if asset else ""), asset
    return False, f"no image ({len(events)} events)", None


def _delete_json(base, path, timeout=60):
    """Execute a DELETE and return the parsed JSON (the older code built a Request
    but never opened it — so cleanup silently no-op'd). Always urlopen."""
    with urllib.request.urlopen(_req(base + path, method="DELETE", timeout=timeout), timeout=timeout) as r:
        return json.loads(r.read().decode())


def run_collection(base, model, region):
    """Collections (SPEC §18) FULL end-to-end regression on the given image model:
    decompose → estimate → recompose-batch → recompose-all → regenerate-roster
    (locked-preserve) → generate (2 Batches × 1×1) → gallery card/index →
    get/reconstruct → select-version (+ design_history) → export graceful-400 →
    delete cleanup. Real HTTP, registry-driven. Live 3D SUBMIT is intentionally NOT
    fired (SageMaker cost + async side-effects); export's no-3D path exercises the
    export wiring instead."""
    import urllib.error
    mk = model["key"]
    ask = "a tiny set of two fantasy gemstones"
    steps, cid = [], None
    try:
        # 1) decompose (art-direction + roster + per-Batch prompts + cost ledger)
        dec = post_json(base, "/api/collections/decompose",
                        {"prompt": ask, "asset_type": "game_asset", "image_model": mk, "count": 2}, timeout=180)
        roster, cid = dec.get("roster") or [], dec.get("collection_id")
        if len(roster) != 2 or not all(r.get("model_agnostic_prompt") for r in roster):
            return False, f"decompose bad roster ({len(roster)})", cid
        if not dec.get("art_direction", {}).get("text") or not (dec.get("cost", 0) > 0):
            return False, "decompose missing art-direction/cost", cid
        ad = dec["art_direction"]["text"]; steps.append("decompose")

        # 2) estimate — projected-cost math (batches × O × V × price)
        est = post_json(base, "/api/collections/estimate",
                        {"image_model": mk, "batches": 2, "options": 3, "variations": 2,
                         "design_cost": dec["cost"]}, timeout=30)
        if est.get("images") != 12:
            return False, f"estimate images={est.get('images')} (want 12)", cid
        if est.get("price_available") and abs((est.get("projected_generation_cost") or 0)
                                              - round(est["price_per_image"] * 12, 4)) > 1e-4:
            return False, "estimate projected-cost math wrong", cid
        steps.append("estimate")

        # 3) recompose ONE Batch prompt
        rb = post_json(base, "/api/collections/recompose-batch",
                       {"art_direction": ad, "name": roster[0]["name"], "concept": roster[0].get("concept", ""),
                        "image_model": mk, "asset_type": "game_asset"}, timeout=90)
        if not rb.get("model_agnostic_prompt"):
            return False, "recompose-batch empty", cid
        steps.append("recompose-batch")

        # 4) recompose ALL prompts (art-direction cascade)
        ra = post_json(base, "/api/collections/recompose-all",
                       {"art_direction": ad, "image_model": mk, "asset_type": "game_asset",
                        "roster": [{"name": r["name"], "slug": r["slug"], "concept": r.get("concept", "")} for r in roster]},
                       timeout=120)
        if len(ra.get("roster", [])) != 2 or not all(x.get("model_agnostic_prompt") for x in ra["roster"]):
            return False, "recompose-all incomplete", cid
        steps.append("recompose-all")

        # 5) regenerate roster PRESERVING a locked entry
        rr = post_json(base, "/api/collections/regenerate-roster",
                       {"prompt": ask, "art_direction": ad, "count": 2, "image_model": mk, "asset_type": "game_asset",
                        "locked": [{"name": roster[0]["name"], "slug": roster[0]["slug"],
                                    "concept": roster[0].get("concept", ""),
                                    "model_agnostic_prompt": roster[0]["model_agnostic_prompt"]}]}, timeout=120)
        if roster[0]["slug"] not in [x["slug"] for x in rr.get("roster", [])]:
            return False, "regenerate-roster dropped the locked entry", cid
        steps.append("regenerate-roster(lock)")

        # 6) generate 2 Batches × 1×1 (SSE) — assert complete + cost_update
        events = post_sse(base, "/api/collections/generate",
                          {"collection_id": cid, "name": dec.get("name", "Sanity Set"), "raw_ask": ask,
                           "art_direction": dec["art_direction"], "roster": roster, "image_model": mk,
                           "region": region, "asset_type": "game_asset", "num_options": 1, "num_variations": 1,
                           "llm_cost_ledger": dec.get("llm_cost_ledger", []), "design_cost": dec.get("cost", 0)},
                          timeout=300)
        comp = next((e for e in events if e.get("type") == "collection_complete"), None)
        if next((e for e in events if e.get("type") == "error"), None) or comp is None:
            return False, f"generate failed ({len(events)} events)", cid
        if comp.get("completed_batches") != 2:
            return False, f"only {comp.get('completed_batches')}/2 batches completed", cid
        if not any(e.get("type") == "cost_update" for e in events):
            return False, "no cost_update event", cid
        steps.append("generate2×1×1")

        # 7) Gallery fast-path: one card w/ cover, batch_count, per-Batch versions field
        card = next((c for c in get_json(base, "/api/collections", timeout=30).get("collections", [])
                     if c.get("collection_id") == cid), None)
        if not card or card.get("batch_count") != 2 or not card.get("cover"):
            return False, "gallery card missing/incomplete", cid
        if not card.get("batches") or "versions" not in card["batches"][0]:
            return False, "summary missing per-Batch versions field", cid
        steps.append("gallery-card")

        # 8) Full view: record finalized + Batches reconstructed with batch_ids
        full = get_json(base, f"/api/collections/{cid}", timeout=30)
        rec = full.get("record", {})
        if rec.get("status") not in ("complete", "partial"):
            return False, "record not finalized", cid
        b0 = (rec.get("roster") or [{}])[0].get("batch_id")
        if not b0 or not full.get("batches"):
            return False, "reconstruction missing batch_id/batches", cid
        steps.append("get/reconstruct")

        # 9) select-version pointer + design_history provenance
        sv = post_json(base, f"/api/collections/{cid}/select-version",
                       {"batch_id": b0, "version": 1}, timeout=30)
        if not sv.get("ok"):
            return False, "select-version failed", cid
        if not get_json(base, f"/api/collections/{cid}", timeout=30).get("record", {}).get("design_history"):
            return False, "design_history not appended", cid
        steps.append("select-version+history")

        # 10) export with no 3D yet → graceful 400 (exercises export wiring)
        try:
            urllib.request.urlopen(_req(f"{base}/api/collections/{cid}/export?fmt=fbx", timeout=60), timeout=60)
            return False, "export should 400 (no 3D) but returned 200", cid
        except urllib.error.HTTPError as e:
            if e.code != 400:
                return False, f"export unexpected status {e.code}", cid
        steps.append("export-graceful400")

        # 11) delete cleanup (ACTUALLY executed) + verify gone
        _delete_json(base, f"/api/collections/{cid}?delete_assets=true")
        if any(c.get("collection_id") == cid for c in get_json(base, "/api/collections", timeout=30).get("collections", [])):
            return False, "collection not deleted", cid
        cid = None
        steps.append("delete-cleanup")

        return True, " → ".join(steps), None
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:140]}", cid
    finally:
        # If we bailed mid-flow, best-effort clean up the collection we created.
        if cid:
            try:
                _delete_json(base, f"/api/collections/{cid}?delete_assets=true")
            except Exception:
                pass


def run_video(base, model, region, timeout):
    payload = {
        "model_key": model["key"], "prompt": VIDEO_PROMPT,
        "region_override": region, "enhance_prompt": False,
    }
    resp = post_json(base, "/api/video/generate", payload, timeout=120)
    job_id = resp.get("job_id") or resp.get("id") or resp.get("async_job_id") or \
        (resp.get("job") or {}).get("job_id")
    if not job_id:
        return False, f"no job_id in submit response: {json.dumps(resp)[:160]}", None
    # Poll like the frontend does
    deadline = time.time() + timeout
    last = ""
    while time.time() < deadline:
        time.sleep(10)
        try:
            st = get_json(base, f"/api/video/status/{job_id}", timeout=30)
        except Exception as e:
            last = f"status poll error: {e}"
            continue
        status = (st.get("status") or st.get("state") or "").lower()
        last = status or json.dumps(st)[:80]
        if status in ("completed", "complete", "succeeded", "done", "ready"):
            return True, f"job {job_id} {status}", job_id
        if status in ("failed", "error", "cancelled"):
            return False, f"job {job_id} {status}: {st.get('error', '')[:120]}", job_id
    return False, f"job {job_id} timeout after {timeout}s (last: {last})", job_id


# ── Orchestration ────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="ArtSmoker end-to-end sanity harness")
    ap.add_argument("--base-url", default="http://127.0.0.1:8000")
    ap.add_argument("--stages", default="chat,image,video",
                    help="comma list of: chat,image,video,collections")
    ap.add_argument("--region-scope", choices=("all", "pinned"), default="all")
    ap.add_argument("--concurrency", type=int, default=10,
                    help="parallel in-flight requests per stage (hides cross-geo hangs)")
    ap.add_argument("--log-path", default="", help="server log file to verify (default logs/artsmoker.log)")
    ap.add_argument("--tiers", type=int, default=2, help="top N tiers per provider (chat)")
    ap.add_argument("--versions", type=int, default=2, help="top N versions per tier (chat)")
    ap.add_argument("--include-custom", action="store_true",
                    help="also test self-deployed custom models (default: native/foundation only)")
    ap.add_argument("--skip-server-check", action="store_true",
                    help="skip the concurrency preflight (run even if the server serializes)")
    ap.add_argument("--max-tokens", type=int, default=512,
                    help="chat max_tokens — 512 so reasoning models (grok/kimi-thinking) emit a "
                         "final answer rather than spending the whole budget on hidden reasoning")
    ap.add_argument("--video-timeout", type=int, default=600, help="per-video poll timeout (s)")
    ap.add_argument("--limit", type=int, default=0, help="cap invocations per stage (0=all)")
    ap.add_argument("--report", default=str(ROOT / "tools" / "sanity_report.json"))
    args = ap.parse_args()

    base = args.base_url.rstrip("/")
    stages = [s.strip() for s in args.stages.split(",") if s.strip()]
    if args.log_path:
        global LOG_PATH
        LOG_PATH = Path(args.log_path)
    reg = load_registry()

    # Preflight: server reachable + version
    try:
        health = get_json(base, "/api/health", timeout=15)
        print(f"Server: {base} | version {health.get('version')} | ready={health.get('ready')}")
    except Exception as e:
        print(f"FATAL: cannot reach server at {base}: {e}")
        sys.exit(1)

    results = {"started": datetime.now(timezone.utc).isoformat(), "base": base,
               "region_scope": args.region_scope, "stages": {}}

    def run_stage(name, models, runner):
        # build (model, region) matrix
        jobs = [(m, r) for m in models for r in regions_for(m, args.region_scope)]
        if args.limit:
            jobs = jobs[:args.limit]
        conc = max(1, args.concurrency)
        print(f"\n=== STAGE {name.upper()} — {len(models)} models, {len(jobs)} invocations "
              f"({args.region_scope} regions, concurrency={conc}) ===", flush=True)
        stage_off = log_offset()   # stage-level baseline (per-call log attribution is
                                   # unreliable once requests overlap — verify per stage)
        rows = [None] * len(jobs)
        done = {"n": 0}
        lock = threading.Lock()

        def work(idx, m, region):
            label = f"{m.get('label', m['key'])} @ {region}"
            t0 = time.time()
            try:
                ok, detail, *_ = runner(m, region)
            except urllib.error.HTTPError as e:
                ok, detail = False, f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:120]}"
            except Exception as e:
                ok, detail = False, f"{type(e).__name__}: {str(e)[:120]}"
            dt = time.time() - t0
            rows[idx] = {"model": m.get("label", m["key"]), "model_id": m.get("model_id"),
                         "key": m["key"], "region": region, "invoke_ok": ok, "detail": detail,
                         "seconds": round(dt, 1), "status": "PASS" if ok else "FAIL"}
            with lock:
                done["n"] += 1
                print(f"[{done['n']}/{len(jobs)}] {'PASS' if ok else 'FAIL'} {label} — {detail} "
                      f"({dt:.1f}s)", flush=True)

        with ThreadPoolExecutor(max_workers=conc) as ex:
            futs = [ex.submit(work, i, m, r) for i, (m, r) in enumerate(jobs)]
            for _ in as_completed(futs):
                pass

        # Stage-level log verification: no ERROR/CRITICAL/Traceback appended, and the
        # log actually grew (activity was recorded).
        newlog, log_errors = log_since(stage_off)
        for row in rows:
            row["log_clean"] = not log_errors
            if not log_errors and row["status"] == "PASS":
                pass
            elif log_errors and row["status"] == "PASS":
                row["status"] = "PASS*"  # invoke ok, but stage log had errors (see below)
        passed = sum(1 for r in rows if r["status"].startswith("PASS"))
        failed = sum(1 for r in rows if r["status"] == "FAIL")
        print(f"--- {name}: {passed} PASS, {failed} FAIL | log grew {len(newlog)} bytes, "
              f"{len(log_errors)} error line(s) ---", flush=True)
        if log_errors:
            for ln in log_errors[:20]:
                print(f"    LOG-ERROR: {ln}", flush=True)
        results["stages"][name] = {"passed": passed, "failed": failed,
                                    "log_errors": log_errors, "log_bytes": len(newlog),
                                    "rows": rows}

    scope_note = "native+custom" if args.include_custom else "native only"
    print(f"Model scope: {scope_note}")

    # Cross-platform concurrency preflight: measure the server's real parallelism and,
    # if it serializes, RECOMMEND a multi-worker restart (portable) rather than forcing one.
    if not args.skip_server_check and args.concurrency > 1:
        pool = select_chat_models(reg, 1, 1, args.include_custom)
        probe = next((m for m in pool if (m.get("region") or "").startswith("us-")
                      and "converse" in (m.get("invoke_api") or "")), pool[0] if pool else None)
        if probe:
            preg = probe.get("region") or (probe.get("available_regions") or ["us-west-2"])[0]
            print(f"Concurrency preflight: probing {probe.get('label')} @ {preg} ...", flush=True)
            try:
                bl, par, factor, n = preflight_concurrency(base, args.concurrency, probe, preg)
                print(f"  baseline={bl:.2f}s | {n} concurrent={par:.2f}s | parallelism≈{factor:.1f}x "
                      f"(ideal ~{n}x)")
                if factor < n * 0.5:
                    print("\nSERVER CONCURRENCY WARNING — not enough parallelism:\n"
                          + _restart_recommendation(base, args.concurrency))
                    sys.exit(2)
                print(f"  OK — server parallelizes; proceeding at concurrency={args.concurrency}.")
            except Exception as e:
                print(f"  preflight probe failed ({e}); proceeding (use --skip-server-check to silence)")
    if "chat" in stages:
        run_stage("chat", select_chat_models(reg, args.tiers, args.versions, args.include_custom),
                  lambda m, r: run_chat(base, m, r, args.max_tokens))
    if "image" in stages:
        run_stage("image", select_image_models(reg, args.include_custom),
                  lambda m, r: run_image(base, m, r))
    if "video" in stages:
        run_stage("video", select_video_models(reg, args.include_custom),
                  lambda m, r: run_video(base, m, r, args.video_timeout))
    if "collections" in stages:
        # One image model is enough to smoke the whole Collections flow (SPEC §18);
        # capped to the first enabled image model to bound cost.
        run_stage("collections", select_image_models(reg, args.include_custom)[:1],
                  lambda m, r: run_collection(base, m, r))

    results["finished"] = datetime.now(timezone.utc).isoformat()
    Path(args.report).write_text(json.dumps(results, indent=2))
    # Summary
    print("\n===== SUMMARY =====")
    total_p = total_f = 0
    for name, st in results["stages"].items():
        total_p += st["passed"]
        total_f += st["failed"]
        le = st.get("log_errors", [])
        print(f"  {name:6s}: {st['passed']} PASS / {st['failed']} FAIL"
              + (f" | {len(le)} LOG-ERROR line(s)!" if le else " | log clean"))
        for row in st["rows"]:
            if row["status"] == "FAIL":
                print(f"     FAIL {row['model']} @ {row['region']}: {row['detail']}")
        for ln in le[:20]:
            print(f"     LOG-ERROR: {ln}")
    print(f"  TOTAL : {total_p} PASS / {total_f} FAIL")
    print(f"  report → {args.report}")
    sys.exit(1 if total_f else 0)


if __name__ == "__main__":
    main()
