"""Process-group cleanup does not return while descendants are alive."""

from __future__ import annotations

import os
import subprocess
import sys
import time

from murmur.procutil import pid_alive, stop_process_group


def test_stop_returns_quickly_when_the_group_is_already_dead():
    proc = subprocess.Popen([sys.executable, "-c", "print('hi')"], start_new_session=True)
    proc.wait(timeout=5)
    started = time.monotonic()
    stop_process_group(proc, term_grace=10, kill_grace=10)
    assert time.monotonic() - started < 2


def test_stop_escalates_to_sigkill_for_a_term_resistant_child(tmp_path):
    marker = tmp_path / "child"
    script = r"""
import os, signal, sys, time
from pathlib import Path
marker = Path(sys.argv[1])
child = os.fork()
if child == 0:
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    def on_term(signum, frame):
        with marker.open("a", encoding="utf-8") as handle:
            handle.write(" TERM\n")
            handle.flush()
    signal.signal(signal.SIGTERM, on_term)
    marker.write_text(f"{os.getpid()} START\n")
    while True:
        time.sleep(0.2)
os._exit(0)
"""
    proc = subprocess.Popen([sys.executable, "-c", script, str(marker)], start_new_session=True)
    deadline = time.monotonic() + 5
    while not marker.exists():
        assert time.monotonic() < deadline
        time.sleep(0.02)
    proc.wait(timeout=5)
    stop_process_group(proc, term_grace=0.3, kill_grace=0.5)
    text = marker.read_text()
    pid = int(text.split()[0])
    assert "START" in text
    assert "TERM" in text
    assert not pid_alive(pid)
