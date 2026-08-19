# Audit log: fixed-term termination reason (product#538)

## Step 1, round 1 — 2026-08-19

Suite: waived (no Solidity); bundled lints ran per the non-Solidity rule
(phylax, ephoros, hypomnema all exit 0); jest 11 passed; tsc exit 0; eslint
0 errors.

| id | severity | file | finding | status |
| --- | --- | --- | --- | --- |

Findings: 0. Manual review against the risk register: the helper keys on the
SDK status alone and never re-derives closability from raw config (the
allowTermReduction-off-Sepolia divergence risk); fixed-term details are only
attached for a FixedTerm hooks kind; every CloseMarketStatus value is pinned
to a flow by a test, so a future SDK enum addition fails the suite loudly at
type level (the routing type is exhaustive over the imported enum).

Leads not pursued: none

## Step 2, round 1 — 2026-08-19

Suite: waived (no Solidity); bundled lints ran (all exit 0); jest src/utils
44 passed; tsc exit 0; eslint 0 errors (one pre-existing-pattern
exhaustive-deps warning, matching the file's original hook).

| id | severity | file | finding | status |
| --- | --- | --- | --- | --- |

Findings: 0. Manual review: the blocked view offers no transaction path (a
Close action only), so a blocked status can never reach closeMarket(),
whose own SDK assertion remains the backstop; indebted markets still route
to the repay flow (pinned by tests); the flow now recomputes on preview
status changes rather than only on modal open; copy comes from i18n keys
aligned with the parameters table's early-closure vocabulary.

Leads not pursued: the repay flow's own hardcoded English strings and its
unexplained UnpaidWithdrawalBatches state predate this ticket and stay as
they are; noted for a possible copy-cleanup ticket.
