"""Official Amazon Bedrock pricing sources (SPEC §14).

Every price ArtSmoker records comes from one of three official AWS sources —
never a hardcoded table:

  1. AWS Price List API (``pricing:GetProducts``) — service codes
     ``AmazonBedrock`` (first-party + open-weight models), ``AmazonBedrockService``
     (Claude global-profile rows) and ``AmazonBedrockFoundationModels``
     (Marketplace-sold models). The same data backs the public pricing page
     (aws.amazon.com/bedrock/pricing — it renders these rate codes).
  2. Agreement offers (``bedrock:ListFoundationModelAgreementOffers``) — the
     rate card AWS bills Marketplace-sold models by (Anthropic, OpenAI frontier,
     Stability, Luma, TwelveLabs, Cohere, Writer, AI21), keyed by EXACT model id.
  3. Bedrock User Guide model cards (docs.aws.amazon.com/bedrock/latest/userguide/
     model-card-*.html) — the In-Region / Geo / Global price tables and the
     long-context threshold ("272K input tokens or fewer") that no API exposes.

Token rate sets are flat dicts in USD per 1K tokens:
  input_per_1k / output_per_1k                — standard, in-Region or Geo profile
  global_input_per_1k / global_output_per_1k  — standard, Global profile
  long_[global_]input_per_1k / …output_per_1k — above the long-context threshold
  speech_input_per_1k / speech_output_per_1k  — speech tokens of a speech model
                                                (Nova Sonic bills speech and text apart)
Flex / Priority / Batch / Reserved / cache tiers are not recorded: ArtSmoker
never requests them, so they can't apply to its calls.
"""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser

logger = logging.getLogger(__name__)

PRICE_LIST_SERVICE_CODES = ("AmazonBedrock", "AmazonBedrockService", "AmazonBedrockFoundationModels")
MODEL_CARDS_BASE_URL = "https://docs.aws.amazon.com/bedrock/latest/userguide/"
_MP_SUFFIX = " (Amazon Bedrock Edition)"

# The ONLY words that may follow the direction phrase ('input tokens', 'Output
# TokenCount') of a standard on-demand token price: the profile scope, the
# long-context band and the explicit 'standard' tier. Anything else — batch,
# flex, priority, per-minute, custom-model, or a tier AWS adds tomorrow — is a
# tier ArtSmoker never requests, so it is rejected by default instead of being
# enumerated in a deny-list. ('units' is the Marketplace usagetype suffix:
# 'USE1-MP:USE1_InputTokenCount-Units'.)
_STANDARD_QUALIFIERS = frozenset({"standard", "global", "geo", "cross", "region",
                                  "long", "context", "ctx", "lctx", "units"})
_CACHE_WORDS = frozenset({"cache", "cached"})  # prompt-cache token kinds (never requested)
# Before the direction phrase, a dimension that carries no model name (a rate-
# card dimension, or a Marketplace 'MP:<code>_<dimension>' usagetype) may hold
# only the unit word ('MillionInputTokens'); 'MillionBatchInputTokens',
# 'CacheReadInputTokenCount', … are other tiers / token kinds.
_STEMLESS_PREFIX = frozenset({"million"})
_MP_DIM_RE = re.compile(r"MP:[A-Z0-9]+_(.+)$")


# ── Price List ────────────────────────────────────────────────────────────

_pl_lock = threading.Lock()
_pl_cache: dict = {"at": 0.0, "products": None}
_PL_TTL_S = 900


def price_list_products() -> list[dict]:
    """Every Bedrock product from the AWS Price List (all three service codes),
    parsed. One full, uncapped scan is shared by the image, video and LLM pricing
    passes of a Sync (cached 15 min) — the old per-pass scans were page-capped
    and silently missed the tail of the ~13K-row AmazonBedrock list. Raises on
    API failure so callers keep their previous pricing."""
    with _pl_lock:
        if _pl_cache["products"] is not None and time.time() - _pl_cache["at"] < _PL_TTL_S:
            return _pl_cache["products"]
        import boto3
        client = boto3.Session().client("pricing", region_name="us-east-1")  # Price List API: us-east-1 only
        products: list[dict] = []
        for code in PRICE_LIST_SERVICE_CODES:
            token = None
            while True:
                kwargs = {"ServiceCode": code, "MaxResults": 100}
                if token:
                    kwargs["NextToken"] = token
                resp = client.get_products(**kwargs)
                for raw in resp.get("PriceList", []):
                    pd = json.loads(raw)
                    pd["_service_code"] = code
                    products.append(pd)
                token = resp.get("NextToken")
                if not token:
                    break
        logger.info("Fetched %d Amazon Bedrock products from the AWS Price List", len(products))
        _pl_cache.update(at=time.time(), products=products)
        return products


