# Deterministic extraction and reconciliation

Question: Does the extractor satisfy byte-level reproducibility and reconcile raw session totals with the run index?

Method: Ran index_runs.py twice into separate output directories. Compared complete bytes and SHA-256 for index.csv, sessions.csv, drafts.csv. Checked each run's input/uncached/output against its session rows and the sum of all per-call input categories against run input. Scanned every indexed raw session for malformed JSON and duplicate modern response IDs within a run. No lab runs.

Prediction: Identical evidence produces identical CSV; category accounting and session totals reconcile.

Raw-data path: the 241 session paths in research/data/sessions.csv; preserved Git repositories and judge artifacts identified by index.csv.

Result: All three output files were byte-identical across independent extractions. At this step their SHA-256 values were index.csv 67e4d922c6342cee4f8852a2f1a14bad08d11609005b612241370bcc1761e77d; sessions.csv 4943a60044a0b0ecc02ee97ba27ff5e260fb0b6fed16a72dd068ad5466d263ba; drafts.csv 55ceed8f19b48701d3355796947b324705e24aa882f8096c977034fc4fc4dfe8. All observed runs reconciled. Zero malformed JSON lines and zero repeated response IDs across indexed sessions within a run. A follow-up made Git file reads preserve leading/trailing whitespace and decode non-text evidence safely; rerun produced unchanged numeric CSV.

Decision: Extraction is reproducible for the retained evidence. Independent a2 review is requested; quality-localization columns may be added and receive a new final hash, without editing this notebook entry.
