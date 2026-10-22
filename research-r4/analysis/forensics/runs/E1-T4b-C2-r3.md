# E1-T4b-C2-r3 (arm C2, task T4b): 6.65

## 1. Outcome
- **Score 6.65** (j1 6.6, j2 6.7). Sub-scores: coverage 7/7, correctness 7/7, design 6/6, robustness 7/7, code 5/5, ux 6/7. This is the lowest of the five T4b C1/C2 runs analysed. Both judges guessed "single".
- **Judges' top penalties (quotes):**
  - j1: "the Python is about 1,800 lines packed tightly, with one-space indents and many statements per line"
  - j1: "Learning: it is just a count of manual choices per merchant"
  - j1: "one generic bar chart built from CSS divs, not 'a few charts'"
  - j1: "flags AIRBNB and Amazon as recurring 'candidates', which is noisy"
  - j1: "1,740 of 5,424 conversions used the fallback rate" (sparse rates file)
  - j1/j2: the transfer matcher is "debit × credit", which is O(n²) and never benchmarked
  - j2 severe: "Server smoke test hung for about 8 minutes and failed with a socket timeout on its first run; six later runs passed (intermittent)"
  - j2: "Match decisions are stored against transaction ids, so they are lost if the same file is reverted and re-imported"
  - j2: "Every re-import of a file adds another quarantine entry"
  - j2: "Recurring detection marks all 54 groups as 'candidate'"
  - j2: DESIGN.md is "short on the rejected alternatives"
- **What worked (both judges):** real import 5,424 / 308 dedup / 6 quarantined; reformatted re-download idempotent; revert; 409 conflict with both versions; accountant scope; backup/restore; ledger; migrations v1→v6. The Kiwi `ref ####` trap was handled.
- **Delivered on main 523fec5:**
  - Product Python: 1,307 lines / 94 KB, the smallest of the T4b C1/C2 runs (others 1,650–2,219 lines, 126–136 KB). Tests: 520 lines. UI: 25 KB (app.js 13.5 KB).
  - Seven docs: DESIGN, DATA_FINDINGS, DATA_POLICY, IMPORT_SUMMARY, OPERATIONS, PLUGIN_GUIDE, VERIFICATION.
- **Run figures:** active 42.1 min in the timeline span (result.json says 52.78; wall 140.8). 25.7M input tokens, the highest of the five. 29 commits, all on main, so there is no draft-branch loss.

## 2. Phase timeline (active minutes)
| Phase | A | What happened |
|---|---|---|
| Spawn | 0.0–1.4 | Root spawns a1/a2/a3 with `fork_turns:none` and waits 1 h (TL:25–41). |
| Board setup, everyone picks "acceptance" | 1.6–5.1 | a1 creates `tasks`/`findings` (TL:~60, 94). a2 posts "CLAIM a2: acceptance ledger + parser/data reconnaissance **while spine builds**" (A4.2, TL:77). a1 posts "CLAIM a1: acceptance checks ... no product code until SPINE DONE" (A5.1, TL:95). Nobody claims SPINE. |
| Triple data reconnaissance | 4.7–11.5 | All three independently scan every export: a2 TL:~110–148, a1 TL:~130–170, a3 TL:103–193. FACT posts at A9.3, A10.3 and A11.5 report the same 6 malformed rows and formats. A VM freeze sits inside this window (wall 10:49→11:06 at A5.6–6.2). |
| SPINE vacuum discovered | 10.2–12.9 | Peers message root and each other (payloads encrypted). a1: "CLAIM SPINE a1 (no prior SPINE claim on board)" (A11.7, TL:211). a3 meanwhile posts "a2 now taking SPINE" (A12.2, TL:237). a2 settles it: "a1 owns SPINE (confirmed direct)" (A12.9, TL:254). |
| Spine | 11.9–15.1 | a1 writes core/schema/CLI (244 lines, 64eeea1, A14.9) and posts "SPINE DONE ... Parsers rough, report naive" (A15.1, TL:313). The spine took 3.2 min. |
| Acceptance artifacts | 12.9–15.5 | a2: ledger plus plan, 59 lines (A12.9), then the independent oracle, 444 lines (A15.5, TL:318). a3: HTTP acceptance test, 132 lines (A13.2), plus matrix (A14.0). |
| Build | 15.1–26.4 | a1: rules, jobs, reports, budgets in **one 209-line commit** (A18.3, TL:379), then benchmark and starter rules (A20.3). a2: parsers, matching, FX, export, 576 lines (A21.4, TL:432). a3: API and UI, 286 lines (A21.6), then CLI/OpenAPI/workflow, 2,420 lines (A25.2, TL:516). |
| Cross-check and polish | 24.3–39.7 | Scope clamp (A24.3, TL:493). Bulk-version and FX caveats (A32.2–32.6). Job progress on revert (A33.0). Stale bulk (A34.0). Quarantine-correction dedup (A36.5, TL:833). Browser captures were run separately by all three (A29.7–38.2). VM freeze at A33.0–34.0 (wall 12:07→12:36). |
| END | 40.8–40.9 | One round, unanimous on 523fec5 (TL:955, 958, 961). |
| Turn ends | 41.5–41.8 | a1, a2, a3 (TL:990, 997, 1007). Root ends at A42.1. |

