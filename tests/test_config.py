"""Configuration precedence and the options setup actually reads."""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from murmur.cli import resolve_options
from murmur.errors import MurmurError
from murmur.util import seconds


def namespace(**overrides):
    base = dict(
        config=None, brief=None, repo=None, base=None, peers=None, model=None,
        effort=None, cap=None, port_base=None, setup=None, setup_env=None,
        solo=False, setup_per_agent=False,
    )
    base.update(overrides)
    return argparse.Namespace(**base)


def test_config_then_flags(tmp_path: Path):
    brief = tmp_path / "brief.md"
    brief.write_text("from config\n")
    other = tmp_path / "other.md"
    other.write_text("from flag\n")
    config = tmp_path / "murmur.toml"
    config.write_text(
        'peers = 2\ncap = "45m"\nbrief = "brief.md"\n'
        'setup = ["echo from-config"]\nsetup_per_agent = true\n'
    )
    options = resolve_options(namespace(
        config=str(config), cap="30m", brief=str(other), setup=["echo from-flag"],
    ))
    assert options["peers"] == 2
    assert seconds(options["cap"]) == 30 * 60
    assert options["brief"] == str(other)
    assert options["setup"] == ["echo from-flag"]
    assert options["setup_per_agent"] is True


def test_config_brief_is_resolved_next_to_the_file(tmp_path: Path):
    nested = tmp_path / "cfg"
    nested.mkdir()
    (nested / "brief.md").write_text("x\n")
    config = nested / "murmur.toml"
    config.write_text('brief = "brief.md"\npeers = 3\n')
    options = resolve_options(namespace(config=str(config)))
    assert options["brief"] == str((nested / "brief.md").resolve())
    assert options["peers"] == 3
    assert options["model"] == "gpt-6-astra"


def test_string_setup_from_toml(tmp_path: Path):
    (tmp_path / "brief.md").write_text("x\n")
    config = tmp_path / "murmur.toml"
    config.write_text('brief = "brief.md"\nsetup = "echo hi"\n')
    with pytest.raises(MurmurError, match="setup must be a list"):
        resolve_options(namespace(config=str(config)))


def test_solo_flag_forces_one_peer(tmp_path: Path):
    (tmp_path / "brief.md").write_text("x\n")
    config = tmp_path / "murmur.toml"
    config.write_text('brief = "brief.md"\npeers = 4\n')
    options = resolve_options(namespace(config=str(config), solo=True))
    assert options["peers"] == 1
