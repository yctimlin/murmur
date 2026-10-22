# E1-T3b-base4-r3 (T3b self-hosted CI platform, arm base4) — score 7.775

## 1. Outcome
- Score 7.775 (j1 7.8, j2 7.75; both cov 8, corr 8, design 8, rob 8, code 6, ux 7). No severe issues. Guesses: team / single.
- Top penalties (quoted):
  - both: "the sample `slow` job (timeout 2s, sleeps 0.05s) never times out in the shipped pipeline; only the tests show a timeout"; "leftover `minici/draft-pipeline.json`"
  - j1: "a manual run defaults to the label `main` even when the repo's branch is `master`"; "the validator silently drops a duplicate-named job, so errors inside it ... go unreported"
  - j1: "`engine.py` packs 40 KB into 557 lines of semicolon-chained statements"; "the cache key hashes all secrets, not only the ones a job references"; "concurrency race test runs only 12 iterations"
  - j2: "if the server can't bind its port, `serve --bootstrap-user` has already created the admin user and token, but the token is never printed"; "fairness is round-robin over (repo, branch) lanes"
  - Positive vs C2: "Corelib commit: downstream rebuilt and `toolchain` was a cache hit" (j1); sample has 10 jobs.
- Delivered: 39 code files, 3515 lines / 226 KB; tests 1289 lines, 66 tests (`python3.12 -m minici.selftest`, ~38 s). 32 commits; `draft/a1..a3` branches remain.
- Active 46.4 (run span 36.1), wall 145.5 (> 120 cap, `capped: null`, so the cap is not wall-clock). Tokens: input 19.6M (uncached 0.44M), output 151K.

## 2. Phase timeline (active minutes)
| Phase | A | Who | What |
|---|---|---|---|
| Claims | 0.9-1.4 | all | a1 control plane + dashboard; a2 switches to "developer-first pipeline compiler" after seeing a1's claim (A1.4); a3 "run evidence and reproducibility" |
| Drafts | 1.4-3.7 | all | a1 `10ea655` A1.8 (52 lines, simulated lifecycle); a3 `cecf9cd` A3.3 (97 lines, real builds + export); a2 `47baa61` A3.6 (423 lines, compiler + 7 tests) |
| Contracts in parallel with ranking | 2.6-6.5 | a1 leads | interfaces A2.6, ownership A2.8, Store schema A3.6, "SCHEMA FREEZE" A5.2 |
| Ranking | 4.3-5.0 | all | a1: 1) a3; a2: 1) a3; a3: 1) a2. a3 base wins 2/3; integrated `9450680` A6.1 (receipt hash corrected A7.5) |
| Build | 6.1-20.7 | a1 engine/store/supervisor/scheduler/GC/plugins; a2 compiler/cache/redaction/sample/acceptance harness; a3 API/CLI/dashboard/auth/archive | a2 helpers `6b86d47` A7.5; a1 engine `f7b5f20` A10.5 (662 lines); a2 sample `ee6626c` A10.8; a2 harness `c6ba5b8` A13.5; a3 API `cff1ba4` A14.8 (588 lines); a1 core tests `861e7b3` A15.0; a1 HTTP 9/10/15/19 `c22b600` A18.3; a2 16 scenarios `7009b39` A20.2 |
| Seam review | 14.5-26.1 | all | supervisor stdout-close hang (a2 A14.5), list_repos/register_repo mismatches (a2 A15.2), "CRITICAL archive.import_run uses `with store.connect()` ... autocommit" (a1 A15.6), JSON-serialized redaction leak (a1 A18.0), plugin teardown race (a3 A25.6), import crash residue (a3 A26.1) |
| Hardening + docs | 20.5-31.6 | all | drafts removed from main (a1 A20.5, `9d273d3`); compiler hardening `a296057` A24.0; README `682eb13` A24.5; DESIGN `215c6ed` A27.0; shutdown fix `7a590a3` A29.4 |
| Rush | 29.3-34.9 | a2, a1 | "a2 at 05:02 UTC (120m cap ~05:17)" (A29.3, TL:602); a1 "Time remaining ~14min" (A29.6); a1 "Clock now shows 05:35 > cap" (A34.5, TL:754) |
| Late real bug | 32.4-33.7 | a2, a1 | "FAIL actual README quickstart! ... nested repo returns422" (a2 A32.4). Fixed twice: a1 `040d18e` A33.0, a2 `c06765e` A33.7 |
| Finish | 34.9-35.9 | all | a1 TURN_END A34.9 (before final suite); a3 final receipt `7c23887` A35.6; a2 TURN_END A35.9 |

