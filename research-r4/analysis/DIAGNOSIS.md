# Round-4 diagnosis notes (incremental; written 10-19 session 2)

## D1. Swarm runs are bimodal, and the low mode is a turn-termination failure
r3 eval, 16 swarm runs (orig+base3). Two regimes (analysis/r3-coord.txt, r3-agents.txt):
- HIGH (q 6.9-8.1, 10/16 runs): root makes ~10 calls (3 spawns, 1-3 waits); peers use the board (post 55-122),
  ~0 send_message; all peers work on `main` together until the end (e.g. E-T4b-base3-r2: drafts 4-58 lines,
  main +5308 lines, 49 files; all peers end within 1 min of each other; peers got woken (task_started=2)).
- LOW (q 0-2.5, 6/16 runs: T1b-orig-r2, T2-base3-r1, T3b-base3-r2, T3b-orig-r1, T4b-base3-r1, T4b-orig-r2):
  root makes 50-70 calls (wait 18-34, list_agents ~28), peers use direct send_message (24-41) and wait_agent,
  each peer ends its turn after a narrow piece at 12-18 min. Example E-T4b-base3-r1: main = parser only (245 lines);
  a2's app/store/API sat on draft/a2-clean, a3's on integration/a3-adapter; every peer's final message reports
  "my part done". Nobody owned completion of the whole.
All 6 low-mode runs drive the "swarm < solo" quality gap: high-mode mean ~7.5 ≈ solo (6.64).

## D2. Root cause verified in Codex 0.162.1 source
- Inter-agent delivery: `send_message` = MessageDeliveryMode::QueueOnly (multi_agents_v2/send_message.rs);
  board post notifications are InterAgentCommunication with trigger_turn=false (core/src/agent_message_board.rs:232);
  completion notices to parent trigger_turn=false (agent/control/completion.rs:117).
- An idle thread only starts a new turn for mail with trigger_turn=true (followup_task) or while a durable `clock.sleep`
  is outstanding (core/src/tasks/mod.rs:437-490). `clock.sleep` exists (tools/handlers/sleep.rs, gated by
  Feature::SleepTool + sleep_tool_mode) and returns early "when new input arrives for the active turn".
- So: a peer that ends its turn is permanently out unless another peer calls followup_task. Ending the turn is the
  only way the root's wait sees completion, and the root ends when all peers are idle. => "ending a turn" is an
  irreversible, unilateral "the objective is done" vote by each peer, and the run ends when every peer has
  individually stopped, regardless of whether the whole is integrated. This is the mechanism behind partial delivery.
- Peers are spawned as forks of the root thread (session_meta forked_from_id = root thread).

## D3. Token sinks (to quantify further)
- coord/(coord+exec) tool calls = 0.46 across r3 swarm runs: nearly half of peer calls are coordination.
- Each peer re-reads a 120-250K context per call; 3 peers x 50-100 calls x ~100K = the 13-30M input.
- Root share is small (4%) except in the low mode (1.2-1.8M from 30 wait/list cycles).
- Draft-then-rank phase: 3 parallel drafts, only one kept (in the low mode the "winner" is a tiny module).

## Open questions
- What triggers the low mode (send_message/wait_agent style)? Model stochastic choice early on? Check first 5 min.
- Is clock.sleep available in our codex config (Feature::SleepTool)? If yes, a "sleep instead of ending the turn"
  protocol would let board posts re-wake peers -> a quorum-based termination mechanism.

## D4. First C1 run (E1-T3b-C1-r1) timeline (01:45 10-20)
- Drafts 0-3.8 active min, ranking 3.4-3.9, ledger in PR.md at 5.0, parallel build 5-20, broad review 20-25,
  first END 25.6, quorum on 46aac16 at 26.5; all three peers ended within 0.1 min. Consensus phase cost 2.8M of 19.0M.
- WALL-CLOCK RUSH (confound): a1 posted "TIME current 16:57 UTC; hard cap started 15:03 => 17:03 (~6min)". The box
  froze ~94 min during the run; peers read wall time and believed the 120m cap was near (murmur's cap uses a
  monotonic clock, the runner's timeout too). Freezes therefore truncate scope for any arm that watches the clock
  (solo too). Recorded as a limitation; freeze exposure per run is reported (wall - raw active).
- Token shape: each peer ~70 calls at ~90K avg context = as many calls as a whole solo run. Tokens ∝ calls x context
  and context grows with calls, so a swarm that divided the work would spend LESS than solo; ours triples the calls
  (coordination ~40% of calls, every peer reviews/tests the whole). Candidate token mechanisms: (i) context rotation
  (a peer that finished its items hands off and is replaced by a fresh-context peer; fresh eyes = clean-room verifier),
  (ii) asymmetric allocation (builders + short-lived verifiers).

## D5. Token attribution over the 6 judged-or-finished E1 swarm runs (10-20 10:39, analysis/tokens.py)
- Method: each token_count (input of one model call) is attributed to the kind of tool cell it answers; code-mode
  cells that mix a board call with a shell command count as the shell kind ('coord' = board/wait/messaging only).
- Totals 13.3-19.0M (r3 solo mean 4.38M). Shares: git-read (fetch/show/diff/log of others' work) 29-44%,
  read/other 9-21%, coord-only 4-22% (C1/C2 14-22% vs base4 4-7%: the quorum/park protocol costs ~10 pp), edit 7-14%,
  test 5-12%, git write 5-13%. Avg context per call 74-96K, max 125-166K; 48-87 calls per peer.
- Reading: the biggest sink is not messaging but peers reading each other's code inside large, ever-growing contexts
  (every call re-pays ~85K of history). C1/C2 add ~2-4M of coordination on top and neither reduces this.
- C3 direction (token mechanism, to pre-register before use): make cross-peer knowledge cheap — merge-time change
  digests (interface/contract summary posted with each merge) replace whole-file git show; review is delegated to
  owner-assigned checks instead of every peer re-reading main; and a peer whose items are done hands off rather than
  idling/reviewing in a 130K+ context. Expected effect: git-read + coord from ~50% to ~20% => ~10M, still >2x solo,
  so C3 alone will likely not reach 1.5-2x; fewer calls per peer (smaller scope per peer) is the other lever.

## D6. First r4 collapse: E1-T4b-base4-r1 (q 1.6, delivered, 7.3M input, 9 commits) (10-20 12:39)
- a3 read its prompt (1 call) and answered "done" 31 s after spawn: no post, no work. Not infra (no error, model replied).
- a2 integrated the winning ingestion draft (parser + SQLite core) and ended its turn at 47.5 wall min with a
  FINAL_ANSWER describing only its own slice; a1 continued alone to the end ("done").
- Judges: "most of the brief is missing (no API, UI, matching, categorisation, reports, auth, backup)", plus parser
  sign/date bugs. This is the r3 low mode (D1): unilateral turn ends with most of the brief unbuilt; the
  quorum/ledger rules of C1 target exactly this. Both judges guessed "single" (team look lost when 1 peer did most).
- Counted as a valid run (collapse), not infra, under E1.md/AMENDMENT-2 definitions.
