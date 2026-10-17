# Independent review of quality localization

Question: Are a3's historical P0/P1 source attribution and cross-peer seam counts supported by original reports and Git history?

Method: Read localize_quality.py, QUALITY_METHODS.md and all seven source-inspection annotations. Added a separate reviewer that reads the emitted CSV, checks each severity at its raw report line, compares every referenced snapshot file to the original run's final Git blob, and independently reruns exact blame ranges. It checks preexisting ancestry and verifies each confirmed seam has an explicit judge claim plus >=2 exact-line peer authors. Inspected W1-a2 B1/B3 report prose directly; searched all retained JUDGEMENT.md files for additional severity headings (none). No candidate/reproducer or lab run.

Raw-data paths: research/data/quality_findings.csv identifies every original report; original repositories and heads are in index.csv. Independent code/results: research/tools/review_quality.py and research/data/quality-review.json.

Prediction: 230 severity observations and 18 evidence-supported cross-peer seams will reproduce; attribution describes surviving lines, not causal introduction.

Result: 230/230 report headings, 375 distinct blame ranges and 164 snapshot comparisons pass, with zero mismatches. 121 P0 + 109 P1; all 18 confirmed seam observations have the required direct authorship evidence. For self2/eval/W1-a2, J11/A-adversarial report lines 21 and 62 explicitly identify timezone production/encoding-restoration seams; raw blame independently gives a1 in schedule/__init__.py and a2 in schedule/_persistence.py at the cited lines. No borrowed flattened-judge commit is used.

Additional finding: direct retained Markdown yields W3-a5 mean P1=1.5, whereas deriving it from averaged risk and P0 gives 0.5. The index now records the actual per-pass count with source and preserves the formula inference as nonauthoritative. The score formula can clip or summaries can disagree, so absent aggregate P1 is not safely reconstructed algebraically.

Decision: Approve the source/blame/seam inventory with its stated caveats. The exact/whole-file basis and subject-heuristic phase provenance must remain visible. 230 observations are not 230 independent defects. Missing application code cannot be blamed on the baseline author; the inherited file serves only to identify what was delivered.
