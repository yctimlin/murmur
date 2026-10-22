# E1-T3b-C1-r3 (arm C1, task T3b self-hosted CI platform), score 7.55

Sources: timeline `timelines/E1-T3b-C1-r3.md` (TL = line no.), judges `judge/E1/E1-T3b-C1-r3.j1.md/.j2.md`,
prompts `lab/ws/E1-T3b-C1-r3/prompts/a{1,2,3}.md` (C1 prompt: drafts, ranking, ledger, END quorum, "Hard cap: 120m"),
`origin.git` log, delivered tree, raw rollouts (a3's rollout used to check its clock source).

## 1. Outcome
- Score 7.55 (j1 7.6, j2 7.5). Subscores: coverage 8/8, correctness 8/8, design 7/7, robustness 8/8, **code 6/5**, ux 7/7. Both judges guessed "team".
- Top penalties (quotes):
  - j1: "The code is written in a dense one-liner style with semicolons". j2: "extremely dense: semicolon-chained one-liners and a single-line minified `dashboard.js`".
  - "Pipeline templates are barely used: every package job overrides `steps`" (j1). j2 says the same.
  - "The dashboard's 'DAG' is a grid of job cards ... not a drawn graph. Its run filters work only on the client side" (j1).
  - "Log streaming is offset polling ... not SSE" (j1, j2).
  - "The package dependency graph is just hand-written `needs`" (j1, j2).
  - j2 severe: "a manual trigger with `commit: "HEAD"` stores the literal "HEAD"". Also "the unknown dependency was not reported when a duplicate job name was also present".
  - "DESIGN.md cites `PR.md` ... that file does not exist" (j1, j2).
- Delivered on main `d12b36f`: 56 files. About 3,300 lines of py/js/html: about 2,090 product (engine.py 435 lines/30.6 KB, dashboard.js 15 lines/6 KB), 1,005 test, 209 sample-repo. 58 tests pass in about 31 s. 29 commits.
- Active time: 32.0 min run span (result.json `active_min` 39.02). Wall time 113.5 min. Input tokens 21.1M (412k uncached), output 132k. No cap hit (`capped: null`). All 3 peers ended on an END quorum.

## 2. Phase timeline (active minutes)
| Phase | A range | What happened |
|---|---|---|
| Read brief, claim draft directions | 0.3-1.2 | a1 "durable-executor" (TL:70), a2 "trust-first inspectable execution ledger" (TL:79), a3 "team-console-first" (TL:90). |
| Drafts | 1.0-2.8 | a2 draft 5390977 at A1.4 (77 lines, ~25 s of work, TL:96). a1 draft 7afcf40 at A2.4 (201 lines). a3 draft 7d5f223 at A2.8. All drafts were far shorter than the suggested 12 min. |
| Interface contracts (overlaps drafts) | 1.7-4.7 | a2 proposed the ownership split and pipeline JSON contract (TL:104,108). a1 proposed the Engine API and DB schema (TL:150,170). a3 proposed the auth tables and API plan (TL:207,212). |
| Ranking | 4.0-4.3 | All three ranked a1 first (TL:189,196,200). a1 posted "DONE chosen draft integrated on origin/main commit 7afcf40" (TL:201). |
| Plan + ledger | 5.0 | a1 pushed PR.md with the plan and a `## Requirements` ledger (d6dbf64, TL:216). |
| Parallel build | 5.0-12.5 | a1 store/migrations/supervisor/engine (f5376fc, 4711e9f). a2 pipeline/validator, sample repo, triggers (7972722, 60d80c0, be2ebb4). a3 API/CLI/auth/archive, fixture, UI (4d6c6c0, 1b3650c, db8fa12). |
| Acceptance tests over HTTP | 10.9-16.9 | a1 split the 20 scenarios at A10.9 (TL:310). Tests landed: a1 69c5c30, a3 c32839e, a2 4312c3c. |
| Wall-clock-driven switch to review | 17.0-18.2 | a3: "Have 40min left on 120min cap. Need accelerate final ledger/whole suite review" (TL:455). a1: "~40min remaining hard cap" (TL:489). |
| Seam review, fixes, docs | 17.5-25.0 | Fixes: selection seam (5eaa7ac), imported-rerun guard (24b1fbf), finite numbers (54d8b4f, 455eb5f), artifact labels (e462b53), interpreter pin (9acc208), UTF-8 log pages (adbb6b2). Docs: DESIGN/README. Browser review by a2 and a3 through CDP. |
| END round 1 | 26.3-26.5 | a2 and a3 posted END adbb6b2 (TL:787,794). The round was voided by a1's push of 33c0435 at A28.4 (TL:833). |
| END round 2 | 29.2-30.4 | END 33c0435 from a1, a3, a2 (TL:869,907,908). |
| Docs-only closure + END round 3 | 30.9-31.3 | a1 pushed d12b36f to record the verification (TL:937). Then three END d12b36f posts (TL:955,957,963). |
| Turn ends | 31.6-32.0 | a2 and a3 at A31.6, a1 at A31.8, root at A32.0. |

## 3. Per-agent account
**a1** (durable engine, store, supervisor, GC, plugins, DESIGN.md; 9 commits incl. draft)
- Its draft won unanimously. Owned the hardest core: f5376fc, 4711e9f (391-line engine), 29863d5, 69c5c30 (10 HTTP scenarios), 59f3dba (DESIGN + retention), 24b1fbf, 7b2eee4, 33c0435.
- Edited the engine with `python3.12 - <<PY s.replace(...)` patches on single dense lines (e.g. TL:347). This is the likely origin of the one-liner style the judges penalized.
- Acted as closer: proposed the scenario split (TL:310), cleanup (TL:620), "Please avoid more scope expansion; finish only discovered defects" (TL:685), "Hard cap ~8min left; no new features" (TL:915).
- TURN_END A31.8 (TL:991): "Completed and pushed to `origin/main` at `d12b36f`. All 58 offline tests pass ... All three peers reviewed and approved the final commit." It ended right after posting CONSENSUS (TL:983).

**a2** (pipeline/validator/cache keys, sample repo, triggers/schedules, incremental tests, PIPELINES/TRIGGERS docs; 8 commits)
- Its draft was a 25-second stub. It spent the draft window proposing the split and the format (TL:104,108), so its contracts anchored the team's division of work.
- Built 7972722 (501 lines), 60d80c0, be2ebb4, 4312c3c. Fixes: 5eaa7ac, 54d8b4f, 9acc208. Also the duplicate CLI test 8ddd5ef.
- TURN_END A31.6 (TL:978): "All three peers reviewed and approved the final commit; no open requirements remain."

**a3** (HTTP API, auth, CLI, archives, dashboard, test fixture, README; 11 commits)
- Built 4d6c6c0 (682 lines), 1b3650c, db8fa12, 905fb58, c32839e, 3ba630f, 34ab001, 455eb5f, e462b53, adbb6b2.
- Did the strongest seam review: imported-rerun bug (TL:469), test discovery gap (TL:455), UTF-8 pagination (TL:727). Also ran a headless-Chrome check at 1440 and 390 px (TL:539).
- First to reason from wall time: it ran `date -u` 9 times in its rollout, and the board's `created_at` timestamps are UTC wall time.
- TURN_END A31.6 (TL:984): "All three peers confirmed final review; the requirements ledger is complete."

**root**: spawned the peers, then `wait_agent` from A0.5 to A31.7 and "done" at A32.0. Normal behaviour.

## 4. Coordination costs
- **Duplicate work**: two CLI operator-workflow tests. a2 announced its test at A19.2 (TL:526) and pushed 8ddd5ef at A19.8. a3 pushed 34ab001 at A20.0 and only then noticed: "a2 overlap: I just added test_cli_operator_workflow" (TL:553). Both tests stayed (`tests/test_cli.py` and `tests/test_api.py`). Cost about 1 agent-min.
- **Conflicts/rebases**: PR.md ledger conflicts (a3 "Resolving ledger conflict" A21.4, a1 "Resolving PR conflict" A23.2). One rejected push: "Final integration push raced a3 artifact-label fix" (TL:685). The cost was small.
- **Integration loss**: none of value. draft/a2 and draft/a3 stayed on branches by design; their ideas are credited in PR.md. Everything built after the drafts reached main.
- **Re-votes**: 3 END rounds, 8 END posts. Round 1 was voided by a late test-strengthening commit (33c0435). Round 3 existed only because the closing ledger commit d12b36f was pushed after the code votes. Cost about 3-4 active min. This is mild because the votes were fast.
- **Schema churn**: a3 proposed auth tables, a1 replaced them, then a1 accepted a3's version ("replacing my earlier users/tokens shape", TL:245). Cost about 1 min.
- **Ignored messages**: none observed. Every BUG and FIX post was answered within about 1-2 active min.

## 5. Penalty -> cause map
- **Dense one-liner code / minified dashboard.js** (code 6/5). Cause: the authors' editing style, not a coordination event. a1 built engine.py through heredoc `s.replace` patches; a3 wrote dashboard.js as 15 lines. No reviewer raised readability; all reviews checked behaviour. Perceived time pressure (A17 onward) removed any slack for a refactor pass. Never in the ledger, because the ledger has no maintainability line.
- **Templates barely used**: the ledger marks "templates" DONE on 4312c3c, verified by "21 tests" (PR.md:14). Verification checked that templates parse, not that the sample pipeline meaningfully reuses them. a2 built the sample (60d80c0) in about 2 min (A7.1-8.8). Tag: SELF_REFERENTIAL_VERIFICATION (mild).
- **DAG as card grid / client-side filters**: the ledger line "responsive dashboard run filters, DAG/live states..." is DONE on 34ab001 (PR.md:33). The browser review checked only "11 jobs, no overflow/errors" (TL:539,636). The brief's "DAG view" was accepted as satisfied by cards. Mild SCOPE_SHRINK by acceptance.
- **Offset polling instead of SSE**: a3's API plan already said "resumable log reads" (TL:303). The brief allows "SSE ... or ranged reads", so this was a legitimate choice that judges still marked down. Never debated on the board.
- **Hand-written `needs` graph**: a2's contract (TL:104) chose declared deps. The brief allows this ("declared, discovered ... or both"). No visible discussion of inferring the graph.
- **`commit: "HEAD"` stored unresolved**: engine.trigger (a1, 4711e9f). No test triggers with a symbolic ref, so the bug was not visible in the log and never claimed as a seam.
- **Unknown-dependency error dropped next to a duplicate name**: pipeline.py (a2, 7972722). The `by_name` dict collapses duplicates before the needs check. a2's "type-mutation fuzz" (TL:566) did not combine errors. Not visible in the log.
- **"PR.md does not exist"**: PR.md *is* on main and in `delivered/`. The judge copy likely stripped PR.md for blinding, so this is a harness artifact. No run-side cause.

## 6. Decision points
1. **A1.7-4.3, contracts before ranking.** a2 posted an ownership split and format contract right after its 25-second draft (TL:104,108). Everyone agreed, and all ranked a1's executor draft first (TL:189-200). Effect: there was no real exploration of alternatives. The split was clean and conflict-free and drove the strong coverage.
2. **A5.0, PR.md plan + ledger by a1 (TL:216).** The ledger had about 30 coarse lines that later got blanket "DONE 24b1fbf (... 50-test suite)" receipts (PR.md:13-43). This made closing easy but the checks shallow.
3. **A17.0-18.2, the team decides time is running out.** a3: "Have 40min left on 120min cap" (TL:455). a1: "~40min remaining hard cap" (TL:489). Real active elapsed was 17-18 of 120 min. VM freezes (08:45->09:10, 09:16->09:35, 09:39->10:01) had moved wall time by about 80 min. From here the team was only in review-and-close mode.
4. **A23.6, a1: "Please avoid more scope expansion; finish only discovered defects" (TL:685).** This locked the feature set. The thin items (templates, SSE, graphical DAG, code density) were never reopened.
5. **A28.6-30.4, "~10m remains" (a2 TL:838: "Hard cap from ~00:43 start is ~02:43"; a3 TL:843; a1 TL:915 "Hard cap ~8min left; no new features").** This drove the quick END rounds. The run ended at A31.8 with about 88 active minutes of budget unused.

## 7. Failure-mode tags
- **WALLCLOCK_RUSH (strong, 6 posts)**: TL:455, 489, 685, 838, 843, 915. The clock came from board `created_at` UTC stamps plus `date -u` (a3 ran it 9 times). The agents believed about 40 min were left at A17 and about 8-10 min at A28-30. True active elapsed was 17 and 28-30 of 120.
- **PREMATURE_END (consequence of the above, 3 agents)**: the quorum was formally correct (no OPEN/CLAIMED items), but it closed at A31.8/120. Judge-visible gaps that the spare time could have fixed: templates, SSE, graphical DAG, code readability, the HEAD bug.
- **SELF_REFERENTIAL_VERIFICATION (mild)**: ledger items closed with a generic suite receipt (PR.md:13-43). "templates" and "DAG view" were counted DONE because tests and screenshots passed, not because the brief's intent was met.
- **SCOPE_SHRINK (mild)**: DAG view as cards, client-side filters, polling logs. All were accepted silently as DONE.
- **DUPLICATE_WORK (1)**: the CLI workflow test (8ddd5ef vs 34ab001).
- **REVIEW_LOOP (mild, 3 END rounds / 8 END posts, about 3-4 min)**.
- **DRAFT_AS_PRODUCT**: no. The a1 draft was the base, but it was heavily built out by all three peers.
- **MERGE_CONFLICT (minor, 2 PR.md conflicts + 1 push race)**.
- **New tag proposal, STYLE_DEBT**: the code is functionally verified but written in a compressed one-liner style that no reviewer checks. It costs 1-2 points on the "code" subscore regardless of correctness.
- Absent: IDLE_PEER, INTEGRATION_LOSS, CAP_HIT, PROVIDER_ERROR.

## 8. Time accounting (active min, estimates from the stream; span about 31.5 each)
| Agent | Building | Coordination (board/plan/ledger/votes) | Reading/reviewing others | Testing (own suites, full runs) | Idle/waiting |
|---|---|---|---|---|---|
| a1 | ~13 (draft 1.2, core 5-11.8, GC/DESIGN 14-18, fixes, 33c0435) | ~5 (contracts 2.5-5, PR.md, closure, CONSENSUS) | ~4 (ranking, browser capture 24-28) | ~6 | ~3 (A29-30.4 waiting for receipts) |
| a2 | ~13 (pipeline, sample, triggers, fixes) | ~4 (split/contract 1.7-3.5, posts, votes) | ~4 (ranking, DESIGN table, browser 21.6-22.6) | ~6 (incremental/CLI tests, full suites) | ~4 (waiting A2-3.5, A25.7-26.3, A29.5-31) |
| a3 | ~14 (API/CLI/archives 4.4-11.2, UI, fixes) | ~3 | ~5 (seam review, CDP browser 18-19.7, final review) | ~5 | ~4 (A26.5-29.3, A30.5-31) |
| root | 0 | ~0.5 (spawn) | 0 | 0 | ~31 (wait_agent; by design) |
In total, about 40% of the agents' active time went to building and about 60% to coordination, review, testing and waiting. Testing was largely re-running the same 58-test suite: each peer ran it 2-4 times in the final 8 minutes.
