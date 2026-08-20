# Loop 1 ranking — 2026-08-19

Board: wildcat-finance/product, 223 open issues, 0 excluded. Scores out of 100 across
ease / benefit / dependency effect / fit (see CLAUDE.md). Top 15 recorded; everything else scored
below 60 for this loop (vague scope, needs people/decisions, epic-sized, or stale).

| # | Score | Issue | Reasoning |
|---|-------|-------|-----------|
| 1 | 88 | #858 Guard restricted withdrawal markets against open transfers | Fresh, crisp AC, suggested copy included. UI-level guard that stops a lender-stranding config (CAF-04/WKI-008). No PR exists. Money-adjacent benefit, single-loop sized. |
| 2 | 84 | #846 Block deposit approvals below the minimum deposit | Well-specified validation fix in lender deposit flow. Small, clear AC. |
| 3 | 80 | #848 Restrict MLA template dropdown to "don't use" + current MLA | Small, well-specified, removes a footgun. |
| 4 | 79 | #838 Hide fixed-term details for non-fixed-term markets | Small conditional-render fix, clear spec. |
| 5 | 78 | #649 Fixed term duration of 2 years not working | Frontend cap mismatch vs contract hardcap; related #658. Fixing one likely fixes both (unlock). |
| 6 | 76 | #833 Missing space between number and currency | Trivial; benefit tiny but near-zero cost. |
| 7 | 75 | #826 Thousand separators on max borrowing capacity | Trivial formatting. |
| 8 | 74 | #815 Withdrawal period > window validation | Mostly fixed via app-v2 PR #356 (merged 2026-08-18). Residual: verify the strictness fix on preview. Close candidate. |
| 9 | 72 | #806 Silent deployment failure (sub-minimum withdrawal period) | Author comments "fixed."; PR #356 merged. Verify + recommend close. |
| 10 | 70 | #792 Fix Safe signing flow | High value (7 broken flows) but a multi-day refactor with persistence + polling design; too big to guarantee in one loop. Good future pick. |
| 11 | 69 | #827 MLA refusal success copy | Trivial copy fix. |
| 12 | 68 | #825 Consistent time units on confirmation screen | Small formatting fix. |
| 13 | 67 | #828 Non-dismissible deployment success dialog | Small dialog-prop fix. |
| 14 | 66 | #503 Template for testing new deployments | Docs deliverable; body already contains the walkthrough — polish + runbook. |
| 15 | 65 | #841 Show access control type in market parameters | Small display addition; masked a production bug once, so mild safety benefit. |

Scored down explicitly:
- #852/#853/#854 exports: PR #340 already open by 0xMcsweeja — in flight, don't collide.
- #772 dark mode: PR #292 open. #679 OTel: PR #257 open.
- #856 Tranching, #742–#748 auctions, #748–#757 risk indices, #762–#769 token infra: epics
  or decision-gated; not single-loop sized.
- #857, #809, #812, #816: investigations needing testnet/admin access we don't have.

## Instant close candidates (no loop needed — operator action)

- **#806** — author confirmed fixed; wildcat-app-v2 PR #356 merged 2026-08-18. Close.
- **#815** — kethcode: "fixed the rest in PR #356"; PR merged. Verify strictness on
  preview once, then close.

## Winner

**#858 — Guard restricted withdrawal markets against open transfers** (88/100).
No tie-break needed.
