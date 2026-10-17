# Quality-finding provenance

Run `python3 research/tools/localize_quality.py` after producing `index.csv`. Outputs are deterministic, read-only derivations of retained judge Markdown and original run git histories. No candidate or historical reproducer is executed in phase A. `quality_findings.csv` has one row per **finding per judge pass**, not per unique root cause. Round 2's A/B passes can repeat the same bug or assign different severities; those remain distinct observations. Do not pool these 230 observations as 230 independent tasks or compute a unique-defect rate from them.

## Coverage and source hierarchy

`quality_coverage.csv` lists every indexed run with a judge source. Retained Markdown contains 230 findings: 121 P0 and 109 P1 across 78 report files. Eleven earlier document-judging runs have no adversarial Markdown; no zero-defect claim is made for them. For every run with retained numerical P0/P1 aggregates in the index, the counts extracted here agree after averaging A/B passes where present. Judge summaries, notes, and reproduction outputs are evidence from prior runs, not independently reconfirmed findings in this phase. Withdrawn round-2 judge prompts/session logs are neither used nor reconstructed.

Each finding retains the original report path/line and reproduction script paths. Parsing recognizes severity-bearing Markdown headings and numbered bold finding titles. Section boundaries stop at the next finding or enclosing heading. This avoids counting repeated P0/P1 words in impacts or result summaries. Every known explicit P0/P1 finding is represented; index count reconciliation is an additional coverage check.

## File and author localization

A source filename and line/range is extracted from each finding's own section. Basename/suffix references resolve only when unique in the original final repository. Scratch reproductions, tests, docs, config files, and raw input files are excluded from implementation authorship. When no line is supplied, the cited file is blamed in full and marked `judge_file_citation`; if the same file has an explicit line citation, that narrower citation takes precedence. Seven findings name functions without supplying a usable file citation. `quality_annotations.json` records source-inspected locations and reasons for those seven; they are marked `source_inspection_line`, never misrepresented as judge-supplied line numbers.

Before attribution, each candidate snapshot file's bytes must exactly match the file at the original run's final `main_head`. This prevents assigning line numbers to a different revision. All currently extracted implementation files match. Git blame uses the **original run repository**, never the judge's flattened snapshot commit. Each location records its SHA-256, actual blamed commits, authors, author timestamps, subjects, and cited line numbers. This is attribution of surviving lines, not proof of who first conceived a bug or introduced an omitted guard. Copying/cherry-picking can obscure an earlier author's conceptual contribution. The labels `a1`, `a2`, etc. are local to each run, not persistent individuals across runs.

Required-but-missing files cannot be blamed. Four explicit absent-application findings instead cite the inherited `legacy_search.py` that actually remained; its baseline author `murmur` identifies the input snapshot, **not** a peer responsible for failing to deliver. These four are classified `delivery_absent`. More inherited-code defects occur in the same undelivered runs.

## Phase interpretation

`phases_json` describes the phase of each cited line's **last blamed change**, not a causally established first introduction of the defect. Exact historical edit-to-defect causality is not recoverable for omissions or copied implementations. Rules are deterministic and each blame record includes `phase_basis`:

1. Ancestor of the task input baseline → `preexisting` (outside this run).
2. Reachable from a retained `draft/*` branch → `drafting` (direct git ancestry evidence).
3. Last change is a merge commit → `merging`.
4. A later commit explicitly starting with documentation/record/report/clarify/polish wording → `polishing`; test/verify/review/coverage wording → `verification` (both subject heuristics).
5. Other new implementation changes → `drafting`, including implementation revisions after draft selection, consistently with the index phase definition.

A finding can span several phases, and broad file-level citations can include old unrelated lines. Consequently phase counts are **not additive causal shares of defects**. Treat subject-based labels as tentative, and inspect `locations_json` before making a mechanism claim. No board-traffic/waiting phase is assigned just because the commit was made after a wait or board post.

## Peer seams

`judge_seam` retains explicit `SEAM yes/no` claims. `exact_cited_peer_count` counts distinct a-numbered authors on explicit cited or source-inspected lines, excluding whole-file fallback. `peer_seam=confirmed_cross_peer` requires both explicit judge `yes` and at least two such peer authors. There are 18 such observations (14 P0, 4 P1). This establishes a module/interface claim plus multiple cited peer authors; it is **not proof that parallelism caused the bug**. `judge_claim_only` has a seam assertion without that stronger authorship evidence; `judge_no` is the judge's own assertion; `unknown` is not a negative result. Solo runs are `not_applicable_solo`, even when a judge uses SEAM to mean a module interface. Older reports often omit explicit seam labels, so comparing raw seam counts across cohorts is biased.

## Failure-mode taxonomy

`failure_mode` is a mutually exclusive, title-led descriptive classification implemented in `failure_mode()` (priority: absent delivery; concurrency/snapshot identity; failure atomicity; lifecycle/serialization/time; schema/data integrity; parsing/query semantics; validation/error handling; other). This is a reproducible exploratory taxonomy, not pre-registered or a causal adjudication. Its denominator is all 230 judge-pass observations; overlap is resolved by rule order, not a claim that defects have only one cause. A full human reclassification would be a separate analysis.
