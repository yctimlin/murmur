# E1-T1b-base4-r1 (baseline 3-peer swarm, T1b Fieldnotes Hub) - score 7.6

Sources: timeline `timelines/E1-T1b-base4-r1.md` (TL:n = line), raw rollouts (a1=`*70ae*`, a2=`*8bc4*`, a3=`*a3a2*`),
`origin.git` (main f24fb5d), judges j1/j2, result.json, prompts/a1.md.

## 1. Outcome
- Score 7.6 (j1 7.8: cov 8/corr 8/des 8/rob 8/code 6/ux 8; j2 7.4: 8/8/7/7/6/7). Both judges guessed "team". No severe defects.
- Top penalties (both judges gave code 6/10):
  - j1: "`static/app.js` is 41 lines, some of them up to 4,004 characters, so effectively hand-minified"; "`store.py` and `team.py` pack several statements per line".
  - Both: "A prototype folder `fieldnotes/drafts/a2` was left in the delivery".
  - j1 coverage: "The CLI cannot change finding state or annotate"; "`fieldnotes item` on the CLI omits annotations and tags"; "An unsupported file type (`.vtsv`) is silently indexed"; "452 metadata findings ... make the health inbox noisy".
  - j2: "log-to-experiment 'time window match' inference is thin"; "Facet counts don't change"; "BrokenPipeError"; "CLI output is JSON".
- Delivered: 37 files under `fieldnotes/` + PR.md. Product code (non-.md, excluding drafts) is 2,279 lines / 177 KB, so lines are very dense (about 78 bytes per line on average; app.js is 32.6 KB in 41 lines). There are 27 tests. Docs (README 172, DESIGN 63, API 66, TEAM 33, PR 72 lines).
- Time: run active span A0.0-A21.3 (result.json active_min 28.42 incl. setup), wall 117.7 min. Peers ended A20.4/A20.7/A21.0 out of a 120-min cap.
- Tokens: input 12.84M (uncached 0.40M), output 113K; 24 commits. Mutation score 19/30.
- Solo comparison (header only): E1-T1b-solo-r1 6.95, span A0.1-A32.0, input 1.97M, 1 commit. Its severe issue was a failing shipped test fixture. Its ux was 5 vs 7-8 here.

## 2. Phase timeline (active minutes)
| Phase | A-range | What happened / who |
|---|---|---|
| Orientation + claims | 0.0-0.9 | All read prompt/archive. Claims are a1 "evidence-first researcher workbench" (TL:66 A0.6), a2 "dossier-first" (TL:73 A0.8) and a3 "team health inbox" (TL:83 A0.9). |
| Drafts | 0.9-2.4 | a1 7e87129 (44 lines, A1.7 TL:89), a3 72ee2e8 (37 lines, A1.8 TL:94), a2 19d8945 (39 lines, A2.4 TL:126). Each took about 1-1.5 min, well under the "about 12 minutes" budget. |
| Cross-capture + ranking | 2.0-3.8 | Each peer ran and screenshotted all three drafts. Rankings: a1 a2>a1>a3 (TL:166), a2 a1>a2>a3 (TL:170), a3 a2>a1>a3 (TL:187). a2 wins 2/3. |
| Contract + ownership | 3.6-5.5 | a1 posted a "Proposed shared contract" (TL:167 A3.6). Owners: a1 core/storage/DESIGN, a2 API/CLI/UI/README, a3 Team/export (TL:181,193,196). Override names crossed in flight (TL:207,211,239). a2 "integrated winner" = PR.md plan 6784bfc (A5.5 TL:225). |
| Parallel building | 4.9-13.4 | Core d56e146 (401 lines, A6.1 TL:237). Team 97421fd (469, A7.7 TL:270). Snapshots/TEAM.md (A9.7). Store 34b8f66 (451, A10.9 TL:320). API/CLI/UI 8ba1691 (315, A11.3 TL:335). Core tests fc639be (A12.4). Manual findings + capture tool 95eb2c4 (A12.7). |
| Review / verification / docs | 13.3-19.8 | a3 UI review with captures (TL:425 A14.3). DESIGN 4f77edf (A15.1). README/API docs + API tests 4ee33c1 (A15.8). HTTP workflow tests 921f7c4 (A16.3). 10x benchmark (A16.3-18.1). Binary-parser seam c10da1d (A17.2). Final mobile polish + demo 49e7ed7 (A19.6). |
| Wrap-up / turn ends | 19.8-21.0 | a1: "Hard cap in ~4m" (TL:614). Receipts follow, then PR.md conflict cleanup. TURN_END a1 A20.4 (TL:651), a3 A20.7 (TL:668), a2 A21.0 (TL:678). Root ended at A21.3. |

