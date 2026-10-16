# Validation: token-lean on long tasks (fixed 2026-10-14 ~14:20 Taipei, before results)
Tasks (new, unseen; solo expected 60+ min):
- W1 marshmallow @ d08471b1: schema versions, data migrations, compatibility checker + CLI
  (existing repo, 1190-test suite).
- W2 greenfield git: trackwell issue tracker web app (stdlib, roles, workflows, search, import,
  audit, API, UI).
Arms (gpt-6-astra high, cap 90m, all parallel): base = original main d881067 3 peers;
lean2 = feat/token-lean @231cab2 2 peers; lean3 = same 3 peers; solo = plain codex exec.
Metrics: uncached input (primary) and total input vs solo; active time (gap-capped 120 s).
Quality: blind rubric judge (correctness, regressions vs base suite, PR.md accuracy, design) + separate
QA judge (10-2*P0-P1); mean of 5.
Keep rule per arm: uncached <= 2.0x solo AND active time <= base*1.15 AND mean >= base-0.7, on both
tasks. Recommendation follows the rule (lean2 expected; lean3 reported).
