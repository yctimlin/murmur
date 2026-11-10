"""The per-run model catalog pins swarm tool_mode only when the catalog left it unset."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from murmur.cli import EXIT_LAUNCHER, write_model_catalog


def _stub_models(monkeypatch, models: list[dict]) -> None:
    payload = json.dumps({"models": models})

    def fake_run(argv, **kwargs):
        assert argv[:3] == ["codex", "debug", "models"]
        return subprocess.CompletedProcess(argv, 0, payload, "")

    monkeypatch.setattr("murmur.cli.subprocess.run", fake_run)


def test_swarm_sets_code_mode_only_when_tool_mode_is_null(tmp_path: Path, monkeypatch):
    _stub_models(monkeypatch, [
        {"slug": "gpt-6-astra", "tool_mode": None},
        {"slug": "other-model"},
    ])
    dest = tmp_path / "models.json"
    write_model_catalog(dest, "gpt-6-astra", "high", solo=False)
    by_slug = {entry["slug"]: entry for entry in json.loads(dest.read_text())["models"]}
    assert by_slug["gpt-6-astra"]["tool_mode"] == "code_mode_only"
    assert by_slug["gpt-6-astra"]["multi_agent_reasoning_effort"] == "high"
    assert "tool_mode" not in by_slug["other-model"]


def test_explicit_tool_mode_is_preserved(tmp_path: Path, monkeypatch):
    _stub_models(monkeypatch, [{"slug": "gpt-6-astra", "tool_mode": "direct"}])
    dest = tmp_path / "models.json"
    write_model_catalog(dest, "gpt-6-astra", "high", solo=False)
    entry = json.loads(dest.read_text())["models"][0]
    assert entry["tool_mode"] == "direct"


def test_solo_leaves_tool_mode_unset(tmp_path: Path, monkeypatch):
    _stub_models(monkeypatch, [{
        "slug": "gpt-6-astra",
        "tool_mode": None,
        "multi_agent_version": "v2",
    }])
    dest = tmp_path / "models.json"
    write_model_catalog(dest, "gpt-6-astra", "high", solo=True)
    entry = json.loads(dest.read_text())["models"][0]
    assert entry["tool_mode"] is None
    assert entry["multi_agent_version"] is None


@pytest.mark.parametrize("payload", [{"models": []}, {}])
def test_empty_catalog_fails_before_writing(tmp_path: Path, monkeypatch, capsys, payload):
    def fake_run(argv, **kwargs):
        return subprocess.CompletedProcess(argv, 0, json.dumps(payload), "")

    monkeypatch.setattr("murmur.cli.subprocess.run", fake_run)
    dest = tmp_path / "models.json"
    with pytest.raises(SystemExit) as exc:
        write_model_catalog(dest, "gpt-6-astra", "high", solo=False)
    assert exc.value.code == EXIT_LAUNCHER
    assert "returned no models" in capsys.readouterr().err
    assert not dest.exists()


def _stub_output(monkeypatch, returncode: int, stdout: str, stderr: str = "") -> None:
    def fake_run(argv, **kwargs):
        return subprocess.CompletedProcess(argv, returncode, stdout, stderr)

    monkeypatch.setattr("murmur.cli.subprocess.run", fake_run)


def _fails(tmp_path: Path, capsys, model="gpt-6-astra", effort="high", solo=False) -> str:
    dest = tmp_path / "models.json"
    with pytest.raises(SystemExit) as exc:
        write_model_catalog(dest, model, effort, solo=solo)
    assert exc.value.code == EXIT_LAUNCHER
    assert not dest.exists()
    return capsys.readouterr().err


def test_failing_codex_debug_models_is_a_launcher_error(tmp_path: Path, monkeypatch, capsys):
    _stub_output(monkeypatch, 5, "", "warning: x\nerror: not logged in\n")
    assert "`codex debug models` failed (5): error: not logged in" in _fails(tmp_path, capsys)


def test_non_json_catalog_is_a_launcher_error(tmp_path: Path, monkeypatch, capsys):
    _stub_output(monkeypatch, 0, "Usage: codex debug ...\n")
    assert "did not print JSON" in _fails(tmp_path, capsys)


def test_swarm_model_missing_from_catalog_fails(tmp_path: Path, monkeypatch, capsys):
    _stub_models(monkeypatch, [{"slug": "gpt-6-astra"}, {"slug": "gpt-6-sol"}])
    err = _fails(tmp_path, capsys, model="nosuchmodel")
    assert "'nosuchmodel' is not in Codex's model catalog" in err
    assert "gpt-6-astra, gpt-6-sol" in err


def test_solo_model_missing_from_catalog_warns(tmp_path: Path, monkeypatch, capsys):
    _stub_models(monkeypatch, [{"slug": "gpt-6-astra", "multi_agent_version": "v2"}])
    dest = tmp_path / "models.json"
    write_model_catalog(dest, "nosuchmodel", "high", solo=True)
    assert "'nosuchmodel' is not in Codex's model catalog" in capsys.readouterr().err
    assert json.loads(dest.read_text())["models"][0]["multi_agent_version"] is None


def test_effort_the_model_does_not_support_fails(tmp_path: Path, monkeypatch, capsys):
    levels = [{"effort": "low"}, {"effort": "high"}]
    _stub_models(monkeypatch, [{"slug": "gpt-6-astra", "supported_reasoning_levels": levels}])
    err = _fails(tmp_path, capsys, effort="hgih")
    assert "gpt-6-astra does not support effort 'hgih'; use one of: low, high" in err
