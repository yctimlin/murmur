# Contrast T3b: C1-r1 (7.0), C1-r3 (7.55), C1-r4 (7.7), C2-r1 (7.55) vs solo-r1 (7.9)

Sources: run notes `runs/E1-T3b-{C1-r1,C1-r3,C1-r4,C2-r1,solo-r1}.md`, timelines (TL = line no. in each run's
timeline), judge json/md in `judge/E1/`, `result.json`. A = active minutes (timeline span). Every claim below
traces to a run note or a timeline line. Lines marked "inference" or "estimate" are my judgement.

## 1. Scoreboard
| Run | Score (j1/j2) | code | Severe (judge) | Span A | Agent-min | Rush onset A | Believed left at END | Unused A |
|---|---|---|---|---|---|---|---|---|
| C1-r1 | 7.0 (7.6/6.4) | 6/5 | 3: cli-only artifact, GC wipes cache, 500 on default trigger | 27.0 | ~80 | 18.1 (TL:526/533) | "~3min" (TL:772) | ~93 |
| C1-r3 | 7.55 (7.6/7.5) | 6/5 | 3 (j2): `HEAD` stored as sha, dup-name masks unknown dep, dense code | 32.0 | ~95 | 17.0 (TL:455) | "~8min" (TL:915) | ~88 |
| C1-r4 | 7.7 (7.8/7.6) | 6/6 | 0 | 33.5 | ~96 | 25.2 (TL:635) | "9min" (TL:797) | ~86 |
| C2-r1 | 7.55 (7.6/7.5) | 6/5 | 1 (j1): flaky watcher test | 28.1 | ~83 | 24.1 (TL:718) | "~26min" at A24 | ~92 |
| solo-r1 | 7.9 (7.5/8.3) | 6/6 | 0 | 39.4 | 39.4 | none confirmed | n/a | ~80 |

- Solo's prompt also gave a 120-minute limit. It ran `date -u` at A33.3 when wall time was about 179 minutes, but no SAY
  mentions time, and it went on to run two more fix/verify cycles (solo note §3). The swarm agents, in contrast, posted
  their "time left" estimates on the board. Those estimates came from board `created_at` stamps and `date -u`.
- Swarm runs had 2.0-2.4 times solo's agent-minutes but delivered about the same amount of code: 2,984 / about 3,300 /
  3,100 / about 3,100 Python lines, against solo's 2,659.
- Swarm building time was about 34-40 agent-minutes in C1-r1, C1-r3 and C2-r1. In C1-r4 it was about 18-28, because
  that note counts build and test together. Solo's building time was 13.1. The surplus went to coordination, seam
  fixing and endgame.

## 2. What all five share (not a swarm effect)
These penalties appear in solo too, so they are model or brief effects:
- Dense semicolon code. The code score is 5-6 in every run, solo included, and it is the largest single subscore loss.
  Every run wrote whole modules in one heredoc and patched them with `str.replace`. No run had a readability pass.
- Offset-polling logs instead of SSE.
- A hand-declared package graph.
- A thin or minified dashboard.
- "PR.md missing". PR.md is present in every delivered tree, so this is a judge-copy artifact.

The slow job is opt-in in solo as well (`sample-repo/tools/slow.py`: "Deliberate opt-in timeout exercise"). Judges
penalised the swarm runs C1-r1, C1-r4 and C2-r1 for it but not solo. That is judge variance, not a log cause.

