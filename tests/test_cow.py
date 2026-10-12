"""Copy-on-write clones, the explicit fallback, and runtime ports."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import stat
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from murmur.cli import codex_command, shell_env
from murmur.cow import CowCopyError, cow_argv, cow_copy

from support import init_repo, run_cli


def test_cow_argv_never_uses_a_plain_copy(tmp_path: Path):
    argv = cow_argv(tmp_path / "src", tmp_path / "dst")
    assert argv[0] == "cp"
    assert "--reflink=always" in argv or "-c" in argv
    assert "-R" in argv


def test_failed_reflink_removes_the_partial_tree(tmp_path, monkeypatch):
    def fake_run(argv, **kwargs):
        dest = Path(argv[-1])
        dest.mkdir()
        (dest / "partial").write_text("x")
        return subprocess.CompletedProcess(argv, 1, "", "cp: failed to clone: Operation not supported")

    monkeypatch.setattr("murmur.cow.subprocess.run", fake_run)
    src = tmp_path / "src"
    src.mkdir()
    with pytest.raises(CowCopyError, match="failed to clone"):
        cow_copy(src, tmp_path / "dst")
    assert not (tmp_path / "dst").exists()


def _install_fake_cp(tmp_path: Path, monkeypatch, *, fail: bool) -> Path:
    real = shutil.which("cp")
    assert real
    log = tmp_path / "cp.log"
    bin_dir = tmp_path / "cpbin"
    bin_dir.mkdir()
    script = textwrap.dedent(
        f"""\
        #!/usr/bin/env python3
        import json, os, sys, shutil
        from pathlib import Path
        argv = sys.argv[1:]
        with open({str(log)!r}, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(sys.argv) + "\\n")
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


def _cow_invocations(log: Path) -> list[list[str]]:
    assert log.is_file(), "copy-on-write cp was not invoked"
    found = []
    for line in log.read_text().splitlines():
        argv = json.loads(line)
        if "--reflink=always" in argv or "-c" in argv:
            found.append(argv)
    return found


def _setup_script(tmp_path: Path) -> Path:
    script = tmp_path / "setup_log.py"
    script.write_text(textwrap.dedent(
        """\
        import os, time
        from pathlib import Path
        root = Path(os.environ["MURMUR_SETUP_LOG"])
        root.mkdir(parents=True, exist_ok=True)
        agent = os.environ.get("MURMUR_AGENT", "shared")
        port = os.environ.get("PORT_BASE", "")
        store = os.environ.get("npm_config_store_dir", "")
        start = time.time()
        time.sleep(0.4)
        end = time.time()
        (root / f"{agent}-{os.getpid()}").write_text(
            "|".join([agent, f"{start:.3f}", f"{end:.3f}", port, os.getcwd(), store]) + "\\n"
        )
        Path("from-setup.txt").write_text("from-setup\\n")
        Path("shim.txt").write_text(os.getcwd() + "\\n")
        os.system('git config --local core.hooksPath "$PWD/.githooks"')
        """
    ))
    return script


