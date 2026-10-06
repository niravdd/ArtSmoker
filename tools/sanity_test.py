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
- chat  : per provider, the top N tiers × top N newest versions each (default 2×2;
          0 = all), excluding models no Region answers (hidden by the server) and
          non-text modalities (rerank / vision-only / audio / video-understanding).
- image : Stability "SD" text-to-image models only.
- video : every enabled video model.
Region scope: every Region a route can be served from ("all"), or one per route.

ROUTES (chat) — every inference profile AWS offers is exercised, not just the pin
(geos come from the registry's discovered inference_profiles; a new geo is picked
up with no code change): the pinned id from each Region Chat Studio offers, every
other profile (global. + each geo) from each Region it covers, the plain in-Region
id where on-demand is supported, and each id with NO Region (server must route
it). Each call asserts: the id invoked, a Region that id can be served from, and
the cost billed at the registry's official rate for THAT route (Global vs
regional). A pass that needed the server's temperature self-heal is a FAIL.
CONTENT checks (pinned id, pinned + home Region): a system-prompt codeword, a
multi-turn follow-up, and — for vision models — a red-disc image sent exactly as
Chat Studio sends it; the reply must show the model received each (a model that
declines the check is a WARN). An AWS 5xx / throttle is retried once (noted in
the row) — it says nothing about the route.

EXCLUDED stage (in-process probes): every Region the server hides an id from
(recorded as not answering, or not listed as serving it) is re-probed. FAIL = it
answers (a working Region is hidden); WARN = a recorded timeout answers now.

LLM stage (in-process): invoke_llm — the path prompt enhancement, templates and
collections use — per selected model (no Region: resolved like Chat Studio), with
an image for vision models, and per LLM category. No HTTP route reaches it without
a long, costly generation, so the harness calls the server's own function.

REGISTRY stage (no invocations): pins are offered profiles in covered Regions that
answer (Regions the Sync probe recorded as not answering are excluded),
pin posture follows the residency setting, categories hold their model's current
pin, /api/chat/models serves each entry's own id + an exact Region picker + the
active flags, no duplicate foundation models, Global rate ≤ regional rate.

USAGE
  python3 tools/sanity_test.py                         # all stages, all regions
  python3 tools/sanity_test.py --stages chat           # one stage
  python3 tools/sanity_test.py --region-scope pinned   # one Region per route
  python3 tools/sanity_test.py --geo-scope pinned      # chat: pinned id only
  python3 tools/sanity_test.py --stages registry       # static consistency only
  python3 tools/sanity_test.py --stages excluded,llm   # hidden Regions + invoke_llm
  python3 tools/sanity_test.py --tiers 2 --versions 2  # selection depth (0 0 = every model)
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
import urllib.parse
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



# ── HTTP helpers (stdlib only) ──────────────────────────────────────────────
def _req(url: str, payload=None, method="GET", accept="application/json", timeout=120):
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Accept": accept}
    if data is not None:
        headers["Content-Type"] = "application/json"
    return urllib.request.Request(url, data=data, headers=headers, method=method)


def _urlopen(req: urllib.request.Request, timeout: float):
    """The one place the harness opens a URL — http(s) only (no file:/custom
    schemes), always against the server under test (--base)."""
    if urllib.parse.urlparse(req.full_url).scheme not in ("http", "https"):
        raise ValueError(f"refusing non-http(s) URL: {req.full_url}")
    return urllib.request.urlopen(req, timeout=timeout)  # nosec B310 # nosemgrep -- scheme checked above; URL is the --base server under test


def get_json(base, path, timeout=60):
    with _urlopen(_req(base + path, timeout=timeout), timeout) as r:
        return json.loads(r.read().decode())


def post_json(base, path, payload, timeout=120):
    with _urlopen(_req(base + path, payload, "POST", timeout=timeout), timeout) as r:
        return json.loads(r.read().decode())


def post_sse(base, path, payload, timeout=300):
    """POST and consume an SSE stream; return the list of parsed `data:` event dicts."""
    events = []
    req = _req(base + path, payload, "POST", accept="text/event-stream", timeout=timeout)
    with _urlopen(req, timeout) as r:
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


_GEOS: set = set()


def _strip_geo(mid: str) -> str:
    # Geo prefixes = the inference-profile geos AWS Sync discovered (registry
    # `inference_profiles`) — same rule as model_registry.strip_geo_prefix.
    if not _GEOS:
        profiles = json.loads(REGISTRY_PATH.read_text()).get("inference_profiles") or {}
        _GEOS.update(g for geos in profiles.values() for g in geos)
    head, dot, rest = mid.partition(".")
    return rest if dot and "." in rest and head in _GEOS else mid


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
        if dead_regions(c, c["model_id"]) and not valid_regions(c, c["model_id"]):
            continue  # no Region answers it — the server hides it from Chat Studio
        cand.append({**c, "key": key})
    # group by provider → tier → members
    by_prov = defaultdict(lambda: defaultdict(list))
    for c in cand:
        by_prov[c.get("provider", "?")][_tier_key(c["model_id"])].append(c)
    selected = []
    for prov, tier_map in by_prov.items():
        ranked_tiers = sorted(tier_map.items(),
                              key=lambda kv: (max(_recency(m) for m in kv[1]), kv[0]), reverse=True)
        for _tier, members in ranked_tiers[:tiers or None]:     # 0 = every tier
            for c in sorted(members, key=_recency, reverse=True)[:versions or None]:
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
    """Regions the entry's PINNED id can be invoked from (a geo profile id only
    from the Regions that profile covers) — all of them, or just the pin."""
    if scope == "pinned":
        return [cfg.get("region")] if cfg.get("region") else (cfg.get("available_regions") or [])[:1]
    return valid_regions(cfg, cfg.get("model_id", "")) or \
        ([cfg["region"]] if cfg.get("region") else [])


# ── Inference-profile routes (every geo AWS offers, all from the registry) ────
_REG_CACHE: dict = {}


def _profile_map() -> dict:
    if "pmap" not in _REG_CACHE:
        _REG_CACHE["pmap"] = json.loads(REGISTRY_PATH.read_text()).get("inference_profiles") or {}
    return _REG_CACHE["pmap"]


def _norm_base(mid: str) -> str:
    """Profile-map key for an id — same normalization the Sync keys it by
    (geo prefix, ':qualifier', trailing '-vN' and a size-suffixed '-N' dropped)."""
    s = _strip_geo(mid).split(":")[0]
    s = re.sub(r"-v\d+$", "", s)
    return re.sub(r"(\d+b)-\d+$", r"\1", s)


def profiles_for(mid: str) -> dict:
    """{geo: [Regions that profile covers]} AWS offers for this foundation model."""
    return _profile_map().get(_norm_base(mid)) or {}


def _geo_of(mid: str) -> str:
    """The id's profile geo ('global', 'us', 'eu', …) or '' for an in-Region id."""
    return mid.split(".", 1)[0] if _strip_geo(mid) != mid else ""


