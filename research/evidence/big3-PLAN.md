# big3 (pre-registered 2026-10-15 18:35 Taipei, before runs)
Task: brief.md on plain folder src/ (84 MB, 73 files incl. 80 MB binary, symlink, exec script,
ignored out/). Arms: swarm = feat/folder-input @90d8501, 3 peers, gpt-6-astra high, cap 75m;
solo = codex exec same model on a copy of src as a git repo. Parallel.
Rubric (blind, 0-10 each): correctness (ingest rules, aggregates verified against an independent
recomputation), robustness (malformed data, re-ingest, API errors), completeness (all brief items,
./report works), design/code quality, PR.md accuracy. Plus separate QA judge (10-2*P0-P1).
Mean of 6. Report time, tokens (input/uncached/output), quality, folder-input behaviour.
