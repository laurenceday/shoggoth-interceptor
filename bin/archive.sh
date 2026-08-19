#!/bin/sh
# Rolling archive: mirror every session scratchpad for this project into the repo,
# then zip scratch + deliverables + state + docs so nothing dies when scratch goes cold.
# Run at the end of every loop (and whenever something worth keeping lands in scratch).
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
MIRROR="$ROOT/archives/scratch-mirror"
mkdir -p "$MIRROR" "$ROOT/archives"

for pad in /private/tmp/claude-501/-Users-c0rtexzer0-Projects-shoggoth-interceptor/*/scratchpad; do
    [ -d "$pad" ] || continue
    session=$(basename "$(dirname "$pad")")
    mkdir -p "$MIRROR/$session"
    rsync -a "$pad/" "$MIRROR/$session/"
done

STAMP=$(date -u +%Y%m%d-%H%M%S)
ZIP="$ROOT/archives/shoggoth-$STAMP.zip"
cd "$ROOT"
zip -qr "$ZIP" deliverables state archives/scratch-mirror CLAUDE.md bin \
    -x 'state/board.json'   # regenerable and big; everything else goes in

# keep the newest 10 zips
ls -t "$ROOT"/archives/shoggoth-*.zip 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null || true
echo "archived -> $ZIP"
