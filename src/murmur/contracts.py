"""Frozen peer-authored interface probes, enforced at the private main ref.

This runtime is copied into each enabled workspace and only uses the stdlib.
It is cooperation infrastructure, not a security boundary between trusted peers.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import signal
import subprocess
import sys
import tempfile
import time

NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
MAX_PROBE = 64 * 1024
MAX_CONTRACTS = 8


def git(origin: Path, *args: str, env=None) -> str:
    result = subprocess.run(["git", "--git-dir", str(origin), *args], env=env,
                            capture_output=True, text=True, check=True)
    return result.stdout.strip()


@contextmanager
def locked(state: Path):
    with (state / "state.lock").open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield


def read_contracts(state: Path) -> list[dict]:
    return json.loads((state / "contracts.json").read_text())


def event(state: Path, **values):
    with (state / "events.jsonl").open("a") as handle:
        handle.write(json.dumps({"time": time.time(), **values}) + "\n")


@contextmanager
def main_lock(origin: Path):
    """Hold Git's own ref lock while activating a contract against accepted main.

    This serializes activation with prepared reference transactions. Merely locking
    the contract manifest would allow a checked push to land after activation.
    """
    head = git(origin, "rev-parse", "refs/heads/main")
    proc = subprocess.Popen(["git", "--git-dir", str(origin), "update-ref", "--stdin"],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True)
    try:
        proc.stdin.write(f"start\nverify refs/heads/main {head}\nprepare\n")
        proc.stdin.flush()
        if proc.stdout.readline().strip() != "start: ok" or proc.stdout.readline().strip() != "prepare: ok":
            raise ValueError("main changed or is busy; retry contract activation")
        yield head
    finally:
        if proc.poll() is None:
            try:
                proc.stdin.write("abort\n")
                proc.stdin.flush()
            except BrokenPipeError:
                pass
        proc.communicate(timeout=10)


def materialize(origin: Path, revision: str, destination: Path):
    """Use a temporary index; never modify origin's index or a peer's checkout."""
    env = dict(os.environ)
    env["GIT_INDEX_FILE"] = str(destination.parent / "index")
    env["GIT_WORK_TREE"] = str(destination)
    git(origin, "read-tree", revision, env=env)
    git(origin, "checkout-index", "--all", "--force", env=env)


def run_probe(state: Path, origin: Path, revision: str, contract: dict) -> dict:
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="contract-", dir=state) as raw:
        temporary = Path(raw)
        tree = temporary / "tree"
        tree.mkdir()
        materialize(origin, revision, tree)
        probe = temporary / "probe"
        probe.write_bytes(bytes.fromhex(contract["probe_hex"]))
        probe.chmod(0o700)
        argv = [arg.replace("{probe}", str(probe)) for arg in contract["argv"]]
        # A probe runs in the candidate tree, not in receive-pack's repository context.
        local_git = {"GIT_DIR", "GIT_COMMON_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE",
                     "GIT_PREFIX", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
                     "GIT_QUARANTINE_PATH"}
        env = {k: v for k, v in os.environ.items() if k not in local_git}
        env["MURMUR_CONTRACT_REVISION"] = revision
        code = None
        reason = None
        with (temporary / "output").open("w+b") as output:
            proc = None
            try:
                proc = subprocess.Popen(argv, cwd=tree, env=env, stdout=output,
                                        stderr=subprocess.STDOUT, start_new_session=True)
                try:
                    code = proc.wait(timeout=contract["timeout"])
                except subprocess.TimeoutExpired:
                    reason = "timeout"
            except OSError as error:
                reason = str(error)
            finally:
                if proc is not None:
                    # Probes may fork; reap the entire group even after a clean leader exit.
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    proc.wait()
            output.seek(0)
            detail = output.read(4096).decode(errors="replace")
        return {"name": contract["name"], "revision": revision,
                "passed": code == 0 and reason is None, "exit_code": code,
                "reason": reason, "output": detail,
                "seconds": round(time.monotonic() - started, 4)}


def register(state: Path, name: str, probe: Path, argv: list[str], timeout: float):
    if not NAME.fullmatch(name):
        raise ValueError("contract name must be 1-64 letters, numbers, dots, dashes or underscores")
    if not 0 < timeout <= 30:
        raise ValueError("probe timeout must be greater than 0 and at most 30 seconds")
    if argv[:1] == ["--"]:
        argv = argv[1:]
    if not argv or not any("{probe}" in arg for arg in argv):
        raise ValueError("provide an argv command containing {probe}, e.g. -- python3 {probe}")
    data = probe.read_bytes()
    if len(data) > MAX_PROBE:
        raise ValueError("probe exceeds 64 KiB; keep interface contracts small")
    origin = state.parent / "origin.git"
    contract = {"name": name, "probe_hex": data.hex(), "sha256": hashlib.sha256(data).hexdigest(),
                "argv": argv, "timeout": timeout, "author": os.environ.get("MURMUR_AGENT", "unknown")}
    with main_lock(origin) as head, locked(state):
        contracts = read_contracts(state)
        if any(item["name"] == name for item in contracts):
            raise ValueError("contract name already frozen; choose a new name")
        if len(contracts) >= MAX_CONTRACTS:
            raise ValueError("at most 8 short contracts per run")
        result = run_probe(state, origin, head, contract)
        event(state, action="activation", **result)
        if not result["passed"]:
            raise ValueError(f"contract does not pass accepted main: {json.dumps(result)}")
        contract["base"] = head
        contracts.append(contract)
        temporary = state / "contracts.json.new"
        temporary.write_text(json.dumps(contracts) + "\n")
        temporary.replace(state / "contracts.json")
    return {"frozen": name, "base": head, "sha256": contract["sha256"]}


def check_transaction(state: Path, phase: str, lines: str) -> int:
    if phase != "prepared":
        return 0
    for line in lines.splitlines():
        old, revision, ref = line.split()
        if ref != "refs/heads/main" or old == revision:
            continue
        with locked(state):
            for contract in read_contracts(state):
                result = run_probe(state, state.parent / "origin.git", revision, contract)
                event(state, action="gate", **result)
                if not result["passed"]:
                    print("murmur contract rejected: " + json.dumps(result), file=sys.stderr)
                    return 1
    return 0


def install(ws: Path, agents: list[dict]) -> str:
    state = ws / "work" / ".murmur-contracts"
    state.mkdir()
    (state / "contracts.json").write_text("[]\n")
    runtime = state / "runtime.py"
    runtime.write_bytes(Path(__file__).read_bytes())
    command = f"{shlex.quote(sys.executable)} {shlex.quote(str(runtime))} --state {shlex.quote(str(state))}"
    hook = ws / "work" / "origin.git" / "hooks" / "reference-transaction"
    hook.write_text(f'#!/bin/sh\nexec {command} hook "$@"\n')
    hook.chmod(0o755)
    for agent in agents:
        wrapper = Path(agent["clone"]) / ".murmur" / "contract"
        wrapper.parent.mkdir(exist_ok=True)
        wrapper.write_text(f'#!/bin/sh\nexport MURMUR_AGENT={shlex.quote(agent["id"])}\nexec {command} "$@"\n')
        wrapper.chmod(0o755)
    return """\nAn executable interface contract gate is enabled. Before parallel implementation of a shared
