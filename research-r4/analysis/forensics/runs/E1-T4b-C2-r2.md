# E1-T4b-C2-r2 (arm C2: spine + acceptance checks, task T4b budget book)

Sources: timeline `timelines/E1-T4b-C2-r2.md` (TL), judges `judge/E1/E1-T4b-C2-r2.j1.md|j2.md`, `origin.git`,
`results/E1-T4b-C2-r2/delivered/`.

## 1. Outcome
- Score **6.8** (j1 6.3, j2 7.3). j1: cov 7 / corr 6 / design 7 / rob 6 / code 5 / ux 6. j2: 8/8/7/7/6/6.
- Severe (j1): "Kiwi overlapping annual exports double-counted (~56 rows) because changing 'ref NNNN' suffix is part of
  dedup identity; undetected by e2e reconciliation and DATA_FINDINGS"; "Reformatted re-download with trailing whitespace
  after quoted fields is wholly quarantined instead of deduplicated" (j2 found the same: "all 365 rows to quarantine").
- Other penalties: "code is very dense ... semicolon-joined statements" (both); rule grammar AND-only, "no OR/NOT" (both);
  "Budgets are set one month at a time", "Undo only covers category changes", "UI was not browser-tested" (j1);
  job-interrupt test "closes and reopens the book rather than killing the process" (j2); re-imports re-add malformed rows
  to quarantine (j2); "docs overall are thin", worked plugin example in PARSERS.md (j2).
- Delivered: ~1,400 lines Python product (finance.py 409, categorisation.py 152, ingestion.py 148, app.py 124, ...;
  123 KB), app.js 37 lines / 14 KB (dense), ~636 lines of tests (13 core + 29 acceptance = 42 tests). j1: "2,160 lines,
  167 KB" total.
- Active 24.6 min (run span; result.json active_min 33.8, wall 136 min), 12.5 M input tokens, 25 commits, all on main
  (no draft branches).

## 2. Phase timeline (active minutes)
| Phase | A | What happened |
|---|---|---|
| Read brief, claims | 0.3-1.3 | a1 "CLAIM SPINE a1" A0.7 (TL:63); a2 claims ledger + ingestion acceptance A0.8/1.1 (TL:67,83); a3 claims API/scope acceptance A1.0 (TL:79). a1 posts contract A1.3 (TL:90). |
| Ledger + acceptance (no product code) | 1.1-5.3 | a2 ledger R01-R40 0941706 A1.6 (TL:100); a2 data-scan FACT A2.2 (TL:120); a2 oracle + ingestion acceptance b330e8d A4.1 (TL:160); a3 finance acceptance e7da835 A4.2 (TL:169), API/UI acceptance 7dba947 A5.3 (TL:220). |
| Spine | 0.7-4.8 | b0fbd6d "SQLite application spine" 611 lines A4.1 (TL:162); "SPINE DONE" A4.8 (TL:197). Spine took ~4 active min, not 12. Ownership re-negotiated 3x A4.1-5.3 (TL:164,184,193,222). |
| Build | 4.8-13.1 | a1 rules/jobs/undo 6740d75 A7.7 (TL:247); a2 six plugins 902eeeb A8.0 (TL:254) + provenance/revert tests 2d3a3c4 A11.3; a3 finance 35f4b00 A12.5 (TL:302); a1 UI 39cef58 1,824 lines A12.8 (TL:310); a2 HTTP acceptance f899c99 A13.1. |
| Wall-clock wrap trigger | 14.0 | a1: "Time checkpoint ~30min to 120m hard cap. Need wrap documentation/benchmarks/real summary now" (TL:350). |
| Docs/benchmark/fixes + cross-check | 14.0-19.9 | benchmark 04ef9f3 A15.8; docs 15bb9a4 A17.0; a3 UI seam reviews A16.9/18.0 (TL:401,450); a1 fixes JS syntax error A19.0 (TL:478); summary/starter rules e485143 A19.2. |
| "Cap passed" freeze | 18.8-19.4 | a3 "Wall clock now14:36 vs start12:34, hardcap reached" (TL:473); a1 "Clock jumped to14:37 (past120m cap); must wrap ... stop new scope. Proposed migration4 ... DESCOPED" (TL:478); a2 "No more feature build" (TL:489). |
| END vote 1 | 20.8-22.1 | a1 END 6bb49cd A20.8 (TL:559), a2 END A21.0 (TL:570); a3 withholds for accountant `why` scope leak A22.1 (TL:588). |
| Fix + END vote 2 | 22.4-24.2 | a1 redaction 9dfad5d A22.6, a2 regression dd7175b A23.0, freeze d9dc3e0 A23.7 (TL:640); END x3 A24.1-24.2 (TL:663,667,674). |
| Turn ends | 24.4-24.6 | a3 A24.4, a1/a2 A24.5, root A24.6 (TL:683-695). |

