# E1-T3b-solo-r1 (solo, T3b MiniCI, score 7.9)

Sources: timeline `timelines/E1-T3b-solo-r1.md` (TL), the one rollout (49 calls, reasoning encrypted, so no THINK
lines), `prompt.md`, judges j1/j2, `result.json`, delivered tree. Stamps are timeline active minutes (A).

## 1. Outcome
- Score 7.9 (j1 7.5, j2 8.3). Both judges: no severe defects, both guessed "single".
- Top penalties (both judges): code style. j1: "the code is compressed, with many statements per line, and the tests
  are the same"; j2: "Lines run up to 295 characters ... the whole dashboard is 17 lines of JS" (code 6/6).
  Dashboard: "minified 17-line `app.js` ... safe ... but bare" (j1). Logs are "offset polling, not SSE" (both).
  Minor issues: "`runs/<bad id>` returns 'unknown endpoint or method'", "`HEAD /` request gets 501" (j2); "the README points
  to a `PR.md` that isn't in the folder" (j1); GC `--dry-run` flag not accepted (j1).
- Positives the judges verified by hand: all 59 tests are green (all 20 scenarios), kill -9 recovery, process-tree kill,
  tamper and traversal rejection, path filtering, cache cascade, idempotency, roles, CSRF/Origin checks.
- Delivered: 1 commit `e429b76` (TL:128), "51 files changed, 3608 insertions". `minici/*.py` has 2,659 lines
  (1,907 product + 752 test), web has 27 lines, and DESIGN/README/PR.md total 456 lines. 11 product lines exceed 200 chars.
- Active time: the timeline span is 39.4 A (TL:12). result.json reports `active_min` 58.07 against 233.2 wall min. The
  difference comes from how each source measures; this note uses timeline A throughout. Tokens: 4.34M input
  (111.8k uncached), 86.9k output.
- Runner: hidden-test scoring failed (`score_error` sudo cp) and mutation testing did not run (`mutants 0`), so the
  only quality signal is the judges.

## 2. Phase timeline (single agent "root")
| A | Phase | Evidence |
|---|---|---|
| 0.0-0.7 | Read repo, sample, interpreters | TL:21-26; architecture decided at A0.7 "JSON pipelines, SQLite ... separate process supervisor" (TL:25) |
| 0.7-11.1 | Build the product in 6 big heredoc calls, with no tests | TL:28 pipeline/redact/storage (25k chars), TL:31 supervisor/plugins/gitops, TL:33 engine (35k), TL:35 archive+server, TL:40 cli+web, TL:42 sample-repo+demo |
| 11.1-12.0 | First smoke: local end-to-end run | A12.0 "The first local end-to-end run passed" (TL:46) |
| 12.0-16.0 | Write tests: unit tests + v1 fixture, then the 20-scenario acceptance suite | TL:47 (18 unit tests pass), TL:49 |
| 16.0-17.9 | Environment blocker: sockets forbidden, so it builds the `ipc.py` HTTP-over-file transport | A17.4 "This environment rejects socket creation" (TL:58-59) |
| 17.9-24.3 | Red/green loops on acceptance and on the new feature tests | A20.2 "passed 16 of 20" (TL:69); A24.3 "corrected scenarios now pass" (TL:82) |
| 24.3-27.8 | Edge fixes and hardening (incremental prerequisites, archive validation, config validation, verify.sh) | TL:83-89; A27.8 "53 tests ... green" (TL:91) |
| 27.8-32.9 | Self-review fix, README, DESIGN.md, launch final verification | TL:92-98 |
| 32.9-38.2 | Final verification finds 2 failures, then 1 error; both fixed; green | TL:102-123 |
| 38.2-39.4 | PR.md result, commit, final message, TURN_END | TL:126-132 |

## 3. Per-agent account (root only)
- It built everything: core library, supervisor, engine, server, CLI, dashboard, sample monorepo, three test files,
  the v1 fixture, the IPC test transport, and the docs. There was no coordination, no board, and no reading of anyone
  else's code.
