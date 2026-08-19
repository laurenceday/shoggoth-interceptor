# Study: shoggoth operator console

Assuming, unless corrected:

1. The console runs locally, one instance per operator, bound to 127.0.0.1 only.
   Each operator brings their own checkout, `.env` keys, and `gh` login. There is
   no hosted deployment, no accounts, and no auth layer in this prototype.
2. Python 3.11+ stdlib only, matching `bin/shoggoth.py`. No package manager, no
   build step, no JavaScript framework; the dashboard is one served HTML page.
3. The console reads board state and writes only local state: the exclusion list
   and archive zips. It never writes to GitHub or ZenHub. Branches and pull
   requests stay in the agent's ticket loops, outside this tool.
4. Running a ticket loop remains the agent's job. The console is the operator's
   window and control panel: refresh the board, read rankings and deliverables,
   exclude finished tickets, cut archives. It does not drive the agent.

## 1. Problem statement

Wildcat runs a backlog-reduction loop over the ZenHub Product Planning board:
rank tickets, work one through a Fiat delivery, store deliverables locally,
exclude it, repeat. Today that state is a set of JSON files and a CLI that only the
agent's operator can comfortably read. Several operators need the same view
without touching a terminal: what is on the board and in which pipeline, what
the current ranking says, which tickets are done or excluded, what deliverables
exist for a ticket, and a way to record an exclusion and cut an archive.

The build is a small local web console over the existing `bin/shoggoth.py`
state. A working prototype means: an operator starts
`python3 bin/console.py`, opens `http://127.0.0.1:8737`, sees the scoped
roster with pipelines and rankings, opens a ticket's detail and deliverables,
triggers a board refresh, records an exclusion, and cuts an archive, all from
the page. The demo path is exactly that sequence, performed for real during
loop 1 on product#789 and checked by `python3 -m unittest discover -s tests`.

## 2. Prior art

- `bin/shoggoth.py` (this repo): fetch, fetch-pipelines, roster, show, exclude.
  The console shells out to it or imports it rather than duplicating logic.
- `state/board.json`, `state/pipelines.json`, `state/excluded.json`,
  `deliverables/*` (this repo): the data the console renders.
- `bin/archive.sh` (this repo): the rolling archive the console will trigger.
- ZenHub GraphQL API (`api.zenhub.com/public/graphql`): pipeline membership,
  already integrated; the board UI at app.zenhub.com remains the write surface.
- GitHub REST API v2022-11-28: issue and comment bodies, already integrated.
- `python3 -m http.server` family (stdlib `http.server`,
  `socketserver`): the serving mechanism, no third-party server.
- Organisation prior art: the Hexaemeron plugin supplies the delivery loop this
  console reports on; `wildcat-app-v2` is where ticket work lands. Neither
  contains an operator dashboard today.

## 3. Constraints and non-goals

- Starting ref: `main` of `laurenceday/shoggoth-interceptor` at the commit that
  contains `bin/shoggoth.py` with pipeline support. Run branch
  `fiat/shoggoth-operator-console`.
- Toolchain: Python 3.11+ stdlib; `zsh`-safe invocations; macOS host.
- The operator directive stands: candidates come from Icebox and Product
  Backlog, tech debt only, frontend first; the console encodes that scope as
  its default filter rather than hard-coding it.
- Non-goals for the prototype: ZenHub or GitHub writes, closing tickets,
  multi-operator concurrency on shared state, hosting, TLS, auth, agent
  orchestration, and any redesign of the ranking rubric. Ranking numbers come
  from committed ranking documents, not from the console recomputing scores.

## 4. Design options

1. **Static page published as a Claude Artifact.** No server, shareable link.
   Rejected: the page cannot read fresh board state, run the fetchers, or write
   the exclusion list; operators would be reading a snapshot.
2. **Python stdlib HTTP server, JSON API plus one HTML page.** Chosen. Zero new
   dependencies, reuses `shoggoth.py` directly, small enough to audit in one
   sitting. Trade named: no reactive framework, so the UI is plain fetch-and-
   render JavaScript, and concurrent mutation from two tabs is resolved by
   last-writer-wins on small JSON files.
