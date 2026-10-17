# reserveplan contract

Python 3.11+, standard library only. Public imports: `plan`, `validate`, and `PlanError` from `reserveplan`. `plan(spec)` returns an ordinary JSON-serializable dict. `validate(spec)` returns None if valid. Neither mutates its input, and repeated calls are deterministic. All schema and feasibility failures are `PlanError`, a subclass of ValueError with string attributes `code` and `path`; the human-readable exception message is up to you. JSON-pointer paths escape `~` as `~0` and `/` as `~1`.

## Input

The top-level object has `version` (required, integer 1), `horizon` (optional positive integer, default 10000), `resources` (required object), `jobs` (required list), and `bookings` (optional list, default []). No unknown fields are allowed anywhere in the schema. Integers exclude booleans. Identifiers are nonempty strings, are case-sensitive, and may contain spaces or punctuation. JSON object keys are strings. Time is an integer minute, never a timestamp. All times and endpoints must be between 0 and horizon inclusive. An input with no resources and no jobs is valid.

* A resource is keyed by its identifier, with `capacity` (required positive integer) and optional `unavailable` (default [], a list of [start,end] intervals). Every interval has exactly two integer endpoints with start < end. Intervals may overlap or touch and mean complete downtime. Their union closes that resource. Resources not named by a job are irrelevant to that job.
* A job has `id` and `duration` (required nonnegative integer), optional `release` (default 0), `priority` (any integer, default 0), `deadline` (optional nonnegative integer), `requires` (default {}, object mapping resource names to positive integer units), and `after` (default [], list). Job duration is bounded by horizon. A dependency is either a job ID string (lag 0), or an object with required `id` and optional nonnegative integer `lag` (default 0, not bounded by horizon). Duplicate dependencies, missing prerequisite IDs, and self-dependencies are invalid. All job IDs must be unique. All resource names in `requires` must exist and requested units cannot exceed that resource's capacity. Dependency cycles are invalid.
* A booking has required `resource`, `start`, `end`, and `units`. The resource must exist, start < end, and units is a positive integer no larger than capacity. Bookings may overlap each other if their summed units never exceed capacity. A booking must not intersect resource downtime. Input list order has no significance for bookings.

Time intervals are **half-open**: [2,5) and [5,7) do not overlap. Jobs cannot be preempted: one job holds every requested resource throughout [start,end). Duration-zero jobs take no resource capacity, may occur during downtime and at horizon, and still obey dependencies and release times. They must nevertheless have valid resource requests.

## Planning

Use a deterministic serial list schedule, not global optimization:

