# Runbook: terminated-market screens (product#442, product#443)

Two steps on `shoggoth/issue-442-443-terminated-market-screens`. Stack
opened for review, not merged (study assumption 3).

## Step 1: Section policy helper wired into page and sidebar

**Goal.** Terminated markets land on Status and Details and lose the Borrow
and Repay entry, through one tested helper, with the spec committed.
**Entry.** `shoggoth/issue-442-443-terminated-market-screens` at the cut of
`main`.
**Exit.** `npx jest src/utils/borrowerMarketSections.test.ts` green (10 or
more assertions); `npx tsc --noEmit` exit 0.
**Files.** `src/utils/borrowerMarketSections.ts` (+ `.test.ts`),
`src/app/[locale]/borrower/market/[address]/page.tsx` (fallback effect via
the helper; guard on the section-1 render block),
`src/components/Sidebar/MarketSidebar/index.tsx` (tab visibility via the
helper), `docs/terminated-market-screens.md` (shipped spec).
**Tests.** Active interactable market keeps the tab and section 1;
terminated market hides the tab and falls back from 1 to 2;
non-interactable viewer behaves as today (fallback subsumes it); sections
other than 1 never trigger fallback.

## Step 2: Remove dead statement machinery, demonstrated

**Goal.** The orphaned statement code is gone and the whole delivery is
proven.
**Entry.** Step 1's exit state.
**Exit.** `npx jest src/utils` green including the wiring pin
(`src/utils/terminatedMarketWiring.test.ts`); `npx tsc --noEmit` exit 0;
eslint 0 errors on changed files; the decision brief written to the
interceptor's `loops/deliverables/issue-442-443/`.
**Files.** Delete
`src/app/[locale]/borrower/market/[address]/components/Modals/StatementModal/`
(three files); remove `borrowerMarketDetails.modals.statement` and
`lenderMarketDetails.buttons.statement` from `src/locales/en/en.json`;
`src/utils/terminatedMarketWiring.test.ts`; deliverables in the interceptor
repo.
**Tests.** Wiring pin: page and sidebar reference the helper, the section-1
block is guarded, and no source file references StatementModal or the
removed i18n keys. Full `src/utils` suite re-runs as the demonstration.
