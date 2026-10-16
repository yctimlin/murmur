# a5: frozen executable interface contracts

## Design and prediction

Failure targeted: seam and single-author errors in `research/evidence/LOG.md` C1/C2;
all seven swarm runs ended peers within 0.5–3 minutes, leaving no late integration.
Prompt-only shared checks failed the keep rule (`research/evidence/lean-RESULTS.md`).
This mechanism executes the agreed invariant before accepting an integrated tree.

Prior art already surveyed: Gas Town's Refinery tests incoming integration batches
(`research/products-other.md`, https://github.com/gastownhall/gastown); MetaGPT uses
intermediate verification (`research/survey-a3.md`, https://arxiv.org/abs/2308.00352).
The implementation uses Git's native `reference-transaction` prepared hook, whose nonzero
exit aborts the ref transaction (https://git-scm.com/docs/githooks#_reference_transaction).
No external benchmark or new survey was performed.

Any peer freezes a standalone executable probe and argv after it passes current accepted main.
The private origin materializes each incoming main tree and executes all frozen probes. A
failing, missing or timed-out command rejects that main update. A probe is stored outside
incoming changes; overwriting the original file cannot weaken it. Git's ref transaction lock
serializes contract activation and incoming main changes, preventing an activation/push race.
Any peer can register; no fixed reviewer, coordinator or root work is added. Existing names
cannot be changed or removed during the run. Draft refs remain available.

Internal switch: `MURMUR_CONTRACTS=1 murmur setup BRIEF ...`; omit it for baseline.
The switch is frozen at setup in `murmur.json`. User CLI remains setup/run.
Peer helper: `.murmur/contract add NAME --probe FILE -- python3 {probe}`; use another
interpreter/argv as appropriate. `.murmur/contract status` shows frozen contracts.
The shared ledger is `work/.murmur-contracts/events.jsonl`.

Expected cost: about 200 words added to each enabled peer's brief, one registration shell
call per contract, and local probe time per main update. At most eight 64-KiB probes, default
5-second/maximum 30-second runtime each; failure output is capped at 4 KiB. No mechanism
model calls. Pre-registered screen prediction: reject every deliberately injected violation
of the registered invariant; small probes should add <=10% run overhead. Only the rejection
prediction was tested successfully; matched end-to-end overhead remains unmeasured.

## Screen and strength of evidence

The deterministic screen invents a note packet with `kind` and `payload`. Scripted peer a1
freezes the shape, peer a2 attempts renaming `payload` to `body` (rejected), then restores the
contract and adds an optional label (accepted). It runs real `murmur setup`, `murmur run`,
Git pushes and the frozen runtime, with a fake Codex driver. It fired: three receipts show
activation pass, incoming violation fail, repaired incoming pass. Run exit 0; 0.6277 seconds
including setup; **zero model calls/tokens**. This proves mechanics, not autonomous adoption,
semantic quality, or token savings. Reproduce with:

```
.venv/bin/python scripts/screen_contracts.py /tmp/a5-contract-screen-new
```

Evidence: `research/screens/a5-contracts-scripted.json`. Full suite before final review:
58 tests passed in 13.52s. Five new tests cover freeze, rejection/repair, draft exclusion,
activation failure/timeouts, ref-lock concurrency and disabled baseline.

A real two-peer, cap25m screen was also attempted on a distinct tiny packet emit/read task.
Both children failed before reading their briefs because nested shell startup reported that
the app-server socket directory must be user-owned mode 0700. No contract activated and no
commit landed. The launcher exited 0; **that is not screen success**. Observed wall time
155.5s; 587,855 input, 529,152 cached, 58,703 uncached, 1,082 output tokens (588,937 total).
Evidence: `research/screens/a5-contracts-live.json`. No permissions, authentication or sandbox
workaround was attempted. Development-agent tokens are unmeasured and excluded from screen
numbers. This candidate passes a scripted mechanics screen; live adoption remains blocked.

## Decisions, limits, and disposition

The round-2 specific independent prototype/screen/evaluation requirements override the generic
draft-vote footer. Prototype is `proto/a5-contracts`; output main is the isolated local origin,
not the user's real repository main. No PR is opened. a3's overlapping contract handshake was
merged as design input; it was not built as a duplicate candidate.

Contracts must represent stable, agreed invariants. Freezing a wrong invariant can block useful
work, and this prototype deliberately has no weakening/unfreeze bypass. Ignored dependencies
are absent from fresh candidate trees; probes must be standalone or explicitly invoke installed
tools. Python probes that import project modules must add cwd to `sys.path`. Coverage depends
on peer-authored probes, and no activation means no extra protection. Peers share filesystem
permissions; this is cooperative enforcement, not a hostile-peer security boundary. Passing
probes do not prove task completion. Submodules/external services are not provisioned by the
runner. Scripts are short and process groups are killed on completion/timeout; output readback
is bounded, though temporary on-disk command output can grow until timeout.

Candidate selection among surviving prototypes must use expected effect on measured failures;
operator evaluation, not peer preference or diff size, chooses a performance winner. This
contract mechanism should remain available on its prototype branch even if other mechanisms
are shortlisted, because early invariant rejection differs from final-head evidence.
