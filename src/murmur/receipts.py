"""Change receipts: for every commit a run produced, who made it, why, and how it was verified.

A receipt is put together from what a run already records. Nothing is executed, checked out
or written in the run to make one:

  work/origin.git                          the commits, their branches and the push reflog
  codex-home/sessions/**/*.jsonl           each agent's commands with the exit status Codex
                                           recorded, and what the agent said it was doing
  codex-home/agent_message_board_1.sqlite  the peers' board posts (a scratch copy, read-only)

Verification comes in three grades, and a receipt never upgrades one into another:

  observed  a test, lint or build command in the author's session log, with its exit status
  claimed   the agent says it verified the change (a `Verified:` line in the commit message,
            or a board post that names the commit), but no such command was seen
  none      neither

A commit is tied to its author's log by the `[branch sha] subject` line `git commit` printed,
or failing that by the commit's author time (marked as inferred). The checks that grade a
receipt are the ones that agent ran after its previous commit and up to this one. Checks after
an agent's last commit, and checks run right after a `git checkout` of something else, are
listed but not graded: they may be about another tree. Only the exit status grades a check,
never the text it printed.

`collect()` returns the whole document as plain dicts and lists; `read_commits`,
`read_sessions` and `read_board` are the readers under it. Text taken from logs is redacted
and shortened before it gets into a receipt, and codex-home/auth.json is never opened.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import sqlite3
import subprocess
import tempfile
import textwrap
from datetime import datetime, timezone
from pathlib import Path

from murmur import tokens

SCHEMA = 1
GIT_TIMEOUT_S = 60
BOARD_DB = "agent_message_board_1.sqlite"
AGENT_EMAIL = "@murmur.local"

MAX_COMMAND = 400
MAX_OUTPUT_LINES = 6
MAX_OUTPUT = 600
MAX_TEXT = 500
MAX_BODY = 2000
MAX_PATHS = 200
MAX_POSTS = 4
TEXT_WIDTH = 100
# Quotes in the text view; receipts.json keeps up to MAX_TEXT of each.
SHOWN_SAID = 300
SHOWN_POST = 220
# How long after a commit's author time the command that made it may finish.
COMMIT_COMMAND_WINDOW_S = 120

STATUS_LABELS = {
    "observed-pass": "OBSERVED, passed",
    "observed-fail": "OBSERVED, FAILED",
    "observed-unclear": "OBSERVED, result unclear",
    "claimed": "CLAIMED only",
    "none": "NOT OBSERVED",
}


class ReceiptsError(Exception):
    """The workspace cannot be read at all."""


# --- redaction -------------------------------------------------------------------------

_SECRETS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?(?:-----END [A-Z ]*PRIVATE KEY-----|\Z)", re.S),
    re.compile(r"\b(?:sk|pk|rk)-[A-Za-z0-9_*-]{10,}"),
    re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})"),
    re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{4,}"),
)
_BEARER = re.compile(r"(?i)\b(bearer\s+)[A-Za-z0-9._~+/=-]{16,}")
# NAME=value and "name": "value" where the name says the value is a credential. After a colon
# an unquoted value must hold a digit, so prose such as "tokenizer: implemented" is left alone.
_NAMED = r"(?i)\b([a-z0-9_.-]*(?:api_?key|token|secret|passw(?:or)?d|credential)[a-z0-9_.-]*"
_ASSIGNED = (
    re.compile(_NAMED + r"\s*=\s*)(\"[^\"\n]{6,}\"|'[^'\n]{6,}'|[^\s\"',;]{6,})"),
    re.compile(_NAMED + r"[\"']?\s*:\s*)(\"[^\"\n]{6,}\"|'[^'\n]{6,}'|(?=[^\s\"',;]*\d)[^\s\"',;]{8,})"),
)
_VERDICT_LINE = re.compile(
    r"(?i)\s*(?:ran \d+ tests?\b|ok\b|pass(?:ed)?\b|fail(?:ed|ure)?\b|error\b|=+ .*\b(?:passed|failed|errors?)\b"
    r"|\d+ (?:passed|failed|passing|failing|errors?)\b|tests?:\s|test result:|all checks passed|found \d+ errors?)"
)
# Colour codes and other control characters: log text ends up on a terminal.
_ESCAPES = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b[@-_]|[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_OTHER_HOME = re.compile(r"(?<![\w.~-])/(?:home|Users)/[^/\s\"':]+")
MASK = "[redacted]"


class Redactor:
    """Masks what looks like a credential and takes personal paths and control characters out of log text."""

    def __init__(self, ws: Path) -> None:
        paths = {str(ws): "<workspace>", str(ws.resolve()): "<workspace>"}
        home = str(Path.home())
        if home not in ("", "/"):
            paths[home] = "~"
        # Longest first, so the workspace wins over a home directory that contains it.
        self._paths = sorted(paths.items(), key=lambda item: -len(item[0]))

    def __call__(self, text) -> str:
        text = text if isinstance(text, str) else str(text or "")
        text = _ESCAPES.sub("", text.replace("\r\n", "\n").replace("\r", "\n"))
        for path, short in self._paths:
            text = text.replace(path, short)
        text = _OTHER_HOME.sub("~", text)
        for pattern in _SECRETS:
            text = pattern.sub(MASK, text)
        text = _BEARER.sub(rf"\1{MASK}", text)
        for pattern in _ASSIGNED:
            text = pattern.sub(rf"\1{MASK}", text)
        return text

    def clip(self, text, limit: int = MAX_TEXT) -> str:
        text = self(text).strip()
        if len(text) <= limit + 40:  # not worth a note about a few characters
            return text
        return f"{text[:limit].rstrip()} [... {len(text) - limit} more chars]"

    def excerpt(self, output, whole: bool) -> str:
        """A few lines of a command's output: its end, where test runners print their result.

        When the check was one command among several (`whole` is false), the end may belong
        to another command, so lines that read like a runner's verdict are preferred.
        """
        lines = [line.rstrip() for line in self(output).strip().splitlines() if line.strip()]
        verdicts = [] if whole else [line for line in lines if _VERDICT_LINE.match(line)]
        kept = (verdicts or lines)[-MAX_OUTPUT_LINES:]
        text = "\n".join(kept)[-MAX_OUTPUT:]
        return ("[...]\n" if len(kept) < len(lines) else "") + text


# --- time ------------------------------------------------------------------------------


def _epoch(stamp) -> float | None:
    if not isinstance(stamp, str):
        return None
    try:
        return datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _iso(epoch: float | None) -> str | None:
    if epoch is None:
        return None
    try:
        return datetime.fromtimestamp(epoch, timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    except (OverflowError, OSError, ValueError):
        return None


# --- which commands are checks ---------------------------------------------------------

_PM = r"(?:npm|pnpm|yarn|bun)\s+(?:run\s+)?"
_PY = r"python[\d.]*\s+(?:-[A-Za-z]+\s+)*-m\s+"
_CHECKS = tuple((kind, re.compile(pattern)) for kind, pattern in (
    ("test", r"(?:pytest|py\.test|tox|nox|nose2|jest|vitest|mocha|ava|rspec|phpunit|ctest|bats|behave)\b"),
    ("test", _PY + r"(?:pytest|unittest|nose2|doctest)\b"),
    ("test", _PM + r"(?:test|e2e)\b"),
    ("test", r"(?:playwright\s+test|cypress\s+run|node\s+--test|deno\s+test|go\s+test|cargo\s+(?:test|nextest)"
             r"|dotnet\s+test|swift\s+test|mix\s+test|rake\s+(?:test|spec))\b"),
    ("test", r"(?:make|just)\s+(?:-\S+\s+(?:\S+\s+)?)*(?:test|check|verify)\b"),
    ("test", r"(?:mvn|mvnw|gradle|gradlew)\s.*\b(?:test|verify|check)\b"),
    ("lint", r"(?:ruff|flake8|pylint|mypy|pyright|eslint|tsc|shellcheck|golangci-lint|biome|stylelint)\b"),
    ("lint", _PY + r"(?:ruff|flake8|pylint|mypy|pyright|py_compile|compileall)\b"),
    ("lint", _PM + r"(?:lint|typecheck|type-check|check)\b"),
    ("lint", r"(?:cargo\s+(?:clippy|check)|go\s+vet)\b"),
    ("build", _PM + r"build\b"),
    ("build", r"(?:cargo\s+build|go\s+build|mvn\s+(?:package|install)|(?:next|vite|webpack)\s+build)\b"),
    ("build", _PY + r"build\b"),
    ("build", r"make(?:\s+(?:all|build))?\s*$"),
))
# Words in front of a command that do not change which program runs.
_PREFIX = re.compile(
    r"(?:(?:sudo|time|command|exec|nice|env|xvfb-run|timeout\s+\S+|uv\s+run|poetry\s+run|pipenv\s+run"
    r"|hatch\s+run|pdm\s+run|npx|pnpm\s+exec|pnpm\s+dlx|bunx|if|then|else|elif|do|while|until|!|\{)\s+"
    r"|-{1,2}[A-Za-z][\w-]*\s+|[A-Za-z_][A-Za-z0-9_]*=\S*\s+)"
)
_HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
_SEPARATORS = ("&&", "||", "|&", ";", "|", "&", "\n", "(", ")")
_NEUTRAL = ("(", ")")


def _without_heredocs(script: str) -> str:
    """The script minus heredoc bodies: text written into a file is not a command that ran."""
    kept, waiting = [], []
    for line in script.split("\n"):
        if waiting:
            if line.strip() == waiting[0]:
                waiting.pop(0)
            continue
        kept.append(line)
        waiting = [match[2] for match in _HEREDOC.finditer(line)]
    return "\n".join(kept)


def _split(script: str) -> list[tuple[str, str]]:
    """A shell script as (simple command, separator after it), split outside quotes."""
    script = _without_heredocs(script)
    parts: list[list[str]] = []
    current: list[str] = []
    quote = None
    index = 0

    def close(separator: str) -> None:
        text = "".join(current).strip()
        current.clear()
        if text:
            parts.append([text, separator])
        elif parts and parts[-1][1] in _NEUTRAL:
            parts[-1][1] = separator  # `(a) && b`: what follows the group follows `a`

    while index < len(script):
        char = script[index]
        if quote:
            if char == "\\" and quote == '"':
                current.append(script[index:index + 2])
                index += 2
                continue
            if char == quote:
                quote = None
            current.append(char)
        elif char in "'\"":
            quote = char
            current.append(char)
        elif char == "\\":
            current.append(script[index:index + 2])
            index += 2
            continue
        elif char == "&" and (script[index - 1:index] == ">" or script[index + 1:index + 2] == ">"):
            current.append(char)  # a redirection such as 2>&1 or &>file
        else:
            separator = next((sep for sep in _SEPARATORS if script.startswith(sep, index)), None)
            if separator:
                close(separator)
                index += len(separator)
                continue
            current.append(char)
        index += 1
    close("")
    return [(text, separator) for text, separator in parts]


def _bare(command: str) -> str:
    """A simple command without the words in front of it and the directory of its program."""
    while match := _PREFIX.match(command):
        command = command[match.end():]
    words = command.split(None, 1)
    return " ".join([words[0].rsplit("/", 1)[-1], *words[1:]]) if words else ""  # .venv/bin/pytest -> pytest


def _moves(command: str) -> bool:
    """Whether a simple command is a `git checkout` or `git switch` to another tree.

    `-b`/`-c` only give the current tree a branch name, and `git checkout -- file` or
    `git checkout .` restore files.
    """
    words = _bare(command).split()
    if words[:2] == ["git", "-C"]:
        del words[1:3]
    if len(words) < 3 or words[0] != "git" or words[1] not in ("checkout", "switch"):
        return False
    return words[2:] != ["."] and not {"-b", "-B", "-c", "-C", "--orphan", "--"} & set(words[2:])


def _kind(command: str) -> str | None:
    """test, lint or build when the simple command runs one, else None."""
    command = _bare(command)
    return next((kind for kind, pattern in _CHECKS if pattern.match(command)), None)


def checks_in(script: str, exit_code: int | None) -> list[tuple[str, str, str, str | None]]:
    """(kind, command, result, checkout) for each test, lint or build command in a shell script.

    The result is `passed` or `failed` only when the script's exit status is that check's
    verdict. Exit 0 says so when everything after the check is joined with `&&`: a pipe
    (`pytest | tail`), a later command (`pytest; git status`) or `|| true` would hide a
    failure. A non-zero exit says so only when the check came last, because in
    `pytest && git push` the push may be what failed. Otherwise the result is `unclear`, or
    `unknown` when no exit status was recorded. `set -e` and `set -o pipefail` at the top of
    the script are honoured.

    `checkout` is the `git checkout` or `git switch` that came before the check in the same
    script, if any: the check then ran on whatever that command moved to, such as a peer's draft.
    """
    parts = _split(script)
    if not parts:
        return []
    first = parts[0][0]
    piped = {"|"} if re.match(r"set\s.*pipefail", first) else set()
    chained = {"&&", *_NEUTRAL, *piped}
    if re.match(r"set\s+-[A-Za-z]*e", first):
        chained |= {";", "\n"}
    found = []
    checkout = None
    for index, (command, _separator) in enumerate(parts):
        kind = _kind(command)
        if not kind:
            if _moves(command):
                checkout = command
            continue
        before = [separator for _text, separator in parts[:index]]
        after = [separator for _text, separator in parts[index:-1]]
        if exit_code is None:
            result = "unknown"
        elif exit_code == 0:
            result = "passed" if "||" not in before and all(sep in chained for sep in after) else "unclear"
        else:
            result = "failed" if all(sep in piped or sep in _NEUTRAL for sep in after) else "unclear"
        found.append((kind, command, result, checkout))
    return found


# --- session logs ----------------------------------------------------------------------

_SHELL_TOOLS = ("exec_command", "shell", "shell_command", "local_shell", "container.exec")
_COMMIT_LINE = re.compile(r"^\[[^\]\n]*? ([0-9a-f]{7,40})\]", re.M)
# Commands that give a commit a new author time (a rebase or cherry-pick keeps the old one).
_COMMITTING = re.compile(r"\bgit\b[^\n]*\b(?:commit|merge|revert)\b")


def _script(command) -> str:
    """The shell text of a recorded command. Codex stores it as [shell, "-lc", script]."""
    if isinstance(command, str):
        return command
    if isinstance(command, list) and all(isinstance(word, str) for word in command):
        if len(command) == 3 and command[1] in ("-lc", "-c"):
            return command[2]
        return shlex.join(command)
    return ""


def _message_text(payload: dict) -> str:
    content = payload.get("content")
    if not isinstance(content, list):
        return ""
    return "".join(str(item.get("text") or "") for item in content if isinstance(item, dict)).strip()


def _agent_from_path(agent_path) -> str | None:
    """`/root/a1` is peer a1 and `/root` the launcher; a peer's own sub-agents count as the peer."""
    if not isinstance(agent_path, str) or not agent_path.strip("/"):
        return None
    parts = agent_path.strip("/").split("/")
    return parts[1] if len(parts) > 1 else "root"


