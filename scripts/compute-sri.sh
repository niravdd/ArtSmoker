#!/usr/bin/env bash
# compute-sri.sh — print the Subresource Integrity (SRI) attribute for a CDN URL.
#
# SRI pins a script/style to EXACT bytes: a new version has a new hash, so
# upgrading a pinned+SRI'd CDN asset in frontend/index.html is a 2-step edit —
# (1) bump the version in the URL, (2) replace its integrity="..." with the
# output of this script. There is intentionally no "always latest": that is the
# supply-chain protection SRI buys (the CDN can't silently swap the file).
#
# Usage:
#   scripts/compute-sri.sh <url> [<url> ...]
# Example:
#   scripts/compute-sri.sh https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js
set -euo pipefail
for url in "$@"; do
  hash=$(curl -fsSL "$url" | openssl dgst -sha384 -binary | openssl base64 -A)
  echo "integrity=\"sha384-${hash}\" crossorigin=\"anonymous\"   # ${url}"
done
