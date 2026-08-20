# Migration check: borrower restriction (PR #367)

Run 2026-08-19 with `bin/migration-check.sh loops/work/wildcat-app-v2` (the #789
run branch tree), answering Jack's question about how the migration was
tested. Method: disposable Postgres 16 in Docker, zero production
credentials anywhere in the pipeline; `prisma migrate deploy` applies the
repo's entire migration history from an empty database, then
`prisma migrate diff --from-url <disposable db> --to-schema-datamodel
prisma/schema.prisma --exit-code` asserts the migrated database matches the
schema exactly.

Result: **PASS.**

- All migrations applied cleanly from zero, including
  `20260819030000_borrower_restriction` (the #367 columns).
- Diff against `schema.prisma`: "No difference detected."

This check is now guardrail (b) in the loop protocol: any future loop
touching `prisma/schema.prisma` or `prisma/migrations/` must pass it and
log the result in the audit round before the step pushes. Preview builds
sharing the production database remain your ticket #665; nothing in this
check or the loop ever runs a migration against a shared environment.
