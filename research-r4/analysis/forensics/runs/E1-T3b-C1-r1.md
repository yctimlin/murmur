# E1-T3b-C1-r1 (T3b self-hosted CI platform, arm C1, score 7.0)

Sources: timeline `timelines/E1-T3b-C1-r1.md` (TL = line number), judges `judge/E1/E1-T3b-C1-r1.j1.md/.j2.md`,
prompts `lab/ws/E1-T3b-C1-r1/prompts/a1.md`, origin.git log, delivered tree, result.json.

## 1. Outcome
- Score 7.0 (j1 7.6, j2 6.4). Both judges guessed "single" agent (uniform style).
- Severe penalties (quoted):
  - j1: "POST /api/v1/runs with default revision on a non-git repo returns generic 500 internal_error instead of a 4xx".
  - j2: "Commit touching only packages/cli fails: path-skipped upstream corelib provides no artifact, so cli fails
    with 'Missing consumed artifact'"; "GC deletes the entire cache whenever any run is collected, and the size cap
    removes all eligible runs".
- Other deductions (both): `slow` job never times out in the sample run (SLOW_SECONDS 0.01 vs timeout 2); templates
  save little (every job overrides `command`); log streaming is ranged polling, no SSE; package graph declared by
  hand; dense semicolon one-liners (code 6/5); DESIGN.md short (102 lines); dashboard DAG thin (j1).
- Delivered: `minici/` 2,984 py lines (1,985 non-test), 49 tests pass in about 47 s, all 20 scenarios mapped. Main has 32 commits
  (31 by the run). PR.md 79 lines.
- Time: active 34.4 min (result.json; the timeline span is A27.0), wall 118.9 min, capped=null. Tokens: input 18.3M
  (445k uncached), output 118k.

## 2. Phase timeline (active minutes)
| A | Phase | Notes |
|---|---|---|
| 0.0-0.8 | read brief, board setup | a1 creates `tasks` channel (TL:68) |
| 0.8-2.6 | claims + drafts | a1 scheduler-first, a2 execution-first, a3 UX-first; drafts pushed A2.4-2.6 (TL:103-114) |
| 2.6-3.9 | ranking | all three rank a1 first (TL:158,161,181); a1 integrates 5c65e23 |
| 3.6-5.3 | contracts/plan | ownership split a1 store/engine/triggers, a2 pipeline/runner/sample, a3 server/CLI/auth/dashboard/archive (TL:182,192,204); PR.md plan+ledger 84fd0bc (TL:220) |
| 5.3-12.8 | building | engine 00833c1 (A7.8), pipeline fb01b64 (A7.8), runner 9a49d6e (A9.4), API/CLI/archives 98002c1 (A10.8), sample repo a99ffcc (A12.3) |
| 12.8-16.0 | acceptance tests + seam fixes | a1 core scenarios (a973d26), a3 API scenarios (4a9a55b), a2 incremental (14e4ee4); seams: pipeline file name, DELETE /repos, admin bootstrap, upstream cache-key propagation (TL:418,427,477) |
| 16.0-19.3 | docs + selftest | README def0005 (a3), PIPELINE.md e268b00 (a2), DESIGN+selftest fc30141 (a1, A19.0) |
| 18.1 | **perceived time pressure begins** | a3 "~30m left hard cap" (TL:533) |
| 19.3-23.4 | ledger closing, review, browser checks | 39 then 44 tests pass; review finds ready-file, export race, and long-log issues |
| 23.4 | **WALLCLOCK_RUSH** | a1 "~6min" to cap; scope freeze (TL:710) |
| 23.4-25.3 | final fixes | 6350e7c, 18ab1b6, b4f1709 (live-log paging), 46aac16 (browser helper cleanup) |
| 25.3-26.6 | END votes | END b4f1709 (a3, a2), voided by 46aac16; re-vote END 46aac16 by all three (TL:843,865,871) |
| 26.8-27.0 | turn ends | a1 A26.8, a2/a3 A26.9, root A27.0 |

VM freezes (wall jumps with no active time): A5.3->5.8 (23:08->23:20), A11.2->11.9 (23:26->23:58), A17.0->17.3
(00:03->00:29), A22.3->22.7 (00:34->00:57). Together these add about 93 wall minutes and 0 active minutes.

## 3. Per-agent account
- **a1** (scheduler/store/engine/triggers/plugin wrappers, core acceptance 5-12,15,16, DESIGN.md, selftest, PR ledger).
  Won the draft vote. It built the engine with GC (00833c1, cc74d8e, 08c89ad), triggers/schedules/v1 fixture (c91a82a), and later
  schedule/branch/retention tests (18c3695). It was the de facto integrator and timekeeper. It ended at A26.8 after the
  three-way END on 46aac16: "Implemented and pushed to `origin/main` at `46aac16`. All three peers approved that commit."
  (TL:880). Its own push of 46aac16 at A25.2 voided the first END round.