def on_demand_dimensions(product: dict):
    """Yield (unit, usd_price) for a product's OnDemand price dimensions."""
    for term in (product.get("terms", {}).get("OnDemand", {}) or {}).values():
        for dim in (term.get("priceDimensions", {}) or {}).values():
            try:
                price = float(dim.get("pricePerUnit", {}).get("USD", "0") or 0)
            except (TypeError, ValueError):
                continue
            yield dim.get("unit", "") or "", price


def product_model_name(attrs: dict) -> str:
    """Display name of a Price List product: the ``model`` attribute, or the
    Marketplace ``servicename`` minus its " (Amazon Bedrock Edition)" suffix."""
    name = attrs.get("model", "") or ""
    if not name:
        svc = attrs.get("servicename", "") or ""
        name = svc[: -len(_MP_SUFFIX)] if svc.endswith(_MP_SUFFIX) else ""
    return name


def region_code_map(products: list[dict]) -> dict:
    """Billing region code → AWS Region ('USE1' → 'us-east-1'), learned from the
    Price List itself (usagetype prefix + regionCode) — no hardcoded table."""
    out: dict = {}
    for pd in products:
        attrs = pd.get("product", {}).get("attributes", {})
        m = re.match(r"^([A-Z]{2,4}\d)-", attrs.get("usagetype", "") or "")
        if m and attrs.get("regionCode"):
            out.setdefault(m.group(1), attrs["regionCode"])
    return out


def _dim_tokens(text: str) -> list:
    # 'CacheWrite1hInputTokenCount_LCtx' → cache write1h input token count lctx
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", text or "")
    return [t for t in re.split(r"[^a-z0-9]+", s.lower()) if t]


def _classify_token_dim(text: str, stemless: bool = False):
    """(direction, is_global, is_long) for a token-priced usage/dimension string,
    or None when it isn't a standard on-demand input/output token price.

    Grammar: <prefix> (input|output|response) token[s] [count] <qualifiers>,
    where every qualifier is in _STANDARD_QUALIFIERS. The prefix is the model
    name in a Price List usagetype (it must not end in a prompt-cache kind), and
    only _STEMLESS_PREFIX words in a ``stemless`` dimension."""
    toks = _dim_tokens(text)
    for i, t in enumerate(toks):
        if t in ("input", "output", "response") and i + 1 < len(toks) and toks[i + 1] in ("token", "tokens"):
            break
    else:
        return None
    if stemless and not set(toks[:i]) <= _STEMLESS_PREFIX:
        return None
    if _CACHE_WORDS & set(toks[:i]):
        return None
    tail = toks[i + 2:]
    if tail[:1] == ["count"]:
        tail = tail[1:]
    if not set(tail) <= _STANDARD_QUALIFIERS:
        return None
    direction = "input" if toks[i] == "input" else "output"
    return direction, "global" in tail, "lctx" in tail or "long" in tail


def _is_standard_on_demand(attrs: dict) -> bool:
    """A Price List row's own tier attributes, when present, must say standard
    on-demand ('standard' / 'global-standard'; 'On-demand Inference') — rows
    for any other tier are skipped whatever their usagetype says."""
    tier = (attrs.get("service_tier") or "").lower()
    if tier and tier.rsplit("-", 1)[-1] != "standard":
        return False
    feature = (attrs.get("feature") or "").lower()
    return not feature or "on-demand" in feature


def _rate_field(direction: str, is_global: bool, is_long: bool) -> str:
    return f"{'long_' if is_long else ''}{'global_' if is_global else ''}{direction}_per_1k"


def _put_rate(rates: dict, field: str, per_1k: float) -> None:
    # Several standard rows per field (e.g. bedrock-runtime and bedrock-mantle
    # surfaces of one model) — keep the lowest standard rate.
    per_1k = round(per_1k, 9)
    if field not in rates or per_1k < rates[field]:
        rates[field] = per_1k


