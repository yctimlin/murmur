# Follow-up review: identity and missing provider usage

- Question: Did a1 resolve the two blocking caveats in the independent raw-token review?
- Method: Inspect changes in 6adc704 and rerun research/tools/review_index_usage.py against corrected index/sessions. Inspect big3 raw root/peer metadata, failed-W1-a1-429's missing peer, and empty-catalog attempt coverage fields.
- Prediction: totals stay unchanged, peer labels become correct, and unknown counters stop masquerading as measured zero.
- Raw-data path: research/tools/review_index_usage.py; research/data/index-usage-review.json (unchanged output); research/data/{index,sessions}.csv.
- Result: big3 sessions now label root/a1/a2/a3 consistently with raw agent_path. The no-usage peer has blank counters and token_method=unavailable, the failed 429 run has token_coverage=partial and sessions_missing_usage=1, and empty-catalog has token_coverage=missing. Independently reproduced totals remain 668,357,819 input / 22,209,979 uncached / 5,016,406 output with no session, run, or active-minute discrepancies. /tmp/wst is an auxiliary exec session inside the historical self research run; a1 will use an explicit auxiliary_exec label rather than imply a solo evaluation arm.
- Decision: approve provider usage, missingness and run timing/identity treatment. This closes the caveats in 0751-a2-review-index-usage. Tool category semantics are a separate audit in 0755-a2-review-tool-classifier; they do not affect this exact usage reproduction.
