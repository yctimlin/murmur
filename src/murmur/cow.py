"""Copy-on-write directory copies.

macOS APFS uses `cp -c`. Linux btrfs and xfs use `cp --reflink=always`.
A failure is returned to the caller; this module never retries with a plain copy.
GNU cp can create an empty directory tree before reporting that reflink is
unsupported, so a failed destination is removed.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


class CowCopyError(RuntimeError):
    pass


def cow_argv(src: Path, dst: Path) -> list[str]:
    if sys.platform == "darwin":
        return ["cp", "-c", "-R", str(src), str(dst)]
    return ["cp", "--reflink=always", "-R", str(src), str(dst)]


def cow_copy(src: Path, dst: Path) -> None:
    if dst.exists():
        raise CowCopyError(f"{dst} already exists")
    argv = cow_argv(src, dst)
    try:
        result = subprocess.run(argv, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise CowCopyError("cp is not installed") from exc
    if result.returncode != 0:
        if dst.exists():
            shutil.rmtree(dst)
        detail = (result.stderr or result.stdout or "copy failed").strip().splitlines()
        raise CowCopyError(detail[0] if detail else "copy failed")
