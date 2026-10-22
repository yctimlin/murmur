# E1-T2-base4-r1 (T2 clinic shift planner, arm base4) — score 7.8

## 1. Outcome
- Score 7.8 / 7.8. j1: cov 8, corr 8, design 8, rob 8, code 6, ux 8. j2: code 7, ux 7, other scores the same. No severe issues. Guesses: single / team.
- Top penalties (quoted):
  - j1: "The code itself is very dense: very long lines, CSS packed into a single line, and an app.js of 51 lines but about 29 KB. A leftover `prototypes/` folder was shipped, and the README links to a PR.md that doesn't exist."
  - j1: "swap consent is only recorded by the manager (there is no staff portal). There are no per-person preferences beyond leave. Public holidays and skill mix are listed in DESIGN.md as future work."
  - j2: "The CLI crashes with a BrokenPipeError when its output is piped to `head`"; "Regenerating discards manual edits unless they are locked"; "Fairness for nights and weekends is only a soft warning"; "The CLI only offers generate, check and state."
  - j2 praised the data: "The demo data is realistic: ... part-time contracts, staff who can't do nights, and seeded leave and swap requests."
- Delivered: 17 code files, 1613 lines / 153 KB (very dense: app.js 51 lines / ~29 KB); tests 360 lines, 32 tests. 21 commits; `draft/a1`, `draft/a2`, `draft/a3` remain as branches (by design).
- Active 40.6 min (run span 31.2), wall 110.0. Tokens: input 18.1M (uncached 0.43M), output 115K.

## 2. Phase timeline (active minutes)
| Phase | A | Who | What |
|---|---|---|---|
| Claims | 0.8-1.5 | all | a1 coverage board (A0.8), a2 staff-first grid (A1.4), a3 people-first ledger (A1.5), then switches to an exception workbench at A3.3 because a2's similar claim came first |
| Drafts | 1.5-4.4 | all | a3 `6ed4ba8` A3.3 (21 lines), a2 `3671812` A3.7 (35 lines), a1 `d031e18` A4.2 (36 lines); a3 capture helper A4.4 |
| Ranking | 5.3-6.1 | all | a3: 1) a1; a1: 1) a2; a2: 1) a1. a1's draft wins 2-1 |
| Plan/contracts | 4.5-8.0 | a1 leads | ownership proposal A4.5 (a1 domain/solver, a2 UI, a3 storage/API/requests/calendar/docs); domain interface A5.7; plan + integration `876274f` A7.8 (receipt correction A8.0) |
| Build | 8.0-20.6 | split | a3 storage/API `d6a05bf` A10.4; a1 domain `a713aef` A11.2 (480/480 seats), tests `eaf5bc3` A14.0, fairness `ee8e87b` A15.6; a3 tests/docs `e113429` A14.7, `b09d6de` A16.4; **a2 UI only lands at `157394a` A20.6** |
| Review/fix | 20.8-28.3 | all | UI review: blank first week, slot height, branding, month bounds (a3 A22.0, a1 A22.2); race on month change (a1 A24.4) fixed `f0cd3fe` A28.3 |
| Final docs/finish | 28.9-31.0 | all | a1 `156ea6f` A29.8; DONE posts; turn ends a1 A30.2, a3 A30.6, a2 A31.0 |

## 3. Per-agent account
- **a1 (winning draft, domain/solver/validation, PR.md, browser interaction reviewer)**: built domain.py (426 lines) plus 18 tests, then fairness refinement ("full-time nurse hours now 144-152h (was 96-168)", A15.6). From A16.3 a1 had nothing left to build. It claimed "final browser interaction review once a2 assets land" and waited on the UI: "current board has been quiet from a2 since 09:40" (A21.4). Its coordination share was high (~9 min). TURN_END A30.2: "Completed and pushed to `origin/main` at `156ea6f` ... 32 passing tests."
- **a2 (UI)**: claimed the UI at A5.2. It posted a UI plan at A6.8, then did not push for about 14 active min (gap A7.1+7.9 in the summary). The production UI landed at A20.6, followed by fix rounds (`e1a5ad2` A24.1, race guard `f0cd3fe` A28.3). TURN_END A31.0 "done".
- **a3 (storage/API/requests/calendar/docs/fixtures/capture)**: was the most productive builder of the infrastructure: API, lifecycle tests, 5 fixture DBs, capture_states.py, timezone config, naming unification. It also caught seed/README mismatches. TURN_END A30.6 after a final latest-main review.

