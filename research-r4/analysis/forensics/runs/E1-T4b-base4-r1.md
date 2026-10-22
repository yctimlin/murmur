# E1-T4b-base4-r1 — forensic notes

Sources: timeline `timelines/E1-T4b-base4-r1.md` (TL = line), raw rollouts in `lab/ws/E1-T4b-base4-r1/codex-home/sessions/2026/10/20/`, prompts, origin.git, judges j1/j2.

## 1. Outcome
- Score **1.6** (j1 1.7, j2 1.5) = collapse. Coverage 1/1.
- Judge penalties (quoted): "Most of the brief is missing: no API, UI, matching, categorisation, reports, auth, migrations or backup"; "Date parsing is wrong: Kiwi MM/DD/YY becomes 2001 and Northbank slash dates have month and day swapped"; "Kiwi overlap rows are not deduplicated because the changing ref suffix is part of the dedup key"; "UnionSav credits imported with wrong sign (all credits negated)"; "DATA_FINDINGS/DESIGN cite tests and features that do not exist".
- Delivered: ~362 lines of Python (`core.py`, `cli.py`, `bench.py`, `data_findings.py`, `test_runner.py`, 3 tests). No PR.md.
- Active 30.17 min (timeline span 26.9), wall 109.4. Input 7.30M tokens, output 30k. 9 commits.

## 2. Phase timeline (active minutes)
| Phase | A | Who | What |
|---|---|---|---|
| Spawn | 0.0-0.5 | root | spawns a1-a3 |
| a3 drops out | 0.5-1.0 | a3 | reads prompt, then answers `done` (TL:70-74) |
| Claims | 1.0-1.8 | a1, a2 | a1 claims ingestion core (TL:84). a2 claims the same 7 s later (TL:89). a1 pivots to "documentation + benchmark/import-summary scaffolding" (TL:100) |
| Drafts | 1.8-5.8 | a2: ingestion core (34b40a6, A5.6). a1: bench + DATA_FINDINGS (3af92e4, A4.5) |
| Ranking | 7.6-10.5 | a2 ranks first (TL:226), a1 agrees (TL:267); "a3 — no draft receipt" |
| Integration | 10.6-12.3 | a2 pushes to main (TL:277), a1 cherry-picks its artifacts (TL:301) |
| "Review" / polish | 12.3-20.1 | a1: dedup canonicalisation (18839fa), inventory fixes, IMPORT_SUMMARY, stdlib test runner (775103d). a2: revert re-import fix, review notes |
| Turn ends | 19.8 (a2), 26.5 (a1) | A21-26: a1 waits on `wait_agent` and sends `send_message` to /root twice (TL:516, 529), then `done` |

No plan, no PR.md, and no requirements split was ever written. Sections 2-9 of the brief were never claimed by anyone.

## 3. Per-agent account
**a3**: 1 call. The forked session context has root's launcher prompt as its user message ("You are the launcher ... Never ... read or edit files, or run commands"). The NEW_TASK then tells it to read `prompts/a3.md`. Reasoning headings (rollout `...0d07...jsonl` l.26): "**Confirming launcher-only task adherence** | **Resolving conflicting parent and user instructions** | **Finalizing agent with done status**". SAY/TURN_END `done` at A1.0 (TL:71-74). Nobody woke it: 0 `followup_task` calls in the run.

**a2**: built the only application code. The draft core took about 4 active min (A1.4-5.6, 230 lines). It ranked the drafts, integrated to main, made one fix (743c8f5) and posted review notes. From A13 on it mostly polled: "**Waiting for parent instructions**" (A13.4, TL:349), `wait_agent` 10 s loops, `list_agents`. It ended at A19.7 after "**Deciding to finalize child agent for parent completion**". TURN_END: "Completed and integrated the winning ingestion draft on `origin/main` ... Posted draft rankings, findings, integration receipt, and review notes" (TL:487).

**a1**: gave up the core after the claim collision (TL:100: "PIVOT a1: since a2 claims parser/SQLite core, I will build the auditable documentation + benchmark..."). It wrote DATA_FINDINGS before any core existed (A4.1). After integration it hardened the ingestion slice: dedup canonicalisation, test runner, IMPORT_SUMMARY with an "honest note that matching/categorisation are not yet implemented" (TL:456). Its final review (TL:509): "latest origin/main 775103d passes ... (3/3) ... Remaining core limitations are documented honestly in IMPORT_SUMMARY." It then waited about 5 active min (about 60 wall min) for /root, messaged /root twice, and ended with `done` (TL:535). That single word mirrors root's own end instruction.

