#!/bin/sh
# Rolling archive: mirror every session scratchpad for this project into .loops/,
# then zip scratch, deliverables, loop state, and docs.
# Run at the end of every loop (and whenever something worth keeping lands in scratch).
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
MIRROR="$ROOT/.loops/archives/scratch-mirror"
mkdir -p "$MIRROR"

for pad in /private/tmp/claude-501/-Users-c0rtexzer0-Projects-shoggoth-interceptor/*/scratchpad; do
    [ -d "$pad" ] || continue
    session=$(basename "$(dirname "$pad")")
    mkdir -p "$MIRROR/$session"
    rsync -a "$pad/" "$MIRROR/$session/"
done

STAMP=$(date -u +%Y%m%d-%H%M%S)
ZIP="$ROOT/.loops/archives/shoggoth-$STAMP.zip"
cd "$ROOT"
zip -qr "$ZIP" .loops/deliverables .loops/excluded.json .loops/loop.json \
    .loops/pipelines.json .loops/archives/scratch-mirror CLAUDE.md bin \
    -x '*/.DS_Store' '*/__pycache__/*' '*.pyc' '*.pyo'

# keep the newest 10 zips
ls -t "$ROOT"/.loops/archives/shoggoth-*.zip 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null || true
echo "archived -> $ZIP"