## 3. Per-agent account
- **a1** (spine owner, then rules/jobs/conflicts/undo, HTTP server, UI, CLI, DESIGN/README/API): spine A0.7-4.8,
  categorisation A4.8-7.7, UI/server A8-12.8, docs/fixes A13.7-20.0, final review/redaction fix A20-24.1. Ran the
  wrap-up from A14.0 on a wall-clock reading. TURN_END A24.5: "Completed on `origin/main` at `d9dc3e0`; all three peers
  approved that commit. - 42 tests pass ... Python 3.12 was unavailable" (TL:688).
- **a2** (ledger, data scan, ingestion oracle + acceptance, six plugins, quarantine/revert, HTTP acceptance, import
  summary, starter rules): acceptance A1.6-5.0, ingestion A5.0-11.3, HTTP acceptance A11.8-16.6, summary A16.6-19.2,
  verification/END A19.2-24.2. TURN_END A24.5 (TL:689): "Real imports reconcile: 5,480 transactions, 252 duplicates,
  six quarantined rows, 12 transfer pairs."
- **a3** (finance acceptance, then finance.py: matching/FX/budgets/reports/exports/backup, benchmark, sample rates,
  FINANCE.md, cross-review): acceptance A1.0-5.3, finance A5.3-12.5 (one 485-line heredoc, gap A5.7+5.8 is generation),
  benchmark/docs A13.1-16.3, cross-review A16.3-22.4 (found the only real bug fixed at the end: accountant scope leak
  A22.4 "Scope repro confirmed", TL:599). TURN_END A24.4 (TL:683).
- All three ended only after a unanimous END on the latest main: no PREMATURE_END in the protocol sense. The END was
  reached early because all three believed the 120 min cap had passed (see section 6).

## 4. Coordination costs
- Ownership churn: four division posts crossed between A4.1 and A5.3 ("Correction to my delayed previous post", TL:184;
  "Our cross-posts crossed", TL:193; "ACK FINAL confirmed directly", TL:222). ~1 active min, no lost code.
- Merge conflict: a2 and a3 both created `test_http_acceptance.py`; a2 renamed his to `test_http_adversarial.py`
  A13.7-14.3 (TL:360). Small DUPLICATE_WORK: a3 had claimed HTTP acceptance at A1.0 then moved to finance; a2 picked it
  up at A11.8 "a3 earlier claimed but finance ownership took priority" (TL:296).
- Seam bugs found by cross-check: CLI admin double json.loads (a2, A13.1 TL:329), backup inside BEGIN IMMEDIATE (a3,
  A12.9 TL:318), UI `missing_rates` vs `missing_count` (a3, A16.9), JS syntax error (a1 node --check, A19.0), wrong
  rates path in README (a3, A18.6), accountant `why` leak (a3, A22.1). All fixed on main.
- Re-vote: one (END 6bb49cd voided by redaction fix), ~2 active min. Plus "doc count churn" (40 vs 42 tests) A23.2-24.1.
- Dropped: migration4 index (a1 proposal A18.7 TL:463) DESCOPED A19.0 because of the clock. Nothing left on branches.

