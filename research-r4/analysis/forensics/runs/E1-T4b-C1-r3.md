# E1-T4b-C1-r3 — forensic notes

Sources: timeline `timelines/E1-T4b-C1-r3.md` (TL = line), rollouts, origin.git, delivered PR.md, judges j1/j2.

## 1. Outcome
- Score **7.4** (j1 7.3, j2 7.5). No severe defects from either judge.
- Penalties: j1 "Its weak points are thin heuristics on this data and code that is hard to read"; "a quoted field followed by spaces quarantines the whole file"; "the crash when the port is in use and the uninformative recurring output". j2 "The browser UI has only one real chart"; "the demo crash when `.work/` is missing, the 3.12 runtime being unverified, and comparison taking 1.8s against a 2s limit". Code score 5/5.
- Delivered: about 2,006 lines of Python plus a JS/HTML UI, 30 tests, PR.md with drafts, a `## Requirements` ledger (about 25 DONE rows, 1 DESCOPED: Python 3.12 execution), DESIGN, DATA_FINDINGS, IMPORT_SUMMARY, RULES, capture script.
- Active 34.99 min (span 25.9), wall 125.8. Input 18.56M tokens, output 114k. 27 commits.

## 2. Phase timeline (active minutes)
| Phase | A | What |
|---|---|---|
| Start | 0.4-0.5 | All three peers start on the task. a3: "I'll read the assigned instructions and follow them." (TL:55). No launcher-conflict reasoning visible |
| Claims / directions | 0.8-1.4 | Three distinct directions: a1 provenance/reconciliation console (TL:68), a2 review/dashboard UI (TL:77, 99), a3 reporting-first (TL:102). At A1.4 a1 already proposes a full-brief domain split (TL:107) |
| Drafts | 1.4-3.9 | All three drafts pushed: a2 641db1a (A3.1), a1 8e2f474 (A3.3), a3 343d0cf (A3.9) |
| Role negotiation | 3.3-5.5 | Crossed proposals, then "Freeze original latest accepted role proposal" (TL:172): a1 ingestion/schema/migrations/backup, a2 app/API/auth/UI/CLI, a3 finance domain (rules, jobs, matching, FX, budgets, reports, exports, benchmark) |
| Ranking | 4.3-4.6 | a1 ranks a2 first (TL:191), a3 ranks a2 first (TL:199), a2 ranks a1 first (TL:204). a2 wins 2/3 |
| Integration + ledger | 5.3 | a2: "DONE winning a2 draft integrated into origin/main with shared PR.md plan + requirements ledger" (TL:223) |
| Building | 5.8-16 | Parallel builds with interface contracts posted on the board (schema TL:158, auth schema TL:188, finance signatures TL:254, TL:264). Main commits: core 1ba55d3 (A5.9), app/server ebf8924 (A9.4), finance e640101 (A10.4), reports a2e4f66 (A12.1), finance tests + benchmark 5cb5872 (A14.9), API tests + smoke 997587b (A15.7) |
| Cross-review / seams | 10.6-22.5 | Seam posts: a1's review of app.py names (TL:336), a3 scope review (TL:386), a2 security seam on comparison leakage (TL:404), a3 demo path (TL:483), a2 browser UX fixes (TL:517), a3 refund scope leak fixed (TL:528), a3 explanation fix (18f0e36, A22.5) |
| END votes | 22.9-25.3 | a2 END fb81a44 (TL:700), voided by a3's push (TL:723). a3 raises a stale BLOCK (TL:697), then ACKs it (TL:718). Final END 18f0e36 from a2 (TL:749), a3 (TL:783), a1 (TL:788) |
| Turn ends | 25.5-25.8 | All three cite the shared END commit |

## 3. Per-agent account
- **a1** (ingestion/schema/migrations/backup/docs): core store, quarantine fix/dismiss, revert, 3 migrations plus committed v1 DB, staged-import tests, DATA_FINDINGS, DESIGN, IMPORT_SUMMARY, upgrade-path end-to-end test (c56dfde). It also did a whole-product screenshot review (TL:735). TURN_END A25.5: "Implemented and pushed to `origin/main` at `18f0e36`; all three peers approved that commit. - 30 tests pass ..." (TL:797).
- **a2** (application facade, auth, scope, API/OpenAPI, server, UI, smoke, capture): 1842-line app commit (ebf8924). It tested every API permission boundary (997587b), did browser checks at 1440 and 390 widths, and exercised a real conflict dialog (TL:672). TURN_END A25.7 (TL:806) lists the limitations: Python 3.12 not available, mobile budget form scrolls.
- **a3** (finance engine): rules/jobs/learning/splits, matching, FX, budgets, reports, ledger export, 250k benchmark, RULES.md, scope fixes. TURN_END A25.8 (TL:811).
- Why they ended: the C1 quorum rule. a1 (TL:788): "a3 please END same 18f0e36 so we can all finish now."

