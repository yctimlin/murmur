# a3 proposals, merged ownership, and screen auditing

## Proposal and ownership history

The first a3 proposal was **leased work stealing**: atomic claims with renewable leases,
explicit task dependencies, and a completion barrier exposing unclaimed or expired work to
any finishing peer. It targets the observation that peers all finished within 0.5–3 minutes
and final integration had little independent attention ([evidence/LOG.md](evidence/LOG.md), C2).
Prior art is the shared task-list/claim mechanism already surveyed in
[products-other.md](products-other.md) (Claude Code agent teams), and the task/progress ledger
in [ORCHESTRATORS.md](ORCHESTRATORS.md) (Magentic-One). These are design precedents, not evidence
that murmur's token or quality target will be met.

A3 and a4 independently proposed essentially the same mechanism. **The proposals were merged
under a4**, rather than implementing two variants. The proposed cost is bounded task-state
responses plus claim/finish calls, with no fixed coordinator and no model configuration change.
The prediction is fewer abandoned runnable tasks and useful reassignment after a lease expires;
quality and token effects require the operator's held-out evaluation.

A3's second proposal was **peer-acknowledged frozen interfaces**. Any peer freezes exact
repository paths representing schemas, stubs, or specifications, including initially absent
files. An intentional change is first published on a draft ref. A different peer acknowledges
the exact old/new Git content and mode; a private-origin hook rejects unacknowledged changes
on main. Other paths are unaffected. This addresses C1's UI/API seam and C2's late changes,
while avoiding a permanent reviewer role. Prior art is MetaGPT's intermediate artifacts and
verification already surveyed in [survey-a3.md](survey-a3.md), plus native Git receive hooks.

The proposed cost is two or three bounded helper replies per interface transition, no
per-push model invocation, and no public command change. The prediction was fewer declared
interface mismatches with at most 25% added wall time/input over base; undeclared interfaces
remain outside coverage. A small prototype exercised rejection, cross-peer acknowledgment,
stale changes, deletion and executable modes using real private origins. Five of six focused
tests passed in 2.79 seconds; a normalized-path edge case (`.`) failed. This was **not a passing
screen** and did not involve a model.

A5 had independently claimed frozen **executable** contracts before a3's switch was visible.
Under the round-two no-duplicate requirement, a3 stopped and discarded its uncommitted
implementation. **The contract proposals merged under a5**; the acknowledgment variant is
retained here as a design alternative, not a separate candidate or a shipped claim. No a3
prototype branch is pushed because there is no surviving distinct a3 mechanism. This resolves
the generic “each peer draft” boilerplate in favor of the explicit no-duplicate rule.

## Reusable screen audit

A3 contributes [scripts/audit_screen.py](../scripts/audit_screen.py), which reads a finished
workspace and emits the recorded elapsed time and UTC timestamp span separately, process and launcher exits, original/final revision,
observed input/cached/uncached/output/total tokens, and requested mechanism evidence sections.
It recomputes usage from persisted per-response rollout records using the existing deduplicating
accountant and flags disagreement with `logs/run.json`. SHA-256 fingerprints identify the exact
metadata/report files inspected. Missing usage stays unknown even if a run is declared a fixture.
The caller's `live`/`fixture` label is explicitly unverified; it does not manufacture proof of a
real backend or mechanism activation. No file is changed and no model is invoked by the auditor.

```bash
.venv/bin/python scripts/audit_screen.py /path/to/workspace --kind live --section review
```

Use the prototype's actual `run.json` evidence key instead of `review`. Omit `--section` for
baseline runs. The command exits 1 for missing/malformed reports, missing requested evidence,
or disagreement with recorded usage, while still printing the available report. It does not
reinterpret process success as task success or pass/fail a candidate based on field presence.
The mechanism owner must cite the actual triggering event and review the artifact.

[tests/test_screen_audit.py](../tests/test_screen_audit.py) checks missing usage, fixture-label
limits, deduplicated usage, stale run reports, and malformed evidence. These are accounting
checks, not a substitute for an actual mechanism screen. A3 will independently review published
prototype behavior and record concrete defects or verification in the shared mechanism report.
