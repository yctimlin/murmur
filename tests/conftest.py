"""Fixtures for launcher tests. No test talks to a live model."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
FAKE_CODEX = Path(__file__).resolve().parent / "fake_codex.py"


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    home = tmp_path / "home"
    tmp = tmp_path / "tmp"
    home.mkdir()
    tmp.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    codex = bin_dir / "codex"
    codex.symlink_to(FAKE_CODEX)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("TMPDIR", str(tmp))
    monkeypatch.setenv("USER", "tester")
    monkeypatch.setenv("LOGNAME", "tester")
    monkeypatch.delenv("CODEX_HOME", raising=False)
    monkeypatch.setenv("MURMUR_TERM_GRACE", "0.4")
    monkeypatch.setenv("MURMUR_KILL_GRACE", "0.4")
    monkeypatch.setenv("PYTHONPATH", str(ROOT / "src"))
    monkeypatch.setenv("PATH", str(bin_dir) + os.pathsep + os.environ.get("PATH", ""))
    yield tmp
    leftovers = [path for path in tmp.iterdir() if path.name.startswith("murmur")]
    assert leftovers == [], f"leaked temp paths: {leftovers}"
