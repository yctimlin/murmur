# E1-T4b-C1-r4 (arm C1, task T4b) — score 7.45

Sources: timeline `timelines/E1-T4b-C1-r4.md` (TL), judges `judge/E1/E1-T4b-C1-r4.j1.md` / `.j2.md`,
`origin.git` log, delivered tree `lab/results/E1-T4b-C1-r4/delivered/`, `result.json`.

## 1. Outcome
- Score 7.45 (j1 7.6, j2 7.3). Sub-scores: coverage 8/8, correctness 8/8, design 8/7, robustness 7/7, code 6/5, ux 7/7.
  Both judges: no crash, all brief-mandated commands pass (36 tests, smoke, 250k benchmark, real e2e).
- Top penalties (quoted):
  - Code style: "The Python is packed onto very long lines with semicolons (`domain.py` is 611 lines and ~50KB)" (j1);
    "Code quality and tests: 5 ... long one-line statements chained with semicolons" (j2).
  - Strict CSV: "a file that is both re-quoted *and* has trailing whitespace got 365 of 366 rows quarantined" (j1);
    j2 severe: "Reformatted re-download with whitespace after closing quotes is quarantined wholesale".
  - Thin UI: "The 'charts' are CSS progress bars only"; "manual pairing works only from the CLI/API, not the browser".
  - Recurring noise: "flags AIRBNB, AMAZON and CAFE NERO as recurring" (j2).
  - Leftovers: "A leftover `drafts/a1.py` is shipped"; "`DESIGN.md` refers to a `PR.md` file that doesn't exist" (j1).
- Delivered: 2,150 Python lines but 180 KB of Python (avg ~84 chars/line; 111 lines >200 chars); `domain.py` 611 lines.
  UI: `static/app.js` 45 lines, `index.html` and `style.css` 1 line each (minified-style).
- Active 41.5 min per result.json (timeline span 34.8); wall 93.5. Input 19.9M tokens, output 141k. 29 commits; all
  three draft branches left as `draft/*` (drafts a2/a3 intentionally unmerged).

## 2. Phase timeline (active minutes)
| Phase | A-range | What happened |
|---|---|---|
| Read brief, claim directions | 0.3-1.4 | a1 claims "audit-first reconciliation workbench" (TL:49); a2 first claims the same, a1 objects (TL:72), a2 switches to "daily household dashboard" (TL:79); a3 "household cockpit" (TL:76). |
| Data study | 1.0-2.9 | a1 builds an exhaustive inventory: "six malformed records ... 2024 contains 12 TFR pairs ... No refund descriptors" (TL:104, A2.9). a3 FACT on python3.12 path (TL:87). |
| Drafts | 1.4-3.4 | Drafts are tiny: a3 22 lines (TL:99, A2.8), a1 40 lines (TL:102, A2.9), a2 20 lines (TL:129, A3.4). ~2 min each, not the 12 allowed. |
| VM freeze | 3.4-4.4 | wall 09:39 -> 10:01, no activity. |
| Ranking | 4.4-5.5 | Unanimous: a3 "1) a1, 2) a2, 3) a3" (TL:152); a2 "1 a1" (TL:164); a1 "1 a1" (TL:184). |
| Integrate winner + contract | 5.5-7.2 | a1 "DONE winning draft integrated origin/main e5bfa46" (TL:186) — a fast-forward of the 40-line draft (later shipped as `drafts/a1.py`). Module ownership proposed by a1 (TL:185), a2 (TL:165, 190), a3 (TL:172, 195); agreed by A7.2 (TL:227-234). |
| Build | 6.7-23.0 | a1: schema+migrations 540fd54 (A6.7), parsers/ingestion df07344 (A8.8), Kiwi ref fix 5e39361 (A11.2). a3: app/auth/server/CLI de787a0 (A9.6). a2: domain.py 2a4c373 (A11.3), tests/FX/benchmark a7ff1ca (A17.1), SLA fix 4e8d4e2 (A19.8). a3 UI ebacb24 (A17.3), 5de3744 (A22.9). |
| Seam review (overlaps build) | 13.0-27.6 | Cross-module bug reports on board: refund merchant markers (TL:300), CLI `name` vs `kind` (TL:324), new imports never categorised (TL:329), accountant budget leak (TL:332), benchmark target merchant absent (TL:413), ledger split/refund categories (TL:429), UI £0 chart bars (TL:470), UI toast race (TL:550). All fixed on main. |
| Docs/verification | 21.2-33.4 | IMPORT_SUMMARY (A21.2), README (A22.9), PR ledger consolidation (A26.7-27.7), VERIFY.md and ledger close d540b4e (A33.4). Freeze wall 10:48 -> 11:06 at A31.0-32.1. |
| END votes | 33.9-34.0 | a2, a1, a3 all `END d540b4e` (TL:780, 785, 789). |
| Turn ends | 34.2-34.8 | a3 A34.2, a2 A34.2, a1 A34.6, root A34.8. |

