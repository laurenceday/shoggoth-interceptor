# Shoggoth guardrails

The full operating contract lives in [`CLAUDE.md`](../CLAUDE.md). This page
pulls together the write controls that apply before the Shoggoth sends work to
GitHub.

## Protected boundary

The Shoggoth cannot modify, rename, delete, disable, replace, or bypass
[`bin/wildcat-gate.sh`](../bin/wildcat-gate.sh) or
[`bin/install-guardrails.sh`](../bin/install-guardrails.sh). Their hashes are
pinned by [`bin/verify-gate.py`](../bin/verify-gate.py), and the repository
workflow checks those hashes and the required references.

Only a human maintainer acting outside the Shoggoth may change either protected
file or its pinned digest.

## Write path

1. Every cloned work repository runs
   [`bin/install-guardrails.sh`](../bin/install-guardrails.sh). It verifies the
   protected files, then installs the gate as the clone's pre-push hook.
   Worktrees inherit that hook.
2. [`bin/wildcat-gate.sh`](../bin/wildcat-gate.sh) reads
   [`state/guardrails.json`](../state/guardrails.json) and decides whether the
   current GitHub identity may push to the target repository.
3. Pull requests go through
   [`bin/shoggoth-pr.sh`](../bin/shoggoth-pr.sh). The wrapper verifies the
   protected files and runs the same gate before calling `gh pr create`.

The gate applies to `wildcat-finance/*`, apart from
`wildcat-finance/skills`. Repositories owned by other users and organisations
are unaffected.

When the gate denies a write, the work stays local under `.loops/` for the
operator to review. The Shoggoth must not use `--no-verify`, raw pushes, raw
pull-request commands, replacement scripts, or alternate paths to get around
the decision.
