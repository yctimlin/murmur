# Round-2 report (facts; Taipei time)

## Results per arm per task (3 peers, gpt-6-astra high, 90m cap, 1 run each, 2 blind judge passes averaged)
quality = mean(c, r, risk, pr, d); risk = adversarial score (10-2*P0-P1); seam P0 = judge-flagged SEAM P0 whose locations git-blame to >=2 peers.
Active min = gap-capped (120 s) union of session events. Input/uncached/output = sum over all codex sessions.
| task | arm | passes | quality | c | r | risk | pr | d | P0 | seam P0 | active min | input | uncached | output | hidden tests |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| W1 | orig | 2 | 6.8 | 9.0 | 7.0 | 5.0 | 5.5 | 7.5 | 2.0 | 0.5 | 33.7 | 12.46M | 450k | 80k | 14 passed in 2.57s |
| W1 | base | 2 | 8.6 | 9.5 | 10.0 | 6.5 | 8.5 | 8.5 | 0.5 | 0.5 | 41.9 | 13.58M | 250k | 72k | 14 passed in 2.60s |
| W1 | a1 | 2 | 7.3 | 8.5 | 10.0 | 5.5 | 5.5 | 7.0 | 1.0 | 0.0 | 46.2 | 15.25M | 458k | 58k | 14 passed in 2.57s |
| W1 | a2 | 2 | 7.6 | 8.0 | 8.5 | 6.0 | 7.5 | 8.0 | 1.5 | 1.0 | 52.0 | 17.78M | 328k | 74k | 14 passed in 2.57s |
| W1 | a5 | 2 | 7.8 | 8.5 | 8.5 | 7.0 | 7.0 | 8.0 | 1.0 | 0.5 | 39.1 | 14.73M | 538k | 71k | 14 passed in 2.59s |
| W1 | solo | 2 | 7.8 | 8.5 | 7.0 | 7.5 | 8.5 | 7.5 | 0.5 | 0.0 | 39.7 | 3.34M | 109k | 44k | 14 passed in 2.56s |
| W2 | orig | 2 | 7.4 | 8.0 | 8.5 | 5.0 | 7.0 | 8.5 | 1.5 | 0.0 | 27.1 | 11.70M | 340k | 88k | 16 passed in 17.22s |
| W2 | base | 2 | 1.1 | 0.0 | 0.0 | 5.5 | 0.0 | 0.0 | 2.0 | 0.0 | 38.9 | 7.12M | 139k | 26k | 1 failed, 15 errors in 0.22s |
| W2 | a1 | 2 | 7.4 | 7.5 | 10.0 | 4.5 | 7.0 | 8.0 | 1.0 | 0.5 | 32.0 | 11.40M | 280k | 68k | 16 passed in 15.28s |
| W2 | a2 | 2 | 1.4 | 0.0 | 5.0 | 2.0 | 0.0 | 0.0 | 3.5 | 0.0 | 35.0 | 10.94M | 205k | 36k | 1 failed, 15 errors in 0.23s |
| W2 | a5 | 2 | 7.0 | 7.0 | 8.5 | 4.5 | 7.5 | 7.5 | 1.0 | 0.5 | 49.2 | 17.94M | 415k | 76k | 16 passed in 14.32s |
| W2 | solo | 2 | 8.5 | 8.0 | 10.0 | 6.5 | 9.0 | 9.0 | 1.0 | 0.0 | 37.0 | 2.90M | 101k | 52k | 16 passed in 16.97s |
| W3 | orig | 2 | 7.8 | 7.0 | 10.0 | 6.5 | 7.5 | 8.0 | 1.0 | 0.0 | 20.0 | 8.26M | 263k | 84k | 38 passed in 0.12s |
| W3 | base | 2 | 7.5 | 7.0 | 10.0 | 5.0 | 7.5 | 8.0 | 2.0 | 1.0 | 21.2 | 9.58M | 239k | 76k | 38 passed in 0.16s |
| W3 | a1 | 2 | 7.2 | 8.0 | 10.0 | 2.5 | 7.5 | 8.0 | 2.0 | 0.5 | 21.9 | 11.73M | 353k | 76k | 38 passed in 0.12s |
| W3 | a2 | 2 | 7.6 | 7.0 | 10.0 | 6.0 | 7.0 | 8.0 | 1.0 | 0.0 | 23.0 | 12.57M | 247k | 65k | 38 passed in 0.11s |
| W3 | a5 | 2 | 7.6 | 8.5 | 10.0 | 4.5 | 6.5 | 8.5 | 2.5 | 0.5 | 18.8 | 8.26M | 272k | 60k | 38 passed in 0.10s |
| W3 | solo | 2 | 9.8 | 10.0 | 10.0 | 9.0 | 10.0 | 10.0 | 0.0 | 0.0 | 25.2 | 1.67M | 89k | 46k | 38 passed in 0.14s |

