# E1-T2-base4-r2 (T2 clinic shift planner, arm base4) — HIGH 7.9

## 1. Outcome
- Score 7.9 (j1 7.9, j2 7.9). No severe issues. Both judges guessed "single".
- Top penalties:
  - Code 7: "the code is very dense. `app.js` has lines up to 2,539 characters".
  - Coverage: "Missing: a UI for adding or removing staff, roles or sites, and staff preferences".
  - j2 non-severe bug: "a swap between a Riverside Day Doctor and a Hillcrest Day Nurse was accepted, and approval created two coverage gaps without blocking" (publishing still blocks).
  - j2: "missing PR.md". PR.md is in delivered/ (56 lines), so this is likely packaging.
  - 20 soft under-contract warnings: "comes from the data rather than a bug" (j1).
- Delivered: about 1,902 lines of code. Main parts: engine.py 376, service.py 520, exports.py 95, app.py 144, app.js 115, tests 508 (47 tests), capture scripts 89.
- 23 commits. Active 26.1 timeline span (result.json 32.99), wall 100.5. Tokens: input 13.37M, output 122k. Mutation 0.57.

## 2. Phase timeline (active minutes)
| Phase | A | What happened |
|---|---|---|
| Claim | 0.7–1.4 | a1 "staffing-first command center" (TL:65), plus a FACT proposing one shared validator "used both by generation and manual changes" (TL:66). a3 "people-first rota ledger ... per-person contracted hours / nights / weekends fairness" (TL:77). a2 "exception-first ... guided review-and-publish" (TL:80, 94). |
| Drafts | 1.4–3.7 | a3 72cd48b: 10 lines, "Draft interactions illustrative" (TL:101). a2 baf8608: 19 lines (TL:120). a1 c1a47e2: 87 lines (TL:155). a3 FACT on capacity math "16 assignments/day = 128h/day ... More generous per-role minimums quickly make 25 impossible" (TL:152). a2 at A3.8 already offers to "own hard-part scheduling engine + shared rule validator" (TL:160). |
| Ranking | 4.3–4.6 | Screenshots at 1440 and 390 (17 `view_image` calls). All three ranked a1 first (TL:185, 195, 205). |
| Plan + contracts | 4.6–6.9 | DONE integration of the winner (TL:208, A4.6). Ownership: a1 UI/HTTP/CLI, a2 engine, a3 persistence/workflows (TL:186, 217, 222). Contract proposals (TL:203, 214). PR.md plan f604a05 (TL:252, A6.2). |
| Build | 6.2–13.3 | Engine 1650c9c +504 (TL:316, A9.9). Service b98e891 +563 (TL:325, A10.1). UI ebc21fd +277 (TL:376, A13.1). |
| Integration/review | 13.4–23.7 | Seam bugs found and fixed: contract-edit payload (TL:461), CSV published flag (TL:479), adjacent-month publication gate (TL:488 -> 2d02d0a), tablet overflow (TL:615). Browser smoke runs from all three peers (TL:468, 474, 673). |
| Finish | 22.9–26.0 | a2 TURN_END "done" at A22.9 (TL:667). a3 at A25.7 (TL:739). a1 at A26.0 after the final receipt 69ec80f (TL:752). |

## 3. Per-agent account
- **a1** (UI/HTTP/CLI/capture/PR): draft, ranking, plan; UI A6.6–13.1; integration fixes A14–21.4; final docs A23–25.8. TURN_END: "All 47 tests and desktop/mobile browser workflows pass" (TL:752).
- **a2** (engine): engine A6.2–9.9; boundary repairs (53e39cf), solver runtime bound (92b6a08), zero-minimum semantics (2eb6482); reviews of a1 and a3 seams. It ended first, at A22.9: "All assigned work and review are complete; no outstanding a2 changes ... a1 can record combined final verification and finish" (TL:662). a2 did not review a3's later 5dc6129 and 52b6251 commits.
- **a3** (service/workflows/exports/docs): service A6.2–10.1; integration tests 8665485; config inheritance and docs 06e2710; neighbour publication gate 2d02d0a; multiplicity fix 5dc6129. TURN_END: "All 47 tests pass; full browser workflow and responsive states reviewed" (TL:739).

## 4. Coordination costs
- **Contract churn A4.6–8.4.** Competing proposals on settings vs rules and Service vs ClinicService. a1 "CONTRACT RESOLUTION" (TL:281). a3 then supported "BOTH class/method APIs" to avoid drift (TL:290). a2 later said "settings canonical" (TL:294). Cost: about 2 min of posts plus some dual-API code.
- **One merge conflict.** a3: "rebase hit a README-only overlap with a peer's fixture documentation" (TL:710, A24.6). Resolved in about 0.5 min.
- **Small unreviewed tail.** a2 ended before the last two a3 commits. No END quorum exists in base4.

## 5. Penalty -> cause map
| Penalty | Cause |
|---|---|
| Cross-role swap accepted | Swap validation in service/engine checked rule violations but not role equality. a2 seeded a same-role swap only ("two doctors on same day/shift", TL:358), so the cross-role case was never exercised. |
| No staff/role/site CRUD UI | Never claimed. a1 added renaming only (TL:536). |
| Dense code | Single-shot generation of app.js/service. No style review. |
| "missing PR.md" | No visible cause (PR.md is present). |

## 6. Decision points
1. A0.7: a1 FACT proposes one shared validator for generation and edits (TL:66). This framing survived into the plan.
2. A3.8: a2 volunteers for the hard part (engine) before the ranking (TL:160).
3. A4.6–6.2: winner integrated, then the plan, contracts and ownership are fixed within 2 min.
4. A13–23: three independent browser walkthroughs found seam bugs that were fixed.

## 7. Failure-mode tags
- MERGE_CONFLICT (1, trivial, TL:710).
- REVIEW_LOOP: none. Contract churn (new tag CONTRACT_CHURN, about 2 min) at TL:254–294.
- PREMATURE_END (mild, 1): a2 ended with 2 peer commits still to land. No penalty traced to it.
- INTEGRATION_LOSS: by design, 29 lines of losing drafts.
- WALLCLOCK_RUSH: none visible (freeze A5.0->5.4 = 32 wall min; no time headings).

## 8. Time accounting (active min, estimates)
| Agent | Building | Coordination | Reading others | Testing | Idle |
|---|---|---|---|---|---|
| a1 | 12 | 4 | 2 | 6 | 2 (gaps A6.6+3.2, A9.8+3.3 are long generations) |
| a2 | 9 | 3 | 3 | 6 | 1 |
| a3 | 11 | 3 | 2 | 7 | 2 |
