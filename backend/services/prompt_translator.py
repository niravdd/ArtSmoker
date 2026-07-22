"""Prompt Translator — detects non-English input and translates to English.

Used by the generation pipeline to ensure all prompts are in English
before being sent to image/video models, which perform best with English.

The original prompt and detected language are preserved in metadata.
Translation uses the fast LLM (Claude Sonnet) for speed and low cost (~$0.001/call).
"""

import logging
import re
from functools import lru_cache

from backend.services.bedrock_client import invoke_llm
from backend.services.prompt_templates import get_template

logger = logging.getLogger(__name__)

# Supported languages for auto-detection
SUPPORTED_LANGS = {"en", "ja", "zh", "ko", "fr", "es", "de", "hi", "ru"}

# Common function words used to disambiguate accented/Latin-script languages.
# NOTE: these must be matched as WHOLE WORDS, never substrings — English prose is
# full of tokens that CONTAIN these ("un-DER-", "gro-UND-", "-LA-nd", "-EN-d",
# "-ES-cape"), so a naive `word in text` check misdetects English as de/fr/es.
# Use `_has_word()` (word-boundary aware), not the `in` operator, against these.
_FR_WORDS = {"le", "la", "les", "un", "une", "des", "est", "sont", "dans", "avec", "pour"}
_ES_WORDS = {"el", "la", "los", "las", "un", "una", "es", "son", "en", "con", "para"}
_DE_WORDS = {"der", "die", "das", "und", "ein", "eine", "ist", "mit", "für", "auf",
             "nicht", "sind", "wird", "auch", "dem", "den", "einen", "eines"}


# Latin-script languages where the UI-language hint can act as a tie-breaker.
_LATIN_HINT_WORDS = {"fr": _FR_WORDS, "es": _ES_WORDS, "de": _DE_WORDS}


def _has_word(text_lower: str, words: set) -> bool:
    """True if ``text_lower`` contains any of ``words`` as a WHOLE word.

    Splits on non-letter boundaries (Unicode-aware) so function words are matched
    as standalone tokens — 'under'/'around'/'ground'/'and'/'land' no longer match
    German 'der'/'und', and 'end'/'escape' no longer match Spanish 'en'/'es'.
    """
    tokens = set(re.findall(r"[^\W\d_]+", text_lower, flags=re.UNICODE))
    return not tokens.isdisjoint(words)


def detect_language(text: str, ui_lang: str = "") -> str:
    """Detect the language of the input text.

    Uses Unicode range heuristics first (fast, no API call), then falls back
    to LLM detection for ambiguous cases.

    ``ui_lang`` is the language the user has selected in the frontend. It is
    only a *soft prior*: unambiguous content signals (script, umlauts, matched
    function words) always win, so a user who deliberately writes in another
    language than their UI setting is still detected correctly. The hint only
    breaks genuine ties (e.g. accented text matching no word list, or accent-free
    Romance-language text), replacing a coin-flip LLM call or an 'en' default.

    Returns a language code: en, ja, zh, ko, fr, es, de, hi, ru, or 'en' as fallback.
    """
    if not text or not text.strip():
        return "en"

    # Normalize the hint — only trust it if it's a language we support.
    ui_lang = (ui_lang or "").strip().lower()[:2]
    if ui_lang not in SUPPORTED_LANGS:
        ui_lang = ""

    # The user is running the tool in English → the prompt IS English. Skip all
    # content-based detection: there is nothing to translate, and heuristic
    # detection on English prose only ever produces false positives (e.g. an
    # English caption misdetected as German because it contains 'under'/'and').
    # Detection/translation exists solely for users working in a NON-English UI.
    if ui_lang == "en":
        return "en"

    # Count characters in different Unicode ranges
    cjk_count = 0
    hiragana_katakana = 0
    hangul = 0
    latin = 0
    accented_latin = 0
    devanagari = 0
    cyrillic = 0

    for ch in text:
        cp = ord(ch)
        if 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF:
            cjk_count += 1
        elif 0x3040 <= cp <= 0x30FF or 0x31F0 <= cp <= 0x31FF:
            hiragana_katakana += 1
        elif 0xAC00 <= cp <= 0xD7AF or 0x1100 <= cp <= 0x11FF:
            hangul += 1
        elif 0x0900 <= cp <= 0x097F:
            devanagari += 1
        elif 0x0400 <= cp <= 0x04FF:
            cyrillic += 1
        elif 0x0041 <= cp <= 0x007A:
            latin += 1
        elif 0x00C0 <= cp <= 0x024F:
            accented_latin += 1

    total = len(text.replace(" ", ""))
    if total == 0:
        return "en"

    # Selected-language-first: the user is working in a specific non-English
    # language, so try to CONFIRM that language in the text before considering
    # any other. If its own signal is present, trust the selection immediately;
    # only when the selected language is NOT confidently found do we fall through
    # to the general cascade below. (English UI already returned "en" above.)
    if ui_lang and ui_lang != "en":
        lower = text.lower()
        confirmed = {
            "ja": hiragana_katakana > 0,
            "ko": hangul > 0,
            "hi": devanagari > 0,
            "ru": cyrillic > 0,
            "zh": cjk_count > total * 0.2,
            "de": ("ß" in text) or _has_word(lower, _DE_WORDS),
            "fr": _has_word(lower, _FR_WORDS),
            "es": _has_word(lower, _ES_WORDS),
        }.get(ui_lang, False)
        if confirmed:
            return ui_lang

    # Japanese: hiragana/katakana present (unique to Japanese)
    if hiragana_katakana > 0:
        return "ja"

    # Korean: hangul present (unique to Korean)
    if hangul > 0:
        return "ko"

    # Hindi: Devanagari script
    if devanagari > 0:
        return "hi"

    # Russian: Cyrillic script
    if cyrillic > 0:
        return "ru"

    # Chinese: CJK ideographs without hiragana/katakana/hangul
    if cjk_count > total * 0.2:
        return "zh"

    # French/Spanish/German: accented Latin characters + common patterns
    if accented_latin > 0 and latin > 0:
        lower = text.lower()
        # German indicators (umlauts ä/ö/ü/ß are a strong German signal)
        if "ß" in text or _has_word(lower, _DE_WORDS):
            return "de"
        # French indicators
        if _has_word(lower, _FR_WORDS):
            return "fr"
        # Spanish indicators
        if _has_word(lower, _ES_WORDS):
            return "es"
        # Accented but matched no word list — trust the UI hint if it's a
        # Latin-script language, else ask the LLM (cheaper than a wrong guess).
        if ui_lang in _LATIN_HINT_WORDS:
            return ui_lang
        return _llm_detect_language(text, ui_lang=ui_lang)

    # Mostly Latin with no accents. German prose frequently has no umlauts, and
    # French/Spanish can be accent-free too — check the UI-hinted language's own
    # function words first, then German's, else treat as English.
    if latin > total * 0.5:
        lower = text.lower()
        if ui_lang in _LATIN_HINT_WORDS and _has_word(lower, _LATIN_HINT_WORDS[ui_lang]):
            return ui_lang
        if _has_word(lower, _DE_WORDS):
            return "de"
        return "en"

    # Ambiguous — fall back to LLM
    return _llm_detect_language(text, ui_lang=ui_lang)


