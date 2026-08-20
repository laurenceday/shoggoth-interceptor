# Shoggoth Interceptor

![Meet our new full-stack developer.](assets/shoggoth-2-1.png)

The issues are full. The loop is hungry.

Shoggoth reads configured GitHub repositories, ranks eligible issues, and takes
them one at a time through a Fiat delivery. Deliverables stay local unless the
repository policy permits a pull request. Then it starts again.

The whole loop protocol, including the sharp edges, lives in `CLAUDE.md`.

<div align="center">
  <video src="https://github.com/user-attachments/assets/87e15a1f-874d-4150-88bf-e6063cb20a2a"></video>
  
  Shoutout to [@banteg](https://github.com/banteg) for what remains the best music video of the year
</div>

*"So watching the automation choose to work on something and start pushing
PRs... on the one hand, that's how the big players are doing things now... it
was... ‘oh, this thing is now in our space’."* - [@Kethic](https://github.com/kethcode)

## What's lurking in here

- `config/resolver.json` names GitHub sources, selectors and target routes.
- `bin/shoggoth.py` knows `fetch`, `roster`, `show <owner/repo#n>`,
  `target`, `exclude`, and optional `fetch-pipelines` metadata.
- `bin/console.py` gives the operator a window into the loop.
- `bin/archive.sh` cuts a rolling local zip under `.loops/archives/`.
- [`docs/guardrails.md`](docs/guardrails.md) explains the
  `bin/repository-gate.py`, `bin/install-guardrails.sh`, and `bin/shoggoth-pr.sh`
  chain. The gate and its installer are fixed boundaries.
  The Shoggoth may neither change nor bypass either file.
- `bin/migration-check.sh` spins up disposable Docker Postgres, applies every
  Prisma migration from zero, and checks the result against `schema.prisma`.
  Any loop that touches `prisma/` must run it.
- `.loops/` holds issue state, rankings, ticket deliverables, run logs,
  working clones, and local archives in one place.
- `docs/console-study.md` and `docs/console-runbook.md` hold the console spec.

## One operator. One console.

Run it locally:

```bash
python3 bin/console.py
```

Then open http://127.0.0.1:8737. The console shows the configured repository
roster, rankings, issue details and comments, deliverables, and exclusions.

The console binds to `127.0.0.1` and nowhere else.

It writes nothing to the issue tracker. External access stays in the 
command-line issue reader.

## First-run write policy

Everything is denied until the operator records consent. The operator names a
protected organisation, then any repositories inside it exempt from that
protection:

```bash
python3 bin/repository-gate.py init protect OWNER
python3 bin/repository-gate.py init exempt OWNER/REPO
```

Each question records the active GitHub login and writes the local policy
under `.loops/`. Every repository in a protected organisation remains
off-limits except the recorded exemptions; organisations the policy does not
name are permitted, always bound to the recorded login. The gate refuses every
merge outright — pull requests only, merged by a human after review.

## Hexaemeron and the Promise Machine

The loop does not improvise. Every issue goes through Hexaemeron's Fiat
delivery: study, runbook, then per-step implementation, audit, prose and push.
Each step is green at both ends, each one arrives as its own pull request, and
the receipts stay in `.loops/deliverables/issue-<owner>-<repo>-<n>/` where an
operator reads what was actually run. A phase without a receipt did not happen.

Six phase skills hold the parts of that loop to their own contracts.
`protasis` decides what a study must answer before code is allowed to exist.
`phylax` names every boundary a step opens and the control that closes it.
`ephoros` says what the step must emit once it runs unattended. `metron`
refuses a speed-motivated change with no recorded before and after. `elenchus`
works a failure down to its cause and leaves a guard behind it. `hypomnema`
decides what gets written down and where it lives. The loop cannot skip one:
the controller emits a single directive at a time and takes a receipt for each.

Above all of them sits the Promise Machine, `promise-machine/v1`, the contract
governing every skill in the suite. Its law is one sentence: no skill may claim
more than its evidence establishes, or authorise a more consequential
transition than that evidence warrants. Every operation declares a bounded
promise, the evidence behind it, and the nearest overclaim that evidence will
not carry. Transitions are graded by consequence. A repository mutation wants
tests, negative evidence and a recoverable change; a deployment or a security
conclusion wants a fail-closed gate, recorded authority and independently
inspectable evidence, and may never rest on model judgement. Missing, stale or
mismatched evidence fails closed with the recovery path still open.

That is the point of the thing. A Shoggoth pull request carries its own
evidence and is forbidden from overstating it: an unexplained strengthening of
a claim is a conformance failure, not a matter of taste. It does not pretend
the code has been proven, and the contract is candid about that too, which is
exactly why the rest of it can be taken at face value.

**The local gates.** Enforced here, whatever the loop believes:
`bin/repository-gate.py` decides whether a push or pull request against the
exact target is allowed, denies every repository in a protected organisation
that is not recorded as exempt, denies everything before consent is recorded,
and refuses merges outright. `bin/install-guardrails.sh` installs it as a pre-push
hook on every clone, and neither file is within the Shoggoth's authority to
change. While the policy denies writes, work lands as worktree branches and
patch files for the operator rather than as a widened policy. Any loop touching
`prisma/` runs `bin/migration-check.sh` from zero against a disposable
Postgres.

## Check the exits

```bash
python3 -m unittest discover -s tests
```
