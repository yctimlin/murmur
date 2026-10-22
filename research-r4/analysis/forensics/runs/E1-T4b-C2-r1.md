# E1-T4b-C2-r1 (T4b budget book, arm C2 = spine + acceptance checks + END quorum)

## 1. Outcome
- Score **7.2** (j1 7.0, j2 7.4; both guess "team"). Sub-scores j1/j2: coverage 8/8, correctness 7/8, design 7/7,
  robustness 7/7, code 6/6, ux 6/7.
- Judges' top penalties:
  - j1 severe: "Recurring/subscription report detects nothing useful on the real data (only an internal transfer),
    despite Netflix/Spotify charges present" ("The synthetic test passes, but the feature isn't useful on this book").
  - j1+j2 code: "dense one-liners joined with semicolons hurt readability" / "about 3k very dense lines".
  - j1 UX: "the bar chart is the only chart, built from CSS divs"; j2: quarantine fix "means typing raw JSON into a
    `prompt()` box".
  - j1: card accounts exported as `Assets:` in the ledger; `next_winner` repeats the winner when a manual choice wins.
  - j2: duplicate quarantine entry on reformatted re-import; rejected match returns as "proposed" after
    revert+re-import; transfers not excluded from recurring report.
  - Python 3.12 unverifiable (only 3.13.5 installed; honestly DESCOPED as R01).
- Positives judges verified: 5738 = 5424 + 308 + 6 reconcile, reformatted re-download imports 0 new rows (j2), 409
  conflicts, accountant scope on every endpoint, backup/restore hash-identical, kill -9 job resume, 250k reports < 1 s.
- Delivered: `budgetbook/` 3053 lines of code (.py/.js/.html/.css); product Python 2061 lines (excl. tests/acceptance),
  static UI 63 lines (app.js 45 dense lines). 49b3c2b adds 4175 lines, mostly generated `openapi.json`.
- Active 31.9 min span (result.json active 42.63, wall 120.75), 18.3M input tokens, 31 commits, all on `main`
  (no draft branches; refs: only `main fcfaf11`).

## 2. Phase timeline (active minutes)
| Phase | A-range | Who / what |
|---|---|---|
| Read brief/prompt | A0.1-0.9 | all |
| Claims | A0.9-1.6 | a1 `CLAIM SPINE` (A0.9, TL:67); a3 acceptance/data inventory (A1.1, TL:78); a2 acceptance + ledger (A1.2, TL:81); module ownership settled A1.5-1.6 (TL:95, 98) |
| Data study (a3) | A1.4-2.9 | full-row census, `CRITICAL FACT` Kiwi `ref ####` regenerates per export (A2.1, TL:112); source_oracle 5738=5424+308+6 (A2.9, TL:132) |
| Acceptance writing (a2, a3) | A2.2-4.4 | a2 ledger R01-R41 + finance acceptance b55a8d6 (A3.1), HTTP acceptance a07d0b9 (A4.1); a3 oracle + ingestion acceptance + DATA_FINDINGS 63d2f70 (A4.2) |
| Spine (a1) | A0.9-4.3 | 6811d80 "13 files, 390 insertions" at A4.0; `SPINE DONE` A4.3 (TL:168) - 3.4 min, not 12 |
| Contract alignment | A4.5-5.1 | a1 FACT field names (TL:184); a3 adapts acceptance spellings 5b082c6 (TL:206) |
| Build | A5.0-14.4 | a3 parsers/ingest 14e531b (A8.0), finance 0750c4d (A13.0); a1 categories/jobs/undo/budgets c3178c1 (A8.9), bench/schema/migrations e1c272e (A11.2); a2 web/UI 9edfb03 (A9.4), OpenAPI/scope/smoke 49b3c2b (A13.3) |
| Cross-check + hardening | A13.7-26.1 | scope leaks found by a2's exhaustive scope test (A13.7, TL:345) and a1 review (A15.7, TL:382); FX rounding seam (A22.1); monotonic tx IDs migration4 (A22.7-25.1); docs/IMPORT_SUMMARY (A20.7) |
| Ledger close + final verify | A26.1-30.3 | a2 ledger DONE (A26.7, TL:688); `~27min before120min cap` (A27.4, TL:707); final UI polish fcfaf11 (A29.8) |
| END votes | A31.1-31.2 | a2, a3, a1 `END fcfaf11` (TL:852, 857, 861) - one round, no re-vote |
| Turn ends | A31.7-31.9 | a3, a2, a1, root |