def _llm_detect_language(text: str, ui_lang: str = "") -> str:
    """Use LLM to detect language when heuristics are ambiguous.

    Falls back to ``ui_lang`` (the frontend selection) when the LLM returns an
    unsupported/empty code or errors, rather than blindly defaulting to English.
    """
    fallback = ui_lang if ui_lang in SUPPORTED_LANGS else "en"
    try:
        from backend.services.prompt_templates import get_system_prompt
        result = invoke_llm(
            prompt=get_template('translate_detect_language').format(text=text[:200]),
            system=get_system_prompt('translate_detect_language'),
            max_tokens=5,
            temperature=0,
            complexity="fast",
        ).strip().lower()[:2]
        return result if result in SUPPORTED_LANGS else fallback
    except Exception:
        return fallback


def translate_to_english(text: str, source_lang: str = "", ui_lang: str = "") -> dict:
    """Translate text to English if it's not already in English.

    ``source_lang``, when given, is an authoritative override and skips detection.
    ``ui_lang`` is a soft hint (the frontend language selection) passed to
    detection as a tie-breaker only — content signals still win.

    Returns:
        {
            "original": str,          # Original text
            "translated": str,        # English translation (or original if already English)
            "source_lang": str,       # Detected or provided language code
            "was_translated": bool,   # True if translation was performed
        }
    """
    if not text or not text.strip():
        return {"original": text, "translated": text, "source_lang": "en", "was_translated": False}

    # Detect language if not explicitly provided (ui_lang is only a soft prior).
    lang = source_lang or detect_language(text, ui_lang=ui_lang)

    # Already English
    if lang == "en":
        return {"original": text, "translated": text, "source_lang": "en", "was_translated": False}

    # Translate via LLM
    try:
        from backend.services.prompt_templates import get_system_prompt
        translated = invoke_llm(
            prompt=get_template('translate_to_english').format(text=text, lang_name=_lang_name(lang)),
            system=get_system_prompt('translate_to_english'),
            max_tokens=min(len(text) * 3, 4000),
            temperature=0.1,
            complexity="fast",
        ).strip()

        logger.info("Translated %s prompt (%d chars) to English (%d chars)", lang, len(text), len(translated))
        return {"original": text, "translated": translated, "source_lang": lang, "was_translated": True}

    except Exception as exc:
        logger.warning("Translation failed for %s text: %s", lang, exc)
        return {"original": text, "translated": text, "source_lang": lang, "was_translated": False}


def _lang_name(code: str) -> str:
    """Get human-readable language name from code."""
    return {
        "ja": "Japanese",
        "zh": "Chinese",
        "ko": "Korean",
        "fr": "French",
        "es": "Spanish",
        "de": "German",
        "hi": "Hindi",
        "ru": "Russian",
        "en": "English",
    }.get(code, code)
