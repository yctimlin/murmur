# Claimable final integration duty (round-2 prototype a1)

The final shared revision can arrive after peers have already checked their own pieces. This
prototype makes completion depend on a real passing check of current shared main, performed
by any peer after implementation readiness. A later commit invalidates the receipt. Missing
or stale evidence makes `murmur run` exit 2 even if Codex exits zero.

The plan is an isolated, disabled-by-default experiment: keep the existing setup/run surface,
install a frozen internal helper and durable SQLite claim/receipt state, then screen before
shortlisting with other independently built mechanisms. There is no leader, new model call,
new model/effort default, or hardcoded repository/language rule.

## Decisions

The specific round-2 instructions override the generic footer's draft vote: prototypes are
screened independently and at most three advance by expected effect on measured failures;
performance selection belongs to the operator's preregistered evaluation. `origin/main` is the
private local integration transport, not the real repository main. This prototype is pushed to
`proto/a1-integration-barrier`; final operator delivery is `experiment/self-improve-r2`.

Readiness is a declaration and the check command is selected by peers. A real command is
executed and bound to a revision, but that cannot establish test adequacy. The mechanism uses
no Git hook and observes current main on each interaction/finalization. Existing shell failure,
cap and interrupt statuses retain precedence. Solo and baseline runs omit the barrier.

## Evidence and how to see it

- Enable: add `integration_barrier = true` to the TOML used by existing `murmur setup --config`.
- Tests: `.venv/bin/python -m pytest -q` — 63 passed.
- Screen: `.venv/bin/python scripts/screen_integration.py NEW_DIRECTORY` — real Git and frozen
  helpers; failure, repair, late-push invalidation and recheck fire; no model calls.
- Read [the mechanism note](research/integration-barrier.md) and [screen data](research/screens/a1-integration.json).
  These establish mechanics only. The attempted two-peer live screen was blocked by host
  app-server socket permissions before either peer read its brief; observed usage and wall
  time are preserved. No sandbox/auth workaround was attempted. Adoption, quality improvement
  and the requested token ratio remain unverified.

The only shared implementation surface changed is setup/finalization in `cli.py`, necessary to
install the mechanism and enforce its result. Prototype candidates must remain independently
switchable if integrated after screening; do not combine before screening.
