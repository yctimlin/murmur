# E1-T1b-C1-r2: forensic notes (C1, T1b field-notes hub). Score 2.45, collapse, CAP_HIT

Sources: timeline `timelines/E1-T1b-C1-r2.md` (TL = line number), rollouts under `lab/ws/E1-T1b-C1-r2/codex-home/sessions/2026/10/20/`,
`logs/run.json`, origin.git `main`, judges `judge/E1/E1-T1b-C1-r2.j1.md` and `.j2.md`. Freeze windows come from `lab/heartbeat.log` (r4eval.freeze_windows).

## 1. Outcome
- Score: 2.45 (j1 2.3, j2 2.6). Coverage 2/3, correctness 3/3, design 2/2.
- Severe penalties the judges quote:
  - "FTS search with hyphenated experiment IDs (e.g. EXP-2023-001) raises sqlite OperationalError and drops the API connection" (both judges).
  - "overrides table schema conflict ... migration 2 is a no-op; override insert/import fails" (j1).
  - "run_health resets acknowledged findings to open on every ingest; no auth enforcement on API writes" (j1).
  - "A single malformed JSON/CSV file aborts the entire ingest" (j2).
  - "UI experiment links (/experiment/<id>) all 404; no login, annotations or finding actions in the UI; no user/export/import/migrate CLI" (j2).
- Also from the judges: "very thin prototype, about 470 lines of Python"; no watcher, background jobs, near-duplicate detection, tags, saved searches, log stats/plot, date/topic facets, or OpenAPI spec.
- Delivered size: about 490 lines (py, html, js, css) under `fieldnotes/` and `tests/`. There are 3 tests. README is 16 lines and DESIGN.md is 11.
- Time and tokens:
  - Active time: 53.2 min by the timeline clock; result.json says 66.97.
  - Wall time: 597.7 min.
  - murmur's monotonic clock: 7200 s, then run_exit 124 (`"capped": true`, `codex_exit_code: -15`).
  - Input tokens: 18.8 M.

## 2. Phase timeline (active minutes)
| Phase | A | What happened |
|---|---|---|
| Read and claim | 0-4.8 | Claims divided **layers**, not alternative directions: a1 "backend persistence/migrations and API foundations" (TL:77), a2 "ingestion/search/health pipeline" (TL:108), a3 "user-facing browser UI/CLI" (TL:115). a1 then narrows itself: "a2 owns ingestion/search/health" (TL:121). |
| Drafts | 5-10.5 | a3 pushes a UI shell, 76 lines (f937a8f, TL:152, A7.3). a1 pushes db/api/cli, 174 lines (049c925, TL:165, A8.2). a2 pushes ingest/FTS/health, 226 lines (4e228fa, TL:173, A9.1). |
| Ranking | 12.4-14.2 | All three rank a2 first: TL:247 (a2), TL:274 (a3), TL:291 (a1). Each also says "fold a1 persistence/auth and a3 UI". |
| Integration | 14.4-17.5 | a2 fixes a syntax error, pushes main f933bce, and posts DONE (TL:358, TL:362). |
| Plan and ledger | 18.7 | a2 writes PR.md with a 16-line ledger. **7 of the 16 rows are already `[x]`, on the strength of the 226-line draft** (add174b, TL:391-392). |
| "Build" | 17.9-37.3 | Only small patches: a1 curated.py, 55 lines (TL:370); web wiring, 16 lines (TL:413); import, 26 lines (TL:509); tests, 18 lines (TL:571); health hook, 15 lines (TL:630); static dossier, 1+11 lines (TL:754, TL:793); jobs, 8 lines (TL:927). a3 UI integration, 51 lines (d820cf5, TL:460). |
| Review fixes | 27.8-36.3 | a3 FAIL on SQLite threading (TL:614), fixed (TL:651). a3 finds the "static dossier" commit only added an import (TL:833). a3 FAIL: dossier returns 404 (TL:893), fixed (TL:911). |
| END votes | 38.3-43.4 | a3 and a2 post END on 5ed4d75 (TL:977, TL:1040). a1's docs-only push voids them (TL:1046). Then END 755b40b from a1 (TL:1062, A41.5), a3 (TL:1072, A41.8) and a2 (TL:1105, A43.4). **Quorum reached at A43.4.** |
| Turn ends | 44.1-cap | a1 ends at A44.1 (TL:1126). a3 cycles three 10-minute waits, then ends at A52.4 (TL:1157). **a2 never ends its turn**, so root keeps waiting and the run hits the cap. |

## 3. Per-agent account
Time splits come from a heuristic classifier over the stream, in active minutes. Time producing a call is credited to that call. A call that both writes a file and posts to the board is counted as coordination.

