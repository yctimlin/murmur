# Round-4 forensics: what actually happens inside the runs (10-21, directive 14:02)

## Scope and method
- **Runs:** all 31 runs judged by 10-21 14:02, from the arms base4 (9), C1 (10), C2 (8) and solo (4) on tasks T1b, T2,
  T3b and T4b. The four infra-withdrawn runs (A6) are not covered.
- **Sources:** raw logs only.
  - Every agent's Codex rollout: tool calls and outputs, reasoning headings, assistant text, inter-agent mail, and
    turn start/end, where the final message gives the reason for stopping.
  - Message-board posts from sqlite.
  - `origin.git`, all branches.
  - The judges' full written evidence.
- **Tools:**
  - `tools/forensics_extract.py` merges these sources into one chronological stream per run:
    `analysis/forensics/timelines/RID.md`. Each line is stamped with freeze-excluded active minutes (A) and Taipei
    wall time.
  - `tools/time_accounting.py` charges each agent's active time to the kind of tool call it was spent on:
    `analysis/forensics/time_accounting.json`.
- **Reading:** seven read-only Claude analysts read every timeline, plus raw rollouts, prompts, git and judge text where
  needed, following `analysis/forensics/PROTOCOL.md`. They wrote `analysis/forensics/runs/RID.md` (31 files: phases,
  per-agent account, penalty→cause map, decision points with TL line references, tags, time) and 7 contrasts in
  `analysis/forensics/contrasts/`. The PI checked the key claims directly against the raw rollouts and the murmur
  source; they are listed under each finding.
- **Limitations:**
  - The time classifier is approximate (about ±2 min per cell).
  - Tag counts are analyst judgements; the counts below were re-checked by the PI where stated.
  - The T4b C1-vs-C2 contrast was written by the PI because that analyst failed on API errors.

## 1. Headline: three root causes dominate, and only one of them is about collaboration design

### F-1. A false budget signal ends swarm runs early ("WALLCLOCK_RUSH")
This is the dominant cause, and it is an environment × design interaction.
- **The mechanism.**
  - murmur enforces its 120-minute cap with `proc.wait(timeout)` on `time.monotonic()`
    (`murmur/src/murmur/cli.py:831-840`, PI-verified). The monotonic clock barely advances while the VM is frozen.
  - The agents, however, estimate their budget from `date` and from board-post timestamps, which are wall time.
  - The host freezes the VM for about 75% of wall time. Peers therefore believe the cap is near after only 15-30
    active minutes.
- **Example posts:**

  | Run | Stamp | Post |
  |---|---|---|
  | E1-T1b-base4-r1 | A19.8 | "Hard cap in ~4m (start21:08, now23:04)" |
  | E1-T3b-C1-r1 | A23.4 | "hard cap started15:03 =>17:03 (~6min)" |
  | E1-T4b-C1-r3 | A24.8 | "now past 120m hard cap" |
  | E1-T1b-C2-r2 | A29.3 | "hard cap reached (~120m since activation)" |

  In E1-T1b-C2-r2, a1 copied that last claim within 20 s and marked 20 ledger rows DESCOPED.
- **Contagion.** One peer's countdown is broadcast on the board, and every peer ends within about 1 active minute of
  the others.
- **Counts (analyst-confirmed).**
  - Swarm: 19 of 27 runs.
  - Solo: 0 of 4. Solo gets the same "You have up to 120 minutes" sentence and once checked `date` past 120 wall
    minutes (T3b A33.3), but kept working until its tests were green. With no peers, there is no shared deadline
    belief.
  - Not affected: T2-C1-r1, T2-C2-r1, T2-base4-r2, T4b-C2-r3, T2-C1-r2 and T1b-C1-r2, plus the two base4 T4b runs,
    which collapsed earlier.