_ID_STEM_RE = re.compile(r"^[A-Z]{2,4}\d-(?P<stem>.+?)(?:-mantle)?-(?:input|output)-tokens", re.I)
# A speech model's usagetypes name the token kind ('USE1-NovaSonic2.0-speech-
# input-tokens' / '…-text-input-tokens'); speech is billed at its own rate.
_SPEECH_DIM_RE = re.compile(r"-speech-(?:input|output)-tokens", re.I)


def price_list_token_rates(products: list[dict]) -> dict:
    """Standard token rates from the Price List.

    Returns {"by_name": {"<model name>|<region>": rates},
             "by_id":   {"<model id>|<region>": rates}}.
    ``by_id`` comes from usagetypes that embed the exact model id (e.g.
    'USE1-mistral.devstral-2-123b-mantle-input-tokens-standard') — an exact key
    that needs no name matching (AWS's display names drift, e.g. the Voxtral
    Small rows are named 'Voxtral-Mini-24B')."""
    by_name: dict = {}
    by_id: dict = {}
    for pd in products:
        attrs = pd.get("product", {}).get("attributes", {})
        usage = attrs.get("usagetype", "") or ""
        region = attrs.get("regionCode", "") or ""
        name = product_model_name(attrs)
        mp = _MP_DIM_RE.search(usage)
        cls = _classify_token_dim(mp.group(1), stemless=True) if mp else _classify_token_dim(usage)
        if not cls or not region or not _is_standard_on_demand(attrs):
            continue
        field = _rate_field(*cls)
        if _SPEECH_DIM_RE.search(usage):
            # Its own field — sharing input_per_1k let the cheaper text row win.
            field = f"speech_{field}"
        id_m = _ID_STEM_RE.match(usage)
        model_id = id_m.group("stem").lower() if id_m and "." in id_m.group("stem") else ""
        for unit, price in on_demand_dimensions(pd):
            u = unit.lower()
            if price <= 0 or u not in ("1k tokens", "1m tokens"):
                continue
            per_1k = price if u == "1k tokens" else price / 1000.0
            if name:
                _put_rate(by_name.setdefault(f"{name}|{region}", {}), field, per_1k)
            if model_id:
                _put_rate(by_id.setdefault(f"{model_id}|{region}", {}), field, per_1k)
    return {"by_name": by_name, "by_id": by_id}


# ── Agreement offers (Marketplace rate cards) ─────────────────────────────

def agreement_rate_cards(model_ids, region: str = "us-east-1", workers: int = 4) -> dict:
    """{model_id: [rateCard entries]} from bedrock:ListFoundationModelAgreementOffers.

    Only Marketplace-sold models have offers; first-party/open-weight models
    answer ValidationException and are simply absent (the Price List prices
    them). AccessDenied (role lacks the permission) is logged once and yields
    {} — callers then fall back to the other sources."""
    import boto3
    from botocore.config import Config
    client = boto3.Session().client(
        "bedrock", region_name=region,
        config=Config(retries={"mode": "adaptive", "max_attempts": 10}))
    denied = threading.Event()

    def _one(mid: str):
        if denied.is_set():
            return mid, None
        try:
            resp = client.list_foundation_model_agreement_offers(modelId=mid)
        except Exception as exc:
            code = getattr(exc, "response", {}).get("Error", {}).get("Code", "")
            if code in ("AccessDeniedException", "UnauthorizedOperation"):
                denied.set()
            return mid, None
        card = []
        for offer in resp.get("offers", []) or []:
            term = (offer.get("termDetails", {}) or {}).get("usageBasedPricingTerm", {}) or {}
            card.extend(term.get("rateCard", []) or [])
        return mid, card or None

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = dict(pool.map(_one, sorted({m for m in model_ids if m})))
    if denied.is_set():
        logger.warning("Agreement-offer pricing skipped: the role lacks "
                       "bedrock:ListFoundationModelAgreementOffers (see SPEC §7)")
    cards = {m: c for m, c in results.items() if c}
    logger.info("Fetched agreement-offer rate cards for %d model(s)", len(cards))
    return cards


