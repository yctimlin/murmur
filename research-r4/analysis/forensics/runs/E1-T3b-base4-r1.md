# E1-T3b-base4-r1 (baseline 3-peer swarm, T3b self-hosted CI platform) — score 7.8

## 1. Outcome
- Score 7.8 from both judges (j1 cov8/cor8/des8/rob8/code7/ux7; j2 cov8/cor8/des8/rob8/code6/ux7). No severe defects. Both judges guessed "team".
- Top penalties (quoted):
  - j1: "a sample 'slow' job that isn't actually slow and leftover draft files"; "JSON only: no anchors or includes"; "Packages are built as zips rather than wheels"; "History pagination is offset-based".
  - j2: "editing a job's command in `pipeline.json` ... left that job path-skipped"; "logs use polling plus byte offsets rather than SSE"; "dashboard JS and parts of the CLI are dense one-line code"; "draft leftovers ship in the tree (`minici/DRAFT-a1.md`, `minici/draft_demo.py`)"; "The CLI prints raw JSON for everything".
- Delivered: about 3,495 lines of py/js/css/html (210 KB, so lines are dense), 55 tests (`python3 -m minici.selftest`, about 30 s). Largest files: engine.py 648, pipeline.py 323, server.py 304, store.py 297, test_execution.py 280.
- Time: active span A0.0–A25.4 against 124.0 wall minutes. result.json reports `active_min` 33.91, while the timeline span is 25.4; I use 25.4. 34 commits; tokens: 15.0M input (380k uncached), 128k output. Not capped (`capped: null`).
- Four VM freezes took about 98 wall minutes:
  - TL:207→208: A6.0, 01:10→01:39
  - TL:306→309: A11.7, 01:44→02:07
  - TL:419→420: A16.5, 02:11→02:40
  - TL:587→591: A21.9, 02:45→03:02

## 2. Phase timeline (active minutes)
| Phase | A range | What happened |
|---|---|---|
| Read brief and claim | 0.2–1.6 | Claims at TL:69, 76, 78. a1 and a2 first both claimed "durability/execution-first". a2 changed to a pipeline compiler at A1.6 "to avoid a1/a3 overlap" (TL:89). |
| Drafting | 1.4–2.9 | Drafts posted: draft/a1 70f8472 at A2.3 (179 lines), draft/a3 f58d709 at A2.5 (75), draft/a2 87c026a at A2.7–2.9 (207). |
| Ranking and selection | 3.0–3.6 | Every peer ran every draft. All three ranked a1 first (TL:140, 147, 157). a1 fast-forwarded main to 70f8472 and posted DONE at A3.6 (TL:160). |
| Contracts and ownership | 3.6–5.5 | a3 posted Store contract and owned Store/API/dashboard/auth/GC/archive (TL:153, 165). a2 owned compiler/sample/CLI and put its draft compiler e4f1222 on main at A4.0 (TL:180). a1 owned engine/scheduler/cache/triggers and wrote PR.md 58374f5 (A4.4). |
| Parallel building | 5.5–13.7 | a3 store fcc4a04 (A6.3). a2 sample and compiler 6734a2e (A7.6). a1 engine 1f0b3c0 (A8.7, 732 lines) and triggers 8e0fe82 (A9.8). a2 CLI and HTTP test harness e98714e (A9.9). a1 execution tests 24f0e32 (A12.8). a3 API/dashboard/archive 48ac6e5 (A13.7). |
| Integration and cross-testing | 13.7–17.7 | Seams fixed: server ready/port 62cd277; CLI to server b1f74ff. Cross-tests found bugs: a2 found the scenario-3 cascade cache bug in a1's engine (TL:404), fixed in 7c92ed3 (A16.9). a1 found CLI bugs (TL:426). a3 platform tests ef5772d. selftest 12a3a85. |
| Review and polish | 17.7–23.7 | Browser review (a1 failed, a3 passed: TL:528, 533). Job-cancel API (TL:539). 400→422 alignment. a2 critical review of secret redaction (TL:591). Large-log EOF fix (TL:629, 636). Exact-cell matrix sample (e971dc3). Secret ≥16-character guard (86f8c66). |
| Final verification and turn ends | 23.7–25.0 | All three ran the full selftest (55 pass). Turns ended: a1 A24.7 (TL:717), a2 A24.9 (TL:726), a3 A25.0 (TL:733). Root ended at A25.4. |

