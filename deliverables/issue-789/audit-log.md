# Audit log: restrict removed borrowers (product#789)

## Step 1, round 1 — 2026-08-19

Suite: waived (no Solidity); bundled lints ran per the non-Solidity rule.

| id | severity | file | finding | status |
| --- | --- | --- | --- | --- |

Findings: 0. phylax, ephoros, hypomnema all exit 0. Manual review against the
risk register: pure state machine has no I/O; migration is additive with
defaults, reversible; persistence helpers lowercase addresses consistently and
guard the removal transition on row existence. Carried note for step 2:
setRestrictionOverride throws Prisma P2025 on an unknown borrower, so the PUT
route must 404 before calling it.

Leads not pursued: none

## Step 2, round 1 — 2026-08-19

Suite: waived (no Solidity); bundled lints ran (all exit 0); jest 29 passed;
eslint 0 errors on changed files; tsc --noEmit exit 0 (after generating the
gitignored next-env.d.ts a fresh clone lacks; the step-1 receipt's tsc claim
predated that file, and re-running against the step-1 content confirms it
held for code the step actually shipped).

| id | severity | file | finding | status |
| --- | --- | --- | --- | --- |

Findings: 0. Manual review: POST sync trusts only its own archcontroller
read and fails closed on RPC errors; PUT enforces token, admin, DTO, and
existence checks before any write (clears the step 1 carried note); the
Slack URL is never logged; enforcement is server-side in both write routes.

Leads not pursued: two concurrent first syncs can each fire the Slack
notification (duplicate message, no state harm); the sync route has no rate
limit, consistent with every other route in the repo. Both accepted for the
prototype.

## Step 3, round 1 — 2026-08-19

Suite: waived (no Solidity); bundled lints ran (all exit 0); jest 41 passed
across 4 suites; eslint 0 errors; tsc --noEmit exit 0.

| id | severity | file | finding | status |
| --- | --- | --- | --- | --- |

Findings: 0. Manual review: fail-closed gate covered by tests (restricted
sticks through backend downtime via the persisted cache); market deployment
is also enforced onchain by the factory's registration check, so the UI gate
is UX rather than the security boundary; profile and description writes are
enforced server-side from step 2. Carve-out pinned mechanically.

Leads not pursued: a removed borrower whose first-ever restriction read
fails (no cache) sees the default banner until a read succeeds; accepted,
the chain and API remain the enforcement.