- How it worked: it wrote a component as a whole file in one heredoc, compile-checked it, and moved on. Later changes
  were Python `str.replace` patches to existing files, made in calls 12-48.
- It ended once after verification passed. A38.4: "Final verification passed: all 59 tests in 63.6 seconds ... then
  committing to `main`" (TL:125). TURN_END at A39.4 (TL:132): "Committed to `main` as **`e429b76`** ... Environment
  limits: tested on Python 3.13 ... direct TCP/browser testing remains unverified here."
- Why it ended: it had worked to a plan stated at A27.8 ("reviewing edge cases and writing the operator documentation
  next, then I'll run verification again and commit", TL:91) and stopped when that plan was done. It ran
  `date -u` twice (A7.6 TL:37, A33.3 TL:100). The second check showed about 179 wall minutes since start, against
  "You have up to 120 minutes" in prompt.md. No SAY mentions time, and the wrap-up plan predates that check, so time
  pressure is not shown.

## 4. Coordination costs
- Not applicable: one agent, so no duplicate work, merge conflicts, or lost branches. One commit went straight to main.
- The solo equivalent of a coordination cost was the sandbox socket ban. About 1.9 A (A16.0-17.9) went to diagnosing it
  and building `ipc.py`, which "uses the exact same BaseHTTPRequestHandler parser" (TL:59). As a result the real TCP
  server and the browser dashboard were never exercised by the agent (TURN_END caveat).

## 5. Penalty -> cause map
| Penalty | Cause in log |
|---|---|
| Dense, golfed code (code 6) | Generation style: whole modules emitted in single heredocs (e.g. engine.py 35k chars at A5.7, TL:33). There was no refactor or readability pass; all later edits were `str.replace` patches (TL:47, 72, 83, 92, 96, 102). |
| Thin 17-line dashboard | Written once inside the CLI call at A9.8 (TL:40, files cli.py + web/index.html/style.css/app.js). Never revisited. Browser testing was impossible ("direct TCP/browser testing remains unverified", TL:132), and no test drives the UI. |
| Log streaming is offset polling, not SSE | Design choice made in the first server/web write (A7.4/A9.8). Never flagged as a gap. Polling meets the brief's "ranged reads" option. |
| Generic 404 / HEAD 501 | No visible cause; no test or review touched those routes. |
| README points to missing PR.md (j1) | PR.md is in the delivered tree (55 lines, written at A36.5 TL:111). The judge copy probably had it removed by the blinding step, so this is not a run defect. |
| GC `--dry-run` not accepted | Dry-run is the default with `--apply` to delete. A CLI design choice; no visible decision point. |
| No penalty for missing features | Coverage is 8/9. The brief's 20 scenarios were all turned into tests at A16.0 (TL:49), and the suite went through 5 fix cycles. |

## 6. Decision points
1. A0.7 (TL:25): architecture chosen up front (stdlib, SQLite, per-job supervisor). There was no draft stage; the
   first artifact was already full-scope.
2. A0.7-11.1 (TL:28-42): the whole product was built before any test ran. The brief's checklist became the module list,
   so nothing was scoped out early.
3. A16.0 (TL:49): the acceptance suite mirrors the brief's 20 numbered scenarios. This tied verification to the brief,
   not just to what existed.
4. A17.4 (TL:58): faced with the socket ban, it built a transport workaround rather than skipping server tests. That
   kept "drives the real server process" honest-ish, at the cost of leaving TCP and the browser unverified.
5. A32.9-38.2 (TL:98-123): the final full verification found 2 failures (test_11 plus a cache-key issue, "hashing the
   whole pipeline file made an unrelated job rebuild", TL:108), then 1 error (server-ready-file race, fixed by atomic
   write, TL:115). It committed only after a green 59/59.

## 7. Failure-mode tags
- NONE (dominant): no premature end, scope shrink, or integration loss. All 20 scenarios were tested, and the final
  suite is green (TL:123-125).
- STYLE_DEBT (new tag: shipped code is functional but compressed and unreadable, because large single-shot
  generations are never refactored): 1 instance across the codebase. Cost about 2 points per judge on "code".
- ENV_BLOCKED_VERIFICATION (new tag: the sandbox prevents a class of verification, so features ship unverified in
  their real mode): 1 instance (sockets, A16.5-17.4). TCP server and dashboard were not tested.
- WALLCLOCK_RUSH: unconfirmed. It checked `date -u` at A33.3 (wall clock past the 120 min given in the prompt), but the
  plan to finish predates this and it still ran 2 more fix/verify cycles. Count 0 confirmed.
- PREMATURE_END: 0. The dashboard and SSE thinness were never planned as further work, so this is not an early stop.

## 8. Time accounting (active minutes, total 39.4; idle 0)
Method: each gap between timeline stamps is assigned to the call that ends it (the model was generating that call's
input). Large gaps before heredoc calls count as building.

| Category | A | % | Segments |
|---|---|---|---|
| Reading brief/repo | 0.7 | 2% | 0.0-0.7 |
| Building product code | 13.1 | 33% | 0.7-7.4 core (pipeline/storage 2.0, supervisor 1.0, engine 2.0, archive/server 1.7); 7.6-11.1 cli/web 2.2, sample-repo 1.3; ipc 0.5; 24.3-26.4 fixes/config/verify.sh 2.1; half of 20.3-21.8 (engine features) 0.75 |
| Writing test code | 4.8 | 12% | 12.0-14.0 unit tests + v1 fixture; 14.0-16.0 acceptance suite; half of 20.3-21.8 test_features |
| Running tests / debugging own work | 11.5 | 29% | 7.4-7.6 compileall; 11.1-12.0 smoke; 16.0-17.4 socket diagnosis; 17.9-20.3; 21.8-24.3; 26.4-27.8 full run; 34.6-35.6; 36.5-38.2 |
| Self-review / hardening | 2.5 | 6% | 24.9-25.4 archive validation; 27.8-28.1 pipeline-only-change fix; 32.9-34.6 status check + type-check fixes |
| Docs (README, DESIGN, PR.md, sample README) | 6.3 | 16% | 28.1-30.1 README; 30.1-32.1 DESIGN.md; 32.1-32.9; 35.6-36.5 PR.md; 38.2-38.8 PR result + commit |
| Final message | 0.6 | 2% | 38.8-39.4 |
| Idle / waiting on others | 0 | 0% | none; test waits are folded into testing |

Build order: pipeline, redaction, storage (A2.7), then supervisor, plugins, gitops (A3.7), engine (A5.7), archive and
HTTP server (A7.4), CLI and dashboard (A9.8), sample monorepo, pipeline and demo (A11.1). After that: unit tests and v1
fixture (A14.0), acceptance suite (A16.0), IPC transport (A17.9), feature tests and engine features (A21.8), config
validation and verify.sh (A26.1-26.4), README (A30.1), DESIGN.md (A32.1), PR.md (A36.5).

First tests: compile-only at A7.6 (TL:37). First real execution was the local end-to-end run at A11.1 (28% of the
run). First unit tests at A14.0. First acceptance attempt at A16.0, which failed to start the server.

Fix iterations: 5 red-to-green cycles.
1. Sockets forbidden, solved with ipc.py (A16.2-17.9).
2. Acceptance 16/20 with 4 failures (test synchronisation and a wrong test input), fixed by A20.3.
3. Feature tests: 1 FAIL + 1 ERROR, fixed by A23.5.
4. Final run 59 tests with 2 failures, fixed in the cache key (A34.7-35.4).
5. 1 error from the ready-file race, fixed (A36.6-37.0); green at A38.2.

The suite grew 18 to 38 to 53 to 59 tests. About 13 test launches in total.

Why it ended: verification was green and committed, and its own plan was complete (TL:91, TL:125, TL:132). No external
stop and no cap hit.

Contrast hooks for swarm vs solo: 0% coordination and 0% idle. 33% product building done in one uninterrupted early
block (A0.7-11.1) before any test. 41% on tests (writing plus running/debugging). 16% on docs. Self-review was short
(6%) but drove 2 real fixes. Verification was tied to the brief's numbered scenarios from A16.0 onward.
