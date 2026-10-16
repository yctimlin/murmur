# Token-lean round 1 (U1 peewee history/restore, U2 quire SSG); cap 75m; active = gap-capped
| task | arm | active min | input | uncached | x solo (uncached / input) | c | r | risk | pr | d | mean |
|---|---|---|---|---|---|---|---|---|---|---|---|
| U1 | base (main) | 23.8 | 12.54M | 344k | 3.7 / 5.7 | 6 | 10 | 6 | 7 | 8 | 7.4 |
| U1 | lean (G1+G2) | 27.4 | 14.36M | 367k | 3.9 / 6.5 | 7 | 10 | 6 | 7 | 8 | 7.6 |
| U1 | solo | 25.9 | 2.21M | 93k | 1 | 7 | 10 | 5 | 7 | 8 | 7.4 |
| U2 | base (main) | 33.2 | 17.92M | 486k | 4.3 / 7.9 | 6 | 10 | 1 | 7 | 8 | 6.4 |
| U2 | lean (G1+G2) | 26.5 | 14.04M | 377k | 3.4 / 6.2 | 7 | 10 | 5 | 7 | 8 | 7.0 |
| U2 | solo | 36.5 | 2.27M | 112k | 1 | 7 | 10 | 1 | 8 | 8 | 6.8 |
G1 sync helper was used (100+ calls) but did not cut call counts; git-coordination share unchanged.
Result: lean -> uncached +7% / -22%; far from 2x solo. Quality and speed not worse.
