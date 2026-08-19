# Study: deposit max button (product#608)

Assuming, unless corrected:

1. The ticket's "whichever is greater" is a typo for "lesser": the greater
   of balance and remaining capacity can never be deposited when they
   differ, and the SDK already defines the sensible value:
   `MarketAccount.maximumDeposit` is `min(market.maximumDeposit,
   underlyingBalance)`. The reading is recorded here and flagged in the
   operator summary.
2. The button fills the field and never submits; every existing validation
   (minimum deposit, allowance, ToU gate) keeps running against the filled
   value. A market whose minimum deposit exceeds the fillable maximum
   shows the existing below-minimum error rather than hiding the button.
3. Stacked PRs open for review, no merge to `main` by this run.

## 1. Problem statement

Lenders typing a deposit amount have no one-tap way to deposit everything
they can. The build adds a Max control to the deposit modal (desktop and
mobile branches of the same component) that fills the amount with
`marketAccount.maximumDeposit`, keeping an exact `TokenAmount` alongside
the display string so the transaction deposits the true value rather than
a five-decimal truncation. A working prototype means the fill and
effective-amount rules are tested pure functions wired into both branches.
Proof: `npx jest src/utils/depositMaxFill.test.ts src/utils` and
`npx tsc --noEmit`.

## 2. Prior art

- The value: `MarketAccount.maximumDeposit` (SDK dist/account/index.js:518,
  `minTokenAmount(market.maximumDeposit, underlyingBalance)`), already
  rendered by the modal as the field label and the "Available to deposit"
  row in both branches (mobile lines 685-722, desktop 1137-1200).
- Fill patterns in the house, newest first: WithdrawModal (exact
  `TokenAmount` truth source, `.format(5)` display, comma-stripping parse,
  cleared on manual edit; `useWithdrawRouting.ts:281-308`), WrapperSection
  (`setExactAmount` + `.format(5)`), RepayModal (fills
  `formatTokenWithCommas` and strips commas at parse).
- The traps, verified: `Token.parseAmount` throws on commas; the modal's
  parse at DepositModal lines 219-222 does not strip them, so
  `formatTokenWithCommas` output cannot be filled; `formatTokenWithCommas`
  also rounds up past the true value via `toLocaleString`;
  `TokenAmount.format` truncates safely but loses sub-five-decimal dust,
  which the exact amount preserves.
- Adornment layout: both branches already hold the token-symbol
  `TextfieldChip` in `endAdornment`; RepayModal's `TextfieldButton`
  ("Max") composes beside it.
- Deposit status logic the fill must satisfy: the modal's local
  `getDepositStatus` (lines 225-244) checks capacity, balance, minimum,
  allowance in that order.
- Test pattern: pure-logic suites beside utils (`withdrawQueue.test.ts`,
  loop precedents on this board).

## 3. Constraints and non-goals

- Base `main` at v2.19.0 (9b8b6d5); run branch
  `shoggoth/issue-608-deposit-max-button`; isolated worktree; Conventional
  Commits; exact pins; Node 22.22.1.
- Non-goals: internationalising the modal's pre-existing hard-coded
  strings (noted for the operator), reworking the modal's local deposit
  status logic or its missing `previewDeposit` (the SDK TODO stands),
  touching borrow/repay/withdraw flows, adding a thousand separator to the
  input.

## 4. Design options

1. **Exact-amount fill, shared handler, button composed into the existing
   adornment.** Chosen. A pure `src/utils/depositMaxFill.ts` supplies
   `fillMaxDeposit(max)` (display string via truncating `format`) and
   `effectiveDepositAmount({exact, parsed})`; the modal gains
   `exactAmount` state set by the Max button, cleared on manual edit and
   on the reset paths, and the transaction amount prefers it. One handler,
   two JSX sites (mobile and desktop). Trade named: a second piece of
   amount state to keep coherent, bought back as dust-free deposits on
   six-decimal tokens.
2. **String-only fill with `.format(5)`.** Smaller, but deposits of a
   six-decimal balance leave dust and "Max" would not mean max. Rejected.
3. **`formatTokenWithCommas` fill like RepayModal.** Would require also
   changing the parse to strip commas and inherits the round-up hazard.
   Rejected.

## 5. Risk register seed

- **Fill exceeding the true value.** Never format with rounding; the
  display string comes from the SDK's truncating `format`, and the exact
  amount is the SDK value itself.
- **Stale exact amount.** Any manual edit and every reset path must clear
  it, or a user could edit the field and still send the old exact value;
  the effective-amount rule only honours the exact value while the input
  still equals its display string.
- **Zero max.** Both branches already disable the deposit entry when
  `maximumDeposit` is zero; the button additionally hides itself on zero
  so it never fills "0".
- **Minimum above maximum.** The existing below-minimum validation fires
  on the filled value; nothing new to enforce.

## 6. Glossary seeds

- Max value: `marketAccount.maximumDeposit`, the SDK's
  min(balance, remaining capacity).
- Exact amount: the `TokenAmount` the fill stores beside the display
  string, used for the transaction while the input is untouched.
- Dust: the sub-display-precision remainder a truncated string would
  leave behind.

## 7. Sources

- Ticket https://github.com/wildcat-finance/product/issues/608.
- Exploration pass over this worktree (paths and line numbers above).
- `@wildcatfi/wildcat-sdk` 3.1.4-beta.4 dist sources for maximumDeposit,
  parseAmount, and format behaviour.

## Boundaries

- **Always.** `npx jest <touched suites>` and `npx tsc --noEmit` before
  every commit; imprimatur on shipped documents; eslint clean on changed
  files.
- **Ask first.** Any dependency; changing the amount parse or input
  component behaviour beyond the fill; touching other modals.
- **Never.** Fill a value the SDK reports as undepositable; round a fill
  upward; submit on fill; claim a suite ran when it did not.

## Success criteria

1. `npx jest src/utils/depositMaxFill.test.ts` passes: display string is
   the truncating format of the max; the effective amount is the exact
   value while the input matches and the parsed value after any edit;
   zero max hides the fill.
2. Wiring pin green: both render branches carry the Max control wired to
   the shared handler; manual edits and reset paths clear the exact
   amount; the transaction amount goes through the effective-amount rule.
3. `npx tsc --noEmit` exit 0; eslint 0 errors on changed files.
4. Operator summary records the "greater"/"lesser" reading for
   confirmation on the ticket.
