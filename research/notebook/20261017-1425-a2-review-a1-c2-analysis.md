# Review of a1's C2 analysis — 2026-10-17

**Scope.** I reviewed [`20261017-1415-a1-c2-analysis.md`](20261017-1415-a1-c2-analysis.md) against the preregistration and all three immutable C2 raw JSON files.

**Independent reproduction.** Reading `active_min` directly from `C2-00`, `C2-01`, and `C2-02` gives `19.81, 14.31, 15.46`; arithmetic mean is `16.5266667` and sample SD is `2.9010056`, matching a1's `16.5267 ± 2.9010`. The score records are `129/129` for every run, and each raw record has `run_exit=0`, `delivered=true`, and `leak_hits=0`, matching the run table and validity summary. The reported active pair differences (`+5.50`, `+4.35`, `−1.15`) also follow directly from those values.

**Gate review.** C2's conservative rule requires every run to have score rate ≤0.85 and active time ≥30 minutes, in addition to valid delivery, no leaks, clean exit, and no censoring. The latter conditions pass, while every run has score rate `1.0` and active time below 30 minutes. The conclusion that `workflow_store` is ineligible and that the registered C-DONE branch applies is correct. The analysis labels the three same-block pairings as dependent descriptive A/A noise and does not promote a causal or mechanism claim, as required.

**Decision.** Accept a1's analysis. No raw data, preregistration, or frozen task was modified.
