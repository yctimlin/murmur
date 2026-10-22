# E1-T1b-C2-r2: forensic notes (C2, T1b field-notes hub). Score 2.55, collapse

Sources: timeline `timelines/E1-T1b-C2-r2.md` (TL = line number), the a2 and a3 rollouts, origin.git, delivered `PR.md` and `acceptance/run.py`, and the judges.

## 1. Outcome
- Score: 2.55 (j1 2.4, j2 2.7). Coverage 2/2.
- Severe penalties, both judges:
  - "No browser UI at all (root returns a JSON stub)"
  - "Import restores only users; annotations and finding states are dropped"
  - "Dossier endpoint returns every finding in the archive"
- j2 adds "no authentication: the brief's onboarding flow ... is impossible".
- Also missing, per j1: watcher and background jobs, near duplicates, orphan and missing-log checks, broken links, people and topic entities, relationship view, log stats and plot, tags, saved searches, overrides. Search uses LIKE even though an FTS5 index is built.
- Delivered size:
  - About 510 lines under `fieldnotes/` and `tests/` (j1: "about 460 lines of Python"), plus a 138-line `acceptance/run.py`.
  - 6 unit tests.
  - PR.md has **20 ledger rows marked `DESCOPED (120-minute hard cap; prototype incomplete)`**.
- Time and tokens: 35.5 active min by timeline span (result.json 44.9), 143.4 wall min, 9.8 M input tokens. run_exit 0; every peer ended on its own.

## 2. Phase timeline (active minutes)
| Phase | A | What happened |
|---|---|---|
| Claims | 0.9-5.7 | a1 claims ACCEPTANCE: "no product code until SPINE DONE" (TL:64). a3 supports acceptance (TL:107). a2 posts CLI shapes (TL:154). **Nobody claims SPINE.** a2 believes "root/a1 likely coordinating launcher and spine" (TL:193). |
| Acceptance and ledger | 6.0 | a1 pushes 0da2e92: ledger (42 OPEN rows) and acceptance suite, 236 lines (TL:204). |
| Spine vacuum | 6.0-8.4 | a2: "No SPINE claim visible yet; I'm waiting" (TL:217, TL:256). a3 computes archive facts (TL:262). Every peer is in a `wait_agent` cycle (30-60 s). |
| Spine | 8.4-17.2 | a1 claims SPINE at A8.4 (TL:266). a2 claims it too at A11.2 (TL:316) and builds a parallel spine anyway. a1's spine is e9ef81c, 151 lines (TL:373). SPINE DONE at A17.2 (TL:393). The browser root is a JSON stub. |
| Build | 18.2-29.9 | a3 claims plugins at A18.2 (TL:416) and lands them at A27.1, 221 lines (45f84c4, TL:541). a1 adds the snapshot command, 3 lines (43c88e5, TL:451), and marks spine rows DONE (TL:469). a2 discards its spine (A24.6, TL:509), claims migrations at A25.2 (TL:514), and lands 8d076e1 (27 lines, TL:551) and e9ff012 (159 lines, TL:614). |
| Wall-clock rush | 29.3 | a3: "**hard cap reached (~120m since activation 00:07)** ... Cannot take more items" (TL:591). a1: "hard cap also reached ... I will mark remaining unsupported ledger items DESCOPED" (TL:603). |
| Wind-down and END | 29.6-35.5 | a3 ends at A29.9 without voting END (TL:611). a1 pushes cf538a9, which turns OPEN rows into DESCOPED (TL:628, TL:638). END c378405 from a2 (TL:672) and a1 (TL:681). Turn ends: a2 A34.9 (TL:696), a1 A35.3 (TL:705). |

## 3. Per-agent account
Heuristic classifier, active minutes.

- **a1: build 8.2, coordination 9.3, waiting 10.7, inspecting 2.8, testing 2.0.**
  - It built the ledger, the acceptance suite, the 151-line spine, a 3-line snapshot, and docs.
  - TURN_END (TL:705): "Pushed prototype ... Hard cap reached; unmet product requirements are documented in `PR.md`."
  - It adopted a3's wall-clock claim without checking its own clock (TL:603).
- **a2: build 5.0, coordination 7.1, waiting 7.1, inspecting 5.4, testing 4.9, git 3.3.**
  - A11.2-24.6 went into a second, competing spine: 123 lines, local commit 7d71a5e (TL:474). It ignored a1's request to hold (TL:331), hit an add/add conflict (TL:474-500), and ran `git reset --hard origin/main` (TL:509).
  - Its useful output was migrations and CAS concurrency (8d076e1, e9ff012).
  - TURN_END (TL:696): "Hard cap reached; incomplete capabilities are documented in `PR.md`."
