# Contrast: did the C2 "spine + acceptance checks" mechanism operate as designed?

Runs: E1-T2-C2-r1 (7.9) vs E1-T2-base4-r1 (7.8); E1-T3b-C2-r2 (7.4) vs E1-T3b-base4-r3 (7.775).
Per-run evidence: `/workspace/r4/analysis/forensics/runs/<RID>.md`. Same model, effort, peers and cap. Only the
coordination block of the prompt differs: C2 has spine/acceptance/build/cross-check plus a ledger and an END quorum.
base4 has draft/rank/integrate/plan.

## 1. Short answer
Mechanically, yes, in both C2 runs. A spine was claimed within 1 active minute and was on main by A7.6 (T2) and A3.8 (T3b). A ledger
and black-box checks for every ledger item or brief scenario were written before or alongside the spine. The checks were
run against the spine and caught real defects. The END quorum worked cleanly with no re-votes.
**But the mechanism did not change the score.** Score deltas are +0.1 (T2) and -0.375 (T3b), within judge noise.
The T3b penalties trace to two blind spots the mechanism has by construction (sections 4-5), plus a wall-clock rush
that hit both arms.

## 2. Mechanism checklist
| Step (C2 prompt) | T2-C2-r1 | T3b-C2-r2 |
|---|---|---|
| SPINE claimed first | a2 A0.6. a1 double-claimed 9 s later and retracted A0.9 | a1 A0.8 |
| Spine owner publishes contract | module contract A1.2, state schema A2.7, mutation payloads A3.0 | API contract FACT A0.9, before any code |
| Spine on main | `9e031d8` A7.6, 13 files/416 lines; covers CLI/UI/SQLite/rules/generate/requests/swaps/publish/ICS/CSV | `a6e28b0` A3.8, 16 files/578 lines (engine/store/server/CLI/dashboard) |
| Others write no product code while waiting | Held. a1/a3 commits A1.9-7.4 are tests/fixtures/PR.md only, verified by `--stat`. Both parked (a3 A5.7 "per instruction parking now") | Held. a2/a3 commits A2.6-4.3 are tests and PR.md only |
| Ledger | R01-R17 by a1 A1.9 (before spine) | 38 lines by a2 A3.3 |
| Ledger kept current while building | No. "ledger all still CLAIMED though a1/a3 completion evidence posted" (a1 A23.1). Closed A25.7 with item-specific evidence | No. "All ledger status still OPEN locally" (a1 A15.1). Closed A18.5 under the rush, with one identical boilerplate verification line on every item |
| Checks written "from the brief alone" | Partly. Content from the brief (oracle recomputes rest/hours/coverage independently, a1 A3.4), but shaped by the spine's published API | Partly. Scenario list copied from the brief's 20 numbered scenarios; endpoints from a1's contract. Assertion strength set by the writer (see 4a) |
| One command | `python3 -m unittest discover -s tests` | `python3.12 -m minici.selftest` |
| Checks run against spine | A8.1-8.5, by all three | A8.7-10.2 |
| Caught real product defects | Yes: cross-month rest/weekly caps absent, generate/check never fail on infeasible input, wrong-role preview (a2 A8.1, a1 A8.5). Fixed by a1 `5e844a1` A11.3 | Yes: validator variable shadowing broke scenarios 04/12/16 (a1 A8.7-9.2); /repos `path` vs `repo` mismatch (a1 A9.9); plugin step validator (a3 A13.5) |
| Check bugs fixed in the open | a3 A8.1 "two checks need legitimate adapter fixes" | Scenario 13 marker (`***` vs `[REDACTED]`, A10.1-11.4). Scenario 03 fixture rewritten by the builder a1 (A13.1) |
| Cross-check before END | Yes, and productive: per-site staffing accepted but ignored (a1 A14.2); a draft October edit could break a published November (a1 A17.6-17.9); date overflow (A19.0) | Yes: notifier orphans (A13.9), GC-vs-cancel race (A14.5), secret rotation race (A17.0), invalid git rev (A17.6) |
| END quorum | `END a6e3558` x3, A25.9-27.2 | `END f1951ea` x3, A19.3-19.8 |

## 3. What concretely differed from base4 (same task)
- **Time to a runnable whole.** C2 had an end-to-end app on main at A7.6 (T2) and A3.8 (T3b). In base4 the drafts were throwaway (21-97 lines); the production pieces arrived separately.
  - T2: domain at A11.2, API at A10.4, and the UI only at A20.6. Peers chased it: "main currently lacks clinic/static entirely" (a3 A18.4).
  - T3b: engine at A10.5, API at A14.8, and the interface mismatches (list_repos/register_repo, autocommit import) were found only at A15.2-15.6.
  - The spine moved integration seams about 7-10 active min earlier.
