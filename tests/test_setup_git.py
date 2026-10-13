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


def test_plain_folder_is_snapshotted_and_left_untouched(tmp_path: Path):
    folder = tmp_path / "docs"
    folder.mkdir()
    (folder / "notes.md").write_text("hello\n")
    brief = tmp_path / "brief.md"
    brief.write_text("Do the thing.\n")
    result = run_cli(
        "setup", str(brief), "--repo", str(folder), "--into", str(tmp_path / "runs"),
        "--id", "run1", "--cap", "30s", "--solo",
    )
    assert result.returncode == 0, result.stderr
    workspace = Path(result.stdout.strip().splitlines()[-1])
    assert (workspace / "work" / "repo" / "notes.md").read_text() == "hello\n"
    assert not (folder / ".git").exists() and not (workspace / "input").exists()


def _folder_run(tmp_path: Path, max_mb: str = "50") -> tuple[Path, Path, Path]:
    folder = tmp_path / "docs"
    folder.mkdir()
    (folder / "a.md").write_text("a\n")
    (folder / "b.md").write_text("b\n")
    (folder / "big.bin").write_bytes(b"x" * 2_000_000)
    brief = tmp_path / "brief.md"
    brief.write_text("Do the thing.\n")
    result = run_cli(
        "setup", str(brief), "--repo", str(folder), "--into", str(tmp_path / "runs"),
        "--id", "run1", "--cap", "30s", "--solo", "--max-file-mb", max_mb,
    )
    assert result.returncode == 0, result.stderr
    ws = Path(result.stdout.strip().splitlines()[-1])
    clone = ws / "work" / "repo"
    (clone / "a.md").write_text("a by agent\n")
    (clone / "b.md").write_text("b by agent\n")
    (clone / "new.md").write_text("new\n")
    git(clone, "add", "-A")
    git(clone, "commit", "-q", "-m", "work")
    git(clone, "push", "-q", "origin", "HEAD:main")
    return folder, ws, clone


def test_large_files_are_linked_not_committed(tmp_path: Path):
    folder, ws, clone = _folder_run(tmp_path, max_mb="1")
    assert (clone / "big.bin").is_symlink()
    assert (clone / "big.bin").stat().st_size == 2_000_000
    out = tmp_path / "out"
    assert run_cli("export", str(ws), "--to", str(out)).returncode == 0
    assert (out / "big.bin").read_bytes() == b"x" * 2_000_000 and not (out / "big.bin").is_symlink()
    assert (out / "new.md").read_text() == "new\n"


def test_apply_keeps_user_edits_made_during_the_run(tmp_path: Path):
    folder, ws, _ = _folder_run(tmp_path)
    (folder / "b.md").write_text("b by user\n")
    result = run_cli("export", str(ws), "--apply")
    assert result.returncode == 0, result.stderr
    assert (folder / "a.md").read_text() == "a by agent\n"
    assert (folder / "new.md").read_text() == "new\n"
    assert (folder / "b.md").read_text() == "b by user\n"
    assert (folder / "b.md.murmur-run1").read_text() == "b by agent\n"
    assert "b.md" in result.stderr
