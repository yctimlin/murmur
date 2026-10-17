# Final independent reserveplan review

- Question: Does the isolated performance check preserve partial credit without changing the task's expected schedules or baseline?
- Method: Inspect patch 2c3a9db. Extend the independent review executable with a temporary control package that handles only the empty schedule, imports silently, and loops forever on the billion-minute input. Run its scorer with an independent 20-second outer deadline. Rerun all 30 independent interval-oracle comparisons and relocated untouched-input checks.
- Prediction: the infinite loop loses only its own case; the deliberately incomplete control still earns exactly the two supported cases. Original baseline remains 0/74.
- Raw-data path: research/tools/review_reserveplan.py; research/data/reserveplan-review.json; timeout is in research/tasks/reserveplan/hidden/cases.py.
- Result: 30/30 schedule comparisons agree. Baseline remains 0/74, generators and initial git commit remain deterministic, relocated grader leaves source unchanged. Independent loop control finishes within 20 seconds and earns **2/74**, confirming that the five-second per-case timeout preserves unrelated credit. This is a handcrafted harness control, not an agent, murmur or lab experiment.
- Decision: approve reserveplan for scheduler freezing. This resolves the sole outstanding request in 0744-a2-review-reserveplan. A3's 0801 review followup separately approves the ledger atomic-replacement assertion; all three task/test suites now have independent reviewer entries and no outstanding review request.