def _session_agent(meta: dict | None, rollout: Path, solo: bool) -> str:
    if solo:
        return "solo"
    if isinstance(meta, dict):
        spawn = meta.get("source")
        for key in ("subagent", "thread_spawn"):
            spawn = spawn.get(key) if isinstance(spawn, dict) else None
        path = meta.get("agent_path") or (spawn.get("agent_path") if isinstance(spawn, dict) else None)
        if agent := _agent_from_path(path):
            return agent
    return tokens.session_usage(rollout)[0]  # the rule the token report uses


def _tool_output(output) -> tuple[int | None, str]:
    """Exit status and text from a `function_call_output`, whose shape varies by tool."""
    if isinstance(output, list):
        output = "".join(str(item.get("text") or "") for item in output if isinstance(item, dict))
    if not isinstance(output, str):
        output = json.dumps(output) if output is not None else ""
    try:
        parsed = json.loads(output)
    except json.JSONDecodeError:
        return None, output
    if not isinstance(parsed, dict):
        return None, output
    meta = parsed.get("metadata") if isinstance(parsed.get("metadata"), dict) else {}
    code = parsed.get("exit_code", meta.get("exit_code"))
    code = code if isinstance(code, int) and not isinstance(code, bool) else None
    return code, str(parsed.get("output") or "")


