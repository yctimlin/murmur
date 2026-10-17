from __future__ import annotations

import json
from pathlib import Path

from support import init_repo, run_cli


def test_one_peer_protocol_switch_builds_swarm_workspace(tmp_path: Path):
    repo, brief = init_repo(tmp_path / "src")
    result = run_cli(
        "setup", str(brief), "--repo", str(repo), "--into", str(tmp_path / "runs"),
        "--id", "run1", "--solo", "--cap", "30s",
        extra_env={"MURMUR_ONE_PEER_PROTOCOL": "1"},
    )
    assert result.returncode == 0, result.stderr
    workspace = Path(result.stdout.strip().splitlines()[-1])
    meta = json.loads((workspace / "murmur.json").read_text())
    assert meta["mode"] == "swarm"
    assert meta["peers"] == 1
    assert meta["agents"][0]["id"] == "a1"
    assert (workspace / "prompts" / "root.md").is_file()
    assert not (workspace / "prompts" / "solo.md").exists()


def test_one_peer_protocol_switch_is_opt_in(tmp_path: Path):
    repo, brief = init_repo(tmp_path / "src")
    result = run_cli(
        "setup", str(brief), "--repo", str(repo), "--into", str(tmp_path / "runs"),
        "--id", "run1", "--solo", "--cap", "30s",
    )
    assert result.returncode == 0, result.stderr
    workspace = Path(result.stdout.strip().splitlines()[-1])
    meta = json.loads((workspace / "murmur.json").read_text())
    assert meta["mode"] == "solo"
    assert meta["agents"][0]["id"] == "solo"
