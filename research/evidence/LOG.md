# murmur research log (times Taipei)

## Baseline batch 1 (A tinydb, B splitledger; 40m cap) — see /workspace/murmur-eval/RESULTS.md
Swarm ≈ solo on quality (8.8/9.0 vs 9.0/8.4), not faster (21-27 vs 22-24 min), 3-6x input tokens.

## E1 non-git folder + peer count (task C: messy CSV analysis, 20m cap)
| arm | wall min | input | uncached | output | acc | repro | report | pr |
|---|---|---|---|---|---|---|---|---|
| swarm-3 | 16.1 | 4.89M | 207k | 39k | 10 | 10 | 10 | 9 |
| swarm-2 | 15.6 | 3.14M | 157k | 27k | 10 | 10 | 10 | 10 |
| swarm-3 draft=cap/8 (E2) | 16.4 | 5.68M | 226k | 39k | 10 | 10 | 10 | 10 |
| solo codex | 16.1 | 0.44M | 50k | 16k | 10 | 10 | 10 | 10 |
- H1 confirmed: plain folder works via snapshot prototype; raw files md5-identical after runs.
- H2: 2 peers = same quality, -36% input, -24% uncached, same time -> keep "fewer peers for small".
  But solo dominates (same quality/time, 10x fewer tokens).
- E2 (draft allowance) DISCARD: drafts self-finish in 2-4 min regardless of allowance.

## R1 disable plugins/apps for agents (micro-benchmark)
Fresh CODEX_HOME: 104 MB -> 3.2 MB, 7.4 s -> 6.5 s first call, identical prompt tokens (17,506).
In runs: codex-home 82 MB -> 9 MB per workspace. KEEP (free, no capability agents can use).

## E3 size the process (task D: meeting notes -> status pack, plain folder, 15m cap)
| arm | wall min | input | uncached | output | acc | fid | use | pr |
|---|---|---|---|---|---|---|---|---|
| swarm-3 current | 7.5 | 3.06M | 211k | 25k | 8 | 10 | 9 | 9 |
| swarm-3 + E3 | 5.1 | 2.12M | 90k | 15k | 8 | 10 | 9 | 9 |
| solo codex | 2.9 | 0.14M | 8k | 4k | 8 | 10 | 9 | 9 |
- E3 KEEP: -32% time, -31% input, -57% uncached, same quality (agents skipped drafts by themselves).
- Still: solo 2.6x faster and 15x fewer tokens on a tiny task. The real fix for small tasks is
  routing: don't swarm (SKILL.md guidance), or a per-run "solo if small" decision.

