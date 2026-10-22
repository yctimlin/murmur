# T1b contrast: collapse runs vs high runs vs solo

| Run | Score | Active min (span) | Delivered size | Input tokens | Ending |
|---|---|---|---|---|---|
| C1-r2 | 2.45 | 53 (cap at 120 monotonic) | ~490 lines | 18.8 M | quorum at A43.4, then CAP_HIT from parking |
| C2-r2 | 2.55 | 35.5 | ~510 lines | 9.8 M | WALLCLOCK_RUSH at A29.3, 20 ledger rows DESCOPED |
| C1-r1 | 7.7 | 19.9 | ~2170 lines | 12.7 M | END quorum at A19.6 |
| C2-r1 | 7.85 | 27.1 | ~3000 lines | 17.2 M | END quorum at A27.1 |
| solo | 6.95 | 32.0 | ~1900 lines | 2.0 M | voluntary end at A32, thin UI |

The prompts are identical within each arm apart from ports (verified with diff). The low and high outcomes therefore come from run-time decisions, not from instructions.

## C1: r2 (2.45) vs r1 (7.7). Same draft, rank and ledger protocol

1. **What the drafts were.**
   - r1: peers first collide on one direction, then re-diversify into competing whole-product directions (C1-r1 TL:90-105). Each draft is a 28-39-line HTML mock-up. The team ranks by looking at real Chrome captures.
   - r2: the claims are complementary layers (persistence, ingestion, UI; C1-r2 TL:77, 108, 115, 121). Each "draft" is a third of a backend, 76-226 lines.
   - The r2 ranking therefore chose a partial *codebase* as the base (TL:247-291). a1's persistence draft was discarded and rebuilt as 55 lines to fit a2's schema (TL:342-370), which created the overrides schema bug.
2. **What the ledger meant.**
   - r1: the ledger was written after selection. It had 22 rows, all `CLAIMED`, with a CONTRACT.md of interfaces (TL:233-236). Every row needed new code, so the commits were 190-1658 lines.
   - r2: the ledger had 16 coarse rows and **7 were pre-marked `[x]` from the 226-line draft** (TL:392). Each remaining row was closed by a 1-55-line commit.
   - Brief items missing from the r2 ledger, such as tags, saved searches, the watcher, near duplicates and log stats, were never claimed.
3. **What the review tested.**
   - r1: reviews were Chrome captures of UI flows, seam bugs were posted as FAIL, and a 10× benchmark was run.
   - r2: "review" meant `py_compile`, 3 unit tests and a search for "annealing". The searches never used an experiment ID, which is exactly the judges' crash (FTS on `EXP-2023-001`).
4. **How the run ended.**
   - r1: all peers ended within 0.2 min of the quorum.
   - r2: a2 parked after its END ("Waiting for root status confirmation", TL:1145). Root never messages peers, so about 69 of 112 freeze-excluded minutes were spent idle until the cap.
   - The cap did not change the r2 score: main was final at A40.8.

## C2: r2 (2.55) vs r1 (7.85). Same spine and acceptance protocol

1. **Who claimed the spine.**
   - r1: a1 claimed SPINE at A0.7 (TL:61) and posted SPINE DONE at A5.1 with 360 lines, every module wired, including a browser shell.
   - r2: a1 claimed ACCEPTANCE at A0.9 with "no product code until SPINE DONE" (TL:64). a2 assumed root would build the spine (TL:193). The first spine claim came at A8.4, a contested second claim at A11.2, and SPINE DONE only at A17.2 with 151 lines and a JSON root stub.
   - a2's duplicate spine (A11.2-24.6) was reset away.
2. **What acceptance tested.**
   - r1: acceptance tests were derived from the brief: 35 ledger rows, plus a cross-check against the brief that found the people-graph gap (TL:417).
   - r2: the browser check was "status 200 at /" (acceptance/run.py:129), so the JSON stub was marked DONE. The import check did not compare curated rows.
3. **How time was read.**
   - Both runs read the wall clock from the board's UTC `created_at` stamps.
   - r1 read it at A18.2, when only 88 wall minutes had passed ("~33min hard cap left").
   - r2's freezes fell early, so at A29.3 the wall clock showed about 120 min. a3 declared "hard cap reached" (TL:591), a1 copied it within 20 s, and 20 rows were turned into DESCOPED.
   - Whether the rush hits before or after the build-out depends on when the VM freezes, i.e. luck. In C1-r1 the rush hit at A18.3, after everything was built.

## Swarm vs solo
- The solo agent built about 1900 lines in about 25 active minutes, using 2 M tokens, with no coordination.
- It lost points only on the UI (UX 5): the sandbox blocked serving (TL:66-68), so the UI was never exercised, and it ended voluntarily with 88 minutes left.
- High swarms beat solo on UX, 8 vs 5, because peers ran headless Chrome reviews of the UI. Collapsed swarms lost to solo by 4.5 points because of DRAFT_AS_PRODUCT and WALLCLOCK_RUSH.
- Swarms spend 9-19 M tokens, and 30-60% of each agent's active time goes to coordination.

## Mechanisms that would have changed the outcome, and their predicted log signatures

1. **Expose real elapsed time to agents.** Give agents freeze-excluded remaining time (murmur's monotonic clock) via a tool or the environment, and forbid stopping on wall-clock or board-stamp readings.
   - Affects: C2-r2, and C1-r1 late.
   - Predicted signature: no "hard cap reached" posts before monotonic minute ~110; no `DESCOPED (… hard cap …)` rows; the C2-r2 build phase continues past A30.
2. **Auto-terminate on quorum.** murmur should end the run (or root should `interrupt_agent`) once all live peers have posted END for the current main head. Alternatively, the prompt should say "after quorum, end your turn immediately; never wait for root".
   - Affects: C1-r2.
   - Predicted signature: a TURN_END within 1 min of the last END post; no `wait_agent 3600000` after quorum; run_exit 0 at about 45 monotonic min.
3. **Use drafts as directions, not layers.** Require each draft to be a whole-product mock-up that can be judged visually, and forbid code reuse from the draft beyond the chosen design. Alternatively, in C2, make SPINE an automatic first-claim rule (a1 always builds the spine).
   - Affects: C1-r2 and C2-r2.
   - Predicted signature: draft branches all touch the UI and the end-to-end flow; the SPINE DONE post appears before A6; no duplicate-spine commits.
4. **Ledger rows start as CLAIMED, never DONE.** The ledger must have one row per brief bullet (35-plus), with no row marked done at creation, and DONE requires a brief-derived check that would fail on a stub.
   - For example: the UI check must find HTML with a search form and dossier links; the round-trip check must compare annotations; search must be exercised with an experiment ID.
   - Affects: C1-r2 and C2-r2.
   - Predicted signature: more than 25 rows at creation; fewer than 30% of rows DONE before A15; build commits of hundreds of lines; failing acceptance checks visible on the board before the fixes.