## 4. Coordination costs
- Role proposals crossed twice (TL:141, 158, 172: "Crossed messages again!"). It cost about 1 active min and was resolved by a1 freezing the earlier proposal.
- Premature receipts: a2's "DONE ... integrated" came before its push had succeeded (TL:307, 316). a2's capture receipt ran ahead of its push (TL:611, 635).
- PR.md merge conflicts while 3 agents edited ledger rows (TL:603, 635: "resolving consecutive PR conflicts").
- One stale BLOCK: a3 reviewed an old app.js (TL:697, 718). One END vote was voided by a later push (TL:723).
- Draft branches stayed off main by design (drafts were superseded). No production work was lost.
- Coordination was a large share of time (about 40%), but it carried contracts and seam bugs rather than polling.

## 5. Penalty -> cause map
| Penalty | Cause |
|---|---|
| Hard-to-read code (5/10) | Three agents writing dense code fast in large heredoc commits (ebf8924 +1842, 5cb5872 +2384). No refactor pass was in anyone's ledger |
| One real chart only | UI owner a2 prioritised permissions and conflict handling. Charts were never a separate ledger item visible in posts |
| Comparison 1.8 s vs 2 s | a3 switched reports to exact Decimal SQL UDF at A16.9 (TL:492) and accepted 1.75 s |
| Mobile budget form clipping | Found by a1 at A24.4 (TL:735). Not fixed because of the wall-clock "hard cap" belief (TL:759, 771, 773) |
| 3.12 unverified | Environment (only 3.13.5). DESCOPED honestly in the ledger |
| Demo crash without `.work/`, port-in-use crash | No visible cause. The demo/capture helpers depended on a local `.work` dir |

## 6. Decision points
1. **A0.4-0.5, all three peers accept the task** (TL:47-55). The forked-launcher conflict that killed a peer in both base4 runs did not fire here.
2. **A1.4, the split covers the whole brief before drafting ends** (TL:107): "a1 schema/ingestion/plugins/revert/quarantine + real data tests; a2 application/auth/API/UI/CLI; a3 categorisation/jobs/matching/FX/reports/budgets/exports/benchmark."
3. **A5.3, the requirements ledger lands in PR.md together with the integration** (TL:223). From then on the work is driven by OPEN/CLAIMED items, not by "integration done".
4. **A13.7-17.9, seam and security reviews against the brief** (TL:404, 465, 528), not just "it runs".
5. **A22.9-25.3, same-head END quorum** with one void and re-vote. It ended on 18f0e36 with the ledger closed.

## 7. Failure-mode tags
- WALLCLOCK_RUSH: 1 (mild). a1 "It is 12:05UTC (~23m until 120m cap)" at A20.3 (TL:587). "now past 120m hard cap" at A24.8 (TL:759), at only A24.8 active. The mobile CSS fix was dropped: "I do not block ship on that polish."
- REVIEW_LOOP: 1 (mild). One voided END and one stale BLOCK, about 2.5 active min.
- MERGE_CONFLICT: 2 (PR.md ledger edits, TL:603, 635).
- DUPLICATE_WORK, IDLE_PEER, INTEGRATION_LOSS, PREMATURE_END, SCOPE_SHRINK, ROLE_INHERITANCE: none.

## 8. Time accounting (active min, gap attributed to the next call)
| Agent | build | coordination | reading others | testing | wait | total |
|---|---|---|---|---|---|---|
| a1 | 11.8 | 10.4 | 0.6 | 2.2 | 0 | 25.2 |
| a2 | 9.7 | 10.9 | 0.7 | 3.3 | 0.4 | 25.3 |
| a3 | 14.7 | 6.3 | 1.2 | 1.8 | 1.1 | 25.3 |

"Coordination" includes generating long board posts that carry schemas and contracts. Building totalled about 36 active minutes, versus about 11-12 in the base4 collapses.
