#!/bin/sh
# The only sanctioned way for a loop to open a pull request. Runs the
# integrity, authorship, and repository gates before handing the request to gh.
# Pull-request creation does not pass through git hooks, so this wrapper is
# the gate for the PR itself; the pre-push hook covers the branch push.
#
# Usage: shoggoth-pr.sh --repo <owner/name> --base <base> --head <head> [args...]
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)

repo=""
base=""
head=""
prev=""
for arg in "$@"; do
    if [ "$prev" = "--repo" ]; then repo="$arg"; fi
    if [ "$prev" = "--base" ]; then base="$arg"; fi
    if [ "$prev" = "--head" ]; then head="$arg"; fi
    prev="$arg"
done
if [ -z "$repo" ]; then
    echo "shoggoth-pr: --repo <owner/name> is required" >&2
    exit 1
fi
if [ -z "$base" ] || [ -z "$head" ]; then
    echo "shoggoth-pr: --base and --head are required for authorship inspection" >&2
    exit 1
fi

"$ROOT/bin/verify-gate.py"
"$ROOT/bin/authorship-gate.py" --base "$base" --head "$head"
"$ROOT/bin/repository-gate.py" "$repo"
exec gh pr create "$@"
