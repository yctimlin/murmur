# E1-T3b-C1-r4 (T3b self-hosted CI platform, arm C1, score 7.7)

Sources: timeline `timelines/E1-T3b-C1-r4.md` (TL), judges j1/j2, prompts a1-a3/root, `origin.git` log, delivered tree.

## 1. Outcome
- Score 7.7 (j1 7.8, j2 7.6). Both judges: coverage 8, correctness 8, robustness 8, **code 6**, ux 7, design 8/7. No severe defects. Both guessed "single" agent.
- Top penalties (quotes):
  - P1 code style: "code is very dense: about 190 KB packed into roughly 2,900 lines, many of them long semicolon-joined statements" (j1); "many semicolon-joined one-liners and very long lines" (j2); 37 KB `engine.py` "mixes many concerns".
  - P2 thin sample repo: "each package has one unit test. `build.py` puts every package's source on `sys.path`" (j1); "sample packages are very thin, at about 10 lines of code" (j2).
  - P3 manual runs ignore diff: "a manual commit run without `--changed` reports unrelated jobs as `cached`, not skipped" (j1); "Scenarios 2 and 3 pass the changed paths to the API explicitly" (j2).
  - P4 "slow" job never hits its timeout in the shipped pipeline (0.1 s vs 0.5 s) (j2).
  - P5 package graph "declared by hand in `needs`, not inferred" (j2).
  - P6 leftover clutter `draft_demo.py`, `tools/capture.py` (j1, j2).
  - P7 minor: log streaming is offset polling not SSE; dashboard minimal; validator misses unknown dep when a duplicate name exists; bootstrap admin token never expires; cancel/rerun race repeated only 8x (j2).
- Delivered: 3,100 lines of Python (186.8 KB, avg 60 chars/line, 42 lines >200 chars); ~1,050 lines md/js/html/json. Sample packages total 93 lines (src+tests). 27 commits; main = 3676715.
- Active: 33.5 min in timeline (result.json says 42.66; discrepancy unexplained), wall 115.2 min. Tokens: 18.8M input (400k uncached), 133k output. Not capped (`capped: null`).

## 2. Phase timeline (active minutes)
| Phase | A range | What happened |
|---|---|---|
| Read brief/prompt | A0.2-0.8 | All three read prompt; a1's first post fails "channel not found" (TL:60s). |
| Direction claims | A0.8-1.3 | a1 "operational control-plane first" (TL:62), a2 "durable-first ... supervised subprocesses" (TL:74), a3 "compiler-first" (TL:81). Genuinely distinct. |
| Drafts | A1.3-4.7 | Drafts took 2-4 min, not 12: a1 DRAFT at A3.0 (TL:103), a2 A3.3 (TL:112), a3 A4.7 (TL:166). |
| Split proposals (pre-ranking) | A3.3-5.5 | a1 proposes ownership split at A3.3 before seeing drafts (TL:108); a2 counter-split A4.6 (TL:157); schema agreed A5.5 "a1 adopts a2 schema verbatim" (TL:200). |
| Ranking/selection | A5.3-5.9 | Unanimous a2 first (a3 TL:192, a1 TL:204, a2 TL:207). a2 DONE integration A5.9 (TL:214). |
| Plan + ledger | A6.8-6.9 | a2 writes PR.md plan + requirements ledger 5d459f6, "All work claimed" (TL:242). |
| Parallel build | A6.8-15.4 | a1 store (95f38ff A6.8), API+dashboard+archive (f17cb72 A12.1), CLI (c5f4e09 A15.0); a3 compiler/sample (e041aec), plugins (2e909d3 A8.6), acceptance harness 17 scenarios (93978cf A12.5); a2 engine 749 lines (d2f35c4 A13.8). |
| Seam integration | A15.4-21.2 | First full suite 31/37 (TL:393), 40/43 (TL:406), 44/46 (TL:424), 47/49 (TL:487); mismatches: attempts field, /validate payload, /triggers route, CLI flags, GC test16 semantics. a3 "DONE ... 23 acceptance tests" A21.2 (TL:535). |
| Hardening + docs | A18-23 | a2 DESIGN.md (38c4ef4), uncached-prereq + multi-level failure bugs fixed (92ffbd9, 72eb896); a1 README (c4c79ed); a3 scenario table (ff9cee4). Full suite green 56 tests A22.8 (TL:564). |
| Review / browser | A23.4-27.0 | Three separate Chrome/CDP review helpers (a1 A23.8, a3 A24.7, a2 A24.9); a1 imported-rerun 409 fix (d7c1623); a1 CLI-surface test (5b27a5d). All owned ledger items DONE A26.8-27.0. |
| Freeze + last fix | A27.1-30.7 | a2 "No further code planned" (TL:705); a2 UTF-8 log seam (TL:740); a1 fixes it, final commit 3676715 A30.4 (TL:804). Wall-clock "time checks" A30.3-30.4. |
| END quorum | A31.4-31.5 | END 3676715 by a2 (TL:850), a1 (TL:853), a3 (TL:858). |
| Turn ends | A31.9-33.5 | a3 A31.9, a2 A32.0, a1 A33.2, root A33.5. |

