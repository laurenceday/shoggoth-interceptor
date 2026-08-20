# Loop 5 ranking: aave/aave-v4

Source: `aave/aave-v4`, 19 open issues, every one unassigned. Target for
implementation: `laurenceday/aave-v4-shoggoth`, a fork of that repository.

Ranked manually from `gh issue list` rather than from `bin/shoggoth.py roster`,
because `config/resolver.json` names only `wildcat-finance/product` and has no
Aave source or route. Recorded here so the pass has a receipt either way; the
config gap is named at the bottom.

Scores are out of 100, weighting ease, benefit, dependency effect and fit
roughly equally.

## Excluded before scoring

The loop protocol skips a ticket whose trail shows someone is already on it.
Three qualify, none of them by assignment:

| Issue | Why |
| --- | --- |
| 640 | `piyushbag`, 2026-07-21: "Taking this on: add dewadifyUp, rayToBpsDown, and rayToBpsUp... PR incoming." |
| 544 | `piyushbag`, 2026-07-21: "Taking this on: add dedicated Spoke tests for borrowing flag toggles... PR incoming." |
| 382 | `DhairyaSethi`, an Aave member: "will implement this separately & we can utilise certora equivalence checker for it" |

## Ranking

| # | Issue | Score | One line |
| --- | --- | --- | --- |
| 1 | 853 | 88 | Debt index uses linear interest, so accrual depends on trigger frequency. Money path, and a commenter already located it in `AssetLogic.getDrawnIndex()` against the V2/V3 split. |
| 2 | 641 | 82 | Branchless `MathUtils.add(uint,int)`. One library function, a member says the existing `MathUtils.t.sol` tests already model the behaviour, and the benefit is measurable rather than argued. |
| 3 | 1283 | 74 | `ITreasurySpoke` does not inherit `IOwnable`. Interface correctness, provable by compilation, no behaviour risk. |
| 4 | 612 | 70 | Spoke `reserveId` to `bucketIndex`/`bucketMask`. A contributor supplied the mask arithmetic, so the approach is not open-ended, but it touches storage layout. |
| 5 | 799 | 66 | Treasury Spoke should allow registering `reserveIds`. Clear feature with a named surface. |
| 6 | 638 | 62 | Dynamic risk config: getter with refresh, event when stale config is overwritten. Two small additions in one file. |
| 7 | 530 | 60 | Refresh dynamic config eventing. Same area as 638 and probably cheaper after it. |
| 8 | 423 | 56 | `KeyValueList` array alloc and dealloc optimisation. Needs the allocation model understood first. |
| 9 | 403 | 52 | Gas report in CI. Cheap mechanically, but CI belongs to the upstream repository rather than a fork. |
| 10 | 1248 | 48 | How to update `tests/mocks/JsonBindings.sol`. Answerable as a short docs note rather than code. |
| 11 | 67 | 44 | solhint and prettier-import style enforcement. Mechanical, and the diff would touch most of the tree. |
| 12 | 94 | 40 | ERC-4626 integration. Design work with named prior art, too large for one pass. |
| 13 | 1222 | 34 | Deployment and config engine user input. Scope not yet stated. |
| 14 | 537 | 26 | Borrow against collateral outside the LiquidityHub. Labelled `investigate`, and the comments turn on custody decisions nobody here can make. |
| 15 | 1060 | 8 | User support question about migrating from V1, already answered by Aave Labs. |
| 16 | 1335 | 6 | Bridge fee question from a user. Not work. |

## Taking

853 as instructed, then 641 and 1283.

Both choices are deliberate company for 853. 641 is a gas change, so it has to
carry a measured before and after rather than an argument, which is what
`hermes` and `metron` exist for. 1283 is provable by compilation alone. Beside a
money-path correctness fix whose evidence is harder to establish, the pass ends
up with one measured result, one proved result, and one that will have to say
plainly how far its evidence reaches.

## Blocked on the operator

- The write gate denies every target until a sandbox is named:
  `python3 bin/repository-gate.py init laurenceday laurenceday/aave-v4-shoggoth`.
  It asks for consent interactively and records the active GitHub login only
  after a yes, so it is not the Shoggoth's to run.
- Note the consequence: that policy makes every other `laurenceday/*`
  repository write-protected, `shoggoth-interceptor` included.
- `config/resolver.json` has no Aave source, so `fetch`, `roster` and `target`
  cannot see this board. Adding one is a config change, not a guardrail
  change.
