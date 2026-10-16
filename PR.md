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

The remaining selected mechanisms are integrated by their owners under the shared plan above;
this document will record the resulting behavior and final validation before completion.

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

The selected base passed 34 tests in 9.41 seconds in a2's clone. All six draft full suites also
passed in independent archived checkouts (8.98–10.28 seconds for the other drafts); these
validation runs made zero model calls and consumed zero model tokens. Research/implementation
agent inference cost is separate and was not measured by those validation figures.

Not verified: real-task speedup, quality parity, the target 1.5–2x total token ratio, backend
cache affinity/hit rates, live-model adherence to generated prompts, the installed Rust test
suite, public GitHub availability of the supplied source revision, or isolation against
malicious agents. Final integrated tests and fixture results are to be added before completion.
