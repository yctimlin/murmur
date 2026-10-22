# E1-T4b-C1-r2 (T4b budget book, arm C1, score 7.275)

TL = `/workspace/r4/analysis/forensics/timelines/E1-T4b-C1-r2.md`

## 1. Outcome
- Score 7.275 (j1 7.3, j2 7.25). Both judges gave identical sub-scores: coverage 8, correctness 8, design 6, robustness 7,
  code 6, ux 7. Both guessed "team". Neither judge listed a severe defect.
- Judges' top penalties:
  - j1: "Whitespace after a closing quote: a field like `\"51.86\"  ` makes every row of the file go to quarantine";
    "`serve` crashes with an `AttributeError` ... instead of a clear error" (port already in use); "migration 5 re-runs
    the whole `finance_schema.sql`"; "normalisation is a hard-coded list of the ten merchant names"; OpenAPI spec has
    "generic response schemas and describes no request bodies"; "`draft.py` and `drafts/a2.py` (a mock server) are left
    in the package"; "`core.py` and `finance.py` pack several statements per line with semicolons".
  - j2: "Merchant names are hard-coded"; "migrations 4 and 5 re-read editable `.sql` files from disk"; refunds, FX and
    cross-currency transfers are "only exercised on fixtures"; "The code is hard to read"; "Prototype files are left in
    the delivery"; "the web charts are plain CSS bars"; the budget report took 1.93 s on the 250k book, close to the 2 s
    limit.
- Delivered tree on main `cfcc26d`: about 2,290 lines and 205 KB of product and test code (py/html/sql, drafts
  excluded). That is very dense: about 89 chars per line, 40 lines in core/finance/application are longer than 200
  chars, and finance.py contains 60 semicolons. Generated `openapi.json` adds 2,363 lines. Docs total 840 lines.
  42 tests pass.
- Active 34.0 min (result.json active_min 43.98 incl. root), wall 124.4 min. Input tokens 21.2M. 28 commits.

## 2. Phase timeline (active min)
| Phase | A | What |
|---|---|---|
| Read brief, claim draft directions | 0.2-1.2 | a1 "provenance-first" (TL:62), a2 "decision-first" (TL:78), a3 "collaboration-first" (TL:87) |
| Drafts | 0.6-4.7 | a2 pushes a 33-line mock dashboard at A2.0 (TL:96). a1 pushes six real parsers plus a workbench at A2.2 (TL:100). a3 pushes a 29-line static HTML at A4.5 (TL:161). |
| Contract negotiation, run in parallel with ranking | 3.2-5.3 | a2 proposes the schema (TL:129). a1 extends it and posts CONFIRMED (TL:154). a2 posts the Finance API (TL:158). a3 accepts and claims app/auth/API/CLI/UI (TL:183). |
| Ranking | 3.5-7.9 | a2 gives a preliminary vote for a1 (TL:138). a1 votes a3 first (TL:192). a3 votes a1 first (TL:195). Split vote, a1 asks a2 to break it (TL:229). a2's final vote is a1 at A7.9 (TL:236). |
| Integration of the winner | 9.7 | a1 pushes c1cff0a (draft plus durable core, which it had built locally while the vote was open, TL:228) and posts DONE (TL:266). a2 integrates finance at A10.3 (TL:291). PR plan and ledger d54b7df at A10.9 (TL:295). |
| Build | 9.7-25 | Ownership: a1 owns core, ingest, migrations and docs. a2 owns finance (rules, jobs, matching, FX, budgets, reports, benchmark). a3 owns app, auth, API, CLI, UI and smoke. Peers cross-review seams continually (TL:365, 385, 400, 406, 488, 577). |
| Final verification / freeze | 25.6-29.7 | a1: "actual clock now 07:41UTC, cap08:04UTC (~23min) ... No broad scope additions" (TL:634) |
| END rounds | 30.2-33.3 | Round 1: END 895909b from a3 and a2 (TL:753, 757). a1's quarantine fix voids it (TL:789). Round 2: END 5477154 from a2 and a3 (TL:808, 817). a2's match guard voids it (TL:824). Round 3: END cfcc26d from all three (TL:841, 857, 870). |
| Turn ends | 33.5-33.7 | All three peers end within 0.2 min of each other, then root at A34.0. |

