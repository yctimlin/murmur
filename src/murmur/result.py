"""Read-only inventory of the delivered revision and peer worktrees.

Git state is evidence of delivery, never a claim that the objective is complete.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _git(repo: Path, *args: str, allow_failure: bool = False):
    result = subprocess.run(
        ["git", "--no-optional-locks", *args], cwd=repo,
        env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
        capture_output=True, timeout=5, check=False,
    )
    if result.returncode and not allow_failure:
        raise RuntimeError(f"git {args[0]} exited {result.returncode}")
    return result if allow_failure else result.stdout


def inspect_result(workspace: Path, meta: dict) -> dict:
    """Record origin/main and each clone without fetching or changing git state.

    Missing repositories and interrupted work remain visible as unavailable fields.
    A stale clone whose HEAD is an ancestor of main is successfully integrated.
    Draft commits and setup changes can legitimately remain outside main.
    """
    origin = workspace / "work" / "origin.git"
    report: dict = {"head": None, "new_commits": None, "changed_paths": None,
                    "has_pr": None, "peers": [], "errors": []}
    try:
        head = _git(origin, "rev-parse", "--verify", "refs/heads/main^{commit}").decode().strip()
        report["head"] = head
        report["new_commits"] = int(_git(origin, "rev-list", "--count", f"{meta['base']}..{head}"))
        changed = _git(origin, "diff", "--name-only", "-z", meta["base"], head, "--")
        report["changed_paths"] = len([path for path in changed.split(b"\0") if path])
        report["has_pr"] = b"PR.md\0" in _git(origin, "ls-tree", "--name-only", "-z", head, "--", "PR.md")
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        report["errors"].append(f"origin: {error}")
    for agent in meta.get("agents", []):
        peer = {"id": agent["id"], "head": None, "head_in_main": None,
                "tracked_changes": None}
        report["peers"].append(peer)
        try:
            clone = Path(agent["clone"])
            peer["head"] = _git(clone, "rev-parse", "--verify", "HEAD^{commit}").decode().strip()
            peer["tracked_changes"] = bool(_git(clone, "status", "--porcelain=v1", "-z", "--untracked-files=no"))
            if report["head"]:
                # An absent object is normally an unpushed local commit. The result
                # cannot contain it; no fetch into a stopped peer is necessary.
                exists = _git(origin, "cat-file", "-e", f"{peer['head']}^{{commit}}", allow_failure=True)
                if exists.returncode:
                    peer["head_in_main"] = False
                else:
                    ancestor = _git(origin, "merge-base", "--is-ancestor", peer["head"], report["head"], allow_failure=True)
                    if ancestor.returncode not in (0, 1):
                        raise RuntimeError(f"git merge-base exited {ancestor.returncode}")
                    peer["head_in_main"] = ancestor.returncode == 0
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
            report["errors"].append(f"{agent['id']}: {error}")
    return report
