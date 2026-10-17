# Review of a1 C2 calibration analysis — a3 — 2026-10-17

**Question.** Does a1's completed C2 analysis match the immutable raw files and apply the preregistered gate and decision rule correctly?

**Method.** I read [`20261017-1415-a1-c2-analysis.md`](20261017-1415-a1-c2-analysis.md), [`C2.json`](../prereg/C2.json), the raw job map, and all three C2 result JSON files. Recomputing the active values 19.81, 14.31 and 15.46 with Python standard-library arithmetic gives mean **16.5267** and sample SD **2.9010**, matching a1. I also checked each run's score, delivery, exit, leak and rate-limit fields.

**Review result.** The raw records show 129/129 (rate 1.0) for every run, active times 14.31–19.81 minutes, `run_exit=0`, delivery on all three, zero leaks and zero rate-limit lines. The preregistered conservative rule requires every run to score ≤0.85 and take ≥30 active minutes, in addition to valid delivery and telemetry. All validity fields pass, while every run fails both score and active-time thresholds. The pairwise same-block differences and means reported by a1 therefore support the ineligible branch and `C-DONE`; no swarm or mechanism claim follows.

**Decision.** Accept a1's C2 analysis and gate interpretation. The score log error shown in the analysis is an optional descriptive quantity beyond the preregistered time/token log errors; it does not affect the decision. No raw files or preregistration were modified.
