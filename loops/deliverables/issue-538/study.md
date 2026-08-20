# Study: fixed-term termination reason (product#538)

Assuming, unless corrected:

1. The authority on "cannot terminate early" is the SDK's
   `previewCloseMarket()` returning `CloseMarketStatus.EarlyClosureNotAllowed`,
   not a re-derivation from `allowClosureBeforeTerm` alone: the SDK also
   treats `allowTermReduction` (off Sepolia) as an escape hatch, and the UI
   must not disagree with the check that gates the transaction.
2. The fix is desktop-only by construction: the terminate entry point exists
   only in the desktop market sidebar; no mobile surface changes.
3. English is the only locale (`src/locales/en/en.json`); new copy lands as
   i18n keys there, matching the existing early-closure vocabulary.
4. Stacked PRs open for review, no merge to `main` by this run.

## 1. Problem statement

When a borrower opens Terminate Market on a fixed-term market that has not
reached maturity (and early closure is off), the modal tells them to repay
outstanding debt, shows a zero-value debts table, and offers a permanently
disabled "Repay and Terminate" button with no explanation. The real reason,
per the ticket: the market cannot be terminated early. The build routes the
`EarlyClosureNotAllowed` preview status to a dedicated blocked view that
states the reason, names the maturity date, and, when term reduction is
allowed, points at the existing Adjust Maturity control. A working
prototype means the routing decision is a tested pure helper and the modal
renders the blocked view for that status. Proof:
`npx jest src/utils/terminationBlockReason.test.ts src/utils` for the
helper plus the wiring pin, and `npx tsc --noEmit`.

## 2. Prior art

- Bug site: `TerminateMarket/index.tsx` lines 50-59, where any non-Ready
  preview status selects the repay flow; the effect also depends only on
  `isModalOpen` while reading the preview.
- The repay copy: `RepayAndTerminateFlow/index.tsx` line 246,
  `borrowerMarketDetails.modals.terminate.repayRemaining`.
- SDK: `CloseMarketStatus` enum (validation.d.ts), `previewCloseMarket()`
  ordering (EarlyClosureNotAllowed returned before any debt reasoning),
  `Market.isInFixedTerm`, `FixedTermHooksConfig.fixedTermEndTime` /
  `allowClosureBeforeTerm` / `allowTermReduction`, all root-exported.
- Unused copy for exactly this status:
  `SDK_ERRORS_MAPPING.closeMarket.EarlyClosureNotAllowed` ("Market can not
  be closed before maturity"), `src/utils/errors.ts` lines 69-76.
- i18n vocabulary to align with: `marketEarlyClosure.no.tooltip` ("Market
  can only be terminated after fixed duration maturity"), the
  `marketMaturityReduction` rows, and `MaturityModal`'s status-to-message
  precedent.
- Test pattern: the pure-helper cluster in `src/utils/*.test.ts`
  (marketCapabilities, marketOnboarding, serviceAgreementState).

## 3. Constraints and non-goals

- Base `main` at v2.19.0 (9b8b6d5); run branch
  `shoggoth/issue-538-termination-reason`; worktree isolated from the
  halted #789 run. Conventional Commits; exact-pinned dependencies; Node
  22.22.1.
- Non-goals: redesigning the repay-and-terminate flow, adding tooltips to
  `TxModalFooter`, mobile terminate entry points, translating other locales,
  and touching the SDK. The other unexplained statuses (NotBorrower,
  UnpaidWithdrawalBatches) get the same blocked-view mechanism only where it
  falls out for free; the ticket is early closure.

## 4. Design options

1. **Route `EarlyClosureNotAllowed` to a dedicated blocked view via a pure
   helper.** Chosen. A `terminationBlockReason` helper in `src/utils` maps
   the preview status plus the market's fixed-term config to a structured
   reason; `TerminateMarket/index.tsx` gains a `blocked` flow rendering the
   reason, the maturity date, and the term-reduction hint. Trade named: a
   third flow in the modal rather than patching copy inside the repay flow,
   which costs a new small component but keeps the repay flow's semantics
   untouched for markets that genuinely owe debt.
2. **Patch the repay flow's alert text conditionally.** Smallest diff, but
   the zero-debt table and the disabled Repay-and-Terminate button would
   remain, which is most of the confusion. Rejected.
3. **Disable the sidebar button with a tooltip.** Hides the flow entirely,
   but the sidebar renders no disabled states today, `TxModalFooter` has no
   tooltip slot, and the ticket asks for feedback, not absence. Rejected.

## 5. Risk register seed

- **Divergence from the SDK.** The helper must key on the SDK status; a
  local re-derivation of "in term and no escape" can disagree with
  `previewCloseMarket()` (the `allowTermReduction`-off-Sepolia subtlety).
- **Stale flow selection.** The existing effect recomputes only when the
  modal opens; keep that trigger but fix the dependency list so the chosen
  flow matches the preview at open time.
- **Repay-flow regression.** Markets with genuine debt must still land in
  the repay flow; the helper's tests pin every `CloseMarketStatus` value to
  its expected flow.
- **Date rendering.** `fixedTermEndTime` is a unix-seconds value; format
  with the repo's existing `formatDate`/dayjs conventions, UTC-labelled.

## 6. Glossary seeds

- Blocked view: the modal state explaining why termination is unavailable.
- Preview status: `CloseMarketStatus` from `previewCloseMarket()`.
- Escape hatch: `allowClosureBeforeTerm`, or `allowTermReduction` off
  Sepolia, either of which avoids `EarlyClosureNotAllowed`.

## 7. Sources

- Ticket https://github.com/wildcat-finance/product/issues/538 (screenshot
  of the wrong repay message).
- Exploration pass over the worktree (paths and line numbers cited above).
- `@wildcatfi/wildcat-sdk` 3.1.4-beta.4 dist typings.

## Boundaries

- **Always.** `npx jest <touched suites>` and `npx tsc --noEmit` before
  every commit; imprimatur on shipped documents; eslint clean on changed
  files.
- **Ask first.** Any dependency; any SDK version change; widening the fix
  beyond the terminate modal.
- **Never.** Re-enable the terminate transaction for a blocked status;
  delete or weaken the repay flow for indebted markets; claim a suite ran
  when it did not.

## Success criteria

1. `npx jest src/utils/terminationBlockReason.test.ts` passes, covering
   every `CloseMarketStatus` value's flow routing and the maturity /
   term-reduction fields of the blocked reason.
2. `npx jest src/utils` stays green (wiring pin included: the modal file
   references the helper and the blocked flow; the repay flow file no
   longer renders for the early-closure status by construction of the
   routing).
3. `npx tsc --noEmit` exit 0; eslint 0 errors on changed files.
4. Opening the modal on a blocked market renders: the real reason, the
   maturity date, and the term-reduction hint when applicable, with a
   single Close action. Verified by the helper tests plus review of the
   rendered JSX; no repay table and no disabled repay button in that state.
