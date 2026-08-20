# Console demo transcript: loop 1 (#789)

Operated live in the Claude Code browser pane on 2026-08-19, server started via
`python3 bin/console.py` (launch config `.claude/launch.json`, port 8737).

## Part 1: viewing (before the #789 loop)

- Dashboard loaded at http://localhost:8737: 76 candidates in scope
  (Icebox + Product Backlog), 0 excluded, health ages in the header.
- Clicked the "Refresh board" button: the fetch and fetch-pipelines
  subprocesses ran to completion; the header age dropped from "board 39m ·
  pipelines 25m" to "board 4s · pipelines 0s".
- Opened ticket detail for #761, #727 (its comment "Not important for now,
  iceboxed." renders, useful ranking signal), and #789. Body, acceptance
  criteria, author, pipeline, and GitHub link all render as text.
- Expanded loop-1-ranking-scoped.md in the rankings panel; the winner line
  (#789 at 86/100) is readable in the page.
- Captured roster text: see roster-capture.txt beside this file.

## Part 2: administration (after the #789 loop)

Recorded below once loop 1 closes: exclusion of #789 via the detail form and
an archive cut via the header button.

Completed 2026-08-19 ~03:16 UTC:

- Opened #789 detail from the roster, entered the exclusion reason
  ("loop 1 complete: stacked PRs #367-#370 open on wildcat-app-v2 ..."),
  clicked "Exclude #789": the roster dropped to 75 candidates / 1 excluded
  and #789 left the list without a reload.
- Clicked "Cut archive": status bar reported
  loops/archives/shoggoth-20260819-031646.zip, confirmed on disk (52KB, includes
  the issue-789 deliverables).
- Every action in this demo ran through the console UI in the browser pane;
  the equivalent curl checks are recorded alongside in roster-capture.txt.
