"""Process-group lifetime for one Codex invocation."""

from __future__ import annotations

import os
import signal
import subprocess
import time
from pathlib import Path


def install_interrupt_handlers():
    previous = {}
    for sig in (signal.SIGTERM, signal.SIGHUP):
        previous[sig] = signal.signal(sig, _interrupt)
    return previous


def restore_interrupt_handlers(previous) -> None:
    for sig, handler in previous.items():
        signal.signal(sig, handler)


def _interrupt(signum, frame) -> None:
    raise KeyboardInterrupt


def _grace(name: str, default: float, override: float | None) -> float:
    if override is not None:
        return override
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return float(raw)


def pid_alive(pid: int | None) -> bool:
    if not pid or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def proc_stat_fields(pid: int) -> list[str] | None:
    try:
        text = Path(f"/proc/{pid}/stat").read_text()
    except OSError:
        return None
    parts = text.rsplit(")", 1)
    if len(parts) != 2:
        return None
    return parts[1].split()


def process_start_ticks(pid: int) -> int | None:
    fields = proc_stat_fields(pid)
    if not fields or len(fields) <= 19:
        return None
    try:
        return int(fields[19])
    except ValueError:
        return None


def is_zombie(pid: int) -> bool:
    fields = proc_stat_fields(pid)
    if fields:
        return fields[0] == "Z"
    try:
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "stat="],
            capture_output=True, text=True, check=False,
        )
    except OSError:
        return False
    return "Z" in result.stdout


def cmdline(pid: int) -> str:
    try:
        data = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        data = b""
    if data:
        return data.replace(b"\0", b" ").decode(errors="replace").strip()
    try:
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "command="],
            capture_output=True, text=True, check=False,
        )
    except OSError:
        return ""
    return result.stdout.strip()


def safe_pgid(pgid: int) -> bool:
    return pgid > 1 and pgid != os.getpgid(0)


def group_alive(pgid: int) -> bool:
    if pgid <= 1:
        return False
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _signal_group(pgid: int, sig: int) -> None:
    # Never signal our own group or init. Codex is started in a new session.
    if pgid <= 1 or pgid == os.getpgid(0):
        return
    try:
        os.killpg(pgid, sig)
    except ProcessLookupError:
        return


def _wait_until_dead(pgid: int, proc: subprocess.Popen | None, timeout: float) -> bool:
    deadline = time.monotonic() + max(0.0, timeout)
    while True:
        if proc is not None and proc.poll() is None:
            remaining = deadline - time.monotonic()
            if remaining > 0:
                try:
                    proc.wait(timeout=min(0.05, remaining))
                except subprocess.TimeoutExpired:
                    pass
        if not group_alive(pgid):
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.02)


def stop_pgid(
    pgid: int, *, term_grace: float | None = None, kill_grace: float | None = None
) -> None:
    """SIGTERM a group, then SIGKILL any member still present after the grace period."""
    if pgid <= 1 or pgid == os.getpgid(0):
        return
    term = _grace("MURMUR_TERM_GRACE", 15, term_grace)
    kill = _grace("MURMUR_KILL_GRACE", 5, kill_grace)
    _signal_group(pgid, signal.SIGTERM)
    if _wait_until_dead(pgid, None, term):
        return
    _signal_group(pgid, signal.SIGKILL)
    _wait_until_dead(pgid, None, kill)


def stop_process_group(
    proc: subprocess.Popen,
    *,
    term_grace: float | None = None,
    kill_grace: float | None = None,
) -> None:
    """Stop the leader and descendants that share its process group.

    The leader exiting does not mean the group is gone: a child can ignore
    SIGTERM. Reap the leader, then escalate to SIGKILL if anyone remains.
    """
    if proc.pid is None:
        return
    pgid = proc.pid
    term = _grace("MURMUR_TERM_GRACE", 15, term_grace)
    kill = _grace("MURMUR_KILL_GRACE", 5, kill_grace)
    _signal_group(pgid, signal.SIGTERM)
    if not _wait_until_dead(pgid, proc, term):
        _signal_group(pgid, signal.SIGKILL)
        _wait_until_dead(pgid, proc, kill)
    if proc.poll() is None:
        try:
            proc.wait(timeout=0.2)
        except subprocess.TimeoutExpired:
            pass