- **a1: build 6.7, coordination 11.4, reading others 8.9, inspecting 7.4, waiting 6.0, testing 1.2.**
  - Its 174-line draft has migrations v1/v2, a Store, an API and a CLI. After the ranking it abandons that draft and rebases onto a2's draft: `git switch -c draft/a1-curated origin/draft/a2` (TL:342-355).
  - It then rewrites the persistence work as a 55-line `curated.py` (TL:370). draft/a1 is never merged.
  - Most of its later commits flip ledger rows: "mark persistence and curated requirements complete" (TL:518), "mark ingest job history complete" (TL:935), "mark documentation requirement complete" (TL:1036).
  - TURN_END (TL:1126): "END 755b40b posted; all three peers have reviewed and posted END for the same latest `main` commit."
- **a2: build 5.2, coordination 13.2, reading others 7.6, inspecting 4.7, testing 3.1, waiting 13.5.** This excludes about 48 parked minutes that the active clock does not credit (section 8).
  - It wrote the base draft and the ledger.
  - It added a duplicate health-plugin hook, 2492ebb (TL:654). That hook collided with a1's 7e6ed24 (TL:630). Removing it cost a rebase conflict and a `reset --hard` (TL:724-808).
  - It posted END at A43.4 (TL:1105), then parked: `wait_agent 3600000` (TL:1114).
  - a3 woke it at A49.4 (TL:1139). It called list_agents, which showed a1 completed and a2/a3 running. It reasoned "**Waiting for root status confirmation**" (TL:1145) and parked again for 60 min (TL:1146).
  - Root is forbidden to message peers ("Never post to the message board, send messages", prompts/root.md), so nobody would ever confirm.
  - It never posted TURN_END.
- **a3: build 4.5, coordination 10.9, reading others 8.1, testing 5.0, waiting 17.7.**
  - It wrote the 76-line UI draft and integrated it (d820cf5).
  - Its runtime checks found three real defects: threading (TL:614), the empty "static dossier" commit (TL:833), and the 404 on a found dossier (TL:893).
  - After quorum it ran three 10-minute `wait_agent` calls (TL:1129, TL:1134, TL:1144), sent messages to a2 and to root, and ended with TURN_END "done" (TL:1157, A52.4).
- **root:** waited the whole run, wait 51.7, in repeated `wait_agent 3600000` calls (last at TL:1163).

## 4. Coordination costs
- **Draft phase used as a division of labour.** Each "draft" was a different layer, so the ranking compared ingest against persistence against UI, which is not a choice between product directions.
  - The loser's code (a1's Store, migrations and API) was discarded. a1 had to rebuild it smaller on a2's string-ID schema. a2 had warned: "a1's Store uses integer IDs" (TL:265).
- **Integration loss:** draft/a1 (049c925) never reached main. draft/a1-curated was cherry-picked as 55 lines.
- **Duplicate work:** two health-plugin loaders were written about 40 s apart. a1 posted its intent on the board first, at A27.3 (TL:598), and a2 never read it. Cleaning this up cost a merge conflict (TL:735) and a reset. The judge still found two copies ("written twice").
- **Re-votes:** END on 5ed4d75 was voided by a1's ledger-only docs push (TL:1046), so all three peers had to review and vote a second time.
- **Waiting after quorum: about 69 of about 112 freeze-excluded minutes** (section 8).

## 5. Penalty to cause map
| Penalty | Cause in the log |
|---|---|
| Search crashes on `EXP-2023-001` | Every search check by every agent used "annealing": 8 times `search?q=annealing`, 7 times CLI `search annealing`, 4 times `search('annealing')`. Experiment IDs, the archive's main key, were never tried. SELF_REFERENTIAL_VERIFICATION. |
| Overrides broken (schema conflict) | a2's draft SCHEMA already had `overrides(source_id,…)`. a1's curated.py migration 2 used `CREATE TABLE IF NOT EXISTS overrides(user_id,…)` (TL:370), a seam from grafting a1's layer onto a2's base. The ledger row was marked `[x]` from a smoke test that never inserted an override (TL:485, TL:519). |
| Acknowledged findings reopen | a2's draft `run_health` logic (4e228fa), not reviewed afterwards. The ledger marked "Health findings with auto-resolution" `[x] f933bce` at A18.7 (TL:392) with no lifecycle test. |
| Malformed file aborts ingest | Draft code. Never exercised: all ingests ran on the clean archive. |
| UI `/experiment/<id>` 404 | a3's UI links (f937a8f) were never clicked. The END reviews checked endpoints with urlopen (TL:1022-1033), not UI links. |
| No watcher, background jobs, near duplicates, tags, saved searches, log stats/plot, facets, OpenAPI, CLI user/export/import | **Never claimed.** These were absent from the 16-row ledger or folded into coarse rows already marked `[x]`. Examples: "Users, annotations, optimistic concurrency, audit log, curated overrides" stands in for tags and saved searches. A Decisions line says "near-duplicate detection is a follow-up health plugin" (PR.md). SCOPE_SHRINK. |
| Thin README/DESIGN | The ledger row was marked `[x]` by a1 with the reason "files present" (TL:1037). |