## 3. What judges penalised in the swarm runs that solo avoided, and the causing log events
| Swarm penalty | Run | Causing event(s) | What solo did instead |
|---|---|---|---|
| A commit touching only `cli` fails because the path-skipped `corelib` provides no artifact (severe) | C1-r1 | The path filter (a2, fb01b64, A7.8) and artifact reuse in the engine (a1) were owned by different agents. The tests covered only docs-only and corelib commits (TL:476). Nobody probed a leaf-package commit. Hardening was displaced by the rush (§4). | Solo found and fixed this exact case in post-green hardening at A24.3: "a CLI-only change should reuse the filtered-out `corelib` artifact, or build that prerequisite" (solo TL:82-83). In C1-r4, a2 found it at A19.4, before its rush: "first-ever manual cli-only run, execute it" (C1-r4 TL:473). |
| GC deletes the whole cache; the size cap removes all runs (severe) | C1-r1 | A shortcut in a1's engine at A7.8: "Conservative storage cap: remove all eligible histories". It was never revisited, and no reviewer read engine GC. | One owner, scenario 16 tested. Not penalised. |
| 500 on POST /runs with the default revision (severe) | C1-r1 | The test harness always passed `revision='working'` (TL:359), so the default path was never called. | — |
| Manual trigger stores the literal `HEAD` | C1-r3 | a1 engine.trigger. No test used a symbolic ref. | — |
| Manual runs ignore the commit diff; tests inject `changed` | C1-r4 | Scenarios 2 and 3 pass `changed` explicitly. Engine semantics (a2) and the tests (a3) were written by different owners against the contract, not against the brief. | Solo's scenarios 2 and 3 drive a watched commit (`test_02_docs_only_watched_commit`, solo TL:62). |
| Unrelated jobs show "skipped", not cache hits, on a corelib change | C2-r1 | test03 was rewritten for a miniature repo with explicit `inputs` (A4.7-6.2). At A13.6 a1 asked a2 for a real-sample cascade test, but it was never written. | Solo tested on the real sample. |
| Flaky watcher test, "63 of 64" (severe) | C2-r1 | Each peer ran the suite once (A20.3, A22.5, A25.4, A25.6). The rush began at A24.1, and END came at A27.5. | Solo's repeated full runs exposed two timing flakes: test_11 at A34.7 and the ready-file race at A36.5. Both were fixed before the commit (solo TL:102-123). |
| `os.environ` in the cache key | C2-r1 | A cross-check overcorrection: a2 suggested documenting it (A13.8), but a1 hashed the whole environment instead (6db5a72, A15.4). | — |
| Thin sample (one test per package); templates barely used; DAG drawn as cards | C1-r4, C1-r3 | The ledger lines were closed by a blanket "suite passes" receipt (C1-r3 PR.md:13-43, C1-r4 PR.md:60). No one checked them against the brief's intent. | Coverage 8 and 9; not penalised. |
| Leftover tooling clutter | C1-r4 | Three agents built three separate browser-capture tools (A23.8-24.9). | — |

**Pattern.** The swarm-only defects fall into two classes:
1. **Seam semantics** (path filter x artifact reuse, trigger x diff, test x sample). The behaviour spans two owners,
   and each owner's tests passed against the agreed contract. Nobody owned the end-to-end brief scenario on the real
   sample.
2. **Unexercised defaults and timing flakes.** These are found only by an exploratory or repeated pass after the suite
   first goes green. Solo spent 11.6 A in that mode (green 53 tests at A27.8, end A39.4) and found 4 real defects there:
   the cli-only artifact, the cache key, the test_11 flake and the ready race.

Post-green hardening time in the swarm runs, measured from the first full green suite to rush onset (§4), was:
| Run | Post-green hardening before rush |
|---|---|
| C1-r1 | 0 A (green A19.7, after onset A18.1) |
| C1-r4 | about 2.4 A (green A22.8, onset A25.2), plus hardening interleaved from A18 |
| C2-r1 | about 3.8 A (green A20.3, onset A24.1) |
| C1-r3 | onset A17.0, before the suite was integrated |

This ordering matches the severe counts: C1-r1 has 3 severe, C1-r3 has 3 from j2, C2-r1 has 1 and C1-r4 has 0 (inference, n=4).

## 4. WALLCLOCK_RUSH, present in all four swarm runs, quantified for C1-r1
**Mechanism.** Peers derived "time left" from wall time: board `created_at` stamps and `date -u`. VM freezes added
about 80-93 wall minutes and no active minutes. The 120-minute cap is monotonic, and no run was capped.

**C1-r1 events.**
- A18.1 (TL:526), a3: "retain ~20m for final integrated END consensus before hard cap".
- A18.3 (TL:533), a3: "~30m left hard cap; all ledger claims must move DONE/DESCOPED".
- A19.7 (TL:592), a1: "hard cap ~31min remaining".
- A23.3 (TL:705), a3 runs `date -u` and gets "16:57:47 UTC".
- A23.4 (TL:710), a1: "hard cap started15:03 =>17:03 (~6min) ... close ledger immediately; avoid more scope".
- A23.8 (TL:728), a2: "~5min".
- A24.8 (TL:772), a1: "~3min before cap".

**Quantification.**
- **Size of the misreading.** At A23.4 the agents believed 114 of 120 minutes were gone. The real figure was 23.4
  active minutes, so they overestimated elapsed time by about 4.9 times.
- **Budget used.** The run ended at A27.0 (34.4 by result.json), which is 22-29% of the cap. About 85.6-93 active
  minutes were unused, roughly 3.2 times the whole run again.
