# Shoggoth guardrails

The full operating contract lives in [`CLAUDE.md`](../CLAUDE.md). This page
pulls together the write controls that apply before the Shoggoth sends work to
GitHub.

## Protected boundary

The Shoggoth cannot modify, rename, delete, disable, replace, or bypass
[`bin/repository-gate.py`](../bin/repository-gate.py) or
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
2. [`bin/repository-gate.py`](../bin/repository-gate.py) reads the local policy
   under `.loops/`, falling back to the default-deny
   [`state/guardrails.json`](../state/guardrails.json). The policy names
   protected organisations and, per organisation, the repositories exempt from
   that protection. A repository in a protected organisation is denied unless
   recorded as exempt; an organisation the policy does not name is permitted.
   Every write requires the GitHub login recorded during setup, nothing is
   permitted before consent is recorded, and a merge is refused on every
   target.
3. Pull requests go through
   [`bin/shoggoth-pr.sh`](../bin/shoggoth-pr.sh). The wrapper verifies the
   protected files and runs the same gate before calling `gh pr create`.

Consent goes through `init`, the only writer of policy:
`python3 bin/repository-gate.py init protect ORG` write-protects an
organisation and `python3 bin/repository-gate.py init exempt ORG/REPO` exempts
one repository inside it. Answering no grants nothing, and a policy widened by
hand-editing the JSON fails validation.

The gate refuses merges, but a pre-push hook cannot stop one: `gh pr merge` is
an API call, not a push. The prohibition is enforced by branch protection on
the protected organisation's repositories requiring a human review, configured
by the operator on GitHub; until that is in place it is stated policy only.

When the gate denies a write, the work stays local under `.loops/` for the
operator to review. The Shoggoth must not use `--no-verify`, raw pushes, raw
pull-request commands, replacement scripts, or alternate paths to get around
the decision.
