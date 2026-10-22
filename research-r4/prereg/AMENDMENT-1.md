# AMENDMENT-1 (2026-10-20 02:45 Asia/Taipei) — judging anonymizer fix, before any E1 comparison is unblinded

Observed: the first E1 judgment (E1-T3b-C1-r1) reported "committed v1 DB fixture minici/fixtures/v1/state.sqlite3
missing; 3 tests fail". The fixture IS committed on main; the anonymizer (inherited from r3 open_eval.py) deletes
every *.db/*.sqlite*/*.log file and rewrites identity words (incl. common identifiers like "lane", and my added
"ledger") inside code files, which can break the delivered program for any arm.
Change (tools/r4eval.py): (1) keep all committed files except planning docs (PR/TASKS/PLAN/NOTES/HANDOFF/AGENTS.md),
.work/, logs/, caches and paths naming murmur/swarm/orchestrat; (2) scrub identity words only in prose docs
(.md/.txt/.rst), never in code or data. Arm-neutral; applies to all E1 and later runs. The 2 judgments of
E1-T3b-C1-r1 made with the old anonymizer are superseded (moved to judge/E1-superseded/) and re-done.
Only one run had been judged (no comparison computed yet).
