# E1-T3b-base4-r2 (baseline 3-peer swarm, T3b self-hosted CI platform) — score 7.6

## 1. Outcome
- Score 7.6 from both judges, with identical sub-scores: cov 8, cor 8, des 7, rob 8, code 6, ux 7. No severe defects. Both judges guessed "single" agent ("The uniform, extremely terse coding style suggests one author", j1).
- Top penalties (quoted):
  - j1: "The dashboard 'DAG' is a grid of job cards with '← needs' text, not a drawn graph"; "Logs update by polling every 1.5s rather than true streaming"; "About 150 KB of Python packed into about 3,200 lines, with many semicolon-chained statements"; "`HEAD /` returns 404"; "On an occupied port the server prints the admin token and then fails"; "Scenario 11 repeats the concurrent cancel and re-run only 8 times"; "`test_cache_inputs` is only 26 lines".
  - j2: "a job whose name is a duplicate gets none of its other checks"; "`limit=abc`, which returns a raw Python `int()` message"; "semicolon-packed lines of up to 251 characters"; "The dashboard is minimal but usable".
- Delivered: 3,241 lines of Python outside sample-repo, plus a 20-line (12.3 KB) static/index.html, README 132, DESIGN 114 and PR 77 lines. 65 tests via `python3 -m minici.selftest` (54 s). Largest files: pipeline.py 460, engine.py 434, test_core_acceptance.py 260, server.py 208.
- Time: active span A0.0–A38.9 against 122.1 wall minutes. result.json reports `active_min` 47.03; I use the span, 38.9.
- Volume: 45 commits. Tokens: 21.3M input (472k uncached), 161k output. Not capped.
- Five VM freezes took about 86 wall minutes:
  - TL:193→194: A5.0, 22.2 min
  - TL:290→291: A9.6, 29.5 min
  - TL:380→381: A15.1, 7.2 min
  - TL:695→696: A30.9, 4.2 min
  - TL:815→816: A36.4, 23.1 min
- Solo reference: E1-T3b-solo-r1 scored 7.9 with a 39.4 active-min span, 4.3M input tokens, 87k output tokens, about 2,659 lines of Python and one commit.

## 2. Phase timeline (active minutes)
| Phase | A range | What happened |
|---|---|---|
| Read brief and claim | 0.3–1.2 | a1 claimed execution/recovery and proposed final ownership right away (TL:66). a3 claimed the operator dashboard (TL:71). a2 claimed compiler-first (TL:74). |
| Drafting | 1.2–4.0 | draft/a1 2dee96b at A2.1 (68 lines). draft/a3 ebed17d at A2.8 (dashboard 19 lines, 11 KB, plus a 20-line fixture server). draft/a2 at A3.6–3.9 (pipeline.py 374 lines plus tests). Contract proposals were posted in parallel (TL:98, 119, 149, 157, 160). |
| Ranking and selection | 3.4–6.1 | Every peer ran the other drafts. a2 ranked a1>a2>a3 (TL:179). a3 ranked a1>a3>a2 (TL:206). a1 ranked a3 first: "UI is strongest operator-facing base" (TL:165, 229). a1 put its draft on main at A6.1 (TL:223). |
| Plan | 6.1–6.7 | PR.md plan 1765e6b. It keeps a3's dashboard and a2's compiler and "replace[s] the prototype engine with the production implementation". |
| Parallel building | 6.7–14.9 | First production code on main: a1 store.py 1e78ac4 at A7.5. Then a2 compiler and sample 9c385ff (A7.4, push race fixed at A9.5, TL:284). a3 auth/API 757f48a (A8.3). a1 cache/redact/supervisor 0c21093 (A9.4). a3 CLI/archive/GC 1229673 (A12.9). a2 plugins/triggers bd12491 (A13.0). a1 engine.py dbff1a3 (A13.5, 395 lines). a1 harness c2ec691 (A14.6). The first full sample run went through the engine at A13.4 (TL:333) and through the CLI at A14.7 (TL:368). |
| Acceptance tests | 14.9–18.2 | a3 HTTP tests 64858fc (A14.9), passing at A15.7 (TL:385). a1 core acceptance, 13 tests, e570210 (A17.3). a2 pipeline acceptance c05286d (A18.0). |
| Cross-review and fixes | 17.6–35.9 | About 25 commits fixed seams found by peers: job cancel (TL:410→448), archive statuses and GC over-deletion (TL:461→486), validation 422 (TL:545), cold-cache prerequisites (TL:560→590), branch-recreation idempotency (TL:568, 677→719), cross-step secret redaction (TL:698→722), import atomicity (TL:755→766). Each peer captured the dashboard in a browser (TL:616, 625, 635, 650). |
| Final verification and turn ends | 34.9–38.9 | A stale cross-owner test assertion failed (TL:777) and was fixed at A35.9 (TL:803). Each peer ran the full suite. Turns ended: a1 A38.1 (TL:864), a3 A38.5 (TL:878), a2 A38.7 (TL:888). Root ended at A38.9. |