interface, agree on a small standalone probe that passes accepted main, then any peer freezes it:
`.murmur/contract add NAME --probe PATH -- python3 {probe}` (replace interpreter as needed).
Use a concrete invariant another peer depends on. The probe runs in a fresh incoming tracked
tree, without ignored dependencies; `{probe}` names its frozen copy. Keep it fast (default 5s,
maximum 30s). Python probes importing project modules should add the working directory to
`sys.path`. Every later main update runs frozen probes and rejects a violation. Fix the change
and push again. Existing names cannot be weakened or removed during this run. Inspect
`.murmur/contract status` for contracts and the shared events.jsonl for exact revision receipts.
Contracts supplement behavioral review; they cover only the invariants peers register.
"""


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", required=True, type=Path)
    sub = parser.add_subparsers(dest="action", required=True)
    add = sub.add_parser("add")
    add.add_argument("name")
    add.add_argument("--probe", required=True, type=Path)
    add.add_argument("--timeout", type=float, default=5)
    sub.add_parser("status")
    hook = sub.add_parser("hook")
    hook.add_argument("phase")
    # Split command argv explicitly; argparse.REMAINDER would swallow --probe.
    raw = list(sys.argv[1:] if argv is None else argv)
    command = []
    if "--" in raw:
        offset = raw.index("--")
        raw, command = raw[:offset], raw[offset + 1:]
    args = parser.parse_args(raw)
    try:
        if args.action == "hook":
            return check_transaction(args.state, args.phase, sys.stdin.read())
        if args.action == "add":
            result = register(args.state, args.name, args.probe, command, args.timeout)
        else:
            with locked(args.state):
                result = [{k: v for k, v in item.items() if k != "probe_hex"}
                          for item in read_contracts(args.state)]
        print(json.dumps(result))
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"murmur contract: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
