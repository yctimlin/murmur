"""Delivered revision inventory uses real local git repositories, never a model."""

import json
import shutil
from pathlib import Path

from murmur.result import inspect_result
from support import git, run_cli, setup_workspace


def _state(tmp_path):
    workspace = setup_workspace(tmp_path, "--solo")
    meta = json.loads((workspace / "murmur.json").read_text())
    return workspace, meta, Path(meta["agents"][0]["clone"])


def test_clean_unchanged_result_is_not_invented_success(tmp_path):
    workspace, meta, clone = _state(tmp_path)
    record = inspect_result(workspace, meta)
    assert record["head"] == meta["base"]
    assert record["new_commits"] == record["changed_paths"] == 0
    assert record["has_pr"] is False
    assert record["peers"] == [{"id": "solo", "head": meta["base"],
                                "head_in_main": True, "tracked_changes": False}]
    assert record["errors"] == []


def test_local_commit_and_tracked_edit_are_visible_without_mutating_clone(tmp_path):
    workspace, meta, clone = _state(tmp_path)
    (clone / "new.txt").write_text("work\n")
    git(clone, "add", "new.txt")
    git(clone, "commit", "-m", "unpublished work")
    (clone / "README.md").write_text("uncommitted edit\n")
    before = git(clone, "status", "--porcelain")
    record = inspect_result(workspace, meta)
    assert record["peers"][0]["head_in_main"] is False
    assert record["peers"][0]["tracked_changes"] is True
    assert git(clone, "status", "--porcelain") == before
    assert record["new_commits"] == 0


def test_pushed_result_and_stale_peer_are_integrated(tmp_path):
    workspace, meta, clone = _state(tmp_path)
    (clone / "PR.md").write_text("review this\n")
    git(clone, "add", "PR.md")
    git(clone, "commit", "-m", "deliver")
    git(clone, "push", "origin", "HEAD:main")
    delivered = git(clone, "rev-parse", "HEAD")
    git(clone, "checkout", "--detach", meta["base"])
    record = inspect_result(workspace, meta)
    assert record["head"] == delivered
    assert record["new_commits"] == record["changed_paths"] == 1
    assert record["has_pr"] is True
    assert record["peers"][0]["head_in_main"] is True


def test_missing_clone_preserves_delivered_revision_and_records_unknown(tmp_path):
    workspace, meta, clone = _state(tmp_path)
    shutil.rmtree(clone)
    record = inspect_result(workspace, meta)
    assert record["head"] == meta["base"]
    assert record["peers"][0]["head_in_main"] is None
    assert record["errors"]


def test_missing_origin_is_unknown_not_zero(tmp_path):
    workspace, meta, clone = _state(tmp_path)
    shutil.rmtree(workspace / "work" / "origin.git")
    record = inspect_result(workspace, meta)
    assert record["head"] is None
    assert record["new_commits"] is None
    assert record["peers"][0]["head_in_main"] is None
    assert record["errors"]


def test_run_records_result_for_success_and_failure(tmp_path):
    workspace, meta, clone = _state(tmp_path)
    result = run_cli("run", str(workspace), extra_env={"MURMUR_FAKE_CODEX_MODE": "fail-with-commit"})
    assert result.returncode == 1
    record = json.loads((workspace / "logs" / "run.json").read_text())
    assert record["result"]["new_commits"] == 1
    assert record["result"]["head"] == git(clone, "rev-parse", "HEAD")