## 3. Per-agent account
- **a1** (93 calls): spine; rules, jobs, reports, budgets, benchmark, starter rules, migrations fixture; README/DESIGN; capture script; final VERIFICATION.
  - Before A11.7 it did only acceptance and reconnaissance, with no checks pushed.
  - TURN_END A41.5 (TL:990): "Pushed completed work to `origin/main` at `523fec5`. All three peers reviewed and approved that commit." It was a protocol-correct end after the END quorum.
- **a2** (96 calls): ledger; source oracle; all six parsers; matching, FX, exports; seventh plugin; IMPORT_SUMMARY; quarantine-correction fix.
  - It posted the decisive Kiwi FACT at A14.6 (TL:301): "identical date/merchant/amount rows are re-exported with DIFFERENT random `, ref ####` suffixes ... Dedup must remove decorative reference".
  - TURN_END A41.6 (TL:997), after the quorum.
- **a3** (96 calls): HTTP acceptance; auth/API/UI/smoke/OpenAPI; UI fixes; browser captures.
  - At A34.2 (TL:775) it saw a "recurring detection—18.48 seconds" benchmark regression, re-ran it, and recorded it as an "outlier" (A36.7, TL:845). The run coincided with the A33–34 VM freeze, so the wall-time measurement is likely a freeze artifact.
  - TURN_END A41.8 (TL:1007), after the quorum.
- **root** (25 calls): woken 9 times by peer `send_message` to `/root` (TL:166, 191, 215, 359, …). Each time it only ran `list_agents` and `wait_agent` again; there were no followups and no interference. Peers using root as a message target is unusual; other runs have 5–7 root calls.

## 4. Coordination costs
- **SPINE vacuum, 11.7 active min (28% of the run) with no product code.**
  - The C2 prompt says "The first peer to claim `SPINE` ... builds" and "While the spine is built, the others write no product code".
  - Each peer read itself as one of "the others": a2 at A4.2 ("while spine builds"), a1 at A5.1 and a3 at A11.5 all claimed acceptance work.
  - The vacuum was noticed only around A10–11.7 through direct messages, and a1 claimed SPINE at A11.7.
  - Solo, by contrast, had its ingestion core done by A5.5 (solo TL:40).
- **DUPLICATE_WORK: three full independent data inventories (A4.7–11.5)**, giving three overlapping FACT posts (TL:148, 170, 193).
  - The prompt asked for this as "study the input"; it was not divided.
  - Its one unique yield was a2's Kiwi `ref` FACT (A14.6).
- **Ownership confusion A12.2–12.9:** a3 posted "a2 now taking SPINE" while a1 had claimed it. It was resolved within 0.7 min, through about 10 encrypted direct messages (TL:205–260).
- **Triplicate browser verification:** a1, a2 and a3 each ran `budgetbook.capture` and viewed screenshots (A29.7, A34.3–35.2, A35.8, A36.7, A40.6). That is roughly 2–3 agent-min of repeated work.
- None of these occurred: merge conflicts of note, INTEGRATION_LOSS (everything on main), ignored messages, re-votes (a single END round).

