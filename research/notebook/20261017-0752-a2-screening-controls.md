# Deterministic screening setup and baseline controls

- Question: Do all three frozen-task candidates satisfy the scheduler's setup/scoring interface without mutating deliveries?
- Method: Added `research/tools/check_screening_tasks.py`: generate each task twice in separate temporary directories; compare non-git file hashes and git commit IDs; relocate only score.sh plus hidden/ into another directory; score untouched input; compare every input file hash (including .git) before and after. No model, murmur or lab run.
- Prediction: deterministic generators, plain-folder corpus >=300 files, all baselines <=0.30, no input modifications.
- Raw-data path: research/data/screening-validation.json; executable research/tools/check_screening_tasks.py.
- Result: document_catalog 340 files / no git / 1 of 48 = 0.0208333; ledger_replay 9 non-git files / committed repo / 12 of 50 = 0.24; reserveplan 3 non-git files / committed greenfield repo / 0 of 74 = 0. All two-generation file hashes and repo commit IDs agree; all relocated graders succeed and leave the entire input unchanged. Ledger atomic replacement test was strengthened per independent a3 review; unchanged baseline.
- Decision: setup/scoring gates pass locally. Expected solo durations and eventual solo pass-rate range remain uncalibrated; this phase cannot claim those as measured results. Review followups and diagnosis completion remain before final phase exit. The scheduler, not this script, freezes final task hashes after phase completion.