def read_session(rollout: Path, ws: Path, solo: bool = False) -> dict:
    """One rollout as {"agent", "path", "events", "final"}.

    Events are in file order: `command` (script, cwd, exit_code, output) and `say` (text the
    agent wrote between tool calls). Each has `at` (epoch seconds, or None) and the `line` it
    came from. Lines that are not JSON and event types this reader does not know are skipped.
    """
    events, calls, final, meta = [], {}, None, None
    executions = own = False
    last_at = None
    with rollout.open(encoding="utf-8", errors="replace") as handle:
        for number, line in enumerate(handle, start=1):
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue  # a session stopped mid-write leaves half a line
            payload = event.get("payload") if isinstance(event, dict) else None
            if not isinstance(payload, dict):
                continue
            last_at = at = _epoch(event.get("timestamp")) or last_at
            kind, inner = event.get("type"), payload.get("type")
            if kind == "session_meta":
                meta = meta or payload  # a forked session repeats its parent's after its own
            elif kind == "event_msg" and inner == "thread_settings_applied" and not own:
                own = True
                if isinstance(meta, dict) and meta.get("forked_from_id"):
                    # A forked session opens with a copy of its parent's conversation, which
                    # ends where this session's settings are applied. That part is the parent's.
                    events.clear()
                    calls.clear()
                    executions = False
            elif kind == "event_msg" and inner == "item_completed":
                item = payload.get("item")
                if isinstance(item, dict) and item.get("type") == "CommandExecution":
                    executions = True
                    code = item.get("exit_code")
                    events.append({
                        "kind": "command", "at": at, "line": number,
                        "script": _script(item.get("command")),
                        "cwd": str(item.get("cwd") or "").removeprefix("file://"),
                        "exit_code": code if isinstance(code, int) and not isinstance(code, bool) else None,
                        "output": str(item.get("aggregated_output") or ""),
                    })
            elif kind == "event_msg" and inner == "task_complete":
                final = payload.get("last_agent_message") or final
            elif kind == "response_item" and inner == "message" and payload.get("role") == "assistant":
                if text := _message_text(payload):
                    events.append({"kind": "say", "at": at, "line": number, "text": text,
                                   "phase": payload.get("phase")})
            elif kind == "response_item" and inner == "function_call" and payload.get("name") in _SHELL_TOOLS:
                try:
                    arguments = json.loads(payload.get("arguments") or "{}")
                except (json.JSONDecodeError, TypeError):
                    arguments = {}
                if isinstance(arguments, dict):
                    calls[payload.get("call_id")] = {
                        "kind": "call", "at": at, "line": number,
                        "script": _script(arguments.get("cmd") or arguments.get("command")),
                        "cwd": str(arguments.get("workdir") or arguments.get("cwd") or ""),
                        "exit_code": None, "output": "",
                    }
                    events.append(calls[payload.get("call_id")])
            elif kind == "response_item" and inner == "function_call_output":
                call = calls.get(payload.get("call_id"))
                if call:
                    call["exit_code"], call["output"] = _tool_output(payload.get("output"))
                    call["at"] = at or call["at"]
    # Codex records each command as a CommandExecution item. Plain tool calls are the
    # fallback for logs without those, and would count the same command twice next to them.
    events = [event for event in events if event["kind"] != "call" or not executions]
    for event in events:
        if event["kind"] == "call":
            event["kind"] = "command"
    return {
        "agent": _session_agent(meta, rollout, solo),
        "path": rollout.relative_to(ws).as_posix(),
        "events": events,
        "final": final if isinstance(final, str) else None,
    }