## 3. Per-agent account
**a1 (engine owner, winning draft).**
- Built: the supervisor draft, engine.py (scheduler, cache, retries, locks, redaction, recovery), triggers.py, test_execution.py, DESIGN.md, selftest.py, and the secret guard.
- Holds the most surviving code: 1,401 code lines in final-main blame.
- Did coordination early (PR.md, contract acceptances TL:186, 200) and late (PR ownership TL:584, deadline nagging TL:439, 624).
- Spent about 2 min on a browser review that duplicated a3's (TL:470–528).
- Ended at A24.7. TL:717: "Implemented and pushed to `origin/main` (`0373eca`). Verification: 55 offline tests passed ... Working tree is clean". Reason, TL:698: "Pushing final receipt then ending within120m."

**a2 (compiler, sample, CLI, build acceptance tests, README).**
- 991 code lines and 366 doc/config lines in final blame.
- The strongest cross-reviewer:
  - engine seam for skipped producers (TL:311)
  - scenario-3 cascade-cache failure (TL:404)
  - API log EOF (TL:479)
  - "Critical review remaining" on secret redaction corrupting keys (TL:591)
- Raised one false alarm: "current origin/main ... does NOT include claimed a3 ef5772d" (TL:542), retracted 10 s later (TL:554).
- Ended at A24.9. TL:726: "Implemented and pushed to `origin/main`. Final verification: 55 tests passed in 30.2 seconds." Reason, TL:713: "No remaining a2 findings ... Finishing before hard cap."

**a3 (Store, HTTP API, dashboard, auth, archive, platform tests, DESIGN-storage.md).**
- 1,098 code lines in final blame.
- Longest single build stretch: A8.9–13.7, writing server.py, web/ and archive.py. The timeline flags this as an "idle gap A8.9+4.3", but it was generation, not idle time.
- Did the real-Chrome desktop/mobile/XSS review (TL:533).
- Resolved PR.md and server.py rebase conflicts (TL:636, 659, 680).
- Ended at A25.0. TL:733: "Implemented and pushed ... 55 tests pass ... Documented limitations: Linux required; ... secrets require at least 16 characters." Reason, TL:721: "No unresolved review defects worth fixing within delivered scope".

All three ended because they believed the 120-minute wall cap had arrived (see 6 and 7), not because they ran out of work.

## 4. Coordination costs
- **Discarded work:** a3's draft (75 lines, about 1.3 agent-min) was never used. a3 rebuilt the console from scratch as server.py/web.
- **Draft leftovers shipped:** a1's draft was fast-forwarded onto main (TL:159) and never cleaned up. `minici/draft_demo.py` (54 lines) and `minici/DRAFT-a1.md` shipped, plus a2's `.work/draft-pipeline.json` via e4f1222. Both judges penalized this; no post ever planned the removal.
- **Duplicate work:**
  - Browser review: a3 said "no need duplicate browser effort" at A18.4 (TL:487). a1 kept trying CDP screenshots until A19.7 (TL:528, "please own that to avoid duplicate review"). About 1.5–2 agent-min lost.
  - Large-log EOF fix: a2 claimed it at A22.7 (TL:622, "please don't duplicate"), but a3 also patched it (TL:636). The resulting conflict was resolved at TL:659: "resolved EOF duplicate conflict retaining a2 e971dc3 version".
