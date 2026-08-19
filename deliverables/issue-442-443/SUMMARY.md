# Loop 3 — product#442 + product#443: terminated-market screens

Delivered 2026-08-19 as a stacked PR pair against `wildcat-app-v2`, opened
for review and deliberately not merged. One loop, two tickets (worked in
dependency order: #443's live half first conceptually, both landing
together).

## Verification against the current app (the tickets are from 2024)

- **#442 was fully live.** Nothing gated the Borrow and Repay tab or screen
  on termination: a borrower's terminated market landed on Borrow and
  Repay by default, showing two amount panels with every action hidden or
  disabled.
- **#443 was half stale.** There is no Market Statement download anywhere
  in today's app. `StatementModal` was an orphan: imported by nothing, its
  Download button only closed the dialog, no export logic, no API route.
  There was nothing to move. The other half (Status and Details as the
  landing screen) was live, scoped to terminated markets to honour
  @miagkova-anastasia's recorded concern about changing the default for
  active markets.

## What shipped

Run branch: `shoggoth/issue-442-443-terminated-market-screens` (off `main`,
own worktree; the halted #789 and #538 runs are untouched).

1. [PR #378](https://github.com/wildcat-finance/wildcat-app-v2/pull/378) —
   section policy as a tested pure helper: the Borrow and Repay tab exists
   only for the borrower of an open market on the right chain; terminated
   markets lose the tab (sidebar and render guard, so stale persisted
   Redux state cannot resurrect the screen) and land on Status and
   Details. Active markets unchanged.
2. [PR #379](https://github.com/wildcat-finance/wildcat-app-v2/pull/379) —
   deletes the orphaned `StatementModal` and its two unused i18n keys, with
   a wiring test that walks `src/` and pins zero remaining references.

Tests: 11 new (7 policy, 4 wiring); full `src/utils` suite 39 green; tsc
and eslint clean. Audit log on the run branch: two clean rounds.

## Decision for the operator (#443's statement half)

Recommendation: treat the statement download as superseded by the
self-serve exports epic (#851/#852, PR #340 in flight), which delivers a
strictly better artefact (full bundle with statements layered on data).
On merging this stack: close #442 outright; close #443 with a note that
its live half shipped here and its statement half is superseded, or
re-scope #443 to "statement lives in the export bundle" under the epic.

## Operator actions

1. Review and merge #378 then #379, then the run branch into `main`
   (fiat state parked in `work/wildcat-app-v2-442/.hexaemeron`,
   `hexctl resume` brings the stack down on the ledger).
2. Eyeball a terminated market on testnet: it should land on Status and
   Details with no Borrow and Repay entry in the sidebar.
3. Close #442 and #443 per the decision above; attach this summary.
4. Flagged for a future ticket: the borrower page's numeric `checked`
   section state (versus the lender side's enum slice) invites drift;
   a small refactor ticket would prevent the next instance of this bug.
