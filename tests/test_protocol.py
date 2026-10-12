"""Peers attest one commit; a later push voids the old attestation."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from murmur.protocol import evaluate_protocol

from support import setup_workspace


def _head(workspace: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "main"], cwd=workspace / "work" / "origin.git", text=True
    ).strip()


def _write(workspace: Path, agent: str, payload: dict) -> None:
    path = workspace / "protocol" / f"{agent}.json"
    path.write_text(json.dumps(payload))


def test_outcomes_and_invalidation(tmp_path: Path):
    workspace = setup_workspace(tmp_path, "--peers", "2")
    attempt = "attempt-1"
    (workspace / "protocol" / "attempt").write_text(attempt + "\n")
    meta = json.loads((workspace / "murmur.json").read_text())
    head = _head(workspace)
    report = evaluate_protocol(workspace, meta, attempt)
    assert report["outcomes"]["a1"]["status"] == "spawn-failed"
    assert report["outcomes"]["a2"]["status"] == "spawn-failed"
    assert report["complete"] is False

    _write(workspace, "a1", {"state": "started", "attempt_id": attempt})
    _write(workspace, "a2", {"state": "blocked", "attempt_id": attempt, "reason": "waiting"})
    report = evaluate_protocol(workspace, meta, attempt)
    assert report["outcomes"]["a1"]["status"] == "blocked"
    assert report["outcomes"]["a2"]["status"] == "blocked"

    _write(workspace, "a2", {"state": "failed", "attempt_id": attempt, "reason": "nope"})
    assert evaluate_protocol(workspace, meta, attempt)["outcomes"]["a2"]["status"] == "failed"

    _write(workspace, "a1", {
        "state": "completed", "attempt_id": attempt, "commit": "deadbeef",
        "checks": [{"name": "acceptance", "result": "pass"}],
    })
    invalidated = evaluate_protocol(workspace, meta, attempt)["outcomes"]["a1"]
    assert invalidated["status"] == "failed"
    assert "later push" in invalidated["reason"]

    _write(workspace, "a1", {
        "state": "completed", "attempt_id": attempt, "commit": head,
        "checks": [{"name": "acceptance", "result": "fail"}],
    })
    assert "acceptance" in evaluate_protocol(workspace, meta, attempt)["outcomes"]["a1"]["reason"]

    _write(workspace, "a1", {
        "state": "completed", "attempt_id": "other-attempt", "commit": head,
        "checks": [{"name": "acceptance", "result": "pass"}],
    })
    assert evaluate_protocol(workspace, meta, attempt)["outcomes"]["a1"]["status"] == "spawn-failed"

    for agent in ("a1", "a2"):
        _write(workspace, agent, {
            "state": "completed", "attempt_id": attempt, "commit": head,
            "checks": [{"name": "acceptance", "result": "pass"}],
        })
    done = evaluate_protocol(workspace, meta, attempt)
    assert done["complete"] is True
    assert done["outcomes"]["a1"]["commit"] == done["outcomes"]["a2"]["commit"] == head


def test_attest_wrapper_and_history(tmp_path: Path):
    workspace = setup_workspace(tmp_path, "--peers", "2")
    (workspace / "protocol" / "attempt").write_text("attempt-9\n")
    clone = Path(json.loads((workspace / "murmur.json").read_text())["agents"][0]["clone"])
    wrapper = workspace / "bin" / "murmur-attest"
    subprocess.run([str(wrapper), "started"], cwd=clone, check=True)
    payload = json.loads((workspace / "protocol" / "a1.json").read_text())
    assert payload["state"] == "started"
    assert payload["attempt_id"] == "attempt-9"
    head = _head(workspace)
    subprocess.run(
        [str(wrapper), "completed", "--commit", head, "--check", "acceptance=pass"],
        cwd=clone, check=True,
    )
    history = (workspace / "protocol" / "a1.history.jsonl").read_text().splitlines()
    assert len(history) == 2
    assert json.loads(history[0])["state"] == "started"
    assert json.loads(history[1])["commit"] == head
    meta = json.loads((workspace / "murmur.json").read_text())
    # a2 has not attested, so the swarm is still incomplete, and a1 matches HEAD.
    report = evaluate_protocol(workspace, meta, "attempt-9")
    assert report["outcomes"]["a1"]["status"] == "completed"
    assert report["outcomes"]["a2"]["status"] == "spawn-failed"
    assert "at most 2 more times" in (workspace / "prompts" / "root.md").read_text()
