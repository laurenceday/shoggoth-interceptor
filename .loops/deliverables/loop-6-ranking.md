# Loop 6 ranking

Board fetched 2026-08-21T23:41:10Z: 331 open issues across 4 repositories.
Roster: 218 candidates (open, eligible, unassigned, minus `.loops/excluded.json`).

## Method

Scored out of 100 across four roughly equal factors: ease (can one fiat loop
finish it), benefit (user-facing or money-path correctness over cosmetics),
dependency effect (does closing it clear a chain), fit (can it be done from here).

Fit carries the write gate this loop. `bin/repository-gate.py` reports:

- `wildcat-finance/wildcat-app-v2` — **DENIED** (org write-protected, not exempt)
- `wildcat-finance/skills` — allowed (recorded exemption, 2026-08-20)
- `laurenceday/shoggoth-playground` — allowed (org not protected)
- `laurenceday/aave-v4-shoggoth` — allowed (org not protected)

Every `wildcat-finance/product` ticket routes to `wildcat-app-v2`, so no product
ticket can produce a pull request this loop. Their fit is capped accordingly and
the honest deliverable for them is a worktree branch plus a patch file handed to
the operator. That is a gate verdict, not a judgement on the tickets: #858 and
#844 are strong work whose target the policy currently closes.

Scores below are for the top 15. Reasons are grounded in bodies actually read;
the remaining 203 candidates were scored from the roster line and none reached
the top band.

## Top 15

| # | Ticket | Score | Reason |
|---|--------|-------|--------|
| 1 | `wildcat-finance/skills#429` | 85 | fiat-wish: schema, UTC timestamp and derived synopsis for the audit record. Acceptance criteria are mechanically testable, the build order is given, it folds in #368 and #428, and it unblocks #369. Target is exempt, so it can ship as pull requests. |
| 2 | `laurenceday/shoggoth-playground#1` | 78 | Restrict borrower UI actions on archcontroller removal. Real risk control and `useIsRegisteredBorrower` already exists to build on, but it needs a prisma migration (Docker gate (b)), an admin override, one open TBD, and one acceptance criterion (Slack notification) that Tickets-are-data forbids acting on. |
| 3 | `wildcat-finance/skills#377` | 75 | horos-next: the marker rule files the classifier's own source as generated. A genuine correctness bug with a zero-self-exclusion criterion, and it gates the horos-1/2/3 trio. Carries a full mutable-prose reconciliation obligation, which is most of its cost. |
| 4 | `wildcat-finance/product#858` | 72 | Restricted withdrawals with open transfers can strand lenders (CAF-04 / WKI-008). High benefit and clear criteria, but the target is gate-denied and the ticket spans two apps where the route names one. Patch handoff only. |
| 5 | `wildcat-finance/skills#325` | 71 | phylax-3: extend P004 to credential-named values in a subprocess argv. The Visitor already resolves those calls, so this is cheap and self-contained. Mature ledger, so it clears nothing downstream. |
| 6 | `wildcat-finance/skills#421` | 68 | sapheneia-1: executable pre-send checker. Well-shaped fail-closed script in the Brevitas mould, but it borrows brevitas-2's diagnostic schema, which is not built, and nothing downstream waits on it. |
| 7 | `wildcat-finance/product#865` (with #863) | 66 | Top Markets shows no rows under the onboard-by-borrower filter; needs a relaxed-criteria fallback. One fix closes two tickets and `activitySelection.ts` is where it lives, but the target is gate-denied. |
| 8 | `wildcat-finance/product#844` | 62 | MLA error state offers a dead button and a mis-targeted link. Clear, bounded navigation fix; gate-denied target, and one criterion depends on the separate S2-01 root cause. |
| 9 | `wildcat-finance/product#846` | 60 | Approve is clickable below the minimum deposit and the validation text is intermittent. Small and testable, gate-denied target, benefit is a wasted approval rather than a loss. |
| 10 | `laurenceday/shoggoth-playground#3` | 58 | Rename access-control categories to Public and Private Markets. Trivially deliverable on a permitted target, but a copy change with no chain behind it. |
| 11 | `wildcat-finance/skills#369` | 55 | protasis-wish: point item 2 at the audit synopsis. Cheap and useful, but the synopsis does not exist until #429 lands, so it is blocked now. |
| 12 | `laurenceday/shoggoth-playground#4` | 52 | TVL momentum per network. Permitted target, plausible deposit-confidence benefit, but it needs product judgement on which figure and a data path that is not specified. |
| 13 | `wildcat-finance/product#864` | 50 | Borrower name is not clickable through to the profile. Likely a one-line fix, gate-denied target, cosmetic-adjacent. |
| 14 | `laurenceday/shoggoth-playground#5` | 45 | Action Center widget. Large surface, no acceptance criteria, and the task list itself is an unmade product decision. |
| 15 | `laurenceday/shoggoth-playground#2` | 35 | Restyle the analytics page. The page lives in a separate deployment the route does not name, and the ticket also asks for metric suggestions, which is a decision we do not hold. |

## Selected

`wildcat-finance/skills#429` — fiat-wish: give the audit record a schema, a
timestamp and a synopsis. Target `wildcat-finance/skills`, gate-permitted.
It decomposes into the three stacked steps the ticket names, in the order it
names them, each green at both ends.