- **When the tests existed.** In C2, all scenario checks existed before product code (T3b: all 20 by A4.3). In base4 they arrived after building: T3b a2 harness A13.5, scenarios A20.2; T2 tests A14.0-14.7. In base4, the serious defects were found by reading code (autocommit import, JSON-byte redaction leak: T3b A15.6, A18.0) and by running the real README quickstart (nested-repo snapshot bug, T3b A32.4). No C2 check targets that class of defect.
- **Overhead.** The C2 runs used less active time (T2 35.0 vs 40.6; T3b 28.0 vs 46.4) and fewer tokens (T2 16.3M vs 18.1M; T3b 12.7M vs 19.6M). There was no draft/rank phase, no prototype remnants (both base4 runs shipped draft leftovers: `prototypes/a1` and `minici/draft-pipeline.json`, penalised by judges), and no duplicate fixes. Parked time for checkers waiting on the spine was small (about 2 min in T2, ~0 in T3b).
- **Base4 decided the sample to satisfy the brief, C2 checked it loosely.** T3b-base4 a2 split cache `inputs` from `paths`: "This resolves acceptance 2 vs 3" (A9.5). Its test 03 asserts `toolchain == 'cache_hit'` and identical artifacts on the shipped sample. In T3b-C2, a2's first check (A3.3) asserted `status in {'skipped','cached'}` for docs. That exact loophole is j2's coverage penalty: "docs is reported `skipped` ... Test 03 passes by accepting either status."

## 4. Why the mechanism did not raise the score: three blind spots seen in the logs
a. **A check is only as strict as its first draft, and nobody audits check strength.** The checks were written in 1-3 active minutes each (T3b: 20 scenarios in A2.6-4.3). Later they were only ever loosened or adapted when they failed: the 03 fixture was rewritten by the builder of the code under test, and the 13 marker was changed toward the implementation first. They were never tightened when they passed (03's either-status, the 8-pair race test). The prompt says "fix the check in the open" but gives no step to review whether a passing check actually encodes the brief.

b. **Synthetic fixtures replace the shipped artifact.** The prompt asks for "fixtures for each state". Both C2 runs complied: T2 had 7 capture states; T3b had per-test temp repos for locks, parallelism, templates and timeouts. So no check looked at the demo or sample the judge actually runs.
   - T2-C2: "demo seed has no requests or swaps" (both judges). In base4 T2, a1 reviewed the seed as a user would (A18.0) and judges praised the data.
   - T3b-C2: sample has "one lock, so ... no jobs in parallel", identical matrix cells, slow job in a separate file, and unused templates. All of this came from one a2 commit (A9.4) that no check or ledger item ever touched.

c. **The ledger became a stamp, not a tracker.** Statuses stayed OPEN/CLAIMED until the final minutes in both runs. In T3b all 38 items were set DONE in one commit with the same justification ("Verified by `python3.12 -m minici.selftest` (51 passing tests)"). So the END quorum certified "our tests pass", the SELF_REFERENTIAL_VERIFICATION pattern, rather than "the brief is met".

The spine also froze the architecture early: T3b's JSON-blob store with full scans (penalised by both judges) is the spine's A3.8 storage, never revisited.

## 5. Confound affecting both arms: wall-clock rush
In three of the four runs, agents ran `date` and compared it to a wall-clock start, while the cap is monotonic.
`wall_min` 145.5 with `capped: null` in T3b-base4 proves wall time does not count.
- T3b-C2: "TIME: current22:05UTC, task began20:12, hardcap~22:12. Need finish within7min" (a1 A18.1). The team closed the ledger and voted END within 1.7 active minutes; the run ended at A21 span / 28 active, with about 90 active minutes unused. This is the largest single cause of T3b-C2's lower score: the blind spots in section 4 had no time to be noticed.
- T3b-base4: "120m cap ~05:17" (a2 A29.3); "Clock now shows 05:35 > cap" (a1 A34.5). a1 ended without a green final run.
- T2-base4: "~33min left" (a1 A18.2), "~18min to cap" (A23.5).
- T2-C2 showed no rush. It ended on its own merits at A27.9 span.

## 6. Which mechanism would have changed the outcome, and predicted log signatures
1. **Monotonic time budget exposed to agents** (e.g. `MURMUR_ACTIVE_MIN` / remaining-active-minutes tool, prompt line "wall clock is not the cap").
   Signature: no `date -u` calls followed by "cap ~HH:MM" posts. T3b-C2 continues past A21 into a second build/review round. More commits after the first all-green suite. Active time closer to T3b-base4's 46.
2. **Check-strength review step** (for each check, a peer who did not write it quotes the brief sentence and states what weaker behaviour would still pass).
   Signature: posts like "FAIL check 03 accepts skipped; brief says cache hit"; commits that tighten assertions (`assertEqual(... 'cached')`); a corresponding product commit adding `inputs` to the sample. Expected effect on T3b-C2: the j2 coverage penalty disappears.
3. **"Shipped-artifact" acceptance item** (one ledger line per demo/sample: the seed and sample must exhibit every brief feature as the user meets it: README quickstart, seeded requests and swaps, parallel jobs, a slow job that times out in the main pipeline).
   Signature: a check that runs README commands verbatim against the checked-in sample or seed (the class of check that found T3b-base4's nested-repo bug at A32.4). Seed and sample commits after A10. The demo-data and sample-realism penalties fall away.
4. **Ledger status changes tied to check names** (DONE must cite the specific test ids, not the whole suite).
   Signature: per-item ledger diffs spread across the run instead of one bulk commit in the last two minutes; blanket "selftest passes" lines disappear.

## 7. Bottom line
The C2 spine worked as designed in both runs. It produced an integrated product earlier and more cheaply than base4: fewer active minutes, fewer tokens, no draft debris. Its acceptance checks caught real spine defects in both runs. The checks did not lift quality, for three reasons visible in the logs:
- they were only as strict as their hasty first draft;
- they tested synthetic fixtures rather than the shipped sample or seed;
- the ledger they fed was rubber-stamped at the end.

In T3b a wall-clock misreading also cut the run short at about 21 active min. Fix the time signal first, then add check-strength review and shipped-artifact checks.
