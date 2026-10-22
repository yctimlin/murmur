# E1-T3b-C2-r2 (T3b self-hosted CI platform, arm C2) — score 7.4

## 1. Outcome
- Score 7.4 (j1 7.3: cov 7, corr 8, design 7, rob 8, code 6, ux 6; j2 7.5: cov 8, otherwise same). No severe issues. Both guessed "single".
- Top penalties (quoted):
  - j1: "Sample pipeline: every job shares one lock, so the sample runs no jobs in parallel. Both matrix cells build byte-identical artifacts. The slow job lives in a separate `pipeline.slow.json`"
  - j2: "Corelib commit: docs is reported `skipped` and carries no artifacts, rather than being a cache hit with reused artifacts. Test 03 passes by accepting either status."
  - j2: "every job overrides the template's steps, so the template's `${matrix.package}` step is never used and the five job blocks are largely copy-pasted"
  - both: JSON-blob storage with full-table scans; "DAG" is a list; logs polled, not SSE; very verbose CLI; dense one-liner code. j1: "the `leases` table that DESIGN.md says v2 adds is never used"; "concurrent cancel/re-run test repeats only 8 pairs".
- Delivered: 37 code files, 3284 lines / 194 KB; tests 1283 lines, 53 tests (`python3.12 -m minici.selftest`, ~35 s). 27 commits, only `main`.
- Active 28.0 (run span 21.0), wall 116.5 (freezes A0.9->1.4 ≈25 min wall, A6.0->7.8 ≈20, A11.8->12.6 ≈29, A17.0->17.5 ≈25). Tokens: input 12.7M (uncached 0.45M), output 110K. Lowest active time of the four runs.

## 2. Phase timeline (active minutes)
| Phase | A | Who | What |
|---|---|---|---|
| Claims + contract | 0.8-2.1 | a1 SPINE (A0.8, TL:65); a1 API contract FACT A0.9; a2 ledger + scenarios; a3 scenarios | Split of the checks negotiated over crossed posts (A1.4-3.6) |
| Acceptance (no product code) | 2.6-4.3 | a3 `2baf5a1` A2.6 (scenarios 15-19, 257 lines), `daacb2a` A3.2 (import attacks/CSRF); a2 `420350e` A3.3 (ledger + harness + scenarios 1-12, 469 lines), `78066f6` A4.2 (13/14/20) | All 20 scenarios had black-box tests before or at SPINE DONE |
| Spine | 0.8-4.1 | a1 | `a6e28b0` A3.8 "Build MiniCI end-to-end engine, persistence, API, CLI and browser spine" (578 lines, 16 files); `SPINE DONE` A4.1 with file-ownership boundaries |
| Build | 4.5-11.3 | a1 engine/pipeline/process/triggers; a3 store/server/security/import/GC/plugins; a2 sample repo/CLI/dashboard/docs | a3 `901b888` A8.5, a1 `537247a` A8.5, a2 `2894048` A9.4 (sample + CLI + dashboard), a3 `ec4ccfb` A9.8 |
| Checks drive fixes | 8.7-14.1 | all | a1 "checks 05-08,10-11 pass via real server" A8.7; validator shadow bug found by 04/12/16 (A9.2); /repos path mismatch from 09 (A9.9); 39/40 at A12.8; "PASS full selftest main2006aed: all44 checks" A14.1 |
| Cross-check | 13.9-17.7 | a1 mostly | notifier orphan risk (A13.9), GC-vs-cancel race (A14.5), secret rotation race (A17.0), invalid git rev (A17.6); a3 archive timestamps (A17.7); a2 browser capture (A17.5) |
| Rush + ledger close | 18.1-18.9 | a1 drives | "TIME: current22:05UTC, task began20:12, hardcap~22:12. Need finish within7min" (a1 A18.1, TL:567); a2 closes the ledger `311c793` A18.5; docs fix `f1951ea` A18.9 |
| END + turn ends | 19.3-20.8 | a2, a3, a1 | END f1951ea a2 A19.3, a3 A19.7, a1 A19.8; TURN_END a1 A20.0, a3 A20.2, a2 A20.8 |

## 3. Per-agent account
- **a1 (spine, then engine/pipeline/process/triggers, main cross-reviewer)**: delivered the spine in about 3 active min. It owned the hardest parts: supervisor, kill -9 recovery, cache keys, and fairness. It found four seams in cross-review. It also started the wall-clock rush. TURN_END A20.0: "Completed and pushed to `origin/main` at `f1951ea`. All three peers approved that revision."
- **a2 (ledger, harness, scenarios 1-14 & 20; then sample repo, CLI, dashboard, README/DESIGN/PR)**: wrote the sample pipeline once (`2894048`, A9.4) and never revisited it. It spent the most time running the suite (~10 min testing). It closed the ledger in one sweep under the rush. TURN_END A20.8 after all 3 END posts.
- **a3 (scenarios 15-19 + security; then store/server/archives/GC/plugins/migrations)**: built most of the admin plane and the v1 fixture. It reviewed docs and pushed the timeout-doc fix. TURN_END A20.2 "Implemented ... all three peers approved the same final commit."

