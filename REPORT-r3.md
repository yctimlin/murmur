# Murmur round 3: final report (operator)

Generated 2026-10-18 (Asia/Taipei). Branch: https://github.com/yctimlin/murmur/tree/experiment/self-improve-r3
(research main 6b446cf; main untouched, no PR). Arms: **orig** = eec78f8, **base3** = f95eaa1 (round-3 bug-fix base), **solo** = plain `codex exec`.
The peers' own research report is `research/REPORT-r3.md`; this file covers the whole round including the sealed evaluation.

## 1. Outcome in one paragraph
The peer research froze a **null candidate** (no mechanism/default change): every screening task saturated (21/21 runs scored 1.0,
all exec calibrations 8–20 active min), so the protocol-vs-parallelism arms and the peer-count curve were never run. The four bug
fixes form base3. On the sealed open-ended evaluation (4 large tasks × 2 reps, blind Claude judging), base3 vs orig quality difference
is **+0.43 (90% CI −2.54 to +3.40)**; the pre-registered non-inferiority rule (lower bound ≥ −0.5 and time ratio ≤ 1.10) is
**not met** (CI too wide; time ratio 1.03, CI 0.70–1.36), so **base3 is not declared non-inferior or better**. orig failed to deliver
2/8 runs (both the no-work-success bug fixed in base3); base3 delivered 8/8. Both swarm arms scored below solo
(orig −1.71, base3 −1.28 vs solo) while using ~0.63× solo active time and ~4× solo input tokens.

## 2. What the peers found (research phases P0–PD)
- **Noise (C1, same-condition A/A on base3, short saturated tasks):** active-time CV .16 (ledger) / .24 (reserve); input CV .16 / .35;
  single paired A/A active ratio ranged .68–1.78 and input ratio .53–2.15. All scores 1.0, so no quality-noise estimate.
- **Protocol vs parallelism:** not measured (0 murmur-solo, 0 one-peer, 0 two-peer runs). Historical reconstruction of 16 past
  swarm/solo pairs: swarm − solo judge score −0.65 (SD .76; better/tied/worse 2/2/12), input ×5.26, active speed-up ×1.15. Cause unresolved.
  A default-off `MURMUR_ONE_PEER_PROTOCOL=1` switch was added for a future one-peer arm.
- **Peer-count curve:** not identifiable (no 1- or 2-peer data). Prior predictions (70/57/59 min for 1/2/3 peers) remain untested.
- **Gate history:** P0 (bug fixes) → PA → PB → PC1 (C1 18 jobs; rerun after a relay outage 17:18–19:00) → PC2 (C2: new task workflow_store,
  3 exec calibrations, 1.0 in 14–20 min → ineligible) → PD → FROZEN 22:32 Oct 17 with `CANDIDATE.json: null`. Budget used 21/36 jobs.

## 3. Bug fixes (base3 = f95eaa1), each with a test failing before / passing after, independently peer-reviewed
| Bug | Fix / test |
|---|---|
| 1 No-work success: a run with nothing merged exited 0 | `tests/test_bug1_no_work_delivered.py`; nonzero result + delivery diagnostic; peers told to integrate |
| 2 Transient 429 killed the swarm | `tests/test_bug2_rate_limit_retry.py`; bounded retry within cap (covers 429 only; sustained 503 still ends a run) |
| 3 Empty wait result / signals not forwarded | `tests/test_bug3_empty_wait_signals.py`; list-agents after empty wait; SIGINT reaches child group |
| 4 Empty model catalog written | `tests/test_bug4_empty_model_catalog.py`; fail before writing an unusable catalog |
Bug 1 reproduced in the eval: both orig non-deliveries (E-T3b-orig-r1, E-T1b-orig-r2) exited 0 after 15–18 min with peer drafts committed
but nothing merged to main and final message "done".

