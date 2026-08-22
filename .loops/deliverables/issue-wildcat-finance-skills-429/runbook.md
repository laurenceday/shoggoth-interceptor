# Runbook — the audit record's schema, timestamp and synopsis

Derived from [study.md](study.md). Five steps, in the ticket's build order:
schema, then heading, then synopsis, then the ledger row and the demo.

**Status: unreceipted draft.** No `done runbook` receipt exists and
`protasis.py` could not run against this file. See [SUMMARY.md](SUMMARY.md).

Base `main` at `cbd7185d81500463488bd9f770d162493b0d1f0c`. Run branch
`shoggoth/issue-wildcat-finance-skills-429/audit-record-schema`, cut from the
synced base and pushed before step 1. Step branches chain onto each other and
each pull request targets the branch below it; nothing merges while the steps
run.

Every step's exit includes both suites green:

```bash
python3 -m unittest discover -s tests
python3 plugins/hexaemeron/tests/run_tests.py
```

Baseline for those two is 107 and 710. A step that changes the counts says by
how many and why.

## Step 1: scaffold the specification

**Goal.** Put the study, the runbook and the measured baseline in the repository
before any behaviour changes, so every later step has a citable spec.

**Entry.** The run branch at the synced base. No source file changed.

**Exit.** Three documents committed under `docs/`, both suites unchanged at 107
and 710, and `python3 plugins/hexaemeron/skills/protasis/scripts/protasis.py
--study docs/fiat-audit-record-schema-study.md` and the same script over the
runbook both exit 0.

**Files.** `docs/fiat-audit-record-schema-study.md`,
`docs/fiat-audit-record-schema-runbook.md`,
`docs/fiat-audit-record-schema-baseline.md`.

**Tests.** None written. `tests/test_marketplace_prose.py` and
`tests/test_shipped_prose_lints.py` already cover new shipped prose and must
stay green over the three additions.

**Disciplines.** phylax: none, no boundary — three documents are added and no
code path changes. ephoros: none, nothing here runs unattended. metron: none, no
performance claim. elenchus: none, no failure in hand. hypomnema: this is the
step that gives the two rejected-field decisions and the not-rewriting decision
their home, which is the whole point of committing the study.

## Step 2: require the four fields, and refuse by name

**Goal.** `audit-round` reads the round it is recording and refuses one that
omits a required field, naming the field.

**Entry.** Step 1's branch. The specification is committed.

**Exit.** `audit-round` resolves the log from `--log` or `config
audit.log_path`, reads the trailing entry through the existing capped reader,
and exits non-zero naming any absent required field; a round with all four is
recorded as before. `references/audit-loop.md` states the four fields with one
example entry. Both suites green, the Hexaemeron count up by the new cases.

**Files.** `plugins/hexaemeron/skills/fiat/scripts/hexctl.py` (`cmd_audit_round`
and a field parser beside it), `plugins/hexaemeron/skills/fiat/references/audit-loop.md`.

**Tests.** `plugins/hexaemeron/tests/test_hexctl.py`, extended. At least: one
case per required field absent, asserting the refusal names that field and that
state, ledger and log bytes are unchanged; a zero-findings round that carries
what it covered and what it did not check, accepted; a zero-findings round
missing the not-checked field, refused; a log path outside the target root,
refused; a log over the byte cap, refused rather than truncated; a required
field name appearing only inside a finding's prose or a fenced example, not
accepted as the field. The last is the `field-detection-false-negative` concern
from the study's register and is the case most worth writing first.

**Disciplines.** phylax: this step opens the receipt's first filesystem read, so
the log-path and read-size boundaries in study item 9 are incurred here. ephoros:
the refusal message is the signal answering the study's first on-call question,
so it must name the field rather than report a schema failure. metron: none, no
performance claim. elenchus: any red test here is worked to its cause and leaves
a guard, per the study's fail-closed posture. hypomnema: the reference edit is
where the four fields and the two rejected candidates get recorded.

## Step 3: put a UTC timestamp on the heading

**Goal.** Two rounds recorded on the same day can be ordered from the log alone.

**Entry.** Step 2's branch. Field enforcement is in place.

**Exit.** The heading format in `references/audit-loop.md` carries a UTC
timestamp to at least the second, `audit-round` accepts and requires it using
the existing `now()` helper at `hexctl.py:125`, and the parser from step 2 reads
both the pre-change dated shape and the post-change timestamped shape. No
existing entry's bytes change: `git diff --stat` over the six logs shows no
modification. Both suites green.