## Gates (eval-plan.md, base = 658d82a). Base: quality W1 8.6 / W2 1.1 / W3 7.5 (mean 5.73), total P0 4.5, active 41.9 / 38.9 / 21.2.
| proto | Q mean (>= 6.03) | per-task >= base-0.5 | P0 total <= 4.5 | speed <= 1.10x base every task | input <= 2x solo every task | <= 1.25x base input | fired >= 2/3 | verdict |
|---|---|---|---|---|---|---|---|---|
| a1 integration-barrier | 7.30 pass | FAIL W1 7.3 < 8.1 | 4.0 pass | FAIL W1 46.2 > 46.1 | FAIL 4.6x / 3.9x / 7.0x | pass W1/W3; W2 11.40 > 8.90 FAIL | 3/3 (receipt recorded on every task) | REJECT |
| a2 cross-review | 5.53 FAIL | FAIL W1 7.6, W2 1.4 | 6.0 FAIL | FAIL W1 52.0 | FAIL 5.3x / 3.8x / 7.5x | FAIL W2, W3 | 2/3 (W1 22 / W3 28 paths with receipts; W2 0 paths) | REJECT (lower mean + slower) |
| a5 contracts | 7.47 pass | FAIL W1 7.8 < 8.1 | 4.5 pass | FAIL W2 49.2 > 42.8 | FAIL 4.4x / 6.2x / 5.0x | FAIL W2 17.94 > 8.90 | 3/3 activation + 14-16 gate checks, 0 rejections | REJECT |
No prototype kept. The confirmation-rerun clause doesn't apply (no prototype passed). The base W2 score (1.1, no code delivered) lowers the base mean; even so, every prototype fails the per-task, speed or token gates.
Every swarm arm, base and orig included, is 2.5-7.5x solo input tokens, so the <=2x-solo gate can't be met by any 3-peer arm here.

## Round-1 (658d82a, "base") vs original (eec78f8, "orig")
quality orig 6.8 / 7.4 / 7.8 (mean 7.33) vs base 8.6 / 1.1 / 7.5 (mean 5.73); active orig 33.7 / 27.1 / 20.0 vs base 41.9 / 38.9 / 21.2; input orig 12.46M / 11.70M / 8.26M vs base 13.58M / 7.12M / 9.58M.
Round-1 is slower on all 3 tasks and failed W2 outright. It scored higher only on W1 (+1.8).
Solo's quality was higher than every swarm arm on W2 and W3 and tied the best non-base arms on W1. Solo used the least input on every task.

## W2 zero-commit (base, a2)
- Both runs exited 0 with 0 commits on main. The result folder is an unchanged copy of the input, so the hidden tests error out (no docsearch.py).
- base board: 3 drafts were posted, all 3 peers ranked them (a2 first by 2 of 3), and then no peer brought the winner onto main. Every peer ended its turn after drafting and ranking. One post says "send parent integration notes". The root's wait returned and the run ended.
- a2 run: same pattern (drafts on draft/a1-3, task_complete "Draft completed"), with 6-16 HTTP 429 retries per session.
- Classification: an arm failure (peers abandoned the integration step) plus a murmur bug (`run` reports success with an empty main, and nothing checks that main advanced). This isn't deterministic for 658d82a: a1 and a5 (same base) integrated on W2, and orig integrated.
- 658d82a differs from eec78f8 in the root prompt. It spawns peers with `fork_turns: "none"` (fresh threads) and calls `wait_agent` with no ids. Peer prompts are identical apart from ports. That this causes the failure is a hypothesis, not tested.

## murmur bugs seen
1. The root dies on a transient 429 and ends the whole run. W1-a5 first attempt: 7.3 min, 0 commits; rerun.
2. 429 at the start also failed W1-a1's first attempt (1.5 min); rerun.
3. setup writes an empty models.json when `codex debug models` returns no models, and doesn't check it. W2-a1 first attempt failed at 0.0 min; rerun.
4. The root hangs in an empty `wait` (receiver_thread_ids=[]) after all peers finish. W1-orig hung about 47 min; SIGINT to murmur was ignored, and it was ended by SIGTERM to the root codex. Active time is unaffected.
5. `run` exits 0 with 0 commits on main (W2 base, W2 a2).
6. Nested murmur inside a Codex sandbox fails with "app-server socket directory must be a user-owned directory with mode 0700". Because of this, no round-2 prototype passed a live screen.
Operator harness bugs, fixed with no change to sealed tasks or scoring:
- W3 hidden-test path: the first rubric judges got wrong input and were rerun.
- rsync missing, so W2 judge sources were empty; they were rebuilt and the judges rerun.
- A map-label race; the affected judge dirs were rebuilt.
Box pauses during interrupts make wall clocks unreliable. Active time is gap-capped, so the pauses add at most 2 min per gap.