def _dim_region(dimension: str, codes: dict):
    """Split a rate-card dimension into (region key, rest). The key is an AWS
    Region ('USE1_' prefix), 'geo:EU' for a geography-wide prefix, or '*' when
    the dimension carries no prefix (applies everywhere)."""
    m = re.match(r"^([A-Z][A-Z0-9]{1,4})_(.+)$", dimension)
    if m:
        pre, rest = m.groups()
        if pre in codes:
            return codes[pre], rest
        if pre.isalpha():
            return f"geo:{pre}", rest
    return "*", dimension


def parse_token_rate_card(card: list, codes: dict) -> dict:
    """Token + non-token unit prices from an agreement-offer rate card.

    Returns {"rates": {region_key: token rate set}, "units": {region_key: {unit: usd}}}.
    Token dimensions are priced per 1M tokens; search units and video seconds
    per unit. A model billed by a non-token INPUT unit (TwelveLabs Pegasus:
    video seconds) gets input_per_1k = 0 — its text input isn't charged."""
    rates: dict = {}
    units: dict = {}
    for entry in card or []:
        dim = entry.get("dimension", "") or ""
        try:
            price = float(entry.get("price", "0") or 0)
        except (TypeError, ValueError):
            continue
        region, rest = _dim_region(dim, codes)
        low = rest.lower()
        if low.startswith("search_unit"):
            units.setdefault(region, {})["search_unit"] = price
            continue
        if low.startswith("inputvideosecond"):
            key = "global_video_input_second" if "global" in low else "video_input_second"
            units.setdefault(region, {})[key] = price
            continue
        cls = _classify_token_dim(rest, stemless=True)
        if cls:
            _put_rate(rates.setdefault(region, {}), _rate_field(*cls), price / 1000.0)
    for region, u in units.items():
        rs = rates.get(region)
        if rs and "video_input_second" in u:
            for g in ("", "global_"):
                if f"{g}output_per_1k" in rs:
                    rs.setdefault(f"{g}input_per_1k", 0.0)
    return {"rates": rates, "units": units}


def parse_media_rate_card(card: list, codes: dict) -> list[dict]:
    """Per-output media prices from an agreement-offer rate card: one row per
    (region, dimension) — e.g. {'region': 'us-west-2', 'dimension':
    'CreatedImageRemoveBg', 'description': 'One image output from Remove
    Background', 'price': 0.07}. Token dimensions are excluded."""
    rows = []
    for entry in card or []:
        dim = entry.get("dimension", "") or ""
        region, rest = _dim_region(dim, codes)
        if {"token", "tokens"} & set(_dim_tokens(rest)) or region.startswith("geo:"):
            continue
        try:
            price = float(entry.get("price", "0") or 0)
        except (TypeError, ValueError):
            continue
        if price > 0:
            rows.append({"region": region, "dimension": rest,
                         "description": entry.get("description", "") or "", "price": price})
    return rows


# ── Model cards (Bedrock User Guide) ──────────────────────────────────────

class _CardParser(HTMLParser):
    """Collects every <table> on a model card with the heading/paragraph text
    that precedes it."""

    def __init__(self):
        super().__init__()
        self.tables: list[dict] = []
        self._table = None
        self._cell = None
        self._text = None
        self._last_heading = ""

    def handle_starttag(self, tag, attrs):
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6", "p") and self._table is None:
            self._text = ""
        elif tag == "table":
            self._table = {"heading": self._last_heading, "rows": []}
        elif tag == "tr" and self._table is not None:
            self._table["rows"].append([])
        elif tag in ("td", "th") and self._table is not None:
            self._cell = ""

    def handle_endtag(self, tag):
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6", "p") and self._text is not None:
            text = " ".join(self._text.split())
            if text:
                self._last_heading = text[:200]
            self._text = None
        elif tag in ("td", "th") and self._cell is not None and self._table is not None:
            if self._table["rows"]:
                self._table["rows"][-1].append(" ".join(self._cell.split()))
            self._cell = None
        elif tag == "table" and self._table is not None:
            self.tables.append(self._table)
            self._table = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell += data
        if self._text is not None:
            self._text += data


def _http_get(url: str, timeout: int = 15) -> str:
    import urllib.request
    if not url.startswith(MODEL_CARDS_BASE_URL):
        raise ValueError("model-card fetch restricted to the Bedrock User Guide")
    req = urllib.request.Request(url, headers={"User-Agent": "ArtSmoker-pricing-sync"})
    # nosemgrep -- fixed https docs.aws.amazon.com prefix, enforced above
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310 -- https AWS docs host, audited prefix
        return resp.read().decode("utf-8", "replace")


