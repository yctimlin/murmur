"""Real Git and subprocess tests for the opt-in completion barrier."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

import pytest

from murmur.integration import BarrierError, Ledger, inspect
from support import git, run_cli, setup_workspace


def enabled(tmp_path, *args):
    config = tmp_path / "integration.toml"
    config.write_text("integration_barrier = true\n")
    ws = setup_workspace(tmp_path, "--config", str(config), *args)
    ledger = Ledger(ws / "work" / ".murmur-integration") if not args else None
    return ws, ledger


def ready_all(ledger):
    for peer in ledger.config["agents"]:
        ledger.ready(peer, True)


def push(clone, name="part.txt"):
    (clone / name).write_text("new part\n")
    git(clone, "add", name)
    git(clone, "commit", "-qm", "part")
    git(clone, "push", "origin", "HEAD:main")


def test_off_and_solo_do_not_install_barrier(tmp_path):
    ws = setup_workspace(tmp_path)
    assert not (ws / "work" / ".murmur-integration").exists()
    assert run_cli("run", str(ws)).returncode == 0
    other = tmp_path / "solo"
    other.mkdir()
    ws, _ = enabled(other, "--solo")
    assert not (ws / "work" / ".murmur-integration").exists()
    assert run_cli("run", str(ws)).returncode == 0


def test_missing_receipt_changes_run_exit_and_records_why(tmp_path):
    ws, ledger = enabled(tmp_path)
    result = run_cli("run", str(ws))
    assert result.returncode == 2, result.stderr
    assert "integration incomplete" in result.stdout
    record = json.loads((ws / "logs" / "run.json").read_text())
    assert record["codex_exit_code"] == 0
    assert record["exit_code"] == 2
    assert record["integration"]["pending_peers"] == ["a1", "a2"]
    assert not record["integration"]["complete"]


def test_helper_frozen_execution_and_successful_run(tmp_path):
    ws, ledger = enabled(tmp_path)
    for peer in ("a1", "a2"):
        helper = ledger.clone(peer) / ".murmur" / "integration"
        result = subprocess.run([str(helper), "ready"], capture_output=True, text=True)
        assert result.returncode == 0, result.stdout
    helper = ledger.clone("a2") / ".murmur" / "integration"
    result = subprocess.run([str(helper), "check", "--", sys.executable, "-c", "print('whole result checked')"], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout
    receipt = json.loads(result.stdout)
    assert Path(receipt["log"]).read_text() == "whole result checked\n"
    assert run_cli("run", str(ws)).returncode == 0
    record = json.loads((ws / "logs" / "run.json").read_text())
    assert record["integration"]["complete"]
    assert record["integration"]["revision"] == record["integration"]["receipt"]["revision"]


def test_readiness_and_check_require_clean_current_main(tmp_path):
    _, ledger = enabled(tmp_path)
    a1 = ledger.clone("a1")
    push(a1)
    with pytest.raises(BarrierError, match="current main"):
        ledger.ready("a2", True)
    git(ledger.clone("a2"), "pull", "--ff-only")
    ready_all(ledger)
    (a1 / "unpublished.txt").write_text("x")
    with pytest.raises(BarrierError, match="clean clone"):
        ledger.check("a1", [sys.executable, "-c", "pass"])
    (a1 / "unpublished.txt").unlink()
    (a1 / ".work").mkdir()
    (a1 / ".work" / "scratch").write_text("not a deliverable")
    assert ledger.check("a1", [sys.executable, "-c", "pass"])["passed"]


def test_failures_and_mutating_commands_never_complete(tmp_path):
    _, ledger = enabled(tmp_path)
    with pytest.raises(BarrierError, match="active"):
        ledger.claim("a1", ["true"])
    ready_all(ledger)
    for command in ([sys.executable, "-c", "raise SystemExit(7)"], ["/missing/check"]):
        assert not ledger.check("a1", command)["passed"]
        assert not ledger.status()["complete"]
    result = ledger.check("a1", [sys.executable, "-c", "open('README.md', 'w').write('mutated')"])
    assert result["exit_code"] == 0 and not result["passed"] and not result["clean_after"]


def test_late_push_invalidates_pass_and_completion(tmp_path):
    ws, ledger = enabled(tmp_path)
    ready_all(ledger)
    assert ledger.check("a1", [sys.executable, "-c", "pass"])["passed"]
    assert ledger.status()["complete"]
    push(ledger.clone("a2"))
    status = ledger.status()
    assert not status["complete"] and status["receipt"] is None
    assert run_cli("run", str(ws)).returncode == 2


def test_concurrent_claim_is_exclusive_and_expiry_is_reclaimable(tmp_path):
    _, ledger = enabled(tmp_path)
    ready_all(ledger)
    def claim(peer):
        try:
            return ledger.claim(peer, ["true"])
        except BarrierError:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(claim, ["a1", "a2"]))
    assert sum(result is not None for result in results) == 1
    with ledger.transaction() as (_, state):
        state["claim"]["expires"] = time.time() - 1
    assert ledger.check("a2", [sys.executable, "-c", "pass"])["passed"]


def test_new_push_during_check_rejects_old_success(tmp_path):
    _, ledger = enabled(tmp_path)
    ready_all(ledger)
    # Exercise the public helper so its signal handlers execute in a main thread.
    marker = tmp_path / "checking"
    helper = ledger.clone("a1") / ".murmur" / "integration"
    command = [sys.executable, "-c", f"from pathlib import Path; import time; Path({str(marker)!r}).touch(); time.sleep(.6)"]
    proc = subprocess.Popen([str(helper), "check", "--", *command], stdout=subprocess.PIPE, text=True)
    deadline = time.monotonic() + 5
    while not marker.exists():
        assert time.monotonic() < deadline
        time.sleep(.01)
    push(ledger.clone("a2"))
    output, _ = proc.communicate(timeout=5)
    assert proc.returncode == 2
    assert not json.loads(output)["passed"]
    assert not ledger.status()["complete"]


def test_active_invalidates_receipt_and_claim(tmp_path):
    _, ledger = enabled(tmp_path)
    ready_all(ledger)
    ledger.check("a1", [sys.executable, "-c", "pass"])
    assert not ledger.ready("a2", False)["complete"]
    with pytest.raises(BarrierError, match="active"):
        ledger.check("a1", [sys.executable, "-c", "pass"])


def test_timeout_and_missing_ledger_fail_closed(tmp_path):
    ws, ledger = enabled(tmp_path)
    ready_all(ledger)
    ledger.config["check_timeout"] = .05
    result = ledger.check("a1", [sys.executable, "-c", "import time; time.sleep(9)"])
    assert not result["passed"] and result["error"]
    (ledger.folder / "ledger.sqlite3").unlink()
    assert not inspect(ws)["complete"]


def test_corrupt_or_missing_state_fails_closed_without_recreating_db(tmp_path):
    ws, ledger = enabled(tmp_path)
    with sqlite3.connect(ledger.folder / "ledger.sqlite3") as db:
        db.execute("DELETE FROM state")
    assert not inspect(ws)["complete"]
    (ledger.folder / "ledger.sqlite3").unlink()
    assert not inspect(ws)["complete"]
    assert not (ledger.folder / "ledger.sqlite3").exists()