## Non-git design: large files
300 MB folder (200 MB binary + 98 MB CSV), 3 peers, overlayfs (no reflink):
| mode | setup | disk |
|---|---|---|
| everything in git | 27.5 s | 1.1 GB (origin 243M + 3x295M trees) |
| files > 50 MB as shared read-only symlinks | 0.3 s | 296 MB |
Prototype (branch feat/folder-input, pushed, no PR): `--max-file-mb` (default 50), `murmur export`
(`--to DIR` new folder with links resolved; `--apply` writes changes back only where the user
didn't edit during the run, else writes `<file>.murmur-<id>` beside theirs). 27 tests pass.

## Note on timing
The box paused 01:28:30-01:39:09 (all sessions froze, then resumed together). Swarm minutes below
are murmur active time (pauses excluded); solo minutes = wall - 639 s for runs spanning the pause.

## E4/E5 (task F: md + PNG + CSV -> static site, plain folder, 15m cap)
| arm | min | input | uncached | output | acc | fid | use | pr |
|---|---|---|---|---|---|---|---|---|
| swarm-3 + E3 (control) | 7.2 | 1.98M | 92k | 19k | 10 | 10 | 10 | 10 |
| + E4 idle peers end early | 7.3 | 2.12M | 174k | 22k | 10 | 10 | 10 | 9 |
| + E5 shared scouting map | 6.7 | 2.11M | 103k | 21k | 10 | 10 | 10 | 10 |
| solo codex | ~8.3 | 0.37M | 35k | 12k | 10 | 10 | 10 | 10 |
- E4 DISCARD (+89% uncached: ended peers get woken and rebuild context). E5 DISCARD (-7% time,
  +12% uncached: within noise, below the 15% bar).
- Read overlap (A/B/C logs): 50-67% of files read by >=2 peers, but mostly cached tokens; scouting
  can't remove the main cost, which is each peer's context re-sent per call.
- Non-code deliverables: peers split naturally by file (STATUS.md vs ACTIONS.csv, build.py vs
  REPORT.md); no merge conflicts seen in C/D/F. Found: scratch `.work/` got committed into the
  result (D) -> `murmur export` now leaves `.work/` out (feat/folder-input).

## L — larger open-ended tasks (cap 50m)
| task | arm | min | input | uncached | output | correct | regress | risk (P0/P1) | PR.md | design |
|---|---|---|---|---|---|---|---|---|---|---|
| L1 tablib diff/merge | swarm-3 | 14.4 | 5.65M | 209k | 52k | 9 | 10 | 4 (2/2) | 8 | 9 |
| L1 | solo | ~15.7 | 1.15M | 77k | 27k | 9 | 10 | 7 (1/1) | 9 | 9 |
| L2 kanban web app (plain folder) | swarm-3 | 24.9 | 10.00M | 346k | 94k | 7 | 10 | 8 (1/0) | 8 | 8 |
| L2 | solo | ~38.4 | 1.77M | 53k | 51k | 9 | 10 | 8 (1/0) | 9 | 9 |
Means: L1 swarm 8.0 vs solo 8.8; L2 swarm 8.2 vs solo 9.0. Swarm 1.09x (L1) / 1.54x (L2) faster,
4.9x / 5.6x input, 2.7x / 6.5x uncached. The pre-existing base failure in tablib was correctly
reported as pre-existing by the swarm (batch-1 regression rule works).

## Conclusions so far
1. Swarm pays off in speed only on larger, parallelisable work (L2 1.5x); on <=25 min tasks it is
   no faster than solo and costs 3-15x tokens. Quality: swarm <= solo in 4 of 7 comparisons, never
   clearly better; risk-path bugs remain for both.
2. Kept: R1 (disable plugins/apps), E3 (skip drafts when small) -> branch feat/efficiency-small-tasks.
   Discarded: E2 draft allowance, E4 idle peers stop, E5 shared scouting.
3. Non-git: snapshot + large-file links + export (--to / --apply edit-safe) on feat/folder-input.
4. Next candidates: route small tasks to solo (SKILL.md guidance / an automatic size check); a
   quality lever for swarms (the integration review is where swarms lose points: c=7 on L2).

## Large tasks only (user decision 09:21) — why swarm quality drops (verified from logs)
Script: explore/seams.py (peer end times, test runs after the final main commit); git blame on
judge-reported P0 lines; board-post grep for harm-path claims.
- C1 single-author logic: every swarm P0 on L1/L2 sits in a file written by one peer only
  (L2 static/app.js: all 3 commits a2; L1 core compare logic: a1, other peers wrote tests/docs from
  the spec). The L2 UI race (dialog captures board A, mutate() uses global board B -> deletes the
  wrong board) is a UI/API seam nobody else exercised.
- C2 end-together: peers end within 0.5-3 min of each other in all 7 swarm runs; the final main was
  tested afterwards by 0 (L1), 1 (L2, A-new, B-new, A-old) peers; 2-6 commits land in the last 20%.
- C3 harm-path review under-applied: L2 had 1 harm-path claim (backend ordering), L1 had 1
  ("independent adversarial safety tests" written in parallel with the implementation).
- E3 side effect: on L1 the peers chose the "small direct split" (no drafts) on a 50m task; the
  core was then built by one peer in ~7 min. E3 excluded from the large-task arms.
Pre-registered experiment: /workspace/large/PLAN.md (T1 huey dead-letter, T2 plain-folder
research synthesis, T3 greenfield money importer; base vs new vs solo; started 09:26).
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

## Token-lean phase (user decision 11:07: baseline = original main; target ~1.5-2x solo tokens)
Breakdown (large/breakdown.py, large/cmdmix.py on T1-T3 base vs solo):
- Swarm makes 4-6x the model calls in total (46-58 per peer vs 26-39 solo) at a similar context per
  call (60-80k vs 50-69k) -> input scales with calls. Uncached 2.1-4.4x solo.
- Per call kind: shell 77-82% of input, board 8-12%, plain messages 5-9%. Waiting (root) ~2%.
- Phase: drafts 4-11% of input (7-20% of uncached); build 75-93%; tail after the final main commit
  10-15% of input.
- Within shell calls, git coordination (pull/rebase/push/commit + status/log/diff) = 41-45% of swarm
  input vs 23-35% solo; test runs 4-5x solo's count; tool output size is not the driver (0.6-9.5M
  chars total, mostly screenshots/HTML in T2/L2).
Side question (smaller speedups vs trials 2/3): speedup vs solo grows with task length:
  solo 67/57 min -> 1.6-1.8x (trials 2/3); solo 38 min -> 1.5x (L2); solo 22-29 min -> 0.9-1.4x
  (A, B, L1, T1-T3); solo <=16 min -> <=1x. Added rules also cost: A-old (main) 21.0 min/9.3M vs
  A-new (batch 1) 26.9 min/12.8M. So both: mostly task size, plus ~25-35% from batch-1 rules.