## 3. Per-agent account
- **a1** (42 posts, 12 commits; most of the coordination load).
  - Built the draft with six parsers (A2.2), then the durable core: identity, provenance, revert and migrations 1-6.
  - Hardened the parser at A12.1, adding "Parser rejects malformed thousand-grouping/CSV quoting" (TL:353).
  - Wrote DATA_FINDINGS and IMPORT_SUMMARY at A18.2, DESIGN.md at A23.3, the crash-resume test at A25.1 and
    VERIFICATION.md at A27.0.
  - Coordination: wrote the PR plan and ledger, reviewed a3's and a2's seams (TL:365, 385, 577), and ran the UI in
    Chrome (TL:525).
  - TURN_END A33.6: "Completed on `origin/main` at `cfcc26d`; all three peers signed off." Reasoning in TL:870: "All
    three END votes now name cfcc26d; objective complete, ending turn."
- **a2** (31 posts, 11 commits).
  - Draft: an in-memory mock dashboard. It then wrote finance.py before the vote closed (A7.1 schema, TL:207) and
    landed it at A10.3: rules, learning, jobs, matching, FX, budgets and reports.
  - Later: 250k benchmark (A12.1), exact per-transaction FX (A20.6), richer generator (A24.5), match-ID sequence
    (A27.6) and the BEGIN IMMEDIATE guard (A32.2).
  - TURN_END A33.5: "done".
- **a3** (23 posts, 8 commits).
  - Draft: static HTML. Then built application/auth/server/CLI (15ea670, A11.2, +616 lines), and at A18.0 the UI,
    OpenAPI spec, API tests and smoke test (36ea144, +2656 lines).
  - Later: README and mobile fixes (A22.4) and refund scope (A25.9).
  - TURN_END A33.7: "All work is on `origin/main` at `cfcc26d`, with unanimous peer review ... Python 3.12 execution
    remains unverified".
- No agent ended its turn early. All three ended only after a same-head unanimous END.

## 4. Coordination costs
- **Drafts and ranking: about 7 active min (A0.6-A7.9) before main had any product code.** The cost was mostly
  hidden, because a1 and a2 kept building against the agreed contract while the vote was open (TL:207, 228). The three
  drafts covered disjoint layers (ingest / categorisation UI / collaboration UI), so the "ranking" really chose a1's
  core as the base and became a division of labour.
- **Split vote.** a1 voted for a3 and a3 voted for a1 (TL:192, 195), so the decision waited for a2 until A7.9
  (TL:229, 236).
- **Draft leftovers shipped.** a2: "Main now has my draft artifact too (review history)" (TL:291). a3: "plus retained a3
  draft" (TL:334). `draft.py` (a1's draft) also stayed. Nobody planned to remove them, and the judges penalised them.
- **Duplicate work and merge conflict.** a1 and a3 both shipped starter_rules.json and README setup. a1 reported: "push
  hit README/starter_rules add/add rebase conflict because a3 independently shipped same starter config" (TL:675).
  Resolved in about 1 min.
- **Cross-agent bug in the shared transaction boundary.** learn() committed on its own, which broke bulk atomicity
  (TL:365, 406, 488 FAIL). It took 3 posts and 2 commits to settle the ownership rule "app owns commit"
  (A12.7-A20.6).
- **Re-votes.** There were 3 END rounds and 8 END posts. Each void was caused by a late "small correctness gap" fix
  pushed after other peers had voted (TL:768, 824). This cost about 3 active min.
- **Branches.** Nothing stayed off main: the draft branches' content is on main.