def read_sessions(ws: Path, solo: bool = False) -> tuple[list[dict], list[str]]:
    """Every readable rollout of a run, oldest first, and a warning for each that is not."""
    sessions, warnings = [], []
    for rollout in sorted((ws / "codex-home" / "sessions").rglob("*.jsonl")):
        try:
            sessions.append(read_session(rollout, ws, solo))
        except OSError as error:
            warnings.append(f"cannot read {rollout.relative_to(ws)}: {error.strerror or error}")
    return sessions, warnings


def _timeline(sessions: list[dict], agent: str) -> list[dict]:
    """One agent's events across its sessions, in time order, each tagged with its rollout."""
    merged = []
    for order, session in enumerate(sessions):
        if session["agent"] == agent:
            merged += [{**event, "rollout": session["path"], "_order": (order, event["line"])}
                       for event in session["events"]]
    merged.sort(key=lambda event: (event["at"] is None, event["at"] or 0, event["_order"]))
    return merged


# --- message board ---------------------------------------------------------------------


def _board_time(value) -> float | None:
    """Post timestamps are microseconds; accept milliseconds and seconds too."""
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
        return None
    if value > 1e14:
        return value / 1e6
    if value > 1e11:
        return value / 1e3
    return float(value)


_POSTS_QUERY = "SELECT seq, channel, author, timestamp, payload FROM posts ORDER BY seq"


def _query_posts(database: Path) -> list[tuple]:
    db = sqlite3.connect(f"{database.as_uri()}?mode=ro", uri=True, timeout=5)
    try:
        return db.execute(_POSTS_QUERY).fetchall()
    finally:
        db.close()


def _board_rows(path: Path) -> list[tuple]:
    """The rows of the posts table, read without touching the run.

    Codex keeps the board in WAL mode and a stopped run leaves most posts in the `-wal` file.
    Reading that in place makes SQLite rewrite the `-shm` index next to it, so the database
    and its WAL are copied to a scratch directory and read there. If that fails (a run in
    progress can be copied mid-write), the original is opened read-only instead.
    """
    try:
        with tempfile.TemporaryDirectory(prefix="murmur-board-") as scratch:
            copy = Path(scratch) / path.name
            shutil.copyfile(path, copy)
            wal = path.with_name(f"{path.name}-wal")
            if wal.is_file():
                shutil.copyfile(wal, copy.with_name(wal.name))
            return _query_posts(copy)
    except (OSError, sqlite3.Error):
        return _query_posts(path)


def read_board(ws: Path) -> tuple[list[dict], list[str]]:
    """The board's posts in order as {"seq", "channel", "agent", "at", "text"}, and warnings.

    A solo run, or a swarm that never posted, has none.
    """
    path = ws / "codex-home" / BOARD_DB
    if not path.is_file():
        return [], []
    try:
        rows = _board_rows(path)
    except (OSError, sqlite3.Error) as error:
        return [], [f"cannot read the message board ({error}); receipts carry no board posts"]
    posts = []
    for seq, channel, author, timestamp, payload in rows:
        try:
            text = json.loads(payload).get("text")
        except (json.JSONDecodeError, TypeError, AttributeError):
            text = None
        if not isinstance(text, str) or not text.strip():
            continue
        posts.append({"seq": seq, "channel": str(channel), "at": _board_time(timestamp), "text": text,
                      "agent": _agent_from_path(author) or str(author)})
    return posts, []


# --- git -------------------------------------------------------------------------------


def _git(origin: Path, *args: str) -> str:
    """Run a read-only git command in origin.git and return its output, or raise ReceiptsError."""
    env = os.environ.copy()
    env |= {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "GIT_OPTIONAL_LOCKS": "0"}
    try:
        result = subprocess.run(["git", *args], cwd=origin, env=env, capture_output=True, check=False,
                                timeout=GIT_TIMEOUT_S)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ReceiptsError(f"git {args[0]} failed: {error}") from None
    if result.returncode != 0:
        detail = result.stderr.decode(errors="replace").strip().splitlines()
        raise ReceiptsError(f"git {args[0]} failed: {detail[-1] if detail else result.returncode}")
    return result.stdout.decode(errors="replace")


_LOG_FORMAT = "%H%x00%P%x00%an%x00%ae%x00%at%x00%cn%x00%ce%x00%ct%x00%s%x00%b%x1e"


def _numstat(origin: Path, sha: str, parents: list[str]) -> list[dict]:
    """Paths a commit changed against its first parent, with lines added and removed."""
    target = [parents[0], sha] if parents else ["--root", sha]
    fields = _git(origin, "diff-tree", "--no-commit-id", "--numstat", "-z", "-r", "-M", *target).split("\0")
    paths, index = [], 0
    while index < len(fields) and fields[index]:
        added, removed, path = (fields[index].split("\t", 2) + ["", ""])[:3]
        index += 1
        if not path and index + 1 < len(fields):  # a rename: old and new path follow
            path = f"{fields[index]} => {fields[index + 1]}"
            index += 2
        # Binary files have no line counts.
        paths.append({"path": path, "insertions": int(added) if added.isdigit() else None,
                      "deletions": int(removed) if removed.isdigit() else None})
    return paths


def _pushes(origin: Path, branch: str, base: str, wanted: set[str]) -> dict[str, float]:
    """When each wanted commit reached `branch`, from the reflog origin.git keeps for it."""
    lines = _git(origin, "log", "-g", "--date=unix", "--format=%H%x00%gd", f"refs/heads/{branch}", "--")
    entries = []
    for line in lines.splitlines():
        sha, _, selector = line.partition("\0")
        stamp = re.search(r"@\{(\d+)\}", selector)
        if sha and stamp:
            entries.append((sha, float(stamp[1])))
    entries.reverse()  # oldest first
    landed: dict[str, float] = {}
    previous = base
    for sha, at in entries:
        for commit in _git(origin, "rev-list", sha, f"^{previous}", f"^{base}", "--").split():
            if commit in wanted:
                landed.setdefault(commit, at)
        previous = sha
    return landed


