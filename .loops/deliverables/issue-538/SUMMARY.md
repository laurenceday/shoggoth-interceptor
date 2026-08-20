# Loop 2 - product#538: Fixed-term termination shows the wrong reason

Delivered 2026-08-19 as a stacked PR pair against `wildcat-app-v2`, opened
for review and deliberately not merged.

## The bug, precisely

`TerminateMarket/index.tsx` routed every non-Ready `previewCloseMarket()`
status into the repay-and-terminate flow. For a fixed-term market inside
its term with early closure off, the SDK returns
`CloseMarketStatus.EarlyClosureNotAllowed` before any debt reasoning, so
the borrower saw the repay-debt alert, a zero-value debts table, and a
permanently disabled button, with no explanation. The flow was also chosen
only when the modal opened, from a stale check.

## What shipped

Run branch: `shoggoth/issue-538-termination-reason` (off `main`, isolated
worktree; the halted #789 run is untouched).

1. [PR #374](https://github.com/wildcat-finance/wildcat-app-v2/pull/374) -
   pure routing helper (`src/utils/terminationBlockReason.ts`) keyed on the
   SDK status (the single authority, respecting the
   allowTermReduction-off-Sepolia subtlety), i18n copy aligned with the
   parameters table's early-closure vocabulary, shipped spec.
2. [PR #375](https://github.com/wildcat-finance/wildcat-app-v2/pull/375) -
   the modal routes through the helper: blocked markets get a view stating
   the real reason, the maturity date, and a pointer to Adjust Maturity
   when term reduction is permitted; non-borrower wallets get their own
   line; indebted markets keep the repay flow; flow recomputes on status
   change.

Tests: 16 new (11 helper covering every `CloseMarketStatus` value, 5 wiring
pins); full `src/utils` suite 44 green; tsc and eslint clean. Audit log on
the run branch: two clean rounds.

## What the operator should do

1. Review and merge #374 then #375, then the run branch into `main`
   (fiat state parked in `.loops/work/wildcat-app-v2-538/.hexaemeron`, resume with
   `hexctl resume` to bring the stack down on the ledger).
2. Eyeball the blocked view on a testnet fixed-term market; copy tweaks are
   one i18n key each under
   `borrowerMarketDetails.modals.terminate.earlyClosure`.
3. Flagged in passing (pre-existing, untouched): the repay flow's hardcoded
   English strings and its unexplained UnpaidWithdrawalBatches state could
   use a small copy-cleanup ticket.
4. Attach this summary to product#538 and move it to Review/QA.