## 5. Penalty -> cause map
| Penalty | Cause in log |
|---|---|
| Whitespace after a closing quote quarantines the whole file | a1's parser hardening at A12.1: "Parser rejects malformed thousand-grouping/CSV quoting" (TL:353). Strict quoting turned a reformatting variant into "malformed". The reformatted-re-download tests never included space-after-quote, and no one probed it. |
| Migrations re-read editable .sql and replay finance_schema twice | A5.3 a1: "a1 will execute finance_schema.sql as migration 4" (TL:186). A11.1 a2 asks for migration5 to replay the same file (TL:309). A13.0 a1: "migration5 that replays idempotent finance_schema.sql" (TL:370). These were contract shortcuts forced by schema changes while two agents built in parallel. |
| Hard-coded merchant list | a2's FACT: "descriptions are 10 named merchants" (TL:122). a1's Kiwi fix: "will use normalized merchant for Kiwi identity" (TL:170). The normalisation was fitted to observed data in a1's draft parser module and never generalised. |
| Dense, semicolon-packed code | No discussion in the log. The code was written in large heredoc bursts (e.g. a3 +2656 lines in one commit, TL:457). It reflects a terse style under perceived time pressure. No code-readability review happened, because all reviews targeted correctness seams. |
| Leftover draft files | This is a C1 mechanism artifact: draft branches were merged as "review history" (TL:291, 334). |
| Thin OpenAPI spec | a3's spec plus parity test checks paths and methods only (TL:443 "OpenAPI parity"). This is SELF_REFERENTIAL_VERIFICATION in a mild form: the test proves the spec matches the routes, not that it documents them. |
| Port-in-use crash in `serve` | No visible cause. Never exercised: every agent used its own free PORT_BASE. |
| Refund / FX / cross-currency only on fixtures | Data limitation, noted early: a2 "No transfer marker in Eurobank real data, so cross-currency matching must use designed fixtures" (TL:122). It was documented honestly. |
| Budget report 1.93 s (j2) | a2 made the benchmark richer at A24.5 ("Reports max1.5196s", TL:599), which left little headroom. |

None of the penalties were a claimed feature that was later dropped: the ledger had no DESCOPED items.

## 6. Decision points
1. **A2.2, TL:100.** a1's "draft" was already the real product core (six parsers, multiset dedup, reconciliation), not a
   mock. This decided the winner and gave main a solid ingestion base.
2. **A3.2-5.3, TL:129-186.** The schema and Finance API contract were agreed before the vote. That let the three
   peers build disjoint layers in parallel. It also baked in "finance_schema.sql as migration 4", the later design
   penalty.
3. **A7.9-10.9, TL:236-295.** The tie was broken and the winner, a2's finance code and the ledger all landed within
   3 min. After that there was little idle time.
4. **A25.6, TL:634.** a1 read wall time ("cap08:04UTC (~23min)") and declared "No broad scope additions". At that
   point only about 26 of 120 active minutes had been used. From then on all effort went to verification, docs and
   micro-fixes, not to readability, migrations or merchant generalisation.
5. **A30.9, TL:782.** "Clock jumped to08:05UTC (hard cap reached)". Agents believed the cap had passed and drove
   straight to END.

## 7. Failure-mode tags
- **WALLCLOCK_RUSH ×3** (TL:504 "~57 minutes cap remaining" at A19.8; TL:634 at A25.6; TL:782 at A30.9). The run
  ended at about A34 of a 120-min monotonic cap. This is the main reason quality polish never happened.
- **DRAFT_LEFTOVER** (new tag: draft or prototype artifacts are merged into the product tree and shipped) ×3 files
  (draft.py, drafts/a2.py, drafts/a3). Penalised by both judges.
- **DUPLICATE_WORK ×1** (starter_rules/README, TL:675).
- **MERGE_CONFLICT ×1** (same event as above).
- **REVIEW_LOOP ×2** voided END rounds (TL:789, 824). Mild.
- **SELF_REFERENTIAL_VERIFICATION ×1, mild.** The OpenAPI parity test covers paths only. The e2e tests reconcile what
  the importer produced. The space-after-quote re-download variant was never tested.
- **PREMATURE_END 0, IDLE_PEER 0** (a3 had one gap of 3.1 min at A1.4), **INTEGRATION_LOSS 0, CAP_HIT 0,
  PROVIDER_ERROR 0.**

## 8. Time accounting (estimate, active min, of about 33.5 each)
| Agent | Building | Coordination (board/contract/ranking) | Reading others' work / review | Testing / verification | Idle / waiting |
|---|---|---|---|---|---|
| a1 | 11 | 8 | 6 | 7 | 1 |
| a2 | 15 | 6 | 4 | 7 | 1 |
| a3 | 16 | 4 | 4 | 7 | 2 |

Drafting and ranking took about 4-5 min per agent. a1's and a2's drafting time partly overlapped with real building.
END rounds took about 3 min per agent.
