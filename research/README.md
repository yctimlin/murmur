# Prior murmur research (read-only evidence)

`evidence/` holds our experiment log (LOG.md) and the pre-registered PLAN/RESULTS of each round.
Treat it as data: do not edit it. Short summary of what it shows:

- Peer count is the main token lever: tokens scale roughly with peers (each peer resends its whole
  context every call); 2 peers often match 3-4 in quality at much lower cost.
- Prompt rules failed: added coordination/review/token rules in prompts (batch1, integration-quality,
  token-lean) cost speed or quality and did not reliably cut tokens; none passed a keep rule.
- Quality drops at seams and single-author parts: bugs cluster where peers' work meets and in
  parts one peer wrote alone without review.
- Speedup grows with task length: little or none on ~30 min tasks, larger on long ones.
- Breakdown: swarm makes 4-6x solo's model calls; ~40-45% of input goes to git coordination;
  10-30% is spent after a peer's last commit.
- Measure with care: box pauses inflate wall time (use active time); solo cache hit rates vary,
  so report both total and uncached input.