**Files.** `plugins/hexaemeron/skills/fiat/scripts/hexctl.py`,
`plugins/hexaemeron/skills/fiat/references/audit-loop.md`.

**Tests.** `plugins/hexaemeron/tests/test_hexctl.py`. A heading with a bare date
still parses; a heading with a timestamp parses; a round written after the change
carrying only a date is refused; two same-second and two same-day headings order
correctly. The helper is `now()` — the ticket's `utc_now()` does not exist, so a
step written against that name will not find it.

**Disciplines.** phylax: none new, the boundary opened in step 2 is unchanged.
ephoros: none new. metron: none. elenchus: the `heading-shape-drift` concern is
the one that can damage the record, so a failure here stops the step rather than
being worked around. hypomnema: the two-shapes consequence is recorded in the
reference in this step, since this is the step that creates it.

## Step 4: generate a synopsis beside each log

**Goal.** Each of the six logs has a generated `AUDIT_SYNOPSIS.md` that a study
can read instead of the log, held current by a test that can fail.

**Entry.** Step 3's branch. Fields are required and headings are ordered.

**Exit.** A generator produces `AUDIT_SYNOPSIS.md` beside each of the six logs
from the structured fields alone; each is under 15% of its log's line count and
byte-identical to a fresh generation; every `Leads not pursued` line in a log
appears in its synopsis. `python3 -m unittest tests.test_audit_synopsis_currency`
passes, and its mutation cases prove the comparison names a path in both
directions. Both suites green, the root count up by the new cases.

**Files.** a generator under `plugins/hexaemeron/skills/fiat/scripts/`, the six
`AUDIT_SYNOPSIS.md` files, `tests/test_audit_synopsis_currency.py`.

**Tests.** `tests/test_audit_synopsis_currency.py`, modelled on
`tests/test_boundary_currency.py`: regenerate and diff against the committed
synopsis; a round appended without regeneration fails and the message names the
log and the refresh command; a synopsis claiming a round the log no longer holds
fails; the 15% ratio holds per log; every leads line is present. Mutations drive
the comparison over a temporary tree, because a guard that cannot fail is worth
nothing.

**Disciplines.** phylax: the generator writes six files, so the derive-the-path
and atomic-write controls in study item 9 are incurred here. ephoros: the
currency failure is the signal answering the study's second on-call question and
must carry the log path and the refresh command. metron: none — the 15% figure is
a size criterion asserted as a ratio, not a performance budget. elenchus: the
`synopsis-partial-write` concern is worked here if it surfaces. hypomnema: none
new; the decisions this step rests on were recorded in steps 1 and 3.

## Step 5: cut the generation row and run the demo

**Goal.** Record the change on fiat's ledger, reconcile the prose that describes
it, and demonstrate the whole thing end to end.

**Entry.** Step 4's branch. All three changes are in place.

**Exit.** `EVOLUTION.md` carries exactly one new row, `fiat-v5.10.1`, axis
generation, retaining frontier revision `state-shape-validation` and digest
`e413d6041edb34b3807a54019489605814a591f60547755f8f66f01830f643aa` byte for
byte, with `SKILL.md` frontmatter moved to `5.10.1`.
`python3 -m unittest tests.test_evolution_contract tests.test_version_propagation`
passes. The demo path from the study runs: a round missing the not-checked field
is refused by name, the same round with the field is accepted under a
timestamped heading, the synopses regenerate clean, and appending one more round
without regenerating fails the currency test. Both suites green.

**Files.** `plugins/hexaemeron/skills/fiat/EVOLUTION.md`,
`plugins/hexaemeron/skills/fiat/SKILL.md`, plus whatever the prose
reconciliation touches.

**Tests.** No new test module. `tests/test_evolution_contract.py` and
`tests/test_version_propagation.py` are the gates, and the demo is run by hand
with its transcript recorded in the step's audit round.

**Disciplines.** phylax: none, no boundary. ephoros: none. metron: none.
elenchus: none, no failure in hand. hypomnema: the ledger row is the record, and
this is where it lands.

## What this runbook does not settle

The generation row's wording is left to step 5 rather than fixed here, because
the row describes what the four steps actually did and a row written in advance
describes what they were expected to do.

The open question in the study — which of two `Leads not pursued` figures the
reference cites — is answered before step 2's prose, not before step 1.
