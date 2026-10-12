"""Exclusive workspace lock and versioned run state.

States: ready, running, succeeded, failed, capped, interrupted.
Each attempt keeps its logs under logs/attempts/<id>/. A later attempt does
not truncate them. `logs/run.json` is only the latest summary.
"""

from __future__ import annotations

import fcntl
import json
import os
import shutil
from pathlib import Path

from murmur.atomic import atomic_write_json
from murmur.errors import EXIT_LAUNCHER, fail
from murmur.procutil import (
    cmdline,
    is_zombie,
    pid_alive,
    process_start_ticks,
    safe_pgid,
    stop_pgid,
)
from murmur.util import now

STATE_VERSION = 1
TERMINAL = {"succeeded", "failed", "capped", "interrupted"}


class WorkspaceBusy(Exception):
    def __init__(self, holder: str) -> None:
        self.holder = holder


class WorkspaceLock:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.fd: int | None = None

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.fd = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o644)
        try:
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.lseek(self.fd, 0, os.SEEK_SET)
            raw = os.read(self.fd, 128).decode(errors="replace").strip()
            holder = raw.splitlines()[0] if raw else "another process"
            os.close(self.fd)
            self.fd = None
            raise WorkspaceBusy(holder) from None
        os.ftruncate(self.fd, 0)
        os.write(self.fd, f"{os.getpid()}\n".encode())
        os.fsync(self.fd)

    def release(self) -> None:
        if self.fd is None:
            return
        try:
            fcntl.flock(self.fd, fcntl.LOCK_UN)
        finally:
            os.close(self.fd)
            self.fd = None


def ready_state() -> dict:
    return {
        "version": STATE_VERSION,
        "state": "ready",
        "updated_at": now(),
        "attempt_id": None,
        "attempt_dir": None,
        "pid": None,
        "pgid": None,
        "hostname": None,
        "codex_pid": None,
        "codex_pgid": None,
        "codex_start_ticks": None,
        "started_at": None,
        "ended_at": None,
        "exit_code": None,
        "codex_exit_code": None,
        "reason": None,
        "command": None,
        "log": None,
        "protocol": None,
        "attempts": [],
    }


def load_state(ws: Path) -> dict | None:
    path = ws / "logs" / "state.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        fail(f"unreadable {path}: {exc}")
    if not isinstance(data, dict):
        fail(f"unreadable {path}: expected an object")
    return data


def save_state(ws: Path, state: dict) -> None:
    state["version"] = STATE_VERSION
    state["updated_at"] = now()
    atomic_write_json(ws / "logs" / "state.json", state)


def classify(ws: Path, state: dict | None) -> str:
    if state is None:
        legacy = (ws / "logs" / "run.json").is_file() and not (ws / "logs" / "state.json").is_file()
        return "legacy-finished" if legacy else "ready"
    if state.get("version") != STATE_VERSION:
        return "future"
    name = state.get("state")
    if name == "ready":
        return "ready"
    if name == "running":
        return _classify_running(ws, state)
    if name in TERMINAL:
        return "terminal"
    return "future"


def _classify_running(ws: Path, state: dict) -> str:
    pid = state.get("pid")
    if pid != os.getpid() and pid_alive(pid) and not is_zombie(int(pid)):
        text = cmdline(int(pid))
        # An empty cmdline means we could not prove the pid was reused.
        if not text or ("murmur" in text and str(ws) in text):
            return "active"
    return _child_or_stale(ws, state)


def _child_or_stale(ws: Path, state: dict) -> str:
    codex_pid = state.get("codex_pid")
    if codex_pid and pid_alive(int(codex_pid)) and not is_zombie(int(codex_pid)):
        if _safe_to_signal(int(codex_pid), ws, state.get("codex_start_ticks")):
            return "orphaned-active"
    return "stale"


def _safe_to_signal(pid: int, ws: Path, start_ticks: int | None) -> bool:
    if start_ticks is not None:
        current = process_start_ticks(pid)
        if current is not None and current != start_ticks:
            return False
        if current is not None and current == start_ticks:
            return True
    text = cmdline(pid)
    return bool(text) and ("codex" in text or str(ws) in text)


def ensure_launchable(ws: Path, *, recover: bool, retry: bool) -> dict:
    """Return state that may start a new attempt, or refuse."""
    state = load_state(ws)
    kind = classify(ws, state)
    if kind == "legacy-finished":
        fail(f"{ws.name} has already run; set up a new workspace")
    if kind == "future":
        version = None if state is None else state.get("version")
        fail(f"unsupported run state version {version}")
    if kind == "ready":
        return state or ready_state()
    assert state is not None
    if kind == "active":
        fail(f"{ws.name} is in use by pid {state.get('pid')}; refusing a concurrent run")
    if kind == "orphaned-active":
        if not recover:
            fail(
                f"{ws.name} attempt {state.get('attempt_id')} lost its launcher "
                f"(pid {state.get('pid')}) but codex pid {state.get('codex_pid')} is still running. "
                f"`murmur run --recover {ws}` stops it and starts a new attempt. "
                f"Evidence: {state.get('attempt_dir')}"
            )
        _stop_recorded_codex(ws, state)
        return _close(ws, state, "failed", "stale", EXIT_LAUNCHER)
    if kind == "stale":
        if not recover:
            fail(
                f"{ws.name} attempt {state.get('attempt_id')} is stale "
                f"(pid {state.get('pid')} is not running). Evidence remains in "
                f"{state.get('attempt_dir')}. `murmur run --recover {ws}` starts a new attempt."
            )
        return _close(ws, state, "failed", "stale", EXIT_LAUNCHER)
    if kind == "terminal":
        if state.get("state") == "succeeded" and not retry:
            fail(
                f"{ws.name} succeeded; logs kept in {state.get('attempt_dir')}. "
                "Re-run with --retry to start another attempt."
            )
        if not retry and not recover:
            fail(
                f"{ws.name} is {state.get('state')}; logs kept in {state.get('attempt_dir')}. "
                "Re-run with --retry to start another attempt."
            )
        return state
    fail(f"cannot start {ws.name}")


