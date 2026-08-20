# Loop 1 ranking (rescoped) — 2026-08-19

Supersedes `loop-1-ranking.md`. New directive from the operator: candidates limited to
the **Icebox** and **Product Backlog** ZenHub pipelines; **tech debt only, frontend
first**; anything DAO / raise / token / vesting / LBP related is out, as are
marketing, hiring, and biz-dev tickets. Pipeline data now comes live from ZenHub
(`bin/shoggoth.py fetch-pipelines`, 269 issues mapped across 8 pipelines).

76 product-repo issues sit in Icebox + Product Backlog. After scope filtering,
~20 are rankable tech debt. Scores /100 (ease / benefit / dependency effect / fit rubric,
CLAUDE.md):

| # | Score | Pipeline | Issue | Reasoning |
|---|-------|----------|-------|-----------|
| 1 | 86 | Backlog | #789 Restrict removed-borrower UI actions | Crisp AC (9 items), safety-relevant (defaulted/ToU-violating borrowers), frontend + persisted flag + admin override. One design TBD (manual-override precedence) worth a short study. Sister ticket #786 already covered deposit/borrow buttons — pattern exists. |
| 2 | 83 | Backlog | #538 Fix wrong reason shown when fixed-term market can't be terminated early | Small, clear, screenshot included. Wrong-message bug: says "repay debt" when the real reason is term not ended. |
| 3 | 81 | Icebox | #442 + #443 Disable Borrow&Repay on terminated markets + move statement download | Natural stacked pair (443 depends on 442) — good fit for stacked PRs, closes two tickets in one loop. |
| 4 | 80 | Icebox | #608 Add max button to deposit modal | Tiny, clearly specified (min of balance vs remaining capacity). |
| 5 | 78 | Backlog | #691 Rename market categories by access control | Copy-level change with the exact mapping given (Self Onboard → Public, Onboard by borrower → Private). |
| 6 | 76 | Icebox | #606 Borrowers cannot withdraw over-repaid funds | Real bug; needs a protocol check first (is there a max-borrow view fn?). Part investigation, part UI. |
| 7 | 74 | Icebox | #639 Lender/Borrower ToU fix (single signature with active invite) | Clear AC but touches ToU/auth backend; adjacent to the ToU family in Review/QA. Medium weight. |
| 8 | 72 | Icebox | #632 Improve Penalty and Delinquent badge | Design-adjacent; 5 comments of context; needs Figma taste but doable. |
| 9 | 71 | Icebox | #727 Expired credential state handling on market page | "Glass Door" child; well-specified state handling, medium-large. |
| 10 | 70 | Icebox | #726 Sanctioned wallet state handling across market views | Sibling of #727, slightly bigger surface (all views). |
| 11 | 68 | Backlog | #420 Adjust available amount after withdrawal served | Accounting display mismatch; old ticket, needs verification it still reproduces on current app. |
| 12 | 66 | Backlog | #531 Lenders sign MLA at current (not initial) market state | Valuable but legal-adjacent and backend-heavy. |
| 13 | 65 | Backlog | #561 Multiple UI improvements | Checklist of Figma screenshots, partially done; needs design cross-referencing, messy to verify. |
| 14 | 64 | Backlog | #695 Restyle analytics page to Wildcat style | Legit debt, but ticket defers to a designer ("Anastasia, this should just…"). |
| 15 | 63 | Icebox | #667 0% Penalty APR markets can't enter penalty state | Protocol bug (v3-labeled), not frontend; eligible but ranks below frontend by directive. Good study candidate later. |

Below the line (eligible, unranked this loop): #660/#665/#664 infra tech debt,
#616/#653/#615 mobile/desktop design epics, #552 Lenders Table Fix (near-empty body),
#684 UI/UX Suggestions (grab-bag), #637 Action Center (needs refinement label),
#564 Markets Organizing Issue.

Out of scope by directive: #533, #543, #544, #542, #545, #525, #498, #523, #414,
#413 (token/DAO/raise); #578, #496, #481, #577, #366, #215, #391, #355, #461, #532,
#369, #682 (marketing/biz-dev); #408 (hiring); #398, #218, #217, #207 (community/
design-guide legacy); #603 (legal); #626, #611, #450, #371, #375, #359, #676, #487,
#362, #761, #696, #663 (integrations/features/research, not debt); #506, #449, #436,
#394, #326, #522, #546 (stale v2-era or design-decision-gated — revisit if the team
confirms still live).

## Winner

**#789 — Restrict all borrower UI actions when a borrower is removed from the
archcontroller** (86/100). No tie-break needed.

## Standing close candidates (from the unscoped pass, still true)

- #806 and #815: fixed via wildcat-app-v2 PR #356 (merged 2026-08-18). Operator can
  verify on preview and close both.