def read_commits(ws: Path, base: str | None) -> tuple[list[dict], dict, list[str]]:
    """The commits a run added to origin.git, the branch tips, and warnings.

    Commits are those on any branch that `base` (the commit the run started from) does not
    contain: first the ones on `main`, oldest first, then the ones only another branch has.
    """
    origin = ws / "work" / "origin.git"
    warnings: list[str] = []
    if not origin.is_dir():
        return [], {}, [f"{origin.relative_to(ws)} is missing; there are no commits to describe"]
    try:
        refs = dict(line.split("\0", 1) for line in _git(
            origin, "for-each-ref", "--format=%(refname:short)%00%(objectname)", "refs/heads/").splitlines())
        if not base:
            return [], refs, ["murmur.json names no base commit, so the run's commits cannot be told apart"]
        log = _git(origin, "log", "--topo-order", "--reverse", f"--format={_LOG_FORMAT}",
                   "--branches", "--not", base, "--")
    except ReceiptsError as error:
        return [], {}, [f"cannot list the run's commits: {error}"]
    commits = []
    for record in log.split("\x1e"):
        fields = record.strip("\n").split("\0")
        if len(fields) != 10:
            continue
        sha, parents, an, ae, at, cn, ce, ct, subject, body = fields
        commits.append({
            "sha": sha, "parents": parents.split(), "subject": subject, "body": body.strip(),
            "author": {"name": an, "email": ae}, "authored_at": float(at),
            "committer": {"name": cn, "email": ce}, "committed_at": float(ct),
            "branches": [], "paths": [], "pushes": {},
        })
    by_sha = {commit["sha"]: commit for commit in commits}
    reflog_missing = []
    for branch in sorted(refs, key=lambda name: (name != "main", name)):
        try:
            for sha in _git(origin, "rev-list", f"refs/heads/{branch}", f"^{base}", "--").split():
                if sha in by_sha:
                    by_sha[sha]["branches"].append(branch)
            landed = _pushes(origin, branch, base, set(by_sha))
        except ReceiptsError:
            landed = {}
        if not landed and any(branch in commit["branches"] for commit in commits):
            reflog_missing.append(branch)
        for sha, at in landed.items():
            by_sha[sha]["pushes"][branch] = at
    if reflog_missing:
        warnings.append(f"no reflog for {', '.join(reflog_missing)}: push times are unknown there")
    for commit in commits:
        try:
            commit["paths"] = _numstat(origin, commit["sha"], commit["parents"])
        except ReceiptsError as error:
            warnings.append(f"cannot read the changes of {commit['sha'][:7]}: {error}")
    commits.sort(key=lambda commit: "main" not in commit["branches"])  # stable: keeps topo order
    return commits, refs, warnings


# --- putting receipts together ---------------------------------------------------------

_TRAILER = re.compile(r"(?im)^\s*verified\s*:\s*(.+)$")
_NOT_RUN = re.compile(r"(?i)^(?:not\s+run|none|no|n/?a)\b")
_CLAIM_WORDS = re.compile(r"(?i)\b(?:verif(?:y|ied|ication)|tests?\s+(?:pass|passed|passing|ok|green)|all\s+green)\b")
_HEX = re.compile(r"\b[0-9a-f]{7,40}\b")


def _commit_agent(identity: dict) -> str | None:
    email = identity.get("email") or ""
    return email[: -len(AGENT_EMAIL)] if email.endswith(AGENT_EMAIL) and len(email) > len(AGENT_EMAIL) else None


def _anchor(commit: dict, timeline: list[dict]) -> tuple[int, float, str | None, dict | None]:
    """Where a commit sits in its author's timeline: (events before or with it, time, how, command).

    `how` is "commit-output" when a command printed git's `[branch sha]` line for this commit,
    and "author-time" when only the commit's author time places it; that also covers a commit
    whose SHA changed in a rebase, because a rebase keeps the author time.
    """
    sha, authored = commit["sha"], commit["authored_at"]
    for position, event in enumerate(timeline):
        if event["kind"] == "command" and any(
                sha.startswith(found) for found in _COMMIT_LINE.findall(event["output"])):
            return position + 1, event["at"] or authored, "commit-output", event
    if not timeline:
        return 0, authored, None, None
    for position, event in enumerate(timeline):
        late = event["at"] is not None and event["at"] >= authored - 1
        if late and event["kind"] == "command" and event["at"] <= authored + COMMIT_COMMAND_WINDOW_S \
                and _COMMITTING.search(event["script"]):
            return position + 1, event["at"], "author-time", event
    # Author times are whole seconds: everything logged within that second counts as before.
    before = sum(1 for event in timeline if event["at"] is None or event["at"] < authored + 1)
    return before, authored, "author-time", None


def _source(event: dict) -> dict:
    return {"rollout": event["rollout"], "line": event["line"]}


def _checks(events: list[dict], when: str, anchor: dict | None, ws: Path, redact: Redactor) -> list[dict]:
    found = []
    for event in events:
        if event["kind"] != "command":
            continue
        cwd = event["cwd"]
        for root in (str(ws), str(ws.resolve())):
            if cwd == root or cwd.startswith(root + "/"):
                cwd = cwd[len(root):].lstrip("/") or "."
                break
        whole = len(_split(event["script"])) == 1
        for kind, command, result, checkout in checks_in(event["script"], event["exit_code"]):
            found.append({
                "kind": kind,
                "command": redact.clip(command, MAX_COMMAND),
                "exit_code": event["exit_code"],
                "result": result,
                "when": "with" if event is anchor else when,
                "checkout": redact.clip(checkout, MAX_COMMAND) if checkout else None,
                "at": _iso(event["at"]),
                "cwd": redact(cwd),
                "output_excerpt": redact.excerpt(event["output"], whole),
                "source": _source(event),
            })
    return found


def _counts(check: dict) -> bool:
    return check["when"] != "after" and not check["checkout"]


