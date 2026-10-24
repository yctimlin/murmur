# murmur research round 4 — final report (DRAFT, non-held-out sections)

Draft written 2026-10-24 from the research records, before the held-out FINAL is unblinded. It contains no held-out
quality score. All times are Asia/Taipei. "active_nf" = freeze-excluded active minutes (r4eval.py, heartbeat gaps
> 60 s removed). Quality = blind Claude judge overall (0-10), mean of 2 judgments (median of 3 if the gap is > 1.5).
Collapse = quality < 3.0 or not delivered. CIs are two-sided 90% t-intervals unless stated otherwise.

## 1. Question and goal

murmur is a leaderless multi-agent swarm CLI on top of `codex exec`. Round 3 found that 3-peer swarms took about
0.63x solo Codex's active time, used about 4x its input tokens, and scored 1.3-1.7 points lower. The main failure
was partial delivery: runs declared completion early with only part of the system integrated.

Goal of round 4 (BRIEF.md): make murmur genuinely better than the original baseline on large, complex, open-ended
tasks by inventing and validating new collaboration mechanisms, not parameter tweaks. Comparators: orig (eec78f8),
base4 (146d476, fix/r3-reliability) and solo `codex exec`. Target: quality at least on par with solo, faster than
solo, about 1.5-2x solo tokens, and no regression against the baseline. A well-evidenced negative result was
acceptable. Binding constraints: the CLI keeps only `setup` and `run`; the root only spawns and waits; no hardcoded
Codex settings; no 429 handling; root causes verified in the Codex source; final claims tested on sealed held-out
tasks the developer has not seen.

## 2. Method

### 2.1 Diagnosis approach
- Read the round-3 sealed-eval runs (16 swarm runs) and classified them by coordination pattern
  (analysis/r3-coord.txt, r3-agents.txt; DIAGNOSIS D1).
- Verified the termination mechanism in the Codex 0.162.1 source (multi_agents_v2/send_message.rs,
  core/src/agent_message_board.rs, agent/control/completion.rs, core/src/tasks/mod.rs; DIAGNOSIS D2).
- Token attribution per tool-cell kind (analysis/tokens.py; DIAGNOSIS D5).
- Log forensics of all 31 runs judged by 10-21 14:02 (FORENSICS.md). tools/forensics_extract.py merged rollouts,
  board sqlite, origin.git and judge text into one timeline per run. Seven read-only Claude analysts wrote per-run
  notes and 7 contrasts under a fixed protocol. The PI re-checked the key claims against the raw rollouts and the
  murmur source. tools/time_accounting.py charged agent time to tool-call kinds.

### 2.2 Fairness scheme (prereg/FAIRNESS.md, committed 107a268 at 10-19 22:54, before any development run)
- F1 sealed held-out tasks. A separate `claude -p` author (heldout/AUTHOR-PROMPT.md, constrains form only) wrote 4 new
  tasks H1-H4 straight into /srv/murmur-sealed-r4 (root:root, mode 700). It calibrated them with solo `codex exec` and
  enlarged any task under 40 active min (at most twice). It published only heldout/PUBLIC.json, which holds sha256
  commitments: H1 b872e7b4..., H2 28e5bc5d... (version H2v3, 2 enlargements), H3 c03aab10..., H4 5d91dae2...
  Calibration solo active: 42.4 / 45.6 / 66.6 / 44.4 min. The author finished at 10-20 13:32. The PI verified
  ownership with stat only and never listed or read the sealed directory.
- F2 frozen evaluation. The rubric, judge prompt, anonymizer, decision code and arm commits were frozen and hashed
  before any held-out copy. tools/final_eval.py copies tasks in by sudo only at eval time, checks each bundle against
  its PUBLIC.json sha256, and runs the arms in randomized interleaved blocks (seed 20261020).
- F3 blind judging. Separate `claude -p` judges get random ids, 2 judgments per run (3rd if the gap is > 1.5), the
  delivered tree only (no git history, PR.md/planning files and `.work/` removed, identity words scrubbed in prose
  docs, mtimes normalised). Judges never hear of murmur, swarms or arms. Each judge guesses "single" or "team", and
  the guess rate is reported as a blinding check.
- F4 r3 tasks T1b, T2, T3b and T4b are development tasks. Held-out tasks are used once, in FINAL.
- F5 infrastructure failures (relay outages, provider-killed sessions) are withdrawn and rerun, never scored.
- Rubric (prereg/RUBRIC.md = the r3 open rubric, sha256 469432ec...) has 6 criteria: coverage x3, correctness by
  running x3, design x2, robustness x2, code/tests x1, UX/docs x1. Claims count only if verified. If the program does
  not start, overall is capped at 3. Not delivered scores 0.