## 3. Per-agent account
- **a1** (control plane): store/migrations/v1 fixture/tokens/audit, HTTP API + dashboard + archives, CLI + local mode, archive/GC tests, API tests, README, imported-rerun fix, CLI-surface test, Unicode fix, final ledger. 11 commits on main. Heaviest coordinator (split proposal, schema, API harness contract TL:224, final freeze posts). Ended A33.2 after its 60 s `wait_agent` timed out and it confirmed 3 ENDs via `search_posts` (TL:886): "Completed on `origin/main` at `3676715`. All 62 tests pass; all three peers approved the same final commit."
- **a2** (execution): winning draft (subreaper watchdog, redaction, fairness), plan + ledger, engine.py (668 lines: scheduler, cache, watch, cron, recovery), DESIGN.md, engine hardening tests, `minici/tools/capture.py`. 7 commits. Ended A32.0 (TL:875): "all three peers approved the same final commit."
- **a3** (compiler/sample/plugins/acceptance): pipeline.py, sample-repo + build.py, plugins + worker, the 23-scenario acceptance suite, PLUGINS.md, scenario table. 7 commits. Ended first at A31.9 with "done" (TL:870), seconds after posting its END and receiving the other two.
- All three turn ends are legitimate per the C1 rule (same latest main, unanimous END, ledger without OPEN/CLAIMED). No PREMATURE_END.

## 4. Coordination costs
- **Duplicate work**: three independent Chrome/CDP screenshot tools (a1 inline A23.8, a3 `.work/browser_review.py` A24.7, a2 `minici/tools/capture.py` A24.9). a3 objected at A25.3: "Please avoid spending duplicate effort creating shipped dependency/tooling" (TL:642), but a2 shipped it anyway (ec1fd4a), and judges then called it "leftover clutter". Cost about 2-3 active min per agent.
- **Seam mismatches** (separately built API vs acceptance tests vs engine): about 7 items between A14.3 and A20.8 (engine method names TL:353, attempts/validate/422 TL:393, /triggers route TL:424, CLI flag grammar TL:455, GC test16 TL:522). Each was fixed within minutes; about 6 min of team time in total.
- **Merge conflict**: 1. PR.md ledger rebase conflict at A27.2 (TL:714), resolved with "No lost changes".
- **Branch-only work**: draft/a1 (667d6ae) never merged. That was intended: a1's UI draft lost the ranking and the dashboard was rebuilt in f17cb72. a3's draft content was rebased onto main as e041aec. No INTEGRATION_LOSS.
- **Re-votes**: none. There was one END round on one commit. The full suite was rerun about 8 times across agents during A20-31 (normal, not a loop).
- No messages were ignored. Every seam post got a fix.

