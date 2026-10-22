# E1-T1b-solo-r1: forensic notes (solo, T1b field-notes hub). Score 6.95

Sources: timeline `timelines/E1-T1b-solo-r1.md` (TL = line number), `lab/ws/E1-T1b-solo-r1/prompt.md`, the repo, delivered `PR.md`, and the judges.

## 1. Outcome
- Score: 6.95 (j1 7.0, j2 6.9). Coverage 7, correctness 8, design 7, robustness 7, code 5-6, **ux 5**.
- Top penalties:
  - "the browser UI covers only search, item detail, annotate, flag, acknowledge and a dossier download. It has no date or experiment filter, tags, saved searches, overrides, jobs view, relationship view or annotation editing" (j1).
  - "a thin browser UI, a small, very dense test suite, and topic tagging that marks most notes as 'drift'" (j2).
  - After Bob edits Alice's annotation, it still shows only Alice's name.
- Severe defect (j2): the shipped test suite fails because the fixture CSV is missing. The judge attributes this to anonymisation and did not penalise it.
- Delivered size: about 1900 lines under `fieldnotes/`, 7 tests, one commit 58e7b1c (2132 insertions).
- Time and tokens: 32.0 active min by timeline span (result.json 43.1), 127.8 wall min, **2.0 M input tokens** (6-9 times fewer than the swarm runs).

## 2. Phase timeline (active minutes)
| Phase | A | What happened |
|---|---|---|
| Inspect the archive | 0.2-1.1 | Archive statistics and front-matter census (TL:21-30). |
| Core build | 2.7-9.4 | Package skeleton (A2.7), extensions (A4.7), core.py (A6.7), jobs (A7.1). First real-archive ingest: "1,249 files, 10,096 derived relationships and 856 health findings" (TL:39, A8.1). Migrations 003 (A9.4). |
| Server and UI | 11.4-13.4 | server.py (A11.4); static UI and transfer code (A13.4). |
| Tests | 15.2-18.0 | pytest is absent, so it switches to unittest. Fixes until the tests pass (TL:49-56). |
| Live run attempt | 21.8-22.2 | Starting the server fails twice: "[Errno 1] Operation not permitted" (TL:66, TL:68, sandbox). **The UI was never seen in a browser.** |
| Commit and polish | 23.9-31.3 | Commit, then amends (TL:73). Dossier button fix (A28.6). Test fix (A29.9-30.5). |
| End | 32.0 | TURN_END (TL:94): "Implemented and committed Fieldnotes Hub on `main` (`58e7b1c`). - Full ingestion/indexing ... Search, facets, graph relationships, experiment dossiers and SVG plots". |

## 3. Per-agent account
- **root (single agent): build 18.0, inspecting 7.2, git 2.7, testing 1.9, final 0.7** (heuristic).
- No coordination overhead.
- It wrote whole modules in one call each.
- Why it ended: "The product pass is complete and committed on `main`" (TL:92), with 88 of 120 active minutes unused.
  - The prompt says "You have up to 120 minutes". The agent never read the clock; it ended voluntarily once its own checklist was done.

## 4. Coordination costs
None. The only rework was test fixes and a dossier-button fix.

## 5. Penalty to cause map
| Penalty | Cause in the log |
|---|---|
| Thin UI (no tags, saved searches, relationship view, jobs view or editing in the UI) | The server could not be started in the sandbox (TL:66, TL:68), so no UI was exercised. The ~4.6 KB `app.js` was written in one shot at A13.4 and never revisited, while backend features existed. PREMATURE_END with 88 minutes left. |
| Dense test suite | 7 tests written under time pressure the agent imposed on itself, plus string-replace fixes (A16.3-16.7, A29.9-30.5). |
| Annotation editor attribution | Not tested. No visible cause. |

## 6. Decision points
1. **A6.7, a single shared `Workspace` core** written before the adapters. This gave the design and correctness scores.
2. **A21.8-23.4, the UI cannot be run, and the agent moves on to commit** instead of testing the UI some other way (e.g. a headless-browser capture against a port-0 server).
3. **A32.0, voluntary end at 27% of the budget.**

## 7. Failure-mode tags
- **PREMATURE_END (1):** UI and UX gaps remained while 88 active minutes were unused.
- **SELF_REFERENTIAL_VERIFICATION (mild):** the tests cover the backend; the UI was unverified.
- **NONE** for coordination.

## 8. Time accounting (active minutes, heuristic)
| Activity | Minutes |
|---|---|
| Build | about 18 |
| Inspect | about 7 |
| Test | about 2 |
| Git | about 3 |
| Idle or waiting | 0 |
