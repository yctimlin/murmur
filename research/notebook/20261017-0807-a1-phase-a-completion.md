# Phase A completion and scheduler handoff

Question: Are the diagnosis and screening artifacts complete, independently reviewed, and reproducible on origin/main before any mechanism hypothesis or lab batch?

Method: Checked final main 2f9d751 and all review follow-ups. Reconciled run/session provider totals and disjoint call-input charges, joined all quality observations, and repeated all five CSV derivations in separate output directories. Read the independently recorded task setup, relocated scoring, input-immutability and deterministic-fixture controls. This phase changed only research/ files relative to its starting commit c9c2b35; no murmur experiments or candidate mechanism changes were run.

Raw evidence and artifacts:

- research/tools/index_runs.py → research/data/index.csv, sessions.csv, drafts.csv: 76 runs, 241 sessions, including preserved failures and explicit missing telemetry.
- research/DIAGNOSIS.md + research/tools/diagnose.py: cost/time/source proxies, draft textual non-retention, reproduced -0.6521 pooled quality difference, ranked deficit/finding shares, and causal limits.
- research/data/quality_findings.csv + quality_coverage.csv: 230 judge-pass P0/P1 observations; original file/line, Git author/commit, last-change phase basis, seam evidence, and transparent source-inspection annotations.
- Independent headline raw-counter reproduction: 0751-a2-review-index-usage, 0757-a2-review-index-followup. Final classification review: 0801-a2-review-tool-classifier-followup (40-call fixed sample, no remaining clear disagreement; semantic ambiguities retained).
- Independent quality attribution review: 0805-a1-review-quality-localization; 375 raw blame queries and 164 snapshot comparisons, zero mismatches.
- Screening tasks: document_catalog (340-file plain folder; 48 cases; baseline 1/48), ledger_replay (committed existing repo; 50 cases; 12/50), reserveplan (committed greenfield, multi-module, expected solo 65 minutes; 74 cases; 0/74). All use only Python stdlib, score a fresh temporary copy, locate hidden tests relative to the scorer, and complete well below 20 minutes on untouched inputs.
- Independent task reviews: 0743-a3-review-document-catalog, 0743-a3-review-ledger-replay plus 0801-a3-review-followups-screening, 0744-a2-review-reserveplan plus 0803-a2-review-reserveplan-followup. All review requests are resolved.

Result: The five regenerated CSVs match the committed bytes. Final hashes at this step:

- index.csv: 8eb01abf812c55fb54342ce3b72711091f48f53545da01c1c71f5500d98a32b8
- sessions.csv: dd322e790f1a54a6f99d7d46e408831bae613d189ea0fb56d97b16f84710bea4
- drafts.csv: 55ceed8f19b48701d3355796947b324705e24aa882f8096c977034fc4fc4dfe8
- quality_findings.csv: e6975fe04c2c7905dab2a4081958480b38cc99dd8b32327ec4dd8f01967facef
- quality_coverage.csv: 3a33ed60d91a9d4a883e142877aa5061b9fc35808eae86724b54dae09409a84d

Decision: Phase A artifacts satisfy the local structural, accounting and review controls and are ready for the scheduler's independent gate and task-hash freeze. No mechanism hypothesis or experiment batch is chosen here. Task duration and 60–85% solo difficulty remain explicit design estimates; this no-lab phase cannot empirically calibrate them. Exact semantic source-token spans and causal bug-introduction time are not present in historical telemetry; operational proxies and provenance limits remain documented rather than fabricated. No outstanding research work or external blocker remains for this phase.
