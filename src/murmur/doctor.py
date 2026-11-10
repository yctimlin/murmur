"""Preflight checks: is this machine ready for a murmur run?

Each check returns ok, warn, fail or skip, with a fix hint for anything that is not ok.
Only `fail` makes `murmur doctor` exit non-zero: a warning means murmur still works, more
slowly or with less headroom. The auth check only looks at whether a credential exists;
it never opens auth.json or reads a key's value.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path

from murmur.cow import CowCopyError, cow_copy

MIN_CODEX = (0, 162, 0)
VERSION_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)")
SWARM_FEATURES = ("agent_message_board", "multi_agent_v2")
API_KEY_VARS = ("CODEX_API_KEY", "OPENAI_API_KEY")
LOW_DISK_BYTES = 2 * 1024**3
TIMEOUT_S = 60


@dataclass
class Check:
    name: str
    status: str  # ok | warn | fail | skip
    detail: str
    hint: str = ""


def _run(argv: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(argv, capture_output=True, text=True, check=False, timeout=TIMEOUT_S, **kwargs)


def _last_line(result: subprocess.CompletedProcess) -> str:
    lines = (result.stderr or result.stdout or "").strip().splitlines()
    return lines[-1] if lines else f"exit {result.returncode}"


def _version(parts: tuple[int, ...]) -> str:
    return ".".join(map(str, parts))


def check_codex() -> Check:
    hint = f"install Codex CLI {_version(MIN_CODEX)} or later: npm install -g @openai/codex"
    if not shutil.which("codex"):
        return Check("codex", "fail", "the `codex` CLI is not on PATH", hint)
    try:
        result = _run(["codex", "--version"])
    except (OSError, subprocess.TimeoutExpired) as error:
        return Check("codex", "fail", f"`codex --version` failed: {error}", hint)
    found = VERSION_RE.search(result.stdout) if result.returncode == 0 else None
    if not found:
        return Check("codex", "fail", f"`codex --version` gave no version ({_last_line(result)})", hint)
    version = tuple(int(part) for part in found.groups())
    label = result.stdout.strip().splitlines()[0]
    if version < MIN_CODEX:
        return Check("codex", "fail", f"{label} is older than {_version(MIN_CODEX)}",
                     hint.replace("install", "upgrade to", 1))
    return Check("codex", "ok", f"{label} (needs {_version(MIN_CODEX)}+)")


def check_model(model: str) -> Check:
    hint = "pick a slug from `codex debug models` and pass it with --model (or `model` in --config)"
    try:
        result = _run(["codex", "debug", "models"])
    except (OSError, subprocess.TimeoutExpired) as error:
        return Check("model", "fail", f"`codex debug models` failed: {error}", hint)
    if result.returncode != 0:
        return Check("model", "fail", f"`codex debug models` failed: {_last_line(result)}", hint)
    try:
        catalog = json.loads(result.stdout)
    except json.JSONDecodeError:
        return Check("model", "fail", "`codex debug models` did not print JSON", hint)
    models = catalog.get("models") if isinstance(catalog, dict) else None
    if not isinstance(models, list) or not models:
        return Check("model", "fail", "`codex debug models` returned no models",
                     "check your model provider with `codex exec --ephemeral --skip-git-repo-check 'Reply with OK'`")
    slugs = [entry.get("slug") for entry in models if isinstance(entry, dict) and entry.get("slug")]
    if model not in slugs:
        shown = ", ".join(slugs[:10]) + (", ..." if len(slugs) > 10 else "")
        return Check("model", "fail", f"{model} is not in `codex debug models` (it has: {shown})", hint)
    return Check("model", "ok", f"{model} is in `codex debug models`")


def check_features() -> Check:
    hint = (f"upgrade Codex to {_version(MIN_CODEX)} or later; a swarm needs "
            f"{' and '.join(SWARM_FEATURES)} (--solo does not)")
    try:
        result = _run(["codex", "features", "list"])
    except (OSError, subprocess.TimeoutExpired) as error:
        return Check("features", "fail", f"`codex features list` failed: {error}", hint)
    if result.returncode != 0:
        return Check("features", "fail", f"`codex features list` failed: {_last_line(result)}", hint)
    stages = {}
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            stages[parts[0]] = " ".join(parts[1:-1]) or parts[1]
    missing = [name for name in SWARM_FEATURES if name not in stages or stages[name] == "removed"]
    if missing:
        return Check("features", "fail", f"this Codex lacks {', '.join(missing)}", hint)
    return Check("features", "ok", f"{', '.join(SWARM_FEATURES)} available")


def check_git(repo: Path) -> Check:
    if not shutil.which("git"):
        return Check("git", "fail", "git is not on PATH", "install git")
    version = _run(["git", "--version"]).stdout.strip()
    if not repo.is_dir():
        return Check("git", "fail", f"{version}; {repo} is not a directory",
                     "pass an existing git repository or folder with --repo")
    top = _run(["git", "rev-parse", "--show-toplevel"], cwd=repo)
    if top.returncode != 0:
        if (repo / ".git").exists():
            return Check("git", "fail", f"{version}; {repo} has a .git but is not a usable git repository",
                         f"repair it (try `git -C {repo} status`) or remove the broken .git")
        return Check("git", "ok", f"{version}; {repo} is a plain folder, murmur will snapshot it")
    head = _run(["git", "rev-parse", "--short", "--verify", "HEAD^{commit}"], cwd=repo)
    if head.returncode != 0:
        return Check("git", "fail", f"{version}; {top.stdout.strip()} has no commits",
                     "commit something first, or pass --base with a commit")
    return Check("git", "ok", f"{version}; {top.stdout.strip()} at {head.stdout.strip()}")


def _existing(path: Path) -> Path:
    while not path.exists() and path != path.parent:
        path = path.parent
    return path


def check_reflink(into: Path) -> Check:
    """Try one copy-on-write copy where workspaces will be created."""
    where = _existing(into)
    if not where.is_dir() or not os.access(where, os.W_OK):
        return Check("reflink", "fail", f"cannot create workspaces under {into}: {where} is not writable",
                     "pass a writable --into directory")
    try:
        scratch = Path(tempfile.mkdtemp(prefix=".murmur-doctor-", dir=where))
    except OSError as error:
        return Check("reflink", "fail", f"cannot write in {where}: {error}", "pass a writable --into directory")
    try:
        (scratch / "src").mkdir()
        (scratch / "src" / "probe").write_bytes(b"murmur" * 1024)
        cow_copy(scratch / "src", scratch / "dst")
    except (CowCopyError, OSError) as error:
        reason = str(error).rsplit(": ", 1)[-1]  # cp's message repeats the scratch paths
        return Check("reflink", "warn", f"{where} does not support copy-on-write copies ({reason})",
                     "murmur falls back to running --setup in every clone in parallel; for one setup "
                     "and instant copies, put --into on APFS (macOS) or btrfs/xfs (Linux)")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    return Check("reflink", "ok", f"{where} supports copy-on-write copies")


def check_disk(into: Path) -> Check:
    where = _existing(into)
    try:
        free = shutil.disk_usage(where).free
    except OSError as error:
        return Check("disk", "warn", f"cannot read free space at {where}: {error}")
    detail = f"{free / 1024**3:.1f} GB free at {where}"
    if free < LOW_DISK_BYTES:
        return Check("disk", "warn", detail,
                     "each agent gets its own clone and installed tree; free some space or pick another --into")
    return Check("disk", "ok", detail)


def check_auth(codex_home: Path) -> Check:
    """Is there a credential Codex can use? Looks at existence only, never at a value."""
    if (codex_home / "auth.json").exists():
        return Check("auth", "ok", f"{codex_home / 'auth.json'} exists")
    config_file = codex_home / "config.toml"
    try:
        config = tomllib.loads(config_file.read_text()) if config_file.exists() else {}
    except (OSError, tomllib.TOMLDecodeError):
        config = {}
    provider = config.get("model_provider")
    table = config.get("model_providers", {}).get(provider) if provider else None
    if isinstance(table, dict):
        env_key = table.get("env_key")
        if isinstance(env_key, str) and env_key:
            if os.environ.get(env_key):
                return Check("auth", "ok", f"provider {provider}: ${env_key} is set")
            return Check("auth", "fail", f"provider {provider} needs ${env_key}, which is not set",
                         f"export {env_key} before running murmur")
        if table.get("requires_openai_auth") is not True:
            return Check("auth", "ok", f"provider {provider} does not use a Codex login")
    elif provider and provider != "openai":
        return Check("auth", "warn", f"provider {provider} is built in; murmur cannot check its login",
                     "check it with `codex exec --ephemeral --skip-git-repo-check 'Reply with OK'`")
    for name in API_KEY_VARS:
        if os.environ.get(name):
            return Check("auth", "ok", f"${name} is set")
    return Check("auth", "fail", f"no Codex login: {codex_home / 'auth.json'} does not exist",
                 "run `codex login`")


def run_checks(*, model: str, repo: Path, into: Path, codex_home: Path, solo: bool) -> list[Check]:
    codex = check_codex()
    checks = [codex]
    if codex.status == "ok":
        checks.append(check_model(model))
        if not solo:
            checks.append(check_features())
    else:
        checks.append(Check("model", "skip", "needs a working codex"))
        if not solo:
            checks.append(Check("features", "skip", "needs a working codex"))
    checks += [check_git(repo), check_reflink(into), check_disk(into), check_auth(codex_home)]
    return checks


def preflight(codex_home: Path) -> Check | None:
    """The quick checks `murmur run` makes before it starts: the first failure, if any."""
    git = Check("git", "ok", "") if shutil.which("git") else Check("git", "fail", "git is not on PATH", "install git")
    for check in (check_codex(), git, check_auth(codex_home)):
        if check.status == "fail":
            return check
    return None


def report(checks: list[Check]) -> list[str]:
    lines = []
    for check in checks:
        lines.append(f"{check.status:<5} {check.name:<9} {check.detail}")
        if check.hint and check.status != "ok":
            lines.append(f"{'':<15} fix: {check.hint}")
    counts = {status: sum(check.status == status for check in checks) for status in ("ok", "warn", "fail")}
    lines.append(f"murmur doctor: {counts['ok']} ok, {counts['warn']} warning(s), {counts['fail']} failed")
    return lines
