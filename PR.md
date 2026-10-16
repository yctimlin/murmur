# Round 2 prototype: frozen interface contracts (a5)

The plan for this independent candidate is to freeze executable invariants at shared interfaces,
then reject incoming main changes that break them. Any peer may register a passing contract;
Git runs the checks before accepting the new ref. The isolated prototype is switchable at setup
with `MURMUR_CONTRACTS=1`; baseline leaves the origin and prompts unchanged except metadata.
No user-facing command or flag, root integration role, model or reasoning constant is introduced.

The real-Git scripted screen rejects a deliberate `payload` -> `body` incompatibility, then
accepts repair and an optional label. It passes in 0.6238s with zero model calls. The live
2-peer screen was blocked before either peer read its brief by nested shell socket permissions;
its exit 0 is explicitly not a success. See [design, limitations, and evidence](research/mechanism-a5.md)
and the machine-readable [scripted](research/screens/a5-contracts-scripted.json) and
[live](research/screens/a5-contracts-live.json) screen records. No quality/token improvement is claimed.

How to see it: `.venv/bin/python scripts/screen_contracts.py /tmp/contracts-new` and
`.venv/bin/python -m pytest -q tests/test_contracts.py`. The final full suite passed 63 tests; snapshot mutation and interruption regressions pass.
Round-2 prototype/screen rules take precedence over the generic draft-vote footer: no winner
vote, no real-repo main push, no PR. Final candidate selection remains operator evaluation;
the shared round-2 output will aggregate every proposal and screen, including dropped candidates.

---

# Shared plan and user experience

Keep `murmur setup` and `murmur run` as the only public commands. Build on the selected
a2 draft: a new swarm starts two peers with separate conversation histories and complete
instruction files, while explicit peer counts and solo runs retain their meaning. The root
uses the actual Codex V2 wait contract. Preserve the user's model choices and Codex defaults;
do not prescribe compaction thresholds. Report observed per-response usage and the delivered
Git state in the existing run report, without equating process exit or a clean tree with
objective quality.

The shared interfaces are the existing setup metadata (`murmur.json`), generated peer/root
prompts, and additive `usage` and `result` objects in `logs/run.json`. Missing usage/state must
remain explicitly unknown. The hard seams are model/config precedence, fresh-thread runtime
inheritance, usage deduplication across copied histories, and final-state inspection after
success, failure, timeout, or interruption. Owners: a2 launcher/source audit; a4 configuration;
a1 accounting/report synthesis; a6 delivery inventory; a3/a5 broader research and independent
review. No shared infrastructure change is needed beyond the launcher mechanisms in scope.

## Drafts and selection

Every peer built an independent draft before examining the others. All six peers ran each
draft's tests and reviewed its implementation. The posted rankings selected a2 with four
first-place votes; a4 received two. No tie-break was needed.

| Voter | Ranking, first to last |
|---|---|
| a1 | a4, a2, a1, a6, a5, a3 |
| a2 | a2, a4, a1, a6, a3, a5 |
| a3 | a2, a4, a1, a6, a3, a5 |
| a4 | a2, a4, a1, a6, a3, a5 |
| a5 | a2, a4, a1, a6, a3, a5 |
| a6 | a4, a2, a1, a6, a3, a5 |

| Draft | Inspected code revision | Idea and disposition |
|---|---|---|
| a1 | `dabf73e` | Per-response usage accounting: retain; makes subsequent optimization measurable without claiming billing completeness. |
| a2 | `fb5ebaa` | Two-peer default, fresh histories, valid V2 waits: selected base; smallest directly supported execution improvement. |
| a3 | `b6d4d15` | Revision-bound check receipts: defer; useful provenance but optional adoption and efficiency gains remain unmeasured. |
| a4 | `563d3cf` | Configured model/effort fidelity: retain and finish source-informed cleanup; meets explicit flexibility requirement. |
| a5 | `c50c5b6` | Per-push integration receipts: defer; adds a hook and subprocesses for information already present in Git, without measured review gains. |
| a6 | `77c4be7` | Final delivered-revision/peer-state inventory: retain; distinguish observable delivery from objective completion. |

The source code and full tests of each draft remain reproducible from `draft/a1` through
`draft/a6`. Research commits can follow the listed code revisions. In a2's independent archived
checkouts, full suites passed: a1 37, a2 34, a3 36, a4 38, a5 35, a6 38. Those are deterministic
fake-Codex tests, not evidence of a real swarm's speed or quality.

## What changed and why

The selected base changes the default from four peers to two while preserving explicit
`--peers` and `--solo`. The matched `lean2`/`lean3` prior arms used the same build and observed
lower total and uncached input with two peers on both tasks. This is useful local evidence,
not a universal guarantee or proof of quality parity. See [prior plan](research/evidence/lean2-PLAN.md)
and [results](research/evidence/lean2-RESULTS.md).

Fresh peers read complete instruction files instead of inheriting the launcher's conversation.
Source inspection verifies fresh-child configuration inheritance and absent parent history;
setup tests verify that every generated peer instruction file contains the brief, clone path,
and project-instruction entry point. Token savings and task-quality effects are unmeasured.
The root wait instruction now passes only `timeout_ms`, matching the source's
`deny_unknown_fields` argument parser. See [source audit](research/CODEX-SOURCE.md),
[setup tests](tests/test_setup_git.py), and [config tests](tests/test_config.py).

