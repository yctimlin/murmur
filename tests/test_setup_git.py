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


def _folder_run(tmp_path: Path, max_mb: str = "50", build=None) -> tuple[Path, Path, Path]:
    folder = tmp_path / "docs"
    folder.mkdir()
    (folder / "a.md").write_text("a\n")
    (folder / "b.md").write_text("b\n")
    (folder / "big.bin").write_bytes(b"x" * 2_000_000)
    if build:
        build(folder)
    brief = tmp_path / "brief.md"
    brief.write_text("Do the thing.\n")
    result = run_cli(
        "setup", str(brief), "--repo", str(folder), "--into", str(tmp_path / "runs"),
        "--id", "run1", "--cap", "30s", "--solo", "--max-file-mb", max_mb,
    )
    assert result.returncode == 0, result.stderr
    ws = Path(result.stdout.strip().splitlines()[-1])
    return folder, ws, ws / "work" / "repo"


def _agent_work(clone: Path) -> None:
    (clone / "a.md").write_text("a by agent\n")
    (clone / "new.md").write_text("new\n")
    git(clone, "rm", "-q", "b.md")
    (clone / ".work").mkdir()
    (clone / ".work" / "notes.md").write_text("scratch\n")
    git(clone, "add", "-A")
    git(clone, "commit", "-q", "-m", "work")
    git(clone, "push", "-q", "origin", "HEAD:main")


def test_result_goes_to_a_new_sibling_folder(tmp_path: Path):
    from murmur.cli import write_result

    folder, ws, clone = _folder_run(tmp_path, max_mb="1")
    assert (clone / "big.bin").is_symlink()
    assert (clone / "big.bin").stat().st_size == 2_000_000
    _agent_work(clone)
    before = sorted(p.name for p in folder.iterdir())
    out = write_result(ws)
    assert out == tmp_path / "docs.murmur-run1"
    assert (out / "big.bin").read_bytes() == b"x" * 2_000_000 and not (out / "big.bin").is_symlink()
    assert (out / "a.md").read_text() == "a by agent\n" and (out / "new.md").read_text() == "new\n"
    assert not (out / "b.md").exists() and not (out / ".work").exists()
    assert sorted(p.name for p in folder.iterdir()) == before
    assert (folder / "a.md").read_text() == "a\n"


def test_exec_bits_and_symlinks_survive(tmp_path: Path):
    from murmur.cli import write_result

    def build(folder: Path) -> None:
        (folder / "run.sh").write_text("#!/bin/sh\n")
        (folder / "run.sh").chmod(0o755)
        (folder / "link.md").symlink_to("a.md")

    _, ws, clone = _folder_run(tmp_path, build=build)
    assert (clone / "run.sh").stat().st_mode & 0o111
    assert (clone / "link.md").is_symlink() and str((clone / "link.md").readlink()) == "a.md"
    _agent_work(clone)
    out = write_result(ws)
    assert (out / "run.sh").stat().st_mode & 0o111 and not (out / "a.md").stat().st_mode & 0o111
    assert (out / "link.md").is_symlink() and str((out / "link.md").readlink()) == "a.md"


def test_nested_repo_files_come_in_as_plain_files(tmp_path: Path):
    def build(folder: Path) -> None:
        sub = folder / "sub"
        sub.mkdir()
        git(sub, "init", "-q")
        (sub / "tracked.py").write_text("x = 1\n")
        git(sub, "add", "tracked.py")
        git(sub, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "s")
        (sub / "untracked.py").write_text("y = 2\n")

    _, _, clone = _folder_run(tmp_path, build=build)
    assert (clone / "sub" / "tracked.py").read_text() == "x = 1\n"
    assert (clone / "sub" / "untracked.py").read_text() == "y = 2\n"
    assert not (clone / "sub" / ".git").exists()
    assert "160000" not in git(clone, "ls-tree", "-r", "HEAD")


def test_ignored_files_are_left_out(tmp_path: Path):
    def build(folder: Path) -> None:
        (folder / ".gitignore").write_text("node_modules/\n*.log\n")
        (folder / "node_modules").mkdir()
        (folder / "node_modules" / "huge.bin").write_bytes(b"y" * 2_000_000)
        (folder / "debug.log").write_text("noise\n")

    _, ws, clone = _folder_run(tmp_path, max_mb="1", build=build)
    assert not (clone / "node_modules").exists() and not (clone / "debug.log").exists()
    assert (clone / ".gitignore").exists()
    shared = ws / "work" / "shared"
    assert sorted(p.name for p in shared.rglob("*") if p.is_file()) == ["big.bin"]
