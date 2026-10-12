"""Shell startup, setup environment, and git URL rewriting match the docs."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from murmur.cli import codex_command
from murmur.isolate import runtime_shell_env

from support import init_repo, run_cli, setup_workspace


def test_setup_environment_is_allowlisted(tmp_path: Path):
    repo, brief = init_repo(tmp_path / "src")
    script = tmp_path / "dump.py"
    script.write_text(
        "import os\nfrom pathlib import Path\n"
        "Path('env.txt').write_text(os.environ.get('SUPER_SECRET', '') + '\\n' +"
        "os.environ.get('PORT_BASE', '') + '\\n')\n"
    )
    secret = "hunter2"
    result = run_cli(
        "setup", str(brief), "--repo", str(repo), "--into", str(tmp_path / "runs"),
        "--id", "run1", "--peers", "2", "--cap", "30s",
        "--setup", f"{sys.executable} {script}",
        extra_env={"SUPER_SECRET": secret},
    )
    assert result.returncode == 0, result.stderr
    workspace = Path(result.stdout.strip().splitlines()[-1])
    meta = json.loads((workspace / "murmur.json").read_text())
    for agent in meta["agents"]:
        dumped = (Path(agent["clone"]) / "env.txt").read_text().splitlines()
        assert dumped[0] == ""
        assert dumped[1] == ""
        assert (workspace / "pnpm-store").is_dir()
        assert str(workspace / "pnpm-store") == agent["env"]["npm_config_store_dir"]


def test_setup_env_opt_in_and_outside_pnpm_store(tmp_path: Path):
    repo, brief = init_repo(tmp_path / "src")
    outside = tmp_path / "global-pnpm"
    (repo / ".npmrc").write_text(f"store-dir={outside}\n")
    subprocess.run(["git", "-C", str(repo), "add", ".npmrc"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "npmrc"], check=True)
    script = tmp_path / "dump.py"
    script.write_text(
        "import os\nfrom pathlib import Path\n"
        "Path('env.txt').write_text(os.environ.get('SUPER_SECRET', '') + '\\n' +"
        "os.environ.get('npm_config_store_dir', '') + '\\n')\n"
    )
    result = run_cli(
        "setup", str(brief), "--repo", str(repo), "--into", str(tmp_path / "runs"),
        "--id", "run1", "--solo", "--cap", "30s",
        "--setup-env", "SUPER_SECRET",
        "--setup", f"{sys.executable} {script}",
        extra_env={"SUPER_SECRET": "opt-in"},
    )
    assert result.returncode == 0, result.stderr
    workspace = Path(result.stdout.strip().splitlines()[-1])
    clone = Path(json.loads((workspace / "murmur.json").read_text())["agents"][0]["clone"])
    secret, store = (clone / "env.txt").read_text().splitlines()
    assert secret == "opt-in"
    assert store == str(workspace / "pnpm-store")
    assert not outside.exists()


def test_in_workspace_pnpm_store_is_kept(tmp_path: Path):
    repo, brief = init_repo(tmp_path / "src")
    (repo / ".npmrc").write_text("store-dir=.pnpm-store\n")
    subprocess.run(["git", "-C", str(repo), "add", ".npmrc"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "npmrc"], check=True)
    script = tmp_path / "dump.py"
    script.write_text(
        "import os\nfrom pathlib import Path\n"
        "Path('env.txt').write_text(os.environ.get('npm_config_store_dir', 'unset') + '\\n')\n"
    )
    result = run_cli(
        "setup", str(brief), "--repo", str(repo), "--into", str(tmp_path / "runs"),
        "--id", "run1", "--solo", "--cap", "30s",
        "--setup", f"{sys.executable} {script}",
    )
    assert result.returncode == 0, result.stderr
    workspace = Path(result.stdout.strip().splitlines()[-1])
    clone = Path(json.loads((workspace / "murmur.json").read_text())["agents"][0]["clone"])
    assert (clone / "env.txt").read_text().strip() == "unset"


def test_runtime_shell_exports_each_agents_port(tmp_path: Path):
    workspace = setup_workspace(tmp_path, "--peers", "2")
    meta = json.loads((workspace / "murmur.json").read_text())
    leaked_home = Path(os.environ["HOME"])
    (leaked_home / ".bashrc").write_text("export LEAKED_FROM_HOME=1\n")
    (leaked_home / ".bash_profile").write_text("export LEAKED_FROM_HOME=1\n")
    shell_env = runtime_shell_env(workspace)
    ports = []
    for agent in meta["agents"]:
        clone = Path(agent["clone"])
        env = dict(shell_env)
        for flag in (["bash", "-lc"], ["bash", "-c"]):
            out = subprocess.check_output(
                [*flag, 'printf %s "$PORT_BASE"; printf " "; printf %s "$LEAKED_FROM_HOME"'],
                cwd=clone, env=env, text=True,
            )
            port, _, leaked = out.partition(" ")
            assert leaked == ""
            assert port == agent["env"]["PORT_BASE"]
        wrapped = subprocess.check_output(
            [str(workspace / "bin" / "murmur-sh"), "bash", "-c", 'printf %s "$PORT_BASE"'],
            cwd=clone, env={"PATH": os.environ["PATH"], "HOME": str(leaked_home)}, text=True,
        )
        ports.append(wrapped.strip())
    assert ports == ["40000", "40100"]
    zsh = shutil_which("zsh")
    if zsh:
        clone = Path(meta["agents"][1]["clone"])
        out = subprocess.check_output(
            [zsh, "-lc", 'printf %s "$PORT_BASE"'], cwd=clone, env=shell_env, text=True,
        )
        assert out.strip() == "40100"


def shutil_which(name: str) -> str | None:
    from shutil import which
    return which(name)


def test_codex_command_sets_shell_policy_and_keeps_network(tmp_path: Path):
    workspace = setup_workspace(tmp_path, "--solo")
    meta = json.loads((workspace / "murmur.json").read_text())
    cmd = codex_command(workspace, meta, workspace / "logs" / "final.md")
    joined = "\n".join(cmd)
    assert 'shell_environment_policy.inherit="core"' in cmd
    assert "shell_environment_policy.ignore_default_excludes=false" in cmd
    assert "shell_environment_policy.experimental_use_profile=false" in cmd
    assert "sandbox_workspace_write.network_access=true" in cmd
    assert str(workspace / "home") in joined
    assert "ZDOTDIR" in joined
    assert "BASH_ENV" in joined


def test_github_git_urls_are_rewritten_locally(tmp_path: Path):
    workspace = setup_workspace(tmp_path, "--solo")
    gitconfig = workspace / "gitconfig"
    env = {
        "PATH": os.environ["PATH"],
        "HOME": os.environ["HOME"],
        "GIT_CONFIG_GLOBAL": str(gitconfig),
        "GIT_CONFIG_NOSYSTEM": "1",
    }
    result = subprocess.run(
        ["git", "ls-remote", "https://github.com/org/repo.git", "HEAD"],
        capture_output=True, text=True, env=env,
    )
    assert result.returncode != 0
    assert "github-is-blocked" in result.stderr
    local = subprocess.run(
        ["git", "-C", str(workspace / "work" / "origin.git"), "rev-parse", "main"],
        capture_output=True, text=True, env=env,
    )
    assert local.returncode == 0
