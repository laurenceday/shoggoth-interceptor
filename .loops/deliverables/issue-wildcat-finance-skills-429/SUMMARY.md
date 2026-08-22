# Summary — wildcat-finance/skills#429

**Loop 6. Ranked and specified. No pull requests: the delivery controller could
not run in this session.**

Ticket: [fiat-wish — give the audit record a schema, a timestamp and a
synopsis](https://github.com/wildcat-finance/skills/issues/429).
Target: `wildcat-finance/skills`, which
`bin/repository-gate.py` permits as a recorded exemption.
Clone: `.loops/work/skills-429`, `main` at
`cbd7185d81500463488bd9f770d162493b0d1f0c`, guardrail pre-push hook installed.

## What happened

The board was refreshed (331 open issues, 4 repositories), the roster built (218
candidates), and every candidate scored. The ranking and its method are in
[../loop-6-ranking.md](../loop-6-ranking.md). #429 came top at 85: mechanically
testable acceptance criteria, a build order the ticket states itself, two issues
folded in (#368, #428), one unblocked (#369), and a gate-permitted target.

Then `/hexaemeron:fiat` could not start. `hexctl init` is a denied command in
this session, and so is every other controller call, so there is no run, no
receipt, and no branch beyond the clone's `main`.

What was done instead, with the tools that are permitted:

- **A measured baseline**, in [baseline.md](baseline.md). Both suites pass before
  any change: root 107/107, Hexaemeron 710/710. The six logs are sized and their
  round entries counted. Two of the ticket's three measurements reproduce; one
  does not, and the discrepancy is recorded rather than smoothed over.
- **A study**, in [study.md](study.md), answering all twelve Protasis items with
  three design options and the chosen one's trade named.
- **A runbook**, in [runbook.md](runbook.md), five steps in the ticket's build
  order, each with an exit a command can prove.

Both documents are drafts in the strict sense: no receipt exists for either, and
`protasis.py` — the mechanical check that settles whether the twelve items are
present — is also a denied command.

## Three things the operator should know

**1. The controller and every gate around it are denied commands.** This
session's allowlist (`.claude/settings.json`) permits `python3` only for
`bin/shoggoth.py`, `bin/repository-gate.py`, `bin/console.py` and
`python3 -m unittest`. Everything below returned *"This command requires
approval"* and was refused:

| Command | What it gates |
|---|---|
| `python3 …/skills/fiat/scripts/hexctl.py …` | the whole loop: `init`, `next`, `done`, `record`, `audit-round`, `verify` |
| `python3 …/skills/protasis/scripts/protasis.py …` | the study and runbook mechanical check |
| `python3 …/skills/phylax/scripts/phylax.py …` | the audit round's mechanical part |
| `python3 …/skills/ephoros/scripts/ephoros.py …` | the same |
| `python3 …/skills/hypomnema/scripts/hypomnema.py …` | the same |
| `python3 …/skills/imprimatur/scripts/imprimatur.py …` | the prose pass |
| `python3 plugins/hexaemeron/tests/run_tests.py` | the documented Hexaemeron suite command |

The plugin cache under `~/.claude/plugins/` is outside the session's working
directory, so the controller could not be read there either, by Bash or by the
file reader. The copy in the clone is reachable but not runnable.

`python3 -m unittest` is permitted, which is why a baseline exists at all.

**2. Nothing was pushed, and that was a choice, not only a consequence.** Git
push and `bin/shoggoth-pr.sh` are both permitted, so an implementation could
have been written, tested against the two suites, and opened as pull requests.
It was not. The audit round's three lints, the prose lint and every controller
receipt are unrunnable, so the pull requests would have carried no audit round
and no receipt — into the file that enforces audit rounds, in the substrate this
loop runs on. Fiat's honesty rule and CLAUDE.md's rigour floor both refuse that,
and a sandbox lowering the cost of being wrong does not lower the standard of
evidence.

**3. When the run is unblocked it will halt before `integrate`.** Fiat's
`integrate` phase merges the stack into the run branch and the run branch into
the base. CLAUDE.md's chains forbid every merge, everywhere, and outrank every
fiat directive. So the run will push five stacked pull requests, leave them open,
and halt on the ledger with that reason. The merges are the operator's, after
review. This is a standing conflict between the two documents, not something
this ticket introduced.

## What the operator should do next

1. **Add one allowlist entry** to `.claude/settings.json` and re-run the loop:

   ```json
   "Bash(python3 .loops/work/:*)"
   ```

   That scopes `python3` to the gitignored clone area and grants nothing inside
   the interceptor's own source. Drive the controller from the interceptor root
   with the `.loops/work/skills-429/…` prefix so the command text matches.
   Some of the tools above resolve paths from the current directory and need
   `cd` into the clone, in which case `"Bash(python3 plugins/:*)"` covers them —
   the interceptor has no `plugins/` directory, so that pattern can only ever
   resolve inside a clone. Neither entry touches the deny list or the protected
   files.

2. **Adopt the three documents as the run's spec.** They are written to be
   receipted as-is: `done study --artifact docs/fiat-audit-record-schema-study.md`
   after step 1 commits them. The one open question — which of two
   `Leads not pursued` figures the reference cites — is answered by segmenting
   the log per entry, which needs the scripting this session was denied.

3. **Note the ticket's one factual error before step 3.** It says `hexctl.py`
   has `utc_now()`. It has `now()`, at line 125, returning full ISO-8601 UTC. The
   precision the ticket says is discarded is real; only the name is wrong. A step
   written against `utc_now()` will not find it.

4. **Decide whether to exclude #429.** It has not been. Nothing was delivered
   against it, so excluding it would hide real work from the next loop; the
   ranking already records that it was selected, and
   `.loops/loop.json` still shows five completed loops. Run
   `python3 bin/shoggoth.py exclude wildcat-finance/skills#429 "<reason>"` only
   if you want it parked rather than picked up again.

## Not done

- No `hexctl` run, no receipts, no branches, no pull requests.
- No audit round, no prose pass, no ledger row.
- `python3 bin/shoggoth.py complete-loop 6` was not run: the pass is not
  complete.
