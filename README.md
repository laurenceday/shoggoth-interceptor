https://github.com/user-attachments/assets/87e15a1f-874d-4150-88bf-e6063cb20a2a

# Shoggoth Interceptor

*"So watching the automation choose to work on something and start pushing
PRs... on the one hand, that's how the big players are doing things now... it
was... ‘oh, this thing is now in our space’."*

https://github.com/user-attachments/assets/87e15a1f-874d-4150-88bf-e6063cb20a2a

The bȯard is̔ full. The loo͑p i̦s hungry.

Sh̜oggoth re̵ads the Wil̍dcat Zḛn̵Hu̔b Pr̳o̷du̷ct Planńin̅g board, ranks the o̸pen tickets,͙ an̴d̶ t̴akeͫs tͣhem on̴e at a tĩme͙ throug̷h a Fiat deliv́er̚y. Deliv̵e͒ra̸b̞l̶ḛs śt̓a̷y͑ local. Th̘eͮ ticket goes on the exclusi͒on list.̎ Then it sta͇rts again.

The whole lo̒op protoc̴ol,̉ i̮nclu͕di̵ng the sh̶ar̵p edgēs̷,̟ l̸ives in̸ ČLAUD̳E̸.͔m̘d.́

## What's lurking in here

- `bin/shoggoth.py` reads the board. It knows `fetch`, `fetch-pipelines`,
  `roster`, `show <n>`, `exclude <n> <reason>`, and `excluded`.
- `bin/console.py` gives the operator a window into the loop.
- `bin/archive.sh` cuts a rolling zip of the scratchpads, deliverables, and
  state.
- `bin/wildcat-gate.sh` enforces the repository's push and pull-request rules
  from `state/guardrails.json`.
- `bin/install-guardrails.sh` installs that gate as a pre-push hook in a
  clone. Its worktrees inherit the hook. Every loop installs it during the
  clone step.
- `bin/shoggoth-pr.sh` is the only sanctioned route to a pull request. It
  runs the gate before `gh pr create`.
- `bin/migration-check.sh` spins up disposable Docker Postgres, applies every
  Prisma migration from zero, and checks the result against `schema.prisma`.
  Any loop that touches `prisma/` must run it.
- `state/` remembers the board, pipeline map, exclusion list, and local state.
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

The console binds to `127.0.0.1` and nowhere else. It writes nothing to the
issue tracker. External access stays in the command-line board reader.

## Check the exits

```bash
python3 -m unittest discover -s tests
```