- **Outcome evidence.**
  - Non-capped swarm runs end at 60-156 wall minutes (median about 117), all with exit 0.
  - The two runs that truly reached murmur's cap ran 535-598 wall minutes.
  - Solo runs last 128-233 wall minutes. Their active time is 36-58 min (runner), against 22-44 for swarms.
- **Effects in the logs.**
  - The build phase ends by declaration:

    | Run | Stamp | Post |
    |---|---|---|
    | E1-T4b-C2-r2 | A14.0 | "~30min to 120m hard cap. Need wrap documentation" |
    | E1-T4b-C1-r2 | A25.6 | "No broad scope additions" |

  - No swarm run had a cleanup or refactor pass, so draft leftovers and dense code remain.
  - Shortcut fixes are taken "at deadline" (E1-T3b-base4-r1 A22.7: narrowing secrets to 16+ characters).
  - Hardening after the first green suite is skipped. Solo found the T3b cli-only artifact bug exactly in that phase
    (A24.3); C1-r1 had no such phase.
- **Consequences.**
  - Swarm active time, and therefore the swarm "speed-up" against solo, is partly an artefact of stopping early.
  - Part of the swarm-versus-solo quality gap is a scope cut, not a coordination weakness.
  - Arm differences of about ±0.5 in E1/E2 are of the same size as the variation caused by when the freezes happen to
    fall. Compare T1b-C2-r1 (rush after the build, 7.85) with T1b-C2-r2 (rush during the build, 2.55).

### F-2. Peers inherit the launcher's role ("ROLE_INHERITANCE"; murmur spawn bug)
- **The mechanism (PI-verified in the raw rollout of E1-T4b-base4-r2/a2).**
  - Peers are spawned as forks of the root thread.
  - The first user message in a peer's context is the root's launcher prompt: "You are the launcher for 3 peer
    agents. You do not work on their objective yourself ... Never ... read or edit files, or run commands".
  - Then the NEW_TASK arrives: "read prompts/aN.md".
- **Failures it caused.**
  - **Quits:**

    | Run | Peer | Stamp | Reasoning heading | Result |
    |---|---|---|---|---|
    | E1-T4b-base4-r2 | a2 | A0.7 | "Deciding to defer action due to instruction conflict" | `done` |
    | E1-T4b-base4-r1 | a3 | A1.0 | "Confirming launcher-only task adherence" | `done` |

  - **Deferral to a "parent" that never acts:**
    - E1-T4b-base4-r1 a2 "Waiting for parent instructions" (A13.4), then ended "for parent completion".
    - E1-T4b-base4-r2 a3 "root should document cuts" (A16.0).
    - E1-T1b-C1-r2 a2 "Waiting for root status confirmation" before parking until the cap.
  - **DMs to the launcher:**

    | Run | Score | DMs |
    |---|---|---|
    | T1b-C1-r2 | 2.45 | 26 |
    | T2-C1-r2 | 2.25 | 33 |
    | T4b-base4-r1 | 1.6 | 2 |
    | T4b-C2-r3 | 6.65 | 9 |

    The other 27 runs have 0.
- **Counts.** Quits: 2 of 27 swarm runs (both base4 T4b collapses). Launcher-directed behaviour: in 4 of 5 collapses.

### F-3. Verification certifies what was built, not what the brief asks ("SELF_REFERENTIAL_VERIFICATION")
This is the main collaboration-design defect. Peers verify that their artefacts run and that their own tests pass.
Requirement rows are closed on the builder's evidence. Nobody independently checks the brief against the real input.
- **E1-T2-C1-r2:** the rule monitor checks only coverage and night eligibility. It reads "0 violations" for every rule
  the app never modelled; 32h staff were rostered 240h/month. All END posts cite "tests 3/3, 0 violations". a2 saw a
  shift wiped ("North day needs 2 nurse(s), has 0") and wrote it off as "intentionally removing coverage" (TL:755-762).
- **E1-T4b-C2-r2:** the "independent" oracle uses the importer's own row identity. Its expected totals were pasted
  from its own output (A4.0, TL:158-160), which locked in the Kiwi double count that j1 marked severe.
