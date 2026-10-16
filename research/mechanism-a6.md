# a6: two-candidate executable alternatives

## Design and falsifiable prediction

The round-one log reports every swarm L1/L2 P0 in a file written by one peer
(`research/evidence/LOG.md`, lines 84–89); review prompts missed their keep rule
(`large-RESULTS.md`). This prototype makes two independently authored implementations
of one bounded risky unit available to the same executable checks. Prior art is
Agentless's repair/validation pipeline, already surveyed in `research/evaluation.md`
(original paper: https://arxiv.org/abs/2407.01489). This is a design analogy, not a
claim that Agentless measured this leaderless mechanism.

Any peer opens a trial at accepted `main`, freezing acceptance command argv and a
finite timeout. Two different peers register distinct commits descending from that
base. Any peer may evaluate. Each candidate gets a separate disposable Git clone;
commands always execute and bounded output, exit status and duration go to SQLite.
A changed tracked tree or HEAD invalidates its evidence. The first submitted passing
candidate wins; an old-head compare-and-swap promotes it only if `main` is still the
trial base. Two passing candidates are not ranked by taste or claimed quality.

Before the screen, the prediction was: a seeded bad candidate fails while a correct
candidate passes and lands; stale shared `main` cannot be overwritten; the full suite
passes. The live screen must show two real peers submitting and an evaluation event.
The broader hypothesis—fewer single-author P0s within the desired token budget—is
unverified and reserved for the operator's preregistered evaluation.

## Enable and use

Enable: `MURMUR_ALTERNATIVES=1 murmur setup BRIEF [existing setup options]`.
Disabled: omit the environment variable or set it to `0`; the same build runs baseline.
The setting is frozen into `murmur.json`. Solo setup does not install the mechanism.
No public CLI flags/subcommands or model settings are added. All roles are claimable.

Peers use the generated `.murmur/alternatives` helper:

1. `open unit --checks '[["python3","-c","...acceptance assertions..."]]' --timeout 60`
2. Independently implement from its returned base, commit and push `draft/<peer>`.
3. `submit unit draft/<peer>` from each peer's clone.
4. `evaluate unit`; `status` shows durable outcomes.

`work/alternatives/trials.sqlite3` contains `trials`, `candidates`, and append-only
`events`. The run's `logs/run.json` carries the summary. An opened trial without a
successful promotion causes launcher exit 1, including interrupted evaluation or
stale/rejected candidates. With no opened trial, there is nothing to gate; adoption
must therefore be inspected separately and is never inferred from an exit code.

## Verification and screen

Initial full regression suite: **60 passed in 13.40 seconds**, fake Codex/no model
calls. Seven new tests cover mixed pass/fail selection, stale main, distinct peer
slots, timeout/dirty-tree rejection, generated helper/final gate, solo disable,
and bounded output/deterministic two-pass choice. Development-agent inference is
not included in zero-model-call fixture accounting.

A live screen uses a fresh plain folder, two peers, 25-minute cap, standard-library
integer-span compression with frozen inline assertions for empty, unsorted, repeated,
negative and singleton inputs. It is an invented small screening task, not an
operator evaluation task. Results follow below.

## Limits and cost

Two implementations are extra work. Expected overhead is two bounded implementation
contexts and open/submit/evaluate/status calls; no savings or numeric token ceiling
is claimed. Limit the mechanism to one risky unit, not the entire assignment.

Frozen argv does not freeze code invoked indirectly: a command naming a candidate's
own test file can be weakened by the candidate. Use inline acceptance code or an
independently preserved acceptance executable. The screen uses inline code. This
prototype checks process exit and tracked state, not the semantic sufficiency of
checks, environment equivalence, or adversarial author identity. Cooperative peers
share the workspace; SQLite is coordination, not a security boundary.

Fresh clones do not contain ignored setup dependencies; checks must be self-contained
or prepare their own dependencies. Every check has a timeout of at most 300 seconds,
at most eight checks run per candidate, and output tails are capped at 4,000 bytes.
Concurrent ordinary main pushes can make a trial stale; no rebase/retry is guessed.
A failed/stale trial is retained as failed run evidence rather than silently erased.
There is no automatic waking of finished peers or guarantee of unbiased independent
solutions. Screen success establishes firing and lifecycle compatibility only.

## Screen outcome (October 16, 2026)

The scripted real-Git screen passed in **0.6435 s including setup**, emitted seven
ledger events, rejected the intentionally defective span implementation, promoted
the passing candidate, and finished `murmur run` with exit 0. Model calls/tokens: zero.
Reproduce with `.venv/bin/python scripts/screen_alternatives.py NEW_OUTPUT_DIRECTORY`.
This substitutes deterministic peer actions for Codex and is explicitly a mechanics
screen, not real-agent adoption evidence. The underlying fake run's usage is unknown
(no provider records); zero inference is established by the fixture implementation.

The real two-peer attempt was **infrastructure-blocked**: both peers' shell tools
failed before reading their instructions with `app-server socket directory must be
a user-owned directory with mode 0700`. No trials or mechanism events occurred.
Its own exec session was interrupted; no final `logs/run.json` survived the external
interrupt. Durable rollouts show **602,795 input**, **540,800 cached**, **61,995 uncached**,
and **1,043 output** tokens across 28 observed responses. These are costs of an
unusable environment, not measured alternative-selection overhead. The evidence
JSON records the observed rollout time span separately from a missing run duration.
No environment/security workaround was attempted.

Machine-readable evidence: [screens/a6-alternatives.json](screens/a6-alternatives.json).
The prototype remains available but is **not a live-screen survivor**; its expected
extra implementation cost also makes it lower priority than mechanisms directly
checking integrated work. The operator must obtain a successful real screen before
including it in a performance claim.
