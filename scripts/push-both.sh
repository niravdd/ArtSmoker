#!/usr/bin/env bash
#
# push-both.sh — keep GitHub AND GitLab in sync for BOTH `main` and the tracked
# feature branch(es), in one step.
#
#   origin  → GitHub  (github.com/niravdd/ArtSmoker)      : full commit history, source of truth
#   aws     → GitLab  (ssh.gitlab.aws.dev:niravdd/ArtSmoker): internal mirror, fresh-base line
#
# Why the mirror is indirect: the GitLab repo was seeded from an ORPHAN snapshot of
# the tree (to avoid mirroring ~1.24 GiB of historical binaries), so its history is
# a separate line with no common ancestor to GitHub's — a plain `git push aws <b>`
# can't fast-forward. Instead we keep orphan-rooted `gitlab-*` branches and
# cherry-pick each new commit onto them (every mirror point is tree-identical, so
# the cherry-picks never conflict), then push those to GitLab. GitLab thus receives
# the SAME content + commit messages as GitHub, on its own linear history.
#
#   • main             → append-only onto `gitlab-main`, tracked by a marker ref.
#   • <feature branch> → a derived `gitlab-<branch>` line ROOTED at the GitLab mirror
#                        of the branch's merge-base with main, with the branch's own
#                        commits cherry-picked on top, then force-pushed (it's a
#                        recomputed mirror of a moving branch). Rooting at the
#                        merge-base mirror — not gitlab-main's tip — keeps the trees
#                        identical to what each commit was authored against, so the
#                        cherry-picks stay conflict-free even when main has advanced
#                        past the branch point.
#
# Runs from ANY branch (saves + restores your current branch). Requires a clean tree.
#
# Config: add branches to FEATURE_BRANCHES to mirror them too.
#
# Usage:  scripts/push-both.sh
#
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

MAIN=main
FEATURE_BRANCHES="feature-Collections"    # space-separated; branches also mirrored to both remotes
MARK=refs/mirror/gitlab-synced            # last main commit already mirrored to GitLab

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "push-both: working tree not clean — commit or stash first." >&2
  exit 1
fi

ORIG=$(git rev-parse --abbrev-ref HEAD)
restore() { git switch -q "$ORIG" 2>/dev/null || true; }
trap restore EXIT

# ── Preflight: the orphan-line branch + marker must exist ──────────────────────
if ! git rev-parse --verify -q gitlab-main >/dev/null; then
  echo "push-both: local 'gitlab-main' branch is missing." >&2
  echo "  It should point at the orphan snapshot that seeds GitLab's main." >&2
  echo "  Recreate the mirror with: scripts/setup-gitlab-mirror.sh" >&2
  exit 1
fi
if ! git rev-parse --verify -q "$MARK" >/dev/null; then
  echo "push-both: mirror marker '$MARK' is unset." >&2
  echo "  Set it to the main commit whose tree matches the GitLab snapshot, e.g.:" >&2
  echo "    git update-ref $MARK <that-commit-sha>" >&2
  exit 1
fi

# ── 1) main — GitHub (source of truth), then append onto gitlab-main ───────────
echo "push-both: main → origin (GitHub)…"
git push origin "$MAIN"

base=$(git rev-parse "$MARK")
count=$(git rev-list --count "${base}..${MAIN}")
if [ "$count" -gt 0 ]; then
  echo "push-both: mirroring $count new main commit(s) onto gitlab-main…"
  git switch -q gitlab-main
  if ! git cherry-pick -x "${base}..${MAIN}"; then
    echo "push-both: main cherry-pick hit a conflict. Resolve it, 'git cherry-pick --continue'," >&2
    echo "  then re-run this script." >&2
    exit 1
  fi
  git switch -q "$MAIN"
fi
echo "push-both: gitlab-main → aws (GitLab main)…"
git push aws gitlab-main:"$MAIN"
git update-ref "$MARK" "$MAIN"
echo "push-both: main in sync at $(git rev-parse --short "$MAIN")."

# ── 2) feature branches — GitHub, then a derived gitlab-<branch> mirror line ────
for B in $FEATURE_BRANCHES; do
  if ! git rev-parse --verify -q "$B" >/dev/null; then
    echo "push-both: no local '$B' branch — skipping."
    continue
  fi
  echo "push-both: $B → origin (GitHub)…"
  git push origin "$B"

  mb=$(git merge-base "$MAIN" "$B")
  mbtree=$(git rev-parse "${mb}^{tree}")
  # The GitLab mirror of the merge-base is the gitlab-main-line commit whose TREE
  # equals the merge-base's tree (mirror points are tree-identical by construction).
  root=""
  for c in $(git rev-list gitlab-main); do
    if [ "$(git rev-parse "${c}^{tree}")" = "$mbtree" ]; then root=$c; break; fi
  done
  if [ -z "$root" ]; then
    echo "push-both: couldn't locate the GitLab mirror of $B's merge-base ($(git rev-parse --short "$mb")) on gitlab-main." >&2
    echo "  Sync main first (this script does), or the branch predates the snapshot base — skipping $B." >&2
    continue
  fi

  gl="gitlab-$B"
  n=$(git rev-list --count "${mb}..${B}")
  echo "push-both: building $gl at merge-base mirror $(git rev-parse --short "$root") + $n commit(s)…"
  git switch -q -C "$gl" "$root"
  if [ "$n" -gt 0 ]; then
    if ! git cherry-pick -x "${mb}..${B}"; then
      echo "push-both: $B cherry-pick hit a conflict — aborting just this branch." >&2
      git cherry-pick --abort || true
      git switch -q "$MAIN"
      continue
    fi
  fi
  git switch -q "$MAIN"

  # Force (the mirror line is recomputed each run); create on first push.
  if git ls-remote --exit-code --heads aws "$B" >/dev/null 2>&1; then
    echo "push-both: $gl → aws ($B, force)…"
    git push --force aws "$gl:$B"
  else
    echo "push-both: $gl → aws ($B, create)…"
    git push aws "$gl:$B"
  fi
  echo "push-both: $B in sync at $(git rev-parse --short "$B")."
done

echo "push-both: done — GitHub and GitLab synced for main + [$FEATURE_BRANCHES]."
