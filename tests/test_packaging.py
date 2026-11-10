"""The package declares its MIT license and ships the license text."""

from __future__ import annotations

from importlib import metadata
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DIST = "codex-swarm"


def test_license_file_is_mit():
    text = (ROOT / "LICENSE").read_text()
    assert text.startswith("MIT License\n")
    assert "Copyright (c) 2026 Yuanqing Lin" in text


def test_installed_metadata_declares_mit_and_ships_license():
    try:
        dist = metadata.distribution(DIST)
    except metadata.PackageNotFoundError:
        pytest.skip(f"{DIST} is not installed")
    assert dist.metadata["License-Expression"] == "MIT"
    assert "LICENSE" in (dist.metadata.get_all("License-File") or [])
    shipped = [f for f in dist.files or [] if f.name == "LICENSE"]
    assert shipped, "LICENSE missing from the installed distribution"
    assert shipped[0].read_text() == (ROOT / "LICENSE").read_text()
