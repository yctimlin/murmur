"""Copy-on-write clones, the explicit fallback, and per-agent setup."""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from murmur.cow import CowCopyError, cow_argv, cow_copy

from support import init_repo, run_cli


def test_cow_argv_never_uses_a_plain_copy(tmp_path: Path):
    src, dst = tmp_path / "src", tmp_path / "dst"
    argv = cow_argv(src, dst)
    assert argv[0] == "cp"
    assert "--reflink=always" in argv or "-c" in argv
    assert argv[-2:] == [str(src), str(dst)]


def test_failed_reflink_removes_the_partial_tree(tmp_path, monkeypatch):
    calls = []

    def fake_run(argv, **kwargs):
        calls.append(argv)
        dest = Path(argv[-1])
        dest.mkdir()
        (dest / "partial").mkdir()
        return subprocess.CompletedProcess(argv, 1, "", "cp: failed to clone: Operation not supported")

    monkeypatch.setattr("murmur.cow.subprocess.run", fake_run)
    src = tmp_path / "src"
    src.mkdir()
    (src / "file").write_text("x")
    with pytest.raises(CowCopyError, match="failed to clone"):
        cow_copy(src, tmp_path / "dst")
    assert not (tmp_path / "dst").exists()
    assert len(calls) == 1
    assert "--reflink=always" in calls[0] or "-c" in calls[0]


def test_real_cow_copy_succeeds_or_fails_explicitly(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "file").write_text("hello")
    dst = tmp_path / "dst"
    try:
        cow_copy(src, dst)
    except CowCopyError:
        assert not dst.exists()
    else:
        assert (dst / "file").read_text() == "hello"


def _install_fake_cp(tmp_path: Path, monkeypatch, *, fail: bool) -> Path:
    real = shutil.which("cp")
    assert real
    log = tmp_path / "cp.log"
    bin_dir = tmp_path / "cpbin"
    bin_dir.mkdir()
    script = textwrap.dedent(
        f"""\
        #!/usr/bin/env python3
        import os, sys, shutil
        from pathlib import Path
        argv = sys.argv[1:]
        with open({str(log)!r}, "a", encoding="utf-8") as handle:
            handle.write(" ".join(sys.argv) + "\\n")
        cow = "--reflink=always" in argv or "-c" in argv
        if cow:
            if {str(fail)}:
                dest = Path(argv[-1])
                dest.mkdir(parents=True, exist_ok=True)
                (dest / "COW_PARTIAL").write_text("partial")
                sys.stderr.write("cp: failed to clone: Operation not supported\\n")
                raise SystemExit(1)
            shutil.copytree(argv[-2], argv[-1], symlinks=True)
            raise SystemExit(0)
        os.execv({real!r}, [{real!r}, *argv])
        """
    )
    path = bin_dir / "cp"
    path.write_text(script)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", str(bin_dir) + os.pathsep + os.environ["PATH"])
    return log


def _setup_log_script(tmp_path: Path) -> Path:
    script = tmp_path / "setup_log.py"
    script.write_text(textwrap.dedent(
        """\
        import os, time
        from pathlib import Path
        root = Path(os.environ["MURMUR_SETUP_LOG"])
        root.mkdir(parents=True, exist_ok=True)
        agent = os.environ.get("MURMUR_AGENT", "shared")
        port = os.environ.get("PORT_BASE", "")
        start = time.time()
        time.sleep(0.4)
        end = time.time()
        (root / f"{agent}-{os.getpid()}").write_text(
            "|".join([agent, f"{start:.3f}", f"{end:.3f}", port, os.getcwd()]) + "\\n"
        )
        Path("from-setup.txt").write_text("from-setup\\n")
        os.system('git config --local core.hooksPath "$PWD/.githooks"')
        """
    ))
    return script


