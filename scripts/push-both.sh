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
#   • main             → append-only onto `gitlab-main`, cherry-picked per commit
#                        (linear, curated history), tracked by a marker ref — GitLab
#                        gets the SAME content AND commit messages as GitHub.
#   • <feature branch> → a CONTENT SNAPSHOT: one `gitlab-<branch>` commit whose tree
#                        == the branch tip's tree, parented on gitlab-main, force-pushed
#                        each run. A feature branch may contain merges (e.g. `main`
#                        merged in), which makes a per-commit replay onto the orphan
#                        line fragile/conflict-prone; snapshotting the tip tree is
#                        DAG-proof and never conflicts. The branch's full per-commit
#                        history stays on GitHub (the source of truth); GitLab holds
#                        byte-identical current content for backup/visibility.
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
FEATURE_BRANCHES=""    # space-separated feature branches to ALSO mirror to both remotes (empty = main only)
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

# ── 2) feature branches — GitHub, then a CONTENT-SNAPSHOT mirror on GitLab ──────
# A feature branch can contain merges (e.g. `main` merged in to pick up a rename),
# so a per-commit cherry-pick replay onto the orphan line is fragile / conflict-prone.
# Instead we mirror the TIP CONTENT: one `gitlab-<branch>` commit whose tree == the
# branch tip's tree, parented on gitlab-main. GitLab thus holds byte-identical content
# to GitHub; the full per-commit history stays on GitHub (the source of truth). This
# is DAG-proof (any merges/rebases) and never conflicts. The line is recomputed +
# force-pushed each run, so it always reflects the branch's current tip.
for B in $FEATURE_BRANCHES; do
  if ! git rev-parse --verify -q "$B" >/dev/null; then
    echo "push-both: no local '$B' branch — skipping."
    continue
  fi
  echo "push-both: $B → origin (GitHub)…"
  git push origin "$B"

  gl="gitlab-$B"
  tip=$(git rev-parse --short "$B")
  n=$(git rev-list --count "${MAIN}..${B}")
  tree=$(git rev-parse "${B}^{tree}")
  msg="Mirror of $B @ $tip — GitLab content snapshot ($n commits; full history on GitHub origin/$B)"
  newc=$(git commit-tree "$tree" -p gitlab-main -m "$msg")
  git update-ref "refs/heads/$gl" "$newc"
  echo "push-both: built $gl ($tip content, $n commits) on the GitLab line…"

  # Force (recomputed each run); create on first push.
  if git ls-remote --exit-code --heads aws "$B" >/dev/null 2>&1; then
    echo "push-both: $gl → aws ($B, force)…"
    git push --force aws "$gl:$B"
  else
    echo "push-both: $gl → aws ($B, create)…"
    git push aws "$gl:$B"
  fi
  echo "push-both: $B mirrored to GitLab at $tip."
done

echo "push-both: done — GitHub and GitLab synced for main + [$FEATURE_BRANCHES]."