## 5. Penalty -> cause map
| Penalty | Cause in log |
|---|---|
| Golfed/dense code (code 5/5) | Modules were written as one heredoc per file in single bursts: a1's 209-line rules/jobs/reports/budgets commit took 2.4 min after SPINE DONE (A15.9→18.3, TL:379), and a3 wrote app.js via `s.replace` patches (TL:552, 864, 885). No review addressed readability; every cross-check concerned behaviour. Same style in solo (code 5/6), so it is a model trait made worse by the compressed build window. |
| Learning is a vote count; suggestions only in `explain` | R13 was closed "DONE 25ba044 (rules/report/migration tests ...)" (PR.md:31) with six other items in one batch status edit by a1 (A36.6, TL:838). No acceptance check for R13 was written from the brief. **SELF_REFERENTIAL_VERIFICATION.** |
| Single CSS chart | R25 "Offline browser UI ... charts" was closed on "HTTP acceptance, every-route scope test and smoke" (PR.md:43). a3's HTTP_ACCEPTANCE matrix (A14.0) had no executable chart check; the captures were looked at, but nobody asked for more chart types. |
| Recurring report noisy (AIRBNB/Amazon; all 54 groups "candidate") | a1 built it inside the 209-line commit at A18.3. It was verified only by a synthetic `COFFEE` unit test (`tests/test_rules_reports.py:32`) and the 250k timing. Nobody ran the recurring report on the real book. Same pattern as C2-r1. |
| Sparse rates file, 32% fallback | No visible discussion. The fallback was disclosed (de9a5e6, A32.6), so the team chose disclosure over a denser sample file. |
| O(n²) matcher | a2's matching.py (A18.4, TL:382). The benchmark (R18) only covers reports, so the check measured what was built. No visible cause beyond that. |
| Intermittent smoke hang (j2 severe) | No visible cause in the log; all smoke runs in the log passed. The server uses `ThreadingHTTPServer` with `daemon_threads`. Likely environment or race; unverified. |
| Decisions keyed by transaction id lost on revert + re-import | No visible cause. a2's DONE (A22.0) claims decisions survive "re-run", and the tests cover unrelated-file revert only. |
| Duplicate quarantine entries on re-import | No visible cause. a2's A36.5 fix addressed corrected rows, not repeated broken rows. |
| Thin DESIGN alternatives | Docs were written A22.6 and A29.7–30.1 in short bursts; no review of DESIGN.md against the brief's "alternatives you rejected" requirement. |

None of the penalised features was ever DESCOPED: the ledger has 0 DESCOPED and 35 DONE lines. All were "done" at minimum depth.

## 6. Decision points
1. **A4.2–5.1 (TL:77, 95):** a2 and then a1 claim acceptance "while spine builds" instead of SPINE. This fixed an 11.7-min delay before any product code.
2. **A11.7 (TL:211):** a1 notices "no prior SPINE claim on board" and takes it. The build window starts at A15.1.
3. **A15.1 (TL:313):** an extremely thin spine ("Parsers rough, report naive") plus a layer split: a1 rules/reports, a2 data, a3 API/UI. Each owner then had about 11 min to build everything in its layer once (A15–26).
4. **A36.6 (TL:838):** a1 batch-marks R02, R03, R12–R18, R21 and R33 DONE on unit/benchmark evidence. Depth gaps in learning, recurring and charts were never re-opened.
5. **A40.8–40.9:** END quorum. Every peer's END cites tests, smoke, benchmark and captures passing, which is evidence that what exists works, not that each brief item is met in depth.

## 7. Failure-mode tags
- **SPINE_VACUUM** (new): under the spine protocol, every peer takes the "others" role and nobody builds the spine; product work is delayed until someone notices. ×1, A1.6–11.7, about 28% of the run.
- **DUPLICATE_WORK** ×2: triple data inventory (A4.7–11.5); triple browser capture review (A29.7–40.6).
- **SELF_REFERENTIAL_VERIFICATION** ×1 (central): R12–R18 and R25 were closed on unit tests, benchmark timing and screenshots. Acceptance checks existed only for data reconciliation (a2's oracle) and HTTP/auth/scope (a3), and these are the areas the judges praised.
- **SHALLOW_DONE** (new): a ledger item is marked DONE when a minimal implementation exists, with no depth criterion. ×3 (learning, recurring, charts).
- **Not seen:**
  - WALLCLOCK_RUSH: no cap or clock posts. This is the one T4b C2 run without it.
  - PREMATURE_END, IDLE_PEER, INTEGRATION_LOSS, REVIEW_LOOP, CAP_HIT, PROVIDER_ERROR.

## 8. Time accounting (estimated active min, span 0.6–41.8)
| Agent | Building product | Acceptance/tests | Recon (data) | Coordination | Reviewing others | Verify runs/captures | Idle/wait |
|---|---|---|---|---|---|---|---|
| a1 | ~12 (spine 3 + build 9) | ~2 | ~6 | ~4 | ~4 | ~6 | ~1 (incl. 1.0 before first call) |
| a2 | ~10 | ~5 (ledger, oracle) | ~7 | ~3 | ~4 | ~5 | ~1 |
| a3 | ~11 | ~4 (HTTP acceptance) | ~6 | ~4 | ~3 | ~6 | ~1 (start A1.4) |

Across the team, about 33 of about 120 agent-minutes went to product building (about 28%). The remainder went roughly as follows:
- about 19 to reconnaissance done in triplicate;
- about 17 to checks and verification runs;
- about 11 to coordination;
- about 11 to cross-review.

Solo spent most of its 32.7 min building.
