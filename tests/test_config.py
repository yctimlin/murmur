"""Config file precedence."""

from __future__ import annotations

from pathlib import Path

import pytest

from murmur.cli import EXIT_LAUNCHER, resolve_options


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


def _rejected(capsys, **overrides) -> str:
    with pytest.raises(SystemExit) as exc:
        resolve_options(_args(**overrides))
    assert exc.value.code == EXIT_LAUNCHER
    return capsys.readouterr().err


def _config(tmp_path: Path, text: str) -> str:
    config = tmp_path / "murmur.toml"
    config.write_text('brief = "brief.md"\n' + text)
    return str(config)


def test_unknown_config_key_is_rejected_with_a_suggestion(tmp_path: Path, capsys):
    err = _rejected(capsys, config=_config(tmp_path, "peeers = 9\n"))
    assert "unknown key 'peeers'" in err and "did you mean 'peers'?" in err


def test_unknown_config_key_lists_known_keys(tmp_path: Path, capsys):
    err = _rejected(capsys, config=_config(tmp_path, "zzz = 1\n"))
    assert "unknown key 'zzz'" in err and "agent_env" in err and "port_base" in err


def test_missing_and_malformed_config_files_are_launcher_errors(tmp_path: Path, capsys):
    assert "cannot read config" in _rejected(capsys, config=str(tmp_path / "nope.toml"))
    assert "is not valid TOML" in _rejected(capsys, config=_config(tmp_path, "peers =\n"))


def test_config_paths_must_be_strings(tmp_path: Path, capsys):
    config = tmp_path / "murmur.toml"
    config.write_text("brief = 3\n")
    assert "brief in" in _rejected(capsys, config=str(config))


@pytest.mark.parametrize(("overrides", "message"), [
    ({"cap": "0m"}, "cap must be longer than 0"),
    ({"cap": "soon"}, "bad duration"),
    ({"peers": 17}, "at most 16 peers"),
    ({"peers": 1}, "at least 2 peers"),
    ({"port_base": 65500}, "past 65535"),
    ({"port_base": 0}, "port_base must be an integer from 1 to 65535"),
    ({"port_base": 70000}, "port_base must be an integer from 1 to 65535"),
    ({"model": " "}, "model must be a non-empty string"),
    ({"effort": ""}, "effort must be a non-empty string"),
    ({"max_file_mb": 0.0}, "max_file_mb must be a number greater than 0"),
])
def test_out_of_range_flags_are_rejected(tmp_path: Path, capsys, overrides, message):
    err = _rejected(capsys, brief=str(tmp_path / "brief.md"), **overrides)
    assert message in err


def test_last_port_may_reach_65535(tmp_path: Path):
    # 4 peers x 100 ports from 65136 end exactly at 65535.
    options = resolve_options(_args(brief=str(tmp_path / "brief.md"), port_base=65136))
    assert options["port_base"] == 65136


@pytest.mark.parametrize(("text", "message"), [
    ("port_stride = 0\n", "port_stride must be a positive integer"),
    ('max_file_mb = "big"\n', "max_file_mb must be a number greater than 0"),
    ("model = 3\n", "model must be a non-empty string"),
    ('agent_env = { DB = "db_$nope" }\n', "agent_env DB: unknown placeholder $nope"),
    ('agent_env = { DB = "cost $" }\n', "write $$ for a literal $"),
    ('agent_env = { "BAD-NAME" = "x" }\n', "invalid environment variable name 'BAD-NAME'"),
    ("agent_env = { DB = 3 }\n", "agent_env DB: the value must be a string"),
])
def test_bad_config_values_are_rejected(tmp_path: Path, capsys, text, message):
    assert message in _rejected(capsys, config=_config(tmp_path, text))


def test_agent_env_templates_with_known_placeholders_pass(tmp_path: Path):
    text = 'agent_env = { DB = "db_${agent}_$index", PRICE = "$$5", PORT = "$port_base", R = "$run" }\n'
    options = resolve_options(_args(config=_config(tmp_path, text)))
    assert options["agent_env"]["PRICE"] == "$$5"
