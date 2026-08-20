# Runbook: fixed-term termination reason (product#538)

Two steps on `shoggoth/issue-538-termination-reason`. Stack opened for
review, not merged (study assumption 4).

## Step 1: Routing helper, i18n copy, and committed spec

**Goal.** The flow decision is a tested pure function and the new copy
exists, with the spec committed.
**Entry.** `shoggoth/issue-538-termination-reason` at the cut of `main`.
**Exit.** `npx jest src/utils/terminationBlockReason.test.ts` green (every
`CloseMarketStatus` value routed, blocked-reason fields covered, 10 or more
assertions); `npx tsc --noEmit` exit 0.
**Files.** `src/utils/terminationBlockReason.ts` (+ `.test.ts`),
`src/locales/en/en.json` (terminate.earlyClosure keys),
`docs/fixed-term-termination-reason.md` (shipped spec).
**Tests.** Ready routes to terminate at zero debt and repay otherwise;
InsufficientBalance / InsufficientAllowance / UnpaidWithdrawalBatches route
to repay; EarlyClosureNotAllowed and NotBorrower route to blocked with the
reason, maturity timestamp, and term-reduction flag populated from the
hooks config.

## Step 2: Blocked view in the terminate modal, demonstrated

**Goal.** The modal shows the real reason instead of the repay flow for
blocked statuses.
**Entry.** Step 1's exit state.
**Exit.** `npx jest src/utils` green including a wiring pin
(`src/utils/terminationWiring.test.ts`: the modal imports the helper and
the blocked component, and selects flows through the helper);
`npx tsc --noEmit` exit 0; eslint 0 errors on changed files.
**Files.** `.../Modals/TerminateMarket/BlockedFlow/index.tsx` (reason,
maturity date, term-reduction hint, Close action),
`.../Modals/TerminateMarket/index.tsx` (route via the helper, fixed effect
dependencies), `src/utils/terminationWiring.test.ts`.
**Tests.** The wiring pin above; the helper suite re-runs as the
demonstration named by the study.
