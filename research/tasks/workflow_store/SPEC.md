# Durable workflow store contract

Python 3.11+, standard library runtime. `from workflow_store import Store, StoreError`.
`StoreError` subclasses `ValueError` and has a string `.code`. All contract validation and logical failures raise it. Do not mutate caller data. Return detached JSON values. No background threads, real-time clock, randomness, or network: every transition uses the integer `now` supplied by the caller. JSON objects compare by value; object key order is irrelevant, array order is significant. Integers exclude booleans everywhere.

## Store, durability, and transactions

`Store(path)` opens or initializes a SQLite file. The parent directory must already exist. Reopening it preserves everything. `close()` releases resources and is idempotent; Store supports `with`. Operations on a closed Store raise `StoreError('closed')`. Concurrent Store instances/processes pointing at one file must serialize whole mutations without losing work, handing the same attempt to two workers, or exposing partial batches. Use SQLite transactions and wait at least five seconds for ordinary lock contention. Invalid commands and failed batches leave the file's logical state unchanged (including clock, idempotency records, and audit history). A store's initial state is clock 0, no workflows, no commands. File/open/read/SQLite errors are `StoreError('storage')`; opening a preexisting nonempty non-workflow database must reject it, never overwrite it. The internal database schema is your choice.

* `apply(command) -> dict`: atomically apply one command.
* `apply_many(commands) -> list[dict]`: consume any iterable, atomically apply its commands in order, and return their corresponding results. If an iterable raises any exception, roll back everything and propagate that original exception. A command failure rolls back the entire batch. An empty iterable changes nothing.
* `snapshot() -> dict`: return the canonical state below, without advancing time.
* `history() -> list[dict]`: accepted **unique** commands in acceptance order, retaining their original JSON values; duplicates do not append history.
* `export() -> dict`: return exactly `{'version': 1, 'state': snapshot(), 'commands': history()}`.
* `load(bundle) -> None`: validate by replay into an empty state, require exact canonical export equality including types, and replace an **empty** store in one transaction. Reject bad/altered/noncanonical exports with `StoreError('snapshot')`, nonempty targets with `StoreError('nonempty')`. A store with any accepted command, even only `advance`, is nonempty. Every failure leaves the target unchanged (an initially empty target remains empty). Replay cannot import duplicate command IDs, tampered state, unknown fields, booleans standing for integers, or inconsistent clock/history. No retained object may alias caller objects. `load` preserves original command IDs/results, so retrying imported commands is still idempotent.

All commands are plain JSON dicts with exactly the documented fields. All required fields must exist; no unknown fields. Optional fields exist only where stated. IDs (command, workflow, task, worker) are nonempty strings without leading/trailing whitespace; internal spaces and Unicode are allowed. JSON payloads/results are any JSON value (including null); nested integers, floats, strings, lists, dicts, booleans are allowed, but no NaN/infinity or non-string object keys. A numeric payload's type must be preserved; `True` and `1` are not equal for idempotency/canonical checking. Strings need no Unicode normalization. A task ID is local to its workflow; command IDs are global to the store.

Every command has `id` (command ID), `now` (nonnegative integer), and `op`. An already accepted command ID with exactly equal original JSON command **and types** returns a detached copy of its original result without doing anything, even when its `now` is older than the current clock. Any changed value/shape reusing an accepted ID raises `conflict`. For a new ID, fully validate command schema first, then reject `now < clock` with `time`; equal times are allowed. Unknown operations and malformed fields raise `schema`.

A new valid command executes in one transaction in this order: (1) set clock to `now`; (2) expire all running leases with `expires <= now`; (3) settle dependency states to a fixed point; (4) perform the named command; (5) settle again; (6) append the unique command and cache its response. Any failure rolls back all six steps. StoreError messages beyond `.code` are unspecified. Error priority across multiple different defects is unspecified, except exact duplicate lookup precedes the clock rule.

## Submission and dependencies

Submit shape:

```
{"id":"s1","now":0,"op":"submit","workflow":"build","tasks":[
  {"id":"compile","payload":{"cmd":"compile"},"priority":5,"max_attempts":2,"retry_delay":3,"after":[],"join":"all_success"},
  {"id":"notify","after":["compile"],"join":"all_done"}
]}
```

`tasks` is a list (empty allowed); each task requires only `id`. Optional defaults: `payload=null`, `priority=0` (any integer), `max_attempts=1` (integer 1..20), `retry_delay=0` (nonnegative integer), `after=[]` (list of unique task IDs), `join='all_success'`. Allowed joins: `all_success`, `all_done`, `any_success`. Duplicate task IDs, unknown dependencies, self-edges, duplicate dependencies, and any cycle raise `graph`. Every task must be reachable by processing this finite DAG; do not use recursive traversal that fails on a 1500-task chain. Reusing an existing workflow ID with a **new** command ID raises `exists`, including a finished or empty workflow.

A submission inserts tasks with attempts=0, ready_at=now, and state `pending`; initial result is exactly `{"workflow":"build","created":2}`. Dependency states settle after insertion. Tasks with no dependencies become `ready` for every join (including any_success). For tasks with dependencies:

* all_success: become `ready` when all dependencies succeed; become `blocked` as soon as any dependency is terminal without success.
* all_done: become `ready` once every dependency is terminal, irrespective of outcomes.
* any_success: become `ready` as soon as any dependency succeeds; become `blocked` only if all dependencies are terminal without success.

Terminal states are `succeeded`, `failed`, `blocked`, `cancelled`. Otherwise remain pending. Settling affects pending tasks only; readiness is permanent until claim/cancel (a dependency cannot undo a prior readiness decision). Blocking sets no result and no attempt. A retrying task is state `ready` with a future ready_at; it does not re-check dependencies. A task may be ready but not yet eligible at the current clock.

