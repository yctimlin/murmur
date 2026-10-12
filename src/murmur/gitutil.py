"""Git subprocess helper."""

from __future__ import annotations

import subprocess
from pathlib import Path


def git(*args: str, cwd: Path | None = None, env: dict | None = None) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, env=env, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()