### 2.3 Pre-registration
- PLAN.md, E1.md and RUBRIC.md were committed (c0eb6a4, 10-19 23:01) before the first E1 job (23:02). Each later
  experiment was registered before its first run: E2.md (2be5fcc, 10-20 05:41), E3.md (92a38f1, 10-20 10:41),
  E4.md (10-21 22:59), E5.md (4833a17, 10-23 01:08). FINAL.md and tools/final_decide.py were frozen at 10-20 14:31,
  before any held-out use and before a candidate was chosen.
- Entries in LOG.md before 10-19 23:07 carried estimated timestamps. The git commit times are authoritative (LOG
  correction 10-19 23:07). The order (prereg before runs) is unaffected.

Amendments (all dated and written before the data they govern were unblinded; disclosures as in the files):

| # | Date (LOG) | What | Why |
|---|---|---|---|
| 1 | 10-20 02:41 | Anonymizer keeps committed fixtures/DBs and scrubs identity words only in prose docs; the first 2 judgments of E1-T3b-C1-r1 superseded | The r3 anonymizer deleted committed sqlite fixtures and rewrote identifiers in code, which broke programs for any arm |
| 2 | 10-20 10:31 | Bayesian sequential (adaptive) allocation for the rest of E1+E2 (tools/adapt.py): two-part collapse+quality model, P_keep stop at 0.90/0.10, cap 3 runs/arm/task | Supervisor directive 10:27; the fixed 28-run schedule needed 30+ h |
| 3 | 10-20 14:46 | final_eval.py precheck pgrep fixed; runner restart-safe concurrency | Tooling bug (pgrep self-matched) |
| 4 | 10-20 18:43 | Hidden-test scoring skipped for open tasks (score_na); mutation scorer copied in; judge empty-stdout handling and backoff | Tooling errors (missing hidden dirs, missing mutation.py, IndexError) |
| 5 | 10-20 22:58 | Tokens removed from all keep rules (secondary only); speed = active_nf vs comparator and vs solo; time model fitted on non-collapsed runs; C3/E3 deprioritized; FINAL G4 secondary | User directive 22:56. Not blind to interim looks (disclosed) |
| 6 | 10-21 07:09 | A run is infra if any codex session ends with task_complete error "stream disconnected" | E1-T3b-C1-r2 had a peer killed by provider overload; mechanical, arm-blind rule |
| 7 | 10-21 10:44 (+11:12) | Dev runner PAR 3 -> 4 -> 5, judge parallelism 2 -> 4 | User directive to speed up; frozen fraction measured at 0.74-0.78 independent of concurrency |
| 8 | 10-21 22:59 | E1/E2 closed (fallback reported, not used for selection); candidate chain replaced by K0/K1 (E4) | FORENSICS F-1/F-2/F-3 showed E1/E2 contrasts confounded. Not blind (disclosed) |
| 9 | 10-22 05:15 | "exceeded retry limit" (429 exhaustion) also counts as provider-killed infra | E4-T1b-K1-r1 peer ended by relay 429s; its 2 judgments moved unread to judge/E4-infra |
| 10 | 10-23 00:45 (commit 01:08) | Freeze-excluded cap clock in murmur (base4F, K1F) and in the lab runner; FINAL on hold until E5 | User directive 10-22 22:50; type-A VM freezes ate murmur's cap (section 2.5) |
| 11 | 10-23 14:35 | FINAL with the E5 winner base4F; arms cand=base4F, origF, solo; 24 runs; G1 vs origF; PAR 4; undelivered = 0 applied in code | E5 STOP-REJECTed K1F; user directive "only proceed with whichever arm wins" |

### 2.4 Lab infrastructure
- Dev lab /workspace/r4/lab with tools/runner.py (self3 runner2 plus configurable ports, restart-safe concurrency and,
  after AMENDMENT-10, `run_active`). Jobs are queued as JSON, results land in lab/results/<name>/result.json, and
  infra runs move to lab/results-infra and lab/ws-infra. Every run used 3 peers, gpt-6-astra, effort high and a
  120-min cap (runner defaults). The solo arm is plain `codex exec` with the round-2 solo prompt.
- tools/heartbeat.sh writes freeze windows to lab/heartbeat.log. tools/r4eval.py handles active_nf, is_infra and
  provider_killed, anonymizing and judging. tools/judge_loop.sh judges each experiment. tools/adapt.py and adapt5.py
  run adaptive allocation. tools/signatures.py and s1_handcheck.py give the E4 mechanism checks. tools/clocklog.py
  is the clock probe. tools/cleanup_ws.py removes scratch files of fully judged runs.
