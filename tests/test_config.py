"""Config file precedence."""

from __future__ import annotations

from pathlib import Path

from murmur.cli import resolve_options


def _args(**overrides):
    values = dict(
        brief=None, config=None, repo=None, base=None, peers=None, solo=False,
        model=None, effort=None, cap=None, port_base=None, setup=None,
        setup_per_agent=False, id=None, into="~/.murmur/runs",
    )
    values.update(overrides)
    return type("Args", (), values)()


def test_config_then_flags(tmp_path: Path):
    config = tmp_path / "murmur.toml"
    config.write_text(
        'peers = 3\ncap = "90m"\nsetup = ["echo from-config"]\n'
        "setup_per_agent = true\n"
        'agent_env = { APP_PORT = "$port_base" }\n'
    )
    options = resolve_options(_args(config=str(config), peers=2, brief=str(tmp_path / "brief.md")))
    assert options["peers"] == 2
    assert options["cap"] == "90m"
    assert options["setup"] == ["echo from-config"]
    assert options["setup_per_agent"] is True
    assert options["agent_env"]["APP_PORT"] == "$port_base"


def test_string_setup_is_rejected(tmp_path: Path):
    config = tmp_path / "murmur.toml"
    config.write_text('setup = "echo no"\nbrief = "brief.md"\n')
    try:
        resolve_options(_args(config=str(config)))
    except SystemExit as exc:
        assert exc.code == 3
    else:
        raise AssertionError("expected setup to be rejected")


def test_two_peers_by_default_and_explicit_counts_are_preserved(tmp_path: Path):
    brief = str(tmp_path / "brief.md")
    assert resolve_options(_args(brief=brief))["peers"] == 2
    assert resolve_options(_args(brief=brief, peers=6))["peers"] == 6
    assert resolve_options(_args(brief=brief, solo=True))["peers"] == 1


def test_model_defaults_are_left_to_codex(tmp_path: Path):
    from murmur.cli import codex_command

    options = resolve_options(_args(brief="brief.md"))
    assert options["model"] is None
    assert options["effort"] is None
    cmd = codex_command(tmp_path, {**options, "mode": "solo"}, {})
    assert "-m" not in cmd
    assert not any(arg.startswith("model_reasoning_effort=") for arg in cmd)
    assert not any("compact" in arg for arg in cmd)


def test_user_model_preferences_then_config_then_flags(tmp_path: Path, monkeypatch):
    from murmur.cli import codex_command

    home = tmp_path / "user-codex"
    home.mkdir()
    (home / "config.toml").write_text('model = "user-model"\nmodel_reasoning_effort = "low"\n')
    monkeypatch.setenv("CODEX_HOME", str(home))
    inherited = resolve_options(_args(brief="brief.md"))
    assert (inherited["model"], inherited["effort"]) == ("user-model", "low")
    config = tmp_path / "murmur.toml"
    config.write_text('model = "config-model"\neffort = "medium"\n')
    selected = resolve_options(_args(brief="brief.md", config=str(config), effort="high"))
    assert (selected["model"], selected["effort"]) == ("config-model", "high")
    cmd = codex_command(tmp_path, {**selected, "mode": "solo"}, {})
    assert cmd[cmd.index("-m") + 1] == "config-model"
    assert 'model_reasoning_effort="high"' in cmd


def test_invalid_model_preference_is_rejected(tmp_path: Path):
    import pytest

    with pytest.raises(SystemExit) as error:
        resolve_options(_args(brief="brief.md", model=""))
    assert error.value.code == 3


def test_setup_freezes_explicit_user_model_settings(tmp_path: Path, monkeypatch):
    import json
    from murmur.cli import codex_command
    from support import setup_workspace

    home = tmp_path / "user-codex"
    home.mkdir()
    config = home / "config.toml"
    config.write_text('model = "user-model"\nmodel_reasoning_effort = "low"\n')
    monkeypatch.setenv("CODEX_HOME", str(home))
    ws = setup_workspace(tmp_path, "--solo")
    config.write_text('model = "changed-after-setup"\n')
    meta = json.loads((ws / "murmur.json").read_text())
    cmd = codex_command(ws, meta, {})
    assert cmd[cmd.index("-m") + 1] == "user-model"
    assert 'model_reasoning_effort="low"' in cmd