- **Merge conflicts:** PR.md concurrent appends (TL:636, 680) and server.py EOF (TL:652–659). Each cost under 1 min.
- **Interface seams:** server stdout gave `url` without `port`, and the CLI called `serve()` where only `main()` existed (TL:366). a2 and a3 fixed this in parallel (b1f74ff, 62cd277); a3 noted "no conflict" (TL:407).
- **Integration loss:** none. Every commit on main is a peer's real work, and the draft branches are subsets. No repeated votes, and no ignored messages found; every cross-review finding got a reply and a fix.
- **Wasted alarm:** a2's false "not integrated" warning (TL:542→554).

## 5. Penalty → cause map
| Penalty | Cause in log |
|---|---|
| "slow" job is not slow (j1, j2) | Deliberate a2 design choice at A6.8 (TL:219): "slow uses SLOW_SECONDS default 0.03 timeout=1 so first full run green; separate acceptance overrides to hang." Never revisited. |
| Draft leftovers in tree (j1, j2) | a1's ff-merge of the draft as the base (TL:159) and a2's draft compiler commit e4f1222. No cleanup task was ever posted, and the final rush (section 6) left no slack for one. |
| Definition change does not select a path-filtered job (j2) | No visible cause. Never claimed or discussed; path selection by `paths` globs only came from a2's compiler draft (TL:89). |
| JSON only, no anchors/includes (j1) | a2's choice at A4.0 (TL:180): "JSON format chosen over TOML to support accurate path indexing and standard-library". Templates kept. |
| Zips, not wheels (j1) | a2's sample plan (TL:219, "cli consumes corelib:corelib.zip"). The brief allows a zip, so this is a minor penalty. |
| Offset pagination, polling instead of SSE (j1, j2) | a3's API contract (TL:229). The brief allows ranged reads; never debated. |
| Dense one-line JS/CLI code (j2 code 6) | a3's web/app.js is 23 lines for a full dashboard (written A8.9–13.2), and a2's cli.py was written in one heredoc. Generation style under time pressure; never reviewed for readability. |
| API reference split across README and DESIGN-storage.md (j1) | a3 wrote its own design doc (TL:455, ef5772d) instead of extending a1's DESIGN.md. This is a team-ownership artifact. |
| CLI prints raw JSON (j2) | No visible cause; never discussed. |

## 6. Decision points
1. **A1.6, TL:89 — claims diverged.** a2 pivoted to "pipeline-first compiler" to avoid overlap. The three drafts became complementary layers (supervisor, compiler, console), so two of three drafts were reused rather than discarded.
2. **A3.6, TL:160 — unanimous base selection and immediate ownership split** (TL:153, 165, 180). With contracts on the board by A5.5, the parallel build had no rework afterwards. This explains why the swarm reached a solo-level score.
3. **A12.0–A16.9 — cross-testing caught real engine bugs** (TL:311, 404 → ebb34f6, 7c92ed3). a2's HTTP scenario 3 failed against a1's cache key. This is real review value that a solo run would only get from its own tests.
4. **A12.8–A22.7 — agents tracked the cap in wall time.**
   - TL:328: "~60min remaining by task cap"
   - TL:439: "~24min wall-clock left of120min cap (task started17:05 now18:41)"
   - TL:611: "~3min to cap"
   - TL:624: "Hard cap ~2min left ... More invasive schema-aware redaction risky at deadline"

   About 98 of the 124 wall minutes were VM freezes, so the team stopped after only 25 active minutes. The secret-redaction bug got a 16-character input restriction instead of a real fix (j1: "slightly odd restriction").
5. **A24.4–A25.0 — all three ended** with no open items "within delivered scope". Nobody looked for brief gaps such as definition-change selection, SSE, wheels or draft cleanup.

