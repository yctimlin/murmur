"""Regression test for setup refusing an empty Codex model catalog."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from murmur.cli import write_model_catalog


def test_empty_model_catalog_fails_without_writing_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fake_run(argv, **kwargs):
        assert argv[:3] == ["codex", "debug", "models"]
        return subprocess.CompletedProcess(argv, 0, json.dumps({"models": []}), "")

    monkeypatch.setattr("murmur.cli.subprocess.run", fake_run)
    destination = tmp_path / "models.json"

    with pytest.raises(SystemExit) as exc:
        write_model_catalog(destination, "gpt-6-astra", "high", solo=False)

    assert exc.value.code != 0
    assert "empty model catalog" in capsys.readouterr().err
    assert not destination.exists()
