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

Everything is denied until the operator names one sandbox repository:

```bash
python3 bin/repository-gate.py init OWNER OWNER/SANDBOX
```

The question records the active GitHub login and writes the local policy under
`.loops/`. Every other repository in that organisation remains off-limits.

## Check the exits

```bash
python3 -m unittest discover -s tests
```
