Updated: 2026-10-23 15:11 (Asia/Taipei)
Phase: 5-FINAL. The held-out eval is running with the E5 winner (AMENDMENT-11, committed+pushed 664c435 before any held-out copy).
Arms: cand = base4F a331d54 (current murmur + freeze-excluded clock), origF c583a63 (orig + same clock), solo codex exec.
Design: 4 sealed tasks x 2 reps x 3 arms = 24 runs. Blind judging. Rule G1 (no regression vs origF), G2 (quality
vs solo), G3 (faster than solo); G4 tokens is secondary.
E5 (dev, block-1 interim): K1F was rejected because it is slower (2.09x active time; quality +0.30 n.s.), so base4F stays.
Per arm mean quality / median active min / median tokens:
  base4F 7.58 / 24.0 / 10.9M; K1F 7.88 / 58.1 / 37.4M; solo 7.90 / 35.4 / 3.2M. 0/12 collapses.
Start-up tooling bug (now fixed, nothing scored): a symlinked repo failed the runner's lab-dir check, and 8 murmur jobs were re-queued.
Running: eval runner PAR 4 (pid 77075; 4 solo runs in flight), watcher 77077, judge loop F, heartbeat, clock probe.
Next: poll until all 24 runs are scored, then tools/final_decide.py, then FINAL-REPORT.md.
Blockers: none. Expected duration ~1-1.5 days (the VM is frozen ~80-90% of wall time).
