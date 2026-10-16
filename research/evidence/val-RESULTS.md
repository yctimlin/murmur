# Validation results (PLAN.md pre-registered, blind judging; map in judge/map.txt)
| task | arm | uncached (x solo) | total in (x solo) | active min | mean (c,r,adv,pr,d) |
|---|---|---|---|---|---|
| W1 | solo | 105k (1.0) | 2.80M (1.0) | ~34 (wall) | 6.4 (6,10,1,7,8) |
| W1 | base3 | 391k (3.7) | 18.1M (6.5) | 32.5 | 6.8 (6,10,3,7,8) |
| W1 | lean2 | 459k (4.4) | 9.9M (3.5) | 35.0 | 6.2 (6,10,1,6,8) |
| W1 | lean3 | 441k (4.2) | 12.4M (4.4) | 30.0 | 6.0 (6,10,0,6,8) |
| W2 | solo | 132k (1.0) | 5.83M (1.0) | ~62 (wall) | 8.4 (7,10,9,8,8) |
| W2 | base3 | 1482k (11.2) | 27.2M (4.7) | 47.2 | 8.2 (8,10,8,7,8) |
| W2 | lean2 | 604k (4.6) | 15.7M (2.7) | 47.5 | 7.2 (7,10,6,6,7) |
| W2 | lean3 | 1074k (8.1) | 21.8M (3.7) | 52.2 | 7.6 (8,10,4,8,8) |
Rule: uncached <=2x solo, time <=base*1.15, mean >=base-0.7, on both tasks.
lean2: token FAIL (4.4x/4.6x), time pass, quality W1 pass (-0.6) but W2 FAIL (-1.0) -> DISCARD.
lean3: token FAIL, time pass, quality W1 FAIL (-0.8), W2 pass -> DISCARD.
