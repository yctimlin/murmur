"""Stop a Codex process group, including descendants that ignore SIGTERM."""

from __future__ import annotations

import os
import signal
import subprocess
import time


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


def _grace(name: str, default: float, override: float | None) -> float:
    if override is not None:
        return override
    raw = os.environ.get(name)
    if not raw:
        return default
    return float(raw)


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
    # Codex is started with start_new_session, so its pid is the process group id.
    # Never signal this process's group or init.
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


def stop_process_group(
    proc: subprocess.Popen,
    *,
    term_grace: float | None = None,
    kill_grace: float | None = None,
) -> None:
    """SIGTERM the leader's group, then SIGKILL anyone still alive.

    The leader exiting does not clear the group: a child can ignore SIGTERM.
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
