# T4b contrast: base4 collapses (r1 1.6, r2 1.7) vs C1-r3 (7.4) vs solo-r1 (7.55)

Per-run evidence: `runs/E1-T4b-base4-r1.md`, `runs/E1-T4b-base4-r2.md`, `runs/E1-T4b-C1-r3.md`, `runs/E1-T4b-solo-r1.md`.

## Headline
Both base4 collapses follow the same three-step path. The model and the peers' forked context are identical in all four runs (gpt-6-astra, high effort, same developer and user messages modulo run id). The prompts differ only in the C1 ledger/END block.

1. **A peer quits within 1 active minute** because of an instruction conflict inherited from the launcher.
2. **The survivors stop after "winner integration"** with no plan or split of the remaining brief.
3. **They hand the remaining brief to "root"/"parent"**, which by prompt never acts, then end their turns.

C1-r3 avoided step 1 by chance; no prompt text is read before that decision. It structurally avoided steps 2-3 through the ledger and the END quorum. Solo has none of these steps.

## Mechanism 0: forked peers inherit the launcher prompt
Every peer rollout in all 3 swarm runs is a fork of root (`"forked_from_id": <root session>` in session_meta). Its user message is root's launcher text: "You are the launcher for 3 peer agents. You do not work on their objective yourself ... Never ... read or edit files, or run commands." The NEW_TASK then says "Your instructions are in .../aN.md. Read the whole file first."

| Run | Peer | A | Reasoning (heading) | Result |
|---|---|---|---|---|
| base4-r1 | a3 | 1.0 | "Confirming launcher-only task adherence \| Resolving conflicting parent and user instructions \| Finalizing agent with done status" (TL:70) | `done`, 1 call |
| base4-r2 | a2 | 0.7 | "Resolving conflicting file reading instructions \| Deciding to defer action due to instruction conflict \| Preparing to signal completion without file reading" (TL:54) | `done`, 0 calls |
| base4-r2 | a1, a3 | 0.4-0.7 | "Clarifying file reading permissions", "Planning file read as child process" (TL:42, 59) | proceeded, but see Mechanism 2 |
| C1-r3 | a1-a3 | 0.4-0.5 | "Opening the project file", "Discovering coordination tools", "Reading the file" (TL:46-53) | all proceeded |

The quit happens before (r2) or right after (r1) reading the prompt file. The C1 prompt text therefore cannot explain why C1-r3 kept 3 peers. Across the T4b timelines on disk, every C1 and C2 run (7) kept all 3 peers to the end, and both scored base4 runs lost one. That pattern is suggestive, not proven, given the small n.

Neither base4 run ever used `followup_task` (0 calls), so the lost peer stayed lost. The base4 prompt only says "Use `followup_task` to wake a peer who has finished when you need them." The C1 prompt makes it mandatory when an item is open.

## Mechanism 1: claim collision, then one real builder
- r1 A1.2/A1.4: a1 and a2 both claim the ingestion core (TL:84, 89). a1 pivots to docs and bench (TL:100) rather than another hard part.
- r2 A0.9/A1.7: a1 and a3 both claim the core (TL:69, 98). a3 pivots to an analytics helper module "so it can plug into whichever SQLite schema wins" (TL:117). Judges say nothing calls it.
- C1-r3 A0.8-1.4: three *different* directions, and at A1.4 a1 proposes a split covering the whole brief (TL:107). It was frozen at A3.9 (TL:172).

## Mechanism 2: "integration DONE" read as the finish line
The base4 prompt says the winner "must immediately bring it onto `main` ... and post a `DONE` receipt naming the integrated commit **before ending the turn**". The next paragraph ("Plan the whole before you split it ... first section of `PR.md`") was skipped in both runs. PR.md was never created.
- r1 A11.0 a2: "DONE winner integration ..." (TL:281). From then on only the ingestion slice was polished. a2 ended at A19.7 after "Deciding to finalize child agent for parent completion".
- r2 A13.3 a1: "DONE winner integration ... 9f1052b" (TL:354). At A15.3 a1 to a3: "Winner integration done at main 9f1052b. You can stop/finish your turn if no more work." (TL:417).
- C1-r3 A5.3 a2: "DONE winning a2 draft integrated into origin/main **with shared PR.md plan + requirements ledger**" (TL:223). Building only starts after this point. About 25 ledger rows were later marked DONE with evidence.

