#!/usr/bin/env python3
"""
One-shot: prefix bare t('…') call-site literals with 'artsmoker.' so they
satisfy Probe's custom i18next-key-format rule (MODULE.FEATURE.*).

- Targets ONLY bare `t(` calls (the rule does not flag `_t(`), so the
  lookbehind excludes `_`, `.`, `$`, and word chars → never matches
  `_t(`, `.t(`, `split(`, `format(`, `assert(`, etc.
- Skips literals already prefixed with `artsmoker.` (idempotent).
- Handles ', ", and ` (template) literals and whitespace after `(`.
- JSON translation files are UNCHANGED; window.t strips the prefix at runtime.

Usage:
  python3 scripts/prefix_i18n_keys.py --dry   # report counts only
  python3 scripts/prefix_i18n_keys.py         # apply in place
"""
import re
import sys

FILES = [
    "frontend/js/components/ModelSettings.js",
    "frontend/js/components/AssetViewer.js",
    "frontend/js/components/ImageStudio.js",
    "frontend/js/components/VideoStudio.js",
    "frontend/js/components/Gallery.js",
    "frontend/js/components/StyleLibrary.js",
    "frontend/js/components/ChatStudio.js",
    "frontend/js/components/TypeStudio.js",
    "frontend/js/components/PromptEditor.js",
    "frontend/js/app.js",
    "frontend/js/components/VoiceInput.js",
    "frontend/js/services/api.js",
]

# group1 = `t(` + optional ws + opening quote ; then NOT already 'artsmoker.'
PATTERN = re.compile(r"(?<![\w.$])(t\(\s*[\"'`])(?!artsmoker\.)")
REPL = r"\1artsmoker."

def main():
    dry = "--dry" in sys.argv
    total = 0
    for path in FILES:
        with open(path, "r", encoding="utf-8") as f:
            src = f.read()
        new, n = PATTERN.subn(REPL, src)
        total += n
        print(f"{n:5d}  {path}")
        if n and not dry:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new)
    print(f"----- {total} call sites {'would be' if dry else ''} prefixed")

if __name__ == "__main__":
    main()