## 3. Per-agent account
- **a1 (spine owner; categories/rules/learning/jobs/undo/budgets/benchmark/migrations/docs).** Spine 390 lines in
  3.4 min. Then the largest product commit c3178c1 (530 lines, A8.9), e1c272e (494, A11.2), docs/verify a44d9c7.
  Coordination: proposals (A1.3, 1.5, 7.6), cross-checks of finance (A15.7 refund-scope leak) and UI (A17.0 month
  format, comparison chart zeros), core safety change (A22.7). TURN_END A31.8: "done" (after `END fcfaf11` A31.2:
  "whole-result review complete ... 54 tests ... 0 JS exceptions").
- **a2 (ledger + finance/HTTP acceptance, then auth/web/UI/OpenAPI/smoke, PR.md).** 272 lines of acceptance A2.2-4.1,
  UI 262 lines (A9.4), OpenAPI+scope+smoke (A13.3), Chrome capture tool (953 lines, 7dbd67e, A16.0) - spent
  ~A12.6-20.2 getting browser capture to work (TL:305-498). UI itself stayed 63 lines. TURN_END A31.7: "all three
  peers approved the same commit ... Python 3.12 was unavailable".
- **a3 (data inventory + ingestion acceptance, then plugins/ingest/finance: matching, FX, reports, export,
  backup).** Best data study of the run (Kiwi ref instability A2.1, six malformed rows A1.9). Built ingest (A5.2-8.0)
  and finance incl. `recurring()` (0750c4d, A13.0, single 328-line commit). Later: FINANCE.md, PLUGIN_GUIDE,
  IMPORT_SUMMARY, FX rounding fix, exclusivity of transfer/refund. TURN_END A31.7: "Completed ... all three peers
  approved that commit".
- No idle peer; a3 posted "Pending SPINE DONE" at A5.1 (TL:208) though SPINE DONE was at A4.3; a2 nudged it at
  A6.3 (TL:221) - ~1-2 min lost.

## 4. Coordination costs
- Duplicated work: none in product code (clear ownership from A1.5). Acceptance split overlap (a2 and a3 both
  initially claimed "acceptance/data investigation", resolved A1.6, TL:98).
- Merge conflicts/rebases: none visible; all work direct to `main` with `pull --rebase`.
- Integration loss: none (no branches besides main).
- Contract friction: acceptance written "from the brief" used different field names; a3 had to "adapt acceptance
  spelling" (5b082c6, A5.1) and later fixed a wrong check ordering ("Acceptance correction (not product bug)", A20.9,
  TL:515).
- Re-verification load: full verify+benchmark run by a1 (A20.9, A28.6, A30.5), a3 (A26.0, A28.9, A29.6), a2 (A27.7,
  A31.1) - ~7 full-suite runs in the last 11 min.
- Review loop: none; single END round.

## 5. Penalty -> cause map
| Penalty | Cause in log |
|---|---|
| Recurring report useless on real data (Netflix/Spotify missed) | R20 implemented by a3 in one finance commit (0750c4d, A13.0). Ledger marks "R20 DONE 5095428; recurring cadence, stopped and price-change test" - a synthetic unit test (`tests/test_finance.py:84`). No acceptance check covers recurring (acceptance files: finance 4 tests on dedup/matching/backup/format, HTTP 3 tests, ingestion 3 tests). In the real data NETFLIX appears ~2-3x per month per account at random dates (e.g. visa_gold_2024: 01-09, 01-21, 01-25), so the median-interval cadence filter (25-35 days, regularity >= 0.7) rejects it. a3 knew at A1.9 that real data has only ten merchants (TL:108) but nobody ran the recurring report on the real book; all "PASS" posts list only recurring *timing* on 250k (TL:422, 578, 721). |
| Dense semicolon code | Authoring style: product written via Python heredoc patches (`p.read_text().replace(...)`, A27.2 TL:697) and large single-shot commits (530, 494, 328 lines). No reviewer comment on readability anywhere in the log. |
| Minimal UI / one CSS chart / raw-JSON prompt | UI owner a2 spent ~A12.6-20.2 building a Chrome capture harness (953 lines) rather than UI; UI remains 63 lines. Seams found late by a1 (A17.0 "Comparison chart values currently fallback ... =>0") and a3 (A28.2 "Review queue displays only transaction IDs") were patched minimally (fcfaf11, 9 insertions). |
| Cards as `Assets:` in ledger; `next_winner` repeats winner | No visible cause/discussion; not covered by any check. |
| Duplicate quarantine entry on re-import; rejected match reverting to proposed | Not tested; R10 check covers "unrelated revert", not revert+re-import of the same file. |
| Python 3.12 unverified | Environment (A2.2 TL:116); honestly DESCOPED R01. Not a team failure. |

