#!/bin/sh
# The only sanctioned way for a loop to open a pull request. Runs the
# repository gate first, then hands everything through to gh pr create.
# Pull-request creation does not pass through git hooks, so this wrapper is
# the gate for the PR itself; the pre-push hook covers the branch push.
#
# Usage: shoggoth-pr.sh --repo <owner/name> [gh pr create args...]
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)

repo=""
prev=""
for arg in "$@"; do
    if [ "$prev" = "--repo" ]; then repo="$arg"; fi
    prev="$arg"
done
if [ -z "$repo" ]; then
    echo "shoggoth-pr: --repo <owner/name> is required" >&2
    exit 1
fi

"$ROOT/bin/verify-gate.py"
"$ROOT/bin/repository-gate.py" "$repo"
exec gh pr create "$@"