## 4. Sealed evaluation (AMENDMENT-3 design)
Tasks (open-ended design+build, Python 3.12 offline, solo calibration ≥ 40 active min required; max 2 enlargements per slot):
- **T1b Fieldnotes Hub** – shared research workspace over a 1,249-file non-git notes archive (solo calib 53.3 min).
- **T2 shiftplan** – clinic rota generation, rule checking, requests/swaps, ICS, web UI (51.3 min).
- **T3b CI platform** – self-hosted multi-user CI for a sample monorepo (57.5 min; T3 was 9.4 min).
- **T4b budgetbook** – shared, incremental, auditable household finance app over 18 bank exports (68.1 min; T4 was 6.4 min).
- T5 tinyq (job queue) **excluded**: 27.7 → 12.0 → 13.9 min after two enlargements.
Rubric (sealed before any run, revised after Claude's pre-run review): blind (random ids, history/logs/planning files stripped, identity words
scrubbed, mtimes normalised); Claude installs/runs/inspects; 6 criteria with anchors (coverage 3, correctness-by-running 3, design 2,
robustness 2, code/tests 1, UX/docs 1); unverified claims and length earn nothing; caps for not starting / altering protected input;
2 independent judgments per run (3rd if gap > 1.5), plus swapped-order pairwise base3 vs orig.

### 4.1 Per-arm results (8 runs per arm; non-delivery scores 0)
| Arm | Delivered | Quality (mean overall 0–10) | Active_nf min (mean) | Raw active | Input tokens (mean) | Uncached (mean) |
|---|---|---|---|---|---|---|
| solo | 8/8 | **6.64** | 38.1 | 42.0 | 4.38M | 0.14M |
| orig | 6/8 | **4.93** | 22.9 | 27.5 | 16.59M | 0.39M |
| base3 | 8/8 | **5.36** | 23.1 | 27.2 | 17.07M | 0.41M |

### 4.2 Per task (mean of 2 reps: quality / active_nf min / input M)
| Task | solo | orig | base3 |
|---|---|---|---|
| T1b | 7.93 / 45.1 / 4.96 | 3.92 / 19.0 / 11.86 | 7.72 / 26.5 / 21.17 |
| T2 | 6.60 / 27.9 / 3.25 | 7.62 / 23.0 / 15.37 | 5.35 / 20.7 / 14.63 |
| T3b | 4.90 / 34.0 / 3.90 | 3.62 / 23.1 / 14.83 | 4.12 / 25.4 / 19.28 |
| T4b | 7.15 / 45.4 / 5.41 | 4.55 / 26.6 / 24.29 | 4.25 / 19.8 / 13.20 |
Per run quality (r1, r2): solo T1b 8.05/7.8, T2 8.8/4.4, T3b 7.9/1.9, T4b 7.5/6.8; orig T1b 7.85/0*, T2 7.2/8.05, T3b 0*/7.25,
T4b 7.25/1.85; base3 T1b 7.64/7.8, T2 2.55/8.15, T3b 6.9/1.35, T4b 1.4/7.1 (* = non-delivery).

### 4.3 Pre-registered contrasts (paired over 4 tasks, t-interval 90%)
| Contrast | Mean [90% CI] |
|---|---|
| base3 − orig quality | +0.43 [−2.54, +3.40] |
| orig − solo quality | −1.71 [−4.23, +0.80] |
| base3 − solo quality | −1.28 [−2.65, +0.08] |
| base3 / orig active_nf | 1.03 [0.70, 1.36] |
| orig / solo active_nf | 0.63 [0.43, 0.83] |
| base3 / solo active_nf | 0.63 [0.45, 0.80] |
| orig / solo input | 3.85 [2.62, 5.09] |
| base3 / solo input | 4.04 [2.74, 5.33] |
| Pairwise base3-preferred rate (6 both-delivered pairs × 2 orders) | 0.17 [−0.04, 0.37]; order agreement 100% (orig won 5 pairs, base3 1) |
**Gate decision:** `base3_noninferior = false`, `base3_better = false` (lower bound −2.54 < −0.5; time ratio 1.03 ≤ 1.10 but CI to 1.36).
No candidate arm existed, so no KEEP decision applied. Note the pairwise comparison excludes the two orig non-deliveries.

### 4.4 Judge consistency and blinding
22 delivered runs × 2 judgments: mean |j1 − j2| = 0.23; no third judgment needed. Judge guessed single-agent vs team correctly 82% of the
time, so blinding against arm type is weak (team-style artifacts remain visible).

### 4.5 Claude review notes (common failure modes)
- **Partial deliveries dominate the low scores** (1.35–2.55): swarm runs ended after 18–30 active minutes with only part of the system
  integrated, e.g. T4b-base3-r1 "only a parser module was delivered, no app/CLI/UI, no persistence"; T4b-orig-r2 "most of the brief not
  implemented; CLI cannot import"; T3b-base3-r2 "no dashboard, fake artifacts, unauthenticated trigger/cancel".