- **Endgame share.** The endgame (ledger, docs, END) took A18.1-27.0, which is 8.9 A or 33% of the span. That is 27
  agent-minutes across three peers.
- **Rushed docs.** DESIGN.md was written in about 3 A (A16-19).
- **No hardening.** C1-r1 is the only run with 0 A of post-green, non-rushed hardening.
- **Most extreme of the four.** C1-r1 had the earliest onset relative to green and the most panicked END. C1-r1
  believed "~3min" left at END, C1-r3 "~8min", C1-r4 "9min", and C2-r1 had about 26 minutes in mind at A24.

**Effect on score (estimate).**
- Nothing that was planned got dropped. All three severe defects were never found, rather than cut.
- The cli-only defect is the one solo and C1-r4 both found in a hardening pass. C1-r1 had no such pass.
- j2's 6.4 (correctness 6, coverage 7, design 6) is driven by the two severe bugs it named. The sibling runs got 7.5-7.6
  from j2 without them.
- If the cli-only and GC bugs had been found, C1-r1 would plausibly score about 7.5. That means the rush accounts for
  roughly 0.5 of C1-r1's deficit to its siblings.
- Against solo, the rush accounts for most of the 0.9 gap. Code style (code 5 vs 6) explains about 0.1-0.2 of it.
- Caveat: all four swarm runs rushed. The rush depressed every swarm run, which is why none reached solo's
  verification depth. C1-r1 was simply the worst affected.

## 5. Low vs high swarm runs: decision points that differed
1. **When the rush began relative to green.** C1-r4 (best swarm) and C2-r1 reached a full green suite 2-4 A before the
   rush. C1-r1 and C1-r3 entered endgame at A17-18, before or as the integrated suite went green.
2. **A dedicated real-process acceptance harness early.**
   - C1-r4: a3 built 93978cf at A12.5, and the suite went from 31/37 to 56/56 by A22.8.
   - C2-r1: the checks were written before product code (A2.3-5.4).
   - C1-r1: the acceptance tests came at A12.8-16.0, split by owner, each owner testing their own scenarios. That is
     self-referential, and no one tested across seams.
3. **A pre-rush seam hunt by a non-owner.** C1-r4 a2's "hardening plan" (TL:473) and C2-r1 a2's cross-check phase
   (A12.4-19.6) found real seam bugs. C1-r1's only seam probe was the upstream cache key (TL:418). Its inverse, the
   leaf-package commit, was never tried.
4. **END verification depth.** In C1-r4, a2 and a3 ENDed on 4 focused tests (TL:850/858). In C2-r1 each peer ran the
   suite once. Solo needed 3 red full runs late in its run (A34.7, A36.5) before it got green.

## 6. Mechanisms that would have changed the outcome, and predicted log signatures
1. **Inject active time into the board, and forbid wall-clock cap estimates.**
   - Fix: give peers an `elapsed_active` tool or a board header such as "A23/120".
   - Prediction: no "~N min left" posts derived from `date -u` or `created_at`.
   - Prediction: END is not reached before about A60-90.
   - Prediction: timeline spans grow from 27-33 A to over 60 A per peer.
   - Prediction: post-green time grows from 0-4 A to over 15 A.
2. **A post-green "adversarial scenario" phase assigned to non-owners.**
   - Fix: each peer must try 3 brief scenarios on the real sample through untested defaults (leaf-package commit,
     plain trigger, symbolic ref, default revision). Each try is posted as `PROBE <scenario> PASS/FAIL`.
   - Prediction: PROBE posts with at least 1 FAIL per run, followed by fix commits.
   - Prediction: C1-r1's cli-only, GC and 500 defects, C1-r3's HEAD defect and C1-r4's diff defect surface as FAILs.
3. **Repeat runs as an END precondition.**
   - Fix: require 3 consecutive full-suite passes on the END sha. Solo effectively did this.
   - Prediction: END posts carry a "3/3 green" receipt.
   - Prediction: timing flakes such as C2-r1's watcher race appear as intermittent FAILs before END.
4. **Ledger receipts must cite the brief clause and the real-sample evidence, not "suite passes".**
   - Prediction: fewer blanket DONE receipts.
   - Prediction: thin-sample, template and DAG-card lines reopen instead of closing at A25.
5. **(All arms, including solo) a readability gate.**
   - This is the largest shared loss: code 5-6.
   - Prediction: refactor commits splitting one-liners, and a lower semicolon-per-line count on main.
   - This would not change the swarm vs solo ordering.

None of fixes 2-4 can work without fix 1. In every swarm run, the perceived deadline is what ended the hardening
phase, not the ledger.
