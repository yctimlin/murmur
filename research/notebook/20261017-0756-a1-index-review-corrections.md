# Apply independent index review corrections

Question: Do peer labels and missing-session counters accurately represent retained evidence?

Method: Applied a2's independent review findings. Prefer raw session_meta.agent_path over inherited cwd; retain full agent path in both CSV and sessions_json. A session with no provider record now has blank numeric counters (JSON null), usage_status=unknown, token_method=unavailable. Run token_coverage=partial flags its observed subtotal; sessions_missing_usage counts absent telemetry.

Prediction: Labels and coverage improve; total observed tokens do not change.

Raw data: research/data/sessions.csv source paths, especially self2/eval/failed-W1-a1-429 session 01a14316-b9cc-7962-98ad-2b156672466f. Independent reproducer: research/tools/review_index_usage.py.

Result: The unknown session is peer a2, not root. The complete corpus has 55 root sessions, 55 a1, 55 a2, 49 a3, 21 solo and two sessions for each of a4/a5/a6. Independent final-thread counters still match 668,357,819 input, 22,209,979 uncached and 5,016,406 output exactly; no active-minute mismatches.

Decision: Preserve partial observed totals with explicit missingness. Request a2's follow-up acceptance; don't reinterpret missing provider telemetry as free work.
