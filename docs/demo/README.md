# Replay demos

Pages and text made by `murmur replay` (see [Replay](../../README.md#replay)). Download an `.html`
file and open it in a browser; each holds its own data and loads nothing from the network.

| File | What it is |
|------|------------|
| [`race-real.html`](race-real.html), [`race-real.txt`](race-real.txt) | A real pair made with this code on 2026-11-11: a 2-peer swarm (`swarm2`) and one agent (`solo2`) on the same brief, a small feature for a toy `wordstats.py` repository, same model, effort, base and cap. The solo run finished sooner (1:45 against 4:26) with fewer tokens (108,013 input against 1,234,194). No quality score was supplied, so none is shown. |
| [`race-E1-T3b.html`](race-E1-T3b.html) | The round-4 research pair `E1-T3b-base4-r1` (3 peers) and `E1-T3b-solo-r1` (one agent), imported from the published forensics timelines. |

`race-real.*` were made with:

```bash
murmur replay runs/swarm2 runs/solo2 > race-real.txt
murmur replay runs/swarm2 runs/solo2 --html race-real.html
```

`race-E1-T3b.html` was made from files on the `experiment/self-improve-r4` branch:

```bash
git archive origin/experiment/self-improve-r4 research-r4/analysis/forensics/timelines \
    research-r4/results/E1.json | tar -x -C /tmp/r4
T=/tmp/r4/research-r4/analysis/forensics/timelines
python scripts/timeline_to_replay.py $T/E1-T3b-base4-r1.md $T/E1-T3b-solo-r1.md \
    --results /tmp/r4/research-r4/results/E1.json --html race-E1-T3b.html
```

What to keep in mind about the research pair:

- Every number on the page comes from those two timeline files or from `results/E1.json`, and the
  page names the file next to each. What they do not record is shown as "not recorded": the
  model, effort and brief hash, per-agent tokens, cached input, which commits are on `main`, and
  change receipts (those need a run's session logs and its `origin.git`).
- The page warns that the pair is not like for like as far as the files show: the two runs
  started from different commits (`fb6b79f`, 17 files, and `52ec4c6`, 18 files).
- Its clock is the timeline's own "active minutes", an estimate that leaves out host freezes and
  counts no gap between events as more than 120 s. On it the swarm ends at 25.4 min and the solo
  run at 39.4 min. The files give other figures for the same runs, and the page lists them:
  `result.json` says 33.91 and 58.07 active minutes, `E1.json` `active_nf` says 25.37 and 47.49,
  and the wall clock ran 124.09 and 233.24 minutes because the host was frozen for long stretches.
  `--clock wall` puts the events on the wall clock instead.
- Input tokens were 15,019,628 for the swarm and 4,336,042 for the solo run; 34 commits against 1.
- The judges' scores (7.8 and 7.9) are shown as supplied by the research files. The replay does
  not count a score as a win, and a difference of 0.1 between two runs says little: the solo
  run's two judges alone gave 7.5 and 8.3.
- Tool calls come from call text that the timeline cut to a few hundred characters, so their
  kinds are rougher than for a workspace, and few commands have an exit status.
