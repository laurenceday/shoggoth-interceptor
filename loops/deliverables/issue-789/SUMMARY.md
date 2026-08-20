# Loop 1 - product#789: Restrict removed-borrower UI actions

Delivered 2026-08-19 as a stacked PR chain against `wildcat-app-v2`, opened
for review and deliberately not merged.

## What shipped

Run branch: `shoggoth/issue-789-restrict-removed-borrowers` (off `main`).

1. [PR #367](https://github.com/wildcat-finance/wildcat-app-v2/pull/367) -
   pure restriction state machine, additive Prisma columns + migration
   (`removedFromArchController`, `removedAt`, `restrictionOverride` + who/when),
   persistence helpers, shipped spec at `docs/borrower-restriction.md`.
2. [PR #368](https://github.com/wildcat-finance/wildcat-app-v2/pull/368) -
   `/api/borrowers/[address]/restriction`: GET computed state, POST
   self-verifying sync (server reads the archcontroller view itself; Slack
   webhook on new restriction via `SLACK_WEBHOOK_URL`), PUT admin override
   behind `verifyApiToken` + `isAdminForChain`. Server-side enforcement in
   the profile-update and market-description routes.
3. [PR #369](https://github.com/wildcat-finance/wildcat-app-v2/pull/369) -
   client gating: fail-closed `useBorrowerRestriction` hook with a persisted
   last-known cache (downtime never re-enables), create-market block panel +
   banner, profile-edit block + hidden entry, description editor gate.
   Repay/terminate pinned ungated by a mechanical test.
4. PR #370 (step 4) - admin override toggle in EditBorrowerModal + hook.

Tests: 43 passing across 5 new suites; `tsc --noEmit` and eslint clean.
Audit log: `audit/AUDIT.md` on the run branch (4 clean rounds, 1 carried
note resolved).

## Acceptance criteria coverage

- Market creation / profile editing / description editing disabled: done
  (client + server; deploy is also enforced onchain by the factory).
- Repayment and termination remain enabled: done, mechanically pinned.
- Persisted set-once flag, no per-load onchain checks: done (sync route).
- Downtime never re-enables: done (persisted last-known cache + server flag).
- Admin manual override with precedence: done (PUT + admin panel toggle).
- Slack notification on restriction: done (`SLACK_WEBHOOK_URL`, degrades to
  a log line when unset - **ops must add this env var**).
- Edge case (re-registration): auto-clears unless manually restricted, per
  the ticket's assumption - **needs Foundation confirmation**.

## What the operator should do

1. Review and merge the stack bottom-up (#367 → #368 → #369 → #370), then
   the run branch into `main`. Apply the Prisma migration on deploy.
2. Add `SLACK_WEBHOOK_URL` to the server environment.
3. Confirm the auto-clear-on-re-registration assumption with the Foundation.
4. Decide who pokes the sync (`POST /api/borrowers/<addr>/restriction`):
   the Foundation's removal runbook, or a follow-up that wires the existing
   registration-change listener to call it.
5. Out of scope, flagged: the subgraph's `handleBorrowerRemoved` writes
   `isRegistered: true` (bug documented in `src/lib/registrar.ts`) - the
   existing "you have been removed" notification likely misfires; separate
   subgraph ticket recommended. Telegram/public notification remains the
   ticket's separate sub-issue.
6. Attach this summary to product#789 and move it to Review/QA.
