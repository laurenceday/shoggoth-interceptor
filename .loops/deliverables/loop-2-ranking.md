# Loop 2 ranking - 2026-08-19

Board refreshed 05:24 UTC (226 open issues, 273 pipeline-mapped). Scope
unchanged: Icebox + Product Backlog, tech debt only, frontend first; 75
candidates after 1 exclusion (#789, loop 1). The loop-1 scoped ranking
(loop-1-ranking-scoped.md) still holds; deltas only:

- #789 excluded (loop 1 delivered; stack #367-#370 awaiting review).
- No new in-scope tickets entered Icebox or Product Backlog since loop 1;
  the three new board issues (all in New Issues) are out of scope.
- No open PR claims any of the remaining top five.

| # | Score | Pipeline | Issue |
|---|-------|----------|-------|
| 1 | 83 | Backlog | #538 Fix wrong reason shown when a fixed-term market can't be terminated early |
| 2 | 81 | Icebox | #442 + #443 terminated-market screen pair |
| 3 | 80 | Icebox | #608 Max button on deposit modal |
| 4 | 78 | Backlog | #691 Rename market categories by access control |
| 5 | 76 | Icebox | #606 Borrowers cannot withdraw over-repaid funds |

## Winner

**#538 - Improve UX when trying to terminate a fixed term market before end
date** (83/100). The message shown when termination is blocked says "repay
debt" even with zero debt; the real reason is the term has not ended and
early termination is disabled. Well-specified, screenshot included,
single-surface UI fix. No tie-break needed.
