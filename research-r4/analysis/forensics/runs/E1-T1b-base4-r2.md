# E1-T1b-base4-r2 (baseline 3-peer swarm, T1b field-notes hub): score 7.65

Sources: timeline `timelines/E1-T1b-base4-r2.md` (TL:n = line), rollouts in `lab/ws/E1-T1b-base4-r2/codex-home/sessions`,
`origin.git`, judges `judge/E1/E1-T1b-base4-r2.j{1,2}.md`, `results/.../result.json`. A = active minutes.

## 1. Outcome
- Score 7.65 (j1 7.6, j2 7.7). Coverage 8/8, correctness 8/8, design 7/7, robustness 8/8, code 6/6, ux 7/8. No severe defects;
  both judges guessed "team". The solo run on the same task (E1-T1b-solo-r1) scored 6.95, with ux 5/5.
- Top penalties: "The code is very dense: semicolon-chained one-liners and 200+ character lines in `core.py` and `health.py`"
  (j1). "A leftover `fieldnotes/drafts/a2` prototype (its own `serve.py`) is dead code" (j1, and j2 #4). "the `duplicates` and
  `statistics` jobs just run a normal incremental scan" (j1). "Malformed YAML front-matter ... is not flagged" (j1). "No XLSX
  parser" (both). j2 adds: an imported `not_duplicate` override is not applied until the next scan; the topic "drift" is
  inferred too broadly ("attached to 616 of 957 notes"); author names are not merged; "Migration 004 only adds indexes".
- Delivered size: about 2,540 lines / 237 KB under `fieldnotes/` plus PR.md. The line count understates the volume because the
  code is dense: app.js is 192 lines but 35 KB. Biggest files: service.py 421 lines, core.py 395, app.js 192, api.py 196.
  29 tests pass. Mutation score 0.67 (20/30).
- Active time: run span A24.1 in the timeline. result.json reports active_min 32.95 (it counts more than the timeline span),
  wall time 151 min, 13.1M input tokens (384k uncached), 116k output tokens, 22 commits on main. The cap was not hit (`capped: null`).

## 2. Phase timeline
| A | Phase | Who / what |
|---|---|---|
| 0.0-0.6 | Spawn | Root spawns a1 at A0.1. a2 and a3 start at A0.5-0.6 because a VM freeze of 25 wall-minutes hit between the spawns. |
| 0.6-1.6 | Brief, archive scan, direction claims | All three claim first. a3 changes direction once (TL:85) and a1 once ("Draft directions overlap", TL:88). a2 posts a FACT (TL:95). |
| 1.5-3.2 | Drafts | a3 bddb04f at A2.4 (TL:101). a1 44db6ae at A2.6 (TL:107). a2 e9c21c9 + ccbf6d0 at A3.0-3.2 (TL:130,138). Each draft took about 1-1.6 min, well under the suggested 12. |
| 2.9-5.0 | Contracts, cross-review, ranking | Ownership and contracts are agreed on the board before any vote (TL:122,154,161,174,179). The ranking is unanimous for a2 (TL:195,213,224). |
| 5.3-5.8 | Winner integration and plan | a2 pushes the draft + PR.md plan as d816d05 (TL:233-241). |
| 5.8-13.9 | Parallel build | a3 service/API/CLI 3143a1c at A9.1 (TL:278). a1 core 56855e9 at A10.8 (TL:300). a3 tests/docs 42092e1 at A13.1. a1 tests/plugins 7ed6026 at A13.3. a2 UI 52bad6e at A13.9 (TL:335). |
| 14-21.2 | Integration, seam review, fixes | Each peer reviews the whole product in a browser (a2 A15.3+, a1 A17.4+, a3 A17.4+). About 9 small fix commits. |
| 21.2-21.8 | VM freeze | 30 wall-min pass (03:38 to 04:08 Taipei) while active time moves only 0.5 min. |
| 21.8-23.8 | "Hard cap" wrap-up, PR.md receipts, turn ends | a3 ends at A22.8, a1 at A23.3, a2 at A23.8. Root ends at A24.1. |

First real product code on main: a3's service/API/CLI at A9.1 (592 lines, but untestable until the core landed). The core
landed at A10.8. The first integrated tests passed at A13.8 (TL:333). The first full product with UI was on main at A13.9.
Before that, main had only a2's 47-line draft and the PR.md plan (A5.3).

## 3. Per-agent account
- **a1 (core):** wrote migrations 001/002/004, core.py, parsers.py, health.py, plugins.py, example plugins, the fixture tool,
  the browser_capture.py harness, the core/override/migration tests and DESIGN.md. Its draft (search-first) was never merged.
  It also acted as the main reviewer of others' code: three "Review task" posts on a3's import/export, the README and the
  findings limit (TL:383,398,407).
  - Turn end (TL:643): "Completed and pushed to `origin/main` at `1a09ba1`. All 29 tests pass."
  - Why it ended: wall time, not completion. Just before the freeze, its reasoning listed more work: "Preparing HTML dossier
    report | Documenting POSIX runtime limits | Adding threshold CLI option" (A21.1, TL:563). After the freeze it posted "Hard
    cap elapsed during tool scheduling, so wrapping immediately" (A22.4, TL:608). None of the "threshold CLI option" work landed.
- **a2 (UI, winner):** wrote the winning draft, the PR.md plan, and static/index.html, style.css, app.js and
  api-reference.html. It kept browser harnesses in its private .work folder (browser.cjs, scenario.js). It handled both PR.md
  merge conflicts (TL:576,581,651-655).
  - Turn end (TL:658): "Completed and pushed ... `5250a4f` ... Own servers stopped".
  - Why it ended: no time reasoning is visible. It wrapped up in the same wall window as the others, after receipts:
    "All user-requested work integrated; stopping" (TL:655).
- **a3 (team service):** wrote service.py, api.py, `__main__` CLI, migration 003, the service and API tests, API.md and README.
  It added relocate-archive, import evidence disambiguation and the static-asset alias fix (af5b9e2). Its draft (health-first)
  was never merged.
  - Turn end (TL:624): "API, CLI, accounts, curation, portable exports, dossier reports, and documentation are complete ... 28 tests passed".
  - Why it ended: "Hard cap reached, no further code changes from a3" (A22.5, TL:614). This came at active minute 22.5 of a
    120-minute budget, and a review item it had just raised (TL:548,561) was handed off.

## 4. Coordination costs
- **Discarded work:** the a1 and a3 drafts (32 and 33 lines, about 1 min each of build time) stayed on draft/* by design.
- **Dead draft on main:** a2's draft (47 lines, about 13 KB) went to main through the mandatory winner integration (TL:236)
  and was never removed. Both judges penalized it, and it is j1's reason for guessing "team".
- **Seam found three times:** index.html loaded `/static/app.js`, but the API served `/app.js`.
  - a2 found it at A14.7 ("correcting own HTML prefix now", TL:351) but pushed the fix only at A18.4 (5e245b1).
  - Meanwhile a3 (A18.2, TL:464 "BLOCKING seam") and a1 (A18.4, TL:474) rediscovered it.
  - a3 also changed the API to serve both paths (af5b9e2), which made the fix redundant: "API prefix aliases harmless but no
    longer needed" (TL:497).
- **Other duplicate detections:**
  - The findings-limit-1000 truncation was found by a1 (A16.8, TL:407) and again by a2 (A18.6, TL:483), and a3 had already
    fixed the API side (36b0079).
  - The restore-relocation seam was "noticed independently too" by a3 (TL:412).
- **Duplicate harnesses:** there are three separate Chrome DevTools harnesses: a1 fieldnotes/tools/browser_capture.py, a2
  .work/browser.cjs and a3 .work/product-check.cjs. The prompt asked for one: "Build first, and once".
- **Merge conflicts:** two PR.md append conflicts, both resolved by a2 (A21.2-21.8 and A23.5-23.7). They cost about 1.1 active
  min in total. Code conflicts: none; file ownership was clean.
- **Ignored messages:** none found. Every review task was claimed or answered within about 1 min.

## 5. Penalty -> cause map
| Penalty | Cause in log |
|---|---|
| Dense, hard-to-read code (code 6) | Each owner wrote whole modules in one heredoc call: a1 core.py at A10.4 (TL:290), health.py at A8.4, a3 service.py at A7.7 (TL:264). No review post ever mentions readability; all reviews targeted seams and behaviour (TL:383-407, 548, 561). |
| Leftover drafts/a2 | The winner integration rule merged draft commits e9c21c9/ccbf6d0 to main (TL:236,241). The production UI was then built in static/ ("UI assets will be fieldnotes/static/...", TL:241). Removing the draft was never claimed. |
| duplicates/statistics jobs are just a scan | The brief asks for long jobs ("full reindex, duplicate detection, log statistics"). a1's contract defined only job states, not kinds (TL:297). There was no discussion, so the gap was never planned. |
| Malformed front-matter not flagged | Never mentioned on the board. No visible cause. |
| No XLSX parser | The brief mentions it. It is never discussed on the board (no "xlsx" posts). a1 shipped a vendor TSV plugin (7ed6026), and PR.md/DESIGN list the gap as a deliberate boundary. |
| Imported not_duplicate applies only after the next scan | a2 raised it at A19.1 (TL:510). a1 answered that the worker "will reconcile soon" (TL:527), so it was accepted as a known lag. |
| Noisy topic "drift", authors not merged | a1's core reports were counts only ("10,846 relationships; 1,298 health findings", TL:308). No one checked the quality of the inferred topics or people. |
| Migration 004 adds only indexes | a1 created it on purpose to prove the user-data upgrade path (TL:554). |

## 6. Decision points
1. **A2.9-4.0: contracts and ownership agreed before the vote** (a3 TL:122,154; a1 TL:161,179). The split into core / service+API /
   UI was settled while the drafts were still being ranked. Build work started at A5.8 with no further negotiation.
2. **A4.3-5.0: unanimous ranking for a2** (TL:195,213,224), so the vote caused no tie and no review loop. The cost: the draft
   was merged as-is and stayed as dead code.
3. **A5.8-13.9: three file-disjoint parallel builds** of 2.4-5.5 min each. This is where the coverage-8 product was produced.
   a3 built against a1's posted contract before the core existed ("awaiting core for integration tests", TL:283), and it fit on
   the first test run (TL:333).
4. **A14-21: three independent whole-product browser reviews.** They found real seams (asset paths, findings truncation, import
   evidence, restore relocation, the oversized-read cap), which explains robustness 8. They found each seam more than once.
5. **A21.7-22.5: the run ended on wall time.** After the 30-wall-minute freeze, a1 and a3 read the board post `created_at`
   timestamps (about 124 wall-min since their spawn) and wrapped up: "Hard cap elapsed" (TL:608), "Hard cap reached" (TL:614).
   At that point only 22.5 of 120 active minutes had been used, and a1 dropped the work it had planned (TL:563).

## 7. Failure-mode tags
- **WALLCLOCK_RUSH (2: a1 TL:608, a3 TL:614):** all three peers ended within 1 active minute of each other, right after the freeze.
- **PREMATURE_END (1, mild: a1, TL:563 vs TL:608):** planned work (threshold CLI option, dossier report docs) was abandoned.
  The product was otherwise reviewed clean.
- **DUPLICATE_WORK (3):**
  - The asset-path seam was detected and fixed twice.
  - The findings-limit seam was found twice.
  - Three browser harnesses were built.
- **INTEGRATION_LOSS (none):** all agreed work reached main. The a1/a3 drafts were discarded by design.
- **DRAFT_LEFTOVER (new tag, 1):** the winning draft is merged verbatim and never deleted, and the dead code is visible to judges.
- **MERGE_CONFLICT (2, PR.md only, minor).**
- **SELF_REFERENTIAL_VERIFICATION (1, mild):** core verification reported counts and speed, not whether the inferred links are
  plausible (TL:308,372). This is consistent with the noisy-topic penalty.
- **SCOPE_SHRINK (mild):** XLSX and dedicated duplicate/statistics jobs were dropped without a board decision.
- **Not observed:** IDLE_PEER, REVIEW_LOOP, CAP_HIT, PROVIDER_ERROR.

## 8. Time accounting (active minutes, estimated per tool call from rollout command contents; +/-0.5 per cell)
Method: the time before each call (generation plus the call itself) is attributed to the call's purpose. Mixed calls are split
by judgment. Orientation means reading the brief and scanning the archive.
- "Building" includes drafts (a1 1.1, a2 1.6, a3 1.0), writing tests and own docs.
- "Coordination" includes board posts, claims, contracts, votes, git pull/rebase/receipts, PR.md plan, receipts and conflict
  resolution.
- "Reviewing+testing others" includes draft cross-review and whole-product browser and API reviews.

| Agent | Span | Orient. | Building | Coordination | Reading others' code | Review+test others | Test own | Idle-wait in turn |
|---|---|---|---|---|---|---|---|---|
| a1 | A0.1-23.3 (23.2) | 0.9 | 11.6 | 3.5 | 1.3 | 2.9 | 3.0 | 0 |
| a2 | A0.5-23.8 (23.3) | 0.7 | 11.5 | 4.3 | 0.8 | 1.4 | 4.6 | 0 |
| a3 | A0.6-22.8 (22.2) | 0.5 | 10.1 | 5.5 | 0.8 | 3.1 | 2.2 | 0 |
| **Swarm** | 68.7 agent-min | 2.1 (3%) | 33.2 (48%) | 13.3 (19%) | 2.9 (4%) | 7.4 (11%) | 9.8 (14%) | 0 |

- **Idle:** no peer waited for another within its turn. The header's "idle gaps" (a2 A8.4+5.5, a3 A9.6+3.5) are single long
  generations of app.js and of the test files (TL:336, TL:314), so they count as building.
- **After turn end:** a3 sat 1.3 min and a1 0.8 min while the others finished. Root was spawn-and-wait for A0.8-24.1, with no work.
- **Wall-active span:** A0.0-24.1 (24.1 active min, 151 wall min). Swarm effort was 68.7 agent-min, about 2.85x the span.
- **Comparison with solo:** the T1b solo run used 32.0 active min (from its timeline header).
- **Overheads:** draft-and-vote overhead before productive building was A0.6-5.8, about 15 agent-min in total. Of that, about
  3.7 was drafting (2.1 of it discarded) and the rest was claims, contracts, cross-review and ranking.
- **Code contribution to final main** (git log --stat on b4c649a..main, +lines; blame on main fieldnotes/ + PR.md):

| Agent | +lines added | -lines removed | Commits | Surviving lines | Surviving KB | Note |
|---|---|---|---|---|---|---|
| a1 | 1,166 | 14 | 10 | 1,153 | 84 | |
| a3 | 1,109 | 31 | 6 | 1,079 | 73 | |
| a2 | 325 | 18 | 8 | 305 | 80 | Dense UI. Includes about 13 KB of dead drafts/a2. |

- **Discarded work:**
  - The draft/a1 (32 lines) and draft/a3 (33 lines) branches.
  - The duplicate asset-path fix: a3's /static alias, about 0.5 min.
  - The duplicate seam rediscoveries, about 1 min across a1 and a3.
  - Two private browser harnesses, about 1.5 min.