- **a2** (pipeline TOML compiler/validator/cache key, runner + supervisor + redaction, plugins CLI, sample repo,
  PIPELINE.md, incremental tests, Chrome capture helper). It found the upstream-cache seam (TL:418) and the long-log
  dashboard bug (TL:658). It ended at A26.9: "Completed and pushed ... All three peers approved the same final commit; the
  requirements ledger is complete." (TL:886).
- **a3** (security/tokens/audit, HTTP API, CLI, archives, dashboard, test harness `support.py`, README, browsercheck).
  It was blocked briefly waiting for the engine contract ("Awaiting the plan" A5.3, "Awaiting engine contract" A6.1). Late work:
  layered DAG, CLI contract test, ready-file token preservation, export race, and log paging. It ended at A26.9 (TL:887).
- All three ended only after unanimous END on the latest main, with no OPEN/CLAIMED ledger items. No ending was premature
  by C1 rules. The one problem is that the "cap" they were racing was wall-clock (see section 6).

## 4. Coordination costs
- Duplicate work: small. a1 and a3 both planned README/pipeline docs, settled at TL:511/514. a2's capture helper
  and a3's browsercheck overlap (a1 TL:741 "don't add duplicate capture").
- Seams between owners (all fixed on main): `pipeline.toml` vs `minici.toml` (TL:391,427); missing
  `builtin_plugins.drop_trigger` (TL:381); DELETE /repos + admin bootstrap for migrated v1 (TL:427,440); upstream
  cache identity (TL:418 -> 08c89ad A15.5); export of cancelled-but-cleaning runs (TL:661); ready-file token
  overwrite (TL:635).
- Merge conflicts: only PR.md rebases (TL:717 "rebase resolved PR"; TL:823 "PR conflict retained ...").
- Integration loss: none for product code. draft/a2 and draft/a3 were left as branches; the a3 dashboard was carried
  over during integration (A4.1 "Cherry-picking dashboard changes").