def _verification(agent: str | None, checks: list[dict], claims: list[dict], how: str | None,
                  command: dict | None, has_log: bool) -> dict:
    """Grade what is known about a commit's checks. `command` is the logged command that made it."""
    # Per kind of check, the verdict of the last run that has one. A later run without a
    # verdict (`pytest | tail`) does not take a pass or a failure back, but it is mentioned.
    # Listed but not graded: what an agent ran after its last commit (by then it may be
    # reviewing the merged result), and what it ran right after checking out something else
    # (a peer's draft, say).
    latest: dict[str, str] = {}
    unclear: list[str] = []
    uncounted = sum(1 for check in checks if not _counts(check))
    for check in checks:
        if not _counts(check):
            continue
        kind = check["kind"]
        if kind in unclear:
            unclear.remove(kind)
        if check["result"] in ("passed", "failed"):
            latest[kind] = check["result"]
        else:
            unclear.append(kind)

    def kinds(result: str) -> str:
        return " and ".join(kind for kind, value in latest.items() if value == result)

    who = f"{agent}'s session log" if agent else "the session logs"
    real_claims = [claim for claim in claims if not claim.get("not_run")]
    later = f"; a later {' and '.join(unclear)} run has no exit status of its own" if unclear else ""
    if "failed" in latest.values():
        status = "observed-fail"
        summary = f"the last {kinds('failed')} run with an exit status of its own in {who} exited non-zero{later}"
    elif "passed" in latest.values():
        status = "observed-pass"
        summary = f"the last {kinds('passed')} run with an exit status of its own in {who} exited 0{later}"
    elif unclear:
        status = "observed-unclear"
        summary = (f"a {' and '.join(unclear)} command ran in {who}, but its own exit status was not recorded "
                   "or is hidden by a pipe or a later command")
    else:
        missing = (f"no test, lint or build command in {who} before this commit" if has_log
                   else f"there is no session log for {agent or 'this author'}")
        if uncounted:
            missing += f" ({uncounted} listed but not counted: run after the commit or on another checkout)"
        if real_claims:
            status, summary = "claimed", f"an agent says this was verified, but {missing}"
        else:
            status, summary = "none", missing
            if claims:
                summary += "; the agent stated that no check was run"
    return {
        "status": status,
        "summary": summary,
        "checks": checks,
        "claims": claims,
        "linked_by": how,
        "certainty": {"commit-output": "observed", "author-time": "inferred"}.get(how, "unknown"),
        "commit_source": _source(command) if command else None,
    }


def _receipt(commit: dict, redact: Redactor) -> dict:
    author, committer = commit["author"], commit["committer"]
    agent = _commit_agent(author)
    paths = commit["paths"]
    integrator = _commit_agent(committer) if committer["email"] != author["email"] else None
    return {
        "sha": commit["sha"],
        "short": commit["sha"][:7],
        "base_sha": commit["parents"][0] if commit["parents"] else None,
        "parents": commit["parents"],
        "subject": redact.clip(commit["subject"]),
        "who": {
            "agent": agent,
            "author": redact(f"{author['name']} <{author['email']}>"),
            "committer": (redact(f"{committer['name']} <{committer['email']}>")
                          if committer["email"] != author["email"] else None),
            "integrated_by": integrator,
        },
        "when": {
            "authored_at": _iso(commit["authored_at"]),
            "committed_at": _iso(commit["committed_at"]),
            "pushed": {branch: _iso(at) for branch, at in commit["pushes"].items()},
        },
        "on_main": "main" in commit["branches"],
        "branches": commit["branches"],
        "change": {
            "files": len(paths),
            "insertions": sum(path["insertions"] or 0 for path in paths),
            "deletions": sum(path["deletions"] or 0 for path in paths),
            "paths": [{**path, "path": redact(path["path"])} for path in paths[:MAX_PATHS]],
            "paths_omitted": max(0, len(paths) - MAX_PATHS),
        },
        "why": {"message": redact.clip(commit["body"], MAX_BODY), "intent": None, "board": []},
        "verification": None,
    }


def _board_links(commit: dict, agent: str | None, posts: list[dict], start: float, end: float,
                 others: list[str], redact: Redactor) -> list[dict]:
    """Posts that name this commit, and the author's own posts made while working towards it.

    A post that names one of the run's `others` commits is about that commit, whenever it was made.
    """
    linked = []
    for post in posts:
        named = _HEX.findall(post["text"])
        names = any(commit["sha"].startswith(token) for token in named)
        elsewhere = any(sha.startswith(token) for token in named for sha in others)
        mine = (agent and post["agent"] == agent and not elsewhere
                and post["at"] is not None and start < post["at"] <= end)
        if names or mine:
            linked.append({
                "seq": post["seq"], "channel": post["channel"], "agent": post["agent"], "at": _iso(post["at"]),
                "text": redact.clip(post["text"]),
                "link": "names-commit" if names else "before-commit",
                "certainty": "observed" if names else "inferred",
            })
    naming = [post for post in linked if post["link"] == "names-commit"][:MAX_POSTS]
    room = MAX_POSTS - len(naming)
    before = [post for post in linked if post["link"] == "before-commit"][-room:] if room else []
    return sorted(naming + before, key=lambda post: post["seq"])


def _claims(commit: dict, board: list[dict], redact: Redactor) -> list[dict]:
    claims = []
    for match in _TRAILER.finditer(commit["body"]):
        text = match[1].strip()
        claims.append({"source": "commit-message", "text": redact.clip(f"Verified: {text}"),
                       "not_run": bool(_NOT_RUN.match(text)), "agent": _commit_agent(commit["author"]),
                       "at": _iso(commit["authored_at"]), "seq": None})
    for post in board:
        if post["link"] == "names-commit" and _CLAIM_WORDS.search(post["text"]):
            claims.append({"source": "board", "text": post["text"], "not_run": False,
                           "agent": post["agent"], "at": post["at"], "seq": post["seq"]})
    return claims


def load_meta(ws: Path) -> dict:
    path = ws / "murmur.json"
    if not path.is_file():
        raise ReceiptsError(f"no workspace at {ws}")
    try:
        meta = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise ReceiptsError(f"unreadable {path}: {error}") from None
    if not isinstance(meta, dict):
        raise ReceiptsError(f"{path} is not a murmur workspace file")
    return meta


