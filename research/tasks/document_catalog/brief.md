We inherited a folder of support articles and need a dependable offline catalogue. Finish the `catalogue` Python package and its command line interface using only the standard library. The work folder is a plain folder, not a git repository. Preserve the source archive. Add useful documentation and your own tests.

The public API is `catalogue.build_catalog(root)` and `catalogue.search_catalog(catalog, query="", *, tags=None, status="published", limit=None)`.

`build_catalog` recursively reads files ending in `.json` (case sensitive) beneath root. Ignore symlink files/directories and directories whose name starts with `.` or `_`. Read UTF-8, allowing an initial BOM. A missing/non-directory root raises ValueError. Examine paths in ascending relative POSIX order. Each file is one JSON object:

* `id` and `title` are required nonempty strings. Trim both; normalize id with casefold. An id may otherwise contain any characters.
* `body` is a string, default empty; preserve its whitespace. `revision` defaults to 1 and must be a positive integer, not a boolean.
* `tags` and `links` default to empty lists of nonempty strings. Trim and casefold each item, deduplicate and sort.
* `status` is `published`, `draft`, or `archived`, default `published` (exact spelling).
* `updated` is an actual calendar date in exact YYYY-MM-DD form, default `1970-01-01`.
* Ignore unknown fields. Invalid JSON/encoding yields an error with code `json`; invalid field/type/date yields code `schema`. Skip invalid documents. Each error is exactly `{"path": <relative POSIX path>, "code": <code>}`, sorted by path.

For repeated normalized ids, choose highest revision, then latest updated date, then lexicographically smallest relative path. Do this before filtering by status. Return exactly `{"documents": [...], "errors": [...]}`. Documents are sorted by normalized id. Every document contains exactly `id`, `title`, `body`, `revision`, `tags`, `links`, `status`, `updated`, `path`, and `broken_links`. `broken_links` is the sorted subset of links absent from all winning document ids (including draft/archived winners); links to oneself are valid.

`search_catalog` returns a list of matching ids. `status` selects that exact status; `"any"` allows all statuses. A different status raises ValueError. `tags`, when given, is a list of nonempty strings normalized like document tags; require every requested tag. Invalid tags raise ValueError. `query` must be a string. Tokenize query, title, body and each tag by casefolding and extracting Unicode alphanumeric runs (`re.findall(r"[^\W_]+", text.casefold())`). Every distinct query token must occur in the document's title, body or tags. Score each distinct query token as three times its title occurrence count, plus its body occurrence count, plus twice its occurrence count across tags. Empty/punctuation-only queries match all eligible documents at score zero. Sort by score descending, updated descending, id ascending. `limit` is None or a nonnegative integer (not boolean); invalid limits raise ValueError. Do not modify the input catalogue.

Support `python -m catalogue build ROOT --output INDEX` (write UTF-8 JSON) and `python -m catalogue search INDEX QUERY [--tag TAG ...] [--status STATUS] [--limit N]` (print a JSON id list). Build reports record errors inside the index and exits successfully. Fatal input, file or argument errors exit 2 with a useful message on stderr and no traceback. The CLI may print a short build summary; search stdout must contain only the JSON result. Keep generated output outside the archive in normal use.