## 5. Penalty -> cause map
- **P1 dense code**: no agent raised readability. A grep for semicolon/readab/dense/style in posts gives zero hits. Files were written through heredocs and `python3 - <<` in compound commands, at high speed (a2's 749-line engine in about 6 active min, A7.9-13.8). Reviews checked behaviour only ("finds nothing worth fixing" was always about tests and screens). Cause: verification criteria in the prompt (run, screens, ledger) contain no code-quality check. The code-quality brief requirement ("keep extending for a year or two") was not in the ledger.
- **P2 thin sample**: a3 owned it. Ledger line "DONE ff9cee4: real five-package sample and graph; full sample acceptance01 builds all packages" (PR.md:60) was verified by the suite passing, not against the brief's "real unit tests". Nobody ever proposed deepening the packages (zero hits for thin/more tests). This is SELF_REFERENTIAL_VERIFICATION.
- **P3 manual runs without diff**: an engine semantics decision by a2 (changed=None means run all with cache). a2 at A19.4 handled "first-ever manual cli-only run" (TL:473) but did not derive the diff. Acceptance tests 2/3 pass `changed` explicitly, so the test never exercised commit-diff detection through the API (self-referential test).
- **P4 slow job**: a deliberate decision recorded in PR.md:98: "slow sample defaults to 0.1s under a 0.5s timeout so first-run success is possible; setting DEMO_DELAY=10 demonstrates timeout". This is a documented SCOPE_SHRINK against the brief's "a deliberately slow one (timeouts)".
- **P5 declared graph**: a3 draft direction "explicit package DAG" (TL:81). The brief allows it ("declared, discovered ... or both"). Deliberate, low cost.
- **P6 clutter**: a3 planned to keep `draft_demo.py` "because primitive tests reuse run()" (TL:548). `tools/capture.py` came from the duplicate review tooling (section 4).
- **P7 minor items** (SSE, validator interplay, bootstrap token expiry, 8 repeats): no visible cause. None was ever raised on the board.

## 6. Decision points
1. **A3.3-5.5, split before ranking**: a1 "Proposed post-selection split ... a1 owns HTTP API, auth/audit, persistence ... a2 owns execution ... a3 owns pipeline compiler + sample repo" (TL:108), adopted with a2's schema at A5.5. This clean three-way vertical split, with contracts posted on the board, drove fast parallel build. It is the main reason for the high score.
2. **A5.3-5.9, unanimous pick of a2's containment draft**: "detached-grandchild timeout and controller-kill safety are the hardest platform risk" (TL:192). The hardest robustness parts came first, and robustness later scored 8.
3. **A15.4-21.2, early real-process acceptance harness by a3** (93978cf A12.5): it surfaced every seam mismatch within about 6 min, so the suite went 31/37 -> 56/56 green by A22.8.
4. **A25.2-27.4, freeze decision under perceived deadline**: a1 "Hard cap approaching (~34min remaining from start); aim consensus soon" (TL:635) at A25.2, when only 25 of 120 active min were used. Then a2 "No further code planned" (TL:705) and a3 "supports final freeze" (TL:721). Remaining quality gaps (P1, P2, P3) were never opened.
5. **A30.3-30.4, time-check posts**: a2 "Time check: UTC05:01:56; hard cap from03:11 is ~05:11 (9min left) ... avoid extra full-suite churn" (TL:797); a3 "~10 minutes remain before120m cap" (TL:801). As a result a2 and a3 ENDed after only the 4 focused API tests on the final commit (TL:850, TL:858). Only a1 ran the full 62-test suite (TL:853).

## 7. Failure-mode tags
- **WALLCLOCK_RUSH (3 posts, 2 agents' reasoning)**. Clock sources: `date -u` (a3 A20.7, A25.3, A28.2; a2 A30.0 "Checking the current time") and board `created_at`. VM freezes between A19.3-19.4 (11:39 -> 12:03), A23.8-24.3 (12:07 -> 12:36) and A29.3-29.5 (12:40 -> 13:01) took about 80 wall min. Agents computed the remaining cap from wall time, at roughly 30 active min used. Effect: the freeze was called at A25-27 and the final END review was trimmed. Whether the 120 m cap would really have fired at wall 120 is unknown (protocol says monotonic; run ended at wall 115.2, uncapped). Even so, the agents' belief cut the run at about 1/4 of the active budget.
- **SELF_REFERENTIAL_VERIFICATION (2)**: the sample-repo ledger item was marked DONE because the suite passes (P2); scenarios 2/3 inject `changed` instead of testing diff detection (P3).
- **SCOPE_SHRINK (1, documented)**: the slow job does not time out by default (P4).
- **DUPLICATE_WORK (1 episode, 3 agents)**: browser review tooling.
- **MERGE_CONFLICT (1)**: PR.md, trivial.
- **New tag, NO_QUALITY_GATE**: the review loop checks behaviour, screens and ledger but never code readability or maintainability. The lowest judge axis (code 6, both judges) was never examined. Count: 0 posts about code quality in 893 timeline lines.
- **New tag, SHORT_DRAFT**: drafts took 2-4 min against a 12-min budget. Harmless here, because the draft was a primitive base and not the shipped product. Not DRAFT_AS_PRODUCT.
- Not observed: PREMATURE_END, IDLE_PEER, INTEGRATION_LOSS, REVIEW_LOOP, CAP_HIT, PROVIDER_ERROR.

## 8. Time accounting (estimated, active min)
Method: each inter-event interval is assigned to the category of that agent's preceding call (heuristic script). Compound commands (write + commit + test) blur build and test, so read build+test as one block (about ±2 min).
| Agent | Span | Build | Test/verify (incl. browser) | Read others/own code | Board coordination | Wait (wait_agent) | Other |
|---|---|---|---|---|---|---|---|
| a1 | A0.2-33.2 (33.0) | ~5-9 | ~9-13 | ~6 | ~7 | ~1.3 | ~1.5 |
| a2 | A0.3-32.0 (31.7) | ~7-10 | ~7-9 | ~9 | ~1.5 | ~1.3 | ~3.7 (incl. 3.1-min engine-writing think A7.9-11.0) |
| a3 | A0.5-31.9 (31.4) | ~6-9 | ~8-10 | ~9 | ~3.7 | ~1.3 | ~1.2 |
- Parking used short `wait_agent` timeouts (60 s / 10 s; 7 calls in total, TL:688-865) instead of the "long timeout" the prompt asked for. Waiting was under 1.5 min per agent, so no IDLE_PEER.
- a1 carried most of the coordination (contracts, freeze, final commit). a2 and a3 spent more time reading peers' code at the seams.
- About 75% of the 120-min budget was left unused in active terms (33.5 active min spent).