def _run_record(ws: Path) -> dict:
    try:
        record = json.loads((ws / "logs" / "run.json").read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    return record if isinstance(record, dict) else {}


def collect(ws: Path) -> dict:
    """The receipts document for a workspace: run facts, one receipt per commit, agents, warnings.

      schema, generated_at
      run        id, mode, peers, model, effort, base, head, commits_on_main, commits_off_main,
                 finished, exit_code, diagnostic
      receipts   sha, short, base_sha, parents, subject, on_main, branches,
                 who {agent, author, committer, integrated_by},
                 when {authored_at, committed_at, pushed {branch: time}},
                 change {files, insertions, deletions, paths [{path, insertions, deletions}]},
                 why {message, intent {text, at, source}, board [{seq, channel, agent, at, text, link}]},
                 verification {status, summary, linked_by, certainty, commit_source,
                               checks [{kind, command, exit_code, result, when, checkout, at, cwd,
                                        output_excerpt, source {rollout, line}}],
                               claims [{source, text, not_run, agent, at, seq}]}
      agents     id, role, sessions, commits, checks, checks_without_commit, final_message
      warnings   what could not be read

    Receipts on `main` come first, oldest first, then those only another branch has. Times are
    ISO 8601 in UTC. Raises ReceiptsError only when `ws` is not a murmur workspace: a missing
    board, missing or damaged session logs, or a missing reflog leave gaps that `warnings` names.
    """
    ws = Path(ws)
    meta = load_meta(ws)
    redact = Redactor(ws)
    solo = meta.get("mode") == "solo"
    base = meta.get("base")
    base = base if isinstance(base, str) and re.fullmatch(r"[0-9a-f]{7,64}", base) else None
    commits, refs, warnings = read_commits(ws, base)
    sessions, session_warnings = read_sessions(ws, solo)
    posts, board_warnings = read_board(ws)
    warnings += session_warnings + board_warnings
    if not sessions:
        warnings.append("no Codex session logs found; nothing about verification could be observed")

    receipts = {commit["sha"]: _receipt(commit, redact) for commit in commits}
    by_agent: dict[str | None, list[dict]] = {}
    for commit in commits:
        by_agent.setdefault(_commit_agent(commit["author"]), []).append(commit)
    for agent, own in by_agent.items():
        timeline = _timeline(sessions, agent) if agent else []
        anchored = sorted(((*_anchor(commit, timeline), commit) for commit in own),
                          key=lambda item: (item[0], item[1]))
        previous_position, previous_time = 0, float("-inf")
        for index, (position, at, how, command, commit) in enumerate(anchored):
            # Commits with the same anchor (a draft and its rebased copy) share one set of evidence.
            last = all(other[0] == position for other in anchored[index:])
            window = timeline[previous_position:position]
            checks = _checks(window, "before", command, ws, redact)
            if last:
                checks += _checks(timeline[position:], "after", None, ws, redact)
            said = [event for event in window if event["kind"] == "say"]
            receipt = receipts[commit["sha"]]
            if said:
                receipt["why"]["intent"] = {"text": redact.clip(said[-1]["text"]), "at": _iso(said[-1]["at"]),
                                            "source": _source(said[-1])}
            end = max(at, commit["authored_at"])
            others = [sha for sha in receipts if sha != commit["sha"]]
            receipt["why"]["board"] = _board_links(commit, agent, posts, previous_time, end, others, redact)
            claims = _claims(commit, receipt["why"]["board"], redact)
            receipt["verification"] = _verification(agent, checks, claims, how, command, bool(timeline))
            following = anchored[index + 1][0] if index + 1 < len(anchored) else None
            if following != position:
                previous_position, previous_time = position, end

    listed = meta.get("agents") if isinstance(meta.get("agents"), list) else []
    ids = [agent.get("id") for agent in listed if isinstance(agent, dict)]
    names = [name for name in dict.fromkeys(
        [*([] if solo else ["root"]), *ids, *(session["agent"] for session in sessions),
         *(agent for agent in by_agent if agent)]) if isinstance(name, str)]
    agents = []
    for name in names:
        own_sessions = [session for session in sessions if session["agent"] == name]
        final = next((session["final"] for session in reversed(own_sessions) if session["final"]), None)
        checks = _checks(_timeline(sessions, name), "no-commit", None, ws, redact)
        agents.append({
            "id": name,
            "role": "solo" if solo else "root" if name == "root" else "peer",
            "sessions": [session["path"] for session in own_sessions],
            "commits": len(by_agent.get(name, [])),
            "checks": len(checks),
            # An agent that only reviewed has checks that belong to no commit of its own.
            "checks_without_commit": [] if by_agent.get(name) else checks,
            "final_message": redact.clip(final) if final else None,
        })

    record = _run_record(ws)
    head = refs.get("main")
    return {
        "schema": SCHEMA,
        "generated_at": _iso(datetime.now(timezone.utc).timestamp()),
        "run": {
            "id": meta.get("run_id") or ws.name,
            "mode": meta.get("mode"),
            "peers": meta.get("peers"),
            "model": meta.get("model"),
            "effort": meta.get("effort"),
            "base": base,
            "head": head,
            "commits_on_main": sum(1 for receipt in receipts.values() if receipt["on_main"]),
            "commits_off_main": sum(1 for receipt in receipts.values() if not receipt["on_main"]),
            "finished": bool(record),
            "exit_code": record.get("exit_code"),
            "diagnostic": record.get("diagnostic"),
        },
        "receipts": list(receipts.values()),
        "agents": agents,
        "warnings": warnings,
    }


def to_json(document: dict) -> str:
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def for_agent(document: dict, agent: str | None) -> dict:
    """The document with only one agent's receipts (and all of them when `agent` is None)."""
    if agent is None:
        return document
    return {**document,
            "receipts": [receipt for receipt in document["receipts"] if receipt["who"]["agent"] == agent],
            "agents": [entry for entry in document["agents"] if entry["id"] == agent]}


# --- rendering -------------------------------------------------------------------------


def _clock(stamp: str | None) -> str:
    return stamp[11:] if stamp else "?"


def _indent(text: str, prefix: str) -> list[str]:
    return [f"{prefix}{line}" for line in text.splitlines()]


def _stat(change: dict) -> str:
    files = change["files"]
    return f"{files} file{'' if files == 1 else 's'}, +{change['insertions']} -{change['deletions']}"


def header_lines(document: dict) -> list[str]:
    run = document["run"]
    shape = "solo" if run["mode"] == "solo" else f"{run['mode']}, {run['peers']} peers"
    span = f"base {(run['base'] or '?')[:7]} -> main {(run['head'] or '?')[:7]}"
    lines = [f"change receipts for {run['id']} ({shape}, {run['model']}/{run['effort']})",
             f"{span}: {run['commits_on_main']} commit(s) on main, "
             f"{run['commits_off_main']} only on other branches"]
    if not run["finished"]:
        lines.append("the run has no logs/run.json yet: it is still going or did not end cleanly")
    return lines


_WHEN = {"before": "before the commit", "with": "in the commit command",
         "after": "after the commit (not counted)", "no-commit": "no commit of its own"}


def _short(text: str, limit: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else f"{text[:limit].rstrip()}..."
_MARKS = {"passed": "ok  ", "failed": "FAIL", "unclear": "?   ", "unknown": "?   "}


def _check_lines(check: dict, pad: str) -> list[str]:
    code = "exit ?" if check["exit_code"] is None else f"exit {check['exit_code']}"
    name = check["source"]["rollout"].rsplit("/", 1)[-1]
    source = f"{name if len(name) <= 24 else '...' + name[-18:]}:{check['source']['line']}"
    note = "  (the whole command line's status, not this check's own)" if check["result"] == "unclear" else ""
    lines = [f"{pad}{_MARKS[check['result']]} {code}  {check['command']}{note}",
             f"{pad}     {check['kind']}, {_WHEN[check['when']]}, {_clock(check['at'])}, "
             f"in {check['cwd'] or '?'} [{source}]"]
    if check["checkout"]:
        lines.append(f"{pad}     run after `{_short(check['checkout'], 80)}` in the same command line: "
                     "another checkout (not counted)")
    return [*lines, *_indent(check["output_excerpt"], f"{pad}     | ")]


_PAD = " " * 12


def _wrapped(first: str, text: str) -> list[str]:
    """`text` after `first`, wrapped, with the lines that follow indented under the column."""
    return textwrap.wrap(" ".join(text.split()), width=TEXT_WIDTH, initial_indent=first,
                         subsequent_indent=f"{_PAD}  ", break_long_words=False,
                         break_on_hyphens=False) or [first.rstrip()]


def receipt_lines(receipt: dict) -> list[str]:
    """One receipt as indented text: who, why, change, verified."""
    who, why, change, verified = receipt["who"], receipt["why"], receipt["change"], receipt["verification"]
    agent = who["agent"] or "unknown agent"
    where = "main" if receipt["on_main"] else ", ".join(receipt["branches"]) or "no branch"
    lines = [f"{receipt['short']}  {agent}  {receipt['subject']}"]
    pad = _PAD

    detail = f"{who['author']}, on {where}"
    pushed = receipt["when"]["pushed"]
    if pushed:
        branch = "main" if "main" in pushed else next(iter(pushed))
        detail += f", pushed to {branch} {_clock(pushed[branch])}"
    lines.append(f"  who:      {detail}")
    if who["committer"]:
        lines.append(f"{pad}committed by {who['committer']} (the author's change, applied by another agent)")

    reasons = []
    for line in why["message"].splitlines():
        if line.strip() and not _TRAILER.match(line):  # the Verified: line is shown as a claim below
            reasons.append(line.strip())
    if why["intent"]:
        reasons.append(f'said before: "{_short(why["intent"]["text"], SHOWN_SAID)}"')
    for post in why["board"]:
        note = "names this commit" if post["link"] == "names-commit" else "before the commit, linked by time"
        reasons.append(f'board #{post["channel"]} {post["agent"]} {_clock(post["at"])} ({note}): '
                       f'"{_short(post["text"], SHOWN_POST)}"')
    if not reasons:
        reasons.append("(only the subject: the commit message has no body, and nothing else was linked)")
    for index, reason in enumerate(reasons):
        lines += _wrapped("  why:      " if index == 0 else pad, reason)

    names = [path["path"] for path in change["paths"][:6]]
    more = change["files"] - len(names)
    lines.append(f"  change:   {(receipt['base_sha'] or 'no parent')[:7]} -> {receipt['short']}, {_stat(change)}: "
                 + ", ".join(names) + (f", +{more} more" if more > 0 else ""))

    lines += _wrapped("  verified: ", f"{STATUS_LABELS[verified['status']]}: {verified['summary']}")
    for check in verified["checks"]:
        lines += _check_lines(check, pad)
    if verified["checks"] and verified["linked_by"] == "author-time":
        lines.append(f"{pad}(tied to this commit by its author time, not by its SHA: inferred)")
    for claim in verified["claims"]:
        if claim["source"] == "board":  # the post itself is quoted under `why`
            lines.append(f"{pad}claim (board post by {claim['agent']} at {_clock(claim['at'])}, quoted above)")
        else:
            lines += _wrapped(pad, f'claim (commit message): "{_short(claim["text"], SHOWN_POST)}"')
    return lines


def render_text(document: dict) -> str:
    lines = header_lines(document)
    main = [receipt for receipt in document["receipts"] if receipt["on_main"]]
    other = [receipt for receipt in document["receipts"] if not receipt["on_main"]]
    for receipt in main:
        lines += ["", *receipt_lines(receipt)]
    if other:
        lines += ["", "not on main:"]
        for receipt in other:
            lines += ["", *receipt_lines(receipt)]
    if not document["receipts"]:
        lines += ["", "no commits to describe"]
    lines += agent_lines(document)
    lines += [f"note: {warning}" for warning in document["warnings"]]
    return "\n".join(lines) + "\n"


def agent_lines(document: dict) -> list[str]:
    """Agents that made no commit, with the checks they ran: a reviewer's evidence is its own."""
    lines = []
    for agent in document["agents"]:
        if agent["role"] == "root" or agent["commits"]:
            continue
        checks = agent["checks_without_commit"]
        lines += ["", f"{agent['id']} made no commits"
                      + (f"; checks in its session log ({len(checks)}):" if checks else " and ran no checks")]
        for check in checks:
            lines += _check_lines(check, "  ")
    return lines


def _fenced(lines: list[str]) -> list[str]:
    """Lines as a markdown code block whose fence is longer than any run of backticks inside."""
    longest = max((len(run) for line in lines for run in re.findall(r"`+", line)), default=0)
    fence = "`" * max(3, longest + 1)
    return [f"{fence}text", *lines, fence, ""]


def render_markdown(document: dict) -> str:
    """The same receipts as a markdown file: a heading per commit over its text block."""
    head = header_lines(document)
    lines = [f"# {head[0][0].upper()}{head[0][1:]}", "", *head[1:], "",
             "`OBSERVED` means murmur found the command and its exit status in the agent's session log. "
             "`CLAIMED` means only an agent says so. Checks are the test, lint and build commands an "
             "agent ran after its previous commit and up to this one.", ""]
    for receipt in document["receipts"]:
        branch = "" if receipt["on_main"] else " (not on main)"
        lines += [f"## {receipt['short']} by {receipt['who']['agent'] or 'unknown agent'}{branch}", "",
                  *_fenced(receipt_lines(receipt))]
    if others := agent_lines(document)[1:]:
        lines += ["## Agents without commits", "", *_fenced(others)]
    lines += [f"- note: {warning}" for warning in document["warnings"]]
    return "\n".join(lines).rstrip("\n") + "\n"


def write(ws: Path, document: dict | None = None) -> Path:
    """Write logs/receipts.json and logs/receipts.md for a workspace; returns the JSON path."""
    ws = Path(ws)
    document = collect(ws) if document is None else document
    logs = ws / "logs"
    logs.mkdir(exist_ok=True)
    for name, text in (("receipts.json", to_json(document)), ("receipts.md", render_markdown(document))):
        partial = logs / f"{name}.partial"
        partial.write_text(text, encoding="utf-8")
        partial.replace(logs / name)
    return logs / "receipts.json"
