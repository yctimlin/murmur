# Archived draft a3 — revision-bound check receipts

Decision: explore a mechanical record of what a peer tested, rather than repeat the prior
prompt rule to share check results. Prior G2 did not meet the validation keep rule
([plan](evidence/lean-PLAN.md), [validation](evidence/val-RESULTS.md)); this draft is not
claimed to reduce model calls or improve delivered quality.

On `draft/a3` commit `b6d4d15` (not the selected main implementation), `murmur setup` installs `.murmur/check` in each clone. Run `.murmur/check python -m pytest`
(or another command plus arguments). It always runs the command in that clone and writes a
shared JSON receipt plus output log under `work/checks/`. Each record contains the agent,
command, before/after commit, before/after dirty state, exit code and elapsed duration.
The wrapper preserves the command's exit status. Failed commands print the last 4 KB of output.

How to see the archived draft without credentials: check out `draft/a3` in a separate clone,
then run `.venv/bin/python -m pytest tests/test_checks.py -v`. The code and tests are present at
commit `b6d4d15`; they are deliberately not installed by the selected main implementation.
The setup integration test creates a fake-Codex workspace and invokes the actual installed
wrapper in two clones. Other tests cover clean trees, mutation, dirty trees, failed/missing
commands, repeated checks and unique receipts.

Deliberately no automatic caching: ignored dependencies, environment and services are not in
Git. Clean before/after snapshots also cannot prove that a command did not temporarily change
a tracked file and restore it. A receipt is supporting evidence, not a completion verdict.
There is no additional murmur CLI command or mandatory user configuration.

Open issues before shipping: whether this evidence helps enough to justify another workspace
helper; how it composes with a6's final verification; interrupted runs currently leave a log but
no completed JSON receipt, intentionally. No live-model cost or quality claim is verified.

Selection decision: all six peers placed this draft outside their top four. The chosen plan
defers it because voluntary adoption and end-to-end value are unproven. Review additionally
found that a check deleting its repository can prevent the final receipt, and interruption
leaves only a log. This experiment is retained as research, not shipped runtime functionality.
