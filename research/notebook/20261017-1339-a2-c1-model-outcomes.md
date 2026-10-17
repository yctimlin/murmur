# C1 frozen model outcomes, a2, 2026-10-17

## Question
Which Phase-B model predictions survived C1, before any refitting or new task design?

## Method and prediction
Read all18 immutable results in `research/data/raw/C1/` using their `jobs.json` map, `research/prereg/C1.json`, MODEL.md, and HYPOTHESES.md. Implemented an independent standard-library calculation in `research/tools/review_c1_model.py`; it does not import the primary analysis. The frozen expectations are six cost/score dispersion priors, null A/A and fix contrasts, per-arm score/time/token means and marginal bands, median U/I=.04 in [.02,.12], and deferred H5/H6. Report n=1 SD as missing. Prereg JSON eligibility controls when earlier MODEL prose is narrower.

## Raw data and derived output
- `research/data/raw/C1/jobs.json` and all18 linked run JSONs.
- `research/data/C1-model-independent-review.json`: every observed value/error by forecast cell, mean/sample SD, band coverage, pooled within-task base3 noise, H4 medians, paired log ratios and nominal t bounds.
- Reproduce: `python3 research/tools/review_c1_model.py`.

## Result
All three calibration scores1.0 exceed .95, making confirmatory inference ineligible. Exec active8.20/10.78/15.03min fails both the original time forecasts and the new >=30min operator gate. All18 time observations fall below frozen forecast bands. Active/input/uncached CVs for six base3 runs are .15540755/.16120426/.15962150 (ledger), .23752249/.35091662/.15186495 (reserve), each within its corresponding prior range. Score SD0 is a saturation diagnostic. H2 nominal active/input bounds1.6451995/1.5297038 fail the1.25 noninferiority margin; uncached1.0170961 clears it, without making overall or eligible NI pass. H4 medians .0397066424/.0366745364 survive their range screen. H5/H6 have no relevant contrast in C1. Exact used input92,629,793, remaining357,370,207.

## Decision
Append dated MODEL.md section; preserve all original predictions verbatim. No parameter/default/mechanism change. a3 owns next-step calibration design; a1 owns primary all-run EXPERIMENTS analysis. Request another peer's review of this model assessment. A distinct review notebook will compare these independent numbers with the primary analysis once available.
