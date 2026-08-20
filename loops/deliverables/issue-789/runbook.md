# Runbook: restrict removed borrowers (product#789)

Derived from `.hexaemeron/study.md`. Four steps, one stacked pull request
each, on `shoggoth/issue-789-restrict-removed-borrowers`. Every exit is a
command. The stack is opened for review and not merged (study assumption 5).

## Step 1: State machine, schema, and committed spec

**Goal.** The restriction domain exists: pure state machine, Prisma fields,
db helpers, and the spec committed to the repo.
**Entry.** `shoggoth/issue-789-restrict-removed-borrowers` at the cut of
`main`.
**Exit.** `npx jest src/utils/borrowerRestrictionState.test.ts` green;
`npx tsc --noEmit` clean; `npx prisma validate` clean.
**Files.** `src/utils/borrowerRestrictionState.ts` (+ `.test.ts`),
`prisma/schema.prisma` (Borrower: `removedFromArchController Boolean
@default(false)`, `removedAt DateTime?`, `restrictionOverride String?`,
`restrictionOverrideBy String?`, `restrictionOverrideAt DateTime?`),
`prisma/migrations/<ts>_borrower_restriction/migration.sql`, db helpers in
`src/lib/borrowerRestriction.ts`, `docs/borrower-restriction.md` (study and
runbook content merged into one shipped doc).
**Tests.** State machine: removed, re-registered auto-clear, manual
`restricted` beating onchain-cleared, manual `cleared` beating removal flag,
unknown/error input staying fail-closed. Expected 10 or more assertions.

## Step 2: Restriction API and server-side enforcement

**Goal.** The flag has a write path and the two write surfaces enforce it.
**Entry.** Step 1's exit state.
**Exit.** `npx jest src/app/api/borrowers src/utils/borrowerRestrictionState.test.ts`
green (prisma and provider mocked); `npx tsc --noEmit` clean.
**Files.** `src/app/api/borrowers/[address]/restriction/route.ts` (GET
computed state; POST self-verifying sync via archcontroller view with Slack
notify on restriction; PUT admin override via `verifyApiToken` +
`isAdminForChain`), `src/lib/slack.ts` (webhook util, no-op without
`SLACK_WEBHOOK_URL`), enforcement inserts in
`src/app/api/profiles/updates/route.ts` and
`src/app/api/market-summary/[market]/route.ts`, route tests.
**Tests.** Auth idiom (401/403), address and chainId validation, sync writes
only after its own onchain read, idempotence, auto-clear on re-registration
unless manual override, webhook failure not failing the write, enforcement
rejections in both write routes.

## Step 3: Client gating of the three surfaces

**Goal.** Restricted borrowers see the three surfaces blocked; repay and
terminate stay untouched.
**Entry.** Step 2's exit state.
**Exit.** `npx jest src/hooks/useBorrowerRestriction.test.tsx
src/utils/borrowerRestrictionState.test.ts src/utils/restrictionCarveOut.test.ts`
green; `npx tsc --noEmit` clean.
**Files.** `src/hooks/useBorrowerRestriction.ts` (+ test): tanstack query on
GET restriction with a redux-persisted last-known slice
(`src/store/slices/borrowerRestrictionSlice`), fail-closed on error;
create-market block in `src/app/[locale]/borrower/create-market/page.tsx`
(mirroring the ToU block panel) and `hideCreateMarket` branch in
`useBorrowerInvitationRedirect.ts`; profile-edit block in
`src/app/[locale]/borrower/profile/edit/page.tsx` and entry-button hide in
`ProfileNamePageBlock`; description-editor gate in
`BorrowerMarketSummary` (`isBorrower && !restricted`); i18n strings in
`src/locales/en/en.json`.
**Tests.** Hook state transitions (restricted sticks on error), carve-out
test asserting RepayModal and TerminateMarket source contains no
restriction import, gating render conditions.

## Step 4: Admin override UI and demonstration

**Goal.** Admins can set or clear the override from the admin panel, and the
whole delivery is demonstrated.
**Entry.** Step 3's exit state.
**Exit.** `npx jest src/app/api/borrowers src/hooks/useBorrowerRestriction.test.tsx
src/utils/borrowerRestrictionState.test.ts src/utils/restrictionCarveOut.test.ts`
green; `npx tsc --noEmit` clean; stacked PRs open for review with the audit
log; deliverables summary written to the interceptor repo
(`loops/deliverables/issue-789/SUMMARY.md`).
**Files.** Override toggle in
`src/app/[locale]/admin/components/EditBorrowerModal` wired to PUT via a new
admin hook; `loops/deliverables/issue-789/` in the interceptor repo (summary,
study copy, operator instructions).
**Tests.** Admin hook fires PUT with token; modal renders current computed
state; full targeted suite re-run as the demonstration.
