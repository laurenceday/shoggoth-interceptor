# Baseline — wildcat-finance/skills#429

Measured 2026-08-22 against `wildcat-finance/skills` at `cbd7185d81500463488bd9f770d162493b0d1f0c`
(clone at `.loops/work/skills-429`, `main` fast-forwarded to `origin/main`, tree clean).

## Suites

Both suites the ticket's last acceptance line names pass before anything changes.

| Suite | Command | Result |
|---|---|---|
| Root | `python3 -m unittest discover -s tests` | 107 tests, OK |
| Hexaemeron | `python3 -m unittest discover -s plugins/hexaemeron/tests` | 710 tests, OK |

The Hexaemeron figure is worth pinning: PR #431's body recorded 640, so 70 tests
have landed since. A later run quoting 640 would be quoting a stale number.

The documented Hexaemeron command is `python3 plugins/hexaemeron/tests/run_tests.py`,
which this session cannot run (see SUMMARY.md). Discovery over the same directory
was used instead. That substitution establishes that the discovered tests pass; it
does not establish that `run_tests.py` selects the same set, so a later run should
re-establish the baseline with the documented command.

## The six logs

| Log | Lines | Round headings |
|---|---|---|
| `audit/AUDIT.md` | 7732 | 310 |
| `plugins/probitas/audit/AUDIT.md` | 842 | 17 |
| `plugins/pandects/audit/AUDIT.md` | 696 | 16 |
| `plugins/ariadne/audit/AUDIT.md` | 466 | 21 |
| `plugins/tabularium/audit/AUDIT.md` | 262 | 13 |
| `plugins/hexaemeron/audit/AUDIT.md` | 71 | 2 |

Round headings counted as lines matching `^##+ .*round [0-9]+`. Total 379 across
the six.

The ticket was filed against 299 entries in the root log and 5,978 lines. It is
now 310 and 7,732. The estate moved, as the ticket said it would; the shape of
its argument survives the move.

## Field presence in the root log

Counted as line occurrences, not per-entry presence.

| Marker | Pattern | Lines | Against 310 rounds |
|---|---|---|---|
| Findings table header | `^\| *id *\|` | 210 | 68% |
| `Leads not pursued` | case-insensitive literal | 253 | 81% |
| Assumption or unknown named | `assumption|unknown|not checked|did not check` | 19 | 6% |

**What these do not establish.** A line count is an upper bound on per-entry
presence, not the presence itself: a round carrying two tables counts twice, and
one carrying none counts zero without the count saying which round it was. The
third row is weaker still — it counts any line mentioning an unknown, including a
finding whose prose happens to use the word, so 6% is an upper bound on the field
the ticket measured at 8%.

Two of the three reproduce the ticket's shape. The findings table lands at 68%
against its 66%, and the assumption field at 6% against its 8% — both within what
the change in denominator and the coarser method would explain. The leads line
does not: 81% here against 58% there. That gap is larger than the method
explains, so a later run should settle it by segmenting the log per entry rather
than counting lines, and record which of the two figures the schema is being
argued from. The design does not depend on the answer — the field is being made
required either way — but the ticket's evidence for *why* does.

## The 9% claim

The ticket says round headings, finding tables and leads lines come to 595 of
5,978 lines, 9% of the file, and that a study told to read the log by path spends
the rest of its context on prose it does not need.

Recomputed: 310 + 210 + 253 = 773 structural lines of 7,732, or 10.0%. The claim
reproduces.

## Heading format

Every heading in the root log carries a date and nothing finer:

```text
## Step 1, round 1 -- 2026-08-17
## Step 6, round 2 -- 2026-08-20
```

The root log's 310 headings do not all take the `## Step N, round R` shape — only
42 do. The rest carry a topic in the heading. Whatever regex step 3 introduces has
to read the shapes actually present, and the count above is how many entries it
has to keep readable without editing them.

## Prior art read

- **Last two merged pull requests touching `plugins/hexaemeron/skills/fiat`.**
  [#431](https://github.com/wildcat-finance/skills/pull/431) (run-level, merged
  2026-08-21) and [#430](https://github.com/wildcat-finance/skills/pull/430)
  (step 3 of the same run). #431 carries forward exactly one item:
  [#363](https://github.com/wildcat-finance/skills/issues/363), the held
  delegated-task-identity frontier job. #429 is generation work and leaves #363
  untouched, so the carried item is answered by name and stays open. #430 is a
  step pull request and carries no `## Carried forward` section, which is correct:
  the obligation is run-level.
- **Audit record of the in-scope skill.** `audit/AUDIT.md` is fiat's. The only
  round touching the round format itself is S3-R1-01, which fixed `audit-loop.md`
  step 4 for showing the bare `audit-round` command as though it were complete for
  a non-Solidity round. That is the same file item 1 of this ticket edits, and the
  finding's shape is a warning for it: a reference that states a requirement
  incompletely reads as complete. Nothing in the log accepts a lead that this
  ticket's design reopens.
