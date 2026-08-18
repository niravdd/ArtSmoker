#!/usr/bin/env python3
"""
Namespace i18n call-site keys to satisfy Probe's custom i18next-key-format rule,
which requires MODULE.FEATURE.* where the FEATURE (2nd) segment is a clean word
with NO underscore (the trailing "*" wildcard may contain underscores/dots).

Our module names contain underscores (model_settings, image_studio, …), so a bare
"artsmoker." prefix fails — the underscore-module becomes FEATURE. Instead we use a
TWO-segment constant prefix "artsmoker.ui." → FEATURE is the clean word "ui" and the
real key lands in the wildcard. `window.t` strips "artsmoker.ui." before lookup, so
the translation JSON is UNCHANGED and runtime is identical.

This inserts the "ui." segment into keys already prefixed with "artsmoker." (an
inline edit → no line-number shift). Idempotent (skips "artsmoker.ui." already).

Usage:
  python3 scripts/prefix_i18n_keys.py --dry
  python3 scripts/prefix_i18n_keys.py
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

# A quote immediately followed by `artsmoker.` (but NOT already `artsmoker.ui.`)
# — this is a t() call-site key literal. Insert the `ui.` FEATURE segment.
PATTERN = re.compile(r"([\"'`])artsmoker\.(?!ui\.)")
REPL = r"\1artsmoker.ui."

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
    print(f"----- {total} keys {'would be' if dry else ''} re-namespaced to artsmoker.ui.")

if __name__ == "__main__":
    main()
