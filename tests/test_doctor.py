"""`murmur doctor` and the preflight `murmur run` makes before it starts Codex."""

from __future__ import annotations

import builtins
import json
import os
from pathlib import Path

import pytest

from murmur import doctor
from murmur.cli import EXIT_LAUNCHER
from murmur.cow import CowCopyError

from support import git, init_repo, run_cli, setup_workspace


def _lines(output: str) -> dict[str, str]:
    """Check name -> status, from the report."""
    found = {}
    for line in output.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0] in ("ok", "warn", "fail", "skip"):
            found[parts[1]] = parts[0]
    return found


def _doctor(tmp_path: Path, *extra: str, extra_env: dict | None = None):
    repo, _brief = init_repo(tmp_path / "src")
    return run_cli("doctor", "--repo", str(repo), "--into", str(tmp_path / "runs"), *extra,
                   extra_env=extra_env)


def test_doctor_passes_with_a_working_setup(tmp_path: Path):
    result = _doctor(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    statuses = _lines(result.stdout)
    for name in ("codex", "model", "features", "git", "auth"):
        assert statuses[name] == "ok", result.stdout
    # These depend on the test machine's disk; neither is a failure.
    assert statuses["reflink"] in ("ok", "warn") and statuses["disk"] in ("ok", "warn")
    assert "codex-cli 0.163.0" in result.stdout
    assert "gpt-6-astra is in `codex debug models`" in result.stdout
    assert "0 failed" in result.stdout
    assert not (tmp_path / "runs").exists()


def test_doctor_fails_on_old_codex(tmp_path: Path):
    result = _doctor(tmp_path, extra_env={"MURMUR_FAKE_CODEX_VERSION": "0.150.2"})
    assert result.returncode == 1
    assert _lines(result.stdout)["codex"] == "fail"
    assert "codex-cli 0.150.2 is older than 0.162.0" in result.stdout
    assert "fix: upgrade to Codex CLI 0.162.0 or later" in result.stdout


def test_doctor_fails_on_unknown_model_and_lists_the_catalog(tmp_path: Path):
    result = _doctor(tmp_path, "--model", "nosuchmodel")
    assert result.returncode == 1
    assert _lines(result.stdout)["model"] == "fail"
    assert "nosuchmodel is not in `codex debug models` (it has: gpt-6-astra)" in result.stdout
    assert "fix: pick a slug from `codex debug models`" in result.stdout


def test_doctor_reads_the_model_from_config(tmp_path: Path):
    config = tmp_path / "murmur.toml"
    config.write_text('model = "from-config"\n')
    result = _doctor(tmp_path, "--config", str(config))
    assert result.returncode == 1
    assert "from-config is not in `codex debug models`" in result.stdout


def test_doctor_fails_without_swarm_features_unless_solo(tmp_path: Path):
    env = {"MURMUR_FAKE_CODEX_NO_FEATURES": "1"}
    result = _doctor(tmp_path, extra_env=env)
    assert result.returncode == 1
    assert _lines(result.stdout)["features"] == "fail"
    assert "lacks agent_message_board, multi_agent_v2" in result.stdout
    solo = run_cli("doctor", "--repo", str(tmp_path / "src"), "--into", str(tmp_path / "runs"),
                   "--solo", extra_env=env)
    assert solo.returncode == 0, solo.stdout
    assert "features" not in _lines(solo.stdout)


def test_doctor_fails_on_missing_repo(tmp_path: Path):
    result = run_cli("doctor", "--repo", str(tmp_path / "nope"), "--into", str(tmp_path / "runs"))
    assert result.returncode == 1
    assert _lines(result.stdout)["git"] == "fail"
    assert "is not a directory" in result.stdout


def test_doctor_fails_without_auth(tmp_path: Path):
    (Path(os.environ["HOME"]) / ".codex" / "auth.json").unlink()
    result = _doctor(tmp_path, extra_env={"CODEX_API_KEY": "", "OPENAI_API_KEY": ""})
    assert result.returncode == 1
    assert _lines(result.stdout)["auth"] == "fail"
    assert "fix: run `codex login`" in result.stdout


# Individual checks


def test_codex_missing_from_path(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    check = doctor.check_codex()
    assert check.status == "fail"
    assert "not on PATH" in check.detail and "install Codex CLI" in check.hint
    statuses = {c.name: c.status for c in doctor.run_checks(
        model="m", repo=tmp_path, into=tmp_path, codex_home=tmp_path, solo=False)}
    assert statuses["model"] == statuses["features"] == "skip"


def test_git_plain_folder_empty_repo_and_broken_git(tmp_path: Path):
    folder = tmp_path / "folder"
    folder.mkdir()
    check = doctor.check_git(folder)
    assert check.status == "ok" and "plain folder" in check.detail

    empty = tmp_path / "empty"
    empty.mkdir()
    git(empty, "init", "-q")
    check = doctor.check_git(empty)
    assert check.status == "fail" and "has no commits" in check.detail

    broken = tmp_path / "broken"
    broken.mkdir()
    (broken / ".git").write_text("gitdir: /nonexistent\n")
    check = doctor.check_git(broken)
    assert check.status == "fail" and "not a usable git repository" in check.detail


def test_reflink_ok_and_fallback_warning_clean_up(tmp_path: Path, monkeypatch):
    base = tmp_path / "fs"
    base.mkdir()
    into = base / "runs" / "deeper"
    monkeypatch.setattr(doctor, "cow_copy", lambda src, dst: None)
    assert doctor.check_reflink(into).status == "ok"

    def refuse(src, dst):
        raise CowCopyError(f"cp: failed to clone '{dst}' from '{src}': Operation not supported")

    monkeypatch.setattr(doctor, "cow_copy", refuse)
    check = doctor.check_reflink(into)
    assert check.status == "warn"
    assert check.detail == f"{base} does not support copy-on-write copies (Operation not supported)"
    assert "running --setup in every clone in parallel" in check.hint
    assert list(base.iterdir()) == []
    assert not into.exists()


def test_reflink_real_probe_reports_ok_or_warn(tmp_path: Path):
    base = tmp_path / "fs"
    base.mkdir()
    assert doctor.check_reflink(base).status in ("ok", "warn")
    assert list(base.iterdir()) == []


@pytest.mark.skipif(os.geteuid() == 0, reason="root can write anywhere")
def test_unwritable_into_fails(tmp_path: Path):
    locked = tmp_path / "locked"
    locked.mkdir()
    locked.chmod(0o500)
    try:
        check = doctor.check_reflink(locked / "runs")
    finally:
        locked.chmod(0o700)
    assert check.status == "fail" and "not writable" in check.detail


def test_low_disk_warns(tmp_path: Path, monkeypatch):
    usage = type("Usage", (), {"free": 100 * 1024**2})
    monkeypatch.setattr(doctor.shutil, "disk_usage", lambda path: usage)
    check = doctor.check_disk(tmp_path)
    assert check.status == "warn" and "0.1 GB free" in check.detail


def _home(tmp_path: Path, config: str = "", auth: bool = False) -> Path:
    home = tmp_path / "codex-home"
    home.mkdir(parents=True)
    if config:
        (home / "config.toml").write_text(config)
    if auth:
        (home / "auth.json").write_text('{"secret": "do-not-read"}\n')
    return home


@pytest.fixture
def no_key_env(monkeypatch):
    for name in doctor.API_KEY_VARS:
        monkeypatch.delenv(name, raising=False)


def test_auth_checks_existence_without_reading_auth_json(tmp_path: Path, monkeypatch, no_key_env):
    home = _home(tmp_path, auth=True)
    real_open = builtins.open

    def guarded_open(file, *args, **kwargs):
        assert Path(file).name != "auth.json", "auth.json must not be opened"
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", guarded_open)
    monkeypatch.setattr(Path, "open", lambda self, *a, **k: guarded_open(self, *a, **k))
    check = doctor.check_auth(home)
    assert check.status == "ok"
    assert "do-not-read" not in check.detail + check.hint


def test_auth_missing(tmp_path: Path, no_key_env):
    check = doctor.check_auth(_home(tmp_path))
    assert check.status == "fail" and check.hint == "run `codex login`"


def test_auth_from_api_key_variable_never_shows_the_value(tmp_path: Path, monkeypatch, no_key_env):
    monkeypatch.setenv("CODEX_API_KEY", "sk-secret-value")
    check = doctor.check_auth(_home(tmp_path))
    assert check.status == "ok" and check.detail == "$CODEX_API_KEY is set"


def test_auth_custom_provider_env_key(tmp_path: Path, monkeypatch, no_key_env):
    home = _home(tmp_path, config=(
        'model_provider = "corp"\n[model_providers.corp]\nbase_url = "https://x"\nenv_key = "CORP_KEY"\n'))
    monkeypatch.delenv("CORP_KEY", raising=False)
    check = doctor.check_auth(home)
    assert check.status == "fail" and check.hint == "export CORP_KEY before running murmur"
    monkeypatch.setenv("CORP_KEY", "secret-value")
    check = doctor.check_auth(home)
    assert check.status == "ok" and "secret-value" not in check.detail


def test_auth_custom_provider_without_openai_auth(tmp_path: Path, no_key_env):
    home = _home(tmp_path, config=(
        'model_provider = "corp"\n[model_providers.corp]\nrequires_openai_auth = false\n'))
    assert doctor.check_auth(home).status == "ok"
    home = _home(tmp_path / "builtin", config='model_provider = "ollama"\n')
    assert doctor.check_auth(home).status == "warn"


# The preflight at the start of `murmur run`


def test_run_fails_fast_on_old_codex(tmp_path: Path):
    workspace = setup_workspace(tmp_path, "--solo")
    result = run_cli("run", str(workspace), extra_env={"MURMUR_FAKE_CODEX_VERSION": "0.100.0"})
    assert result.returncode == EXIT_LAUNCHER
    assert "murmur: codex: codex-cli 0.100.0 is older than 0.162.0" in result.stderr
    assert "`murmur doctor` runs every check" in result.stderr
    assert not (workspace / "logs" / "run.json").exists()
    assert not (workspace / "logs" / "session.jsonl").exists()
    # Nothing was recorded, so the same workspace runs once Codex is fixed.
    again = run_cli("run", str(workspace), extra_env={"MURMUR_FAKE_CODEX_MODE": "commit"})
    assert again.returncode == 0, again.stderr


def test_run_fails_fast_without_auth(tmp_path: Path):
    workspace = setup_workspace(tmp_path, "--solo")
    (Path(os.environ["HOME"]) / ".codex" / "auth.json").unlink()
    result = run_cli("run", str(workspace), extra_env={"CODEX_API_KEY": "", "OPENAI_API_KEY": ""})
    assert result.returncode == EXIT_LAUNCHER
    assert "murmur: auth: no Codex login" in result.stderr
    assert "fix: run `codex login`" in result.stderr
    assert not (workspace / "logs" / "run.json").exists()


def test_run_preflight_uses_the_workspace_provider(tmp_path: Path):
    codex_home = Path(os.environ["HOME"]) / ".codex"
    (codex_home / "auth.json").unlink()
    (codex_home / "config.toml").write_text(
        'model_provider = "corp"\n[model_providers.corp]\nbase_url = "http://localhost:1"\n'
        'env_key = "CORP_KEY"\n')
    workspace = setup_workspace(tmp_path, "--solo")
    env = {"CODEX_API_KEY": "", "OPENAI_API_KEY": ""}
    result = run_cli("run", str(workspace), extra_env=env)
    assert result.returncode == EXIT_LAUNCHER
    assert "provider corp needs $CORP_KEY" in result.stderr
    result = run_cli("run", str(workspace), extra_env={**env, "CORP_KEY": "x",
                                                         "MURMUR_FAKE_CODEX_MODE": "commit"})
    assert result.returncode == 0, result.stderr
    assert json.loads((workspace / "logs" / "run.json").read_text())["exit_code"] == 0
