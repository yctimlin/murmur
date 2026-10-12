"""Lock, atomic writes, and versioned run state."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from murmur.atomic import atomic_write_json
from murmur.errors import MurmurError
from murmur.state import WorkspaceBusy, WorkspaceLock, ensure_launchable, save_state


def test_lock_is_exclusive(tmp_path: Path):
    path = tmp_path / "run.lock"
    first = WorkspaceLock(path)
    second = WorkspaceLock(path)
    first.acquire()
    try:
        with pytest.raises(WorkspaceBusy) as caught:
            second.acquire()
        assert str(os.getpid()) in caught.value.holder
    finally:
        first.release()
    second.acquire()
    second.release()


def test_atomic_write_failure_leaves_no_temp(tmp_path, monkeypatch):
    dest = tmp_path / "out"
    dest.mkdir()

    def boom(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        atomic_write_json(dest / "state.json", {"a": 1})
    assert list(dest.iterdir()) == []


def test_atomic_write_replaces_in_place(tmp_path: Path):
    dest = tmp_path / "out"
    dest.mkdir()
    target = dest / "state.json"
    atomic_write_json(target, {"a": 1})
    atomic_write_json(target, {"a": 2})
    assert json.loads(target.read_text())["a"] == 2
    assert list(dest.iterdir()) == [target]


def test_future_state_version_is_rejected(tmp_path: Path):
    workspace = tmp_path / "ws"
    (workspace / "logs").mkdir(parents=True)
    (workspace / "murmur.json").write_text("{}\n")
    save_state(workspace, {"version": 1, "state": "ready", "attempts": []})
    state_path = workspace / "logs" / "state.json"
    payload = json.loads(state_path.read_text())
    payload["version"] = 99
    state_path.write_text(json.dumps(payload))
    with pytest.raises(MurmurError, match="unsupported run state version"):
        ensure_launchable(workspace, recover=False, retry=False)