def _run_setup(tmp_path: Path, *extra: str, extra_env: dict | None = None):
    repo, brief = init_repo(tmp_path / "src")
    config = tmp_path / "murmur.toml"
    config.write_text('setup_env = ["MURMUR_SETUP_LOG"]\n')
    log = tmp_path / "setup-log"
    env = {"MURMUR_SETUP_LOG": str(log)}
    if extra_env:
        env.update(extra_env)
    result = run_cli(
        "setup", str(brief), "--repo", str(repo), "--into", str(tmp_path / "runs"),
        "--id", "run1", "--cap", "30s", "--config", str(config),
        "--setup", f"{sys.executable} {script_of(tmp_path)}",
        *extra,
        extra_env=env,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    workspace = Path(result.stdout.strip().splitlines()[-1])
    return workspace, log


def script_of(tmp_path: Path) -> Path:
    path = tmp_path / "setup_log.py"
    if not path.exists():
        _setup_log_script(tmp_path)
    return path


def test_mocked_cow_runs_setup_once_and_rewrites_identity(tmp_path, monkeypatch):
    log = _install_fake_cp(tmp_path, monkeypatch, fail=False)
    script_of(tmp_path)
    workspace, setup_log = _run_setup(tmp_path, "--peers", "2")
    meta = json.loads((workspace / "murmur.json").read_text())
    assert meta["clone_strategy"] == "cow"
    records = list(setup_log.iterdir())
    assert len(records) == 1
    agent, _start, _end, port, cwd = records[0].read_text().strip().split("|")
    assert agent == "shared"
    assert port == ""
    assert cwd == meta["agents"][0]["clone"]
    cp_log = log.read_text()
    assert "--reflink=always" in cp_log or " -c " in cp_log
    a2 = Path(meta["agents"][1]["clone"])
    assert (a2 / "from-setup.txt").read_text() == "from-setup\n"
    assert "COW_PARTIAL" not in cp_log
    name = subprocess.check_output(["git", "-C", str(a2), "config", "user.name"], text=True).strip()
    assert name == "a2"
    hooks = subprocess.check_output(
        ["git", "-C", str(a2), "config", "--get", "core.hooksPath"], text=True
    ).strip()
    assert hooks == str(a2 / ".githooks")
    assert str(Path(meta["agents"][0]["clone"])) not in hooks
    status = subprocess.run(["git", "-C", str(a2), "status", "--porcelain"], capture_output=True, text=True)
    assert status.returncode == 0
    assert ".murmur" not in status.stdout


def test_cow_failure_falls_back_to_parallel_setup(tmp_path, monkeypatch):
    log = _install_fake_cp(tmp_path, monkeypatch, fail=True)
    script_of(tmp_path)
    workspace, setup_log = _run_setup(tmp_path, "--peers", "3")
    meta = json.loads((workspace / "murmur.json").read_text())
    assert meta["clone_strategy"] == "parallel-fallback"
    cp_log = log.read_text()
    assert "--reflink=always" in cp_log or "\ncp -c " in "\n" + cp_log
    assert "COW_PARTIAL" not in "".join(path.read_text() for path in setup_log.iterdir())
    for agent in meta["agents"]:
        clone = Path(agent["clone"])
        assert not (clone / "COW_PARTIAL").exists()
        assert (clone / ".git").exists()
    def parsed(path: Path):
        agent, start, end, port, cwd = path.read_text().strip().split("|")
        return agent, float(start), float(end), port, cwd

    records = [parsed(path) for path in setup_log.iterdir()]
    assert len(records) == 3
    first = Path(meta["agents"][0]["clone"])
    shared = [item for item in records if item[4] == str(first)]
    peers = [item for item in records if item[4] != str(first)]
    assert len(shared) == 1
    assert len(peers) == 2
    assert {item[3] for item in records} == {""}
    assert {item[4] for item in records} == {agent["clone"] for agent in meta["agents"]}
    assert min(item[1] for item in peers) >= shared[0][2] - 0.05
    assert min(item[2] for item in peers) > max(item[1] for item in peers)


def test_setup_per_agent_skips_cow_and_sees_ports(tmp_path, monkeypatch):
    log = _install_fake_cp(tmp_path, monkeypatch, fail=False)
    script_of(tmp_path)
    workspace, setup_log = _run_setup(tmp_path, "--peers", "2", "--setup-per-agent")
    meta = json.loads((workspace / "murmur.json").read_text())
    assert meta["clone_strategy"] == "per-agent"
    assert meta["setup_per_agent"] is True
    assert not log.exists()
    ports = set()
    for path in setup_log.iterdir():
        agent, _start, _end, port, _cwd = path.read_text().strip().split("|")
        ports.add((agent, port))
    assert ports == {("a1", "40000"), ("a2", "40100")}
