"""Real origin ref transactions: contracts fire before integration, never by model fiat."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from support import git, setup_workspace
from murmur.contracts import main_lock


def fixture(tmp_path):
    ws = setup_workspace(tmp_path, extra_env={"MURMUR_CONTRACTS": "1"})
    clone = ws / "work" / "peers" / "a1"
    return ws, clone, ws / "work" / ".murmur-contracts"


def helper(clone, *args):
    return subprocess.run([str(clone / ".murmur" / "contract"), *map(str, args)],
                          cwd=clone, capture_output=True, text=True, timeout=15)


def freeze(clone, name="shape", content=None, timeout=5):
    probe = clone / ".murmur" / "probe.py"
    probe.write_text(content or 'from pathlib import Path\nassert Path("README.md").read_text() == "hello\\n"\n')
    return helper(clone, "add", name, "--probe", probe, "--timeout", str(timeout), "--", sys.executable, "{probe}")


def push(clone, text):
    (clone / "README.md").write_text(text)
    git(clone, "add", "README.md")
    git(clone, "commit", "-qm", "change")
    return subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=clone,
                          capture_output=True, text=True, timeout=15)


def test_frozen_probe_rejects_breakage_and_accepts_repair(tmp_path):
    ws, clone, state = fixture(tmp_path)
    baseline = git(clone, "rev-parse", "HEAD")
    assert freeze(clone).returncode == 0
    # Altering the local test after activation cannot weaken the shared gate.
    (clone / ".murmur" / "probe.py").write_text("pass\n")
    broken = push(clone, "broken\n")
    assert broken.returncode != 0
    assert "contract rejected" in broken.stderr
    assert git(state.parent / "origin.git", "rev-parse", "main") == baseline
    fixed = push(clone, "hello\n")
    assert fixed.returncode == 0, fixed.stderr
    events = [json.loads(row) for row in (state / "events.jsonl").read_text().splitlines()]
    assert [row["passed"] for row in events] == [True, False, True]
    assert events[-1]["revision"] == git(clone, "rev-parse", "HEAD")
    other = ws / "work" / "peers" / "a2"
    assert json.loads(helper(other, "status").stdout)[0]["name"] == "shape"
    assert "probe_hex" not in helper(other, "status").stdout


def test_bad_probe_never_activates_and_names_are_immutable(tmp_path):
    ws, clone, state = fixture(tmp_path)
    assert freeze(clone, content="raise RuntimeError('bad')").returncode == 1
    assert json.loads((state / "contracts.json").read_text()) == []
    assert freeze(clone).returncode == 0
    assert freeze(clone, content="pass").returncode == 1
    assert len(json.loads((state / "contracts.json").read_text())) == 1


def test_timeout_is_failure_and_main_lock_blocks_activation(tmp_path):
    ws, clone, state = fixture(tmp_path)
    timed = freeze(clone, content="import time\ntime.sleep(60)", timeout=0.05)
    assert timed.returncode == 1 and "timeout" in timed.stderr
    with main_lock(state.parent / "origin.git"):
        busy = freeze(clone)
    assert busy.returncode == 1 and "busy" in busy.stderr
    assert freeze(clone).returncode == 0


def test_baseline_has_no_gate_or_helper(tmp_path):
    ws = setup_workspace(tmp_path)
    assert not (ws / "work" / ".murmur-contracts").exists()
    assert not (ws / "work" / "origin.git" / "hooks" / "reference-transaction").exists()
    assert not (ws / "work" / "peers" / "a1" / ".murmur" / "contract").exists()


def test_non_main_push_remains_available_for_drafts(tmp_path):
    ws, clone, state = fixture(tmp_path)
    assert freeze(clone).returncode == 0
    (clone / "README.md").write_text("draft\n")
    git(clone, "add", "README.md")
    git(clone, "commit", "-qm", "draft")
    git(clone, "push", "origin", "HEAD:draft/a1")
    assert len((state / "events.jsonl").read_text().splitlines()) == 1


def test_interrupted_activation_kills_probe_and_releases_main(tmp_path):
    import signal
    import time

    ws, clone, state = fixture(tmp_path)
    marker = tmp_path / "probe.pid"
    probe = clone / ".murmur" / "slow.py"
    probe.write_text(f"import os,time\nfrom pathlib import Path\nPath({str(marker)!r}).write_text(str(os.getpid()))\ntime.sleep(60)\n")
    proc = subprocess.Popen([str(clone / ".murmur" / "contract"), "add", "slow", "--probe",
                             str(probe), "--timeout", "30", "--", sys.executable, "{probe}"],
                            cwd=clone, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        deadline = time.monotonic() + 5
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert marker.exists()
        pid = int(marker.read_text())
        proc.send_signal(signal.SIGTERM)
        proc.communicate(timeout=5)
        assert proc.returncode == 1
        with pytest.raises(ProcessLookupError):
            os.kill(pid, 0)
        assert json.loads((state / "contracts.json").read_text()) == []
        assert freeze(clone).returncode == 0
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.communicate()


def test_probe_cannot_repair_broken_candidate_and_claim_success(tmp_path):
    ws, clone, state = fixture(tmp_path)
    repair = 'from pathlib import Path\np=Path("README.md")\np.write_text("hello\\n")\nassert p.read_text()=="hello\\n"\n'
    assert freeze(clone, content=repair).returncode == 0
    result = push(clone, "broken\n")
    assert result.returncode != 0
    assert "probe changed tracked candidate inputs" in result.stderr
    assert git(state.parent / "origin.git", "show", "main:README.md") == "hello"


@pytest.mark.parametrize("mutation", ['p.write_text("changed")', 'p.unlink()', 'p.chmod(0o755)'])
def test_activation_rejects_content_deletion_and_mode_mutation(tmp_path, mutation):
    ws, clone, state = fixture(tmp_path)
    result = freeze(clone, content='from pathlib import Path\np=Path("README.md")\n' + mutation + '\n')
    assert result.returncode == 1
    assert "probe changed tracked candidate inputs" in result.stderr
    assert json.loads((state / "contracts.json").read_text()) == []