def valid_regions(cfg: dict, mid: str) -> list[str]:
    """Regions ``mid`` (any profile/plain id of this entry's model) can be
    invoked from: a geo profile → the Regions it covers that the account has the
    model in; ``global.`` / an in-Region id → every Region the model is in. Per
    what the Sync recorded: a Mantle-served model → Regions whose Mantle lists it;
    a plain id → Regions serving it on demand (as listed by the Sync). Minus
    the Regions recorded as not answering this id kind (unservable_regions)."""
    avail = cfg.get("available_regions") or ([cfg["region"]] if cfg.get("region") else [])
    geo = _geo_of(mid)
    if cfg.get("invoke_endpoint") == "bedrock-mantle" and cfg.get("mantle_regions"):
        avail = cfg["mantle_regions"]
    elif not geo and "on_demand_regions" in cfg:
        avail = [r for r in avail if r in cfg["on_demand_regions"]]
    avail = set(avail) - set(dead_regions(cfg, mid))
    if geo and geo != "global":
        return sorted(set(profiles_for(mid).get(geo) or ()) & avail)
    return sorted(avail)


def dead_regions(cfg: dict, mid: str) -> dict:
    """{Region: info} the Sync probe (or a chat timeout) recorded as not answering
    this id kind — the server skips them (services/servability.py)."""
    return ((cfg.get("unservable_regions") or {}).get(_geo_of(mid))) or {}


def server_settings() -> dict:
    """Residency + home Regions as the server reads them (config.py / .env)."""
    try:
        sys.path.insert(0, str(ROOT))
        from backend.config import settings
        geo = (settings.preferred_residency_geo or "").strip().lower()
        # Same validation as the server (admin._preferred_residency_geo): 'global'
        # is not a residency, and an undiscovered geo is ignored → no constraint.
        offered = {g for p in _profile_map().values() for g in p}
        if geo == "global" or (offered and geo not in offered):
            geo = ""
        return {"residency": geo,
                "home_models": settings.aws_region_models, "home_images": settings.aws_region_images}
    except Exception:
        return {"residency": "", "home_models": "", "home_images": ""}


def _pick_one(regions: list, *prefer) -> list:
    for r in prefer:
        if r and r in regions:
            return [r]
    return regions[:1]


def chat_routes(cfg: dict, scope: str, served: dict | None, home: str) -> list[dict]:
    """Every way a user/app can invoke this model, each checked independently:
      - the pinned id from every Region Chat Studio offers for it (served usable_regions)
      - EVERY other inference profile AWS offers (global. + each geo), from each
        Region that profile covers — a lookup keyed by one exact id breaks here
      - the plain in-Region id where the model supports on-demand
      - each id with NO Region (the server must route it to a Region it can serve)
    `scope=pinned` keeps one Region per route (the home/pinned Region when valid)."""
    pinned = cfg.get("model_id", "")
    base = _strip_geo(pinned)
    out = []
    pin_regions = sorted((served or {}).get("usable_regions") or regions_for(cfg, "all"))
    ids = [(pinned, "pinned:" + (_geo_of(pinned) or "in-region"), pin_regions)]
    for geo in sorted(profiles_for(pinned)):
        mid = f"{geo}.{base}"
        if mid != pinned:
            ids.append((mid, geo, valid_regions(cfg, mid)))
    if "ON_DEMAND" in (cfg.get("inference_types") or []) and base != pinned:
        ids.append((base, "in-region", valid_regions(cfg, base)))
    for mid, kind, regions in ids:
        if not regions:
            out.append({"id": mid, "kind": kind, "region": "", "expect": [], "skip":
                        "no Region this account has the model in is covered by this profile"})
            continue
        chosen = _pick_one(regions, cfg.get("region"), home) if scope == "pinned" else regions
        out += [{"id": mid, "kind": kind, "region": r, "expect": [r]} for r in chosen]
        expect_auto = ([cfg["region"]] if mid == pinned and cfg.get("region") in regions
                       else regions)
        out.append({"id": mid, "kind": kind + "/auto", "region": None, "expect": expect_auto})
    # Content checks (system prompt, multi-turn, vision) on the pinned id from the
    # pinned and home Regions — the routes users hit by default.
    checks = [c for c in CONTENT_CHECKS if c != "vision" or cfg.get("has_vision")]
    for r in sorted({r for r in (cfg.get("region"), home) if r in pin_regions}) or pin_regions[:1]:
        out += [{"id": pinned, "kind": f"check:{c}", "region": r, "expect": [r], "check": c}
                for c in checks]
    return out


def expected_llm_cost(reg: dict, mid: str, region: str, tin: int, tout: int):
    """Independent re-derivation of what one call must cost from the registry's
    official rates: the Region's rate set (or its geography's / '*'), the Global
    rate for a global. id and the regional rate otherwise (each falling back to
    the other). None when the registry has no price for the model."""
    cms = reg.get("chat_models", {}) or {}
    base = _strip_geo(mid)
    cm = next((c for c in cms.values() if c.get("model_id") == mid), None) or \
        next((c for c in cms.values() if _strip_geo(c.get("model_id", "")) == base), None)
    if not cm:
        return None
    tp = cm.get("token_pricing") or {}
    by_region = tp.get("by_region") or {}
    rates = by_region.get(region)
    if rates is None and region:
        g = region.split("-", 1)[0].upper()
        rates = next((by_region[k] for k in (f"geo:{g}", "geo:AP" if g == "AP" else "",
                                             "geo:APAC" if g == "AP" else "") if k and k in by_region), None)
    rates = rates or by_region.get("*") or tp.get("rates") or {}
    order = ("global_", "") if mid.startswith("global.") else ("", "global_")
    io = next(((rates[f"{p}input_per_1k"], rates[f"{p}output_per_1k"]) for p in order
               if rates.get(f"{p}input_per_1k") is not None
               and rates.get(f"{p}output_per_1k") is not None), None)
    if not io:
        pr = (cm.get("token_pricing_by_region") or {}).get(region) or {}
        io = (pr.get("input_per_1k"), pr.get("output_per_1k")) if pr else None
    if not io or not any(io):
        io = (cm.get("input_price_per_1k"), cm.get("output_price_per_1k"))
    if not any(io):
        return None
    return round(tin * (io[0] or 0) / 1000 + tout * (io[1] or 0) / 1000, 6)


# ── Stage runners (drive the real endpoints) ─────────────────────────────────
CHAT_PROMPT = [{"role": "user", "content": "Reply with exactly one word: OK"}]


# A red disc on white, not a solid fill: Nova 2 reads a uniform image as blank
# ("black"/"white") on every route, even via raw Converse.
VISION_PROMPT = "What colour is the circle? Reply with one word."