## Mechanism 3: deferring to a non-acting "root/parent"
In both collapses the survivors treat /root as a supervisor who will finish the work:
- r1 a2 A13.4 "Waiting for parent instructions" (TL:349). a1 "Parent should pull latest main" (TL:316), then 2 `send_message` to /root (TL:516, 529) and about 5 active min (about 60 wall min) of waiting before `done`.
- r2 a1 A15.1 to /root: "full brief docs/API/UI still absent. Use this as base and record scope honestly in PR.md/DESIGN.md." (TL:406). a3 A16.0: "root should document cuts and add at least minimal honest stubs/tests" (TL:437), then "Confirming parent agent completion behavior" (TL:442).
- C1-r3: 0 posts address root. Unfinished work goes to peers as tasks. Ending is gated on "every peer ... posted `END` for the same, latest `main` commit".

So the missing deliverables were *known* in r2 (TL:437 lists DESIGN, DATA_FINDINGS, IMPORT_SUMMARY, PR.md, HTTP/API/UI ...). They were routed to an agent whose prompt forbids editing files. This is not a knowledge failure. It is an ownership and termination failure.

## Mechanism 4: verification of what exists, not of the brief
- r1 A7.6 a2: "all Kiwi date quirks handled" (TL:211). The evidence was only that quarantine fell from 573 to 6 after appending `%m/%d/%y` *after* `%y/%m/%d` (TL:172). Judges found Kiwi dates parsed as 2001.
- r1 A21.0 a1: "latest origin/main 775103d passes ... (3/3) ... Remaining core limitations are documented honestly" (TL:509).
- C1-r3 reviews targeted the brief: per-endpoint accountant scope (TL:404, 437), refund scope leak (TL:528), and browser capture at 1440/390 (TL:672).
- Solo spent A0.2-1.8 reading every row before designing (TL:20-33) and got Kiwi and UnionSav right. The base4 drafts sampled `head -3/-5` (r1 TL:93, 98).

## Exact divergence points (collapse vs high run)
| # | Decision | base4-r1 | base4-r2 | C1-r3 |
|---|---|---|---|---|
| D1 | Peer survives the launcher conflict | a3 quits A1.0 | a2 quits A0.7 | all 3 work (A0.5) |
| D2 | Distinct claims | collision; a1 pivots to docs (A1.8) | collision; a3 pivots to helpers (A3.0) | 3 directions + whole-brief split (A1.4) |
| D3 | After integration | "DONE winner integration" A11.0, no plan | same A13.3 | PR.md ledger at A5.3 |
| D4 | Known gaps routed to | root/parent (A13.4, A23.6) | root (A15.1, A16.0) | peers as tasks/seams |
| D5 | Stop rule | each agent ends alone (A19.8, A26.5) | a1 releases a3 (A15.3) | same-head END quorum (A25.3), one void and re-vote |
| Build time | sum of active building | about 11 min | about 12 min | about 36 min |

Solo vs swarm: solo reached a similar score (7.55 vs 7.4) with about 1/5 of the input tokens (3.7M vs 18.6M), one build stream and about 85% build/test time. The swarm's gain over solo here is nil. The swarm's risk, without C1, is total collapse.

## Which mechanism would have changed the outcome, and predicted log signatures
1. **Do not fork the launcher context into peers.** Spawn peers fresh, or give the root prompt as a system note rather than a user message, or add one line to the peer NEW_TASK: "The launcher instructions above apply only to /root."
   - Signature: no peer TURN_END before A2. No THINK headings containing "conflict", "launcher" or "parent". Peers' posts never address /root or "parent".
2. **Make the base4 end condition explicit**, as in C1: ledger plus "nobody finishes alone", plus a mandatory `followup_task` when a peer has ended with items open.
   - Signature: PR.md `## Requirements` commit within about A6. Every TURN_END follows an `END <sha>` post. `followup_task` calls appear when `list_agents` shows a completed peer.
3. **Tell peers that /root never acts** ("root only waits; it will not read, write or integrate anything").
   - Signature: no `send_message`/`agents_to_notify` targeting /root. Gap lists are posted as claimable tasks.
4. **Require a full-data scan in the draft phase**, as solo did, and require verification against the brief: ledger rows cite a test.
   - Signature: an early FACT post with per-file row counts and quirks (C1-r3 TL:106). Fewer "handled" claims backed only by quarantine counts.

Mechanism 1 alone would probably not rescue base4 (r2 had 2 working peers and still collapsed at D3/D4). Mechanisms 2 and 3 address the decisive steps. C1-r3 shows that with them, about 36 build-minutes go into the whole brief.

Residual C1 issue: a mild WALLCLOCK_RUSH. Peers read wall time across VM freezes ("~23m until 120m cap" at A20.3, TL:587; "past 120m hard cap" at A24.8, TL:759) and skipped the mobile budget fix. Expose active or monotonic elapsed time to peers.