def _run_setup(tmp_path: Path, *extra: str, extra_env: dict | None = None):
    repo, brief = init_repo(tmp_path / "src")
    log = tmp_path / "setup-log"
    env = {"MURMUR_SETUP_LOG": str(log)}
    if extra_env:
        env.update(extra_env)
    script = _setup_script(tmp_path)
    result = run_cli(
        "setup", str(brief), "--repo", str(repo), "--into", str(tmp_path / "runs"),
        "--id", "run1", "--cap", "30s",
        "--setup", f"{sys.executable} {script}",
        *extra,
        extra_env=env,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    workspace = Path(result.stdout.strip().splitlines()[-1])
    return workspace, log


def test_mocked_cow_runs_setup_once_and_keeps_first_clone_paths(tmp_path, monkeypatch):
    monkeypatch.delenv("npm_config_store_dir", raising=False)
    log = _install_fake_cp(tmp_path, monkeypatch, fail=False)
    workspace, setup_log = _run_setup(tmp_path, "--peers", "2")
    meta = json.loads((workspace / "murmur.json").read_text())
    assert meta["clone_strategy"] == "cow"
    assert _cow_invocations(log)
    records = list(setup_log.iterdir())
    assert len(records) == 1
    _agent, _start, _end, port, cwd, store = records[0].read_text().strip().split("|")
    assert port == ""
    assert store == ""
    assert cwd == meta["agents"][0]["clone"]
    a1 = Path(meta["agents"][0]["clone"])
    a2 = Path(meta["agents"][1]["clone"])
    assert (a2 / "from-setup.txt").read_text() == "from-setup\n"
    # pnpm shims and similar files keep the first clone's absolute paths.
    assert (a2 / "shim.txt").read_text().strip() == str(a1)
    hooks = subprocess.check_output(
        ["git", "-C", str(a2), "config", "--get", "core.hooksPath"], text=True
    ).strip()
    assert hooks == str(a2 / ".githooks")
    name = subprocess.check_output(["git", "-C", str(a2), "config", "user.name"], text=True).strip()
    assert name == "a2"
    assert not (workspace / "pnpm-store").exists()
    assert not (workspace / "home").exists()
    assert "npm_config_store_dir" not in (a2 / ".murmur" / "env.sh").read_text()
    assert not (a2 / "COW_PARTIAL").exists()


def test_setup_keeps_the_user_pnpm_store(tmp_path, monkeypatch):
    _install_fake_cp(tmp_path, monkeypatch, fail=False)
    store = tmp_path / "global-pnpm-store"
    workspace, setup_log = _run_setup(
        tmp_path, "--peers", "2", extra_env={"npm_config_store_dir": str(store)}
    )
    seen = {path.read_text().strip().split("|")[-1] for path in setup_log.iterdir()}
    assert seen == {str(store)}
    meta = json.loads((workspace / "murmur.json").read_text())
    for agent in meta["agents"]:
        assert "npm_config_store_dir" not in (Path(agent["clone"]) / ".murmur" / "env.sh").read_text()
    assert not (workspace / "pnpm-store").exists()


def test_cow_failure_falls_back_to_parallel_setup(tmp_path, monkeypatch):
    log = _install_fake_cp(tmp_path, monkeypatch, fail=True)
    workspace, setup_log = _run_setup(tmp_path, "--peers", "3")
    meta = json.loads((workspace / "murmur.json").read_text())
    assert meta["clone_strategy"] == "parallel-fallback"
    invocations = _cow_invocations(log)
    assert invocations
    assert all("--reflink=always" in argv or "-c" in argv for argv in invocations)
    for agent in meta["agents"]:
        clone = Path(agent["clone"])
        assert not (clone / "COW_PARTIAL").exists()
        assert (clone / ".git").exists()

    def parsed(path: Path):
        agent, start, end, port, cwd, _store = path.read_text().strip().split("|")
        return agent, float(start), float(end), port, cwd

    records = [parsed(path) for path in setup_log.iterdir()]
    assert len(records) == 3
    first = Path(meta["agents"][0]["clone"])
    peers = [item for item in records if item[4] != str(first)]
    shared = [item for item in records if item[4] == str(first)]
    assert len(shared) == 1 and len(peers) == 2
    assert {item[3] for item in records} == {""}
    assert min(item[1] for item in peers) >= shared[0][2] - 0.05
    assert min(item[2] for item in peers) > max(item[1] for item in peers)


def test_setup_per_agent_skips_cow_and_sees_ports(tmp_path, monkeypatch):
    log = _install_fake_cp(tmp_path, monkeypatch, fail=False)
    workspace, setup_log = _run_setup(tmp_path, "--peers", "2", "--setup-per-agent")
    meta = json.loads((workspace / "murmur.json").read_text())
    assert meta["clone_strategy"] == "per-agent"
    assert not log.exists()
    ports = set()
    for path in setup_log.iterdir():
        agent, _start, _end, port, _cwd, _store = path.read_text().strip().split("|")
        ports.add((agent, port))
    assert ports == {("a1", "40000"), ("a2", "40100")}


def test_runtime_shell_exports_each_agents_port_without_moving_home(tmp_path, monkeypatch):
    _install_fake_cp(tmp_path, monkeypatch, fail=False)
    workspace, _log = _run_setup(tmp_path, "--peers", "2")
    meta = json.loads((workspace / "murmur.json").read_text())
    injected = shell_env(workspace)
    assert "HOME" not in injected
    assert "npm_config_store_dir" not in injected
    assert injected["ZDOTDIR"] == str(workspace / "zdot")
    command = " ".join(codex_command(workspace, meta, injected))
    assert '"HOME"' not in command
    assert "ZDOTDIR" in command
    home = os.environ["HOME"]
    startup = shlex.quote(str(workspace / "zdot" / ".zshenv"))
    for agent in meta["agents"]:
        clone = Path(agent["clone"])
        result = subprocess.run(
            ["sh", "-c", f'. {startup}; printf %s "$PORT_BASE"; printf " "; printf %s "$HOME"'],
            cwd=clone,
            env={"PATH": os.environ["PATH"], "HOME": home, "ZDOTDIR": injected["ZDOTDIR"]},
            capture_output=True, text=True, check=True,
        )
        port, seen_home = result.stdout.split(" ")
        assert port == agent["env"]["PORT_BASE"]
        assert seen_home == home
        assert seen_home != str(workspace / "home")