## 6. Decision points
1. **A0.9 a1 claims SPINE**, and finishes in 3.4 min (A4.3) with "services have stubs". The spine was a thin
   contract; real build-out happened A5-14 in ~9 active minutes of parallel work.
2. **A2.1 a3 "CRITICAL FACT ... Kiwi overlapping rows regenerate `, ref ####`"** - the data study during the
   acceptance phase caught the dedup trap that sank C2-r2; j2's reformatted re-download imported 0 new rows.
3. **A1.6 module ownership by layer** (a3 all finance incl. reports): put recurring/reports, matching, FX, export,
   backup in one owner's single 328-line commit; reports got no second builder.
4. **A26.7-27.4 ledger declared complete** ("R02-33,35-37,39 DONE with test evidence") and a2's wall-clock framing
   "~27min before120min cap" (A27.4; actual active 27 of 120). From here only polish; END within 4 active min.
5. **A31.1-31.2 END quorum** on fcfaf11 with every check green - verification was "do our tests pass", not "does
   the recurring report find the household's subscriptions".

## 7. Failure-mode tags
- SELF_REFERENTIAL_VERIFICATION (1, central): R20 marked DONE on a synthetic test; acceptance suite (written in
  ~2 min each by a2/a3, A2.2-4.4) concentrated on ingestion/HTTP/backup and had no outside-in check for reports
  on real data. END posts cite only tests/benchmark/screens.
- WALLCLOCK_RUSH (1, mild): a2 A27.4 "~27min before120min cap" from wall time (94 wall min vs 27 active);
  followed by closing ledger and END at A31.
- SCOPE_SHRINK (mild): UI kept minimal (63 lines, one CSS chart) without DESCOPED note; R29 marked DONE.
- NEW: CHECK_COVERAGE_GAP - acceptance checks exist for some ledger items only, yet the ledger rule "DONE only when
  its acceptance check passes" was satisfied by unit tests. Count: >=1 (R20), likely R13-R18 too.
- PREMATURE_END: none in the protocol sense (ledger empty), but END at A31 of a 120-min cap.
- IDLE_PEER, DUPLICATE_WORK, INTEGRATION_LOSS, MERGE_CONFLICT, REVIEW_LOOP, CAP_HIT, PROVIDER_ERROR: none.

## 8. Time accounting (active min, estimate; span 31.9)
| Agent | Building | Acceptance/tests | Coordination (board) | Reading others / cross-check | Verify runs | Idle/wait |
|---|---|---|---|---|---|---|
| a1 | ~15 (spine 3.4, build 5-14, docs, migration4) | ~3 | ~3 | ~4 | ~4 | ~2 |
| a2 | ~6 (UI, OpenAPI, smoke) | ~3 (A2.2-4.1) + ~7 capture harness | ~3 | ~3 | ~5 | ~2 |
| a3 | ~11 (ingest, finance, fixes) | ~5 (oracle, acceptance, real E2E) | ~3 | ~3 | ~4 | ~4 (A5.1-6.3 wait, A30.0 "Waiting for countdown") |
Calls per 5-min bucket (a1/a2/a3): 0-5: 11/15/13; 5-10: 5/7/5; 10-15: 8/8/4; 15-20: 9/16/4; 20-25: 9/10/11;
25-30: 11/10/16; 30+: 5/5/6. Last third of the run is dominated by verification and docs.