There was no END-vote phase (base4 arm). The root only spawned and waited from A0.4 to A20.5.

## 3. Per-agent account
**a1 (core / storage / DESIGN)**
- Built: parsers, migrations, plugins, store.py (ingest/inference/search/jobs), core tests, DESIGN.md, the binary-parser seam, the 10x benchmark and PR verification text.
- Final main: 9 commits, 1,086 insertions (996 code lines / 58.7 KB by blame).
- Did the biggest single generation: store.py in one 4.5-min call (A6.1-10.6, 31.9K-char call).
- Ran the whole-product CLI/browser review (A13.3, A15.8).
- Turn end A20.4: "Completed and pushed to `origin/main` at `85a3ae4`. All 27 tests pass..." (TL:651).
- Why it ended: it believed the cap was imminent based on wall clock. At A15.8 it posted "Need a2 finish README/API docs and integration tests urgently (remaining ~33m of cap)" (TL:470). At A19.8 it posted "Hard cap in ~4m (start21:08, now23:04)... Do not add new broad work" (TL:614).

**a2 (API / CLI / UI / README; draft winner)**
- Built: app.py, api.py, cli.py, static UI (app.js, css), test_api, README, API.md and demo.py.
- Final main: 6 commits, 803 insertions (473 code lines but 67.1 KB, the densest; plus a 29-line leftover draft).
- Wrote the API before the core existed: "a2 API/CLI implemented against proposed contracts. Need a1 confirm..." (TL:258 A6.8). It then rewrote api.py and app.js (A10.1, 21.8K-char call) once Store shapes landed. Its CLI plan omitted annotate and finding-state commands: "CLI init/migrate/ingest/search/findings/export/import/user/serve" (rollout, A4.9).
- Turn end A21.0: "Completed and pushed to `origin/main` at `f24fb5d`. Implemented CLI, authenticated API, responsive offline UI, documentation and seeded demo..." (TL:678). This came after a1's cap warning and its own final browser-flow PASS (TL:609).

**a3 (Team / curation / export / capture tool / workflow tests)**
- Built: team.py, migrations 002-004, snapshots.py, TEAM.md, the shared Chrome-CDP capture.py (A11.5), HTTP workflow tests and the PR walkthrough.
- Final main: 9 commits, 893 insertions (810 code lines / 50.9 KB).
- Did the most cross-review: UI captures at A13.9-14.3, A18.4 and A19.1, and a DESIGN review at A17.0 (TL:520).
- Turn end A20.7: "Completed and integrated on `origin/main` at `85a3ae4`. All 27 tests pass..." (TL:668). It had first posted "no remaining issue owned by a3" (TL:619 A19.8), the same second as a1's cap warning.

