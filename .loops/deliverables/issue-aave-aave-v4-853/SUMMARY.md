# aave/aave-v4#853: interest rate linearisation lets anyone inflate borrower interest

Target: `laurenceday/aave-v4-shoggoth`, a fork of `aave/aave-v4`. Nothing was
pushed to `aave/aave-v4`, and the write gate denies that organisation outright.

## What the operator should do next

Read the two candidate branches and decide the semantic question below. Neither
candidate is adoptable as it stands, and the reason is not implementation
quality.

## Confirmed, not taken on trust

`src/hub/libraries/AssetLogic.sol:163` grows the debt index with
`previousIndex.rayMulUp(MathUtils.calculateLinearInterest(rate, last))`, and
`calculateLinearInterest` returns `RAY + rate * dt / SECONDS_PER_YEAR`. Every
accrual multiplies by that factor where a single accrual over the same span
would add the rate once, and `accrue()` runs on any interaction with the asset.
Whoever triggers accrual therefore sets what borrowers owe.

Measured on the fork at a 1000% annual rate over one year:

| Accrual frequency | Debt index | Against annual |
| --- | --- | --- |
| once per year | 11 RAY | reference |
| once per day | 19,253 RAY | 1,750x |
| once per hour | higher again | |

Per-second tends to `e^10` = 22,026, which is the 2,202,543% the issue reports.
Daily poking is not adversarial behaviour; it is a busy market.

Branch: `shoggoth/issue-aave-aave-v4-853/linear-interest-frequency`. Five tests,
all passing on the unfixed tree because they state current behaviour. A
1000-run fuzz shows the direction holds for any rate and any split.

## The finding that outranks both candidates

The two candidates answer different questions, and 853 cannot be closed until
Aave says which question `drawnRate` asks.

- Compounded accrual treats it as a nominal, continuously compounded rate. A
  configured 1000% then costs 2,202,600%, so the number stops meaning what an
  operator reading a config file would take it to mean.
- Quantised accrual preserves that meaning and keeps a frequency dependence,
  turned around to underpay when accrual is infrequent.

## Candidate A: the V2/V3 compounded debt index

Branch: `shoggoth/issue-aave-aave-v4-853/candidate-a-compounded`.

Frequency invariance is exact: daily, hourly and per-minute all land on 22,026.
Gas for one step rises from 115 to 1,482.

It also breaks the numeric envelope. `accrue()` stores the index with
`toUint120()`, which allows growth of 1,329,227,995x above RAY. At the maximum
configurable rate, compounded daily accrual passes that ceiling after **97
days**, reverting `SafeCastOverflowedUintDowncast(120, index)` inside the
accrual path, and after 244 days the arithmetic itself overflows uint256 before
any cast is reached. An asset there cannot accrue, so it cannot be borrowed
against, repaid or liquidated. `drawnRate` is a `uint96`, so that rate is
settable rather than absurd.

Suite: 94 failures against a 1,564-pass baseline. 86 are scenarios whose
provisioned collateral no longer covers the debt, 8 are reverts on paths the
larger index drives, the rest are expected values pinning linear arithmetic, and
4 are the SafeCast overflows above.

## Candidate B: quantise accrual to whole periods

Branch: `shoggoth/issue-aave-aave-v4-853/candidate-b-decompounded`.

`accrue()` advances `lastUpdateTimestamp` by whole `COMPOUNDING_PERIOD` steps
instead of to `block.timestamp`, leaving the part-period remainder on the clock.
Weekly, daily and hourly accrual then all give 9,166 exactly, against 18,740
unfixed.

Two honest limits. 9,166 is still weekly compounding of a 1000% annual rate, so
this removes the exploit without reaching the intended 11; that needs the rate
expressed per period too, which is the other half of the reporter's suggestion
and is not implemented here. And a position opened and closed inside one period
accrues nothing at all, which is a real loss to lenders.

Its envelope is later, not safe: 23 weekly accruals, 161 days, at the maximum
rate. At a plausible 20% the index after ten years is 7 RAY.

Suite: 69 failures. Roughly 30 repricing, 16 tests that skip days and assert
something accrued, 4 test-body arithmetic underflows traced to the test frame
rather than library code, 4 expecting reverts that no longer happen.

## What neither candidate did

Neither is proposed as the fix, and neither establishes a security conclusion.
The reproduction is evidence about accrual arithmetic on this fork at named
rates and frequencies. It says nothing about exploitability under real market
conditions, about other paths into `accrue()`, or about the premium and fee
maths that read the same index.

The uint120 ceiling deserves separate attention either way: it is sized for
linear per-second accrual specifically, and both candidates reach it at rates
the type permits.
