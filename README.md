# Shoggoth Interceptor

https://github.com/user-attachments/assets/87e15a1f-874d-4150-88bf-e6063cb20a2a

The board is full. The loop is hungry.

Shoggoth reads the Wildcat ZenHub Product Planning board, ranks the open
tickets, and takes them one at a time through a Fiat delivery. Deliverables
stay local. The ticket goes on the exclusion list. Then it starts again.

The whole loop protocol, including the sharp edges, lives in
[CLAUDE.md](CLAUDE.md).

## What's lurking in here

- `bin/shoggoth.py` reads the board. It knows `fetch`, `fetch-pipelines`,
  `roster`, `show <n>`, `exclude <n> <reason>`, and `excluded`.
- `bin/console.py` gives the operator a window into the loop.
- `bin/archive.sh` cuts a rolling zip of the scratchpads, deliverables, and
  state.
- `bin/wildcat-gate.sh` stops pushes and pull requests to
  `wildcat-finance/*`, apart from `skills`, unless the shoggoth GitHub
  credential is recorded in `state/guardrails.json`.
- `bin/install-guardrails.sh` installs that gate as a pre-push hook in a
  clone. Its worktrees inherit the hook. Every loop installs it during the
  clone step.
- `bin/shoggoth-pr.sh` is the only sanctioned route to a pull request. It
  runs the gate before `gh pr create`.
- `bin/migration-check.sh` spins up disposable Docker Postgres, applies every
  Prisma migration from zero, and checks the result against `schema.prisma`.
  Any loop that touches `prisma/` must run it.
- `state/` remembers the board, pipeline map, and exclusion list.
- `deliverables/` keeps each ticket's output until an operator attaches it to
  the issue by hand.
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

The console binds to `127.0.0.1` and nowhere else. It reads no credentials and
writes nothing to GitHub or ZenHub. Only `bin/shoggoth.py` touches `.env`.

## Bring your own keys

- `.env` needs `WILDCAT_ZENHUB_READ_ONLY_PAT`, a fine-grained GitHub token
  with read access to `wildcat-finance/product`, and `ZENHUB_API_KEY`, a
  ZenHub GraphQL personal key for the Product Planning workspace.
- Agent ticket loops need a `gh` login with push access. The console never
  uses it.

## Check the exits

```bash
python3 -m unittest discover -s tests
```
