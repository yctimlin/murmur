# Token-lean round 2 (fixed 2026-10-14 ~12:05 Taipei, before results)
Round 1 (U1/U2): G1 sync helper + chain + shared checks: U1 uncached +7%, U2 -22% vs base;
still 3.4-3.9x solo. Breakdown adds: 10-30% of swarm input is spent after each peer's own last
commit (review/waiting loops).
Arms (gpt-6-astra high, cap 75m):
- base: original main d881067, 3 peers.
- lean3: feat/token-lean @231cab2 (G1+G2 + G3 split final review by area, review only changes), 3 peers.
- lean2: same build, 2 peers.
- solo: plain codex exec.
Tasks (new): V1 bottle @ 8ec5fe2 sessions/CSRF/rate-limit plugins (364-test suite);
V2 greenfield notedrift notes + search + multi-machine folder sync.
Primary metric: uncached input ratio vs solo (also total input). Active time gap-capped.
Keep rule: an arm is acceptable if uncached <= 2.0x solo (or <= 0.6x base), active time <= base *
1.15, quality mean >= base - 0.7 (blind rubric + QA judge as before).
