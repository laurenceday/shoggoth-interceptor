# Audit log: deposit max button (product#608)

## Step 1, round 1 — 2026-08-19

Suite: waived (no Solidity); bundled lints ran per the non-Solidity rule
(phylax, ephoros, hypomnema all exit 0); jest 5 passed; tsc exit 0; eslint
0 errors.

| id | severity | file | finding | status |
| --- | --- | --- | --- | --- |

Findings: 0. Manual review against the risk register: the display string
comes only from the SDK's truncating format (no rounding, no commas); the
exact value is honoured solely while the input equals the filled string, so
a stale exact amount cannot survive a manual edit even if a caller forgets
to clear it; zero max returns null so the control has nothing to fill.

Leads not pursued: none

## Step 2, round 1 — 2026-08-19

Suite: waived (no Solidity); bundled lints ran (all exit 0); jest src/utils
39 passed; tsc exit 0; eslint 0 errors (1 pre-existing-pattern
exhaustive-deps warning on the parse memo, same shape the file already
had).

| id | severity | file | finding | status |
| --- | --- | --- | --- | --- |

Findings: 0. Manual review: the fill can never exceed the depositable value
(the string is the SDK's truncating format and the exact amount is the SDK
value itself); the approve path uses the same effective amount as the
deposit, so approval covers the exact value; every reset path is covered by
the input-equality guard even where the exact state is not explicitly
cleared; the control hides on a zero maximum, matching the modal's existing
disable conditions.

Leads not pursued: the modal's on-screen strings remain hard-coded English
despite matching i18n keys existing; pre-existing, noted for a copy-cleanup
ticket alongside the same finding from the #538 loop.
