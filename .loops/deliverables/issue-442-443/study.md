# Study: terminated-market screens (product#442, product#443)

Assuming, unless corrected:

1. The tickets predate the current app. Verified against the tree at
   v2.19.0: #442 is fully live, while #443's "move the statement download"
   half has nothing to move. `StatementModal` is imported by nothing, its
   Download button only closes the dialog, and no statement export or API
   route exists. The recorded reading: implement #442 plus #443's live half
   (Status and Details as the landing screen for terminated markets),
   remove the orphaned statement code, and hand the operator a decision
   brief recommending #443's statement half be treated as superseded by the
   in-flight exports work (#851/#852, wildcat-app-v2 PR #340).
2. The designer's recorded doubt on #443 (the default screen matters for
   active markets) is honoured by scoping the default change to terminated
   markets only; active markets keep Borrow and Repay as the landing
   screen.
3. Stacked PRs open for review, no merge to `main` by this run.

## 1. Problem statement

A borrower opening their terminated market lands on Borrow and Repay: two
amount panels whose action buttons are all hidden or disabled, as the
landing screen, with the sidebar still offering the tab. The build makes a
terminated market land on Status and Details, removes the Borrow and Repay
entry for it (sidebar and render guard, so a stale persisted selection
cannot resurrect it), and deletes the dead statement machinery. A working
prototype means the section decision is a tested pure helper wired into the
page and sidebar. Proof: `npx jest src/utils` (helper suite plus wiring
pin) and `npx tsc --noEmit`.

## 2. Prior art

- Section state: `highlightSidebarSlice` (`checked`, default 1 = Borrow and
  Repay, unconditional), rendered as `{checked === N && ...}` blocks in
  `borrower/market/[address]/page.tsx` (lines 278-388), sidebar buttons in
  `src/components/Sidebar/MarketSidebar/index.tsx` (Borrow and Repay at
  lines 76-107 behind `canInteract` only).
- The one existing fallback: `page.tsx:173-178` redirects `checked === 1`
  to section 2 when `!canInteract`; the lender side has the clean shape
  (`lender/market/[address]/page.tsx:172-178`).
- Termination signal: `market.isClosed`, already mapped to
  `MarketStatus.TERMINATED` in `src/utils/marketStatus.ts`; the terminate
  button itself hides on `isClosed`.
- Today's terminated-market rendering: `MarketTransactions` hides
  RepayModal/BorrowModal and disables every parameter modal on `isClosed`,
  leaving an actionless screen (index.tsx lines 43-47, 119-168, 236-270).
- Dead statement machinery: `.../Modals/StatementModal/*` (unreferenced),
  i18n keys `borrowerMarketDetails.modals.statement.*` and
  `lenderMarketDetails.buttons.statement` (unused).
- Exports work that supersedes the statement idea: product#851/#852,
  wildcat-app-v2 PR #340 (open, feat/exports).
- Test pattern: pure helpers in `src/utils` with wiring-pin suites, as
  shipped for product#538 on this board.

## 3. Constraints and non-goals

- Base `main` at v2.19.0 (9b8b6d5); run branch
  `shoggoth/issue-442-443-terminated-market-screens`; isolated worktree.
  Conventional Commits, exact pins, Node 22.22.1.
- Non-goals: building a statement export (superseded by the exports epic);
  changing the default screen for active markets (designer's doubt);
  reworking the numeric `checked` section state into an enum (worth its own
  ticket; noted in the brief); the lender side; the pre-existing
  `setSidebarHighlightState` call that omits `tokenWrapper`.

## 4. Design options

1. **Pure section-policy helper wired into the page and sidebar.** Chosen.
   `src/utils/borrowerMarketSections.ts` answers two questions:
   `showBorrowRepayTab({canInteract, isClosed})` and
   `borrowerMarketFallbackSection({canInteract, isClosed, checked})`
   (returning the section to switch to, or null). The page's existing
   fallback effect and the sidebar button consume it; the `checked === 1`
   render block gains the same guard. Trade named: one more indirection
   for two small conditions, bought back as testability and a single place
   the next section rule lands.
2. **Inline `!market.isClosed` at each of the three sites.** Smallest diff,
   but the rule would live in three places with no test, which is how the
   current inconsistency happened. Rejected.
3. **Migrate sections to an enum slice like the lender side first.**
   Correct long-term, but a refactor of eight screens for a two-condition
   fix; out of single-loop scope. Rejected, recommended in the brief.

## 5. Risk register seed

- **Stale persisted selection.** `checked` lives in Redux; a user already
  on section 1 when the market terminates (or with persisted state) must
  be moved by the effect and blocked by the render guard, not just hidden
  in the sidebar.
- **Active-market regression.** Active markets must keep section 1 as
  default and keep the tab; helper tests pin both.
- **Non-borrower flows.** The existing `!canInteract` fallback must keep
  working unchanged; the helper subsumes it and tests pin equivalence.
- **Dead-code removal blast radius.** `StatementModal` is provably
  unreferenced (grep pinned in a test is unnecessary; deletion compiles or
  it does not); the two i18n keys are removed with it.

## 6. Glossary seeds

- Section: the numeric `checked` value selecting a market-detail screen.
- Landing rule: which section a borrower first sees for a given market
  state.
- Statement half: the part of #443 about a download that no longer exists.

## 7. Sources

- Tickets: product#442, product#443 (including the designer comment).
- Exploration pass over this worktree (paths and line numbers above).
- product#851/#852 and wildcat-app-v2 PR #340 for the exports supersession.

## Boundaries

- **Always.** `npx jest <touched suites>` and `npx tsc --noEmit` before
  every commit; imprimatur on shipped documents; eslint clean on changed
  files.
- **Ask first.** Any dependency; touching the lender side; widening into
  the section-enum refactor.
- **Never.** Change the landing screen for active markets; leave the
  Borrow and Repay screen reachable on a terminated market via stale
  state; claim a suite ran when it did not.

## Success criteria

1. `npx jest src/utils/borrowerMarketSections.test.ts` passes: tab shown
   and section 1 kept for active interactable markets; tab hidden and
   fallback to section 2 for terminated markets and for non-interactable
   viewers; no fallback fired from sections other than 1.
2. Wiring pin green: page and sidebar consume the helper; the
   `checked === 1` render block carries the guard; `StatementModal` and
   both unused statement i18n keys are gone from the tree.
3. `npx tsc --noEmit` exit 0; eslint 0 errors on changed files.
4. Decision brief for the operator covering #442 (close on merge), #443
   (close the statement half as superseded, or re-scope), delivered in the
   interceptor's deliverables.