## 3. Per-agent account
- **a1** (63 calls, 15 commits, 36 posts). Owned db/migrations, six parser plugins, ingestion (dedup, quarantine,
  revert), staged import, real-data reconciliation, backup, DATA_FINDINGS, DESIGN, IMPORT_SUMMARY, PR ledger, VERIFY.
  Also the most active seam reviewer (TL:300, 324, 329, 413, 429, 470, 477, 550). Found the Kiwi regenerated
  `ref ####` overlap at A9.3 ("Kiwi overlapping exports regenerate ', ref ####' ... canonicalizing", TL:254) and fixed
  it (5,480 -> 5,424 tx, TL:276). Ended A34.6: "Completed on `origin/main` at `d540b4e`; all peers approved the same
  commit." (TL:813).
- **a2** (58 calls, 8 commits, 25 posts). Owned domain.py: matching/refunds, FX, rules/learning/splits, jobs, undo,
  budgets/reports/exports, benchmark. domain.py written in one heredoc call after a 3.5-min generation gap
  (A7.4 SAY -> A10.9 CALL; 540 lines). Benchmark SLA fix A17.8-19.8 (TL:373, 436). Late correctness patches on refund
  categories (A26.7, A27.6). Ended A34.2 with "done" (TL:805) after its END "no remaining fixes. Parked pending
  unanimous same-hash receipts" (TL:780).
- **a3** (59 calls, 8 commits, 23 posts). Owned app.py dispatcher, auth, HTTP API/OpenAPI, CLI, browser UI, smoke,
  Chrome capture script, README, demo. First app commit A9.6 (3,206 insertions incl. generated OpenAPI). UI fixes from
  a1 reviews (A22.9, A27.2), why-panel polish from a2 suggestion (A30.3). Ended A34.2 after "All three peers posted
  matching END approvals" (TL:801).
- No agent ended early; all three ended within 0.4 min of each other after a unanimous END on the same sha.

## 4. Coordination costs
- Direction collision at claim time: a2 initially claimed a1's direction (TL:64 vs TL:49); a1 had to post twice to
  get a2/a3 to differentiate (TL:72, TL:105). Cost < 1 min.
- Draft/rank overhead: ~2 min building throwaway drafts + ~1.1 active min ranking (each agent ran/captured all three
  drafts, e.g. a1 Chrome screenshots TL:184). Drafts did not shape the product beyond the "audit/receipts" emphasis;
  the 40-line winning draft was merged verbatim and survives as dead code `drafts/a1.py` (judge penalty).
- Duplicate seam report: a2 asked a1 at A16.8 to strip REFUND markers (TL:355) that a1 had already fixed at A14.1
  (c5b33e5); a1: "refund merchant strip already on main c5b33e5 ... before your later request; pull it" (TL:392).
- PR.md edit collisions: a3 edited its ledger lines while a1 consolidated (TL:541); a1 hit a rebase conflict
  "consolidating PR ledger hit conflict from a2/other PR update" (TL:588). Resolved without force-push (TL:622).
- No product work left on branches; no code merge conflicts reported; no repeat END votes (single round).

## 5. Penalty -> cause map
| Penalty | Cause in log |
|---|---|
| Dense semicolon code (code 6/5) | Each owner wrote whole modules in single heredoc calls after long silent generation (a2 domain.py A7.4->A10.9, 540 lines in one `cat > ... <<'PY'`, TL:~ A10.9; a1 common.py "reusable strict primitives" TL:249). No reviewer ever commented on readability; all seam reviews were behavioural. No visible prompt cause. |
| Re-quoted + trailing-whitespace file quarantined | a1 chose `csv.reader(..., strict=True, skipinitialspace=True)` (delivered `plugins/common.py:59`; written A8.8, TL:249). a1's staged test covers "requoted/reordered/BOM redownload" (TL:276) but never the combination "space after closing quote". Brief lists "trailing whitespace and re-quoted fields" separately; tests treated them separately. Never claimed/planned as a combined case. |
| CSS-bar charts only | Drafts' "budget bars" (a2, TL:131) became the chart concept; a1 flagged "Reports comparison/recurring chart ... all £0 bars" and "Budget view currently JSON only" (TL:470, A22.5); a3 fixed to "readable tables, budget bars" (TL:494). Nobody proposed SVG charts. PR ledger line 38 marks "budget charts" DONE. |
| No browser manual-pair form | Ledger line 21 marks "confirm/reject/manual pairing" DONE via finance/integration tests (API). UI review checks (14 capture states, TL:594) did not include a manual-pair action. Coarse ledger line hid the UI gap. |
| Recurring report noisy on real data | Recurring only verified on synthetic benchmark ("recurring 1.226s (3 detected)", TL:436); a1 noted "0 actual refund candidates" for real data (TL:459) but nobody inspected real recurring output. |
| Leftover `drafts/a1.py` | C1 protocol: winner's draft is merged to main as the base (TL:186); never deleted. |
| DESIGN.md references PR.md | PR.md is removed by the judging anonymiser (RUBRIC.md); artifact of the protocol, not of the run. |