- **Unverified correctness claims**: T2-base3-r1 rota "ignores contract hours … rule check reports 0 conflicts"; missing DESIGN.md.
- **Solo variance**: solo also produced small builds (T2-solo-r2 4.5 min, 497 lines, 4.4; T3b-solo-r2 12.5 min, 1.9 with auth/retry bugs).
- **Security/robustness gaps** recur (unauthenticated admin paths, data loss on revert/regenerate).

## 5. Amendments (all logged in LOG.md and sealed under /srv/murmur-sealed/r3 before results were unblinded)
- **AMENDMENT-1** (pre-run): mutation-scorer robustness fixes. **AMENDMENT-2**: eval lab lacked bin/mutation.py (IndexError on empty output); sealed scorer installed unchanged.
- **AMENDMENT-3** (user, Oct 18 01:32): hidden-test pass-rate gates were the wrong metric → open-ended tasks, blind Claude rubric, only a
  ≥ 40 min solo floor; addendum 02:01: under-floor tasks enlarged (≤ 2 per slot); hidden-test score_error ignored.
- **AMENDMENT-4** (Oct 18 07:10, approved): box freezes (7 windows, 8.7–29.9 min, e.g. 05:13/05:37/06:12) inflated runner active time by
  up to 2 min per gap and wall time fully; all time rules use **active_nf** (gaps reduced by overlap with box-wide freeze windows, then
  capped at 120 s), computed identically for all arms; raw active and wall reported.
- **AMENDMENT-5** (Oct 18 16:36): the original-input checksum check covered all input, but T3b's brief requires changing sample-repo;
  check restricted to paths briefs protect (T1b archive, T4b exports/; T2, T3b none); all 10 T3b judgments re-judged blind.

## 6. Superseded/aborted evaluations (not counted)
1. Hidden-test tasks X1–X5 (Oct 17 22:35): solo 4.6–14.3 min, pass .81–1.0 → aborted by user ("tasks too small").
2. Large hidden-test tasks X1a–X5b (Oct 18 00:00–01:30): solo 14–59 min but pass .93–1.0 → superseded by AMENDMENT-3.
3. Open tasks T1, T3, T4, T5, T5b, T5c: below the 40-min floor (6.4–27.7 min).

## 7. Murmur / harness bugs observed
- orig: no-work success (2/8 eval runs) – fixed in base3 (bug 1).
- Sustained relay 503 ends a swarm (Codex gives up after reconnects; bug-2 fix covers 429 only). Relay outage Oct 17 17:18–19:00 invalidated C1 jobs 03–17 (withdrawn, rerun).
- murmur cannot write its result copy next to a read-only input (`Permission denied … .partial`); result still in origin.git (harmless here).
- murmur's run.json `seconds` uses a clock that stops during VM suspension (16.7 min vs 83.9 wall on E-T2-base3-r1).
- Harness (operator) bugs fixed: scheduler recorded no error on setup failure (C1 looked complete); runner `exec -a` emptied sys.executable;
  eval lab r3.git initially empty (8 jobs withdrawn as infra); scorer missing in eval lab.

## 8. Limitations
- n = 4 tasks × 2 reps (df = 3): intervals are wide; non-inferiority could not be shown either way.
- Large solo variance on the same task (T2 solo 51.3 vs 4.5 min; T3b 55.6 vs 12.5) – solo-relative ratios are noisy.
- Box freezes during runs; corrected by AMENDMENT-4 but freeze detection relies on box-wide session silence.
- Blinding against single-vs-team style is weak (82% guess accuracy).
- Tasks are operator-written (T1–T5) and Claude-enlarged (T1b, T3b, T4b); the judge is also Claude.
- Round-2 judge prompts remain in ~/.codex/sessions (round 3 used new prompts/rubric).
- No protocol-vs-parallelism or peer-count data: the round's original research questions remain open.

## 9. Files
Box: /workspace/self3/LOG.md, eval/open-decision.json, eval/open-runs.json, eval/freeze-active.json, eval/judge-open/*, eval/open-rubric.md,
eval/SEALED.md, review/*.md (Claude reviews), labdata/repos/r3-work/research/*.