## 4. Coordination costs
- Crossed scope messages over the checks split (a2 A1.4 vs a3 A1.4, resolved A3.6 "FINAL ACK"). Expression syntax flip-flop: a3 changed tests to `${{ }}` while a2 proposed the opposite (A4.0). a1 settled it in SPINE DONE.
- Assertion-format churn: scenario 13 expected `[REDACTED]`, the implementation printed `***`. a2 first changed the assertion to `***` (A10.1); a3 then asked a1 to align to `[REDACTED]` (A11.4).
- Ledger stale: "All ledger status still OPEN locally" (a1 A15.1); "PR.md still duplicate stale sections+OPEN/CLAIMED" (a3 A18.1). It was closed at A18.5 with a boilerplate verification line on all 38 items ("Verified by `python3.12 -m minici.selftest` (51 passing tests) and the scenario map in DESIGN.md").
- No merge conflicts beyond one rejected push (a2 A17.5); nothing left on branches.

## 5. Penalty -> cause map
| Penalty | Log cause |
|---|---|
| Docs skipped (not cached) on corelib commit; test 03 accepts either | The check was written loose from the start. a2's first version (`420350e`, A3.3) already asserted `status in {'skipped','cached'}` for docs, against the brief's "unrelated jobs are cache hits whose artifacts are reused". The sample (`2894048`) gives docs `paths` and no separate `inputs`. The only strict part of test 03 is a synthetic two-job fixture, and the builder rewrote that fixture: a1 A13.1 "use inputs:[] with NO paths ... semantic correction, same strong cached assertion". **The acceptance check did not encode the brief and could not catch it.** |
| Sample: single shared lock, identical matrix cells, slow job in separate file, unused template | All from one commit by a2 at A9.4. The checks for parallelism, locks and templates use synthetic fixtures (a2 A11.4: "matrix include/exclude/templates/single-cell artifact, global locks, parallel jobs"). Nobody checked the sample's realism; no item in the ledger names it. |
| JSON-blob store, full scans | Spine design (a1 A3.8: "store uses SQLite state.db with JSON runs/jobs/cache/settings records"). It was never revisited; the spine's storage became the product. |
| Unused `leases` table claimed in DESIGN | No visible cause (docs written by a2 A16.5 from contracts). |
| 8-pair concurrency test | a2 scenario 11 written at A3.3; never strengthened. |
| DAG as list, polled logs, verbose CLI | Dashboard/CLI built by a2 in a single commit (A9.4); no UX review except a headless capture for overflow/XSS (A17.5). |

## 6. Decision points
1. A0.9: a1 publishes the API contract before writing code. The checks are written against it, so the checks are "outside-in" but contract-shaped.
2. A3.3: a2's scenario 3 accepts `skipped` or `cached`. This one line made the run's biggest coverage penalty invisible to the team's own verification.
3. A3.8: the spine fixes the storage model (JSON blobs) and file ownership. Everything after is fill-in within the spine.
4. A8.7-14.1: the checks catch real defects (validator variable shadowing, /repos route mismatch) and converge to 44/44 green.
5. A18.1: a1 reads `date -u` (TL:555) and declares "Need finish within7min". The cap was monotonic: about 18 of 120 active min had been used. Ledger closure, docs and END followed within 1.7 active min, and the run ended at A21 (span) / 28 (active).

## 7. Failure-mode tags
- WALLCLOCK_RUSH (1 decisive post plus echo: a1 A18.1, a3 A18.1 "hardcap about22:12UTC", a1 A18.3 "Actual task cap22:12UTC gives6min"): this caused the early END. About 90 active minutes went unused.
- PREMATURE_END (consequence of the above): the team ended at A21 with known-thin areas (sample realism, DAG view, SSE) never examined.
- SELF_REFERENTIAL_VERIFICATION (2): (a) scenario 03 accepted the weaker behaviour; (b) the ledger was closed with one blanket "selftest passes" justification per item, so "DONE" means "tests we wrote pass".
- SCOPE_SHRINK (mild, 1): "cache hits whose artifacts are reused" silently became "skipped is fine".
- DUPLICATE_WORK: none of note. MERGE_CONFLICT: none. REVIEW_LOOP: none.

## 8. Time accounting (heuristic, from call gaps; build includes writing tests)
| Agent | build | coordination | reading others | testing/review | idle |
|---|---|---|---|---|---|
| a1 | 4.6 | 5.0 | 2.6 | 7.1 | 0 |
| a2 | 5.0 | 0.4 | 3.0 | 10.2 | 1.2 |
| a3 | 2.7 | 3.8 | 3.7 | 8.6 | 0.5 |

## C2 mechanism check
- Spine early: yes. It was complete at A3.8-4.1, well under 12 min.
- Ledger: created A3.3 (38 items). Statuses were not maintained while building and were closed in bulk at A18.5.
- Acceptance checks: yes, all 20 scenarios before SPINE DONE (A2.6-4.3), plus extra security/archive checks.
- Ran and caught things: yes. Validator shadowing (04/12/16), the /repos path alias (09), the redaction marker (format only), and a plugin-step validator gap. Two check bugs were fixed "in the open" (03 fixture, 13 marker). One of them (03) was fixed by the builder whose code it tested.
- Weakness: the checks were exactly as strong as their first draft. The loose scenario 03 and the 8-pair race test were never tightened. Synthetic fixtures meant the shipped sample was never under test for realism.