## 6. Decision points
1. **A2.9, a1 exhaustive inventory** (TL:104): every malformed row and the 12 TFR pairs known before any product code;
   this fed dedup/quarantine correctness and the honest "0 real refunds" claim the judges verified.
2. **A5.5, unanimous rank for a1 + immediate contract split** (TL:184-195): clean three-way module ownership
   (ingestion / finance / app+UI) agreed within 1.7 min; no duplicate building afterwards.
3. **A9.3-11.2, a1 discovers and fixes Kiwi regenerated refs** (TL:254, 276): avoids the ~56-row Kiwi double count
   that a judge flagged as severe in E1-T4b-C2-r2.
4. **A13.0-25.3, continuous cross-module seam review** (TL:300-550): a1 caught ~8 integration bugs (CLI report kind,
   imports never categorised, £0 chart bars, UI null-target toast) that each would have been judge-visible.
5. **A28.4, freeze decision** "avoid churn after" with wall-clock framing "hard cap03:36 UTC currently02:46" (TL:632):
   final 6 active minutes went to verification/docs; residual UI/CSV gaps not pursued.

## 7. Failure-mode tags
- NONE dominant (no collapse, no premature end, unanimous single-round END).
- WALLCLOCK_RUSH (mild, 2): a1 plans against wall time "Need final ledger by ~03:20 UTC (hard cap03:36)" (TL:404,
  A18.5) and "hard cap03:36 UTC currently02:46 so enough review time, but avoid churn" (TL:632, A28.4). At A28.4 only
  28 of 120 cap minutes were active, but 70 wall minutes had elapsed. Effect: freeze declared at ~A28 with gaps open.
- SELF_REFERENTIAL_VERIFICATION (mild, 2): recurring verified only as "3 detected" on synthetic data (TL:436);
  ledger items closed on tests the owners wrote (e.g. re-download variants tested one quirk at a time).
- COARSE_LEDGER (new: ledger lines bundle several brief capabilities, so a missing sub-capability is marked DONE)
  (1): ledger line 21 "confirm/reject/manual pairing" DONE while the browser has no manual-pair form.
- DRAFT_RESIDUE (new: throwaway draft code merged and shipped) (1): `drafts/a1.py`.
- DUPLICATE_WORK (minor, 1): refund-marker request TL:355 after fix c5b33e5.
- MERGE_CONFLICT (minor, 1): PR.md ledger rebase TL:588.

## 8. Time accounting (estimated, active min; run span ~34.5)
| Agent | Building | Coordination (board/contract/ledger) | Reading/reviewing others | Testing/verification | Idle/waiting |
|---|---|---|---|---|---|
| a1 | ~14 (draft 1.5, db/ingestion/plugins 6, docs/summary 6.5) | ~5 (36 posts, PR ledger consolidation 2) | ~5 (drafts 1, seam reviews of domain/app/UI 4) | ~8 (21 test/smoke/capture calls; VERIFY) | ~2 (end parking) |
| a2 | ~15 (domain.py 4, benchmark/SLA 4, fixes 7) | ~3 (25 posts) | ~3 (drafts 1, UI/visual review 2) | ~10 (15 test/bench calls; final validation) | ~3 |
| a3 | ~16 (app/server/CLI 4, UI 7, smoke/capture/demo/README 5) | ~3 (23 posts) | ~3 (drafts 1, seam review 2) | ~9 (19 test/smoke/capture calls) | ~3 |
Note: the per-agent "idle gaps" in the timeline header (a2 A7.1+3.8, a3 A10.2+3.1, a1 A14.4+3.6) are long single
generations of whole modules, i.e. building, not idling.