3. **Node/React app.** Familiar dashboard stack, richer UI. Rejected: adds a
   toolchain and dependency surface the two-file design does not need, and the
   audit loop would spend its time on packaging rather than behaviour.
4. **TUI (curses).** Cheap, but the request is a website usable by several
   operators, some of whom will not live in a terminal.

Option 2 is the cheapest to comprehend that still meets the problem statement.

## 5. Risk register seed

The audit loop should look hardest at:

- **Untrusted input rendered in a browser.** Issue titles and bodies come from
  the board and are attacker-writable by anyone who can file a ticket. They
  must be rendered as text, never as HTML; the ticket instruction-boundary rule
  from CLAUDE.md applies to the console too.
- **Subprocess handling.** The console shells out to `shoggoth.py`,
  `archive.sh`, and nothing else: fixed argv lists, no shell interpolation, no
  request-derived arguments except a validated integer issue number and a
  bounded reason string.
- **Secret material.** `.env` holds two credentials. The console never reads
  them itself, never serialises them into a response, and never logs request
  bodies. Only `shoggoth.py` touches `.env`.
- **Network exposure.** Bind 127.0.0.1 explicitly; mutating endpoints are POST
  only; no CORS headers, so a hostile web page in the same browser cannot read
  responses. A same-site page can still fire blind POSTs, so mutations are
  limited to reversible local-state writes.
- **Partial writes.** `excluded.json` updates go through write-temp-then-rename.
  A killed archive run leaves at worst a stale zip, never corrupt state.
- **Observability (ephoros).** One access-log line per request and the exit
  code of every subprocess to stderr; `/api/health` reports state-file ages so
  an operator can see a stale board at a glance.

## 6. Glossary seeds

- Roster: open product-repo issues minus exclusions, with pipeline names.
- Pipeline map: ZenHub issue-to-column mapping in `state/pipelines.json`.
- Scope filter: Icebox and Product Backlog, tech debt, frontend first.
- Exclusion list: tickets no future loop may pick, with reasons.
- Loop: one ranked pick worked through a Fiat delivery to deliverables.
- Deliverable bundle: `deliverables/issue-<n>/` files the operator attaches.
- Archive: rolling zip from `bin/archive.sh`, newest ten kept.

## 7. Sources

- This conversation (2026-08-19) and the operator's board screenshot.
- `CLAUDE.md` in this repo: loop protocol, scope directive, hygiene rules.
- `deliverables/loop-1-ranking-scoped.md`: the ranking the console displays.
- ZenHub GraphQL public API documentation (developers.zenhub.com).
- GitHub REST issues API documentation (docs.github.com/rest/issues).

## Boundaries

- **Always.** Run `python3 -m unittest discover -s tests` before every commit.
  Run the imprimatur lint on every shipped document. Keep the console bound to
  127.0.0.1.
- **Ask first.** Adding any dependency. Binding any other interface. Adding an
  endpoint that writes anywhere beyond `state/` and `archives/`. Exposing agent
  or credential state in a response.
- **Never.** Serialise `.env` contents into a response or log. Render board
  text as HTML. Shell-interpolate request data. Claim a lint, test, or fetch
  ran when it did not.

## Success criteria

1. `python3 bin/console.py` starts a server on 127.0.0.1:8737 and logs it.
2. `curl -s 127.0.0.1:8737/api/roster` returns JSON whose default view lists
   only Icebox and Product Backlog candidates, excluded tickets absent.
3. `curl -s 127.0.0.1:8737/api/issue/789` returns title, body, comments,
   pipeline, and the deliverable file list for product#789.
4. POST `/api/refresh`, `/api/exclude`, `/api/archive` perform the fetch,
   exclusion, and archive actions and report subprocess outcomes truthfully.
5. `python3 -m unittest discover -s tests` passes with no network access,
   using fixture state files.
6. Demo path: the console is operated in a browser through loop 1 on
   product#789, ending with 789 excluded via the page and an archive cut.
