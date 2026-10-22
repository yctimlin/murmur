# E1-T3b-C2-r1 (T3b self-hosted CI platform, arm C2, score 7.55)

## 1. Outcome
- Score 7.55 (j1 7.6 "guess single", j2 7.5 "guess team"). Sub-scores both judges: coverage 8, correctness 8, design 7,
  robustness 8, code 6/5, ux 7.
- Top penalties (quoted):
  - j1 severe: "Acceptance command intermittently fails: test_watcher_new_deleted_branch_and_current_schedule races
    (refs saved after audit event)"; selftest "passed 63 of 64".
  - Both: "code is extremely dense, with many statements per line joined by semicolons" (code 6/5).
  - Both: "The cache key includes the daemon's whole `os.environ`. That over-invalidates".
  - j1: "Log streaming is offset polling only, not SSE"; "sample pipeline's 'slow' job never times out; the failing
    variant lives in a separate `.minici.slow.json`"; "In the corelib-change run, unrelated jobs show as 'skipped' by
    the path filter, not as cache hits"; "cycle error is masked when the file also has an unknown dependency";
    "API responses expose absolute artifact paths"; concurrent cancel/re-run "repeats only 5 times".
  - j2: "README links to a `PR.md` that doesn't exist"; "Only two roles"; "v1->v2 migration is thin" (j1).
- Delivered (main 270f07a): minici product Python 1,589 lines / 95 KB (avg ~60 chars/line), tests ~1,520 lines in 12
  files (64 tests), dashboard JS/HTML/CSS 36 lines / 17.9 KB, sample-repo 203 Python lines, README 198, DESIGN 112,
  PR.md 70, PIPELINE.md, PLUGINS.md. 31 commits, all on main; no other branches.
- Active 28.1 min run span (result.json active_min 36.76 incl. setup), wall 97.7 min (three VM freezes: A2.3->A2.8
  = 07:08->07:37, A12.9->A13.5 = 07:49->08:01, A22.9->A23.5 = 08:13->08:39). Tokens: input 17.3M (uncached 762k),
  output 149k. Not capped; run_exit 0. Used ~23% of the 120-min cap.

## 2. Phase timeline (active minutes)
| Phase | A range | What happened |
|---|---|---|
| Read brief + claims | 0.1-1.8 | a1 "CLAIM SPINE a1 ... within ~12 minutes" (A0.9, TL:68). a2 and a3 both claim overlapping acceptance sets; flip-flop resolved by A1.7: a2=13-20+ledger, a3=1-12+harness (TL:120). |
| Contract | 2.1 | a1 posts "CONTRACT v1 for tests: serve --data DIR --port 0 --token TOKEN ... POST /api/v1/runs ..." (TL:127) before writing spine code. |
| Acceptance (parallel to spine) | 2.3-5.4 | a3 harness d2acc45 (A3.0), scenarios 1-12 32b45a7 (A4.1), selftest entrypoint 9954574 (A5.1). a2 ledger 721efd2 "33 ... rows" (A3.3), scenarios 13-18,20 0785825 (A4.5), pipeline checks ef3119e (A5.4). No product code by a2/a3. |
| Spine | 1.6-5.8 | a1 0afc3cc "Build end-to-end offline CI platform spine" (11 files, 665 lines; store/server/engine/runner/pipeline/CLI/dashboard stubs) A5.6; "SPINE DONE 0afc3cc ... a1 owns engine.py runner.py __main__.py README.md DESIGN.md ... a2 owns pipeline.py sample-repo ... a3 owns store.py server.py dashboard..." A5.8 (TL:245). ~4.2 min, well under the 12-min budget. |
| Build | 6.1-15.1 | a1 engine/cache/CLI (4a1d377 A8.3, 52823cf A11.3); a3 triggers/plugins/retention/archives 269a14b (A9.8), dashboard 481da37 (A12.1), plugins+API 4480e1f (A15.0); a2 parser ca94949 (A10.0), real invoice sample 72439b3 (A12.3), change detection f6a04f0 (A15.1). a1 "DONE 4a1d377 execution scenarios 2-8,10-12 pass" A9.4. |
| Cross-check / seam fixing | 12.9-20.1 | a3 finds missing job-cancel route (A12.9); a2 "CROSS-CHECK findings: ... transitive skip ... " (A13.6), env/timeout seam (A13.8), GC lease seam (A15.6), watcher stale-artifact FAIL test 18cbbd9 (A17.7), snapshot/spec-secret seams (A18.1, A19.2); a3 runner stdin hang (A17.9), audit atomicity (A19.2). Fixes 6db5a72, 7d11814, 01f3cbe, ebbc0af. |
| Docs + hardening | 17.1-24.1 | a1 README/DESIGN + hardening 60c6864 (A22.1), regressions 1213a48 (A23.8), 81332cf (A24.1); a2 PIPELINE.md 23b15c9 (A22.3); a3 captures 21d71d6, 396ef45 (A22.9). Full-suite passes: a3 56 tests A20.3, a2 57 tests A22.5. |
| Finalization + END | 24.1-27.9 | Wall-clock cap talk (A24.1, A24.5); a3 "CROSS-CHECK PASS 81332cf ... 64 tests" A25.4; ledger evidence 72e888f (a1 A25.6), 270f07a (a2 A26.4) "FINAL CANDIDATE" A26.5. END 270f07a: a2 A26.7, a3 A27.0, a1 A27.5. TURN_END a3/a1 A27.7, a2 A27.9, root A28.1. |

