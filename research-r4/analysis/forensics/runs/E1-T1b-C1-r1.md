# E1-T1b-C1-r1: forensic notes (C1, T1b field-notes hub). Score 7.7, high

Sources: timeline `timelines/E1-T1b-C1-r1.md` (TL = line number), origin.git, and the judges.

## 1. Outcome
- Score: 7.7 (both judges 7.7: coverage 8, correctness 8, design 7, robustness 8, code 6, ux 8). No severe defects.
- Top penalties:
  - "The static HTML dossier export never draws its plot" (`team.py:400` reads `stats['sample']`, which has no `value` key).
  - "Facets are not result-scoped".
  - "Every scan, even one with no changes, deletes and rebuilds all links and findings ... unchanged scan took 53s" at 10× scale.
  - No API route to delete an annotation or override.
- Delivered size: about 2170 lines under `fieldnotes/` (core, team, server, jobs, static UI, OpenAPI) and 24 tests.
- Time and tokens: 19.9 active min by timeline span (result.json 27.0), 122.4 wall min, 12.7 M input tokens.

## 2. Phase timeline (active minutes)
| Phase | A | What happened |
|---|---|---|
| Claims | 0.8-1.7 | All three first claim "dossier-first" (TL:68, TL:79, TL:85). a1 enforces the earliest claim (TL:90). a2 and a3 both switch to health-first (TL:101, TL:105). These are competing **whole-product directions**. |
| Drafts | 2.3-2.7 | Tiny HTML and data.js mock-ups built from real archive data: a1 b8cea8c, 28 lines (TL:112); a3 c9c1c2a, 29 lines (TL:123); a2 fe8c450, 39 lines (TL:126). |
| Ranking | 3.4 | All three render every draft in headless Chrome at 1440x1000 and rank a1 first unanimously (TL:166, TL:170, TL:174). |
| Plan and contract | 2.8-5.9 | Ownership is negotiated: a1 core; a2 team, auth, export, CLI and docs; a3 HTTP, UI and jobs (TL:141, TL:187-207). a1 pushes plan, CONTRACT.md and a **22-row ledger with every row CLAIMED, none done** (5ed02ad, TL:233-236, A4.5). Interface details posted: schema (TL:203), JobRunner (TL:217), Team API (TL:220), auth (TL:225, TL:231). |
| Build | 5.9-11.8 | Large single-shot modules. a1: 6869d29 (190 lines, TL:277), 6d230ad (378 lines, TL:332), c8846fb (119 lines, TL:376). a2: team.py 400 lines (TL:294), CLI 130 lines (TL:304), tests 148 lines (TL:328), docs 168 lines (TL:365). a3: server, UI, jobs and OpenAPI, 1658 lines (458abd7, TL:389). |
| Seam review and fixes | 10.2-17.4 | a1 FAIL on finding timestamps (TL:351). a2 finds an unlink seam (TL:411) and a NaN-ingest seam (TL:475). a3 finds an XLSX binary-plugin seam (TL:535). Fixes land (TL:471, TL:522, TL:581). Browser reviews on desktop and mobile (TL:515, TL:537). |
| Rush and END | 18.3-19.6 | a1: "Clock jumped to 21:06, hard cap reached unexpectedly" (TL:610). a3 says the same (TL:635). Ledger closed at 1f9023d (TL:626). END from all three peers (TL:658, TL:662, TL:675). Turn ends at TL:685, TL:689, TL:694. |

## 3. Per-agent account
Heuristic classifier, active minutes. Coordination includes calls that both write code and post.

- **a1: build 7.2, coordination 9.3.** Core: storage, migrations, parsers, ingest, relationships, search, health, plugins, a demo and a 10× benchmark.
  - TURN_END (TL:689): "All three peers approved the same final commit. 24 tests pass. Real archive and 10× stress validation completed."
- **a2: build 4.4, coordination 11.2.** team.py, CLI, tests and docs. It also posted the "~26m hard cap remaining (clock jumps)" note (TL:443).
  - TURN_END (TL:694): "All 24 tests pass; documentation, CLI, API, UI, plugins, migrations, curation transfers, and capacity measurements are included".
- **a3: build 6.7, coordination 8.8, testing 1.8.** HTTP server, browser UI, jobs and HTTP tests. Its Chrome captures were the strongest outside-in review.
  - TURN_END (TL:685): "done".
- **root:** waited.

## 4. Coordination costs
- **Claim collision:** about 1 active min re-diversifying directions (TL:90-120).
- **Ownership churn:** two competing split proposals were resolved within 1 min (TL:192-235).
- **Discarded work:** a2's team schema SQL, after "disregard my earlier migration SQL" (TL:282). Small.
- **Merge conflicts:** a `.gitignore` conflict (TL:449) and a docs merge (TL:646).
- **No integration loss:** draft branches were mock-ups, not product code.

## 5. Penalty to cause map
| Penalty | Cause in the log |
|---|---|
| Static dossier has no plot | a1 changed the stats shape (`sample` rows of dicts, TL:334), but a2's snapshot code in team.py expected a `value` key. The seam between a1 and a2 was never exercised in an HTML snapshot check. |
| Facets not result-scoped | No visible cause: never discussed. |
| Unchanged scan rebuilds derived data (53 s at 10×) | a1's design. The 10× benchmark measured it (TL:628) but it was reported, not fixed. Late WALLCLOCK_RUSH at A18.3 (TL:610) left no time. |
| No delete route for annotations or overrides | Not in the ledger. Minor SCOPE_SHRINK. |

## 6. Decision points
1. **A1.4-1.7, directions re-diversified** (TL:90-105). The draft phase stays a choice between whole-product directions.
2. **A3.4, unanimous visual ranking from real Chrome captures** (TL:166-174).
3. **A4.5, plan, CONTRACT.md and a full ledger with every row CLAIMED** (TL:233-236). The draft is treated as a *design*, not as code.
4. **A5.9-11.8, single-shot module builds against the contract** (TL:277-389), followed by seam review.

## 7. Failure-mode tags
- **WALLCLOCK_RUSH (2 posts, low impact):** TL:610 and TL:635, after all build work was done. It truncated the benchmark write-up.
- **MERGE_CONFLICT (2, minor).**
- **DUPLICATE_WORK (1, minor).**
- **SCOPE_SHRINK (minor).**
- Otherwise NONE.

## 8. Time accounting (active minutes, heuristic)
| Agent | Build | Coordination | Testing | Other | Total |
|---|---|---|---|---|---|
| a1 | 7.2 | 9.3 | 1.3 | about 1.6 | 19.4 |
| a2 | 4.4 | 11.2 | 0.7 | about 2.9 | 19.2 |
| a3 | 6.7 | 8.8 | 1.8 | about 1.8 | 19.1 |

- Large code writes take more than 2 min of generation. They are under-counted, because the active clock caps each gap at 120 s.
