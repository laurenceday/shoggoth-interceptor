# Loop 3 ranking - 2026-08-19

Board refreshed (226 open, 274 pipeline-mapped). Scope unchanged; 74
candidates after 2 exclusions (#789, #538). The loop-1 scoped ranking still
holds; deltas only:

- #538 excluded (loop 2 delivered; PRs #374-#375 awaiting review).
- No new in-scope tickets; no open PR claims the remaining top picks.

| # | Score | Pipeline | Issue |
|---|-------|----------|-------|
| 1 | 81 | Icebox | #442 + #443 terminated-market pair (one loop, two tickets) |
| 2 | 80 | Icebox | #608 Max button on deposit modal |
| 3 | 78 | Backlog | #691 Rename market categories by access control |
| 4 | 76 | Icebox | #606 Borrowers cannot withdraw over-repaid funds |

## Winner

**#442 + #443** (81/100). #442 ("Disable Borrow and Repay screen on
terminated markets") is blocked by #443 ("Move Market statement download to
Status and Details"), so the pair is worked in dependency order: #443 first,
then #442, as one stacked run. Scope note carried into the study: the
tickets are from 2024 and the app has since been rebuilt; the study must
verify the surfaces still exist and honour the designer's recorded doubt
about changing the default screen for active markets (the change is scoped
to terminated markets only).
