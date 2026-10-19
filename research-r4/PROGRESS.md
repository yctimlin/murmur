Updated: 2026-10-19 23:52 (Asia/Taipei)
Phase: 2 — E1 (consensus termination, C1) running on dev tasks.
Findings so far (analysis/DIAGNOSIS.md):
- r3 swarm runs are bimodal: 10/16 high-mode (quality ≈7.5, ≥ solo 6.64) vs 6/16 collapsed (quality 0-2.5): peers each
  finish a narrow part, end their turns, run ends half-integrated. Verified in Codex 0.162.1: ending a turn is
  irreversible (board posts/send_message never wake an idle peer), so termination = AND of unilateral "done" votes.
- Tokens: each peer ≈ one solo run; 46% of peer tool calls are coordination.
Done: FAIRNESS.md + held-out author launched (sealed /srv/murmur-sealed-r4, I read only heldout/PUBLIC.json);
PLAN.md, E1.md, RUBRIC.md pre-registered and pushed; C1 = experiment/r4-c1 76d8b44.
Running: held-out author (calibrating, ≤2 solo runs); E1: 20 jobs queued (base4 vs C1 × 4 tasks × 2 reps + 4 solo), PAR 1.
Next: eval/judging tool; judge E1 as runs finish; design C2 (serial spine, parallel burst, parallel verification).
Blockers: Claude API daily limit hit once (session 1 died 22:42); concurrency limited to 1 dev run while author calibrates.
