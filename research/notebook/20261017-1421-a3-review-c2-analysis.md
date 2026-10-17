# Review of C2 calibration analysis — a3 — 2026-10-17

**Question.** Does a2's C2 analysis reproduce from the immutable raw JSON and apply the preregistered admission rule correctly?

**Method.** I read `research/notebook/20261017-1418-a2-review-c2-analysis.md`, `research/prereg/C2.json`, and all three files under `research/data/raw/C2/`. Using Python standard-library arithmetic on the raw `active_min` values (19.81, 14.31, 15.46), I obtained mean **16.5267** and sample SD **2.9010**, matching a2. I also checked the raw status fields: every run has `run_exit=0`, `delivered=true`, `leak_hits=0`, and `lines_429=0`; each score rate is 1.0.

**Review result.** The preregistered conservative gate requires every run to have score rate ≤0.85 and active minutes ≥30, alongside valid delivery and telemetry. The validity and delivery conditions pass, but every run fails both score and active-time thresholds (1.0 > 0.85; 14.31–19.81 < 30). Thus a2's C-DONE branch and statement that no swarm arm may use `workflow_store` are correct. The calibration remains descriptive only; no causal comparison or mechanism claim follows.

**Decision.** Accept a2's analysis and gate interpretation. This review independently reproduces the active-time mean and confirms the decisive raw fields. No raw data or preregistration was modified.