## 3. Per-agent account
**a1 (store, engine, supervisor, cache, redaction, harness, DESIGN/PR).**
- Built: 1,321 surviving lines, including engine 434, test_core_acceptance 260, supervisor 161, store 101, testing 100 and DESIGN 114.
- Acted as the de facto integrator and PR owner. It posted 9 REVIEW/FAIL items on peers' seams.
- Ended with "Implemented and pushed to `origin/main` at `88c13e9`. All 64 acceptance/unit tests passed..." (TL:864). The trigger was a full-suite pass, "No remaining code defects after whole-product review" (TL:834). It also pressed peers: "Please finish current read-only reviews promptly within cap" (TL:834, A37.3). That was right after THINK "Checking the current timestamp" (TL:832), at wall 23:36, which is 2 h after start.

**a2 (compiler, sample-repo, plugins, triggers, pipeline acceptance).**
- Built: 1,672 surviving lines, the most of any agent, including pipeline 460, triggers 174, test_acceptance_pipeline 141 and the sample packages.
- Its draft compiler became the product compiler; it was extended but not rewritten.
- Declared "FINAL a2 feature freeze" at A29.2 (TL:661). It reopened for the review findings (TL:700, 738) and a cron fix at A37.0 (TL:827).
- Ended after its own full-suite pass: "All 65 offline tests pass in 54.4 seconds" (TL:888). It spent A37.6–38.5 polling that run.

**a3 (HTTP/auth, CLI, archive, GC, dashboard, README, capture tool).**
- Built: 1,059 surviving lines, including archive 177, server 208, test_http 163, cli 135, README 132 and capture_dashboard 100.
- The dashboard stayed essentially the A2.8 draft: 11.1 KB → 12.3 KB across 4 small edits, at most 5 changed lines each.
- Ended with "Implemented and pushed to `origin/main`. All 64 integration/unit tests passed" (TL:878), after "No remaining review findings... Ready to finish" (TL:875).

All three ended within 0.6 active min of each other, each after a green full suite. No peer was left idle while others worked.

## 4. Coordination costs
- **Draft and ranking ritual (A1.2–6.1, about 15 agent-min).** The "winning" draft/a1 (68 lines) went to main at A6.1 and was then superseded: PR.md says it would "replace the prototype engine". a3 deleted it at A26.8 with "removed obsolete draft executables" (b33d5da: draft_a1.py 68 and draft_server.py 20 lines). The two "losing" drafts (a2 compiler, a3 UI) are what survived. The vote never chose the base.
- **Discarded or leftover work:** 88 draft lines deleted. `.work/draft.json` (11 lines, a2 draft fixture) still ships in the tree.
- **Duplicate work:**
  - Two real-server HTTP harnesses: a1 `testing.ServerProcess` (TL:364), and a3's self-contained `HTTPServerProcess` in test_http.py (TL:379, "Harness self-contained").
  - All three ran browser captures of the dashboard (a2 TL:616, a1 TL:625/639, a3 TL:635/650).
  - The full suite ran at least 9 times across peers from A18.0 to A38.5.
