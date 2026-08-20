# Runbook: general GitHub issue resolver

Derived from `docs/general-resolver-study.md`. Each step ends green.

## Step 1: Configuration and issue identity

**Goal.** Add the versioned source, selector, and route configuration and use
`owner/repo#number` across snapshots and exclusions.
**Entry.** `f77f527`; 56 tests pass.
**Exit.** Config validation and duplicate-number tests pass with legacy
single-repository state still readable.
**Files.** `config/resolver.json`, `bin/shoggoth.py`, resolver tests.
**Tests.** Valid and malformed config, ambiguous bare numbers, legacy state.
**Disciplines.** phylax: configuration and state cross trust boundaries;
hypomnema: identity is costly to reverse; elenchus: malformed-state guards.

## Step 2: Multi-repository GitHub intake and routing

**Goal.** Fetch configured repositories atomically, apply selectors, and resolve
implementation targets without requiring ZenHub.
**Entry.** Step 1 green.
**Exit.** Multi-repository, partial-fetch, hostile-shape, selector, and route
tests pass; a live read contains the source issue.
**Files.** `bin/shoggoth.py`, configuration, fixtures, tests.
**Tests.** Pagination bounds, response shape, incomplete snapshot, routes.
**Disciplines.** phylax: GitHub HTTP, credentials, and untrusted text; ephoros:
complete snapshot and issue count; elenchus: partial-fetch guard.

## Step 3: Organisation sandbox gate

**Goal.** Replace the Wildcat exception with first-run default deny and one
named sandbox tied to the active GitHub login.
**Entry.** Step 2 green and maintainer approval to replace the protected gate.
**Exit.** Setup yes records one sandbox; no records nothing; the sandbox passes;
unknown organisations, other repositories, and other logins fail.
**Files.** Repository gate, installer, verifier, PR wrapper, policy, docs, tests.
**Tests.** Policy shape, target normalisation, setup, decision, integrity drift.
**Disciplines.** phylax: mutation and credential boundary; hypomnema: write
authority; ephoros: bounded allow/deny reason; elenchus: old exception guards.

## Step 4: Console, documentation, and demonstration

**Goal.** Remove repository and pipeline assumptions from the operator surface
and demonstrate the complete local flow.
**Entry.** Step 3 green.
**Exit.** The console uses repository-qualified refs; 66 tests, gate integrity,
Phylax, compilation, diff, live fetch, and live gate demonstrations pass.
**Files.** Console, launcher prompt, README, operating contract, guardrail docs.
**Tests.** API, fixed argv, path containment, browser text sinks, live demos.
**Disciplines.** phylax: local HTTP, subprocess, and displayed hostile text;
ephoros: launch and result visibility; elenchus: environment failures stay
explicit; hypomnema: this study and runbook record the release boundary.
