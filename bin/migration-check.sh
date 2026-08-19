#!/bin/sh
# Guardrail (b): the disposable-Postgres migration test. Required for any
# loop whose diff touches prisma/schema.prisma or prisma/migrations. Never
# needs, sees, or accepts production credentials: it boots a throwaway
# Postgres in Docker, applies every migration from zero, and asserts the
# resulting database matches schema.prisma exactly.
#
# Usage: migration-check.sh <app-worktree-path>
# Exit 0 = migrations apply cleanly from zero AND produce schema.prisma.
set -eu

WORKTREE=$(cd "${1:?usage: migration-check.sh <app worktree>}" && pwd)
PORT=$((20000 + $$ % 10000))
NAME="shoggoth-migration-check-$$"
URL="postgresql://postgres:shoggoth@127.0.0.1:$PORT/postgres"

command -v docker >/dev/null || { echo "migration-check: docker required" >&2; exit 1; }
[ -f "$WORKTREE/prisma/schema.prisma" ] || { echo "migration-check: no prisma/schema.prisma in $WORKTREE" >&2; exit 1; }

cleanup() { docker rm -f "$NAME" >/dev/null 2>&1 || true; }
trap cleanup EXIT INT TERM

echo "migration-check: starting disposable postgres ($NAME, port $PORT)"
docker run --rm -d --name "$NAME" -p "127.0.0.1:$PORT:5432" \
    -e POSTGRES_PASSWORD=shoggoth postgres:16-alpine >/dev/null

tries=0
until docker exec "$NAME" pg_isready -U postgres >/dev/null 2>&1; do
    tries=$((tries + 1))
    [ "$tries" -gt 60 ] && { echo "migration-check: postgres never became ready" >&2; exit 1; }
    sleep 1
done

cd "$WORKTREE"
export DATABASE_URL="$URL" DIRECT_URL="$URL"

echo "migration-check: applying all migrations from zero"
npx --no-install prisma migrate deploy

echo "migration-check: diffing migrated database against schema.prisma"
npx --no-install prisma migrate diff \
    --from-url "$URL" \
    --to-schema-datamodel prisma/schema.prisma \
    --exit-code && diff_status=0 || diff_status=$?

if [ "$diff_status" -ne 0 ]; then
    echo "migration-check: FAILED — migrations do not reproduce schema.prisma (drift above)" >&2
    exit 1
fi
echo "migration-check: OK — migrations apply cleanly and match schema.prisma"