- Re-votes: one void-and-revote cycle (a1 pushed 46aac16 after a3's END b4f1709). It cost about 1 active minute.
- Time lost to coordination messages: low. Board posts were dense contract specs.

## 5. Penalty -> cause map
| Penalty | Cause in log |
|---|---|
| cli-only commit fails (path-skipped upstream gives no artifact) | Path-filter design in pipeline.py (`skip_reason='path_filter'`, a2 A7.8 fb01b64). The engine reuses cached artifacts only for jobs that run as cache hits. Tests cover only docs-only and corelib commits (a2 TL:476 "HTTP docs-only/identical/env/matrix pass; corelib cascade"). The case was never raised on the board. Not cut by the rush, but the final review (A19-26) never tried a leaf-package commit. |
| GC wipes cache / size cap removes all runs | a1's engine.gc: unconditional `DELETE FROM cache` plus the comment "Conservative storage cap: remove all eligible histories when over budget" (engine.py:338). This was a deliberate shortcut from the build phase (00833c1 A7.8 "safe retention") and was never revisited. |
| 500 on POST /runs without revision on non-git repo | No visible cause; never discussed. The harness defaults to `revision='working'` (a3 TL:359), so the default path was never tested. |
| slow job never times out in sample run | Deliberate: a2 TL:362 "Slow fixture green default .01s, timeout2s; custom tests override". |
| weak templates | a2 pipeline/sample design; not discussed. |
| no SSE, ranged polling | a3 choice A9.6 ("logs with byte offsets"). The brief allows ranged reads; j1 penalized it anyway. |
| package graph declared by hand | Documented decision in DESIGN.md; not a log event. |
| dense code style / short DESIGN | Style throughout. DESIGN.md was written in about 3 active minutes (A16-19, fc30141) once the team believed time was short. |

None of the judged defects was ever claimed and then dropped. The ledger was closed with every item DONE (TL:741 "no
OPEN/CLAIMED ledger remains"). The penalties come from defects nobody found, not from features that were descoped.

## 6. Decision points
1. **A3.4-3.9 unanimous base choice** (TL:158,161,181): a1's durable scheduler became the base. The clean ownership split
   that followed explains the high coverage and the low conflict cost.
2. **A13.8 upstream cache-key seam** (TL:418): a2 found that unchanged ZIP bytes could hide a corelib change. The
   fix (08c89ad) made scenario 3 pass. No similar probe was made for the inverse case (a leaf-package commit with path-skipped upstream).
3. **A18.1-18.3 first wall-clock read** (TL:526) a3: "Please retain ~20m for final integrated END consensus before hard
   cap". TL:533 a3: "~30m left hard cap; all ledger claims must move DONE/DESCOPED before final votes." The wall clock was
   00:30 Taipei = 87.7 wall min after the 23:02:42 start, but only A18.1 active. a1 repeated it at A19.7 (TL:592): "hard cap
   ~31min remaining". From here the team was in endgame mode (ledger, docs, selftest, END), not building.
4. **A23.4 rush order** (TL:704-710): a3 ran `date -u` -> "Mon Oct 19 16:57:47 UTC 2026" (TL:705). a1 posted: "TIME
   current16:57 UTC; hard cap started15:03 =>17:03 (~6min). a3 please commit current ... and close ledger immediately;
   avoid more scope. a2 capture helper only if can ship within1min otherwise explicitly descoped ... Need common
   latest END votes before17:03." Also TL:728 a2 "hard-cap now only ~5min" and TL:772 a1 "~3min before cap".
5. **A25.3-26.6 END quorum** on 46aac16, and all turns ended by A26.9. At least 85 active minutes of the cap were left unused.

## 7. Failure-mode tags
- **WALLCLOCK_RUSH (1 run-level instance, 6 posts):** TL:526, 533, 592, 710, 728, 772. The peers computed time left from
  board `created_at`/`date -u` wall timestamps. That read included about 93 min of VM freeze, so 115 wall minutes looked
  like the cap when only 23.4 active minutes had passed.
  - Quantification: the run ended at A27.0 (timeline) / 34.4 active (result.json) of a 120-min monotonic cap. At least
    85.6 (by result.json) to 93 (by timeline A) active minutes were left. That is roughly 2.5-3.5 times the work already done.
  - Effects: the build phase effectively stopped at about A18 (9 of 27 active min went to endgame), DESIGN.md was written in
    about 3 min, scope was explicitly frozen at A23.4, and END was rushed.
  - Caveat: the run finished at 118.9 wall min with capped=null. If the cap had been enforced on wall time, the peers'
    estimate would have been correct. The protocol says monotonic, so they treated that as a rush.
  - Nothing concrete was dropped (the a2 capture helper still shipped). The real loss is the review and hardening time
    that never happened, which is where all three severe penalties sit.
- **SELF_REFERENTIAL_VERIFICATION (mild, 1):** the final reviews re-ran the team's own 49 tests and browsercheck (TL:788,
  835, 843) and never tried untested brief cases (leaf-package commit, plain trigger on README sample, slow-job timeout).
- **REVIEW_LOOP (minor, 1):** one END void/re-vote from a1's post-END cleanup commit (TL:823).
- **SCOPE_SHRINK (mild, 1):** a "demo" slow job that never times out in the default run (TL:362).
- Not observed: PREMATURE_END under C1 rules, DUPLICATE_WORK (beyond trivial), INTEGRATION_LOSS, CAP_HIT, PROVIDER_ERROR.

**C1 rule compliance:**
- END votes named full main SHAs. The re-vote after the post-END push was handled correctly. Turns ended only after all
  three ENDed on the latest main (46aac16).
- Parking used short timeouts (a3 `wait_agent 10000ms` TL:826; a1/a2 60000ms TL:846-876), not the "long timeout" the
  prompt asks for. This was harmless here because all peers were active. No peer ended while items were OPEN/CLAIMED.

## 8. Time accounting (active min, estimate from stream; span about 26.5 per peer)
| Agent | Building | Coordination (board, plan, ledger) | Reading/reviewing others | Testing/verification | Idle/waiting |
|---|---|---|---|---|---|
| a1 | ~10 (draft 2.5, engine/triggers/plugins 6, DESIGN/selftest 2) | ~5 | ~2.5 | ~6 (core acceptance + suite reruns + browsercheck) | ~3 (gap A16.0+3.0, END parking) |
| a2 | ~12 (draft 2, pipeline/runner 5, sample 2.5, PIPELINE.md/validator 2.5) | ~3.5 | ~3 (draft ranking, Chrome dashboard review) | ~6 | ~1.5 |
| a3 | ~12.5 (draft 2, auth/API/CLI/archive 7, dashboard DAG/fixes 3.5) | ~3.5 | ~2 | ~5 | ~1.5 (waiting for engine contract A5.3-6.1, END parking) |

All three peers spent the last about 9 active min (A18-27) mostly on endgame activity driven by the perceived 120-min wall
deadline.
