"""Helpers shared by launcher tests."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def init_repo(path: Path) -> tuple[Path, Path]:
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(path)], check=True)
    git(path, "config", "user.email", "tester@example.com")
    git(path, "config", "user.name", "Tester")
    (path / "README.md").write_text("hello\n")
    git(path, "add", "README.md")
    git(path, "commit", "-q", "-m", "init")
    brief = path.parent / "brief.md"
    if not brief.exists():
        brief.write_text("Do the thing.\n")
    return path, brief


def run_cli(*args: str, extra_env: dict | None = None, timeout: float = 30) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, "-m", "murmur", *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def setup_workspace(tmp_path: Path, *extra: str, extra_env: dict | None = None) -> Path:
    repo, brief = init_repo(tmp_path / "src")
    into = tmp_path / "runs"
    result = run_cli(
        "setup", str(brief), "--repo", str(repo), "--into", str(into), "--id", "run1",
        "--cap", "30s", *extra,
        extra_env=extra_env,
    )
    assert result.returncode == 0, result.stderr
    workspace = Path(result.stdout.strip().splitlines()[-1])
    assert workspace.is_dir()
    return workspace
