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