- **E1-T4b-C2-r1/r3:** recurring detection was "verified" by a synthetic `COFFEE` test and timing. Nobody ran it on
  the real book, and the judges found it misses Netflix or flags everything.
- **E1-T3b-C2-r2:** an acceptance check accepted "skipped OR cached" where the brief requires a cache hit (A3.3). That
  loophole is the run's main coverage penalty.
- **Ledgers were stamped, not tracked:**
  - T3b-C2-r2: 38 rows marked DONE in one commit (A18.5), all "verified by selftest".
  - T4b-C2-r3: 11 rows batch-closed at A36.6.
  - T2-C1-r2: the draft shipped a ledger with all 10 rows already DONE.
  - T1b-C1-r2: 7 of 16 rows were pre-marked DONE from the draft.
- **Counts.** Analysts tagged it in 19 of 31 runs, including 1 solo (T1b, whose UI was never run). It appears in all
  5 collapses.
- **Contrast.**
  - High runs did ground their checks:
    - T2-C2-r1 a1 wrote an oracle that recomputes the rules independently (A3.1) and caught real defects.
    - T4b-C1-r4 a1 inventoried every malformed row before any product code (A2.9).
    - C1-r1 runs used Chrome captures of user flows.
  - Solo T2 checked the generated rota against contract targets at A10.2, not just the violation count.