def parse_model_card(html: str) -> dict:
    """Pricing facts from one model card: {"model_ids": [...], "threshold_tokens":
    int|None, "rates": token rate set}. Prices on cards are per 1M tokens; the
    In-Region/Geo row is the regional rate, the Global row the global rate.
    GovCloud tables are ignored (ArtSmoker runs in commercial Regions)."""
    p = _CardParser()
    p.feed(html)
    model_ids: list[str] = []
    rates: dict = {}
    threshold = None
    for t in p.tables:
        rows = [r for r in t["rows"] if r]
        if not rows:
            continue
        header = [c.lower() for c in rows[0]]
        if "model id" in header:
            col = header.index("model id")
            model_ids += [r[col] for r in rows[1:] if len(r) > col and "." in r[col]]
            continue
        if not header or "inference option" not in header[0] or "output" not in header:
            continue
        heading = t["heading"].lower()
        if "govcloud" in heading:
            continue
        is_long = "long context" in heading
        m = re.search(r"(\d+(?:\.\d+)?)\s*([km])\s*input tokens", heading)
        if m and threshold is None:
            threshold = int(float(m.group(1)) * (1000 if m.group(2) == "k" else 1_000_000))
        try:
            i_col = next(i for i, h in enumerate(header) if h == "input")
            o_col = header.index("output")
        except (StopIteration, ValueError):
            continue
        for r in rows[1:]:
            if len(r) <= max(i_col, o_col):
                continue
            is_global = "global" in r[0].lower()
            for direction, col in (("input", i_col), ("output", o_col)):
                pm = re.search(r"\$\s*([\d,]+(?:\.\d+)?)", r[col])
                if pm:
                    _put_rate(rates, _rate_field(direction, is_global, is_long),
                              float(pm.group(1).replace(",", "")) / 1000.0)
    return {"model_ids": sorted(set(model_ids)), "threshold_tokens": threshold, "rates": rates}


def model_card_pricing(workers: int = 8) -> dict:
    """{base model id: {"threshold_tokens", "rates", "card"}} for every Bedrock
    model card that publishes a price table or a long-context threshold.
    Network failures yield {} (the API sources still price models)."""
    try:
        index = _http_get(MODEL_CARDS_BASE_URL + "model-cards.html")
    except Exception as exc:
        logger.warning("Model-card index fetch failed: %s", exc)
        return {}
    slugs = sorted(set(re.findall(r"model-card-[a-z0-9-]+\.html", index)))

    def _one(slug):
        try:
            return slug, parse_model_card(_http_get(MODEL_CARDS_BASE_URL + slug))
        except Exception:
            return slug, None

    out: dict = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for slug, card in pool.map(_one, slugs):
            if not card or not (card["rates"] or card["threshold_tokens"]):
                continue
            for mid in card["model_ids"]:
                entry = {"threshold_tokens": card["threshold_tokens"],
                         "rates": card["rates"], "card": slug[:-5]}
                out[mid] = entry
                # Cards may list only a profile id (global./us./…) — also key
                # the foundation id, which is what the pricing pass looks up.
                out.setdefault(base_model_id(mid.strip()), entry)
    logger.info("Model cards: %d of %d publish pricing details", len(out), len(slugs))
    return out


# ── Name matching (Price List display names ↔ registry models) ────────────

# Trailing tokens that don't distinguish a priced model: release dates (2507,
# 20250514), revisions (v1), and packaging words. Bare digits are NOT noise —
# they are version numbers. A word missing here only makes a match stricter
# (never a wrong price): the exact-id sources come first anyway.
_NOISE_RE = re.compile(r"^(v\d+|\d{4}|\d{6,8}|instruct|it|pt|dense|bf16|preview)$")


def strip_geo_prefix(model_id: str) -> str:
    from backend.services.model_registry import strip_geo_prefix as _strip
    return _strip(model_id)


def base_model_id(model_id: str) -> str:
    """Invoked id → the foundation-model id offers and model cards are keyed by
    (inference-profile geo prefix removed; 'us.anthropic.x' → 'anthropic.x')."""
    return strip_geo_prefix(model_id)


