#!/usr/bin/env bash
#
# push-both.sh — push `main` to BOTH remotes in one step.
#
#   origin  → GitHub  (github.com/niravdd/ArtSmoker)      : full commit history, source of truth
#   aws     → GitLab  (ssh.gitlab.aws.dev:niravdd/ArtSmoker): internal mirror, fresh-base line
#
# Why this exists: the GitLab repo was seeded from an ORPHAN snapshot of the
# current tree (to avoid mirroring the 1.24 GiB of historical binaries), so its
# history is a separate line with no common ancestor to GitHub's. A plain
# `git push aws main` therefore can't fast-forward. Instead we keep a local
# `gitlab-main` branch rooted at that orphan and cherry-pick each new `main`
# commit onto it — every mirror point has an identical tree, so the cherry-picks
# never conflict — then push `gitlab-main` to GitLab's `main`.
#
# Result: GitLab receives the SAME content and commit messages as GitHub, on its
# own linear history from the snapshot base.
#
# One-time setup (already done, but safe to re-run): see the marker/branch checks
# below — if either is missing the script prints the exact command to create it.
#
# Usage:  scripts/push-both.sh            # push main to GitHub + GitLab
#
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$BRANCH" != "main" ]; then
  echo "push-both: you're on '$BRANCH' — switch to 'main' first." >&2
  exit 1
fi
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "push-both: working tree not clean — commit or stash first." >&2
  exit 1
fi

MARK=refs/mirror/gitlab-synced   # last main commit already mirrored to GitLab

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

# 1) GitHub — full history, source of truth.
echo "push-both: pushing main → origin (GitHub)…"
git push origin main

# 2) GitLab — replay any new commits onto the orphan-based line, then push.
base=$(git rev-parse "$MARK")
mapfile -t NEW < <(git rev-list --reverse "${base}..main") || true
if [ "${#NEW[@]}" -gt 0 ]; then
  echo "push-both: mirroring ${#NEW[@]} new commit(s) onto gitlab-main…"
  git switch -q gitlab-main
  if ! git cherry-pick -x "${NEW[@]}"; then
    echo "push-both: cherry-pick hit a conflict. Resolve it, run 'git cherry-pick --continue'," >&2
    echo "  then 'git switch main' and re-run this script." >&2
    exit 1
  fi
  git switch -q main
fi
echo "push-both: pushing gitlab-main → aws (GitLab main)…"
git push aws gitlab-main:main
git update-ref "$MARK" main
echo "push-both: done — GitHub and GitLab are in sync at $(git rev-parse --short main)."