## 3. Per-agent account
- **a1 (engine/store/supervisor/scheduler/recovery/GC/plugins, DESIGN.md)**: the largest builder (~12.5 min build). It wrote core and HTTP tests for its own scenarios (9/10/15/19), was a strong reviewer (autocommit import, JSON redaction), and removed the drafts. TURN_END A34.9: "Latest local suite passed 64/65 tests; the remaining browser synchronization failure is fixed in the latest pulled commit, with a3 handling final verification." It ended on the belief that the cap had passed (A34.5), **before seeing a green run on the final head**.
- **a2 (compiler, cache key, change detection, redaction, sample repo, harness, 16 acceptance scenarios)**: designed `inputs` separate from `paths`: "This resolves acceptance 2 vs 3: a toolchain metadata job is selected on corelib/tools changes but hashes only tools" (A9.5). It found the quickstart bug by running the real README flow (A32.4). TURN_END A35.9 after a 66/66 run.
- **a3 (API/CLI/dashboard/auth/archives/README/PR)**: built the authenticated API and dashboard, the browser regression test, and fixed CSV secret scrubbing (A32.9). It wrote the final verification receipt `7c23887`. TURN_END A35.8.

## 4. Coordination costs
- Draft phase about 6 active min. The winning a3 draft was a 97-line prototype, and the production modules came from the contracts, not the draft. A remnant (`minici/draft-pipeline.json`) shipped and was penalised by both judges.
- Crossed schema posts led to a "SCHEMA FREEZE" (A5.2) and a stale receipt hash (A6.1 -> A7.5).
- Interface seams between separately built modules surfaced late (A15.2-18.0) because the API (a3) and engine (a1) landed only at A10.5-14.8.
- DUPLICATE_WORK: the nested-snapshot fix was done by both a1 (`040d18e`) and a2 (`c06765e`) within 0.7 min ("a1 crossed messages—please retain this integrated engine fix", a2 A34.3).
- No lost work on branches; drafts intentionally retained on `draft/*`.

## 5. Penalty -> cause map
| Penalty | Log cause |
|---|---|
| Sample slow job never times out in shipped pipeline | a2's sample (A10.0 "10 jobs (... flaky/slow/secret-check)") sets slow below its timeout so the main run stays green; timeouts are only tested synthetically (a1 A15.0). Planned, never reconciled with the brief. |
| Leftover draft-pipeline.json | a1 A20.5 "Keeping a2 draft-pipeline.json if used as compiler example". This was a deliberate keep. |
| Branch label defaults to main; duplicate-job validator gap; bootstrap token lost on bind failure | No visible cause; not covered by tests. a2's compiler hardening (A21.9-24.0) addressed other malformed inputs. |
| Dense engine.py | No visible cause; a1 wrote 662 lines in one commit (A10.5). |
| Secrets hashed globally in cache key | a2 A5.7 "cache_key(..., secrets=None) ... values hashed into key". This was a contract decision. |
| 12-iteration race test | a1 A15.0 "12 simultaneous cancel/rerun". Never strengthened. |

## 6. Decision points
1. A2.6-5.2: a1 drives interface contracts during the draft phase, so ranking and contracts overlap. This was effectively a spine by contract.
2. A9.5: a2 separates cache `inputs` from selection `paths` explicitly to satisfy scenarios 2 and 3 together. This is the decisive difference from E1-T3b-C2-r2's scenario 3.
3. A15.6 / A18.0: code review finds two real data-integrity and security defects (autocommit import, JSON-byte redaction). No pre-written check would have caught these.
4. A29.3-34.5: wall-clock reading ("120m cap ~05:17", then "Clock now shows 05:35 > cap") frames the end. About 36 active min had been used.
5. A32.4: a2 runs the actual README quickstart and finds the nested-repo snapshot bug, the most user-visible defect. It was found by acting as the user, not by the suite (the suite used temporary standalone repos).

## 7. Failure-mode tags
- WALLCLOCK_RUSH (4 posts: a2 A29.3, a1 A29.6, a1 A34.5, a2 A34.8 "cap exceeded during apparent clock jump"): the end was driven by a perceived cap.
- PREMATURE_END (a1, 1): it ended at A34.9 without a passing run on the final head ("64/65"); a3 and a2 completed verification.
- DUPLICATE_WORK (1): nested snapshot fix.
- DRAFT_AS_PRODUCT (mild): draft leftovers only.
- MERGE_CONFLICT: none serious ("docs conflict resolved", a3 A31.6). INTEGRATION_LOSS: none.

## 8. Time accounting (heuristic, from call gaps; build includes writing tests)
| Agent | build | coordination | reading others | testing/review | idle |
|---|---|---|---|---|---|
| a1 | 12.5 | 5.9 | 5.6 | 9.8 | 0 |
| a2 | 13.2 | 5.3 | 8.2 | 7.1 | 0 |
| a3 | 13.1 | 4.0 | 7.9 | 9.7 | 0 |

## Verification profile (for the C2 contrast)
- The acceptance tests were written after building, by the module owners. a2's harness landed at A13.5 and its 16 scenarios at A20.2; a1's 4 scenarios at A18.3. The suite went from 30 tests (A18.9) to 66 (A35.6).
- Most of the serious defects were found by reading the code (A14.5, A15.2, A15.6, A18.0) and by running the real quickstart (A32.4).
