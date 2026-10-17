from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from murmur.cli import write_model_catalog


def test_empty_codex_model_catalog_fails_without_writing(tmp_path: Path, monkeypatch, capsys):
    def fake_run(argv, **kwargs):
        assert argv[:3] == ["codex", "debug", "models"]
        return subprocess.CompletedProcess(argv, 0, json.dumps({"models": []}), "")

    monkeypatch.setattr("murmur.cli.subprocess.run", fake_run)
    dest = tmp_path / "models.json"

    with pytest.raises(SystemExit) as exc:
        write_model_catalog(dest, "gpt-6-astra", "high", solo=False)

    assert exc.value.code != 0
    assert "model catalog is empty" in capsys.readouterr().err
    assert not dest.exists()