def norm_name(s: str) -> str:
    s = re.sub(r"(\d+)\.0(?!\d)", r"\1", (s or "").lower())  # 'Nova 2.0 Lite' == 'nova-2-lite'
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


# ── Vendors (learned from AWS data, never a fixed list) ───────────────────

def model_vendors(provider: str, model_id: str) -> set:
    """One model's own vendor names, normalised: its ``provider`` (from
    ListFoundationModels) and the provider segment of its id ('xai.grok-4' →
    'xai')."""
    out = {norm_name(provider)} if provider else set()
    base = base_model_id(model_id or "")
    seg = base.split(".", 1)[0] if "." in base else ""
    if seg and ":" not in seg:
        out.add(norm_name(seg))
    return {v for v in out if v}


def vendor_names(products=(), models=()) -> frozenset:
    """Every vendor name AWS uses ('openai', 'luma ai', 'z ai', …): the Price
    List ``provider`` attribute plus each model's own vendors (``models`` =
    registry entries). A vendor AWS adds tomorrow is picked up by the next
    Sync with no code change."""
    out = set()
    for pd in products or ():
        p = pd.get("product", {}).get("attributes", {}).get("provider")
        if p:
            out.add(norm_name(p))
    for cfg in models or ():
        if isinstance(cfg, dict):
            out |= model_vendors(cfg.get("provider") or "", cfg.get("model_id") or "")
    return frozenset(v for v in out if v)


def _same_vendor(key: str, own_keys: set) -> bool:
    # Space-insensitive, prefix-tolerant: 'moonshotai' == 'moonshot ai',
    # 'mistralai' ~ 'mistral', 'minimaxai' ~ 'minimax'.
    return any(key == k or key.startswith(k) or k.startswith(key) for k in own_keys)


def _strip_vendor(toks: tuple, vendor: tuple):
    """``toks`` minus a leading ``vendor`` phrase, when at least two tokens
    remain ('openai gpt 6 astra' → 'gpt 6 astra'); else None."""
    n = len(vendor)
    if n and len(toks) - n >= 2 and toks[:n] == vendor:
        return toks[n:]
    return None


def _name_variants(norm: str) -> set:
    toks = tuple(norm.split())
    out = {toks} if toks else set()
    # A price name with trailing noise ('Stable Diffusion 3.5 Large v1.0') also
    # matches its bare form.
    trimmed = toks
    while len(trimmed) > 1 and _NOISE_RE.match(trimmed[-1]):
        trimmed = trimmed[:-1]
    if trimmed != toks:
        out.add(trimmed)
    return out