## 2. How the five collapses happened (decisive events)
| Run | q | Chain (active min, TL = timeline line) |
|---|---|---|
| T4b-base4-r1 | 1.6 | F-2 quit a3 A1.0 → a1/a2 claim the same core (A1.2/1.4), a1 pivots to docs → "DONE winner integration" taken as the finish (A11.0); PR.md plan never written → gaps handed to "parent" → unilateral turn ends A19.8/26.5. About 11 build-minutes in total. |
| T4b-base4-r2 | 1.7 | F-2 quit a2 A0.7 → core claim collision, a3 retreats to an unused helper → "Winner integration done ... You can stop/finish your turn" (A15.3) → missing parts listed and routed to root (A16.0). |
| T2-C1-r2 | 2.25 | Drafts framed as whole mini-apps (A0.7) → a3's 131-line draft ships a PR.md with plan + ledger all DONE (A7.3) → "already includes Plan ... Requirements ledger all DONE" (A12.3) → no build-out at all → END quorum on the draft's own "0 violations" (A14.7-17.0). F-3. |
| T1b-C1-r2 | 2.45 | Drafts split by layer (A2.3-4.8) → 226-line partial base → ledger 16 coarse rows, 7 pre-DONE (A18.7) → rows closed by 1-55-line commits; search checks never used an experiment ID (the judges' crash) → END A43.4 → a2 parks "waiting for root" until the cap. F-3 + F-2. |
| T1b-C2-r2 | 2.55 | a1 claims ACCEPTANCE and no one claims SPINE; a2 expects root to build it (A0.9) → spine only at A17.2 (151 lines, JSON stub as the "UI"); duplicate spine A11.2-24.6 discarded → F-1 "hard cap reached" at A29.3 → 20 rows DESCOPED; the "UI" check was status-200. |

The C1 ledger and END quorum prevented the base4-style unilateral ending (0 such ends in C1/C2). However, a ledger
whose rows are closed by the builder's own evidence is satisfied by a tiny product (T2-C1-r2, T1b-C1-r2). C1 moved the
failure from "stop alone" to "stop together on a self-certified draft".

## 3. Taxonomy (counts over 27 swarm + 4 solo runs; analyst tags, PI re-checked where marked *)
| Failure mode | Swarm runs | Solo | Note |
|---|---|---|---|
| WALLCLOCK_RUSH* | 19/27 | 0/4 | F-1; ends the build or hardening phase by declaration |
| SELF_REFERENTIAL_VERIFICATION | 18/27 | 1/4 | F-3; in all 5 collapses |
| SCOPE_SHRINK (silent narrowing) | 15/27 | 0/4 | often a consequence of F-1 (DESCOPED "hard cap") or of coarse ledgers |
| DUPLICATE_WORK | 17/27 | – | duplicated browser harnesses and re-found seams; duplicate spine (T1b-C2-r2) |
| MERGE_CONFLICT (minor) | 15/27 | – | mostly PR.md; about 3 agent-min per run; never decisive |
| DRAFT_AS_PRODUCT (decisive) | 4/27 | – | 4 of the 5 collapses; milder form = DRAFT_LEFTOVER (dead draft code shipped) in ≥4 high runs |
| IDLE_PEER | 9/27 | – | mostly short parks; decisive only in the base4 quits and the C1-r2 cap |
| INTEGRATION_LOSS | 8/27 | – | mostly unmerged draft branches by design; never decisive |
| REVIEW_LOOP (re-votes after a push) | 8/27 | – | C1/C2 END-void rule; costs 1-3 min |
| ROLE_INHERITANCE* | 2 quits + 4 launcher-DM runs | – | F-2 |
| CAP_HIT / PROVIDER_ERROR | 1 / 1 | – | |
| Dense one-shot code (judge "code" 5-6) | 27/27 | 4/4 | a model trait, not a swarm effect; no run ever reviewed readability |

## 4. Where the time goes (tools/time_accounting.py; freeze-excluded peer agent-minutes)
| Group | n | Run active | Agent-min | Build (edit/read/git) | Verify (test/smoke) | Others' work (git fetch/show/merge) | Coord (board/mail/wait) | Main lines |
|---|---|---|---|---|---|---|---|---|
| solo | 4 | 37.8 | 34.4 | 11.6 | 21.1 | 1.5 | 0 | 4579 |
| base4 (non-collapsed) | 7 | 29.0 | 79.6 | 16.7 | 37.6 | 19.7 | 5.5 | 3188 |
| C1 (non-collapsed) | 8 | 29.4 | 84.5 | 16.1 | 38.8 | 19.8 | 9.5 | 4807 |
| C2 (non-collapsed) | 7 | 28.9 | 82.1 | 20.4 | 34.4 | 14.2 | 12.5 | 5251 |
| collapses | 5 | 31.9 | 79.0 | 16.0 | 10.4 | 9.3 | 43.2 | 412 |

- **Scaling.** A healthy swarm spends 2.3-2.5x solo's agent time but only about 1.5x its build time. It delivers
  roughly the same amount of code (3.2-5.3k lines on main against 4.6k).
- **Where the surplus goes:**
  - Duplicated verification: about 37 agent-min against 21 for solo, with each peer re-testing and re-capturing.
  - Reading and integrating others' work: 14-20 agent-min.
  - The draft-and-rank ritual: about 15 agent-min, which also delays product code on main to A6-9. Solo writes
    full-scope modules from A2.7.
- **Collapses** are coordination-dominated: 42-67% of peer time goes to board, mail and wait, and almost none to
  verification.
- **Idle time** inside turns is near 0 in healthy runs. The runs do not lose time waiting; they lose it at the end,
  through F-1.

## 5. What this means for the E1/E2 results so far
- **E1/E2 (C1, C2 vs base4) measured mechanism effects inside a run window cut short by F-1.** That window is set by
  when the freezes fall, which is random with respect to arm.
  - C1 removed the base4 unilateral-stop collapse (0/10 C1 runs stop alone).
  - C1 added a new collapse route: a self-certified draft (2/10).
  - C2's spine helps when it is claimed early (T1b/T2-C2-r1) and stalls the run when nobody claims it (T1b-C2-r2,
    T4b-C2-r3).
  - Neither mechanism touches F-1 or F-3, which matches P_keep staying near 0.3-0.4 for both.