1. Among unscheduled jobs whose prerequisites have all been scheduled, select the one with highest numeric priority, breaking ties by lexicographically smallest ID (Python's ordinary string order). A job is ready for this selection even if its prerequisite ends in the future. Do not use input order or earliest feasible start to choose the next job.
2. Compute its lower bound as max(release, end(prerequisite)+lag for each prerequisite), using 0 when there are no prerequisites. Find the earliest integer start at or after that bound such that end <= horizon, all demanded resources are outside downtime throughout the job, and existing bookings plus previously scheduled jobs plus this job never exceed any demanded resource's capacity. Jobs with no resource requests can overlap everything. Previously scheduled jobs never move. Later selected jobs may fill earlier gaps.
3. If no slot exists, raise `PlanError(code="unschedulable", path="/jobs/<input index>")`. Otherwise reserve the slot and continue. Jobs exceeding a deadline are allowed; deadline affects reporting only, never selection or feasibility.

Performance: event boundaries matter, not the numeric horizon. Inputs with a horizon of one billion and a few dozen jobs/bookings must finish promptly; do not loop over every minute. For reference, the intended scale is 500 jobs, 50 resources, and 1000 booking/downtime intervals.

## Result

Return exactly these fields:

```
{
  "version": 1,
  "order": ["job IDs in selection order"],
  "jobs": [{"id": "...", "start": 0, "end": 3, "tardiness": 0}],
  "makespan": 3,
  "total_tardiness": 0,
  "resources": {"name": {"peak": 1, "unit_minutes": 3}}
}
```

`jobs` is sorted lexicographically by job ID; its rows have exactly the four shown keys. Tardiness is max(0,end-deadline), or 0 without a deadline. Makespan is the maximum job end, or 0 for no jobs; bookings do not affect makespan. Every input resource appears in `resources`, including unused ones. Peak is maximum simultaneously occupied units; unit_minutes is sum(units * (end-start)). Both include pre-existing bookings and planned jobs, with zero-duration jobs excluded. Touching intervals do not add together at their common endpoint. Object key order is not significant.

## Validation failures

Validation checks the complete schema and references before attempting a schedule. `validate` checks schema, references, dependency cycles, and booking consistency; it does **not** attempt scheduling (an impossible horizon can still validate). For inputs with exactly one defect use the codes and paths below. When multiple defects exist, which one is reported first is unspecified.

| Defect | code | path |
|---|---|---|
| Wrong type, missing required field, unknown field, invalid integer range, empty identifier, malformed interval, unsupported version | `schema` | JSON pointer to the bad or missing value, or unknown field; top-level wrong type uses the empty string |
| Duplicate job ID | `duplicate_job` | `/jobs/i/id` for the later occurrence |
| Missing resource referenced by job | `unknown_resource` | `/jobs/i/requires/<escaped name>` |
| Job request exceeds capacity | `capacity` | `/jobs/i/requires/<escaped name>` |
| Missing dependency ID | `unknown_dependency` | `/jobs/i/after/j` |
| Duplicate dependency ID in one job | `duplicate_dependency` | `/jobs/i/after/j` for the later occurrence |
| Self-dependency or any directed cycle | `cycle` | `/jobs` |
| Missing resource referenced by booking | `unknown_resource` | `/bookings/i/resource` |
| Booking units exceeds capacity | `capacity` | `/bookings/i/units` |
| Aggregate booking overcapacity or a booking intersecting downtime | `booking_conflict` | `/bookings` |

For a malformed interval [a,b], the path is the interval itself if it has wrong length or a >= b; a wrong type/range of an endpoint uses `/.../<endpoint index>`. For a booking with start >= end, the path is `/bookings/i/end`. Invalid string dependency IDs (empty string or wrong type) use `/jobs/i/after/j`; an invalid object dependency's ID uses `/jobs/i/after/j/id`. `requires` and `resources` empty keys are schema errors at the pointer to that key. An unrecognized command-line option is a usage error, not a PlanError.

## Command line

`python -m reserveplan plan INPUT [--format json|csv] [--output PATH]`

* INPUT is a JSON path or `-` for stdin. JSON is the default format. A successful command exits 0, writes only the requested output to stdout (or the chosen UTF-8 file), and writes no stderr. Create parent directories for `--output` if necessary. A file output produces no stdout. End JSON output with one newline.
* CSV uses the exact header `id,start,end,tardiness`, jobs in result order, and standard CSV quoting. End rows with LF; empty jobs still emit the header. The plan's other fields do not appear in CSV.
* Input path/UTF-8/JSON failures and schema/planning failures exit 2, emit exactly one JSON object plus newline on stderr with keys `error` and `path`, and no stdout. Map path/read/encoding failures to `{"error":"input","path":""}`; malformed JSON to `{"error":"json","path":""}`. Map PlanError to its code/path. If output cannot be written, use `{"error":"output","path":""}` and exit 2. Do not truncate an existing output when planning or input validation fails. Error messages do not include tracebacks.

`python -m reserveplan validate INPUT`

* Same input/error behavior. On valid input exit 0 and print `{"valid": true}` followed by newline; validation does not schedule.

Provide standard --help usage. Command usage errors may use argparse's normal text and exit 2. Importing the package must not start the CLI or print anything. Include useful docs and your own automated tests.