## 4. Coordination costs
- Draft phase cost about 7 active min (A0.8-7.8) for three 21-36-line drafts. The winning draft was mostly rewritten. Its remnant `prototypes/a1` shipped on main, which both judges penalised.
- Late UI integration: main had no UI from A8 to A20.6. Peers repeatedly asked for it: "a2 please push available UI now so we can review within cap; main currently lacks clinic/static entirely" (a3 A18.4).
- Branding seam: the UI said "Fieldwork" while docs, CLI and ICS said "Daywell" (a1 A22.2). Fixed by a3 at A23.6.
- No merge conflicts reported; no lost work; no re-votes (base4 has no END quorum).

## 5. Penalty -> cause map
| Penalty | Log cause |
|---|---|
| Leftover `prototypes/` folder; README links to missing PR.md / "draft comparison" | Draft-then-integrate step: a1 integrated the winning draft into main (`876274f`, A7.8) and nobody removed it. PR.md removal is the anonymiser. |
| Dense code (51-line, 29 KB app.js) | a2 wrote app.js in one heredoc at A20.4 (TL:442), right after the peers' "~30-33 min left" posts (A18.2-18.4). No one reviewed the code style. |
| BrokenPipe on CLI; CLI only generate/check/state | No visible cause; CLI was never a ledger-like item; nobody ran the CLI piped. |
| No preferences, holidays, skill mix | a1 A16.2 asked a3 to "document remaining clinic-specific policies to confirm (skill grades, breaks, on-call, training, holi...)", a deliberate descope recorded in DESIGN. |
| Fairness only soft | a1 design choice (A15.0 "minimizing contract-normalized squared hours/night/weekend burden"). |
| (Positive) realistic seed with leave and swaps | a1 review A18.0 "README says seed includes approved leave but initialize currently only 2 pending leave requests ... I recommend richer seed"; a3 already enriched it (A18.4). |

## 6. Decision points
1. A5.3-6.1: ranking picks a1's coverage board, and the team agrees a split (a1 domain, a2 UI, a3 API). The production architecture was decided here, not by the drafts.
2. A7.8: a1 integrates the winning draft plus the plan. The `prototypes/a1` remnant enters main.
3. A8-20.6: the UI owner works off-main for about 12 active min. Every UI seam was found after A21, compressing review into the last 10 minutes.
4. A18.2: a1 reads wall clock ("my120min cap began08:38Z (~33min left)"). Actual active time used was 18 min of the monotonic 120-min cap. a3 echoes "~30min until conservative 120m cap" (A18.4). The rest of the run is framed as a rush.
5. A23.5: a1 "I have~18min to cap; will finish remaining actual UI interactions". Finishing posts follow at A29.8-31.0, when about 31 of 120 active min had been used.

## 7. Failure-mode tags
- WALLCLOCK_RUSH (3 posts: a1 A18.2, a3 A18.4, a1 A23.5): the team believed ~18-33 min remained when ~90 active min remained. Plausible effect: dense code, no further scope (CLI, preferences).
- DRAFT_AS_PRODUCT (mild): the draft was not shipped as the product, but its prototype directory was shipped alongside it.
- IDLE_PEER (a1, partial, A16.3-20.6): waited for the UI and filled the time with docs and review notes.
- INTEGRATION_LOSS: none (drafts were intentionally left on branches).
- PREMATURE_END: arguably yes, through the rush, though the brief's core was met. Rated soft.

## 8. Time accounting (heuristic, from call gaps; build includes writing tests)
| Agent | build | coordination | reading others | testing/review | idle |
|---|---|---|---|---|---|
| a1 | 5.9 | 9.1 | 7.6 | 6.1 | 0 |
| a2 | 6.6 | 2.3 | 7.6 | 12.5 | 0.8 |
| a3 | 5.9 | 3.9 | 6.7 | 10.6 | 0.4 |

## Verification profile (for the C2 contrast)
- No pre-written acceptance checks. Tests were written by each builder after building: a1 domain tests A14.0 (18 tests), a3 lifecycle/HTTP tests A14.7 (32 total).
- Defects were found by cross-review and live browser use: overnight leave/adjacent-month seams (a1 A12.6, a3 A12.1), the seed/README mismatch (a1 A18.0), UI layout seams (A22.0), and the month-change race (a1 A24.4).