## 7. Failure-mode tags
- **WALLCLOCK_RUSH (x4 posts, all 3 agents):** TL:328, 439, 611, 624. Turn ends are tied to the cap (TL:698, 713). This is the run's main limiting factor: only 25.4 of a possible ~120 active minutes were used.
- **PREMATURE_END (3 agents, mild):** all ended at A24.7–25.0 while judge-visible gaps remained, e.g. the definition-change bug and the slow job. The cause is the believed wall cap, not a belief that the work was done.
- **SHORTCUT_FIX** (new tag: a defect is "fixed" by narrowing accepted input instead of fixing the mechanism, because of perceived deadline): TL:624, 86f8c66, the 16-character secret minimum.
- **DUPLICATE_WORK (x2, small):** browser review (TL:487 vs 528) and log EOF fix (TL:622 vs 636). About 2.5 agent-min total.
- **DRAFT_LEFTOVER** (new tag: draft scaffolding merged as base and shipped uncleaned): draft_demo.py, DRAFT-a1.md, .work/draft-pipeline.json. Penalized by both judges.
- **MERGE_CONFLICT (x3, trivial):** PR.md twice, server.py once (TL:636, 659, 680).
- **Absent:** DRAFT_AS_PRODUCT, IDLE_PEER, INTEGRATION_LOSS, REVIEW_LOOP, CAP_HIT, PROVIDER_ERROR.

## 8. Time accounting (active minutes; estimated from gaps between calls, attributed to the call they produce)
| Agent (span) | Building | Coordination (board, mail, claim, vote, PR, conflicts) | Reading others' work | Reviewing/testing others' work | Testing own | Idle/waiting | Sum |
|---|---|---|---|---|---|---|---|
| a1 (A0.2–24.7) | 12.5 | 3.5 | 2.0 | 2.5 (draft runs 0.6; duplicate browser try 1.5; CLI review 0.4) | 3.5 | 0.5 | 24.5 |
| a2 (A0.3–24.9) | 10.0 | 4.5 | 2.5 | 3.0 (draft runs 0.6; HTTP suite vs engine 0.6; redaction critique 0.9; EOF fix on a3 server 0.5; browser search 0.4) | 4.0 | 0.6 | 24.6 |
| a3 (A0.4–25.0) | 13.5 | 3.0 | 2.0 | 1.2 (draft runs 0.6; full selftest of others' suites 0.6) | 4.5 (incl. Chrome review of own dashboard) | 0.4 | 24.6 |
| **Swarm total** | **36.0 (49%)** | **11.0 (15%)** | **6.5 (9%)** | **6.7 (9%)** | **12.0 (16%)** | **1.5 (2%)** | **73.7** |

- **Wall vs active:** the run's active span is 25.4 min (A0.0–A25.4) against 124.0 wall min. Root waited the whole time (A0.4–25.4) and is not counted.
- **First product code on main:** a1's draft 70f8472 at A3.6 (TL:159), then a2's draft compiler e4f1222 at A4.0. The first post-selection product module was a3's store fcc4a04 at A6.3 (TL:212), and the first runnable end-to-end sample came at A9.9 (TL:277).
- **Contribution to final main**, in lines inserted on main (`git log --numstat`):

  | Agent | Inserted | Deleted |
  |---|---|---|
  | a1 | 1,587 | 32 |
  | a2 | 1,398 | 86 |
  | a3 | 1,151 | 10 |

  In final-tree blame (code / docs+config): a1 1,401 / 153; a2 991 / 366; a3 1,098 / 44. Load was roughly balanced; no peer idled.
- **Discarded or duplicated:**
  - a3's draft: 75 lines, about 1.3 min
  - duplicate browser review: about 1.5–2 min
  - duplicate EOF fix: about 0.5 min
  - shipped draft leftovers: 72 lines that drew judge penalties

  About 3.5 agent-min in total, under 5% of swarm time.
- **Comparison with solo E1-T3b-solo-r1** (7.9, about 39 active min of one agent):
  - Agent-minutes: the swarm spent 73.7 to reach 7.8, about 1.9x the solo's agent-minutes, with about 0.65x the wall-active span (25.4 vs 39.4).
  - Overhead: only 36 swarm agent-min (49%) went to building. Coordination, reading and reviewing others' work took 24.2 min (33%).
  - Hidden budget: the swarm stopped with roughly 95 active minutes unused because of WALLCLOCK_RUSH. Parallelism bought speed, not quality.