The delivered-state inventory records the actual `origin/main` commit, new commits and changed
paths, PR.md presence, and each peer HEAD's inclusion in main, tracked dirt and nonignored
untracked count. It excludes `.work/` scratch and never fetches or alters a peer tree. Missing
repositories stay unknown, and these observations never change the process exit code or assert
functional completion. Evidence is strong for these narrow mechanics: [real-git regression
tests](tests/test_result.py) cover clean/stale/pushed/unpushed/dirty/missing states and a failed
Codex run with a pushed commit. Ignored deliverables, discarded draft intent, objective quality,
and whether tests cover requirements are not inferred. The research rationale is [verification
and termination evidence](research/evaluation.md); improved task outcomes remain unverified.

Model and effort now follow explicit murmur flags, murmur TOML, the user's top-level Codex
configuration, then installed Codex defaults. Explicit preferences are frozen at setup. No model
name, reasoning level or compaction threshold is imposed. The source audit also corrects the old
blanket catalog-effort workaround: ordinary child effort inherits from the session; the catalog
field resolves the Ultra alias and is left intact. Strong evidence for configuration behavior is
[configuration tests](tests/test_config.py), [catalog tests](tests/test_catalog.py), and the
[version-specific audit](research/CODEX-SOURCE.md). Named profiles and project-level configuration
are deliberately not reimplemented; users can express those choices via existing flags/TOML.
This is portability/correctness work, not a demonstrated speed improvement.

Run accounting reads only this run's Codex rollouts and sums provider-observed per-response
usage, deduplicating `(thread_id, response_id)` across copied or replayed records. Input, cached
input, derived uncached input, output and response count remain separate; cumulative thread
counters and reasoning output are not added again. Missing data stays unknown, malformed or
truncated records are counted, and the terminal prints a short summary. Strong narrow evidence:
[source definitions/persistence](research/usage.md) and [accounting tests](tests/test_usage.py),
including a failed run and inherited/replayed records. Complete billing, all failed API calls,
provider reporting fidelity and efficiency gains are not established.

The [research report](research/REPORT.md) and its linked appendices cover the named products,
additional discovered projects, original research/engineering accounts, the installed source,
and all supplied prior evidence. Each externally sourced claim links to its source; gaps and
vendor-only results are marked. Prior evidence was not edited. The [README](README.md) and
existing [murmur skill](skills/murmur/SKILL.md) now describe the selected defaults and limits,
including the distinction between an exited process, delivered work and functional quality.
[State captures](scripts/capture_states.py) make the launcher reviewable without credentials.

## Decisions and evidence strength

- Favor mechanical behavior and observable results over extra coordination prose, because prior
  prompt/sync-helper rounds did not meet their keep rules. [Prior evidence overview](research/README.md),
  [lean results](research/evidence/lean-RESULTS.md), [large results](research/evidence/large-RESULTS.md).
- Keep the peer count user-configurable. Two is an evidence-informed default, not an enforced
  optimum. The sample is small and tasks differ. [Matched experiment](research/evidence/lean2-RESULTS.md).
- Keep compaction under Codex/user control. Thresholds and implementation depend on model/config
  and provider capability. [Version-specific source audit](research/CODEX-SOURCE.md).
- Keep draft receipts out of the shipped footprint until their adoption/value can be measured.
  Their tests establish local correctness, not lower coordination cost. Draft review and prior
  failed sync-helper evidence support this scope choice.
- The broad product survey is necessarily bounded by discoverable primary sources as of the
  audit date; unsupported claims must be marked unverified, not filled in from memory.

## How to see it

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/capture_states.py .work/capture-review
.venv/bin/python -m murmur setup --help
```

The capture destination must be new. It produces success, failure, partial-result, timeout,
interruption, and resistant-descendant fixtures without credentials or model calls. The state
capture is a launcher exercise, not a live-agent evaluation. For real usage, run the unchanged
`murmur setup BRIEF --repo REPO` and `murmur run WORKSPACE`; inspect the generated root prompt,
peer files, and `logs/run.json`.

## Verification and remaining limits

The integrated code at `8ccb0d5` passed **53 tests** in all six peer reviews. In a1's clone,
`.venv/bin/python -m pytest -q` took **11.22 seconds**. The six-state capture produced exits
**0 / 1 / 1 / 124 / 130 / 0**, with additive `usage` and `result` fields after success, failure,
cap and interruption. All relative Markdown links in README/PR/research resolve locally.
Other peers independently reviewed generated prompts, configuration precedence, returned state,
and the unchanged command surface. a3 also built a wheel on Linux/Python 3.13, installed it into a clean virtualenv, and verified
isolated imports, the installed entry point and packaged prompts. Evidence files are unchanged
from baseline `3775a84`. These packaging checks establish the tested local installation path;
they do not establish macOS/Python 3.11 support. This document update changes no executable behavior.

The selected base separately passed 34 tests in 9.41 seconds in a2's clone. All six draft full
suites also passed in independent archived checkouts; these validation runs used fake Codex,
made zero model calls and consumed zero model tokens. Research/implementation agent inference
cost is separate and was not measured by those validation figures. These timings are test
runtime, not agent-speed measurements. No paid/live performance experiment was run.

Not verified: real-task speedup, quality parity, the target 1.5–2x total token ratio, backend
cache affinity/hit rates, live-model adherence to generated prompts, the installed Rust test
suite, public GitHub availability of the supplied source revision, or isolation against
malicious agents, macOS or Python 3.11 runtime behavior, or present/future product behavior beyond
the retrieved documentation and pinned source. The observed token report cannot recover usage
that the provider or killed process never persisted.