## 3. Per-agent account
- **a1 (spine, engine/runner/cache/CLI/docs)**: 13 commits. Built spine alone (A1.6-5.6), then engine hardening,
  full CLI, README/DESIGN (single long generation A17.1-21.5, the header's "A16.9+4.2" gap is this, not idle),
  regressions. Fixed seams reported by a2/a3. Ran `date -u` in a shell (rollout: "Tue Oct 20 00:11:48 UTC 2026").
  TURN_END A27.7: "Completed on `origin/main` at `270f07a`. All 64 tests pass ... All three peers approved the same
  final commit." Reason: END quorum observed ("a2/a3 already END same commit; consensus complete", A27.5, TL:855).
- **a2 (ledger, acceptance 13-20, parser, sample-repo, cross-checker)**: 10 commits, most lines added (1,627).
  Wrote ledger and black-box checks, then parser + invoice sample; from A12.4 mainly cross-checking other owners'
  code and writing regression tests against them (CLI live test a9a5d3b, watcher regression 18cbbd9). Posted the
  FINAL CANDIDATE and the first END. TURN_END A27.9: "done", after `list_agents` showed peers finishing.
- **a3 (harness, acceptance 1-12, store/server/plugins/archive/GC/dashboard, browser tests)**: 8 commits. Built the
  shared test harness, the control plane and a stdlib Chrome CDP browser test + 18-state capture script. Parked with
  `wait_agent` 60 s twice before SPINE DONE (A5.3, A5.8) and three times during finalization (A25.6-27.2).
  TURN_END A27.7: "All three peers approved completion. All 64 tests pass".
- **root**: spawned, waited (A0.5 + 27.3 min), "done" at A28.1.

## 4. Coordination costs
- Claim overlap at start: a2 and a3 both claimed 13-19; three contradictory re-splits in 0.6 min (TL:98, 101, 106,
  120). Cost ~0.5 min each, no duplicated code.
- Contract churn on checks: 400 vs 422 for validation (a3 changed server to 400 to fit test18, a2 changed test to 422
  A9.4, a3 "accepted will restore 422" A9.6); attempts integer vs list (a1 changed test05, A6.2); artifact input
  path vs env var (a3 1643b6d A4.5); test03 given `inputs:['independent/**']` (a1/a3 A4.7-6.2). All done in the
  open as the prompt asked.
- Ledger hygiene lag: rows stayed OPEN after implementation; reminders at A18.8 (a3) and A20.1 (a2) "ledger currently
  mostly OPEN despite passing implementation"; finally closed A25.6/A26.4.
- No merge conflicts or rebase failures visible, no work stranded on branches, no ignored messages found, one END
  round (no re-votes). Strict file ownership (SPINE DONE post) kept the three peers out of each other's files.

## 5. Penalty -> cause map
- **Flaky watcher test (j1 severe)**: test and code by a3 (4480e1f A15.0; R10 "DONE 01f3cbe —
  test_watcher_new_deleted_branch_and_current_schedule"). The test polls the audit log for `branch_deleted`, then
  reads `_refs`, which plugins.py saves after the audit event. Every suite run in the log passed (a3 A20.3, a2 A22.5,
  a3 A25.4, a1 A25.6), so the race was never seen. Nobody ran the suite repeatedly or under load; the final checks
  were one pass per peer.
- **Dense semicolon code (code 6/5)**: present from the spine. 0afc3cc engine.py was 186 lines / 12 KB with 25
  semicolons, written in single heredocs. Peers kept the style, and no cross-check commented on readability (the
  review posts are all about behaviour seams).
- **Cache key hashes whole os.environ**: caused by a cross-check. a2 A13.8: "cache key hashes inherited os.environ
  only via explicit job.env; known staleness hole document inherited host env (PATH etc)". a1 chose to hash it
  instead of documenting it: "now hashes inherited environment ... to avoid stale host env" (6db5a72, A15.4,
  TL:485). This is a correctness-motivated overcorrection.
- **Unrelated jobs "skipped" rather than cache hits on a corelib change**: scenario 3 checks were rewritten for a
  miniature repo with an explicit `inputs` job (a3 A4.7, a1 A6.2 "test03 constant independent job needs
  inputs:['independent/**']"). a1 asked a2 at A13.6 to "add actual sample docs-only and corelib-cascade test", but
  a2's next commit (f6a04f0) covered merge/force-push semantics, not the sample cascade. Nobody re-raised it. In the
  real sample, path filters skip unrelated jobs.
- **Slow job not timing out in main pipeline**: a2's sample design: "bounded slow example" (A11.2); timeout demo
  moved to `.minici.slow.json`. Never questioned in review.
- **Offset polling, not SSE**: decided in a1 CONTRACT v1 (A2.1). The brief allows ranged reads; ledger R22 "offset
  log resume" DONE.
- **Concurrent cancel/rerun x5**: a3's acceptance test (32b45a7 A4.1, `for _ in range(5)`), written before the spine
  and never strengthened.
- **"PR.md doesn't exist" (j2)**: PR.md is present in delivered/ (70 lines). No visible cause in the log; this looks
  like an artifact of how the judges' tree was set up.
- **Cycle masked by unknown dep, absolute paths in API, thin migration, two roles**: no visible cause. None was
  flagged in any cross-check post.

## 6. Decision points
1. **A0.9-A2.1 spine claim + early contract.** "CLAIM SPINE a1" (A0.9), then "CONTRACT v1 for tests" (A2.1). The
   acceptance writers got a concrete black-box API within 2 min. That made independent checks feasible and is why
   the 20 scenarios existed as runnable tests by A5.4, before any product beyond the spine.
2. **A5.8 SPINE DONE with a file-ownership split.** This post fixed one owner per module for the rest of the run:
   zero conflicts, and parallel building from A6.1. Deviation from the protocol: the plan section of PR.md was not
   written with the spine. a2 wrote the ledger (A3.3) and a1 added the plan only at A13.6 (5efa4ac "Record shared
   implementation plan").
3. **A12.4-A19.6 the cross-check phase.** a2 switched from building to reviewing others' seams and turned findings
   into failing tests (e.g. "FAIL confirmed watcher stale artifact regression", A17.7). This caught real bugs:
   missing job-cancel route, transitive skip, GC lease, multi-step timeout, spec-file secrets in artifacts, stdin
   hang. It also produced the os.environ overcorrection (A13.8 -> A15.4).
4. **A24.1-A24.5 wall-clock cap reasoning.** a1: "Hardcap ~26min remains (actual clock 00:40UTC). Please finish
   outstanding owned work" (TL:718). a2: "post candidate freeze commit; hard cap remaining about27min per board
   timestamps" (TL:742). This came at A24 active, so about 96 active min actually remained. It switched the team
   into freeze/END mode.
5. **A26.5-A27.5 END quorum.** a2 "FINAL CANDIDATE" -> "END 270f07a" (A26.7); a3 END (A27.0); a1 END (A27.5, after
   generating 18 captures). All three voted on the same commit in one round, with no voiding push, and all three
   turns ended within 0.2 min.

**Spine/acceptance assessment.** Both happened as intended and on time. The spine was thin, wired end to end and
done in ~4 min. The acceptance checks were black-box (real server process via HTTP) and were written before product
code, from the brief plus a1's API contract. They were run and adjusted in the open. What they changed:
- Every scenario had an owner and a test from A5.4.
- "DONE" claims were backed by passing checks (a1 A9.4; a3 A10.3 "PASS real server scenarios 13,14,15,16,17,20").
- Seams surfaced quickly.

Their limits:
- Several checks were bent toward the implementation (test03 `inputs`, test05, test18).
- Scenario 3 was verified on a miniature repo, not the real sample.
- Checks were run once each, so the flake survived.
- The checks measure behaviour only, so code readability (the largest sub-score loss) was outside their scope.

## 7. Failure-mode tags
- **WALLCLOCK_RUSH (2 agents, contributing)**:
  - a3 A4.9: "120-minute cap began ~23:07 UTC, current board ~23:39", meaning it believed 32 min were used at A4.9.
  - a1 A24.1: "Hardcap ~26min remains".
  - a2 A24.5: "hard cap remaining about27min per board timestamps".
  - Effect: the team moved straight to freeze/END and spent no time on repeat runs or on the known-thin areas. The
    run ended at A28 of 120.
- **SINGLE_RUN_VERIFICATION (new; definition: completion is certified by one pass per peer of a suite that
  contains timing-dependent tests, with no repetition or stress) (1)**: four single passes A20.3-A25.6. The watcher
  race passed every time and then failed for j1.
- **SELF_REFERENTIAL_VERIFICATION (mild, 1)**: scenario 3 was satisfied by a constructed repo with explicit
  `inputs`, while the real sample's corelib run shows skips, not cache hits. Ledger rows were marked DONE by test
  name, not by trying the brief's scenario on the sample.
- **CROSSCHECK_OVERCORRECTION (new; definition: a review finding is "fixed" by a design change that a judge
  penalises, where documenting the limitation was the cheaper and better answer) (1)**: os.environ in the cache key
  (A13.8 -> A15.4).
- **EARLY_CONSENSUS (new; definition: the END quorum is reached with most of the budget unused because the ledger
  reads all DONE, while known quality gaps such as code density, thin migration or the 5x concurrency test remain)
  (1)**: END at A27.5 of 120. This overlaps with PREMATURE_END but no ledger item was open.
- PREMATURE_END: not strictly, since every ledger row was DONE. DUPLICATE_WORK: none, only overlapping claims for
  about 1 min. INTEGRATION_LOSS, MERGE_CONFLICT, REVIEW_LOOP, CAP_HIT, PROVIDER_ERROR: none. IDLE_PEER: minimal
  (a3 ~0.6 min pre-spine, ~1.5 min at the end).

## 8. Time accounting (estimated active min, span ~27.5 each)
| Agent | Building product | Writing checks/tests | Coordination (board, claims, ledger) | Reading/cross-checking others | Running tests | Idle/wait |
|---|---|---|---|---|---|---|
| a1 | ~15 (spine 4, engine/CLI 6, docs 4.5) | ~2.5 (unit + regressions) | ~2.5 | ~1.5 | ~4 | ~0.5 (END wait) |
| a2 | ~8 (parser, sample, PIPELINE.md) | ~5 (ledger-linked 13-20, pipeline, CLI, watcher regressions) | ~3 (ledger, evidence) | ~7 (seam reviews, visual review) | ~3.5 | ~1 |
| a3 | ~11 (store/server/plugins/archive/dashboard, fixes) | ~6 (harness, 1-12, platform, browser/CDP, captures) | ~2 | ~3 | ~3 | ~2 (wait_agent x5) |
| root | 0 | 0 | 0.5 | 0 | 0 | 27.5 |