## Leasing, fencing, completion, retries

Claim:
`{"id":"c1","now":0,"op":"claim","worker":"w","lease":10,"limit":2}`.
`lease` is positive integer, `limit` integer 1..100; both are required. Select ready tasks with `ready_at <= now` globally across workflows, in order of descending priority, then lexicographic workflow ID, then task ID (ordinary Python string order). Dependencies may only make tasks ready, never alter this sort order. Return exactly `{"leases":[...]}`. Each lease row has exactly `token`, `payload`, `expires`; token is `{"workflow":str,"task":str,"attempt":int,"worker":str}`. Claim increments attempts by one, sets running, worker, and expires=now+lease. A claim with no work is accepted and returns an empty list. A request for multiple tasks selects from the ready set existing when the claim runs; it does not finish anything.

Renew:
`{"id":"r1","now":4,"op":"renew","token":TOKEN,"lease":20}`.
Token has exactly the four above fields, attempt is positive integer, other fields valid IDs. The currently running task must match all token fields. Missing tasks, stale attempts, expired attempts, wrong workers, or a terminal/nonrunning task raise `stale`. An accepted renewal sets expires=now+lease (it may shorten a lease) and returns `{"expires":24}`. At exactly old expiry the token is already stale. Failed renewal rolls back expiration/time changes; a later successful command will observe those expirations normally.

Finish:
`{"id":"f1","now":5,"op":"finish","token":TOKEN,"ok":true,"result":JSON_VALUE}`.
`ok` is boolean; `result` is required even when null. Validate the same token as renew. Return exactly `{"state":STATE,"ready_at":INTEGER}` after applying the attempt outcome. Success sets state=succeeded and stores result. Explicit failure stores result; if attempts < max_attempts, set ready and ready_at=now + retry_delay * 2**(attempts-1); otherwise set failed. Success/exhausted failure retains the previous ready_at. Every finish clears worker/expires; token attempts remain the count. Result remains visible during retries until overwritten by a later finish or expiration.

Expiration acts as an unsuccessful finish at the **lease's expires time**, stores result `{"error":"lease_expired"}`, and uses the same exponential retry policy. Thus an observation at now=100 of expiry=10 with delay=3 yields ready_at=13, not103. An expired attempt with no attempts left becomes failed. Expiration never auto-claims or consumes another attempt. Process all expirations before settling dependencies. Equality of endpoints matters: a finish at expires is stale.

## Cancellation, time, snapshots

Cancel:
`{"id":"x1","now":6,"op":"cancel","workflow":"build"}`.
Unknown workflow raises `missing`. After the usual expiration/settlement, change **every nonterminal task in that workflow** to cancelled, clear worker/expires, preserve attempts/ready_at/result, and return `{"cancelled":COUNT}`. Existing terminal states are unchanged. No dependent task within the cancelled workflow gets to escape cancellation because it became ready during the operation. Empty/already terminal workflows return0. Other workflows never depend across workflow boundaries.

Advance:
`{"id":"a1","now":100,"op":"advance"}` returns `{"now":100}` after expiration/settlement. This is how clients advance time without claiming work.

Snapshot shape (all keys mandatory and exclusive):

```
{"version":1,"clock":5,"workflows":[
 {"id":"build","state":"succeeded","tasks":[
  {"id":"compile","payload":null,"priority":0,"max_attempts":1,"retry_delay":0,
   "after":[],"join":"all_success","state":"succeeded","attempts":1,
   "ready_at":0,"worker":null,"expires":null,"result":null}
 ]}
]}
```

Workflows sorted by ID, tasks by ID, and normalized `after` sorted by ID. Preserve payload value/types. `worker`/`expires` are null except for running tasks; result initially null. Workflow state is `running` if any task is nonterminal; otherwise `succeeded` if every task succeeded (including empty); otherwise `cancelled` if at least one task is cancelled; otherwise `failed`. A failed/blocked task plus a pending/ready/running task still gives running. Snapshot never modifies state.

## Command line

`python -m workflow_store DB apply INPUT [--output PATH]`
reads one command JSON from file or `-` for stdin; emits its result.

`python -m workflow_store DB batch INPUT [--output PATH]`
reads a JSON array and calls apply_many atomically; emits result array. A nonarray is schema.

`python -m workflow_store DB snapshot [--output PATH]`
and `... DB export [--output PATH]` emit the corresponding object.

`python -m workflow_store DB load INPUT` loads an export and emits `{"loaded":true}`.

Successful output is one UTF-8 JSON line and exit0, no stderr. With --output, create parent directories and atomically replace PATH, with no stdout. Complete input parsing before opening DB. Inputs must be strict JSON (reject duplicate object keys, NaN and infinity); malformed JSON maps to error `json`. Input/read/UTF-8 failures map to `input`. Output-write failures map to `output`; an apply already committed need not be undone for an output failure. On errors exit2, no stdout, exactly one JSON line on stderr `{"error":CODE}`, no traceback. Do not replace an existing output file on an input, schema, or StoreError failure. Usage errors may use normal argparse text/exit2. Help must work without opening a database. Imports print nothing. No CLI option is a request to change clocks implicitly.

## Intended scale

A 1500-task dependency chain must submit, snapshot and cancel without recursion errors. Multiple independent processes each claiming 20 of100 ready tasks must obtain exactly100 distinct tokens in total, with no storage errors. A batch of200 claims/completions on one database should complete within15 seconds on a normal development machine; avoid fsyncing each batch member separately. Large timestamps/delays are exact arbitrary-size Python integers (no float rounding or SQLite INTEGER overflow); payload integers likewise retain exact value. This task evaluates correct observable behavior, not a mandated SQL schema, architecture, code length, documentation style, or test count.
