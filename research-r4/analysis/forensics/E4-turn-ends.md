# E4 turn-end forensics (interim, PI, 10-22 ~09:40; descriptive, no judge files read)
Tool: analysis/turn_ends.py (last items of each peer rollout before task_complete).

| run | peer | end | reason (from last THINK/MSG) |
|---|---|---|---|
| E4-T3b-K0-r1 | a1,a2,a3 | 22:04-22:06, clock ~100/120 | all three posted DONE FINAL after a whole-main review ("No further issues worth fixing") — legitimate joint finish |
| E4-T2-K0-r1 | a3 | 19:38 | posted a serious defect ("per-day duplicate assignments ... coverage claim inaccurate") then ended with a report — handed the defect off, did not fix/claim it |
| E4-T2-K0-r1 | a1 | 20:07 | fixed the defect, post addressed "Root: origin/main now 08ed181", THINK "Considering direct parent notification", wait_agent, then final summary |
| E4-T2-K0-r1 | a2 | 20:11 | send_message to /root, THINK "Finalizing root-aware scheduler summary", ended |
| E4-T1b-K1-r1 (infra) | a2 | 20:07 | THINK "Verifying parent process termination", wait_agent, "Deciding to finalize parent API updates", ended with 27/84 rows open |
| E4-T1b-K1-r1 (infra) | a1 | 20:09 | wait_agent, ended with rows open |
| E4-T2-K1-r1 | a1,a2,a3 | 00:08-00:09 (cap) | checked ledger.py (0 OPEN/FAIL), posted "ship-ready"; a3 send_message to /root with final verification |

Interim reading:
- R1 SUBAGENT SELF-MODEL (residual F-2): even with fork_turns "none" and the prompt line that the launcher never answers,
  peers know they are codex sub-agents (spawned by /root) and treat the end of their turn as "report to the parent":
  send_message to /root, posts addressed to "Root", wait_agent calls, final summary messages. A peer's turn end is
  then a report, not a team decision, and work it found open (T2-K0 a3's defect; T1b-K1 open rows) is left to "the parent".
- R2: the K1 finish condition (ledger 0 OPEN/FAIL) is obeyed when the ledger is small (T2: 9 rows) but not with 84 rows
  (T1b), where peers ended with 27 open (one peer was killed by the relay, which removed a third of the verifiers).
- Candidate mechanism (not pre-registered, for after E4): the root, when a peer's turn ends while ledger rows are open
  or budget remains, resumes that peer (followup_task) with the ledger state instead of letting the run end — i.e. turn end
  is not a stop signal; only the clock or an all-rows-closed ledger ends a run. Predicted log change: no peer ends
  while `ledger.py` shows OPEN rows with > 10 budget min left; send_message to /root still occurs but is harmless.
  Note: the root must then do more than spawn and wait (BRIEF: "the root only spawns and waits") -> must be done by
  murmur's runner process, not the root agent.
