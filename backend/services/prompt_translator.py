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
SUPPORTED_LANGS = {"en", "ja", "zh", "ko", "fr", "es"}


def detect_language(text: str) -> str:
    """Detect the language of the input text.

    Uses Unicode range heuristics first (fast, no API call), then falls back
    to LLM detection for ambiguous cases.

    Returns a language code: en, ja, zh, ko, fr, es, or 'en' as fallback.
    """
    if not text or not text.strip():
        return "en"

    # Count characters in different Unicode ranges
    cjk_count = 0
    hiragana_katakana = 0
    hangul = 0
    latin = 0
    accented_latin = 0

    for ch in text:
        cp = ord(ch)
        if 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF:
            cjk_count += 1
        elif 0x3040 <= cp <= 0x30FF or 0x31F0 <= cp <= 0x31FF:
            hiragana_katakana += 1
        elif 0xAC00 <= cp <= 0xD7AF or 0x1100 <= cp <= 0x11FF:
            hangul += 1
        elif 0x0041 <= cp <= 0x007A:
            latin += 1
        elif 0x00C0 <= cp <= 0x024F:
            accented_latin += 1

    total = len(text.replace(" ", ""))
    if total == 0:
        return "en"

    # Japanese: hiragana/katakana present (unique to Japanese)
    if hiragana_katakana > 0:
        return "ja"

    # Korean: hangul present (unique to Korean)
    if hangul > 0:
        return "ko"

    # Chinese: CJK ideographs without hiragana/katakana/hangul
    if cjk_count > total * 0.2:
        return "zh"

    # French/Spanish: accented Latin characters + common patterns
    if accented_latin > 0 and latin > 0:
        lower = text.lower()
        # French indicators
        if any(w in lower for w in ["le ", "la ", "les ", "un ", "une ", "des ", "est ", "sont ", "dans ", "avec ", "pour "]):
            return "fr"
        # Spanish indicators
        if any(w in lower for w in ["el ", "la ", "los ", "las ", "un ", "una ", "es ", "son ", "en ", "con ", "para "]):
            return "es"
        # Could be either — use LLM for disambiguation
        return _llm_detect_language(text)

    # Mostly Latin with no accents → English
    if latin > total * 0.5:
        return "en"

    # Ambiguous — fall back to LLM
    return _llm_detect_language(text)


def _llm_detect_language(text: str) -> str:
    """Use LLM to detect language when heuristics are ambiguous."""
    try:
        result = invoke_llm(
            prompt=get_template('translate_detect_language').format(text=text[:200]),
            system="Reply with only the 2-letter language code. Nothing else.",
            max_tokens=5,
            temperature=0,
            complexity="fast",
        ).strip().lower()[:2]
        return result if result in SUPPORTED_LANGS else "en"
    except Exception:
        return "en"


def translate_to_english(text: str, source_lang: str = "") -> dict:
    """Translate text to English if it's not already in English.

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

    # Detect language if not provided
    lang = source_lang or detect_language(text)

    # Already English
    if lang == "en":
        return {"original": text, "translated": text, "source_lang": "en", "was_translated": False}

    # Translate via LLM
    try:
        translated = invoke_llm(
            prompt=get_template('translate_to_english').format(text=text, lang_name=_lang_name(lang)),
            system="You are a precise translator. Output only the English translation. No explanations, no notes, no quotes around the text.",
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
        "en": "English",
    }.get(code, code)
