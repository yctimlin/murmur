"""What the private origin carries over from the source repository."""

from __future__ import annotations

from pathlib import Path

from support import git, init_repo, run_cli


def test_clone_has_tags_reachable_from_base_only(tmp_path: Path):
    repo, brief = init_repo(tmp_path / "src")
    git(repo, "tag", "v1.0")
    git(repo, "tag", "-a", "v1.0-annotated", "-m", "release")
    base = git(repo, "rev-parse", "HEAD")
    (repo / "later.txt").write_text("later\n")
    git(repo, "add", "later.txt")
    git(repo, "commit", "-q", "-m", "later")
    git(repo, "tag", "v2.0")
    result = run_cli(
        "setup", str(brief), "--repo", str(repo), "--into", str(tmp_path / "runs"),
        "--id", "run1", "--cap", "30s", "--solo", "--base", base,
    )
    assert result.returncode == 0, result.stderr
    workspace = Path(result.stdout.strip().splitlines()[-1])
    clone = workspace / "work" / "repo"
    assert set(git(clone, "tag", "--list").split()) == {"v1.0", "v1.0-annotated"}
    assert git(clone, "describe", "--tags", "--abbrev=0") in {"v1.0", "v1.0-annotated"}


def test_prompts_render_with_fixes(tmp_path: Path):
    from murmur.cli import ROOT_WAIT_MS, render

    closing = render("closing.md", cap="1h")
    assert "draft/<your id>" in closing and "port 0" in closing
    peer = render("peer.md", id="a1", n="2", peer_ids="a1, a2", clone="/c", env="", draft="10")
    assert "$MURMUR_AGENT" in peer
    root = render("root.md", n="2", spawns="-", wait_ms=str(ROOT_WAIT_MS))
    assert str(ROOT_WAIT_MS) in root