- **Merge friction:**
  - Push race (TL:284).
  - PR.md conflict "despite ownership message" (TL:732), resolved at A33.8.
  - Interface name mismatch TriggerService vs TriggerManager (TL:295, 312), fixed by an alias at A13.8.
  - STEP_TYPES vs available_step_types (TL:335 → A17.3).
  - Stale migration-shape assertion after a3 changed the API shape (TL:777 → 2767f4e).
  - All were small, about 3 agent-min in total.
- **Integration loss:** none. All draft commits were rebased into main; the draft/* branches hold no unique surviving work.
- **Ignored messages:** none found. Every REVIEW post got an ACK or a fix.

## 5. Penalty → cause map
| Penalty | Cause in log |
|---|---|
| Dashboard DAG is a card grid, minimal UI | The UI is a3's 1.6-minute draft (A1.2–2.8) carried "wholesale" (TL:206). Later work on it was checks (screenshots, XSS, viewer controls), not build-out. No one claimed a drawn graph. |
| Logs poll instead of SSE | A design choice: DESIGN lists "polling instead of SSE" as a limit. It was never claimed or discussed on the board. |
| Dense, semicolon-packed code (code 6) | Model style. Solo got the same code scores (6/6), so it is not swarm-specific. No reviewer posted about readability. |
| Duplicate job name suppresses other checks; `limit=abc` raw error; `HEAD /` 404; token wasted on busy port | No visible cause. These paths were never exercised by any of the 3 reviewers. Reviews covered seams between owners, not single-owner edge input. |
| Scenario 11 only 8 repeats | a1 wrote `for _ in range(8)` (test_core_acceptance:125). No one questioned it. |
| Thin `test_cache_inputs` (26 lines) | a2 wrote it quickly at A13.8 (7214907). |
| Scenarios 2/3 pass changed paths explicitly | a2's pipeline acceptance design. Watcher diffing is tested separately. |

## 6. Decision points
1. **A1.1 (TL:66): a1 proposed final ownership before any draft existed.** The others accepted within 3 minutes (TL:74, 119, 157). The split held to the end, which made the later draft vote largely moot. Every module had a single owner, so parallel building was cleanly separated.
2. **A4.8–6.1 (TL:179, 206, 223): ranking picked a1 "for the difficult execution objective".** a1 immediately planned to replace its own draft. The real product base came from three separate fresh builds on the agreed contract.
3. **A13.3–22.7 (TL:329, 351, 509): wall-clock time read as remaining budget.** Posts said "~55m remain by wall clock" at A13.3 and "~35min cap remains" at A22.7. The real active time was 13 and 23 of 120 minutes; the VM freezes made wall time look nearly spent. These posts set the urgency for feature freezes (a2 at A29.2) and the final wrap-up (TL:834).
4. **A17.6–35.9: cross-owner review found real defects.** Examples: secret redaction across steps, GC over-deletion, cold-cache prerequisites, import atomicity. This is the main value the swarm added over its build phase, and it probably explains robustness 8.
5. **A37.3 (TL:834): a1 declared "no more code work needed absent concrete defect"** after checking the timestamp. All peers ended within about 1.4 min.

## 7. Failure-mode tags
- **WALLCLOCK_RUSH (3 posts):** TL:329, 351, 509, plus a1's "within cap" at TL:834. The impact was moderate: the run ended at A38.9 of a 120-minute cap. The review queue was empty, so the cost was probably the unexamined single-owner edge cases.
- **DRAFT_AS_PRODUCT (1, partial):** the dashboard draft shipped almost unchanged (11.1 → 12.3 KB). The compiler draft was a real base and was extended to 460 lines.
- **DUPLICATE_WORK (minor, 3 instances):** two HTTP harnesses, triple dashboard captures, repeated full-suite runs.
- **COORDINATION_THEATER (new tag: a ritual whose decision is not used):** the draft vote chose a base that the plan replaced at A6.7. About 15 agent-min went to drafts and ranking, and 88 lines were deleted later.
- **MERGE_CONFLICT (1):** PR.md at TL:732, plus a push race at TL:284.
- **SELF_REFERENTIAL_VERIFICATION (weak):** each peer reported "No remaining review findings" (TL:875), yet the judges still hit unvalidated edge input. Coverage was nevertheless high.
- **Not observed:** PREMATURE_END in the strong sense (the brief was met, with no severe defects), IDLE_PEER, INTEGRATION_LOSS, CAP_HIT, PROVIDER_ERROR.

## 8. Time accounting (active minutes)
**Method.**
- For each agent, every tool call from the rollout is mapped from wall time to active minutes by interpolating against the timeline.
- Generation time (from the previous output to the call) is split by character weight over the call's segments: board/mail, writing a file, reading peer-owned files, and so on.
- Execution time goes to the call's non-board segments.
- "Building" includes writing one's own tests.
- "Review/test others" includes running peers' drafts, browser captures of a peer-owned UI, and runs of the integrated full suite.
- Coordination includes git pull/push/commit (shown separately).
- Testing of one's own work is undercounted, because runs chained after `cat >` writes count as building. Expect about ±2 min per cell.

| Agent | Building (product + own tests) | Coordination (board/mail/claim/vote + git) | Reading others' work | Review/test others (incl. full suite) | Testing own | Orientation | Idle/waiting | Total |
|---|---|---|---|---|---|---|---|---|
| a1 | 20.1 (16.6 + 3.5) | 9.9 (9.6 + 0.3) | 3.1 | 3.7 | 0.3 | 0.3 | ~0 | 37.5 |
| a2 | 22.2 (16.5 + 5.7) | 7.6 (6.3 + 1.3) | 2.2 | 3.5 (about 0.9 of it polling the final suite) | 1.5 | 0.8 | ~0.9 inside review | 37.9 |
| a3 | 22.9 (20.7 + 2.2) | 7.9 (6.5 + 1.4) | 1.5 | 2.1 | 3.0 | 0.4 | ~0 | 37.7 |
| **Swarm** | **65.2 (58%)** | **25.4 (22%)** | **6.8 (6%)** | **9.3 (8%)** | **4.8 (4%)** | **1.5** | **<1** | **113.0** |

- **Spans:** run wall-active span A0.0–A38.9. Root used about 0.5 active min; it was a spawner/waiter. Peers were active A0.3–38.7, with no gap over 3 active min (timeline header).
- **Comparison with solo:**
  - Solo E1-T3b-solo-r1 delivered 7.9 in a 39.4 span with about 39 agent-min.
  - The swarm used 2.9× the agent-minutes (113 vs 39) in the same span. Its pure building time alone (65.2) is 1.7× the solo's entire time, and it scored 0.3 lower.
  - Coordination plus reading plus reviewing others is 41.5 agent-min, more than the whole solo run.
  - The swarm consumed 4.9× the input tokens and 1.9× the output tokens.
- **First code:**
  - Real product code on main: A7.5 (a1 store.py 1e78ac4). Draft code was on main from A6.1 (2dee96b, later deleted).
  - Core execution engine: A13.5. First end-to-end sample run: A13.4.
  - Solo wrote its first 22 KB of product code at A2.7, but committed to main only once, at A38.8.
- **Contribution to final main** (surviving lines by git blame, including sample-repo and docs; insertions in parentheses):
  - a1: 1,321 (1,430 ins / 44 del)
  - a2: 1,672 (1,718 / 86)
  - a3: 1,059 (1,154 / 165)
  - murmur seed: 25
  - Discarded: 88 draft lines. Duplicated: about 35 lines of HTTP harness. Leftover: an 11-line draft fixture.
