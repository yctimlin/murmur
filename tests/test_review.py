"""Real Git review-gate invariants; no credentials or model calls."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from murmur import review
from support import git, run_cli, setup_workspace


def workspace(tmp_path):
    config = tmp_path / "config.toml"
    config.write_text("independent_review = true\n")
    ws = setup_workspace(tmp_path, "--peers", "2", "--config", str(config))
    meta = json.loads((ws / "murmur.json").read_text())
    return ws, Path(meta["agents"][0]["clone"]), Path(meta["agents"][1]["clone"])


def land(clone, path, text):
    (clone / path).write_text(text)
    git(clone, "add", "--", path)
    git(clone, "commit", "-qm", "change")
    git(clone, "push", "origin", "HEAD:main")
    return git(clone, "rev-parse", "HEAD")


def sign(ws, clone, revision, paths):
    return review.attest(ws / "work" / ".murmur-review", clone, revision, paths, "Inspected input boundaries and exercised behavior")


def test_independent_receipt_required_and_self_review_rejected(tmp_path):
    ws, a1, a2 = workspace(tmp_path)
    head = land(a1, "widget.txt", "single author\n")
    assert review.inspect(ws)["pending"] == ["widget.txt"]
    with pytest.raises(review.ReviewError, match="self-review"):
        sign(ws, a1, head, ["widget.txt"])
    git(a2, "pull", "--ff-only")
    sign(ws, a2, head, ["widget.txt"])
    assert review.inspect(ws)["complete"]
    result = run_cli("run", str(ws))
    assert result.returncode == 0, result.stderr
    assert json.loads((ws / "logs/run.json").read_text())["independent_review"]["complete"]


def test_launcher_rejects_unreviewed_success(tmp_path):
    ws, a1, _ = workspace(tmp_path)
    land(a1, "widget.txt", "single author\n")
    result = run_cli("run", str(ws))
    assert result.returncode == 1
    assert "independent review incomplete" in result.stderr
    record = json.loads((ws / "logs/run.json").read_text())
    assert record["codex_exit_code"] == 0
    assert record["exit_code"] == 1
    assert record["independent_review"]["pending"] == ["widget.txt"]


def test_stale_dirty_and_unknown_peer_rejected(tmp_path):
    ws, a1, a2 = workspace(tmp_path)
    head = land(a1, "widget.txt", "v1\n")
    with pytest.raises(review.ReviewError, match="stale"):
        sign(ws, a2, head, ["widget.txt"])
    git(a2, "pull", "--ff-only")
    (a2 / "widget.txt").write_text("dirty")
    with pytest.raises(review.ReviewError, match="clean"):
        sign(ws, a2, head, ["widget.txt"])
    with pytest.raises(review.ReviewError, match="configured peer"):
        sign(ws, tmp_path / "src", head, ["widget.txt"])


def test_receipt_survives_unrelated_commit_but_not_content_change(tmp_path):
    ws, a1, a2 = workspace(tmp_path)
    head = land(a1, "widget.txt", "v1\n")
    git(a2, "pull", "--ff-only")
    sign(ws, a2, head, ["widget.txt"])
    land(a1, "other.txt", "unrelated\n")
    assert review.inspect(ws)["pending"] == ["other.txt"]
    head = land(a1, "widget.txt", "v2\n")
    assert review.inspect(ws)["pending"] == ["other.txt", "widget.txt"]
    git(a2, "pull", "--ff-only")
    sign(ws, a2, head, ["widget.txt", "other.txt"])
    assert review.inspect(ws)["complete"]


def test_deletions_and_modes_are_reviewable(tmp_path):
    ws, a1, a2 = workspace(tmp_path)
    git(a1, "rm", "README.md")
    git(a1, "commit", "-qm", "delete")
    git(a1, "push", "origin", "HEAD:main")
    git(a2, "pull", "--ff-only")
    sign(ws, a2, git(a2, "rev-parse", "HEAD"), ["README.md"])
    assert review.inspect(ws)["complete"]
    head = land(a1, "tool", "#!/bin/sh\nexit 0\n")
    git(a2, "pull", "--ff-only")
    sign(ws, a2, head, ["tool"])
    (a1 / "tool").chmod(0o755)
    git(a1, "add", "tool")
    git(a1, "commit", "-qm", "mode")
    git(a1, "push", "origin", "HEAD:main")
    assert review.inspect(ws)["pending"] == ["tool"]


def test_historical_second_author_does_not_waive_later_review(tmp_path):
    ws, a1, a2 = workspace(tmp_path)
    land(a1, "widget.txt", "v1\n")
    git(a2, "pull", "--ff-only")
    land(a2, "widget.txt", "v2\n")
    git(a1, "pull", "--ff-only")
    head = land(a1, "widget.txt", "rewritten solely by a1\n")
    result = review.inspect(ws)
    assert not result["complete"]
    assert result["multi_author_paths"] == 1
    with pytest.raises(review.ReviewError, match="self-review"):
        sign(ws, a1, head, ["widget.txt"])
    git(a2, "pull", "--ff-only")
    sign(ws, a2, head, ["widget.txt"])
    assert review.inspect(ws)["complete"]


def test_helper_runs_without_package_and_rejects_empty_notes(tmp_path):
    ws, a1, a2 = workspace(tmp_path)
    head = land(a1, "path with space.txt", "v1\n")
    git(a2, "pull", "--ff-only")
    result = subprocess.run([str(a2 / ".murmur/review"), "attest", "--revision", head,
        "--note", "Reviewed edge behavior", "--", "path with space.txt"], cwd=a2, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert review.inspect(ws)["complete"]
    with pytest.raises(review.ReviewError, match="nonempty"):
        review.attest(ws / "work/.murmur-review", a2, head, ["path with space.txt"], " ")


def test_disabled_mode_and_solo_validation(tmp_path):
    ws = setup_workspace(tmp_path, "--solo")
    assert not (ws / "work/.murmur-review").exists()
    assert "Independent review is enforced" not in (ws / "prompts/solo.md").read_text()
    config = tmp_path / "review.toml"
    config.write_text("independent_review = true\n")
    result = run_cli("setup", str(tmp_path / "brief.md"), "--repo", str(tmp_path / "src"),
        "--solo", "--config", str(config))
    assert result.returncode == 3
    assert "at least two peers" in result.stderr


def test_broken_ledger_fails_closed(tmp_path):
    ws, a1, _ = workspace(tmp_path)
    land(a1, "widget.txt", "v1\n")
    (ws / "work/.murmur-review/reviews.sqlite").write_bytes(b"not sqlite")
    result = run_cli("run", str(ws))
    assert result.returncode == 1
    assert "error" in json.loads((ws / "logs/run.json").read_text())["independent_review"]


def test_missing_ledger_fails_closed_even_without_changes(tmp_path):
    ws, _, _ = workspace(tmp_path)
    (ws / "work/.murmur-review/reviews.sqlite").unlink()
    result = run_cli("run", str(ws))
    assert result.returncode == 1
    assert "error" in json.loads((ws / "logs/run.json").read_text())["independent_review"]
    assert not (ws / "work/.murmur-review/reviews.sqlite").exists()


def test_malformed_config_is_recorded_instead_of_losing_run_log(tmp_path):
    ws, _, _ = workspace(tmp_path)
    (ws / "work/.murmur-review/config.json").write_text("{}")
    result = run_cli("run", str(ws))
    assert result.returncode == 1
    assert "error" in json.loads((ws / "logs/run.json").read_text())["independent_review"]


def test_plain_merge_does_not_let_content_author_self_review(tmp_path):
    ws, a1, a2 = workspace(tmp_path)
    land(a1, "widget.txt", "authored only by a1\n")
    # a2 has not pulled a1's change; create a divergent independent change.
    (a2 / "other.txt").write_text("a2 work\n")
    git(a2, "add", "other.txt")
    git(a2, "commit", "-qm", "a2 branch")
    git(a2, "fetch", "origin")
    git(a2, "merge", "--no-edit", "origin/main")
    git(a2, "push", "origin", "HEAD:main")
    head = git(a2, "rev-parse", "HEAD")
    git(a1, "pull", "--ff-only")
    with pytest.raises(review.ReviewError, match="self-review"):
        sign(ws, a1, head, ["widget.txt"])
    sign(ws, a2, head, ["widget.txt"])
    sign(ws, a1, head, ["other.txt"])
    assert review.inspect(ws)["complete"]