class NameIndex:
    """Matches a registry model (label + model id) to Price List display names.

    AWS names models inconsistently — display names ('Claude Sonnet 4.5', 'Ray
    v2', 'Stable Diffusion 3.5 Large v1.0') or ids ('openai.gpt-5.4') — so a
    model is tried by its label and its id (geo prefix and ':N' revision
    stripped, with and without the provider segment). A price name matches when
    it EQUALS a candidate, or is a PREFIX of it followed only by non-version
    noise (dates, 'v1', 'instruct', …). Version digits must agree, so 'GLM 4.7'
    never takes 'Grok 4.7' and 'Claude Sonnet 4.5' never takes 'Claude Sonnet 4'.
    The most specific name wins.

    Vendor words: AWS sometimes prefixes the vendor ('OpenAI GPT-6 Astra') and
    sometimes not. ``vendors`` (see vendor_names) lets a price name also match
    without its leading vendor — but only for a model of THAT vendor, so 'Foo
    V3.1' can never take 'DeepSeek V3.1'. A model's own label/id likewise drops
    only its own vendor."""

    def __init__(self, names, vendors=()):
        phrases = sorted({tuple(v.split()) for v in vendors if v}, key=len, reverse=True)
        # (tokens, price name, vendor key the tokens dropped | None, published
        # as-is — False for a noise-trimmed variant)
        self._names = []
        for n in set(names):
            norm = norm_name(n)
            toks = tuple(norm.split())
            self._names.extend((v, n, None, v == toks) for v in _name_variants(norm))
            for vt in phrases:
                rest = _strip_vendor(toks, vt)
                if rest:
                    self._names.extend((v, n, "".join(vt), v == rest)
                                       for v in _name_variants(" ".join(rest)))
                    break

    def best(self, label: str, model_id: str, provider: str = ""):
        tied = self.matches(label, model_id, provider)
        return tied[0] if tied else None

    def matches(self, label: str, model_id: str, provider: str = "") -> list:
        """Every price name tied for the best match, sorted. AWS sometimes lists
        one model under two names ('Qwen3 Next 80B A3B' and 'qwen3-next-80b-a3b',
        each covering different Regions) — callers merge them rather than take
        whichever a set happened to yield first."""
        own = model_vendors(provider, model_id)
        own_keys = {v.replace(" ", "") for v in own}
        mid = re.sub(r"(:[0-9a-z]+)+$", "", strip_geo_prefix(model_id or ""))
        cands = set()
        for raw in (label or "", mid, mid.split(".", 1)[-1]):
            norm = norm_name(raw)
            cands |= _name_variants(norm) - {()}
            for v in own:
                rest = _strip_vendor(tuple(norm.split()), tuple(v.split()))
                if rest:
                    cands |= _name_variants(" ".join(rest)) - {()}
        best, best_score = set(), None
        for ptoks, name, vkey, as_is in self._names:
            if vkey and not _same_vendor(vkey, own_keys):
                continue
            for ctoks in cands:
                if ctoks[:len(ptoks)] == ptoks and all(_NOISE_RE.match(t) for t in ctoks[len(ptoks):]):
                    # Ordered; the more specific name first, then exact over prefix —
                    # 'Mistral Large 2407' beats 'Mistral Large' even though the id's
                    # noise-trimmed form ('mistral large') equals the shorter name.
                    score = (1, len(ptoks), len(ctoks) == len(ptoks))
                elif set(ptoks) == {t for t in ctoks if not _NOISE_RE.match(t)}:
                    score = (0, len(ptoks), True)  # same tokens, other order ('Ministral 8B 3.0')
                else:
                    continue
                # A name as AWS published it beats another name's noise-trimmed
                # form: 'Mistral Large' — not 'Mistral Large 2407' trimmed to it.
                score += (as_is,)
                if best_score is None or score > best_score:
                    best, best_score = {name}, score
                elif score == best_score:
                    best.add(name)
        return sorted(best)


# ── Rate selection (shared by the Sync and cost_tracker) ──────────────────

def rates_for_region(by_region: dict, region: str | None) -> dict | None:
    """The rate set that applies in ``region``: that Region's own rates, else
    its geography's ('geo:EU' for eu-*), else the region-agnostic '*' set."""
    if not by_region:
        return None
    if region and region in by_region:
        return by_region[region]
    if region:
        geo = region.split("-", 1)[0].upper()
        for key in (f"geo:{geo}", "geo:AP" if geo == "AP" else None, "geo:APAC" if geo == "AP" else None):
            if key and key in by_region:
                return by_region[key]
    return by_region.get("*")


def video_resolution_tier(resolution) -> str | None:
    """Price-List video tier for an output resolution: 'hd' (720p and above —
    the HD definition AWS's '…HDRes' rows use) or 'standard' (below, e.g. Luma
    Ray 540p). None when the resolution is unknown (→ the default HD rate)."""
    m = re.search(r"(\d{3,4})", str(resolution or ""))
    if not m:
        return None
    return "hd" if int(m.group(1)) >= 720 else "standard"


def pick_token_rate(rates: dict, invoked_model_id: str, input_tokens: int | None = None,
                    threshold_tokens: int | None = None):
    """(input_per_1k, output_per_1k) for one call. A ``global.`` profile bills
    the Global rate; in-Region and Geo profiles (us./eu./apac./…, bare ids,
    Mantle in-Region) bill the regional rate — each falls back to the other when
    a model publishes only one. Above a documented long-context threshold the
    long-context rate applies. None when the set has no complete pair."""
    if not rates:
        return None
    is_global = (invoked_model_id or "").startswith("global.")
    is_long = bool(threshold_tokens and input_tokens and input_tokens > threshold_tokens)
    for long_pre in (("long_", "") if is_long else ("",)):
        for glob_pre in (("global_", "") if is_global else ("", "global_")):
            i = rates.get(f"{long_pre}{glob_pre}input_per_1k")
            o = rates.get(f"{long_pre}{glob_pre}output_per_1k")
            if i is not None and o is not None:
                return i, o
    return None
