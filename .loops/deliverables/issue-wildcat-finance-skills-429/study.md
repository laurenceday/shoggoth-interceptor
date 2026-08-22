# Study — the audit record's schema, timestamp and synopsis

Source ticket: [wildcat-finance/skills#429](https://github.com/wildcat-finance/skills/issues/429).
Target repository: `wildcat-finance/skills`. Starting ref
`cbd7185d81500463488bd9f770d162493b0d1f0c` on `main`.

**Status: unreceipted draft.** This session could not run `hexctl`, so no
`done study` receipt exists and no run has begun. It could not run
`protasis.py` either, so the twelve items below have not been checked
mechanically. Both blockers are in
[SUMMARY.md](SUMMARY.md). Everything the study asserts about the code was read
from the tree at the ref above; the measurements are in
[baseline.md](baseline.md).

Assuming, unless corrected:

1. Python 3 and stdlib `unittest`, matching every other suite here. The
   measured toolchain is Python 3.14.6.
2. Generation work on Fiat, not a frontier advance. The ticket says so and
   fiat's ledger holds [#363](https://github.com/wildcat-finance/skills/issues/363)
   as the open frontier job, which this leaves alone.
3. The change is Fiat's alone. #369 carries the Protasis half and is not
   touched.
4. `AUDIT.md` stays append-only. All 310 existing root-log entries and the 69
   in the five plugin logs keep their bytes.
5. No Solidity changes, so the Pashov pair is waived and the three bundled
   lints are the mechanical part of every round.

## 1. Problem statement

An audit round is written by whoever ran it and read later by somebody deciding
whether to trust it. Three properties of the current format defeat that reader.

The format's two stated requirements are optional in practice: nothing refuses a
round that omits the findings table or the `Leads not pursued` line, and
`cmd_audit_round` never opens the log it is handed, so it cannot. The field a
later reader most needs — what the round did not check — is named in at most 6%
of rounds. And the root log is 7,732 lines of which 773 are structural, so a
study following Protasis item 2 and reading the log by path spends 90% of that
context on prose it does not need.

Working prototype means all three closed: the receipt refuses a round missing a
required field and names it, a heading written after the change orders two
rounds from the same day, and a generated synopsis stands beside each of the six
logs, held current by a test.

**Demo path.** On the run branch, append a round to `audit/AUDIT.md` missing the
`What it did not check` field and record it: the receipt exits non-zero naming
that field. Add the field and re-record: the receipt succeeds and the heading it
requires carries a UTC timestamp to the second. Regenerate the synopses and run
the currency test; append one more round without regenerating and the same test
fails, naming the log and the refresh command.

## 2. Prior art

Read before design options were drawn. What each source establishes is in
[baseline.md](baseline.md); this item names them and what they change here.

- `plugins/hexaemeron/skills/fiat/scripts/hexctl.py`, 2,553 lines.
  `cmd_audit_round` at line 1089 validates `--findings`, the three lint exits,
  the max-round ceiling and any `--fixes-commit`, then appends a state entry
  holding `log` as an unopened path string. Every check it performs is over its
  own argv. Nothing reads the log, which is why the format's requirements are
  unenforceable today rather than merely unenforced.
- `--log` is optional (line 2513) and `config audit.log_path` defaults to
  `audit/AUDIT.md` (line 80). Enforcement can therefore resolve the log from
  config when the flag is absent, without making a previously optional flag
  required.
- `now()` at line 125 returns `datetime.now(timezone.utc).isoformat()` — full
  ISO-8601 UTC, already stamped on every ledger entry including each round's
  `ts`. **The ticket calls this `utc_now()`; no such function exists.** The
  precision the ticket says is thrown away is real and the helper is real; only
  the name in the ticket is wrong.
- `scoped_path` bounds a repo-relative path against the target root and is
  already used for the warden packet's `audit_log_path` (line 2209).
  `bounded_source` (line 160) caps a read at `SOURCE_BYTES_MAX`. Both are the
  existing controls for the boundary item 9 opens.
- `plugins/hexaemeron/skills/fiat/references/audit-loop.md`, 126 lines, states
  the round template and the two conventional fields. Its most recent audit
  finding, S3-R1-01 in `audit/AUDIT.md`, was exactly this file stating a
  requirement incompletely and reading as complete. Item 1 edits the same file
  and inherits the warning.
- `tests/test_boundary_currency.py`, 126 lines, is the model item 3 names: it
  imports the generator module, regenerates, diffs against the committed
  artefact, and carries mutation tests that require the comparison to name a
  path in both directions — an entry the tree earned and the artefact lacks, and
  one the artefact claims and the tree no longer earns. Its `REFRESH` constant
  puts the regeneration command in the failure message. Copy all of that.
- `tests/test_version_propagation.py` requires a governed skill's ledger version
  and its `SKILL.md` frontmatter to agree. Fiat states `5.9.1` in both, so the
  generation row and the frontmatter move together or the suite fails.
- `plugins/hexaemeron/skills/VERSIONING.md` fixes the row: generation increments
  the second number, and retains the prior frontier revision and its digest byte
  for byte.
- [#431](https://github.com/wildcat-finance/skills/pull/431) is the last merged
  pull request touching fiat. Its `## Carried forward` names one item,
  [#363](https://github.com/wildcat-finance/skills/issues/363), the held
  frontier job. It stays open and untouched: this is generation work.
  [#430](https://github.com/wildcat-finance/skills/pull/430) is a step pull
  request from the same run and carries no such section, which is correct.

Outside this repository: nothing. The format is local.

## 3. Constraints and non-goals

Starting ref `cbd7185d81500463488bd9f770d162493b0d1f0c`. Python 3.14.6, stdlib
`unittest`. Two suites gate every commit: `python3 -m unittest discover -s tests`
(107 at baseline) and the Hexaemeron suite (710 at baseline via discovery).

Non-goals, each from the ticket:

- **Existing entries are not rewritten.** An append-only record edited to
  satisfy a later schema stops being a record. The consequence is a log holding
  two shapes, which the synopsis reports rather than hides.
- **What a round *does* is unchanged.** This is what a round writes down, not
  how hard it looks.
- **Protasis item 2 is not repointed at the synopsis.** That is #369, on
  Protasis's ledger. A Fiat run cannot cut a row on another skill's.
- **`AUDIT.md` is not put behind the Horos boundary.** The only mechanism
  available today is marking it `linguist-generated`, and the log is not
  generated. The ticket recommends against it and gives the honest route if it
  is wanted later; that is a Horos frontier job with its own study.
- **A `Status: clean` line and a suite count are both rejected as fields.** The
  first is derivable from the findings table. The second is worse than
  redundant: prose repeating evidence the receipt already holds invites a round
  to claim a suite passed without running it.

## 4. Design options

**A. Enforce over the log's content, resolved from config.** `audit-round`
resolves the log from `--log` or `config audit.log_path`, reads its last entry
under the bounded reader, and refuses when a required field is absent, naming
which. Trade: the receipt gains a filesystem read it did not have, so it can now
fail for reasons that are not about the round — a moved log, a permission error.
Those become explicit refusals rather than silent passes.

**B. Take the fields as receipt arguments.** `--covered`, `--not-checked` and so
on, validated in argv the way the lint exits are. Trade: cheap and consistent
with the existing shape, but it enforces nothing about the log. The ledger would
carry fields the log does not, and the artefact a later reader opens is the log.
The ticket's whole complaint is about what the log holds.

**C. Enforce in a separate linter, run as part of the round.** A fourth lint
beside phylax, ephoros and hypomnema. Trade: no change to the receipt, but the
requirement then depends on somebody passing its exit — which is the same
honour-system failure at one remove, and #427 already records half the prose
contract failing exactly that way.

**Chosen: A.** It is the only option where the artefact that is read is the
artefact that is checked. B enforces the wrong surface and C enforces it
optionally. A's trade — a receipt that can fail on the filesystem — is bounded
by controls that already exist for this exact path, `scoped_path` and the capped
reader, and a refusal that names a missing log is a better outcome than a round
recorded against a log nobody opened.

The synopsis follows from A rather than competing with it: once the fields are
structured and required, the synopsis is those fields, so no prose scraper is
built and thrown away. This is why the ticket's build order is schema, then
heading, then synopsis, and the order is adopted unchanged.

## 5. Risk register seed

The work is Python: a receipt that now reads a file, a generator that writes six
files beside logs, and a regex over 379 existing entries that must not be
rewritten.

```risk-register
log-path-resolution | the log path from argv or config before the receipt opens it | a path outside the target root, a directory, or a missing file is refused by name and no round is recorded
unbounded-log-read | the receipt reading a 7,700-line log into memory | the read goes through the existing capped reader and a log over the cap is refused rather than truncated
heading-shape-drift | the round-heading regex over two shapes of entry | both the pre-change dated heading and the post-change timestamped heading parse, and no existing entry's bytes change
schema-refusal-integrity | the state and ledger during a refused round | a refusal leaves state, ledger and log bytes identical, so a rejected round is not half-recorded
synopsis-partial-write | each synopsis file during regeneration | a killed regeneration leaves the previous synopsis or none, never a truncated one
synopsis-drift | the committed synopsis against the log it describes | the currency test fails in both directions and its message names the log and the refresh command
field-detection-false-negative | the parser deciding a required field is present | a heading, a quoted example, or a field name inside a finding's prose does not satisfy the field it names
```

The two the audit loop should look hardest at are `heading-shape-drift` and
`field-detection-false-negative`. The first is the one that can damage the
record: a regex that matches too widely and a generator that rewrites what it
matched would edit 379 append-only entries. The second is the one that makes the
whole change worthless while appearing to work — a field satisfied by the word
appearing anywhere is a field nobody has to fill in.

## 6. Glossary seeds

- **Round entry.** One appended block in a log, opened by a heading matching the
  round-heading shape and ending where the next such heading begins.
- **Required field.** One of the four the reference will name: what the round
  covered, what it did not check, the findings table, and `Leads not pursued`.
- **Synopsis.** `AUDIT_SYNOPSIS.md` beside a log, generated from that log's
  structured fields, never hand-edited.
- **Currency.** The property that a committed synopsis is byte-identical to a
  fresh generation from its log.
- **Two shapes.** The consequence of not rewriting history: entries written
  before the schema and entries written after it, in one file.

## 7. Sources

- Ticket: `https://github.com/wildcat-finance/skills/issues/429`, folding #368
  and #428, unblocking #369.
- Tree at `cbd7185d81500463488bd9f770d162493b0d1f0c`: `hexctl.py`,
  `references/audit-loop.md`, `EVOLUTION.md`, `../VERSIONING.md`,
  `tests/test_boundary_currency.py`, `tests/test_version_propagation.py`, the
  six `AUDIT.md` files.
- Pull requests [#431](https://github.com/wildcat-finance/skills/pull/431) and
  [#430](https://github.com/wildcat-finance/skills/pull/430).
- Measurements: [baseline.md](baseline.md).

## 8. Signals, and the questions behind them

The controller runs unattended inside a loop, so a refusal that does not say
what it wants stops the loop without telling anyone why. Two questions, per
[ephoros](https://github.com/wildcat-finance/skills/tree/main/plugins/hexaemeron/skills/ephoros).

- *Which required field did the round omit?* Answered by the refusal message in
  step 2, which names the field rather than reporting a schema failure. This is
  the shape the existing lint-exit refusal already uses, which names the missing
  flags rather than saying flags are missing.
- *Which synopsis is stale, and how do I refresh it?* Answered by the currency
  test in step 4, whose failure names the log path and carries the regeneration
  command, the way `test_boundary_currency.py`'s `REFRESH` constant does.

## 9. Boundaries, per capability

Per [phylax](https://github.com/wildcat-finance/skills/tree/main/plugins/hexaemeron/skills/phylax).

- **The receipt reads a repository file (step 2, new).** Worth taking: a path
  from argv or config, resolved and opened. Control: `scoped_path` against the
  target root, the existing capped reader, and refusal by name on absent,
  oversized or non-UTF-8 content. No shell, no subprocess.
- **The generator writes six files (step 4, new).** Worth taking: an output path
  derived from each log's own directory, never from argv. Control: derive rather
  than accept, write via a temporary file and atomic replace, and never open the
  log for writing.
- **The regex reads 379 entries it must not change (steps 3 and 4).** Control:
  the generator and the parser open the logs read-only; the currency test proves
  a fresh generation matches the committed synopsis, and the suite proves the
  logs' bytes are untouched.

No credential, no network, no subprocess argv is introduced.

## 10. The budget, or its absence

None: no performance claim is made and no step is motivated by speed, so
[metron](https://github.com/wildcat-finance/skills/tree/main/plugins/hexaemeron/skills/metron)
has nothing to measure before and after.

One size criterion is not a budget but is checked the same way: each synopsis
must be under 15% of its log's line count, from the ticket's acceptance list.
For the root log that is 773 lines against 7,732 at baseline — the structural
lines already come to 10.0%, so the criterion is met by generating the fields and
nothing else, and is tight enough to fail if the generator starts copying prose.
The test asserts the ratio per log rather than a fixed number, since every log
grows.

## 11. The fail-closed posture

Per [elenchus](https://github.com/wildcat-finance/skills/tree/main/plugins/hexaemeron/skills/elenchus).

Three things stop the run. `audit-round` refuses and records nothing when a
required field is absent or the log cannot be read. The currency test fails when
a synopsis and its log disagree. Either suite going red stops the step.

Guard convention: every fix committed during an audit round arrives with a test
that fails without it, and the mutation tests in step 4 exist because a guard
that cannot fail is worth nothing — the same argument
`tests/test_boundary_currency.py` states in its own docstring.

## 12. Decisions and their homes

Per [hypomnema](https://github.com/wildcat-finance/skills/tree/main/plugins/hexaemeron/skills/hypomnema).

- **Not rewriting the 379 existing entries**, and the two-shapes consequence
  that follows. Expensive to reverse in the sense that matters: once edited, the
  record cannot be un-edited. Home: `references/audit-loop.md`, beside the
  format it explains, and the ledger row.
- **Rejecting `Status: clean` and a suite count as fields.** Home: the same
  reference, so a later reader proposing them finds the reason rather than the
  absence.
- **Rejecting the `.gitattributes` route to a Horos boundary.** Home: this
  study's non-goals, committed in step 1, since it is a decision about work not
  done here.
- **The generation row itself.** Home: `plugins/hexaemeron/skills/fiat/EVOLUTION.md`,
  `fiat-v5.10.1`, axis generation, retaining frontier revision
  `state-shape-validation` and digest
  `e413d6041edb34b3807a54019489605814a591f60547755f8f66f01830f643aa` byte for
  byte, with `SKILL.md` frontmatter moved to match.

## Boundaries

**Always.** Both suites before a commit. The imprimatur lint on every shipped
document. The three bundled lints on every round, with their exits on the
receipt.

**Ask first.** Making `--log` a required flag rather than falling back to
config. Changing the round-heading shape for anything beyond adding the time.
Any change to what a round does rather than what it writes down.

**Never.** Edit an existing entry in any of the six logs. Regenerate a synopsis
by hand. Mark the log `linguist-generated`. Delete or skip a test to make a
suite pass. Record a round whose lints did not run.

## Success criteria

Each is the ticket's, with the command that checks it.

1. `references/audit-loop.md` states the four required fields and the heading
   format, with one example entry. Checked by the imprimatur lint and by review.
2. `audit-round` refuses a round missing a required field and names it. Checked
   by new cases in `plugins/hexaemeron/tests/test_hexctl.py`.
3. A round recording zero findings still carries what it covered and what it did
   not check. Same suite, as its own case.
4. A heading written after the change carries a UTC timestamp to at least the
   second. Same suite.
5. `AUDIT_SYNOPSIS.md` exists beside all six logs, each under 15% of its log's
   line count and byte-identical to a fresh generation. Checked by the currency
   test.
6. The currency test fails when a round is appended without a regenerated
   synopsis. Checked by that test's own mutation cases.
7. Every `Leads not pursued` line in a log appears in its synopsis. Checked by a
   case in the currency test.
8. No existing entry is edited, and the decision not to is on the page. Checked
   by `git diff --stat` over the six logs showing additions only, and by review.
9. Both suites pass: `python3 -m unittest discover -s tests` and
   `python3 plugins/hexaemeron/tests/run_tests.py`.

## Open question

One, and it does not block the build. [baseline.md](baseline.md) reproduces two
of the ticket's three measurements but not the third: the `Leads not pursued`
line appears on 81% of rounds by line count against the ticket's 58% per entry.
The field is being made required either way, so no step changes. What changes is
which figure the reference cites when it explains why. Settle it with a
per-entry segmentation of the log before step 2's prose is written.