## 6. Decision points
1. **A2.3-4.8 claims split by layer** (TL:77, 108, 115, 121). This turned "build alternative drafts" into "build one third each, about 200 lines each", which fixed the base size at 226 lines.
2. **A18.7, a2's ledger** (TL:392). Seven rows were pre-marked `[x]` from the draft and the brief was compressed to 16 rows. From then on the team "closed rows" with 1-55-line commits. This is the moment the draft became the product.
3. **A41.0, a1's docs-only push voids the END votes** (TL:1046). It cost a full second round of reviews.
4. **A43.4-49.8, a2 parks instead of ending after quorum** (TL:1114, TL:1145-1146). Its reasoning: "Waiting for root status confirmation". This alone caused CAP_HIT.

## 7. Failure-mode tags
- **DRAFT_AS_PRODUCT (1):** the 226-line draft became main, and every later commit was 55 lines or fewer.
- **DRAFTS_AS_LAYERS (new, 1):** in the draft phase peers claim complementary layers instead of competing whole-product directions. The ranking then picks a partial layer as the "base" and the other layers are rebuilt smaller to fit it.
- **SCOPE_SHRINK (about 10 brief items):** never on the ledger, or hidden inside coarse `[x]` rows.
- **SELF_REFERENTIAL_VERIFICATION (5+):** a single search term; `py_compile` and 3 tests as the "review"; a3's END said "No further issues found" (TL:977) while the UI links were dead.
- **INTEGRATION_LOSS (1):** draft/a1 was never merged.
- **DUPLICATE_WORK (1):** two health-plugin hooks.
- **MERGE_CONFLICT (4):** TL:406 (`__init__.py`), TL:490 (`web.py`), TL:735 (`core.py`), plus a3's rejected push at TL:629.
- **REVIEW_LOOP (1):** an END round voided by a docs-only push.
- **CAP_HIT (1).**
- **PARK_DEADLOCK (new, 1):** after the END quorum a peer keeps parking in `wait_agent`, waiting for a signal (root or peer confirmation) that the protocol never sends. Root waits for that peer, so the run idles until the cap.
- **IDLE_PEER (post-quorum):** a3 and a2.

## 8. Time accounting, and where the 120 monotonic minutes went
- The heartbeat-based freeze-excluded time from start to the end at 01:35:51 UTC is **112.3 min**. murmur's monotonic clock counted 120.0.
  - The 7.7-min difference is most likely sub-60-s freezes or resume overhead, which the heartbeat threshold of 60 s does not count as freezes. This is an inference, not verified.
- The active clock caps every inter-event gap at 120 s. Long `wait_agent` calls therefore count as only 2 active minutes each, even though they burn monotonic time. That is why active time is about 53-67 min while the monotonic clock reached 120.

| Freeze-excluded interval (UTC) | min | What agents were doing |
|---|---|---|
| 15:38:16 to 19:36:26 | 43.4 | All real work, including the 3 END votes (quorum at TL:1105). |
| 19:36:26 to 19:37:10 | 0.7 | a1 ends its turn (TL:1126). |
| 19:37:10 to 21:37:30 | 20.0 | Nobody working. a2 in `wait_agent 3600000` (TL:1114). a3 in two `wait_agent 600000` calls that timed out (TL:1131, TL:1135). root in `wait_agent 3600000` (TL:1130). Credited as about 5.7 active min. |
| 21:37:30 to 22:32:35 | 9.5 | a3 wakes a2 (TL:1138). a2 re-parks for 60 min (TL:1146). a3 waits 10 min more (TL:1144 to TL:1147), then ends "done" (TL:1157). |
| 22:32:35 to 01:35:51 (cap) | 38.7 | **No events at all.** a2 is still inside its 60-min wait, which would end about 10 min after the cap. root is inside its 60-min wait (TL:1163). 0 active minutes credited. |

- Long-running commands and sleeps: none.
  - The longest tool call was 18.7 s (TL:876). The only sleeps are `time.sleep(.2/.3)` inside smoke tests (TL:1022, TL:1032).
- So **about 69 of 112 freeze-excluded minutes (62%) were post-quorum parking**. Nothing was lost to the cap: main 755b40b was final at A40.8.
- Per agent, active minutes up to its last event:

| Agent | Build | Coordination | Reading others | Inspecting | Testing | Waiting | Total |
|---|---|---|---|---|---|---|---|
| a1 | 6.7 | 11.4 | 8.9 | 7.4 | 1.2 | 6.0 | 43 |
| a2 | 5.2 | 13.2 | 7.6 | 4.7 | 3.1 | 13.5 | 48, plus about 48 uncredited park minutes |
| a3 | 4.5 | 10.9 | 8.1 | 3.3 | 5.0 | 17.7 | 51 |
