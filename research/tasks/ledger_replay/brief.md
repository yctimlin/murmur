Our small Python ledger package works for the happy path but cannot safely replay real event files. Repair and complete it without adding external dependencies. Preserve the import API, document the behavior, and add useful tests. The work folder is an existing git repository.

Export `Ledger` and `LedgerError` from `ledger`. `LedgerError` must derive from ValueError. A new `Ledger()` is empty. Implement:

* `apply(event) -> bool`: accept one event; True means newly applied, False means an exact duplicate already applied. Reject invalid events with LedgerError, leaving all state untouched.
* `apply_many(events) -> int`: consume an iterable of events atomically, returning the number newly applied (duplicates do not count). A LedgerError or any exception raised while consuming the iterable rolls back the entire batch. Preserve the original exception from an iterable. Do not mutate input objects.
* `balance(account_id) -> str`: balance with exactly two decimal places; unknown ids raise LedgerError. Closed accounts still have a readable zero balance.
* `snapshot() -> dict`: a detached, JSON-serializable snapshot as specified below.
* `Ledger.from_events(events) -> Ledger`: replay into a new ledger.
* `Ledger.from_snapshot(snapshot) -> Ledger`: validate and restore a snapshot. Invalid snapshots raise LedgerError. Never trust balances without verifying that replayed events reproduce the entire snapshot.

An event is a dict with exactly the keys of one of these shapes (extra or missing fields are invalid):

```
{"id": "event-id", "seq": 1, "type": "open", "account": "alice", "currency": "USD"}
{"id": "event-id", "seq": 2, "type": "deposit", "account": "alice", "amount": "12.30"}
{"id": "event-id", "seq": 3, "type": "withdraw", "account": "alice", "amount": "2"}
{"id": "event-id", "seq": 4, "type": "transfer", "from": "alice", "to": "bob", "amount": "5.50"}
{"id": "event-id", "seq": 5, "type": "close", "account": "alice"}
```

Ids and account names are nonempty strings with no leading/trailing whitespace; they are case sensitive. `seq` is a positive integer, not a boolean. A new event's seq must be strictly greater than the last accepted seq; gaps are allowed. An already accepted id with an equal event dict (key order irrelevant) is a harmless duplicate, even with its old seq; reuse with any changed value raises LedgerError. Retain original event values in history, including amount spelling. Copy accepted events so caller mutation cannot alter the ledger.

Opening creates a zero-balance account; currency is exactly three uppercase ASCII letters. No account id can be opened twice, including after closure. Monetary amounts must be strings matching `[0-9]+(?:\.[0-9]{1,2})?`, and strictly positive. Leading zeroes are allowed. Reject signs, surrounding spaces, exponent notation, NaN, non-string values and fractional cents. Money must be exact even for very large values, without decimal context rounding. Withdrawals and transfers must not overdraw. Transfers require distinct existing open accounts in the same currency. Deposits and withdrawals require an existing open account. Closing requires an existing open zero-balance account. Every rejected operation leaves history, seq and accounts untouched.

A snapshot has exactly these top-level fields:

```
{"version": 1, "last_seq": 0, "accounts": [], "events": []}
```

`accounts` is sorted by account id and each entry has exactly `id`, `currency`, `balance` (two-decimal string), and `closed` (boolean). `events` is the list of newly accepted events in acceptance order, with duplicates omitted. `last_seq` is zero for empty ledgers or the last accepted event's seq. Snapshot version is integer 1, not boolean. Restoration accepts only the exact canonical snapshot produced by replay: reject altered balances, seq, account order/types, extra/missing fields, or a duplicate event in the history. Snapshot and restored state must share no mutable objects with their inputs or with each other.

Support `python -m ledger replay EVENTS [--snapshot OUTPUT]`. EVENTS is UTF-8 JSON Lines, one event per nonblank line; skip blank lines, reject malformed JSON/non-event values. On success print the final snapshot as a single JSON line and, if supplied, write the same JSON to OUTPUT. On failure exit 2, put a useful error on stderr without a traceback, and leave an existing OUTPUT unchanged (do not create it if absent). Successful file replacement must be atomic. Only the standard library is available; the tool must work offline.