Experiment (lean/PLAN.md, pre-registered): base = original main, new = feat/token-lean
(G1 one-call sync helper, chain commands, G2 share full-check results), solo; tasks U1 peewee
change history + restore, U2 greenfield static site generator; cap 75m; started 11:11.
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
Round 2 started 12:00 (lean2/PLAN.md): base vs lean3 (+G3 split final review) vs lean2 (2 peers) vs solo on V1 bottle plugins, V2 notedrift.
R2 interim 12:47: V1 base 20.8m/370k, lean3 15.4m/295k, lean2 16.9m/211k, solo 21.7m/115k; V2 base 33.9m/398k, lean3 22.0m/343k, lean2 22.1m/172k; solo running
# Token-lean round 2 (lean2/PLAN.md), cap 75m, active = gap-capped
| task | arm | active min | input | uncached | x solo uncached / input | c | r | risk | pr | d | mean |
|---|---|---|---|---|---|---|---|---|---|---|---|
| V1 bottle plugins | base (main, 3p) | 20.8 | 11.34M | 370k | 3.2 / 5.3 | 7 | 10 | 6 (2/0) | 7 | 8 | 7.6 |
| V1 | lean3 (G1-G3, 3p) | 15.4 | 7.46M | 295k | 2.6 / 3.5 | 9 | 10 | 4 (3/0) | 8 | 8 | 7.8 |
| V1 | lean2 (G1-G3, 2p) | 16.9 | 5.24M | 211k | 1.8 / 2.5 | 7 | 10 | 8 (1/0) | 7 | 8 | 8.0 |
| V1 | solo | 21.7 | 2.12M | 115k | 1 | 8 | 10 | 7 (1/1) | 9 | 8 | 8.4 |
| V2 notedrift | base (main, 3p) | 33.9 | 16.41M | 398k | 3.9 / 4.3 | 7 | 10 | 1 (3/3) | 8 | 8 | 6.8 |
| V2 | lean3 | 22.0 | 10.44M | 343k | 3.4 / 2.7 | 5 | 10 | 5 (1/3) | 6 | 7 | 6.6 |
| V2 | lean2 | 22.1 | 4.33M | 172k | 1.7 / 1.1 | 8 | 10 | 5 (2/1) | 8 | 8 | 7.8 |
| V2 | solo | 48.1 | 3.84M | 102k | 1 | 10 | 10 | 7 (1/1) | 8 | 9 | 8.8 |
Round 2 decision (pre-registered rule): lean2 (G1-G3 + 2 peers) PASSES on both tasks: uncached
1.8x / 1.7x solo (target <=2x), active time 16.9 vs 20.8 and 22.1 vs 33.9 min (faster than base),
mean 8.0 vs 7.6 and 7.8 vs 6.8. lean3 (3 peers) fails the token target (2.6x / 3.4x) though
faster. Base speedup vs solo: V1 1.04x, V2 1.42x; lean2: 1.28x, 2.18x.
Main lever = peer count; prompt-level coordination tweaks give 15-35% input (more on total input
than uncached). Caveat: 1 run x 1 judge per arm; quality differences within noise.
## Validation (val/PLAN.md) pre-registered 14:20
- 14:18 launched 8 val runs (6 swarm + 2 solo)
- 14:46 val runs in progress
- 15:06 W1 all done, W2-base done; W2 lean2/lean3/solo running
- 15:07 W1 blind judging launched (E1-E4, map.txt)
- 15:21 all 8 runs done; W2 blind judging launched (F1-F4)
- 15:48 judging partial: E1 W1 base - | ADV: p0=3 p1=1 score=3;E2 W1 lean3 - | ADV: p0=5 p1=0 score=0;E3 W1 solo - | ADV: p0=4 p1=1 score=1;E4 W1 lean2 - | ADV: p0=4 p1=1 score=1;F1 W2 solo - | ADV: p0=0 p1=1 score=9;F2 W2 lean3 - | ADV: p0=3 p1=0 score=4;F3 W2 base - | ADV: p0=1 p1=0 score=8;F4 W2 lean2 SCORES: c=7 r=10 pr=6 d=7 | ADV: p0=2 p1=0 score=6;
- 15:48 VAL DONE: no arm passes keep rule; see val/RESULTS.md
- 17:13 PR #4 opened: feat/folder-input -> main (4 commits, 27 tests pass)
- 12:23 PR #4 review fixes pushed (677a691, f85b116): export/--apply removed, sibling output, exec/symlink/nested/gitignore; 29 tests pass
- 17:14 PR#4 perf/atomic/global-ignore fixes (444768f, 90d8501), 32 tests; e2e 2-peer folder run OK 8.0min
- 18:27 big3 launched (3-peer folder swarm + solo), setup 3.5s
- 18:53 big3 running
- 19:31 big3 swarm done 28.1min wall, result folder written; solo still running
- 19:41 big3 solo done (active 34.2m); blind judging G1/G2 launched
- 20:18 big3 DONE: swarm 28.1m wall/31.0 active, in 14.43M uncached 397k out 100k, mean 8.33 (c9 rb9 cp10 d9 pr9 adv4); solo 34.2 active, in 3.01M uncached 88k out 52k, mean 7.67 (9,8,9,9,9 adv2). Folder input OK: setup 3.5s, 73 entries, modes kept, 80MB linked, source md5 unchanged, 95 files out.