## 4. Coordination costs
- Claim collision (a1/a2, A1.2 vs A1.4) and a1 pivoting away from the core: the team had 1 builder instead of 3.
- Duplicate integration: a2 also cherry-picked 3af92e4 after a1 had already pushed it (TL:320-334). This was harmless and lost no work.
- Ranking had 2 voters for 2 drafts and took about 3 active min.
- About 25% of a2's and a1's active time went to `wait_agent`/`list_agents` polling for a "parent" that never acts.
- No INTEGRATION_LOSS: draft branches equal main content.

## 5. Penalty -> cause map
| Penalty | Cause in log |
|---|---|
| ~90% of brief missing | Never claimed or planned. The only claims were ingestion (a1, a2) and docs/bench (a1). After integration nobody wrote the PR.md plan the prompt requires. Agents treated the post-integration state as the end ("DONE winner integration", TL:281). a3 absent from A1.0 |
| Kiwi dates parsed as 2001 | A5.1 (TL:172): a2 appends `'%m/%d/%y'` *after* `'%y/%m/%d'`. Quarantine drops from 573 to about 6 and is read as success: "all Kiwi date quirks handled" (TL:211). Output dates were never checked |
| Northbank day/month swap | Same `date_iso` format order (`%d/%m/%Y` before `%m/%d/%Y`, TL:379). a2 grepped the list at A14.9 but did not test it |
| Kiwi ref suffix in dedup key | a1's DATA_FINDINGS (A4.1) noted "changing `ref ####` suffixes", but a1's dedup fix (18839fa, A15.2) normalised only case, whitespace and decimals |
| UnionSav sign | In a2's draft (A3.5). No visible check; totals were never inspected per account |
| Docs cite nonexistent tests | a1's DATA_FINDINGS (3af92e4, A4.1), written aspirationally before the code existed: "`test_parsers.py` covers all six families; `test_import_idempotency.py` ..." |
| No DESIGN depth / README stub | a2 draft stubs (DESIGN 7 lines). Never revisited |

## 6. Decision points
1. **A1.0, a3 quits** (TL:70): conflict between the inherited launcher prompt and the NEW_TASK, resolved toward the launcher.
2. **A1.8, a1 pivots off the core** (TL:100): a1 does not take a different hard part (matching, UI) and picks docs/bench instead.
3. **A10.6-11.0, integration declared the finish line**: "DONE winner integration" (TL:281). The plan step ("Plan the whole before you split it ... first section of PR.md") never happens.
4. **A13.4, a2 waits for the parent**: "**Waiting for parent instructions**" (TL:349). It ends at A19.7 "for parent completion".
5. **A21.0, a1's review checks the slice, not the brief** (TL:509), then it waits for /root and ends with `done`.

## 7. Failure-mode tags
- **ROLE_INHERITANCE** (new tag: a forked peer adopts the launcher's role or authority from inherited context, either quitting or deferring to /root as "parent"): 3 agents. a3 quit at A1.0. a2 "Waiting for parent instructions" and ended "for parent completion". a1 sent 2 `send_message` to /root and posted "Parent should pull latest main" (TL:316).
- PREMATURE_END: 3 (a3 A1.0, a2 A19.8, a1 A26.5, all with the brief largely open).
- IDLE_PEER: a3 (whole run, never woken). a1 and a2 polling about 4-5 active min each.
- SCOPE_SHRINK: 1. The team silently reduced the brief to an ingestion slice. Only IMPORT_SUMMARY admits it.
- DRAFT_AS_PRODUCT: 1. The 4-minute a2 draft is the product core.
- SELF_REFERENTIAL_VERIFICATION: 2. The quarantine count fell, so "date quirks handled" (TL:211). Final review "passes 3/3" (TL:509).
- DUPLICATE_WORK: 1 (minor cherry-pick).
- INTEGRATION_LOSS, MERGE_CONFLICT, REVIEW_LOOP, CAP_HIT, PROVIDER_ERROR, WALLCLOCK_RUSH: none.

## 8. Time accounting (active min, estimated by attributing each inter-call gap to the next call)
| Agent | build | coordination (board/msg) | reading others | testing | idle/wait | total |
|---|---|---|---|---|---|---|
| a1 | 5.6 | 9.2 | 3.4 | 3.5 | 4.2 | 26.1 |
| a2 | 5.6 | 5.3 | 3.9 | 0.9 | 3.3 | 19.3 |
| a3 | 0 | 0 | 0 | 0 | 0 | 0.3 (quit) |

Building totalled about 11 active minutes across the team.
