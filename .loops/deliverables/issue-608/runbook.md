# Runbook: deposit max button (product#608)

Two steps on `shoggoth/issue-608-deposit-max-button`. Stack opened for
review, not merged (study assumption 3).

## Step 1: Fill and effective-amount helpers, with the spec committed

**Goal.** The fill rules exist as tested pure functions.
**Entry.** `shoggoth/issue-608-deposit-max-button` at the cut of `main`.
**Exit.** `npx jest src/utils/depositMaxFill.test.ts` green (8 or more
assertions); `npx tsc --noEmit` exit 0.
**Files.** `src/utils/depositMaxFill.ts` (+ `.test.ts`),
`docs/deposit-max-button.md` (shipped spec).
**Tests.** Display string equals the truncating format of the max; zero
max yields no fill; the effective amount is the exact value while the
input still equals its display string and the parsed value otherwise
(edited, cleared, or replaced input).

## Step 2: Max control in both deposit branches, demonstrated

**Goal.** Desktop and mobile deposit inputs gain the Max control through
one shared handler, with the transaction using the effective amount.
**Entry.** Step 1's exit state.
**Exit.** `npx jest src/utils` green including the wiring pin
(`src/utils/depositMaxWiring.test.ts`); `npx tsc --noEmit` exit 0; eslint
0 errors on changed files.
**Files.** `.../lender/market/[address]/components/Modals/DepositModal/
index.tsx` (exactAmount state, shared fill handler, Max button composed
into both endAdornments, effective amount feeding the deposit call, exact
cleared on edit and reset), `src/utils/depositMaxWiring.test.ts`.
**Tests.** Wiring pin: both branches reference the shared handler and the
Max control; the parse site routes through the effective-amount rule; the
exact amount clears on manual edit. Full `src/utils` suite re-runs as the
demonstration.