def begin_attempt(ws: Path, previous: dict) -> tuple[str, Path]:
    import secrets

    attempt_id = secrets.token_hex(8)
    attempt_dir = ws / "logs" / "attempts" / attempt_id
    attempt_dir.mkdir(parents=True, exist_ok=True)
    archive_protocol(ws, previous.get("attempt_dir"), clear=True)
    from murmur.atomic import atomic_write_text
    atomic_write_text(ws / "protocol" / "attempt", attempt_id + "\n")
    running = {
        "version": STATE_VERSION,
        "state": "running",
        "updated_at": now(),
        "attempt_id": attempt_id,
        "attempt_dir": str(attempt_dir.relative_to(ws)),
        "pid": os.getpid(),
        "pgid": os.getpgid(0),
        "hostname": _hostname(),
        "codex_pid": None,
        "codex_pgid": None,
        "codex_start_ticks": None,
        "started_at": now(),
        "ended_at": None,
        "exit_code": None,
        "codex_exit_code": None,
        "reason": None,
        "command": None,
        "log": None,
        "protocol": None,
        "attempts": list(previous.get("attempts") or []),
    }
    save_state(ws, running)
    return attempt_id, attempt_dir


def note_codex_process(ws: Path, pid: int) -> None:
    state = load_state(ws) or {}
    state["codex_pid"] = pid
    state["codex_pgid"] = pid
    state["codex_start_ticks"] = process_start_ticks(pid)
    save_state(ws, state)


def finalize_attempt(
    ws: Path,
    *,
    terminal: str,
    reason: str | None,
    exit_code: int,
    codex_exit: int | None,
    command,
    protocol,
    log: str | None,
) -> dict:
    state = load_state(ws) or ready_state()
    state["codex_exit_code"] = codex_exit
    state["command"] = command
    state["protocol"] = protocol
    state["log"] = log
    return _close(ws, state, terminal, reason, exit_code)


def archive_protocol(ws: Path, attempt_dir: str | None, *, clear: bool = False) -> None:
    live = ws / "protocol"
    if not live.exists():
        return
    if attempt_dir:
        dest = ws / attempt_dir / "protocol"
        dest.mkdir(parents=True, exist_ok=True)
        for path in live.iterdir():
            if path.name == "attempt" or not path.is_file():
                continue
            shutil.copy2(path, dest / path.name)
    if clear:
        for path in list(live.glob("*.json")):
            path.unlink()
        for path in list(live.glob("*.history.jsonl")):
            path.unlink()


def _close(ws: Path, state: dict, terminal: str, reason: str | None, exit_code: int) -> dict:
    archive_protocol(ws, state.get("attempt_dir"))
    ended = now()
    entry = {
        "id": state.get("attempt_id"),
        "state": terminal,
        "reason": reason,
        "dir": state.get("attempt_dir"),
        "started_at": state.get("started_at"),
        "ended_at": ended,
        "exit_code": exit_code,
        "codex_exit_code": state.get("codex_exit_code"),
    }
    attempts = [item for item in (state.get("attempts") or []) if item.get("id") != entry["id"]]
    attempts.append(entry)
    closed = dict(state)
    closed.update(
        state=terminal,
        reason=reason,
        ended_at=ended,
        exit_code=exit_code,
        attempts=attempts,
        pid=None,
    )
    save_state(ws, closed)
    rel = closed.get("attempt_dir")
    if rel:
        atomic_write_json(ws / rel / "record.json", closed)
    summary = {
        "attempt_id": closed.get("attempt_id"),
        "started_at": closed.get("started_at"),
        "ended_at": ended,
        "exit_code": exit_code,
        "codex_exit_code": closed.get("codex_exit_code"),
        "capped": terminal == "capped",
        "interrupted": terminal == "interrupted",
        "state": terminal,
        "reason": reason,
        "command": closed.get("command"),
        "log": closed.get("log"),
        "protocol": closed.get("protocol"),
    }
    atomic_write_json(ws / "logs" / "run.json", summary)
    return closed


def _stop_recorded_codex(ws: Path, state: dict) -> None:
    pid = state.get("codex_pid")
    pgid = state.get("codex_pgid") or pid
    if not pid or not pgid:
        return
    if not _safe_to_signal(int(pid), ws, state.get("codex_start_ticks")):
        return
    if safe_pgid(int(pgid)):
        stop_pgid(int(pgid))


def _hostname() -> str:
    import socket
    return socket.gethostname()
