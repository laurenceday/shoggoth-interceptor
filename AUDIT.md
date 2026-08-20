# Audit log: shoggoth operator console

> **Scope:** This file records implementation review rounds for the operator
> console. It is not a protocol security audit, an external audit report, or
> the per-ticket audit record produced during a Fiat delivery. Those ticket
> records stay with their other material under `loops/deliverables/`.

## Step 1, round 1 - 2026-08-19

Suite: waived (no Solidity); bundled lints ran per audit-loop non-Solidity rule.

| id | severity | file | finding | status |
| --- | --- | --- | --- | --- |

Findings: 0. phylax exit 0, ephoros exit 0, hypomnema exit 0 over
tests/test_smoke.py, bin/shoggoth.py, docs/*, README.md. Manual review against
the risk register: step ships docs and one import-only smoke test; no
subprocess, no rendering surface, no secret handling introduced.

Leads not pursued: none

## Step 2, round 1 - 2026-08-19

Suite: waived (no Solidity); bundled lints ran.

| id | severity | file | finding | status |
| --- | --- | --- | --- | --- |

Findings: 0. phylax exit 0 (bin/console.py, tests/test_api.py), ephoros exit 0,
hypomnema exit 0. Manual review: JSON-only responses with nosniff, integer-bound
issue paths, no subprocess, no secret reads, 127.0.0.1 bind, no state writes.
Test test_no_secret_material_in_responses guards the secret boundary.

Leads not pursued: none

## Step 3, round 1 - 2026-08-19

Suite: waived (no Solidity); bundled lints ran (all exit 0).

| id | severity | file | finding | status |
| --- | --- | --- | --- | --- |
| S3-R1-01 | low | bin/console.js | GitHub link href taken from board data without scheme/host validation; a hostile html_url could carry a javascript: URI (CSP mitigates, defence in depth missing) | fixed on --audit branch |
| S3-R1-02 | medium | bin/console.py | No Host header pinning; a DNS-rebound origin becomes same-origin with 127.0.0.1:8737 and bypasses the preflight guard | fixed on --audit branch |

Findings: 2. Fixes: client renders the GitHub link only for https://github.com/
URLs; server rejects any request whose Host is not 127.0.0.1 or localhost, with
a host_allowed unit test covering rebinding shapes.

Leads not pursued: none

## Step 3, round 2 - 2026-08-19

Suite: waived (no Solidity); bundled lints re-ran against the fixed tree.

| id | severity | file | finding | status |
| --- | --- | --- | --- | --- |

Findings: 0. phylax, ephoros, hypomnema all exit 0; 20 tests green. Re-review of
the round 1 fixes: Host pinning splits on the last colon (IPv6 literals are out
of scope while the bind is 127.0.0.1), and the link guard renders no anchor at
all for a non-GitHub URL.

Leads not pursued: none

## Step 4, round 1 - 2026-08-19

Suite: waived (no Solidity); bundled lints ran per the non-Solidity rule.

| id | severity | file | finding | status |
| --- | --- | --- | --- | --- |

Findings: 0. phylax, ephoros, hypomnema all exit 0. The step ships demo
evidence and a launch config only; no new code surface. The demo itself
exercised refresh, detail, exclude, and archive against the live server with
the results recorded in loops/deliverables/console-demo/.

Leads not pursued: none

# Run: console loop launcher

## Step 1, round 1 - 2026-08-19

Suite: waived (no Solidity); bundled lints ran (all exit 0); 25 tests green.

| id | severity | file | finding | status |
| --- | --- | --- | --- | --- |

Findings: 0. Manual review: only the two hard-coded prompts can be launched
and a test proves request data never reaches argv; one-launch-at-a-time is
enforced through pidfiles with a liveness check; spawned sessions run under
acceptEdits so they cannot self-approve broader actions; loop logs are
gitignored; the launch endpoint sits behind the existing Host pinning and
custom-header preflight guard.

Leads not pursued: a launched session inherits the operator's environment
by design (it needs the board keys and gh to work a loop); accepted and
documented in the shipped spec.

## Step 2, round 1 - 2026-08-19

Suite: waived (no Solidity); bundled lints ran (all exit 0); 25 tests green.

| id | severity | file | finding | status |
| --- | --- | --- | --- | --- |

Findings: 0. The step ships demo evidence only. The smoke launch itself ran
end to end from the page: spawn, pidfile, running status in /api/loops, the
expected SHOGGOTH-SMOKE-OK marker in the log, and the finished status
surviving a server restart.

Leads not pursued: none
