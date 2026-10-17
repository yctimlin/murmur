# C1 ledger forecast prose correction — a1 — 2026-10-17 13:39 UTC

Question: does the compact ledger correctly summarize the generated input forecast table?

Method: compared `research/EXPERIMENTS.md` at 8b84cbf against `research/data/C1-analysis.json` and a2's independently generated MODEL table. The generated statistics were correct, but the ledger's prose incorrectly said most input means missed the bands.

Result: only the three exec input means miss their lower bands. All swarm input means (A, B, orig where present, and pooled base3 within each task) are inside their broad frozen bands. All active-time means still miss low. No numerical outputs or frozen predictions changed.

Decision: correct the ledger prose now; retain this append-only notebook correction. The disagreement was independently detectable in a2's MODEL assessment, whose input coverage and mean interpretation agrees with raw recalculation.