- Held-out lab /workspace/r4/evallab is driven only by tools/final_eval.py (runner, infra watcher, judge loop F).
  tools/final_decide.py does the unblinding and the verdict.
- Box: 8 cores, 15 GB RAM. The host froze the VM for about 75-95% of wall time (9-30 min freezes).

### 2.5 The freeze-excluded clock problem and its fix (AMENDMENT-10)
1. F-1, wall-clock rush (FORENSICS, 10-21). Peers estimated murmur's 120-min cap from `date` and board timestamps,
   which are wall time. Wall time keeps running through VM freezes. Teams broadcast false countdowns ("Hard cap in
   ~4m") and ENDed at 20-35 active min. This affected 19/27 swarm runs and 0/4 solo runs.
2. M0 (K0, E4) published murmur's enforced clock in budget-clock.txt. E4 then showed that this enforced clock was
   wrong too. murmur's cap (`proc.wait(timeout)` on time.monotonic) reached 116-124/120 at only 35-55
   freeze-excluded minutes (LOG 10-22 21:55).
3. The clock probe (tools/clocklog.py; analysis/clock/clocklog.txt) found two freeze types that roughly alternate.
   - Type A: REALTIME and MONOTONIC, MONOTONIC_RAW and BOOTTIME all jump by the whole freeze (332-678 s).
   - Type B: only REALTIME jumps (247-1088 s) while MONOTONIC advances 8-13 s.
   Steal time stays at about 0, so no kernel clock excludes type-A freezes. From 22:51 to 00:08 the VM was frozen
   about 69 of 77 wall minutes.
4. Fix: `_ActiveClock` in murmur.
   - A 1 s ticker runs on MONOTONIC. Any tick that arrives more than 10 s late is a stall and is excluded.
   - The cap wait loops until active time reaches the cap. run.json gains active_seconds and stalled_seconds.
   - The patch was applied unchanged to base4 (base4F a331d54), to K1 (K1F a50d547) and later to orig (origF c583a63).
   - The runner's `run_active` applies the same rule to the setup, murmur and solo timeouts (16-h wall ceiling).
   - Tests: a fake-clock test, a cap wait with a 1-h jump, and SIGSTOP end-to-end tests. base4F passed 44 tests and
     K1F 47.
5. After the fix (E5), no run hit the cap, every swarm ended on its own, and 6-26 stalled minutes per run were
   excluded.
6. E1, E2 and E4 results stay as reported, labelled "confounded by type-A freezes eating the cap".

## 3. Diagnosis findings

### 3.1 Round-3 data and the Codex source (DIAGNOSIS D1-D3)
- Quality was bimodal. 10/16 r3 swarm runs were high mode (q 6.9-8.1, mean about 7.5, at or above solo's 6.64).
  6/16 were low mode (q 0-2.5): each peer ended its turn after a narrow piece at 12-18 min, and parts sat unmerged on
  draft/side branches. The 6 low-mode runs account for the whole swarm-vs-solo quality gap.
- Mechanism (verified in Codex 0.162.1). send_message is QueueOnly, and board notifications and completion notices
  have trigger_turn=false. An idle thread only wakes for followup_task or an outstanding clock.sleep. So ending a turn
  is an irreversible, unilateral "done" vote, and the root ends when every peer is idle, integrated or not.
- In the low mode the root made 50-70 calls (18-34 waits), and peers used direct messages. In the high mode the root
  made about 10 calls, and peers used the board and worked on main together.

### 3.2 Failure taxonomy (FORENSICS section 3; 27 swarm + 4 solo E1/E2 runs; analyst tags, * = PI re-checked)
| Failure mode | Swarm | Solo | Note |
|---|---|---|---|
| WALLCLOCK_RUSH* (F-1) | 19/27 | 0/4 | false countdown ends the build or hardening phase |
| SELF_REFERENTIAL_VERIFICATION (F-3) | 18/27 | 1/4 | rows closed on the builder's own tests; in all 5 collapses |
| SCOPE_SHRINK | 15/27 | 0/4 | often a result of F-1 or coarse ledgers |
| DUPLICATE_WORK | 17/27 | – | duplicate harnesses or spines |
| MERGE_CONFLICT (minor) | 15/27 | – | about 3 agent-min per run, never decisive |
| DRAFT_AS_PRODUCT (decisive) | 4/27 | – | 4 of the 5 collapses |
| IDLE_PEER | 9/27 | – | decisive only in base4 quits and one C1 cap |
| INTEGRATION_LOSS | 8/27 | – | never decisive |
| REVIEW_LOOP | 8/27 | – | C1/C2 END-void re-votes, 1-3 min |
| ROLE_INHERITANCE* (F-2) | 2 quits + 4 launcher-DM runs | – | peers forked with the launcher prompt ("never ... run commands") |
| CAP_HIT / PROVIDER_ERROR | 1 / 1 | – | |
| Dense one-shot code (judge code score 5-6) | 27/27 | 4/4 | model trait |

- F-2 (murmur spawn bug). Peers are forks of the root thread, so their context starts with the launcher prompt. Both
  base4 T4b collapses began with a peer quitting this way (A0.7, A1.0). Launcher-directed behaviour (waiting for the
  "parent", DMs to /root) appeared in 4 of the 5 collapses.
- F-3. Examples: a rule monitor reporting "0 violations" for rules it never modelled (T2-C1-r2), an oracle pasted from
  the importer's own output (T4b-C2-r2), and ledgers batch-stamped DONE (38 rows in one commit, T3b-C2-r2).
- Five collapses (T4b-base4-r1/r2, T2-C1-r2, T1b-C1-r2, T1b-C2-r2) scored 1.6-2.55. C1's quorum removed unilateral
  stops (0/10 C1 runs stopped alone) but moved the failure to "stop together on a self-certified draft" (2/10).

### 3.3 Where the time and tokens go
Time (FORENSICS section 4, freeze-excluded agent-minutes, ±2 min per cell):

| Group | n | Run active | Agent-min | Build | Verify | Others' work | Coord | Main lines |
|---|---|---|---|---|---|---|---|---|
| solo | 4 | 37.8 | 34.4 | 11.6 | 21.1 | 1.5 | 0 | 4579 |
| base4 (non-collapsed) | 7 | 29.0 | 79.6 | 16.7 | 37.6 | 19.7 | 5.5 | 3188 |
| C1 (non-collapsed) | 8 | 29.4 | 84.5 | 16.1 | 38.8 | 19.8 | 9.5 | 4807 |
| C2 (non-collapsed) | 7 | 28.9 | 82.1 | 20.4 | 34.4 | 14.2 | 12.5 | 5251 |
| collapses | 5 | 31.9 | 79.0 | 16.0 | 10.4 | 9.3 | 43.2 | 412 |

- A healthy swarm spends 2.3-2.5x solo's agent time for about 1.5x its build time and about the same code on main.
- The surplus goes to three places: duplicated verification (about 37 vs 21 agent-min), reading and merging others'
  work (14-20 agent-min) and the draft-and-rank ritual (about 15 agent-min). The draft ritual also delays product code
  on main to A6-9.
- Collapses are coordination-dominated: 42-67% of peer time goes to board, mail and wait.

Tokens (DIAGNOSIS D3/D5, 6 E1 swarm runs):
- Total input was 13.3-19.0M per swarm run, against 4.38M for an r3 solo run.
- Shares: git-read of peers' work 29-44%, read/other 9-21%, coordination 4-22% (C1/C2 14-22% vs base4 4-7%), edit
  7-14%, test 5-12%, git write 5-13%.
- Average context per call was 74-96K (max 125-166K), with 48-87 calls per peer. Each peer costs about one solo run.
- The main sink is peers reading each other's code inside large, growing contexts, not messaging.

## 4. Development experiments (dev tasks T1b, T2, T3b, T4b; 3 peers; gpt-6-astra/high)

### C1 — consensus termination (E1)
- Mechanism (prompt-only): requirements ledger; peers park with wait_agent instead of ending their turn; END quorum
  on the same latest main commit; followup_task wakes idle peers that have open items.
- Code: experiment/r4-c1, tested commit 76d8b44 (the branch head c0eb6a4 adds only research records).
- Experiment: E1 with adaptive allocation (AMENDMENT-2/5), 36 valid E1/E2 rows; 7 E1 runs withdrawn as infra.
- Numbers:
  - C1: 11 runs, mean q 6.54 [5.41, 7.67], 2 collapses. base4: 11 runs, 6.51 [5.19, 7.82], 2 collapses. Solo: 4 runs,
    7.58 [7.05, 8.10], 0 collapses.
  - C1 - base4 over 8 task-rep pairs: -0.71 [-3.07, +1.65]. Over task means: -0.20 [-3.59, +3.18].
  - Active ratio C1/base4 1.04 [0.81, 1.26]. C1/solo 0.80 [0.68, 0.93]. Input C1/solo 6.58x [4.17, 9.00], and
    C1/base4 1.28x.
  - Per-task means base4/C1/solo: T4b 3.53/7.38/7.55, T3b 7.72/7.42/7.90, T1b 7.37/5.80/6.95, T2 7.85/5.08/7.90.
- Decision: REJECT. Under the AMENDMENT-5 deterministic fallback (analysis/e1_fallback.json), the quality difference
  is -0.20 against a required +0.5. The active ratio was 0.87 vs base4 and 0.76 vs solo. The adaptive P_keep was
  0.21-0.60 throughout. C1 fixed base4's unilateral-stop collapse on T4b but added self-certified-draft collapses on
  T1b and T2. Confounded by F-1.

### C2 — spine + independent acceptance checks (E2)
- Mechanism: built on C1, it replaces the draft tournament. One peer builds a thin end-to-end spine and a plan. The
  others write the ledger and black-box acceptance checks from the brief alone. An item is DONE only when its check
  passes on main, and peers cross-check parts they did not build.
- Code: experiment/r4-c2 1c0364e.
- Experiment: E2, pooled into the E1 adaptive design.
- Numbers: 10 runs, mean q 6.86, 1 collapse (T1b-C2-r2, 2.55). Median active_nf 28.0, median input 15.3M.
  Fallback vs base4 (C1 rejected): quality +0.16, active ratio 0.88 vs base4 and 0.77 vs solo.
- Decision: REJECT. Neither branch of the rule holds: the quality gain is not >= +0.5, and the active ratio is not
  <= 0.85. C2 reached its run cap at 10-21 15:07. When the spine was claimed early it helped (T1b/T2-C2-r1). When
  nobody claimed it, the run stalled (T1b-C2-r2, T4b-C2-r3).

### C3 — token economy (E3)
- Mechanism (prompt-only, on C1): a DONE change digest of 10 lines or fewer with every push to main; narrow reading
  rules; partitioned final review.
- Code: experiment/r4-c3 fbda22e. E3 was registered with a keep rule of input ratio <= 0.75 vs ref3.
- Decision: NOT RUN. AMENDMENT-5 removed tokens from the keep rules, and C3 targets only cost. E3 stays registered but
  not run, so there is no data.

### K0 — truthful budget + clean roles (E4, mechanism M0)
- Mechanism: murmur writes its enforced cap clock to budget-clock.txt every 30 s, and the prompt names it as the only
  budget. The root spawns peers with fork_turns "none" (no launcher context), and peers are told the launcher never
  answers. These are bug fixes for F-1 and F-2.
- Code: experiment/r4-k0 708d5fa.
- Experiment: E4, 24 valid runs, 8 infra events (all K runs, rerun under the same names).
- Numbers:
  - K0: 8 runs, mean q 6.19, 2 collapses (T2-r1 2.00, T3b-r2 1.30), median active_nf 41.1, median input 17.1M.
  - base4: 4 runs, 7.24, 0 collapses, 29.0 min, 9.9M.
  - D1 (M0 executes): PASS on the hand-check (S1 0/16, S2 0/16). The regex proxy would give 6/16, a FAIL.
  - D2 (K0 vs base4): mean task difference -1.05 [-3.46, +1.35]; collapse rate 0.25 vs 0.
- Decision: D2 FAIL, so K0 alone is rejected. Its components were carried inside K1.

### K1 — grounded cross-verification ledger (E4, mechanism M1)
- Mechanism: built on K0. murmur/ledger.py splits the brief into rows that start OPEN. Verifiers are assigned by
  rotation. Only the assigned non-builder verifier closes a row, with a `VERIFIED`/`FAIL` evidence post, and row
  status is computed from board posts. Peers finish only with 0 OPEN/FAIL rows.
- Code: experiment/r4-k1 cd0d635.
- Numbers:
  - K1: 8 runs, mean q 6.62, 1 collapse (T2-r1 2.85), median active_nf 32.3, median input 15.0M.
  - D3 (K1 vs K0): +0.43 over 8 pairs [-1.14, +2.01]; collapses 1 vs 2; geometric active ratio K1/K0 0.85.
    Safety stop not triggered.
  - Descriptive: K1 - base4 -0.62 [-2.14, +0.90]; K1 - solo +2.53 [-2.06, +7.13]. E4 solos collapsed on T3b (1.90)
    and T4b (2.35). The ledger was fully closed in 5/8 K1 runs.
- Decision: KEPT in E4 (D3, point-estimate rule), so K1 was the FINAL candidate (FINAL-CANDIDATE 5c75a7b, 10-22 22:35).
  It was superseded before any held-out run, when the clock problem led to E5.

### K1F — K1 under the freeze-excluded clock (E5)
- Code: experiment/r4-k1f a50d547 (K1 + `_ActiveClock`). Reference: base4F a331d54. soloF was reference only.
- Experiment: E5 block 1, 12 runs, 0 infra. Decision code analysis/e5_decide.py (sha256 a8ee56aa) was written before
  any E5 result.
- Numbers:
  - K1F - base4F quality +0.295 [-0.059, +0.649]; collapses 0 vs 0.
  - Active ratio K1F/base4F 2.09x [1.37, 3.20] (mean log ratio 0.737 [0.312, 1.162]).
  - Per arm (mean q, median active_nf, median input): base4F 7.58 [7.08, 8.09], 24.0 min, 10.9M; K1F 7.88
    [7.69, 8.07], 58.1 min, 37.4M; solo 7.90 [7.59, 8.21], 35.4 min, 3.2M.
- Decision: STOP-REJECT at the block-1 interim, because the lower bound of the log ratio is > 0 (clearly slower).
  Blocks 2-3 were not run. Under the user's rule (non-inferior quality and not slower), current murmur (base4F)
  stays. base4F vs solo (reference, n=4): quality -0.32, active about 0.68x, input about 3.4x.

### Summary
| Candidate | Branch / commit | Experiment | n (cand) | Mean q | Collapses | Key contrast (90% CI) | Decision |
|---|---|---|---|---|---|---|---|
| C1 | experiment/r4-c1 76d8b44 | E1 | 11 | 6.54 | 2/11 | vs base4 pairs -0.71 [-3.07, +1.65]; fallback -0.20 | rejected (needs >= +0.5) |
| C2 | experiment/r4-c2 1c0364e | E2 | 10 | 6.86 | 1/10 | vs base4 +0.16; active 0.88 | rejected |
| C3 | experiment/r4-c3 fbda22e | E3 | 0 | – | – | – | not run (token-only, A5) |
| K0 | experiment/r4-k0 708d5fa | E4 | 8 | 6.19 | 2/8 | vs base4 -1.05 [-3.46, +1.35] | rejected (D2 fail) |
| K1 | experiment/r4-k1 cd0d635 | E4 | 8 | 6.62 | 1/8 | vs K0 +0.43 [-1.14, +2.01]; vs base4 -0.62 | kept in E4, superseded by E5 |
| K1F | experiment/r4-k1f a50d547 | E5 | 4 | 7.88 | 0/4 | vs base4F q +0.30 [-0.06, +0.65]; active 2.09x [1.37, 3.20] | rejected (slower) |
| base4F | experiment/r4-base4f a331d54 | E5 | 4 | 7.58 | 0/4 | reference | FINAL candidate (infrastructure fix only) |

Every collaboration mechanism tested in round 4 (C1, C2, K0, K1/K1F) was rejected on dev data. The FINAL candidate
is current murmur plus the freeze-excluded clock, which is an infrastructure correction, not a collaboration
mechanism. origF c583a63 (orig + the identical clock patch) is the baseline arm.

## 5. Deviations and incidents
- Claude API limits ended sessions and failed judge attempts (10-19 22:42; 10-20 08:47-10:17; 10-21 07:49-10:07).
  Failed judgments were retried automatically, and none was recorded with a verdict.
- Tooling faults (all disclosed, none scored):
  - The anonymizer broke fixtures (A1).
  - The pgrep precheck self-matched (A3).
  - Hidden-test and mutation errors, and empty judge stdout (A4).
  - adapt.py rep-naming bug (10-20 10:36).
  - Accidental extra interim looks at 10-20 18:44 and 10-21 07:09. They queued nothing, and the JSON of the second
    was deleted by mistake, so its numbers are in LOG.
  - final_eval.py symlinked the murmur repo out of the lab dir, so the 8 murmur-arm jobs failed instantly at FINAL
    start (10-23 15:43). No agent ran. The jobs were re-queued under the same names, and the 4 solos already in flight
    kept running.
- Infra reruns (AMENDMENT-6/9 rule, mechanical and arm-blind):
  - E1: 7 runs withdrawn (T4b-C1-r1 setup 503; T3b-C1-r2, T4b-base4-r3, T2-C2-r2, T1b-C2-r3, T3b-C2-r3, T2-C1-r3).
  - E1-T2-C1-r3 was not rerun, a disclosed deviation from AMENDMENT-8 (E1 no longer selected anything).
  - E4: 8 events listed in E4-RESULT, all K0/K1. E4-T4b-K0-r1 was infra twice. Earlier LOG counts (10-22 11:08-14:10)
    wrongly counted two infra K0 runs as valid; this was corrected at 14:10 before any use.
  - E5: 0. FINAL: 0 runs classified infra (LOG 10-24 10:37).
- E4 D1 relied on a hand-check that overrode the regex proxy (6/16 flagged). This is disclosed as a sensitivity: under
  the proxy D1 fails and no K arm could have been the candidate.
- Blinding leaks in FINAL. r4eval.py logged "judged <run>: <score>" to LOG.md, so 2 held-out scores, both solo-arm
  runs, were exposed with arm labels (seen at 10-23 18:41; the second, F-H2-solo-r1, was logged at 19:12 by a judge
  pass loaded before the fix). Both LOG lines were redacted, and r4eval now logs no score for experiment F. Impact
  assessment: solo is a reference arm, all arms, rules and code were frozen, and no decision remained before
  final_decide.py.
- H2 domain glimpse (10-24 09:10). During a liveness check of F-H2-orig-r2 the PI printed that run's last git commit
  subjects, which showed a few words of held-out task H2's domain. Nothing remained to decide. Later liveness checks
  use mtimes and process trees only.
- F-H2-orig-r2 genuine non-delivery (10-24 ~10:16). The swarm exited 0 after 84.7 runner minutes (active 32.9) with 0
  commits on origin main, 3 unmerged draft branches and 0 END posts. is_infra and provider_killed are both False, there
  are no 429 or stream errors, and all 4 sessions ended normally. It is scored as undelivered = 0 and not rerun
  (FINAL.md / AMENDMENT-11). This is the pre-r4 "drafts pushed, nobody merged" mode, bug 1 class, in orig.
- Process deviations from FINAL.md, made by amendment before the held-out runs: PAR 4 instead of <= 3 (A11); arm
  base4 dropped and replaced by base4F as cand; orig replaced by origF (A10/A11).

## Held-out FINAL results

TODO (filled after tools/final_decide.py unblinds the 24 runs; G1-G3 verdict, G4 secondary, blinding check).

Run metadata from LOG.md (no quality scores). Active = murmur run.json active minutes for cand/orig, runner
freeze-excluded clock for solo. Stalled = minutes excluded by the clock ("–" = not logged). This is not the
pre-registered active_nf, which final_decide.py computes.

| Run | Delivered | Active min | Stalled min |
|---|---|---|---|
| F-H1-cand-r1 | yes | 28.8 | 3.2 |
| F-H1-cand-r2 | yes | 26.1 | 2.4 |
| F-H1-orig-r1 | yes | 31.9 | 3.3 |
| F-H1-orig-r2 | yes | 25.1 | 2.4 |
| F-H1-solo-r1 | yes | 74.8 | 12.4 |
| F-H1-solo-r2 | valid (delivery not stated in LOG) | 31.6 | – |
| F-H2-cand-r1 | yes | 30.1 | 0.6 |
| F-H2-cand-r2 | yes | 33.5 | – |
| F-H2-orig-r1 | yes | 33.0 | 1.1 |
| F-H2-orig-r2 | NO (0 commits on main) | 32.9 | – |
| F-H2-solo-r1 | yes | 33.5 | 9.3 |
| F-H2-solo-r2 | yes | 39.4 | – |
| F-H3-cand-r1 | yes | 23.3 | – |
| F-H3-cand-r2 | yes | 31.8 | 1.5 |
| F-H3-orig-r1 | yes | 25.3 | – |
| F-H3-orig-r2 | yes | 23.4 | – |
| F-H3-solo-r1 | yes | 54.0 | – |
| F-H3-solo-r2 | yes | 43.8 | – |
| F-H4-cand-r1 | yes | 28.3 | 3.1 |
| F-H4-cand-r2 | yes | 35.4 | – |
| F-H4-orig-r1 | yes | 39.6 | 3.6 |
| F-H4-orig-r2 | yes | 29.7 | – |
| F-H4-solo-r1 | valid (delivery not stated in LOG) | 47.3 | – |
| F-H4-solo-r2 | yes | 33.2 | 2.0 |

Delivered: 23/24 (21 logged as delivered, 2 logged only as "finished valid"); 1 genuine non-delivery (F-H2-orig-r2).
Infra: 0. Runs went from 10-23 14:36 to 10-24 10:37 (all 24 finished), at eval runner PAR 4.

## 7. Limitations
- Held-out task size. Held-out solo active times were 31.6-74.8 min, and 4/8 fell below the brief's >= 40 target
  (31.6, 33.5, 33.2, 39.4). The author's calibration runs were 42.4-66.6 min. The tasks could not be enlarged after
  sealing without breaking the prereg.
- Small n. Dev cells have 1-3 runs. FINAL has 8 blocks (df = 7). The dev intervals are very wide, for example
  C1 - base4 [-3.07, +1.65].
- Bimodal quality. Scores are about 6.5-8.6 or 1.3-3.5, so means are driven by rare collapses.
- Solo instability. Solo collapsed in 2/4 E4 runs and 0/4 in E1 and E5. Solo is also a noisy reference.
- Drift across days. Relay/model behaviour may have drifted (3/8 collapses after 10-20 21:00 vs 2/20 before). E1,
  E4 and E5 ran on different days and are not comparable to each other. Arms within an experiment were interleaved.
  turn_context showed gpt-6-astra/high throughout.
- VM freezes (75-95% of wall time).
  - E1, E2 and E4 are confounded by F-1 and by type-A freezes eating the cap. Only E5 and FINAL run under the fixed
    clock.
  - active_nf (heartbeat gaps) and murmur's active clock (10 s tick rule) are different estimators. In one capped run
    (E1-T1b-C1-r2) active_nf was 53-67 min while murmur's clock reached 120.
  - CPU contention at PAR 4-5 inside non-frozen time is possible (A7 sensitivity check pre-declared).
- Infra reruns were outcome-blind, but all 8 E4 infra events hit long K runs, which leaves a residual selection risk.
- Non-blind amendments. A5 and A8 were written after interim or judged dev data had been seen (disclosed). The
  held-out FINAL itself is unaffected apart from the leaks in section 5.
- Blinding check. Judges guessed solo vs team correctly in 57% of E1 judgments (41/72), 48% in E4 (23/48) and 75% in
  E5 (18/24). They almost always said "single" for solo (23/24) and often for swarms, so the rate mostly reflects a
  "single" bias, not true discrimination. Judge consistency: mean |j1 - j2| was 0.23 (E1), 0.30 (E4) and 0.37 (E5),
  and no 3rd judgment was needed.
- Single judge family (Claude) with one rubric. Code-quality scores of 5-6 everywhere reflect a model trait.
- The candidate is an infrastructure fix. Round 4 produced no collaboration mechanism that passed dev screening, so
  FINAL tests "current murmur with a correct clock" against orig and solo, not a new mechanism.

## 8. File index
- Brief and context: /workspace/r4/BRIEF.md, /workspace/r4/CONTEXT.md, /workspace/r4/SUPERVISOR-DIRECTIVES.md
- Records: /workspace/r4/LOG.md, /workspace/r4/STATE.json, /workspace/r4/PROGRESS.md
- Pre-registration: /workspace/r4/prereg/PLAN.md, FAIRNESS.md, RUBRIC.md, E1.md-E5.md, FINAL.md, FINAL-CANDIDATE.md,
  AMENDMENT-1.md-AMENDMENT-11.md
- Held-out commitments: /workspace/r4/heldout/PUBLIC.json, heldout/AUTHOR-PROMPT.md (sealed tasks in
  /srv/murmur-sealed-r4, root-only)
- Diagnosis: /workspace/r4/analysis/DIAGNOSIS.md, analysis/FORENSICS.md, analysis/forensics/ (timelines/, runs/,
  contrasts/, time_accounting.json, E4-turn-ends.md, PROTOCOL.md), analysis/tokens.py
- Results: /workspace/r4/results/E1.json, analysis/e1_fallback.json, analysis/E4-RESULT.md, analysis/E4-decision.json,
  analysis/E4-signatures.json, analysis/E5-RESULT.md, analysis/E5-decision-b1.json, analysis/adapt/ (interim looks)
- Clock: /workspace/r4/analysis/clock/ (clocklog.txt, runner.pre-A10.py, FINAL-CANDIDATE.pre-A11.md), tools/clocklog.py
- Tools: /workspace/r4/tools/runner.py, r4eval.py, judge_loop.sh, adapt.py, adapt5.py, final_eval.py, final_decide.py,
  signatures.py, forensics_extract.py, time_accounting.py, heartbeat.sh
- Labs and judging: /workspace/r4/lab/ (dev), /workspace/r4/evallab/ (held-out), /workspace/r4/judge/E1, E4, E5, F
- murmur repo: /workspace/r4/murmur, https://github.com/yctimlin/murmur, branches experiment/self-improve-r4
  (research records), experiment/r4-c1, -c2, -c3, -k0, -k1, -k1f, -base4f, -origf
