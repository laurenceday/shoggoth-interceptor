# Loop 4 — product#608: Max button on the deposit modal

Delivered 2026-08-19 as a stacked PR pair against `wildcat-app-v2`, opened
for review and deliberately not merged.

## One reading to confirm

The ticket says to fill "the user's balance in the underlying asset or the
remaining market capacity, whichever is greater". Implemented as
**lesser**, treating "greater" as a typo: the greater of the two can never
be deposited when they differ, and the SDK agrees; its
`marketAccount.maximumDeposit` is exactly `min(wallet balance, remaining
capacity)` and is what the button fills. If d1ll0n meant something else,
say so on the PR.

## What shipped

Run branch: `shoggoth/issue-608-deposit-max-button` (off `main`, own
worktree).

1. [PR #381](https://github.com/wildcat-finance/wildcat-app-v2/pull/381) —
   pure fill rules: truncating, parser-safe display string (the house
   comma-formatter would both break the parser and round up past the true
   balance); an exact `TokenAmount` behind the fill so the deposit and its
   approval use the true value with no five-decimal dust; zero maximum
   fills nothing.
2. [PR #382](https://github.com/wildcat-finance/wildcat-app-v2/pull/382) —
   the Max control in both input branches (desktop and mobile share the
   component), one handler, hidden when nothing is depositable, exact fill
   cleared by any manual edit; all existing validations (minimum deposit,
   allowance, ToU/agreement gates) run against the filled value.

Tests: 11 new (5 fill rules, 6 wiring pins); full `src/utils` suite 39
green; tsc and eslint clean. Audit log on the run branch: two clean rounds.

## Operator actions

1. Review and merge #381 then #382, then the run branch into `main`
   (state in `work/wildcat-app-v2-608/.hexaemeron`, `hexctl resume`).
2. Confirm the lesser/greater reading above on the ticket, then close
   #608.
3. Repeat flag (also raised in loops 2 and 3): the deposit modal's
   on-screen strings are hard-coded English despite matching i18n keys
   existing; one copy-cleanup ticket would cover the terminate, deposit,
   and repay modals together.
