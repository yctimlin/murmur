# Forensics protocol (round 4, written 10-21 14:20 by the PI)

You are a forensic analyst of multi-agent coding runs. Your job is to read the REAL logs of a few runs and write
evidence-based per-run notes. No speculation without evidence; every claim gets a quote plus an active-minute stamp
(`A12.3`) and, where possible, a line number in the timeline file (`TL:465`).

## Setup of the experiment (context)
- murmur = a launcher that runs one Codex "root" agent which spawns 3 peer agents (a1, a2, a3), each with its own git
  clone, sharing a bare repo `origin.git` and a message board (posts in channels such as `tasks`, `findings`). The
  root only spawns and waits. A run ends when every peer has ended its turn (a peer that ends its turn is not woken
  again unless someone sends it a follow-up task). Hard cap 120 min (monotonic clock).
- Arms: `base4` = baseline murmur prompts; `C1` = base4 + consensus termination (requirements ledger in PR.md, peers
  "park" instead of exiting, the run should end only on an `END <sha>` quorum of all peers on the same main commit);
  `C2` = C1-style plus a "spine" (one integrated skeleton early) and acceptance checks; `solo` = one `codex exec`
  agent alone on the same task. All runs: model gpt-6-astra, reasoning effort high.
- Tasks: large open-ended product briefs (T1b field-notes app, T2 clinic shift planner, T3b, T4b budget book from bank
  exports). Brief: `/workspace/r4/lab/tasks/<T>/brief.md`.
- Quality = mean of 2 blind Claude judges (0-10), rubric `/workspace/r4/prereg/RUBRIC.md`. A score < 3 = "collapse".
- The VM freezes often (wall time >> active time). Use active minutes (A) for durations, never wall time.

## Sources for run RID (read-only! do not modify, move or delete anything; do not run git commands that write)
- Timeline (start here): `/workspace/r4/analysis/forensics/timelines/RID.md` — header with judge scores/severe
  issues and per-agent summary, then a merged chronological stream: `A<active min> | <Taipei time> | <who> | <kind> |
  <content>`. Kinds: CALL/FCALL (tool call, input truncated), OUT (tool output head), THINK (reasoning heading),
  SAY (assistant text), MAIL (inter-agent message), POST#channel (board post), COMMIT (git, all branches),
  TURN_START/TURN_END (TURN_END carries the agent's final message = WHY it stopped). Use grep on it; it is large.
- Raw rollouts (when the timeline truncates something you need):
  `/workspace/r4/lab/ws/RID/codex-home/sessions/**/rollout-*.jsonl` (one per agent; solo has one).
- Prompts actually given: `/workspace/r4/lab/ws/RID/prompts/*.md` (swarm) or `/workspace/r4/lab/ws/RID/prompt.md` (solo).
- Git: `git --git-dir=/workspace/r4/lab/ws/RID/work/origin.git log --all --stat` (swarm) or
  `/workspace/r4/lab/ws/RID/repo/.git` (solo). Delivered tree: `/workspace/r4/lab/results/RID/delivered/`.
- Judge evidence (full text): `/workspace/r4/judge/E1/RID.j1.md`, `RID.j2.md` (+ `.json`).
- Runner result: `/workspace/r4/lab/results/RID/result.json`.

## What to write: `/workspace/r4/analysis/forensics/runs/RID.md` (one file per run), sections:
1. **Outcome**: score, judges' top penalties (quote), delivered size (lines of code on main), active min, tokens.
2. **Phase timeline** (active minutes): e.g. reading brief, claiming, drafting, ranking/selection, building,
   integration, review/verification, END votes, turn ends. Note what happened in each phase and who did it.
3. **Per-agent account**: what each agent built, how much time on own building vs coordination (board, reading
   others' code/branches, reviewing, re-testing others' work) vs waiting/idle; when and WHY it ended its turn (quote
   the TURN_END message and the reasoning that led to it).
4. **Coordination costs**: duplicated work (two agents building the same thing), merge conflicts/rebases, work that
   stayed on branches and never reached main, repeated reviews/re-votes, messages that were ignored.
5. **Penalty -> cause map**: for each judge penalty, the event(s) in the log that caused it (or "no visible cause").
   In particular: was the missing feature ever claimed/planned? by whom? why was it dropped?
6. **Decision points**: the 1-5 moments where the run's fate was decided, with quotes and stamps.
7. **Failure-mode tags** with counts/evidence, from this provisional taxonomy (add new tags if needed, define them):
   PREMATURE_END (an agent ends while required work remains), DRAFT_AS_PRODUCT (a quick draft is shipped as the
   product with no build-out), SELF_REFERENTIAL_VERIFICATION (agents verify that what exists works, not that the brief
   is met; e.g. a rule monitor that reports 0 violations while rules are ignored), SCOPE_SHRINK (the team silently
   narrows the brief), IDLE_PEER, DUPLICATE_WORK, INTEGRATION_LOSS (work never merged to main), MERGE_CONFLICT,
   WALLCLOCK_RUSH (agents rush because they read wall time across VM freezes), REVIEW_LOOP (excess re-review/re-votes),
   CAP_HIT, PROVIDER_ERROR, NONE.
8. **Time accounting** (estimate from the stream, active minutes per agent): building / coordination / reading others'
   work / testing / idle-waiting.

Then write the group contrast file you are asked for (see your task), comparing low vs high runs of the same task
and swarm vs solo: what concretely differed in the logs, at which decision points, and which mechanism would have
changed the outcome. Predict what a fix would change in the logs (observable signature).

Keep each run file factual and compact (roughly 80-200 lines). Quote briefly. English only.
When done, reply with a 10-line summary of the main root causes you found (with run ids and stamps).
