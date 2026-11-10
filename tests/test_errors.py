"""Expected mistakes get one `murmur:` line and exit 3, never a Python traceback."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from murmur.cli import EXIT_LAUNCHER

from support import init_repo, run_cli, setup_workspace


def _launcher_error(result, message: str) -> None:
    assert result.returncode == EXIT_LAUNCHER, (result.returncode, result.stderr)
    assert "Traceback" not in result.stderr, result.stderr
    assert message in result.stderr, result.stderr


def _setup(tmp_path: Path, *extra: str, extra_env: dict | None = None):
    repo, brief = init_repo(tmp_path / "src")
    return run_cli("setup", str(brief), "--repo", str(repo), "--into", str(tmp_path / "runs"),
                   "--id", "run1", *extra, extra_env=extra_env)


def test_nonexistent_repo_inside_a_git_repo(tmp_path: Path):
    repo, brief = init_repo(tmp_path / "src")
    result = run_cli("setup", str(brief), "--repo", str(repo / "nosuch"),
                     "--into", str(tmp_path / "runs"))
    _launcher_error(result, f"{repo / 'nosuch'} does not exist")


def test_missing_brief_is_reported_before_any_slow_step(tmp_path: Path):
    repo, _brief = init_repo(tmp_path / "src")
    # The catalog step would fail too; the brief must be checked first.
    result = run_cli("setup", str(tmp_path / "nope.md"), "--repo", str(repo),
                     "--into", str(tmp_path / "runs"), extra_env={"MURMUR_FAKE_CODEX_MODELS": "fail"})
    _launcher_error(result, "brief not found")
    assert "catalog" not in result.stderr
    assert not (tmp_path / "runs").exists()


def test_failing_model_catalog_is_one_line_and_removes_the_workspace(tmp_path: Path):
    result = _setup(tmp_path, "--solo", extra_env={"MURMUR_FAKE_CODEX_MODELS": "fail"})
    _launcher_error(result, "`codex debug models` failed (5): error: simulated catalog failure")
    assert not (tmp_path / "runs" / "run1").exists()


def test_model_missing_from_the_catalog_fails_a_swarm(tmp_path: Path):
    result = _setup(tmp_path, "--peers", "2", "--model", "nosuchmodel")
    _launcher_error(result, "'nosuchmodel' is not in Codex's model catalog")
    assert not (tmp_path / "runs" / "run1").exists()


def test_unsupported_effort_fails(tmp_path: Path):
    _launcher_error(_setup(tmp_path, "--solo", "--effort", "hgih"), "does not support effort 'hgih'")


@pytest.mark.parametrize("run_id", ["../escaped", "a b", "x.lock", ".hidden", "a..b"])
def test_bad_workspace_id(tmp_path: Path, run_id: str):
    repo, brief = init_repo(tmp_path / "src")
    result = run_cli("setup", str(brief), "--repo", str(repo), "--into", str(tmp_path / "runs"),
                     "--id", run_id, "--solo")
    _launcher_error(result, "bad --id")
    assert not (tmp_path / "escaped").exists()


def test_into_is_a_file(tmp_path: Path):
    repo, brief = init_repo(tmp_path / "src")
    result = run_cli("setup", str(brief), "--repo", str(repo), "--into", str(brief), "--solo")
    _launcher_error(result, "is not a directory")


def test_unknown_config_key_end_to_end(tmp_path: Path):
    repo, brief = init_repo(tmp_path / "src")
    config = tmp_path / "murmur.toml"
    config.write_text(f'brief = "{brief}"\nrepo = "{repo}"\npeeers = 9\n')
    result = run_cli("setup", "--config", str(config), "--into", str(tmp_path / "runs"))
    _launcher_error(result, "unknown key 'peeers'")


def test_unparseable_user_codex_config(tmp_path: Path):
    codex_home = tmp_path / "home" / ".codex"
    codex_home.mkdir(parents=True, exist_ok=True)
    (codex_home / "config.toml").write_text("model_provider =\n")
    result = _setup(tmp_path, "--solo")
    _launcher_error(result, "cannot read Codex's config")
    assert not (tmp_path / "runs" / "run1").exists()


def test_missing_git(tmp_path: Path):
    only_codex = tmp_path / "bin"  # conftest puts just the fake codex here
    repo, brief = init_repo(tmp_path / "src")
    result = run_cli("setup", str(brief), "--repo", str(repo), extra_env={"PATH": str(only_codex)})
    _launcher_error(result, "the `git` CLI is not on PATH")


@pytest.mark.skipif(os.geteuid() == 0, reason="root can read any file")
def test_unreadable_file_in_a_plain_folder(tmp_path: Path):
    folder = tmp_path / "docs"
    folder.mkdir()
    (folder / "secret.txt").write_text("x\n")
    (folder / "secret.txt").chmod(0)
    brief = tmp_path / "brief.md"
    brief.write_text("Do the thing.\n")
    result = run_cli("setup", str(brief), "--repo", str(folder), "--into", str(tmp_path / "runs"),
                     "--id", "run1", "--solo")
    _launcher_error(result, "secret.txt")
    assert not (tmp_path / "runs" / "run1").exists()


def test_run_without_codex_on_path(tmp_path: Path):
    workspace = setup_workspace(tmp_path, "--solo")
    empty = tmp_path / "empty-bin"
    empty.mkdir()
    result = run_cli("run", str(workspace), extra_env={"PATH": str(empty)})
    _launcher_error(result, "the `codex` CLI is not on PATH")
    assert not (workspace / "logs" / "run.json").exists()
    assert not (workspace / "logs" / "run.lock").exists()


def test_run_with_a_foreign_murmur_json(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "murmur.json").write_text(json.dumps({"mode": "solo"}))
    result = run_cli("run", str(workspace))
    _launcher_error(result, "is not a murmur workspace file (missing peers, model")
