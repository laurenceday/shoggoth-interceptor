# Study: restrict removed borrowers (product#789)

Assuming, unless corrected:

1. "Removed" means the address no longer passes the archcontroller's
   `isRegisteredBorrower` view. The subgraph's `BorrowerRegistrationChange.
   isRegistered` field is not usable for removals: `src/lib/registrar.ts:83-88`
   documents that `handleBorrowerRemoved` writes `isRegistered: true`.
   Detection therefore uses the onchain view (server-side) only.
2. Re-registration auto-clears the persisted removal flag unless an admin has
   set a manual restriction, matching the ticket's stated assumption; the
   ticket asks for Foundation confirmation, and the code comment marks it.
3. The Slack notification is a server-side webhook POST to a
   `SLACK_WEBHOOK_URL` environment variable; no Slack integration exists in
   the repo today, and absence of the variable downgrades to a server log
   line rather than a failure.
4. Node 22 with exact-pinned dependencies (husky check); tests are jest.
   Tests that need a live database (the existing integration-flavoured API
   tests) are out of scope to run here; new tests are written so the pure
   logic and route guards run without a database.
5. Stacked pull requests are opened for review but not merged: the operator
   reviews before anything lands on `main` of the production app.

## 1. Problem statement

When the Foundation removes a borrower from the archcontroller (default or
Terms of Use violation), wildcat-app-v2 must restrict that borrower's UI:
no new market creation, no borrower profile editing, no market description
editing. Debt repayment and market termination stay fully enabled so the
borrower can wind down. The removal state is persisted as a flag that flips
once on removal rather than being re-derived onchain on every load; backend
or RPC downtime never re-enables a restricted borrower. Admins can set or
clear a manual override that takes precedence over the onchain-derived state,
and each restriction fires an internal Slack notification.

A working prototype means: the restriction state machine and its persistence
exist with tests; the three surfaces are gated client-side and their API
routes enforce the same rule server-side; repay and terminate provably carry
no new gate; an admin toggle exists in the admin panel. Proof commands:
`npx jest src/utils/borrowerRestrictionState.test.ts src/app/api/borrowers`
plus `npx tsc --noEmit`, and the stacked PRs as the demo path.

## 2. Prior art

- ToU re-acceptance lockout, the structural template: pure state machine
  `src/utils/serviceAgreementState.ts` (with `TOU_BLOCKED_STATES` and the
  "withdrawals are never blocked" carve-out comment), server gate
  `src/lib/serviceAgreement.ts:381` exposed at `/api/sla/[address]`, client
  gate `src/hooks/useNetworkGate.ts`, full-page block in
  `src/app/[locale]/borrower/create-market/page.tsx:833-893`.
- Registration checks: `src/hooks/useIsRegisteredBorrower.ts` (client view
  call), `src/lib/db.ts:97-118` (server view call persisting
  `registeredOnChain`/`registeredBy` once, the set-once precedent),
  `src/app/api/invite/route.ts:104-124`.
- Existing switches to reuse: `hideCreateMarket` in
  `src/app/[locale]/borrower/hooks/useBorrowerInvitationRedirect.ts`;
  `isBorrower` prop on `BorrowerMarketSummary`; `disabled` pattern in
  `EditProfileForm`.
- Admin surface: `src/app/[locale]/admin/page.tsx`, `BorrowersTable` +
  `EditBorrowerModal`, auth via `verifyApiToken` / `isAdminForChain`
  (`src/app/api/auth/verify-header.ts`), `AdminAccount` Prisma model.
- Server enforcement points: `src/app/api/profiles/updates/route.ts` (POST),
  `src/app/api/market-summary/[market]/route.ts` (POST).
- Pure-logic test template: `src/utils/serviceAgreementState.test.ts`.
- Sister ticket #786 covered deposit/borrow buttons; no removed-borrower
  gating exists in the repo today.

## 3. Constraints and non-goals

- Base: `main` of wildcat-finance/wildcat-app-v2 at v2.19.0; run branch
  `shoggoth/issue-789-restrict-removed-borrowers`; Conventional Commits
  enforced by commitlint; exact-pinned dependencies only.
- The Prisma migration is written but not applied to any environment from
  here; it ships as a normal `prisma/migrations` entry for their deploy flow.
- Non-goals: the Telegram/public lender notification (the ticket marks it a
  separate sub-issue); any archcontroller event indexer or cron (no cron
  infrastructure exists in the repo); fixing the subgraph's
  `handleBorrowerRemoved` bug (separate repo); merging to `main`.

## 4. Design options

1. **Client-only gating from the onchain view.** Smallest diff, but violates
   the ticket directly: re-checks onchain on every load, downtime re-enables
   the borrower, nothing persists, no server enforcement. Rejected.
2. **Persisted flag on `Borrower` plus a self-verifying sync route, mirror of
   the ToU gate.** Chosen. New Prisma fields on `Borrower` (removal flag,
   timestamps, manual override), a pure state machine in `src/utils`, one
   API namespace `/api/borrowers/[address]/restriction` (GET read, POST
   self-verifying sync, PUT admin override), server-side enforcement in the
   two write routes, and client gating that reuses the ToU gate's shapes.
   Trade named: the flag flips when the sync route is poked (client signal
   or admin action), not the instant the onchain event fires; there is no
   indexer here, and the ticket's own design (set-once flag) accepts this.
3. **Subgraph-event-driven indexer.** Real-time, but the subgraph removal
   event is broken (prior art above), and the repo has no indexer or cron
   home; building one is out of prototype scope. Rejected.

## 5. Risk register seed

- **Sync route abuse.** POST sync takes an address, so it must verify
  onchain itself (server provider) before writing, never trust the caller,
  rate-limit by being idempotent, and validate address shape and chainId.
- **Auth on the override.** PUT must require `verifyApiToken` +
  `isAdminForChain`, the repo's canonical admin check; 401/403 idiom.
- **Fail-closed semantics.** Restricted state must survive backend or RPC
  downtime: client caches last-known state (persisted slice) and only a
  successful authoritative read may clear it. Never re-enable on error.
- **Server-side enforcement, not just UI.** Profiles-update POST and
  market-summary POST must reject restricted borrowers (admin exempt for
  profile route per its existing admin path); UI gating alone is bypassable
  with curl.
- **Carve-out regression.** Repay and terminate must not acquire the gate;
  a mechanical test pins their components clean of the new hook.
- **Webhook secret.** `SLACK_WEBHOOK_URL` is a server env var, never sent to
  the client, never logged; webhook failures must not fail the state write.
- **Migration safety.** New columns nullable/defaulted so the migration is
  additive and reversible.

## 6. Glossary seeds

- Restriction state: one of `unrestricted`, `removed` (onchain-derived,
  persisted), `manual` (admin override), computed by the pure state machine.
- Sync: the self-verifying server action that reads the archcontroller view
  and persists a transition, notifying Slack on restriction.
- Override: admin-set value (`restricted` or `cleared`) that beats the
  onchain-derived flag in the computed state.
- Carve-out: repay and terminate, never gated by restriction.

## 7. Sources

- Ticket: https://github.com/wildcat-finance/product/issues/789 (and #786
  context in its body).
- Codebase map from the exploration pass (paths cited inline above).
- `src/lib/registrar.ts:83-88` for the subgraph removal bug.
- Operator directive (this session): stacked PRs for review, no merge.

## Boundaries

- **Always.** `npx jest <new and touched suites>` and `npx tsc --noEmit`
  before every commit; the imprimatur lint on every shipped document;
  Conventional Commit format on every commit.
- **Ask first.** Any new dependency (none planned); applying the migration
  anywhere; widening the sync route beyond the single restriction concern;
  merging anything to `main`.
- **Never.** Trust caller-supplied restriction state; ship the webhook URL
  or any env var to the client; gate repay or terminate; delete or weaken a
  failing test; claim a suite ran when it did not.

## Success criteria

1. `npx jest src/utils/borrowerRestrictionState.test.ts` passes: the state
   machine covers removed, re-registered, override-restricted,
   override-cleared, and unknown-input cases.
2. `npx jest src/app/api/borrowers` passes: route guards (auth, address and
   chain validation, self-verification, idempotence) tested without a live
   database via mocked prisma and provider.
3. `npx tsc --noEmit` clean on every step branch.
4. Grep-level proof that RepayModal and TerminateMarket import no
   restriction gate, pinned by a test.
5. Client: create-market page, profile edit, and market description editor
   render their blocked state when the restriction hook reports restricted;
   the three entry points hide or disable.
6. Admin: EditBorrowerModal exposes the override toggle wired to PUT.
7. Stacked PRs open against the run branch with the audit log; no merge to
   `main` from this run.
