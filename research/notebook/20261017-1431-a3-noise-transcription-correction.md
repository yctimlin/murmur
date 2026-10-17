# Correction to final audit prose (a3)

- Question: Does every prose number match `final-noise-audit.json`?
- Method: Directly read the generated C2 input SD and compare the final audit notebook.
- Prediction: The machine-readable calculation remains authoritative over hand-transcribed prose.
- Raw-data path: `research/data/raw/C2/`; generated field `noise[2].metrics.input.sd` in `research/data/final-noise-audit.json`.
- Result: `20261017-1430-a3-final-noise-and-suite.md` mistakenly transcribes C2 input SD as 177,805.8. The correct sample SD is **177,806.31329342612** (177,806.3 to one decimal), matching the raw values 1,231,152; 924,556; 921,827 and the primary C2 notebook's rounded 177,806. The code, JSON, sizing calculations, and conclusions are unchanged.
- Decision: Correct the notebook by this append-only entry; downstream reports must use 177,806 or 177,806.3 according to precision.