def _vision_png(size=128) -> bytes:
    import io
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (size, size), (255, 255, 255))
    ImageDraw.Draw(img).ellipse((size // 4, size // 4, size * 3 // 4, size * 3 // 4), fill=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _vision_messages():
    import base64
    # Exactly what Chat Studio sends for an attachment: a Converse image block
    # whose bytes are base64 text (JSON can't carry raw bytes).
    return [{"role": "user", "content": [
        {"image": {"format": "png", "source": {"bytes": base64.b64encode(_vision_png()).decode()}}},
        {"text": VISION_PROMPT}]}]


# Beyond "it answered": does the request's content reach the model on this route?
# Each check's reply must contain `expect` (case-insensitive). The multiturn check
# asks for arithmetic on the earlier turn, not recall of what the user said:
# small models refuse "what did I tell you" questions as memory or privacy issues.
CONTENT_CHECKS = {
    "system": {"what": "system prompt ignored", "expect": "pineapple",
               "system": "Whatever the user says, reply with only the codeword PINEAPPLE.",
               "messages": lambda: [{"role": "user", "content": "Say something."}]},
    "multiturn": {"what": "earlier turns lost", "expect": "42",
                  "messages": lambda: [
                      {"role": "user", "content": "Think of the number 41. Reply OK."},
                      {"role": "assistant", "content": "OK, I'm thinking of 41."},
                      {"role": "user", "content": "Add one to that number. "
                                                  "Reply with just the result."}]},
    "vision": {"what": "image not seen", "expect": "red", "messages": _vision_messages},
}

# AWS-side transient failures (5xx / throttling / model warming): retried once,
# since they say nothing about whether the route is wired correctly.
TRANSIENT_ERROR = re.compile(r"ServiceUnavailable|InternalServer|Throttl|ModelNotReady|"
                             r"too many requests|\b50[0234]\b", re.I)
TRANSIENT_RETRY_DELAY_S = 5
# A content check the model declined (over-cautious refusal) says the request
# reached it, not that the route dropped content: WARN, not FAIL.
REFUSAL = re.compile(r"^\W*(sorry|i'm sorry|i am sorry|i can(no|')t|i'm (not able|unable)|"
                     r"i am (not able|unable))\b", re.I)
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


# The server's per-route Mantle timeout (mantle_client._get_openai_client): a route
# that hangs costs this long before chat falls back to the next one.
MANTLE_ROUTE_TIMEOUT_S = 90


def run_chat(base, model, region, max_tokens, timeout=None, model_id=None,
             messages=None, system_prompt=""):
    # 90s: past the server's 60s Bedrock read timeout, so a stalled model surfaces
    # as the server's own error (logged inside this stage), and slow REASONING
    # models (grok, kimi-thinking) aren't flagged as hangs. A Mantle model gets
    # room for one hung route + the fallback that answers (what a user waits for),
    # so a recovered request isn't reported as a hang. temperature is ALWAYS sent —
    # the server must drop it for models the registry says reject it (gate by
    # foundation model, so every profile id of the model is gated).
    if timeout is None:
        timeout = (2 * MANTLE_ROUTE_TIMEOUT_S + 20 if model.get("invoke_endpoint") == "bedrock-mantle"
                   else 90)
    payload = {
        "model_id": model_id or model["model_id"], "region": region,
        "messages": messages or CHAT_PROMPT, "system_prompt": system_prompt,
        "temperature": 0.7, "max_tokens": max_tokens,
    }
    try:
        events = post_sse(base, "/api/chat/stream", payload, timeout=timeout)
    except (TimeoutError, OSError) as e:
        # A geo-pinned id sent to a non-matching region often HANGS (Bedrock accepts
        # but never responds) rather than erroring — bound it and report clearly.
        return False, f"timeout/no-response after {timeout}s ({type(e).__name__}) — region likely can't serve this id", None, ""
    err = next((e for e in events if e.get("type") == "error"), None)
    blocked = next((e for e in events if e.get("type") == "content_blocked"), None)
    meta = next((e for e in events if e.get("type") == "metadata"), None)
    text = "".join(e.get("text", "") for e in events if e.get("type") == "delta")
    got_stop = any(e.get("type") == "stop" for e in events)
    if err:
        return False, f"error: {err.get('detail', '')[:120]}", meta, text
    if blocked:
        return False, "content_blocked", meta, text
    if text.strip() or got_stop:
        return True, (text.strip()[:60] or "(stop, no text)"), meta, text
    return False, f"no output ({len(events)} events)", meta, text


def run_chat_route(base, reg, model, route, max_tokens):
    """One route of a model (chat_routes) + the checks that make it correct, not
    just 'it answered': the server invoked the id asked for, from a Region that
    route can be served from, and billed it at the registry's rate for THAT
    route (Global rate for global., regional otherwise)."""
    if route.get("skip"):
        return None, f"SKIP {route['skip']}"
    check = CONTENT_CHECKS.get(route.get("check") or "")
    kw = {"messages": check["messages"](), "system_prompt": check.get("system", "")} if check else {}
    ok, detail, meta, text = run_chat(base, model, route["region"], max_tokens, model_id=route["id"], **kw)
    retried = ""
    if not ok and TRANSIENT_ERROR.search(detail):
        # An AWS-side 5xx/throttle says nothing about the route — retry it once.
        retried = f" (retried after: {detail[:60]})"
        time.sleep(TRANSIENT_RETRY_DELAY_S)
        ok, detail, meta, text = run_chat(base, model, route["region"], max_tokens,
                                          model_id=route["id"], **kw)
    if not ok:
        return False, detail + retried
    if check and check["expect"] not in text.lower():
        if REFUSAL.match(text):
            return "WARN", f"{detail} | model declined the {route['check']} check (not a routing fault){retried}"
        return False, f"{detail} | {check['what']}: reply lacks '{check['expect']}'{retried}"
    if not meta:
        return False, f"{detail} | no metadata event (tokens/cost/route not reported)"
    problems = []
    if meta.get("model_id") and meta["model_id"] != route["id"]:
        problems.append(f"invoked {meta['model_id']} instead of {route['id']}")
    used = meta.get("region") or ""
    if route["expect"] and used not in route["expect"]:
        problems.append(f"routed to {used or '?'} — not a Region this id can be served from "
                        f"({', '.join(route['expect'][:6])})")
    tin, tout = int(meta.get("input_tokens") or 0), int(meta.get("output_tokens") or 0)
    cost = float(meta.get("cost_usd") or 0)
    want = expected_llm_cost(reg, route["id"], used, tin, tout)
    if want is None:
        note = "unpriced in registry"
    elif tin + tout == 0:
        note = "no token usage reported"
        problems.append(note)
    elif abs(cost - want) > max(2e-6, 0.02 * want):
        problems.append(f"cost ${cost:.6f} ≠ registry rate ${want:.6f} for {route['kind']} @ {used}")
        note = ""
    else:
        note = f"${cost:.6f}"
    if problems:
        return False, f"{detail} | " + "; ".join(problems) + retried
    return True, f"{detail} | {used} {tin}+{tout} tok {note}{retried}"


# ── In-process stages (no HTTP route reaches these paths cheaply) ────────────
def _backend():
    """The server's own modules, imported once on the main thread (a threaded
    first import of the openai SDK can deadlock)."""
    if "backend" not in _REG_CACHE:
        sys.path.insert(0, str(ROOT))
        import openai  # noqa: F401
        from backend.services import bedrock_client, mantle_client, servability
        from backend.services.model_registry import get_registry
        get_registry()
        _REG_CACHE["backend"] = (bedrock_client, mantle_client, servability)
    return _REG_CACHE["backend"]


def excluded_routes(cfg: dict) -> list[dict]:
    """Regions the server WON'T route each of this model's ids to — the ones a
    Region picker hides: recorded as not answering (unservable_regions), or not
    listed as serving it (mantle_regions / on_demand_regions). Each is re-probed
    to prove the exclusion still holds."""
    _, mc, _ = _backend()
    pinned = cfg.get("model_id", "")
    base = _strip_geo(pinned)
    avail = set(cfg.get("available_regions") or ([cfg["region"]] if cfg.get("region") else []))
    mantle = cfg.get("invoke_endpoint") == "bedrock-mantle"
    ids = {pinned} | {f"{g}.{base}" for g in profiles_for(pinned)}
    if "ON_DEMAND" in (cfg.get("inference_types") or []):
        ids.add(base)
    out = []
    for mid in sorted(ids):
        geo = _geo_of(mid)
        universe = set(profiles_for(mid).get(geo) or ()) & avail if geo and geo != "global" else avail
        if mantle:
            universe &= mc.known_mantle_regions()  # elsewhere a call is remapped, not probed
        dead = dead_regions(cfg, mid)
        for r in sorted(universe - set(valid_regions(cfg, mid))):
            why = (dead.get(r) or {}).get("reason") if r in dead else \
                ("not in mantle_regions" if mantle else "not in on_demand_regions")
            out.append({"id": mid, "kind": "excluded:" + (geo or "in-region"), "region": r,
                        "why": why or "recorded"})
    return out


def run_excluded(cfg, route):
    """PASS: the hidden Region still doesn't answer. FAIL: it answers — the
    server hides a working Region. WARN: a timeout-recorded Region answers now
    (intermittent; the next Sync re-probes it). SKIP: probe inconclusive."""
    _, _, sv = _backend()
    got = sv.probe_region(route["id"], cfg, route["region"])
    if got is None:
        return None, f"probe inconclusive (excluded: {route['why']})"
    if got != sv.OK:
        return True, f"still unservable ({got}); excluded: {route['why']}"
    if route["why"] == "timeout":
        return "WARN", "answers now — recorded timeout was intermittent (next Sync re-probes)"
    return False, f"ANSWERS — but the server excludes it ({route['why']})"


def llm_jobs(reg: dict, chat_models: list[dict]) -> list[tuple]:
    """invoke_llm — the path every in-app LLM step uses (prompt enhancement,
    templates, collections) — per selected model with no Region (resolved like
    Chat Studio) plus vision where supported, and per LLM category."""
    jobs = []
    for m in chat_models:
        jobs.append((m, {"id": m["model_id"], "kind": "invoke_llm", "region": None}))
        if m.get("has_vision"):
            jobs.append((m, {"id": m["model_id"], "kind": "invoke_llm:vision", "region": None,
                             "check": "vision"}))
    for name, cat in sorted((reg.get("categories") or {}).items()):
        if name.endswith("_llm") and name != "fallback_llm" and cat.get("current"):
            cm = next((c for c in (reg.get("chat_models") or {}).values()
                       if c.get("model_id") == cat["current"]), {})
            jobs.append(({**cm, "key": name, "label": f"category {name}", "model_id": cat["current"]},
                         {"id": cat["current"], "kind": "invoke_llm:category", "region": None,
                          "complexity": name.removesuffix("_llm")}))
    return jobs


def run_llm(model, job, max_tokens):
    bc, _, _ = _backend()
    kw = {"max_tokens": max_tokens}
    if job.get("check") == "vision":
        kw["images"] = [_vision_png()]
        prompt, expect = VISION_PROMPT, "red"
    else:
        prompt, expect = CHAT_PROMPT[0]["content"], ""
    if job.get("complexity"):
        kw["complexity"] = job["complexity"]
    else:
        kw["model_id"] = job["id"]
    retried = ""
    for attempt in (1, 2):
        try:
            text = bc.invoke_llm(prompt, **kw) or ""
            break
        except Exception as e:
            err = f"{type(e).__name__}: {str(e)[:120]}"
            if attempt == 2 or not TRANSIENT_ERROR.search(err):
                return False, err + retried
            retried = f" (retried after: {err[:60]})"
            time.sleep(TRANSIENT_RETRY_DELAY_S)
    if not text.strip():
        return False, "empty reply" + retried
    if expect and expect not in text.lower():
        return False, f"{text.strip()[:60]} | image not seen: reply lacks '{expect}'{retried}"
    return True, text.strip()[:60] + retried


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
    with _urlopen(_req(base + path, method="DELETE", timeout=timeout), timeout) as r:
        return json.loads(r.read().decode())


def _tiny_reference_png_b64():
    """A small two-tone PNG to exercise the Image-Inspired art-direction VISION path
    (the model just needs SOMETHING to describe). Returns raw b64 (no data-URL)."""
    import io, base64
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (96, 96), (34, 40, 92))          # deep indigo ground
    d = ImageDraw.Draw(img)
    d.ellipse([20, 20, 76, 76], fill=(224, 176, 64), outline=(250, 240, 200), width=3)  # gold disc
    d.rectangle([40, 40, 56, 88], fill=(180, 60, 70))       # crimson bar
    buf = io.BytesIO(); img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def run_collection(base, model, region, extra_models=None):
    """Collections (SPEC §18) FULL end-to-end regression on the given image model:
    decompose → estimate → recompose-batch → recompose-all → regenerate-roster
    (locked-preserve) → generate (2 Batches × 1×1) → multi-model set (when a 2nd
    model is enabled) → gallery card/index → get/reconstruct → select-version
    (+ design_history) → export graceful-400 → delete cleanup. Real HTTP,
    registry-driven. Live 3D SUBMIT is intentionally NOT fired (SageMaker cost +
    async side-effects); export's no-3D path exercises the export wiring instead."""
    import urllib.error
    mk = model["key"]
    mk2 = (extra_models or [{}])[0].get("key") if extra_models else None   # a 2nd enabled model → multi-model set
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

        # 1b) IMAGE-INSPIRED art direction (SPEC §18 — the reference LOOK drives the
        # art direction via a VISION call). `reference_used` is set by the endpoint to
        # the number of images that actually reached the vision model (0 = a text-only
        # fallback ran) — so asserting >=1 GENUINELY proves the vision path executed,
        # not just that some art direction came back. Also assert non-empty text + cost.
        img_ai = post_json(base, "/api/collections/art-direction",
                           {"prompt": "a matching set in this style", "asset_type": "game_asset",
                            "image_model": mk, "reference_images": [_tiny_reference_png_b64()]},
                           timeout=180)
        if not (img_ai.get("art_direction", {}).get("text") or "").strip():
            return False, "image-inspired art-direction returned empty text", cid
        if not (img_ai.get("cost", 0) > 0):
            return False, "image-inspired art-direction booked no cost (vision path didn't run)", cid
        if not (img_ai.get("reference_used", 0) >= 1):
            return False, f"image-inspired AD did NOT feed the image to vision (reference_used={img_ai.get('reference_used')})", cid
        # A GARBAGE 'image' (valid b64, not an image) must be rejected → text fallback
        # (reference_used == 0). Proves the validation gate is real, not decode-only.
        junk = post_json(base, "/api/collections/art-direction",
                        {"prompt": "x", "image_model": mk,
                         "reference_images": ["bm90LWFuLWltYWdl"]}, timeout=120)  # b64("not-an-image")
        if junk.get("reference_used", 0) != 0:
            return False, f"garbage reference not rejected (reference_used={junk.get('reference_used')})", cid
        # And the guided-scaffold dimensions from the same reference image (vision).
        img_fields = post_json(base, "/api/collections/art-direction-fields",
                              {"prompt": "", "reference_images": [_tiny_reference_png_b64()]}, timeout=120)
        if not (img_fields.get("fields") and "Negative" in img_fields["fields"]):
            return False, "image-inspired field scaffold missing core dimensions", cid
        if not (img_fields.get("reference_used", 0) >= 1):
            return False, "image-inspired field scaffold did NOT run vision", cid
        steps.append("image-inspired-AD")

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
        rr_locked = next((x for x in rr.get("roster", []) if x["slug"] == roster[0]["slug"]), None)
        if not rr_locked:
            return False, "regenerate-roster dropped the locked entry", cid
        # LOCK must preserve the entry VERBATIM — not merely keep the slug. A regen that
        # kept the slug but rewrote its prompt would otherwise pass falsely.
        if rr_locked.get("model_agnostic_prompt") != roster[0]["model_agnostic_prompt"]:
            return False, "regenerate-roster did not preserve the locked entry's prompt verbatim", cid
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

        # 6b) MULTI-MODEL set (SPEC §18.4): a multi-model selection must render EVERY
        # chosen model (the exact gap behind "where are the other models' outputs?").
        # Only when a 2nd model is enabled: a fresh 1-Batch collection, 2 models × 1×1,
        # then assert the reconstructed Batch's Jobs carry BOTH model keys. Own cid +
        # own cleanup so the primary flow (steps 7-11) stays on the single-model cid.
        if mk2:
            cid2 = None
            try:
                d2 = post_json(base, "/api/collections/decompose",
                               {"prompt": ask, "asset_type": "game_asset", "image_model": mk, "count": 1}, timeout=180)
                r2, cid2 = (d2.get("roster") or [])[:1], d2.get("collection_id")
                if not r2 or not cid2:
                    return False, "multi-model decompose returned no roster/cid", cid
                ev2 = post_sse(base, "/api/collections/generate",
                               {"collection_id": cid2, "name": d2.get("name", "MM Set"), "raw_ask": ask,
                                "art_direction": d2["art_direction"], "roster": r2,
                                "image_model": mk, "selected_models": [mk, mk2],
                                "region": region, "asset_type": "game_asset",
                                "num_options": 1, "num_variations": 1,
                                "llm_cost_ledger": d2.get("llm_cost_ledger", []), "design_cost": d2.get("cost", 0)},
                               timeout=300)
                c2 = next((e for e in ev2 if e.get("type") == "collection_complete"), None)
                if c2 is None or c2.get("completed_batches") != 1:
                    return False, f"multi-model generate did not complete 1 batch: {c2}", cid
                mm = get_json(base, f"/api/collections/{cid2}", timeout=30)
                mods = {v.get("model_used")
                        for b in mm.get("batches", [])
                        for o in ((b.get("batch") or {}).get("options") or [])
                        for v in o.get("variants", [])}
                missing = {mk, mk2} - mods
                if missing:
                    return False, f"multi-model set missing model(s) {sorted(missing)} (got {sorted(m for m in mods if m)})", cid
                steps.append("multi-model×2")

                # 6b-retry) The per-Batch RETRY endpoint (/generate-batch) must reproduce
                # the SAME model shape — this is the path that carried the multi-model
                # bug (single-model retry orphaned the set). Retry the one Batch on a
                # VALID slug (no forced block needed) and re-assert BOTH models land in
                # the (newly-minted) batch. A single-model regression here would fail.
                slug2 = (r2[0] or {}).get("slug")
                rb = post_json(base, f"/api/collections/{cid2}/generate-batch",
                               {"slug": slug2}, timeout=300)
                if not (rb.get("ok") and rb.get("batch_id")):
                    return False, f"multi-model retry did not succeed: {rb}", cid
                mm2 = get_json(base, f"/api/collections/{cid2}", timeout=30)
                mods2 = {v.get("model_used")
                         for b in mm2.get("batches", [])
                         for o in ((b.get("batch") or {}).get("options") or [])
                         for v in o.get("variants", [])}
                if {mk, mk2} - mods2:
                    return False, f"multi-model RETRY regressed to single-model (got {sorted(m for m in mods2 if m)})", cid
                steps.append("multi-model-retry×2")
            finally:
                if cid2:
                    try:
                        _delete_json(base, f"/api/collections/{cid2}?delete_assets=true")
                    except Exception:
                        pass
        else:
            steps.append("multi-model(n/a:1 enabled model)")

        # 6c) IMAGE-INSPIRED generation with the reference ANCHOR (SPEC §18): a fresh
        # 1-Batch collection whose art direction AND per-Batch render are driven by a
        # reference image (cohesion_mode=reference). Assert it completes AND the record
        # persisted the reference + image_inspired flag + reference cohesion — proving
        # the anchor branch actually ran (not a silent text fallback). Own cid+cleanup.
        cid3 = None
        try:
            ref_png = _tiny_reference_png_b64()
            d3 = post_json(base, "/api/collections/decompose",
                           {"prompt": "a small matching set in this style", "asset_type": "game_asset",
                            "image_model": mk, "count": 1, "reference_images": [ref_png]}, timeout=180)
            r3, cid3 = (d3.get("roster") or [])[:1], d3.get("collection_id")
            if not r3 or not cid3:
                return False, "image-inspired decompose returned no roster/cid", cid
            if not (d3.get("reference_used", 0) >= 1):
                return False, "image-inspired decompose did NOT run vision on the reference", cid
            ev3 = post_sse(base, "/api/collections/generate",
                           {"collection_id": cid3, "name": d3.get("name", "Img Set"),
                            "raw_ask": "a small matching set in this style",
                            "art_direction": d3["art_direction"], "roster": r3,
                            "image_model": mk, "asset_type": "game_asset",
                            "num_options": 1, "num_variations": 1,
                            "cohesion_mode": "reference", "reference_images": [ref_png],
                            "llm_cost_ledger": d3.get("llm_cost_ledger", []), "design_cost": d3.get("cost", 0)},
                           timeout=300)
            c3 = next((e for e in ev3 if e.get("type") == "collection_complete"), None)
            if c3 is None or c3.get("completed_batches") != 1:
                return False, f"image-inspired generate did not complete 1 batch: {c3}", cid
            full3 = get_json(base, f"/api/collections/{cid3}", timeout=30)
            rec3 = full3.get("record", {})
            if rec3.get("knobs", {}).get("cohesion_mode") != "reference":
                return False, "image-inspired run did not persist reference cohesion", cid
            if not rec3.get("reference_images") or not rec3.get("knobs", {}).get("image_inspired"):
                return False, "image-inspired run did not persist the reference/flag", cid
            # The DECISIVE check: a produced Job must carry reference_mode='inspired'
            # (written only when the render actually used the anchor image) — proving
            # the anchor BRANCH ran, not just that config persisted. Config fields above
            # can be set even if the anchor were skipped; this cannot.
            variants3 = [v for b in full3.get("batches", [])
                         for o in ((b.get("batch") or {}).get("options") or [])
                         for v in o.get("variants", [])]
            if not any(v.get("reference_mode") == "inspired" and v.get("reference_guided")
                       for v in variants3):
                return False, "image-inspired set did NOT anchor to the reference (no job reference_mode=inspired)", cid
            steps.append("image-inspired-generate")

            # 6c-reload) The persisted reference must be SERVABLE for reloading the
            # collection into Image Studio — GET /{cid}/reference/ref_0.png returns the
            # PNG; a non-conforming name is rejected (no path traversal). Without this
            # the image-inspired reload can't repopulate the Reference Studio.
            ref_fn = (rec3.get("reference_images") or ["ref_0.png"])[0]
            with _urlopen(_req(f"{base}/api/collections/{cid3}/reference/{ref_fn}", timeout=30), 30) as _rr:
                if _rr.status != 200 or not _rr.read(8).startswith(b"\x89PNG"):
                    return False, "collection reference route did not serve the persisted PNG", cid
            try:
                _urlopen(_req(f"{base}/api/collections/{cid3}/reference/asset.png", timeout=15), 15)
                return False, "collection reference route accepted a non-ref filename (should 400)", cid
            except urllib.error.HTTPError as e:
                if e.code != 400:
                    return False, f"collection reference route bad-name status {e.code} (want 400)", cid
            steps.append("collection-reference-route")
        finally:
            if cid3:
                try:
                    _delete_json(base, f"/api/collections/{cid3}?delete_assets=true")
                except Exception:
                    pass

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

        # 8b) BACKGROUND REMOVAL (collections default to cut-outs, remove_background=True):
        # fetch a produced Job's PNG and assert it actually carries an alpha channel with
        # some transparency — proving the cut-out ran (not just that generation completed).
        png_rel = next((v.get("png_path") for b in full.get("batches", [])
                        for o in ((b.get("batch") or {}).get("options") or [])
                        for v in o.get("variants", []) if v.get("png_path")), None)
        if not png_rel:
            return False, "no produced Job PNG to check background removal", cid
        try:
            import io as _io
            from PIL import Image as _Image
            with _urlopen(_req(f"{base}{png_rel}", timeout=60), 60) as _r:
                _img = _Image.open(_io.BytesIO(_r.read()))
            if _img.mode not in ("RGBA", "LA") and "transparency" not in _img.info:
                return False, f"background not removed — Job PNG has no alpha (mode={_img.mode})", cid
            # a cut-out has genuinely transparent pixels (min alpha well below opaque)
            alpha = _img.convert("RGBA").getchannel("A")
            if alpha.getextrema()[0] > 250:
                return False, "background not removed — alpha channel is fully opaque", cid
        except urllib.error.HTTPError as e:
            return False, f"could not fetch Job PNG for bg-removal check ({e.code})", cid
        steps.append("bg-removed(alpha)")

        # 8c) COLLECTION LINEAGE stamped on Jobs (SPEC §18.7c) — the Asset Viewer's
        # Collection panel reads these off the Job's metadata. Fetch a member Job's
        # full metadata and assert the lineage (collection id + NAME + subject +
        # model-agnostic prompt) is actually stamped — not just that a Job exists.
        job_id = next((v.get("id") for b in full.get("batches", [])
                       for o in ((b.get("batch") or {}).get("options") or [])
                       for v in o.get("variants", []) if v.get("id")), None)
        if not job_id:
            return False, "no member Job to check collection lineage", cid
        jm = get_json(base, f"/api/gallery/{job_id}", timeout=30)
        _lin = {k: (jm.get(k) or "") for k in ("collection_id", "collection_name", "batch_name", "model_agnostic_prompt")}
        if _lin["collection_id"] != cid or not all(str(_lin[k]).strip() for k in _lin):
            return False, f"Job metadata missing collection lineage: {_lin}", cid
        steps.append("collection-lineage")

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
            _urlopen(_req(f"{base}/api/collections/{cid}/export?fmt=fbx", timeout=60), 60)
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


# ── Registry / routing consistency (no invocations) ─────────────────────────
def registry_checks(base, reg) -> list[dict]:
    """Static checks that every pin, category and served id is one the app can
    actually invoke — the failures here are the ones a single happy-path call
    never shows (stale category ids, a profile pinned in a Region it doesn't
    cover, Chat Studio serving another model's id, a Region picker offering a
    Region the id can't route from). Rows: PASS / FAIL / WARN (WARN never fails)."""
    rows = []
    cfgs = server_settings()
    residency, home = cfgs["residency"], cfgs["home_models"]

    def row(check, name, ok, detail, region="", warn=False):
        rows.append({"model": name, "key": check, "model_id": "", "region": region,
                     "route": check, "invoke_ok": ok,
                     "status": "PASS" if ok else ("WARN" if warn else "FAIL"), "detail": detail})

    chat = {k: c for k, c in (reg.get("chat_models") or {}).items() if isinstance(c, dict)}
    enabled = {k: c for k, c in chat.items() if c.get("enabled") is not False}

    # 1) Every geo-prefixed pin (chat / image / post-processing) is a profile AWS
    #    offers for that model, pinned in a Region the profile covers.
    for section in ("chat_models", "image_models", "post_processing"):
        for k, c in (reg.get(section) or {}).items():
            mid = (c or {}).get("model_id", "") if isinstance(c, dict) else ""
            geo = _geo_of(mid)
            if not geo:
                continue
            profs = profiles_for(mid)
            name = f"{section}.{k}"
            if geo not in profs:
                row("pin-valid", name, False, f"{mid}: AWS offers no '{geo}' profile "
                    f"(offered: {', '.join(sorted(profs)) or 'none'})", c.get("region", ""))
            elif geo != "global" and c.get("region") not in profs[geo]:
                row("pin-valid", name, False, f"{mid} pinned @ {c.get('region')} — the '{geo}' "
                    f"profile doesn't cover it", c.get("region", ""))
            else:
                row("pin-valid", name, True, f"{mid} @ {c.get('region')}", c.get("region", ""))

    # 1b) Every enabled chat pin is servable where it's pinned, per the Sync's
    #     per-Region data (Mantle catalog / on-demand) — not merely listed there.
    for k, c in enabled.items():
        mid, pin = c.get("model_id", ""), c.get("region", "")
        served = valid_regions(c, mid)
        mantle = c.get("invoke_endpoint") == "bedrock-mantle"
        if mantle and "mantle_regions" not in c:
            row("pin-servable", k, False, f"{mid}: Mantle-served but no mantle_regions "
                f"recorded — run AWS Sync", pin, warn=True)
        elif pin and served and pin not in served:
            row("pin-servable", k, False, f"{mid} pinned @ {pin} — servable only in "
                f"{', '.join(served)}", pin)
        elif not served and dead_regions(c, mid):
            row("pin-servable", k, False, f"{mid}: no Region answers it ("
                + ", ".join(f"{r}: {i.get('reason')}" for r, i in dead_regions(c, mid).items())
                + ") — hidden from Chat Studio", pin, warn=True)
        elif not served:
            row("pin-servable", k, False, f"{mid}: no Region can serve this id", pin)
        else:
            row("pin-servable", k, True, f"{mid} @ {pin}" + (" (Mantle)" if mantle else ""), pin)

    # 2) Pin posture follows the residency setting (none = global. where offered;
    #    set = that geo's profile where it covers a Region the model is in).
    for k, c in enabled.items():
        mid, profs = c.get("model_id", ""), profiles_for(c.get("model_id", ""))
        if not profs or not c.get("available_regions"):
            continue
        avail = set(c["available_regions"])
        if residency and residency in profs and set(profs[residency]) & avail:
            want = residency
        elif not residency and "global" in profs:
            want = "global"
        else:
            continue
        got = _geo_of(mid) or "in-region"
        row("pin-posture", k, got == want,
            f"{mid} — expected the {want}. profile (residency: {residency or 'none'})", c.get("region", ""))
        if got == want == "global" and home and home in avail and c.get("region") != home:
            row("pin-home", k, False, f"{mid} pinned @ {c.get('region')}, home Region {home} "
                f"is available (tie-break should pick it)", c.get("region", ""), warn=True)

    # 3) No two enabled entries are the same foundation model (lookups by
    #    foundation model would be ambiguous).
    seen: dict = {}
    for k, c in enabled.items():
        b = _strip_geo(c.get("model_id", ""))
        if b in seen:
            row("unique-base", k, False, f"same foundation model as {seen[b]} ({b})")
        seen[b] = k

    # 4) Categories hold their model's CURRENT pin and a Region it can use.
    for cat_name in ("fast_llm", "complex_llm", "fallback_llm"):
        cat = (reg.get("categories") or {}).get(cat_name) or {}
        cur = cat.get("current", "")
        if not cur:
            row("category", cat_name, False, "no model assigned")
            continue
        twin = next((c for c in enabled.values() if _strip_geo(c.get("model_id", "")) == _strip_geo(cur)), None)
        if not twin:
            row("category", cat_name, False, f"{cur} is not an enabled chat model", warn=True)
            continue
        ok = twin["model_id"] == cur
        ok_r = cat.get("region") in valid_regions(twin, cur)
        row("category", cat_name, ok and ok_r,
            f"{cur} @ {cat.get('region')}" + ("" if ok else f" — model is now pinned as {twin['model_id']}")
            + ("" if ok_r else " — Region can't serve this id"), cat.get("region", ""))

    # 5) Chat Studio's model list serves each entry's own pin, its foundation id,
    #    a Region picker of exactly the Regions that id routes from, and the
    #    active flag for the category models.
    try:
        served = {m.get("key"): m for m in get_json(base, "/api/chat/models").get("models", [])}
    except Exception as e:
        row("served", "/api/chat/models", False, f"fetch failed: {e}")
        served = {}
    cat_bases = {_strip_geo((reg.get("categories") or {}).get(c, {}).get("current", ""))
                 for c in ("fast_llm", "complex_llm", "fallback_llm")} - {""}
    for k, m in served.items():
        c = chat.get(k)
        if not c:
            continue  # category / custom-LLM rows
        problems = []
        if m.get("model_id") != c.get("model_id"):
            problems.append(f"serves {m.get('model_id')} for {c.get('model_id')}")
        if m.get("base_model_id") != _strip_geo(c.get("model_id", "")):
            problems.append(f"base_model_id {m.get('base_model_id')!r}")
        usable, want = sorted(m.get("usable_regions") or []), valid_regions(c, c.get("model_id", ""))
        if want and usable != want:
            problems.append(f"usable_regions {usable} ≠ {want}")
        if c.get("region") and want and c["region"] not in usable:
            problems.append(f"pinned Region {c['region']} not offered")
        if bool(m.get("is_active_llm")) != (_strip_geo(c.get("model_id", "")) in cat_bases):
            problems.append(f"is_active_llm={m.get('is_active_llm')}")
        row("served", k, not problems, "; ".join(problems) or f"{m.get('model_id')} "
            f"({len(usable)} Regions)", c.get("region", ""))

    # 6) Official pricing: a Global rate is never above the regional one.
    for k, c in enabled.items():
        tp = c.get("token_pricing") or {}
        sets = {"(pinned)": tp.get("rates") or {}, **(tp.get("by_region") or {})}
        bad = [r for r, rs in sets.items() if isinstance(rs, dict) and any(
            rs.get(f"global_{d}_per_1k") is not None and rs.get(f"{d}_per_1k") is not None
            and rs[f"global_{d}_per_1k"] > rs[f"{d}_per_1k"] for d in ("input", "output"))]
        if bad:
            row("price-order", k, False, f"Global rate above regional in {', '.join(bad[:5])}")
        if not (c.get("input_price_per_1k") or c.get("output_price_per_1k") or tp):
            row("priced", k, False, f"{c.get('model_id')} has no official price", warn=True)
    return rows


# ── Orchestration ────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="ArtSmoker end-to-end sanity harness")
    ap.add_argument("--base-url", default="http://127.0.0.1:8000")
    ap.add_argument("--stages", default="registry,chat,excluded,llm,image,video",
                    help="comma list of: registry,chat,excluded,llm,image,video,collections")
    ap.add_argument("--region-scope", choices=("all", "pinned"), default="all",
                    help="every Region each route can be served from, or one per route")
    ap.add_argument("--geo-scope", choices=("all", "pinned"), default="all",
                    help="chat: every inference profile AWS offers (global + each geo + "
                         "in-Region + no-Region), or the pinned id only")
    ap.add_argument("--concurrency", type=int, default=10,
                    help="parallel in-flight requests per stage (hides cross-geo hangs)")
    ap.add_argument("--log-path", default="", help="server log file to verify (default logs/artsmoker.log)")
    ap.add_argument("--tiers", type=int, default=2, help="top N tiers per provider (chat; 0 = all)")
    ap.add_argument("--versions", type=int, default=2, help="top N versions per tier (chat; 0 = all)")
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

    def run_stage(name, models, runner, jobs=None):
        # (model, target) matrix — target is a Region, or a chat route dict
        jobs = jobs if jobs is not None else \
            [(m, r) for m in models for r in regions_for(m, args.region_scope)]
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

        def work(idx, m, target):
            route = target if isinstance(target, dict) else None
            region = (route["region"] if route else target) or ""
            mid = route["id"] if route else m.get("model_id")
            label = (f"{m.get('label', m['key'])} [{route['kind']}] {mid} @ {region or 'auto'}"
                     if route else f"{m.get('label', m['key'])} @ {region}")
            t0 = time.time()
            try:
                ok, detail, *_ = runner(m, target)
            except urllib.error.HTTPError as e:
                ok, detail = False, f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:120]}"
            except Exception as e:
                ok, detail = False, f"{type(e).__name__}: {str(e)[:120]}"
            dt = time.time() - t0
            status = "SKIP" if ok is None else "WARN" if ok == "WARN" else ("PASS" if ok else "FAIL")
            rows[idx] = {"model": m.get("label", m["key"]), "model_id": mid,
                         "key": m["key"], "region": region or "auto",
                         "route": route["kind"] if route else "pinned",
                         "invoke_ok": bool(ok), "detail": detail,
                         "seconds": round(dt, 1), "status": status}
            with lock:
                done["n"] += 1
                print(f"[{done['n']}/{len(jobs)}] {status} {label} — {detail} "
                      f"({dt:.1f}s)", flush=True)

        with ThreadPoolExecutor(max_workers=conc) as ex:
            futs = [ex.submit(work, i, m, r) for i, (m, r) in enumerate(jobs)]
            for _ in as_completed(futs):
                pass

        # Stage-level log verification: no ERROR/CRITICAL/Traceback appended, and the
        # log actually grew (activity was recorded).
        newlog, log_errors = log_since(stage_off)
        # The temperature self-heal ("<id> rejects temperature — retried without it")
        # means the registry gate MISSED a model it knows about — e.g. a lookup by
        # one exact profile id. A call that only passed via the self-heal is a FAIL.
        healed_ids = set(re.findall(r"(\S+) rejects temperature", newlog))
        for row in rows:
            row["log_clean"] = not log_errors
            if row["status"] == "PASS" and row["model_id"] in healed_ids:
                row["status"] = "FAIL"
                row["detail"] += " | temperature gate missed (server self-healed)"
            elif log_errors and row["status"] == "PASS":
                row["status"] = "PASS*"  # invoke ok, but stage log had errors (see below)
        record_stage(name, rows, log_errors, len(newlog))

    def record_stage(name, rows, log_errors=(), log_bytes=0):
        passed = sum(1 for r in rows if r["status"].startswith("PASS"))
        failed = sum(1 for r in rows if r["status"] == "FAIL")
        other = {st: sum(1 for r in rows if r["status"] == st) for st in ("WARN", "SKIP")}
        extra = "".join(f", {n} {st}" for st, n in other.items() if n)
        print(f"--- {name}: {passed} PASS, {failed} FAIL{extra} | log grew {log_bytes} bytes, "
              f"{len(log_errors)} error line(s) ---", flush=True)
        for ln in list(log_errors)[:20]:
            print(f"    LOG-ERROR: {ln}", flush=True)
        # Per route kind (pinned / global / each geo / in-region / …/auto) — proof
        # that every residency AWS offers was exercised, not just the pin.
        kinds: dict = {}
        for r in rows:
            k = kinds.setdefault(r.get("route") or "-", {"PASS": 0, "FAIL": 0, "WARN": 0, "SKIP": 0})
            k["PASS" if r["status"].startswith("PASS") else r["status"]] += 1
        if len(kinds) > 1:
            for k, c in sorted(kinds.items()):
                print(f"    {k:22s} " + "  ".join(f"{st} {n}" for st, n in c.items() if n), flush=True)
        results["stages"][name] = {"passed": passed, "failed": failed, **{s.lower(): n for s, n in other.items()},
                                   "by_route": kinds, "log_errors": list(log_errors),
                                   "log_bytes": log_bytes, "rows": rows}

    scope_note = "native+custom" if args.include_custom else "native only"
    srv = server_settings()
    print(f"Model scope: {scope_note} | residency: {srv['residency'] or 'none (global. preferred)'} "
          f"| geos offered: {', '.join(sorted({g for p in _profile_map().values() for g in p})) or 'none'}")

    if "registry" in stages:
        print("\n=== STAGE REGISTRY — pins, categories, served ids, Region pickers, price order ===")
        record_stage("registry", registry_checks(base, reg))

    # Cross-platform concurrency preflight: measure the server's real parallelism and,
    # if it serializes, RECOMMEND a multi-worker restart (portable) rather than forcing one.
    # Probe = the app's own Fast LLM (whatever Region/profile it is pinned to).
    if not args.skip_server_check and args.concurrency > 1 and set(stages) - {"registry"}:
        pool = select_chat_models(reg, 1, 1, args.include_custom)
        fast = ((reg.get("categories") or {}).get("fast_llm") or {})
        probe = next((m for m in pool if _strip_geo(m["model_id"]) == _strip_geo(fast.get("current", ""))),
                     None) or next((m for m in pool if "converse" in (m.get("invoke_api") or "")),
                                   pool[0] if pool else None)
        if probe:
            preg = probe.get("region") or (probe.get("available_regions") or [""])[0]
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
        chat_models = select_chat_models(reg, args.tiers, args.versions, args.include_custom)
        try:
            served = {m.get("key"): m for m in get_json(base, "/api/chat/models").get("models", [])}
        except Exception:
            served = {}
        jobs = []
        for m in chat_models:
            routes = chat_routes(m, args.region_scope, served.get(m["key"]), srv["home_models"])
            if args.geo_scope == "pinned":
                routes = [r for r in routes if r["kind"].startswith(("pinned", "check:"))]
            jobs += [(m, r) for r in routes]
        run_stage("chat", chat_models, lambda m, rt: run_chat_route(base, reg, m, rt, args.max_tokens),
                  jobs=jobs)
    if {"excluded", "llm"} & set(stages):
        _backend()  # in-process: the server's own modules, imported on this thread
        sel = select_chat_models(reg, args.tiers, args.versions, args.include_custom)
    if "excluded" in stages:
        run_stage("excluded", sel, run_excluded,
                  jobs=[(m, rt) for m in sel for rt in excluded_routes(m)])
    if "llm" in stages:
        run_stage("llm", sel, lambda m, job: run_llm(m, job, args.max_tokens), jobs=llm_jobs(reg, sel))
    if "image" in stages:
        run_stage("image", select_image_models(reg, args.include_custom),
                  lambda m, r: run_image(base, m, r))
    if "video" in stages:
        run_stage("video", select_video_models(reg, args.include_custom),
                  lambda m, r: run_video(base, m, r, args.video_timeout))
    if "collections" in stages:
        # One image model is enough to smoke the whole Collections flow (SPEC §18);
        # capped to the first enabled image model to bound cost. A 2nd enabled model
        # (when present) is passed through so run_collection can also verify the
        # multi-model set path (every selected model must render) — SPEC §18.4.
        _coll_models = select_image_models(reg, args.include_custom)
        run_stage("collections", _coll_models[:1],
                  lambda m, r: run_collection(base, m, r, extra_models=_coll_models[1:2]))

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
            if row["status"] in ("FAIL", "WARN"):
                print(f"     {row['status']} {row['model']} [{row.get('route', '')}] "
                      f"{row.get('model_id') or ''} @ {row['region']}: {row['detail']}")
        for ln in le[:20]:
            print(f"     LOG-ERROR: {ln}")
    print(f"  TOTAL : {total_p} PASS / {total_f} FAIL")
    print(f"  report → {args.report}")
    sys.exit(1 if total_f else 0)


if __name__ == "__main__":
    main()
