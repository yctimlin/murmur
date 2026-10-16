"""The per-run model catalog pins swarm tool_mode only when the catalog left it unset."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from murmur.cli import write_model_catalog


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


def test_unspecified_model_prepares_all_without_pinning_effort(tmp_path: Path, monkeypatch):
    _stub_models(monkeypatch, [
        {"slug": "first", "multi_agent_reasoning_effort": "low"},
        {"slug": "second", "multi_agent_reasoning_effort": "high", "tool_mode": "direct"},
    ])
    dest = tmp_path / "models.json"
    write_model_catalog(dest, None, None, solo=False)
    first, second = json.loads(dest.read_text())["models"]
    assert first["tool_mode"] == "code_mode_only"
    assert first["multi_agent_reasoning_effort"] == "low"
    assert second["tool_mode"] == "direct"
    assert second["multi_agent_reasoning_effort"] == "high"


def test_effort_override_without_model_applies_to_all_candidates(tmp_path: Path, monkeypatch):
    _stub_models(monkeypatch, [{"slug": "first"}, {"slug": "second"}])
    dest = tmp_path / "models.json"
    write_model_catalog(dest, None, "medium", solo=False)
    assert all(model["multi_agent_reasoning_effort"] == "medium"
               for model in json.loads(dest.read_text())["models"])
