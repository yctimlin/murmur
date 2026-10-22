# E1-T1b-C2-r1: forensic notes (C2, T1b field-notes hub). Score 7.85, high

Sources: timeline `timelines/E1-T1b-C2-r1.md` (TL = line number), origin.git, and the judges.

## 1. Outcome
- Score: 7.85 (j1 7.8, j2 7.9). Coverage 8, correctness 8, design 8. No severe defects.
- Top penalties:
  - No XLSX example; only a vendor TSV parser is bundled.
  - "People and topics are projections rather than full entities".
  - "Plot x-values are sample order, not time".
  - `capture_browser.py` token-file format bug.
  - Health listings are not paged; results open in a modal.
  - No inconsistent-metadata findings on the real archive.
- Delivered size: about 3000 lines (fieldnotes package, static UI, 26-path OpenAPI spec) and 37 tests.
- Time and tokens: 27.1 active min by timeline span (result.json 34.0), 98.2 wall min, 17.2 M input tokens.

## 2. Phase timeline (active minutes)
| Phase | A | What happened |
|---|---|---|
| Claims | 0.7-1.1 | **a1 claims SPINE at A0.7** (TL:61). a3 claims acceptance (TL:71). a2 claims acceptance, then corrects itself to ledger plus ingestion acceptance (TL:89). |
| Ledger and acceptance | 1.8-4.5 | a2 writes a 35-row ledger, R01-R35 (75b5aa3, TL:112). Acceptance tests: a2 136, 76 and 69 lines (TL:134, TL:180, TL:198); a3 302 lines of fixtures and team tests (TL:167). FACT posts on the archive and environment (TL:99, TL:111, TL:159). |
| Spine | 0.7-5.1 | d0d9118, 360 lines across 14 files, every module wired including a browser shell (TL:220). SPINE DONE at A5.1 (TL:229). |
| Build | 5.2-11.7 | Item claims with one owner each (TL:244, TL:254, TL:258). Large builds: a1 1575 lines of API, OpenAPI and hardening (afe3bed, TL:296); a2 717 lines of ingest, inference and plugins (43a9739, TL:318); a3 772 lines of curation, restore, search and dossiers (6ee224b, TL:345). At A11.9 all 24 acceptance tests pass (TL:363). |
| Cross-check and gap-fill | 12.8-23.4 | Import identity seam found (TL:392, fixed TL:415). People-graph gap found against the brief (TL:417, TL:446), filled at TL:485 and TL:559. Binary plugin seam (TL:467-473). 10× benchmark (TL:493). Settings knob (TL:688). Archive-output guard (TL:719). Independent Chrome captures by each peer (TL:627, TL:655, TL:707). |
| END | 25.3-27.1 | Ledger closed at 4dc0af3 (TL:797). END from all three peers (TL:809, TL:826, TL:832). Turn ends at TL:848, TL:854, TL:859. |

## 3. Per-agent account
Heuristic classifier, active minutes.

- **a1: build 9.7, coordination 9.2, inspecting 5.4.** Spine, API, OpenAPI, UI flows, docs, settings, browser capture.
  - It read the wall clock once: "current UTC02:11 (~33min hard cap left)" (TL:542). Wall time was only 88 min, so it did not trigger a stop.
  - TURN_END (TL:859): "All three peers approved the same revision. All 37 tests pass".
- **a2: coordination 18.0, testing 1.6.** Ledger, acceptance tests, ingest, inference, plugins, the 10× benchmark. Most of its code was written in calls that also posted, which the classifier counts as coordination.
  - TURN_END (TL:854): "done".
- **a3: coordination 13.7, inspecting 5.4, build 3.0.** Fixtures, team acceptance, core curation, import, people graph, jobs.
  - TURN_END (TL:848): "All 37 tests pass; desktop/mobile browser checks pass."

## 4. Coordination costs
- **Claim correction:** one (TL:89). Negligible.
- **PR.md push races:** resolved by narrow per-row edits (TL:305, TL:599).
- **Capture-tool failures:** the browser capture failed twice (TL:557, TL:586) and needed one fix.
- **Duplicate work:** none visible.
- **Integration loss:** none; everything was built on main.

## 5. Penalty to cause map
| Penalty | Cause in the log |
|---|---|
| No XLSX example | a2 made the binary-parser seam (TL:467-473) but shipped only a TSV example. The brief requires "one example plugin of each kind", which was met. |
| People and topics are projections | Gap found by the cross-check (TL:417, TL:446). Filled with a projection-based people graph (TL:485). Time-boxed. |
| Plot x by sample order | a2's stats contract (TL:284) carried samples without timestamps. No visible review. |
| Capture-script token format | a1's tool. Fixed for one format only (TL:576). |

## 6. Decision points
1. **A0.7, immediate SPINE claim** (TL:61). Product code starts in the first minute.
2. **A1.8, a full 35-row ledger** (TL:112) plus brief-derived acceptance tests while the spine is being built.
3. **A5.1, a 360-line spine with every module wired**, including a browser shell (TL:229). The parallel builds then fill real modules of 700+ lines.
4. **A13.4, a cross-check against the brief, not against the code** (TL:417). It found the people-graph gap and closed it.

## 7. Failure-mode tags
- **WALLCLOCK_RUSH (1 read, no impact):** TL:542.
- **MERGE_CONFLICT (minor):** PR.md races.
- Otherwise NONE.

## 8. Time accounting (active minutes, heuristic)
| Agent | Build | Coordination | Inspecting | Testing | Waiting | Total |
|---|---|---|---|---|---|---|
| a1 | 9.7 | 9.2 | 5.4 | 1.1 | 0.7 | 26.7 |
| a2 | 1.3 | 18.0 | 1.5 | 1.6 | 2.9 | 26.5 |
| a3 | 3.0 | 13.7 | 5.4 | 2.0 | 1.1 | 25.9 |

- Builds embedded in post scripts are counted as coordination.
- Waiting was almost nil, compared with 7-11 min per agent in C2-r2.