- **a3: build 3.9, coordination 5.3, waiting 9.2, inspecting 4.5.**
  - It wrote archive FACT posts (TL:141, TL:262) and the plugin mechanism.
  - Its time source was the board's UTC `created_at` stamps: its first post was 00:07 UTC, and at the time of TL:591 the board time was 02:06 UTC. At that point active time was 29.3 min and wall time 137 min, because of five freezes, for example 07:49 to 08:07 and 08:11 to 08:40.
  - TURN_END (TL:611): "Hard time cap reached; full workspace remains incomplete".

## 4. Coordination costs
- **Spine vacuum, about 8 active min.** C2 says "the first peer to claim SPINE builds" it. All three first took acceptance or support roles and then waited for a spine claim that nobody made.
- **Duplicate spine:** a2 spent about 13 active min (A11.2-24.6) building a spine that was then thrown away. INTEGRATION_LOSS and MERGE_CONFLICT.
- **Ignored message:** a1's "a2's later claim conflicts; please hold" (TL:331) was not acted on.
- **Rush contagion:** one peer's wall-clock reading (TL:591) became the team's stopping rule within 20 s (TL:603, TL:632).

## 5. Penalty to cause map
| Penalty | Cause in the log |
|---|---|
| No browser UI | The spine shipped a JSON landing page. The ledger row went to "DONE 53036a5 — browser root responds with JSON landing page". The acceptance check is only `if status != 200: fail("browser root returned ...")` (acceptance/run.py:129), which is SELF_REFERENTIAL_VERIFICATION. Nobody claimed the UI before the rush. |
| Import loses annotations and finding states | The spine's import branch. The ledger says "DONE 53036a5 — SQLite store and export/import checks pass", but the acceptance round-trip check did not compare curated rows. |
| Dossier returns all findings | Spine stub (`SELECT * FROM findings`). The dossier row was DESCOPED at A30.4 (TL:628). |
| Missing watcher, near duplicates, links and provenance, tags, saved searches, overrides, audit, OpenAPI, stats and plot | All were OPEN rows that **were claimed by nobody** before A29.3, then converted to DESCOPED citing the "120-minute hard cap" (cf538a9, TL:638). WALLCLOCK_RUSH followed by SCOPE_SHRINK. |
| LIKE search | The spine's thinnest implementation was never revisited. |

## 6. Decision points
1. **A0.9, a1 claims ACCEPTANCE instead of SPINE** (TL:64). With a2 deferring to "root/a1" (TL:193), product code started only at A8.4 (TL:266).
2. **A11.2, a2 counter-claims SPINE** (TL:316) and ignores the hold request (TL:331). About 13 active minutes of one peer were lost.
3. **A17.2, the spine is a 151-line stub with a JSON root** (TL:393). The UI was never a claimable item before the rush.
4. **A29.3, a3 declares the hard cap from wall-clock board stamps** (TL:591), with 90 active minutes actually left. a1 converts 20 rows to DESCOPED (TL:603, TL:638). This decided the score.

## 7. Failure-mode tags
- **WALLCLOCK_RUSH (3 agents):** TL:591 (a3), TL:603 (a1), TL:632 (a2: "Hard cap acknowledged: stopping feature growth").
- **PREMATURE_END (3):** every peer ended at A29.9-35.3 with 20 rows DESCOPED.
- **SCOPE_SHRINK (20 rows),** explicitly labelled.
- **SPINE_VACUUM (new, 1):** under the spine protocol nobody claims the spine, and all peers wait in non-product roles.
- **DUPLICATE_WORK (1)** and **INTEGRATION_LOSS (1):** a2's discarded spine.
- **MERGE_CONFLICT (2):** TL:474-500 (a2), and the PR.md conflicts at TL:635.
- **SELF_REFERENTIAL_VERIFICATION (2+):** the acceptance browser check accepts any 200 response; the export/import check is shallow.
- **IDLE_PEER:** A2-8.4, all peers.

## 8. Time accounting (active minutes, heuristic)
| Agent | Build | Coordination | Waiting | Inspecting | Testing | Git | Total |
|---|---|---|---|---|---|---|---|
| a1 | 8.2 | 9.3 | 10.7 | 2.8 | 2.0 | 1.4 | 34.8 |
| a2 | 5.0, about 3 of it on the discarded spine | 7.1 | 7.1 | 5.4 | 4.9 | 3.3 | 34.2 |
| a3 | 3.9 | 5.3 | 9.2 | 4.5 | 2.0 | 2.9 | 29.1 |

- The team used about 35 of 120 available active minutes. About 85 minutes were left unused because of WALLCLOCK_RUSH.
