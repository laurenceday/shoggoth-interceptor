# Shoggoth Interceptor

![Meet our new full-stack developer.](assets/shoggoth-2-1.png)

The bȯard is̔ full. The loo͑p i̦s hungry.

Sh̜oggoth re̵ads the Wil̍dcat Zḛn̵Hu̔b Pr̳o̷du̷ct Planńin̅g board, ranks the o̸pen tickets,͙ an̴d̶ t̴akeͫs tͣhem on̴e at a tĩme͙ throug̷h a Fiat deliv́er̚y. Deliv̵e͒ra̸b̞l̶ḛs śt̓a̷y͑ local. Th̘eͮ ticket goes on the exclusi͒on list.̎ Then it sta͇rts again.

The whole lo̒op protoc̴ol,̉ i̮nclu͕di̵ng the sh̶ar̵p edgēs̷,̟ l̸ives in̸ ČLAUD̳E̸.͔m̘d.́

<div align="center">
  <video src="https://github.com/user-attachments/assets/87e15a1f-874d-4150-88bf-e6063cb20a2a"></video>
  
  Shoutout to [@banteg](https://github.com/banteg) for what remains the best music video of the year
</div>

*"So watching the automation choose to work on something and start pushing
PRs... on the one hand, that's how the big players are doing things now... it
was... ‘oh, this thing is now in our space’."* - [@Kethic](https://github.com/kethcode)

## What's lurking in here

- `bin/shoggoth.py` reads the board. It knows `fetch`, `fetch-pipelines`,
  `roster`, `show <n>`, `exclude <n> <reason>`, and `excluded`.
- `bin/console.py` gives the operator a window into the loop.
- `bin/archive.sh` cuts a rolling local zip under `.loops/archives/`.
- [`docs/guardrails.md`](docs/guardrails.md) explains the
  `bin/wildcat-gate.sh`, `bin/install-guardrails.sh`, and `bin/shoggoth-pr.sh`
  chain. The gate and its installer are fixed boundaries.
  The Shoggoth may neither change nor bypass either file.
- `bin/migration-check.sh` spins up disposable Docker Postgres, applies every
  Prisma migration from zero, and checks the result against `schema.prisma`.
  Any loop that touches `prisma/` must run it.
- `.loops/` holds the board state, rankings, ticket deliverables, run logs,
  working clones, and local archives in one place.
- `docs/console-study.md` and `docs/console-runbook.md` hold the console spec.

## One operator. One console.

Run it locally:

```bash
python3 bin/console.py
```

Then open http://127.0.0.1:8737. The console shows the scoped roster from
Icebox and Product Backlog, with tech debt first. It shows rankings, ticket
details and comments, deliverables, and the exclusion list. From there an
operator can refresh the board, record an exclusion, or cut an archive.

The console binds to `127.0.0.1` and nowhere else.

It writes nothing to the issue tracker. External access stays in the 
command-line board reader.

## Hexaemeron and the Promise Machine

The lo̶op does not im̷prov̴ise. Every ticket goes through Hexaemeron's Fiat
delivery: study, runbook, then per-step implementation, audit, prose and push.
Each step is green at both ends, each one arrives as its own pull request, and
the receipts stay in `.loops/deliverables/issue-<n>/` where an operator reads
what was actually run. A phase without a receipt d̷i̶d not happen.

Six phase skills hold the parts of that loop to their own contracts.
`protasis` decides what a study must answer before code is allowed to exist.
`phylax` names every boundary a step opens and the control that closes it.
`ephoros` says what the step must emit once it runs unattended. `metron`
refuses a speed-motivated change with no recorded before and after. `elenchus`
works a failure down to its cause and leaves a guard behind it. `hypomnema`
decides what gets written down and where it lives. Th̘e loop cannot skip one:
the controller emits a single directive at a time and takes a receipt for each.

Ab̸ove all of them sits the Promise Machine, `promise-machine/v1`, the contract
governing every skill in the suite. Its l̷aw is one sentence: no skill may claim
more than its evidence establishes, or authorise a more consequential
transition than that evidence warrants. Every operation declares a bounded
promise, the evidence behind it, and the ne̶arest overclaim that evidence will
not carry. Transitions are graded by consequence. A repository mutation wants
tests, negative evidence and a recoverable change; a deployment or a security
conclusion wants a fail-closed gate, recorded authority and independently
inspectable evidence, and may never rest on model judgement. Missing, stale or
mismatched evidence fails closed with the recovery path still open.

That is th̷e point of the thing. A Shoggoth pull request carries its own
evidence and is f̶orbidden from overstating it: an unexplained strengthening of
a claim is a conformance failure, not a matter of taste. It does not pretend
the code has been proven, and the contract is candid about that too, which is
exactly why the r̵est of it can be taken at face value.

**The local gates.** Enforced here, whatever the loop believes:
`bin/wildcat-gate.sh` decides whether a push or pull request into a
`wildcat-finance/*` repository is allowed, `bin/install-guardrails.sh` installs
it as a pre-push hook on every clone, and n̶either file is within the
Shoggoth's authority to change. Any loop touching `prisma/` runs
`bin/migration-check.sh` from zero against a disposable Postgres. The console
binds to `127.0.0.1` and writes nothing to the issue tracker.

## Check the exits

```bash
python3 -m unittest discover -s tests
```
