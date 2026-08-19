# Runbook: shoggoth operator console

Derived from `.hexaemeron/study.md`. Four steps, one pull request each, stacked
on `fiat/shoggoth-operator-console`. Every exit is a command.

## Step 1: Scaffold and committed spec

**Goal.** The repo carries the spec, a test harness, and the console's skeleton
so every later step lands on a green tree.
**Entry.** `fiat/shoggoth-operator-console` at the run-branch cut of `main`.
**Exit.** `python3 -m unittest discover -s tests` reports 1 passing smoke test;
`docs/console-study.md` and `docs/console-runbook.md` exist and pass the
imprimatur lint.
**Files.** `docs/console-study.md`, `docs/console-runbook.md`,
`tests/__init__.py`, `tests/test_smoke.py`, README section for the console.
**Tests.** One smoke test asserting `bin/shoggoth.py` imports as a module and
its state paths resolve inside the repo.

## Step 2: Read-only API server

**Goal.** `bin/console.py` serves the board state as JSON over 127.0.0.1.
**Entry.** Step 1's exit state.
**Exit.** `python3 -m unittest discover -s tests` green (smoke + new API
tests, expected 8 or more assertions against fixture state); manual check
`curl -s 127.0.0.1:8737/api/roster` returns scoped candidates.
**Files.** `bin/console.py` (HTTP server, GET `/api/health`, `/api/roster`,
`/api/issue/<n>`, `/api/rankings`, `/api/excluded`, `/api/deliverables/<n>`),
`tests/test_api.py`, `tests/fixtures/*.json`.
**Tests.** Endpoint tests run the handler against fixture state files with no
network; assertions cover scope filtering, exclusion masking, unknown issue
404, and that responses never contain `.env` keys.

## Step 3: Mutations and the dashboard page

**Goal.** Operators can act: refresh the board, exclude a ticket, cut an
archive, all from one served HTML page.
**Entry.** Step 2's exit state.
**Exit.** `python3 -m unittest discover -s tests` green (POST endpoint tests
added); manual check: dashboard renders roster, ticket detail, rankings, and
the three actions respond with subprocess outcomes.
**Files.** `bin/console.py` (POST `/api/refresh`, `/api/exclude`,
`/api/archive`; GET `/` serving the page), `bin/console.html`,
`tests/test_mutations.py`.
**Tests.** POST tests use a stubbed subprocess runner: fixed argv asserted,
issue number validated as integer, reason length bounded, temp-then-rename on
`excluded.json`, board text rendered via text nodes only (no innerHTML of
board data).

## Step 4: Demonstrate on loop 1 (#789)

**Goal.** Prove the demo path from the study, for real, during loop 1 on
product#789.
**Entry.** Step 3's exit state.
**Exit.** `python3 -m unittest discover -s tests` green; demo evidence in
`deliverables/console-demo/` (screenshots plus a transcript note) showing:
console opened, roster and ranking viewed, #789 detail read, and, after the
789 loop closes, the exclusion recorded and an archive cut from the page.
**Files.** `deliverables/console-demo/*`, `docs/console-study.md` updated only
if the demo corrects it.
**Tests.** No new suites; the demo path is the check named by the study.