- **The swarm-versus-solo comparisons inherit F-1.** Solo is not affected, so swarm active time is biased down
  (looking faster) and swarm quality is biased down (scope cut).

## 6. Mechanisms derived from the evidence (each with the logs it fixes and the predicted log signature)
**M0. Truthful budget and clean roles.** These are infrastructure bug fixes, not collaboration features; they apply to
F-1 and F-2.
- **Budget:** murmur exposes the clock it actually enforces. The launcher writes elapsed and remaining minutes of its
  monotonic cap clock to a file every 30 s, and the peer prompt names that file as the only budget. It also says that
  wall clock and post timestamps are not the budget (the machine may sleep).
  - Fixes the posts listed under F-1.
  - Predicted signature:
    - no "hard cap"/"min left" posts before budget minute ~100;
    - turn ends are no longer clustered right after a countdown post;
    - run active spans grow (prediction: median ≥ 40 active min, against 29);
    - hardening and cleanup commits appear after the first all-green suite;
    - no DESCOPED rows with a time reason.
- **Roles:** spawn peers without the launcher's context, and tell peers that the launcher never acts or answers.
  - Fixes the F-2 quits and the "waiting for parent" episodes.
  - Predicted signature:
    - no peer TURN_END before A2;
    - no THINK headings containing "launcher"/"parent conflict";
    - 0 DMs to /root.

**M1. Grounded, cross-checked requirements (addresses F-3; the collaboration mechanism).**
- **Ledger rows.** They come from the brief's own sentences (one capability or constraint per row) and are written
  after the base is chosen. Every row starts OPEN, and a draft can never close a row.
- **Closing a row.** A row is DONE only when a peer who did not build it verifies it as the user would meet it on the
  REAL input, and posts `VERIFIED <row> <evidence: command + observed output>` or `FAIL <row> <what>`.
  - "As the user would meet it" means the browser for UI rows and the real data files for data rows. It never means
    re-running the builder's tests.
  - Builders do not verify their own rows.
- **Assignment and END.** Verification work is assigned by rotation, so each peer verifies different rows and repeat
  testing goes away. END requires every row to be VERIFIED, or DESCOPED with a brief-based reason.
- **Fixes:** T2-C1-r2 (rule rows such as "contract hours" would FAIL on 240h), T4b-C2-r2 (Kiwi rows checked on the
  real file), T4b-C2-r1/r3 (recurring checked on the real book), and the pre-closed ledgers of T1b-C1-r2 and T2-C1-r2.
- **Predicted signature:**
  - the ledger commit has 25 or more OPEN rows;
  - VERIFIED/FAIL posts by non-authors cite real-input output;
  - at least one FAIL per run is followed by a fix commit;
  - verify agent-minutes are partitioned, not duplicated (the duplicated-harness pattern disappears);
  - no batch DONE edits.

**Deferred (weaker or later):**
- Removing the draft ritual (about 15 agent-min; T3b-base4-r2 shows that it decided nothing). It is not decisive for
  quality, and its effect on the collapse modes is mixed: directions-only drafts are what saved T2-C1-r1.
- A readability pass. Code scores 5-6 everywhere, including solo; this is a model trait.
- A spine with forced ownership (C2). Its stall mode is real, but C2 is at cap and is not carried forward.

## 7. Files
- `analysis/forensics/PROTOCOL.md`: the analyst protocol.
- `analysis/forensics/timelines/RID.md`: event streams.
- `analysis/forensics/runs/RID.md`: 31 per-run notes.
- `analysis/forensics/contrasts/`:
  - `T4b-collapse.md`
  - `T4b-C1-vs-C2.md`
  - `T2-collapse.md`
  - `T1b-collapse.md`
  - `baseline-vs-solo.md`
  - `T3b-C1C2.md`
  - `C2-spine.md`
- `analysis/forensics/time_accounting.json`, plus the tools `tools/forensics_extract.py` and
  `tools/time_accounting.py`.
