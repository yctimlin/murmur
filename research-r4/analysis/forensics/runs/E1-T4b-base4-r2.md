# E1-T4b-base4-r2 — forensic notes

Sources: timeline `timelines/E1-T4b-base4-r2.md` (TL = line), rollouts `lab/ws/E1-T4b-base4-r2/codex-home/sessions/`, origin.git, judges j1/j2.

## 1. Outcome
- Score **1.7** (j1 1.8, j2 1.6) = collapse.
- Judge penalties: "Most of the brief is absent: no matching, FX, categorisation, budgets wired to data, auth, HTTP API, web UI, backup, export or migrations"; "Test suite does not run on a clean Python (unittest finds 0 tests; the tests need pytest) and one analytics test fails"; "Required deliverables missing: DESIGN.md, DATA_FINDINGS.md, IMPORT_SUMMARY.md, smoke test, benchmark". j1 adds "No plugin system: formats are picked by `if name.startswith(...)`" and "`analytics.py` ... that nothing in the book calls".
- Delivered: 366 lines of Python (`core.py` 131, `analytics.py` 181, cli 12, tests 38). README stub, no PR.md.
- Active 22.26 min (span 16.9), wall 92.6. Input 5.30M tokens, output 23k. 3 commits on main.

## 2. Phase timeline (active minutes)
| Phase | A | Who | What |
|---|---|---|---|
| Spawn | 0.0-0.5 | root | |
| a2 drops out | 0.4-0.7 | a2 | 0 tool calls; answers `done` (TL:54-56) |
| Claims | 0.9-1.7 | a1, a3 | a1 claims "parser/data inventory and core ingestion" (TL:69). a3 claims the *same* ingestion core (TL:98). At A3.0 a3 silently switches to an analytics module (TL:117) |
| Drafts | 1.7-7.8 | a1 ingestion (5d4091f, A6.8), a3 analytics helpers (8281455, A7.8) |
| Ranking | 9.2-13.1 | a1 ranks a3 first (TL:255). a3 ranks a1 first (TL:270). They resolve "reciprocal rankings tie" to a1 (TL:346) |
| Integration | 13.1-13.3 | a1 merges both onto main (9f1052b), "DONE winner integration" (TL:354) |
| Review / hand-off | 14.0-16.5 | both run an import smoke test, then post the missing docs/API/UI to "root" (TL:406, 437) and end |
| Turn ends | a2 0.7, a1 15.6, a3 16.5 | |

No PR.md, plan or requirements split. Build work was about 12 active min in total.

## 3. Per-agent account
**a2**: 0 calls. Reasoning (TL:54): "**Resolving conflicting file reading instructions** | **Deciding to defer action due to instruction conflict** | **Preparing to signal completion without file reading**". The forked context carries root's "Never ... read or edit files, or run commands". `done` at A0.7. Never woken.

**a1**: ingestion core draft (131 lines, parser selection by filename if-chain), then integration. From A8.1 it addressed root as a parent: "**Notifying parent about branch status**" (TL:215), with `agents_to_notify:["/root"]`. At A15.1 it posted to /root (TL:406): "Main now intentionally contains only vertical slice (ingestion + analytics); full brief docs/API/UI still absent. Use this as base and record scope honestly in PR.md/DESIGN.md." At A15.3 it told a3: "Winner integration done at main 9f1052b. You can stop/finish your turn if no more work." (TL:417). TURN_END A15.6: "Integrated the winning a1/a3 drafts onto `origin/main` at commit `9f1052b`; import smoke test passed with 5,480 imported rows and 6 quarantined malformed rows." (TL:426).

**a3**: claimed the core, then pivoted to "a standalone analytics/reporting module ... so it can plug into whichever SQLite schema wins" (TL:117). It reviewed and ranked, and found the superset dedup edge (TL:363). Final review (TL:437): "Current tree still lacks DESIGN.md, DATA_FINDINGS.md, IMPORT_SUMMARY.md, PR.md, HTTP/API/UI/auth/migrations/matching/rules; **root should document cuts** and add at least minimal honest stubs/tests." Then "**Checking root status for docs**" (TL:439) and "**Confirming parent agent completion behavior**" (TL:442). It ended at A16.5.

## 4. Coordination costs
- Claim collision on the core (TL:69, 98). a3's draft became an unwired module ("nothing in the book calls" it, j1).
- Ranking confusion: each agent ranked the other's draft first, and resolving it took about 4 active min (A9.2-13.1).
- a1 asked the board "Can you post your draft/ranking if any" (TL:321) for a2, which had already ended. No `followup_task` was used (0 calls).
- Known defects reported but never fixed: the superset dedup shift (TL:363) and the missing docs (TL:437).
- No integration loss: main contains both drafts.

## 5. Penalty -> cause map
| Penalty | Cause in log |
|---|---|
| Brief largely absent | Never claimed beyond ingestion and analytics. After the integration DONE (TL:354) no plan or split followed. Both survivors deferred the remainder to root (TL:406, 437). a2 absent from A0.7 |
| Tests need pytest, 0 run under unittest | a3 noted at A11.8 (TL:324) "tests are pytest-style (no pytest installed here)". Nobody fixed it |
| Failing analytics test | a3 draft. "**Planning analytics bug fix and test updates**" (A12.1, TL:329) was never carried out |
| DESIGN/DATA_FINDINGS/IMPORT_SUMMARY missing | Identified at TL:406 and TL:437 and assigned to "root", which by prompt never edits files |
| No plugin system | a1 draft design (filename if-chain). The brief requirement was never checked |

## 6. Decision points
1. **A0.7, a2 quits on the instruction conflict** (TL:54): one of three builders is gone in under 1 min.
2. **A1.7-3.0, a3 duplicates the core claim, then retreats to a helper module** (TL:98, 117): no second hard part is built.
3. **A13.3, integration receipt treated as completion** (TL:354): the plan step is skipped.
4. **A15.1-16.0, both peers hand the gap list to "root"** (TL:406, 437) instead of claiming it.
5. **A15.3, a1 tells a3 it may stop** (TL:417): mutual release, with no review against the brief.

## 7. Failure-mode tags
- **ROLE_INHERITANCE** (see the base4-r1 definition): 3. a2 quit. a1 "Notifying parent", tasks addressed to /root. a3 "root should document cuts" and "Confirming parent agent completion behavior".
- PREMATURE_END: 3.
- IDLE_PEER: a2 (whole run).
- SCOPE_SHRINK: 1. "Main now intentionally contains only vertical slice" (TL:406).
- DRAFT_AS_PRODUCT: 1. Both 5-minute drafts are the product.
- DUPLICATE_WORK: 1 (core claim collision, partly built twice in planning).
- SELF_REFERENTIAL_VERIFICATION: 1. The final reviews check that the import runs ("5,480 imported rows"), not the brief.
- INTEGRATION_LOSS, MERGE_CONFLICT, CAP_HIT, PROVIDER_ERROR, WALLCLOCK_RUSH: none. REVIEW_LOOP: none (but see the ranking tie).

## 8. Time accounting (active min, gap attributed to the next call)
| Agent | build | coordination | reading others | testing | wait | total |
|---|---|---|---|---|---|---|
| a1 | 6.4 | 4.3 | 1.3 | 0.9 | 2.0 | 15.2 |
| a2 | 0 | 0 | 0 | 0 | 0 | 0.3 |
| a3 | 6.2 | 5.1 | 1.6 | 1.2 | 1.4 | 15.8 |