## 4. Coordination costs
- **Winner draft not built on, shipped as dead code.** "Integrating" the winner meant merging draft/a2, which left `fieldnotes/drafts/a2` on main, then writing PR.md (6784bfc, TL:225). The product was rewritten from scratch in `fieldnotes/`. Nobody deleted the draft folder, and both judges penalized it. The a1 and a3 drafts (44+37 lines) stayed on draft/* by design.
- **Contract churn / rework.**
  - Override naming crossed three times: link/linked (TL:207 -> TL:211 -> TL:239 "Names crossed in flight; core will accept BOTH").
  - a2's guessed-contract API (A6.6) was largely rewritten at A10.1 to use `Store.start_worker` instead of `Worker` (TL:289). That cost about 3 min of a2 building time.
- **Duplicate work (small).**
  - a1 announced a "tiny stdlib Chrome CDP harness" (TL:431 A14.8) that a3 had already pushed at A12.7. a1 cancelled it 0.3 min later (TL:439), so about 0.4 min was lost.
  - The binary-parser seam was raised by a3 (TL:509) and implemented by a1 (A17.2). a2 then requested it again (TL:562 A18.2), and a1 answered "already on main c10da1d" (TL:573).
- **Merge conflicts (4, all on shared docs).**
  - a2: `.gitignore` rebase union (TL:480 A16.2).
  - a1: PR.md append conflict, resolved by script (TL:585 A18.6).
  - a3: PR.md conflict ended with `git rebase --skip`, which discarded its doc commit: "skipped own overlapping doc-only commit" (TL:657,660 A20.5).
  - a2: PR.md conflict markers stripped by script (TL:663 A20.7).
  - None reached main (0 markers in f24fb5d).
- **Repeated verification.** The full UI was captured independently by a3 (3x), a1 (1x) and a2 (3x incl. montage). The 27-test suite was re-run by all three in the last 1.5 min. This is mild redundancy, but it also found real seams, e.g. UUIDs in Team activity and narrow health list reachability (TL:425), fixed by a2 in 4ee33c1.
- **Ignored messages:** none material. Every seam post got an owner reply within about 1 active min.

## 5. Penalty -> cause map
| Penalty | Cause in log |
|---|---|
| Dense, minified code (code 6) | No visible cause beyond generation style. Files were written whole via heredocs, and app.js was patched by Python `s.replace(...)` (e.g. TL:380 A12.6 "Fixing app.js parentheses"). No review post ever mentioned readability (0 rollout hits for minif/readab/semicolon). Reviews checked behaviour only. |
| `fieldnotes/drafts/a2` left in delivery | The integration step at A5.5 (TL:225). The prompt says the winner "must immediately bring it onto main". a2 merged the draft branch and then built the product elsewhere. Nobody cleaned it up. |
| CLI lacks annotate / finding-state; `item` omits tags/annotations | Never planned. a2's interface proposal (A4.9) listed CLI "init/migrate/ingest/search/findings/export/import/user/serve". Composition of annotations lives in api.py:97 (j1). No reviewer exercised CLI parity. |
| Unsupported types silently indexed | No visible cause (a1 parser default). Not discussed. |
| Time-window inference "thin" | It was planned and documented (DESIGN tiers 0.85/0.55 for "overlapping timestamp windows"). The judge copy lacked logs/, so this is partly a judging artifact. |
| Noisy health inbox (452 metadata findings); near-dup threshold finds 0 | a2 added `--duplicate-threshold (.94 default)` only at A20.1 (TL:632). Real-archive findings were counted (635 open, TL:332), but their usefulness was never triaged. |
| Facet counts static; BrokenPipe; JSON-only CLI | No visible cause. Not discussed. |

## 6. Decision points
1. **A3.6-4.5 ranking + contract** (TL:166-207). a1 voted for a2's draft rather than its own: "a2 dossier-first: strongest daily research workflow". At the same time it posted a full shared contract. This fixed a clean 3-way module split with each module having an owner. The split explains the high design/correctness scores.
2. **A5.5 winner "integration"** (TL:225). Merging the draft branch as-is, instead of folding it into the product, left dead code on main (code-score penalty).
3. **A6.1-11.3 parallel build.** About 31 agent-min of building in about 7 active min. The first product code was on main at A6.1 (core). The first runnable whole product (UI+API on main) was at A11.3 (TL:335).
4. **A15.8 / A19.8 wall-clock deadline** (TL:470, TL:614). a1 read wall time ("start21:08, now23:04") across VM freezes and announced the cap was about 4 min away when about 99 cap-minutes remained. Within 1.2 active min all three peers ended. The CLI gaps, code readability and draft cleanup were never reached.

## 7. Failure-mode tags
- **WALLCLOCK_RUSH (1 agent, 2 posts)**: a1 at A15.8 "remaining ~33m of cap" and A19.8 "Hard cap in ~4m". Actual active elapsed was 15.8 and 19.8 of 120. The cap is monotonic: solo ran 127.8 wall min uncapped, so freezes do not count. This one is decisive for the run's length.
- **PREMATURE_END (3 agents)**: all ended at A20.4-21.0 with judge-visible gaps open (CLI parity, minified code, leftover draft), triggered by the wall-clock rush.
- **INTEGRATION_LOSS (inverted) / DRAFT_LEFTOVER (new tag: the draft is merged as an inert artifact rather than evolved into the product)**: 1 (drafts/a2).
- **DUPLICATE_WORK (minor, 2)**: CDP harness (about 0.4 min), binary-seam re-request.
- **MERGE_CONFLICT (4)**: all on PR.md/.gitignore, all resolved; one doc commit discarded.
- **REVIEW_LOOP (mild)**: 7 independent full-UI capture rounds and 3 final full-suite reruns. These were useful, not excessive.
- **SCOPE_SHRINK (minor, 1)**: CLI scoped to read/admin commands at A4.9 without a PR.md note.
- Not seen: DRAFT_AS_PRODUCT, IDLE_PEER, CAP_HIT, PROVIDER_ERROR, SELF_REFERENTIAL_VERIFICATION (verification was against the real archive, a 10x stress copy, and real HTTP/Chrome flows).

## 8. Time accounting (active minutes)
Method: the active-time gap before each tool call (generation time plus the previous call's execution) is assigned to that call's purpose. Combined calls are split by content (raw rollout arguments). Resolution is 0.1 min, so expect about ±0.5 min per cell.
- **Orient** = prompt, brief and archive survey, tool probing.
- **Coord** = board posts, claims, contract, rankings, PR.md plan, rebase/conflict handling.
- **Read** = `git show`, sed or cat of other owners' files and drafts.
- **Review** = running, capturing or testing other peers' work, including a3's HTTP workflow tests of a2's API.
- **Test-own** = running own code, suite runs and own captures.
- **Idle** = no tool activity inside the turn. Multi-minute gaps (a1 A6.1+4.6, a2 A6.8+3.4) were long code generations (store.py, api.py), not waiting.

| Agent | Span (A) | Orient | Build | Coord | Read others | Review/test others | Test own | Idle in turn | After turn end |
|---|---|---|---|---|---|---|---|---|---|
| a1 | 0.1-20.4 (20.3) | 0.6 | 10.7 | 3.6 | 1.4 | 2.1 | 1.9 | 0 | 0.9 |
| a2 | 0.2-21.0 (20.8) | 0.4 | 12.3 | 3.9 | 0.8 | 1.1 | 2.3 | 0 | 0.3 |
| a3 | 0.3-20.7 (20.4) | 0.5 | 8.3 | 4.9 | 1.8 | 3.7 | 1.2 | 0 | 0.6 |
| **Swarm** | 61.5 agent-min | 1.5 (2%) | **31.3 (51%)** | **12.4 (20%)** | 4.0 (7%) | 6.9 (11%) | 5.4 (9%) | 0 | 1.8 |

- **Build split.** Building includes drafts (a1 0.9, a2 1.3, a3 0.7 = 2.9). Two of the drafts were thrown away and the third shipped as dead code, so effectively all of it was discarded. Building also includes rework: a2's API rewrite after the contract was clarified (about 3 min) and a3's discarded PR.md commit (0.3). Productive building that reached main is about 25 agent-min.
- **Overhead.** Coordination + reading + reviewing others = 23.3 agent-min (38%) vs 31.3 building.
- **Root.** It waited A0.4-A20.5 (about 20 min) at no token cost.
- **Wall-active span.** A0.0-A21.3 = 21.3 active min (wall 117.7). Solo T1b used a 32.0-min span with one agent. The swarm used about 1.9x the agent-minutes (61.5 vs about 32) for +0.65 score, and 6.5x the input tokens.
- **First product code on main.** a1 core d56e146 at A6.1 (pushed by A6.4: a3 read db.py at A6.6). Before that, main held only the snapshot, the inert a2 draft and PR.md (A5.5). The first end-to-end runnable app was on main at A11.3 (8ba1691).
- **Contribution to final main (git log --stat main / blame):**

| Author | Commits | Insertions | Code lines (blame) | Code bytes | Doc lines |
|---|---|---|---|---|---|
| a1 | 9 | 1,086 | 996 | 58.7 KB | 77 |
| a2 | 6 | 803 | 473 (+29 draft) | 67.1 KB (+11.0 KB draft) | 281 |
| a3 | 9 | 893 | 810 | 50.9 KB | 58 |

- **Duplicated or discarded work.**
  - Drafts: a1 44 lines and a3 37 lines never merged (by design); a2's 39 merged but inert.
  - a1's CDP harness was cancelled before any code (about 0.4 min).
  - a3's final PR.md commit was dropped via `rebase --skip` (A20.5).
  - The first api.py version was superseded (A10.1).
  - No product module was built twice: the ownership split held throughout.
