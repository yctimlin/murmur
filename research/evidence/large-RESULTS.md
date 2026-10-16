# Large-task integration-quality results (PLAN.md pre-registered; judges blind, 1 pass each)
Active min = event-gap-capped (120 s) time over all sessions (box pauses excluded, same for all arms).

| task | arm | active min | input | uncached | output | correct | regress | risk (P0/P1) | PR.md | design | mean |
|---|---|---|---|---|---|---|---|---|---|---|---|
| T1 huey dead-letter | base | 25.7 | 13.80M | 398k | 87k | 8 | 7 | 3 (3/1) | 7 | 8 | 6.6 |
| T1 | new | 35.3 | 20.90M | 573k | 96k | 7 | 10 | 7 (1/1) | 7 | 7 | 7.6 |
| T1 | solo | 28.3 | 2.48M | 191k | 40k | 7 | 10 | 8 (0/2) | 8 | 7 | 8.0 |
| T2 research synthesis (plain folder) | base | 24.5 | 12.01M | 448k | 79k | 10 | 10 | 5 (2/1) | 10 | 9 | 8.8 |
| T2 | new | 22.3 | 12.35M | 378k | 78k | 10 | 10 | 7 (1/1) | 10 | 9 | 9.2 |
| T2 | solo | 22.8 | 1.20M | 102k | 34k | 10 | 10 | 9 (0/1) | 10 | 9 | 9.6 |
| T3 moneyfold (greenfield) | base | 20.6 | 8.86M | 283k | 82k | 9 | 10 | 9 (0/1) | 9 | 9 | 9.2 |
| T3 | new | 18.5 | 7.57M | 333k | 72k | 9 | 10 | 7 (1/1) | 8 | 8 | 8.4 |
| T3 | solo | 28.6 | 1.84M | 73k | 47k | 9 | 10 | 9 (0/1) | 9 | 9 | 9.2 |

Means: base 8.2, new 8.4, solo 8.9. P0 totals: base 5, new 3, solo 0.
H-q (new >= base + 0.5 and fewer P0): mean +0.2 -> FAIL (P0s fewer). H-t: T1 time +37%, uncached
+44% -> FAIL. Decision per pre-registered rule: do not keep M1-M3 as is.
Seams: new peers ended later relative to the last main commit on T1 (last commit 50.2, ends 46.5-51.2)
but not on T2/T3 (ends 0.6-1.3 min after last commit, like base). Review posts: T1 24->37,
T2 35->44, T3 35->28.