## 5. Penalty -> cause map
- **Kiwi overlap double count.** a2 saw the cue at A2.2: "Kiwi comma quoted descriptions carry , ref ####" and
  "No ... description changes ... in actual data" (TL:120). The "independent" oracle (b330e8d,
  `ingestion_oracle.py`) keys rows on `(account, date, desc, amount, currency)` with the full description, so it too
  treats different `ref` suffixes as distinct. The test's expected totals were not derived from the brief but pasted
  from the oracle's own output: A4.0 "Fixing canonical kiwi tests" then a script that replaces the placeholder with
  `str(sum(x['rows'] for x in i))` (TL:158-160). a2 then wrote the importer with the same identity ("Identity =
  hash(account,date,minor,currency,normalized description)", A6.7 TL:235) and reported "Data totals match oracle"
  (A8.0 TL:256). Same author, same assumption, test passes -> SELF_REFERENTIAL_VERIFICATION. No one else ever checked
  Kiwi dedup (0 Kiwi dedups in IMPORT_SUMMARY went unremarked; a3 only checked Kiwi FX wording A17.0-17.4).
- **Trailing whitespace after closing quote quarantined.** The acceptance test covered whitespace inside quotes
  (`"SHOP "`, test line 80) and `csv.QUOTE_ALL` re-quoting, not `"x" ,`. Requirement R04 marked "DONE 902eeeb + ingestion
  detail tests". Check written from a narrow reading of the brief; not caught.
- **Dense code / thin docs / AND-only grammar / per-month budgets / undo only for categories.** No visible discussion;
  these are build-out depth. Building ran only A4.8-13.1 (~8 active min per agent) before the wall-clock wrap at A14.0
  switched everyone to docs/verification. Plausibly caused by the short build window (inference).
- **Job-interrupt test reopens instead of killing.** No visible discussion; a1's "Six core tests pass" A7.7 was accepted.
- **UI not browser-tested.** a1 planned "headless Chrome visual check" A18.0 (TL:446); dropped and "visual browser
  automation limitation explicit" A20.5 (TL:548) under the clock rush.

## 6. Decision points
1. A2.2-4.1: a2 declares "No ... description changes" and freezes oracle numbers from the oracle's own output
   (TL:120,158-160). Locks in the Kiwi double count and makes the e2e test blind to it.
2. A4.8: SPINE DONE after ~4 min with a contract-first spine; build parallelised cleanly (positive point).
3. A14.0: a1 reads the wall clock (22:03 Taipei = 90 wall min, 14 active) and announces "~30min to 120m hard cap. Need
   wrap documentation" (TL:350). Build phase ends here.
4. A18.8-19.2: all three declare the cap passed ("hardcap reached" TL:473, "past120m cap" TL:478, "No more feature
   build" TL:489); migration4 and browser check dropped. The run then converges to END in 5 min.
5. A22.1: a3 withholds END for a real scope leak (TL:588) -> fixed. The only cross-check catch that changed product
   behaviour; cross-check never looked at dedup correctness on real data.

## 7. Failure-mode tags
- **WALLCLOCK_RUSH** x3 agents (TL:350, 473, 478, 489, 631 "user120min cap already exceeded while waiting/scheduling").
  Main reason the run ended at A24.6 of a 120 min budget. VM freezes visible at A2.9->3.3 (20:36->21:11), A11.2
  (21:38), A13.6 (22:02), A18.6 (22:36).
- **SELF_REFERENTIAL_VERIFICATION** x1 major: ingestion oracle expected values pasted from its own run, same author as
  importer (TL:158-160, 256). Also e2e "5738=5480+252+6" (TL:398) checks internal consistency, not dedup truth.
- **SCOPE_SHRINK** x2 (explicit, documented): migration4 DESCOPED (TL:478), browser automation DESCOPED (TL:548).
- **DUPLICATE_WORK** x1 minor (two HTTP acceptance files, TL:360).
- **MERGE_CONFLICT** x1 minor (same file, A13.7).
- **REVIEW_LOOP** x1 minor (one voided END + count-only doc churn, TL:631-663).
- New tag **ORACLE_BLINDSPOT_SHARED** (check author = builder of the same part, so a misread of the data is encoded in
  both check and product): the Kiwi case.
- Not present: PREMATURE_END (unanimous END), INTEGRATION_LOSS, IDLE_PEER, CAP_HIT, PROVIDER_ERROR.

## 8. Time accounting (estimates, active min, run span 24.6)
| Agent | Building product | Acceptance/tests | Coordination (board, ownership) | Reading others' work / review | Testing/verify | Idle/wait |
|---|---|---|---|---|---|---|
| a1 | ~13 (spine 4, rules 3, UI 5, fixes 1) | ~1 | ~2 | ~2 | ~2 | ~3 (END waits A20.8-22, A23.2-24) |
| a2 | ~6 (ingestion) | ~9 (oracle, HTTP acceptance, regressions) | ~2 | ~1 | ~3 | ~2 |
| a3 | ~9 (finance 7, benchmark/rates 2) | ~4 | ~2 | ~4 (UI/doc/scope seams) | ~2 | ~2 |
Product code vs acceptance: ~1,400 lines product Python + 1.8 k UI commit vs ~636 lines tests; of the 42 tests, 29 are
"acceptance". Roughly 30% of peer effort went to writing checks, ~45% to product, rest docs/coordination/verify.
