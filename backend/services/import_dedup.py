"""Smart deduplication and prioritization for style reference imports.

Conservative approach — only deduplicates when there's strong evidence
of duplicate patterns. Works with any asset type, not just standardized
isometric packs.

Detection patterns:
- Rotation variants: files with identical names except _N/_E/_S/_W suffix
  (only when ALL four rotations exist for the same base name)
- Animation frames: sequential numbered files with identical base name
  (only when there are 3+ sequential frames)
- Duplicate folders: same filenames appearing in multiple folders
"""

import logging
import re
from collections import Counter
from pathlib import Path

logger = logging.getLogger(__name__)

# Folder priority — higher number = higher priority for style analysis
# Only well-known folder names get non-default scores
_FOLDER_PRIORITY = {
    'samples': 10,
    'screenshots': 10,
    'preview': 10,
    'previews': 10,
    'rendered': 9,
    'output': 9,
    'final': 9,
    'sprites': 7,
    'icons': 7,
    'ui': 6,
}


def _get_folder_priority(file_path: Path, base_dir: Path) -> int:
    """Score a file's folder for priority. Higher = more valuable."""
    rel = file_path.relative_to(base_dir)
    score = 5  # default — treat everything equally unless we recognize the folder
    for part in rel.parts[:-1]:
        part_lower = part.lower()
        for key, priority in _FOLDER_PRIORITY.items():
            if key in part_lower:
                score = max(score, priority)
    return score


def _detect_rotation_groups(image_files: list[Path]) -> dict[str, set[str]]:
    """Detect files that are rotation variants of the same object.

    Only marks files as rotation variants when the SAME base name has
    files ending in _N, _E, _S, _W (at least 3 of the 4 must exist).
    This avoids false positives like 'character_new.png' or 'logo_s.png'.
    """
    # Group by (parent_dir, base_name_without_rotation_suffix)
    potential: dict[tuple[Path, str], dict[str, Path]] = {}

    for f in image_files:
        stem = f.stem
        # Check if filename ends with exactly _N, _E, _S, or _W
        match = re.match(r'^(.+)_([NESW])$', stem, re.IGNORECASE)
        if match:
            base = match.group(1)
            direction = match.group(2).upper()
            key = (f.parent, base)
            potential.setdefault(key, {})[direction] = f

    # Only treat as rotation group if 3+ of the 4 directions exist
    rotation_files: dict[str, set[str]] = {}  # canonical_key → set of filenames to skip
    for (parent, base), directions in potential.items():
        if len(directions) >= 3:
            # Keep S (front-facing) if available, else E, else any
            keep = directions.get('S') or directions.get('E') or next(iter(directions.values()))
            for direction, fpath in directions.items():
                if fpath != keep:
                    rotation_files.setdefault(base, set()).add(fpath.name)

    return rotation_files


def _detect_animation_groups(image_files: list[Path]) -> set[str]:
    """Detect animation frame sequences and return filenames to skip.

    Only marks files as animation frames when there are 3+ sequential
    numbered files with the same base name (e.g. Idle0, Idle1, Idle2...).
    Keeps frame 0.
    """
    # Group by (parent_dir, base_name_without_trailing_digits)
    potential: dict[tuple[Path, str], list[tuple[int, Path]]] = {}

    for f in image_files:
        stem = f.stem
        # Match trailing digits preceded by a non-digit
        match = re.match(r'^(.+?)(\d+)$', stem)
        if match and match.group(1):  # must have a non-empty base
            base = match.group(1)
            frame_num = int(match.group(2))
            key = (f.parent, base)
            potential.setdefault(key, []).append((frame_num, f))

    skip_files: set[str] = set()
    for (parent, base), frames in potential.items():
        if len(frames) >= 3:
            # This looks like an animation sequence — keep the lowest frame number
            frames.sort(key=lambda x: x[0])
            for frame_num, fpath in frames[1:]:  # skip all except first
                skip_files.add(fpath.name)

    return skip_files


def _detect_cross_folder_duplicates(image_files: list[Path], base_dir: Path) -> set[str]:
    """Detect the same filename appearing in multiple folders.

    When the same filename exists in multiple folders, keep the one
    from the highest-priority folder and skip the rest.
    """
    # Group by filename
    by_name: dict[str, list[Path]] = {}
    for f in image_files:
        by_name.setdefault(f.name, []).append(f)

    skip_paths: set[str] = set()
    for name, paths in by_name.items():
        if len(paths) > 1:
            # Keep the one with highest folder priority
            scored = [((_get_folder_priority(p, base_dir), p)) for p in paths]
            scored.sort(key=lambda x: x[0], reverse=True)
            for _, path in scored[1:]:  # skip all except highest priority
                skip_paths.add(str(path))

    return skip_paths


def deduplicate_imports(
    image_files: list[Path],
    base_dir: Path,
    max_count: int = 100,
) -> list[Path]:
    """Deduplicate and prioritize image files for style import.

    Always runs deduplication regardless of file count — even small sets
    can have rotation variants or cross-folder duplicates.

    Conservative approach — only removes files when there's strong
    evidence they're duplicates (rotation variants with 3+ directions,
    animation sequences with 3+ frames, same filename in multiple folders).

    Files that don't match any pattern are kept as-is.

    Returns a prioritized list of unique files, up to max_count.
    """
    # Always dedup — even small sets can have redundancy
    rotation_skips = _detect_rotation_groups(image_files)
    rotation_skip_names = set()
    for skip_set in rotation_skips.values():
        rotation_skip_names.update(skip_set)

    anim_skips = _detect_animation_groups(image_files)
    cross_folder_skips = _detect_cross_folder_duplicates(image_files, base_dir)

    # Phase 2: Filter
    kept = []
    skipped_rotation = 0
    skipped_anim = 0
    skipped_cross = 0

    for f in image_files:
        if f.name in rotation_skip_names:
            skipped_rotation += 1
            continue
        if f.name in anim_skips:
            skipped_anim += 1
            continue
        if str(f) in cross_folder_skips:
            skipped_cross += 1
            continue
        kept.append(f)

    # Phase 3: Sort by folder priority (higher first), then alphabetically
    kept.sort(key=lambda f: (-_get_folder_priority(f, base_dir), f.name.lower()))

    result = kept[:max_count]

    logger.info(
        "Deduplication: %d files → %d kept (skipped: %d rotation, %d animation, %d cross-folder). Limit: %d.",
        len(image_files), len(result),
        skipped_rotation, skipped_anim, skipped_cross, max_count,
    )

    return result
