# Phase B completion and C1 scheduler handoff

- **Question:** Are the phase's model, falsifiable hypotheses, independent red-team and first preregistered batch complete and reviewed on origin/main?
- **Method:** Pulled origin/main through `3fa83a2`, checked the model/hypothesis/preregistration artifacts and each independent review, reproduced C1/C2 forecast arithmetic, checked the final C1 hash, and confirmed no product or frozen-task changes were introduced in this phase. The read-only author validator and independent reviewer checks passed; no scheduler code was executed by researchers.
- **Prediction:** C1 will supply the first repeated out-of-sample observations. Priors and experimental decisions remain those frozen in MODEL.md, HYPOTHESES.md and C1.json; this entry makes no new empirical claim.
- **Raw-data paths:** Current design: `research/MODEL.md`, `research/HYPOTHESES.md`, `research/prereg/C1.json`, `research/data/C1-design-validation.json`. Future results: `/workspace/self3/labdata/results/<name>/` and `research/data/raw/C1/`. No C1 results existed during preregistration/review.
- **Result:** All required deliverables and independent reviews are present on origin/main. The final C1 JSON SHA256 remains `b87b334c358fdd93962257c003b21459d70095e547a89959572b6b6b6b5cac6c`, unchanged since independent final approval. Phase B has made no product mechanism or default peer-count change.
- **Decision:** Research exit criteria are satisfied. Return control to the operator scheduler to validate and execute C1 after the phase ends. Do not run experiments directly or edit the started preregistration. C2 remains a future registration after C1 analysis, subject to actual remaining budget and task suitability.

## Ownership, review and numeric checks

| Deliverable | Author/result commit | Independent review |
|---|---|---|
| Quantitative model with literature URLs and Codex path:line references; H1–H6 | a1 `24df7ef`, clarifications `cc55944` and `e95e8b2` | a3 `3fa83a2`, `20261017-0829-a3-review-model-final.md`; a2 also reproduced C1/C2 formula values and requested experimental-unit/evidence wording fixes, now applied |
| Hypothesis red-team: alternative explanation/discriminator for every H1–H6 | a3 `63af4f1`, `20261017-0818-a3-hypotheses-redteam.md` | a2 `6f83eff`, `20261017-0822-a2-review-redteam.md` |
| C1 JSON, notebook, read-only validation tool/result | a2 `cb5227a`, `20261017-0812-a2-c1-prereg.md` | a3 `79667e8`, `20261017-0819-a3-review-c1-final.md`; a1 `cc55944`, `20261017-0822-a1-review-c1-and-model-clarifications.md` |

C1 is eighteen jobs in seven consecutive blocks (3/3/2/3/2/3/2). Its first three jobs calibrate document_catalog, ledger_replay and reserveplan with exec. Ledger and reserve each have six identical base3 runs, comprising three A/A pairs and three repeats per arbitrary label. Ledger has three original-baseline runs paired only with the predesignated A run. Caps match within task; both exact revisions exist in r3.git. This exceeds four unchanged-base3 repetitions/task and preserves true same-treatment A/A.

The scheduler admission estimate is 189M input; the model mean forecast is 203.7792M. Eighteen jobs remain by count, with actual input spending controlling future admission. Budget permitting, C2 can allocate three reps to each of exec/solo/protocol-1/protocol-2/protocol-3, all murmur arms on base3; that plan is not an executable registration. All numerical priors remain hypotheses. Calibration >.95, leaked/missing telemetry, delivery failure, censoring and rate limits have preregistered handling. Saturated or invalid calibrations can leave C1 inference unavailable; this is an allowed honest outcome, not a reason to retune hidden tests or substitute tasks after seeing results.

Independent arithmetic reproduced ledger 35.933333 active minutes, 10.3488M input and .413952M uncached; reserve 59.166667, 17.04M and .6816M. Deferred reserve n=1/2/3 predictions reproduce 70/57/59.166667 minutes and 4.2/8.892/17.04M input. These checks establish internal consistency only. Three bug-fix contrasts cannot establish exact .05 significance or rare-failure safety; the noninferiority screen can honestly remain inconclusive.
