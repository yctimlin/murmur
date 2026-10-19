"""murmur: run a leaderless swarm of Codex agents on one objective.

  murmur setup BRIEF [--repo DIR] [--peers N | --solo] [--setup CMD]... [options]
  murmur run WORKSPACE

`setup` builds an isolated workspace for one run. Setup commands run once in the
first clone; the other clones are copy-on-write copies of that tree. `run`
launches Codex and stops its whole process group on the way out.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shlex
import signal
import shutil
import subprocess
import sys
import threading
import time
import tomllib
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path
from string import Template

from murmur.cow import CowCopyError, cow_copy
from murmur.procutil import (
    install_interrupt_handlers,
    restore_interrupt_handlers,
    stop_process_group,
)

EXIT_OK = 0
EXIT_CODEX_FAILED = 1
EXIT_CAPPED = 124
EXIT_LAUNCHER = 3
EXIT_NO_WORK = 4
EXIT_INTERRUPTED = 130

DURATION_RE = re.compile(r"^(\d+)([smh])$")
ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
DEFAULTS = {
    "peers": 4,
    "model": "gpt-6-astra",
    "effort": "high",
    "cap": "3h",
    "port_base": 40000,
    "port_stride": 100,
    "setup": [],
    "setup_per_agent": False,
    "agent_env": {},
    "max_file_mb": 50,
}

# Agents get network access but no way to reach GitHub through git: no credential
# helper, and these GitHub URL prefixes are rewritten to a path that does not exist.
GITCONFIG = """\
[init]
\tdefaultBranch = main
[credential]
\thelper =
[url "file:///nonexistent/github-is-blocked/"]
\tinsteadOf = https://github.com/
\tinsteadOf = git@github.com:
\tinsteadOf = ssh://git@github.com/
"""


def fail(message: str) -> None:
    print(f"murmur: {message}", file=sys.stderr)
    raise SystemExit(EXIT_LAUNCHER)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def seconds(duration: str) -> int:
    match = DURATION_RE.match(duration)
    if not match:
        fail(f"bad duration {duration!r} (use e.g. 45m or 3h)")
    return int(match[1]) * {"s": 1, "m": 60, "h": 3600}[match[2]]

# Codex caps `features.multi_agent_v2.max_wait_timeout_ms` at one hour.
ROOT_WAIT_MS = 3_600_000


def git(*args: str, cwd: Path | None = None, env: dict | None = None) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, env=env, check=False, capture_output=True, text=True
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "git failed").strip()
        fail(detail.splitlines()[-1] if detail else "git failed")
    return result.stdout.strip()


def toml_value(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, list):
        return "[" + ", ".join(toml_value(item) for item in value) + "]"
    if isinstance(value, dict):
        pairs = (f"{json.dumps(key)} = {toml_value(item)}" for key, item in value.items())
        return "{" + ", ".join(pairs) + "}"
    raise TypeError(f"cannot write {type(value).__name__} as TOML")


class _SetupProcs:
    def __init__(self) -> None:
        self._procs: list[subprocess.Popen] = []
        self._lock = threading.Lock()

    def add(self, proc: subprocess.Popen) -> None:
        with self._lock:
            self._procs.append(proc)

    def discard(self, proc: subprocess.Popen) -> None:
        with self._lock:
            self._procs = [item for item in self._procs if item is not proc]

    def stop_all(self) -> None:
        with self._lock:
            procs = list(self._procs)
        for proc in procs:
            stop_process_group(proc)


def user_codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()


def write_model_catalog(path: Path, model: str, effort: str, solo: bool) -> None:
    """Pin how the model catalog treats sub-agents.

    The bundled catalog forces Multi-Agent V2 on for some models regardless of
    `--disable` flags (openai/codex#50880), and spawns sub-agents at its own reasoning
    effort. So a solo run gets no agent tools, and swarm peers think at the run's effort.

    A swarm also enables the agent message board. Codex reads `tool_mode` from this
    catalog and, when it is null, falls back to Direct mode, which sends the board
    tools as `collaboration.*` functions. Backends reject those names. `code_mode_only`
    leaves the model with `exec`, and the board tools are called from inside it. An
    explicit catalog value is left alone. Solo runs do not use the board.
    """
    out = subprocess.run(["codex", "debug", "models"], check=True, capture_output=True, text=True)
    catalog = json.loads(out.stdout)
    models = catalog.get("models") if isinstance(catalog, dict) else None
    if not isinstance(models, list) or not models:
        fail("`codex debug models` returned no models; refusing to write an empty model catalog")
    for entry in models:
        if solo:
            entry["multi_agent_version"] = None
        elif entry.get("slug") == model:
            entry["multi_agent_reasoning_effort"] = effort
            if entry.get("tool_mode") is None:
                entry["tool_mode"] = "code_mode_only"
    path.write_text(json.dumps(catalog, indent=2) + "\n")


def write_codex_home(home: Path, trusted: Path, catalog: Path) -> None:
    """A minimal CODEX_HOME that carries over only the user's model provider and auth."""
    source = user_codex_home()
    config_file = source / "config.toml"
    user = tomllib.loads(config_file.read_text()) if config_file.exists() else {}
    provider = user.get("model_provider")
    lines = [f"model_catalog_json = {toml_value(str(catalog))}"]
    if provider:
        lines.append(f"model_provider = {toml_value(provider)}")
    lines += ["", "[features]", "memories = false", ""]
    if provider in user.get("model_providers", {}):
        lines.append(f"[model_providers.{toml_value(provider)}]")
        lines += [f"{key} = {toml_value(value)}" for key, value in user["model_providers"][provider].items()]
        lines.append("")
    lines += [f"[projects.{toml_value(str(trusted))}]", 'trust_level = "trusted"', ""]
    config = home / "config.toml"
    config.write_text("\n".join(lines))
    config.chmod(0o600)
    auth = source / "auth.json"
    if auth.exists():
        (home / "auth.json").symlink_to(auth)


def render(name: str, **values: str) -> str:
    text = files("murmur").joinpath("prompts", name).read_text()
    return Template(text).substitute(values).strip()


def env_block(env: dict[str, str]) -> str:
    pairs = ", ".join(f"`{key}={value}`" for key, value in env.items())
    return (
        f"Your environment values: {pairs}. "
        "Shells started in this clone export them. "
        "Commands that start outside this clone, including in `work/`, do not: "
        "export them in those commands."
    )


def git_env(ws: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["GIT_CONFIG_GLOBAL"] = str(ws / "gitconfig")
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    return env


def shell_env(ws: Path) -> dict[str, str]:
    """What Codex injects into agent shells.

    ZDOTDIR is an empty directory plus murmur's `.zshenv`, so login zsh does not
    read the user's dotfiles. HOME is left alone: pnpm and other tools need the
    real home. Per-agent ports are not in this dict; one session cannot hold
    every peer's PORT_BASE. `.zshenv` loads the clone's `.murmur/env.sh` instead.
    """
    return {
        "GIT_CONFIG_GLOBAL": str(ws / "gitconfig"),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GH_CONFIG_DIR": str(ws / "gh"),
        "ZDOTDIR": str(ws / "zdot"),
    }


def write_zshenv(ws: Path) -> None:
    root = shlex.quote(str(ws))
    # pwd -P so a symlink such as /tmp -> /private/tmp still matches the workspace path.
    (ws / "zdot" / ".zshenv").write_text(
        f"""# Generated by murmur. Login zsh reads this because ZDOTDIR points here.
_murmur_root=$(CDPATH= cd {root} && pwd -P)
_murmur_dir=$(pwd -P)
case "$_murmur_dir" in
  "$_murmur_root"|"$_murmur_root"/*)
    while :; do
      if [ -f "$_murmur_dir/.murmur/env.sh" ]; then
        . "$_murmur_dir/.murmur/env.sh"
        break
      fi
      if [ "$_murmur_dir" = "$_murmur_root" ] || [ "$_murmur_dir" = / ]; then
        break
      fi
      _murmur_dir=$(dirname "$_murmur_dir")
    done
    ;;
esac
unset _murmur_dir _murmur_root
"""
    )


def write_env_sh(clone: Path, env: dict[str, str]) -> None:
    lines = ["# Generated by murmur. Sourced for shells started in this clone.", ""]
    for key, value in env.items():
        if not ENV_NAME.fullmatch(key):
            fail(f"invalid environment variable name {key!r}")
        lines.append(f"export {key}={shlex.quote(str(value))}")
    lines.append("")
    path = clone / ".murmur" / "env.sh"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))


def _as_string_list(value, name: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str) or not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        fail(f"{name} must be a list of strings")
    return list(value)


def resolve_options(args: argparse.Namespace) -> dict:
    """Defaults, then the optional config file, then flags."""
    options = dict(DEFAULTS)
    if args.config:
        config_path = Path(args.config).expanduser().resolve()
        config = tomllib.loads(config_path.read_text())
        for key in ("repo", "brief"):
            if key in config:
                config[key] = str((config_path.parent / str(config[key])).resolve())
        options |= config
    flags = {
        "brief": args.brief,
        "repo": args.repo,
        "base": args.base,
        "peers": args.peers,
        "model": args.model,
        "effort": args.effort,
        "cap": args.cap,
        "port_base": args.port_base,
        "max_file_mb": getattr(args, "max_file_mb", None),
        "setup": args.setup or None,
    }
    options |= {key: value for key, value in flags.items() if value is not None}
    if args.solo:
        options["peers"] = 1
    elif not isinstance(options["peers"], int) or isinstance(options["peers"], bool) or options["peers"] < 2:
        fail("a swarm needs at least 2 peers; use --solo for a single agent")
    if args.setup_per_agent:
        options["setup_per_agent"] = True
    elif not isinstance(options["setup_per_agent"], bool):
        fail("setup_per_agent must be a boolean")
    options["setup"] = _as_string_list(options.get("setup"), "setup")
    agent_env = options.get("agent_env") or {}
    if not isinstance(agent_env, dict):
        fail("agent_env must be a table of string templates")
    options["agent_env"] = agent_env
    if not options.get("brief"):
        fail("give a brief file (or a config with `brief`)")
    if not isinstance(options["cap"], str):
        fail("cap must be a duration string such as 45m or 3h")
    seconds(options["cap"])
    if not isinstance(options["port_base"], int) or isinstance(options["port_base"], bool):
        fail("port_base must be an integer")
    if not isinstance(options["port_stride"], int) or isinstance(options["port_stride"], bool):
        fail("port_stride must be an integer")
    return options


def _run_setup_command(command: str, cwd: Path, env: dict[str, str], procs: _SetupProcs) -> None:
    label = env.get("MURMUR_AGENT", "setup")
    print(f"murmur: [{label}] {command}", file=sys.stderr)
    proc = subprocess.Popen(command, shell=True, cwd=cwd, env=env, start_new_session=True)
    procs.add(proc)
    try:
        returncode = proc.wait()
    except KeyboardInterrupt:
        stop_process_group(proc)
        raise
    finally:
        if proc.poll() is None:
            stop_process_group(proc)
        procs.discard(proc)
    if returncode != 0:
        fail(f"setup command failed ({returncode}): {command}")


def _configure_clone(
    clone: Path, agent_id: str, origin: Path, env: dict[str, str], template: Path | None = None
) -> None:
    git("config", "user.name", agent_id, cwd=clone, env=env)
    git("config", "user.email", f"{agent_id}@murmur.local", cwd=clone, env=env)
    git("remote", "set-url", "origin", str(origin), cwd=clone, env=env)
    exclude = clone / ".git" / "info" / "exclude"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    current = exclude.read_text() if exclude.exists() else ""
    if ".murmur/" not in current:
        exclude.write_text(current + ("" if not current or current.endswith("\n") else "\n") + ".murmur/\n")
    if template is None:
        return
    config = clone / ".git" / "config"
    if config.is_file():
        text = config.read_text()
        old = str(template)
        if old in text:
            config.write_text(text.replace(old, str(clone)))


def _agent_env(options: dict, run_id: str, agent_id: str, index: int) -> dict[str, str]:
    port_base = str(options["port_base"] + index * options["port_stride"])
    values = {"run": run_id, "agent": agent_id, "index": str(index), "port_base": port_base}
    env = {"PORT_BASE": port_base, "MURMUR_AGENT": agent_id}
    for key, template in options["agent_env"].items():
        if not isinstance(key, str) or not isinstance(template, str):
            fail("agent_env keys and values must be strings")
        env[key] = Template(template).substitute(values)
    return env


def _prepare_clones(ws: Path, origin: Path, options: dict, run_id: str, ids: list[str], procs: _SetupProcs):
    isolated = git_env(ws)
    work = ws / "work"
    clones = []
    for index, agent_id in enumerate(ids):
        dest = work / ("repo" if len(ids) == 1 else f"peers/{agent_id}")
        clones.append((index, agent_id, dest))

    first_index, first_id, first = clones[0]
    git("clone", "-q", str(origin), str(first), env=isolated)
    _configure_clone(first, first_id, origin, isolated)
    per_agent = len(ids) == 1 or options["setup_per_agent"]

    def installed(index: int, agent_id: str, dest: Path, *, clone: bool) -> dict:
        if clone:
            git("clone", "-q", str(origin), str(dest), env=isolated)
            _configure_clone(dest, agent_id, origin, isolated)
        agent = {"id": agent_id, "clone": str(dest), "env": _agent_env(options, run_id, agent_id, index)}
        setup_env = dict(isolated)
        setup_env.update(agent["env"])
        for command in options["setup"]:
            _run_setup_command(command, dest, setup_env, procs)
        return agent

    if per_agent:
        if options["setup_per_agent"] and len(ids) > 1:
            print("murmur: running setup in each clone (--setup-per-agent)", file=sys.stderr)
        agents = [installed(index, agent_id, dest, clone=dest != first) for index, agent_id, dest in clones]
        return agents, "solo" if len(ids) == 1 else "per-agent"

    print(f"murmur: running setup once in {first_id}", file=sys.stderr)
    for command in options["setup"]:
        _run_setup_command(command, first, isolated, procs)
    agents = [{"id": first_id, "clone": str(first), "env": _agent_env(options, run_id, first_id, first_index)}]
    copied: list[Path] = []
    try:
        for index, agent_id, dest in clones[1:]:
            cow_copy(first, dest)
            copied.append(dest)
            _configure_clone(dest, agent_id, origin, isolated, template=first)
            agents.append({"id": agent_id, "clone": str(dest), "env": _agent_env(options, run_id, agent_id, index)})
    except CowCopyError as exc:
        print(
            f"murmur: copy-on-write clone failed ({exc}); "
            "running setup in the remaining clones in parallel",
            file=sys.stderr,
        )
        for dest in copied:
            shutil.rmtree(dest, ignore_errors=True)
        jobs = []
        for index, agent_id, dest in clones[1:]:
            if dest.exists():
                shutil.rmtree(dest)

            def job(index=index, agent_id=agent_id, dest=dest):
                git("clone", "-q", str(origin), str(dest), env=isolated)
                _configure_clone(dest, agent_id, origin, isolated)
                for command in options["setup"]:
                    _run_setup_command(command, dest, isolated, procs)
                return {"id": agent_id, "clone": str(dest), "env": _agent_env(options, run_id, agent_id, index)}

            jobs.append(job)
        rest = []
        if jobs:
            with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
                futures = [pool.submit(job) for job in jobs]
                try:
                    for future in as_completed(futures):
                        rest.append(future.result())
                except BaseException:
                    procs.stop_all()
                    raise
        order = {agent_id: index for index, agent_id, _dest in clones}
        rest.sort(key=lambda item: order[item["id"]])
        return [agents[0], *rest], "parallel-fallback"

    names = ", ".join(agent["id"] for agent in agents[1:])
    print(f"murmur: copy-on-write cloned {names} from {first_id}", file=sys.stderr)
    return agents, "cow"


def in_git_repo(path: Path) -> bool:
    found = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], cwd=path if path.is_dir() else path.parent,
        capture_output=True, text=True, check=False,
    )
    return found.returncode == 0


def _folder_files(folder: Path, env: dict, prefix: str = "") -> list[str]:
    """Paths under `folder` that git would add, honouring .gitignore and the standard excludes.

    `env` points GIT_DIR at a scratch repo whose work tree is `folder`, or has no GIT_DIR when
    `folder` is itself a nested repository. A nested repository (listed by git as `sub/`) is
    expanded into its own tracked and untracked files, without its .git, so it comes in as
    normal files rather than an empty submodule pointer.
    """
    listed = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                            cwd=folder, env=env, capture_output=True, check=True)
    nested = {k: v for k, v in env.items() if k not in ("GIT_DIR", "GIT_WORK_TREE")}
    files: list[str] = []
    for rel in filter(None, listed.stdout.decode().split("\0")):
        if rel.endswith("/"):
            files += _folder_files(folder / rel, nested, f"{prefix}{rel}")
        elif not (folder / rel).is_dir() or (folder / rel).is_symlink():
            files.append(f"{prefix}{rel}")
    return files


def _hash_bytes(data: bytes, repo: Path, env: dict) -> str:
    return subprocess.run(["git", "hash-object", "-w", "--stdin"], input=data, cwd=repo, env=env,
                          capture_output=True, check=True).stdout.decode().strip()


def _user_excludes() -> str | None:
    """The user's global ignore file (core.excludesFile, else git's XDG default), if any."""
    found = subprocess.run(["git", "config", "--global", "--path", "core.excludesFile"],
                           capture_output=True, text=True, check=False).stdout.strip()
    xdg = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "git" / "ignore"
    path = Path(found).expanduser() if found else xdg
    return str(path) if path.is_file() else None


def snapshot_folder(folder: Path, dest: Path, env: dict, max_mb: float) -> tuple[Path, str]:
    """Commit a plain folder into a new one-commit repo at `dest`, without writing to it.

    Files git would ignore (.gitignore, info/exclude) are left out. Executable bits and
    symlinks are kept. Nested git repositories come in as plain files. Files over `max_mb`
    stay out of git: one read-only copy goes to `shared/` next to `work/` and the snapshot
    commits a symlink to it, so every clone sees the file without another copy.
    """
    if (folder / ".git").exists():
        fail(f"{folder} has a .git but is not a usable git repository")
    shared = dest.parent / "shared"
    limit = max_mb * 1024 * 1024
    git("init", "-q", str(dest), env=env)
    probe = {k: v for k, v in env.items() if k not in ("GIT_DIR", "GIT_WORK_TREE")}
    # List from inside a throwaway git dir whose work tree is the folder, so ignore rules apply.
    probe |= {"GIT_DIR": str(dest / ".git"), "GIT_WORK_TREE": str(folder)}
    if excludes := _user_excludes():  # murmur's isolated config hides the user's global one
        probe |= {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "core.excludesFile",
                  "GIT_CONFIG_VALUE_0": excludes}
    files = sorted(_folder_files(folder, probe))
    big, entries, plain = [], [], []
    for rel in files:
        path = folder / rel
        if path.is_symlink():
            entries.append(("120000", _hash_bytes(os.readlink(path).encode(), dest, env), rel))
        elif path.stat().st_size > limit:
            target = shared / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            target.chmod(0o444)
            big.append(rel)
            entries.append(("120000", _hash_bytes(str(target).encode(), dest, env), rel))
        else:
            plain.append(rel)
    # One process hashes every regular file; one per file is ~50x slower on large trees.
    hashed = subprocess.run(
        ["git", "hash-object", "-w", "--no-filters", "--stdin-paths"], cwd=dest, env=env,
        input="".join(f"{folder / rel}\n" for rel in plain).encode(), capture_output=True,
        check=True).stdout.decode().split()
    for rel, sha in zip(plain, hashed, strict=True):
        mode = "100755" if os.access(folder / rel, os.X_OK) else "100644"
        entries.append((mode, sha, rel))
    entries = [f"{mode} {sha}\t{rel}" for mode, sha, rel in entries]
    subprocess.run(["git", "update-index", "--add", "-z", "--index-info"], cwd=dest, env=env,
                   input="".join(e + "\0" for e in entries).encode(), check=True)
    note = f" ({len(big)} large file(s) linked read-only from shared/)" if big else ""
    git("-c", "user.name=murmur", "-c", "user.email=murmur@murmur.local",
        "commit", "-q", "--allow-empty", "-m", f"Snapshot of {folder}{note}", cwd=dest, env=env)
    if big:
        print(f"murmur: kept {len(big)} file(s) over {max_mb:g} MB out of git: {', '.join(big)}",
              file=sys.stderr)
    return dest, git("rev-parse", "HEAD", cwd=dest, env=env)


# Agents keep scratch notes here (closing.md); they are not part of the result.
SCRATCH = ".work/"


def write_result(ws: Path) -> Path | None:
    """Write a plain-folder run's result to a new sibling folder; the source is never touched.

    The folder is filled under a temporary name and renamed at the end, so a failure leaves no
    partial result.
    """
    meta = json.loads((ws / "murmur.json").read_text())
    if not meta.get("folder"):
        return None
    out = Path(f"{meta['folder']}.murmur-{ws.name}")
    if out.exists():
        print(f"murmur: {out} already exists; not overwriting it", file=sys.stderr)
        return out
    tmp = out.with_name(f".{out.name}.partial")
    shutil.rmtree(tmp, ignore_errors=True)
    try:
        count = _fill_result(ws, tmp)
        tmp.rename(out)
    except (OSError, subprocess.CalledProcessError, SystemExit) as error:
        shutil.rmtree(tmp, ignore_errors=True)
        print(f"murmur: could not write the result to {out}: {error}", file=sys.stderr)
        print(f"murmur: the result is still in {ws / 'work' / 'origin.git'} (branch main)",
              file=sys.stderr)
        return None
    print(f"murmur: wrote {count} file(s) to {out}")
    return out


def _fill_result(ws: Path, out: Path) -> int:
    origin, shared = ws / "work" / "origin.git", (ws / "work" / "shared").resolve()
    env = git_env(ws)
    listing = git("ls-tree", "-r", "-z", "main", cwd=origin, env=env)
    out.mkdir(parents=True)
    count = 0
    for entry in filter(None, listing.split("\0")):
        info, path = entry.split("\t", 1)
        mode, kind, sha = info.split()
        if kind != "blob" or path.startswith(SCRATCH):
            continue  # submodule pointers agents may add have no content to write
        data = subprocess.run(["git", "cat-file", "blob", sha], cwd=origin, env=env,
                              capture_output=True, check=True).stdout
        dest = out / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        if mode == "120000":
            target = Path(data.decode())
            real = (dest.parent / target).resolve()
            if real.is_relative_to(shared) and real.is_file():
                shutil.copyfile(real, dest)  # fill large-file links in with the real file
                dest.chmod(0o644)
            else:
                dest.symlink_to(target)
        else:
            dest.write_bytes(data)
            dest.chmod(0o755 if mode == "100755" else 0o644)
        count += 1
    return count


def setup(args: argparse.Namespace) -> None:
    if not shutil.which("codex"):
        fail("the `codex` CLI is not on PATH")
    options = resolve_options(args)
    solo = options["peers"] == 1
    brief_file = Path(options["brief"]).expanduser().resolve()
    start = Path(options.get("repo") or ".").expanduser().resolve()
    folder = None if in_git_repo(start) else start
    if folder is not None and (not folder.is_dir() or options.get("base")):
        fail(f"{start} is not a git repository" + (" (--base needs one)" if folder.is_dir() else ""))
    repo = start if folder else Path(git("rev-parse", "--show-toplevel", cwd=start))
    base_ref = options.get("base") or "HEAD"
    base = "" if folder else git("rev-parse", "--verify", f"{base_ref}^{{commit}}", cwd=repo)
    if not folder and base_ref == "HEAD" and git("status", "--porcelain", cwd=repo):
        print(
            f"murmur: {repo} has uncommitted changes; agents start from {base[:10]} without them",
            file=sys.stderr,
        )
    ids = ["solo"] if solo else [f"a{i}" for i in range(1, options["peers"] + 1)]
    run_id = args.id or secrets.token_hex(4)
    ws = Path(args.into).expanduser().resolve() / run_id
    if ws.exists():
        fail(f"{ws} already exists")

    previous = install_interrupt_handlers()
    procs = _SetupProcs()
    published = False
    try:
        work = ws / "work"
        home = ws / "codex-home"
        for directory in (ws / "logs", ws / "prompts", ws / "gh", ws / "zdot", work, home):
            directory.mkdir(parents=True)
        (ws / "gitconfig").write_text(GITCONFIG)
        write_zshenv(ws)
        write_model_catalog(home / "models.json", options["model"], options["effort"], solo)
        write_codex_home(home, work, home / "models.json")
        isolated = git_env(ws)
        if folder:
            repo, base = snapshot_folder(folder, work / "input", isolated, options["max_file_mb"])
        origin = work / "origin.git"
        git("init", "-q", "--bare", str(origin), env=isolated)
        git("config", "receive.denyNonFastForwards", "true", cwd=origin, env=isolated)
        git("config", "receive.denyDeletes", "true", cwd=origin, env=isolated)
        git("config", "core.logAllRefUpdates", "always", cwd=origin, env=isolated)
        git("fetch", "-q", "--no-tags", str(repo), f"{base}:refs/heads/main", cwd=origin, env=isolated)
        # Tags reachable from base, so `git describe` and version tooling work in clones.
        tags = git("tag", "--merged", base, cwd=repo, env=isolated).split()
        if tags:
            git("fetch", "-q", "--no-tags", str(repo), *(f"refs/tags/{t}:refs/tags/{t}" for t in tags),
                cwd=origin, env=isolated)
        if folder:
            shutil.rmtree(repo)  # origin.git holds the snapshot now; do not keep a second copy
        if not brief_file.is_file():
            fail(f"brief not found: {brief_file}")
        brief = brief_file.read_text().strip()
        agents, strategy = _prepare_clones(ws, origin, options, run_id, ids, procs)
        closing = render("closing.md", cap=options["cap"])
        draft_minutes = max(10, seconds(options["cap"]) // 600)
        for agent in agents:
            write_env_sh(Path(agent["clone"]), agent["env"])
            if solo:
                appendix = render("solo.md", clone=agent["clone"], env=env_block(agent["env"]))
            else:
                appendix = render(
                    "peer.md",
                    id=agent["id"],
                    n=str(len(ids)),
                    peer_ids=", ".join(ids),
                    clone=agent["clone"],
                    env=env_block(agent["env"]),
                    draft=str(draft_minutes),
                )
            (ws / "prompts" / f"{agent['id']}.md").write_text(f"{brief}\n\n{closing}\n\n{appendix}\n")
        if not solo:
            spawns = "\n".join(
                f"   - `task_name`: `{agent['id']}`, message: `Your instructions are in "
                f"{ws / 'prompts' / (agent['id'] + '.md')}. Read the whole file first, then follow it.`"
                for agent in agents
            )
            (ws / "prompts" / "root.md").write_text(
                render("root.md", n=str(len(ids)), spawns=spawns, wait_ms=str(ROOT_WAIT_MS)) + "\n"
            )
        meta = {
            "run_id": run_id,
            "mode": "solo" if solo else "swarm",
            "peers": len(ids),
            "brief": str(brief_file),
            "repo": str(repo),
            "folder": str(folder) if folder else None,
            "base": base,
            "model": options["model"],
            "effort": options["effort"],
            "cap": options["cap"],
            "clone_strategy": strategy,
            "setup_per_agent": bool(options["setup_per_agent"]),
            "agents": agents,
            "created_at": now(),
        }
        (ws / "murmur.json").write_text(json.dumps(meta, indent=2) + "\n")
        published = True
        print(ws)
    except KeyboardInterrupt:
        print("murmur: setup interrupted", file=sys.stderr)
        raise SystemExit(EXIT_INTERRUPTED) from None
    finally:
        procs.stop_all()
        restore_interrupt_handlers(previous)
        if not published and ws.exists():
            shutil.rmtree(ws, ignore_errors=True)


def codex_command(ws: Path, meta: dict, injected: dict) -> list[str]:
    # The session starts in work/, which is not a repository, so it never auto-loads the
    # repo's AGENTS.md or .codex hooks; the closing prompt sends each agent to AGENTS.md.
    cmd = [
        "codex", "exec", "--json", "--skip-git-repo-check",
        "-m", meta["model"],
        "-c", f"model_reasoning_effort={toml_value(meta['effort'])}",
        "-c", 'model_reasoning_summary="auto"',
        "--disable", "memories",
        "--sandbox", "workspace-write",
        "-c", 'approval_policy="never"',
        "-c", "sandbox_workspace_write.network_access=true",
        "-c", 'shell_environment_policy.inherit="core"',
        "-c", f"shell_environment_policy.set={toml_value(injected)}",
        "-C", str(ws / "work"),
        "-o", str(ws / "logs" / "final.md"),
    ]
    if meta["mode"] == "solo":
        cmd += ["--disable", "multi_agent", "--disable", "multi_agent_v2"]
    else:
        # V2 allows 4 threads per session by default, counting the root, so a fourth peer
        # would fail with "agent thread limit reached". Make room for the root plus every peer.
        # The root only waits; let one wait last up to ROOT_WAIT_MS (Codex's hard ceiling)
        # instead of the shorter default ceiling, so it makes few calls.
        threads = {
            "enabled": True,
            "max_concurrent_threads_per_session": meta["peers"] + 1,
            "max_wait_timeout_ms": ROOT_WAIT_MS,
        }
        cmd += ["-c", f"features.multi_agent_v2={toml_value(threads)}"]
        cmd += ["--enable", "agent_message_board"]
    return [*cmd, "-"]


def _choose_exit(
    capped: bool, interrupted: bool, codex_exit: int | None, delivered: bool | None = None
) -> tuple[int, str]:
    if interrupted:
        return EXIT_INTERRUPTED, "interrupted"
    if capped:
        return EXIT_CAPPED, "capped"
    if codex_exit not in (0, None):
        return EXIT_CODEX_FAILED, f"codex exited {codex_exit}"
    if delivered is False:
        return EXIT_NO_WORK, "no work delivered: main did not advance"
    return EXIT_OK, "exit 0"


def _delivery(origin: Path, base: str) -> tuple[str | None, list[str]]:
    """New commits on origin main since base, and the draft branches the peers left."""
    if not origin.exists():
        return None, []
    counted = subprocess.run(
        ["git", "rev-list", "--count", f"{base}..main"],
        cwd=origin, capture_output=True, text=True, check=False,
    )
    commits = counted.stdout.strip() if counted.returncode == 0 else None
    listed = subprocess.run(
        ["git", "for-each-ref", "--format=%(refname:short)", "refs/heads/draft/"],
        cwd=origin, capture_output=True, text=True, check=False,
    )
    drafts = listed.stdout.split() if listed.returncode == 0 else []
    return commits, drafts


def _review_command(ws: Path, meta: dict, origin: Path) -> str:
    return f"git -C {meta['repo']} fetch {origin} main:murmur/{ws.name}"


def _draft_hint(ws: Path, meta: dict, origin: Path, drafts: list[str]) -> str:
    """How to get at unmerged drafts. The refs never nest under the review branch murmur/<id>."""
    if meta.get("folder"):
        # The run's repo is murmur's internal snapshot, so point at origin.git itself.
        first = drafts[0]
        target = f"{meta['folder']}.murmur-{ws.name}-{first.replace('/', '-')}"
        return (f"murmur: the drafts are branches of {origin}: {', '.join(drafts)}; "
                f"to look at one: git clone -b {first} {origin} {target}")
    return f"murmur: recover the drafts: {_drafts_command(ws, meta, origin)}"


def _drafts_command(ws: Path, meta: dict, origin: Path) -> str:
    return (f"git -C {meta['repo']} fetch {origin} "
            f"'refs/heads/draft/*:refs/heads/murmur/{ws.name}-drafts/*'")


def run(args: argparse.Namespace) -> None:
    previous = install_interrupt_handlers()
    proc: subprocess.Popen | None = None
    try:
        ws = Path(args.workspace).expanduser().resolve()
        meta_path = ws / "murmur.json"
        if not meta_path.is_file():
            fail(f"no workspace at {ws}")
        try:
            meta = json.loads(meta_path.read_text())
        except json.JSONDecodeError as exc:
            fail(f"unreadable {meta_path}: {exc}")
        if (ws / "logs" / "run.json").exists():
            fail(f"{ws.name} has already run; set up a new workspace")
        injected = shell_env(ws)
        cmd = codex_command(ws, meta, injected)
        env = {**os.environ, **injected, "CODEX_HOME": str(ws / "codex-home")}
        prompt = ws / "prompts" / ("solo.md" if meta["mode"] == "solo" else "root.md")
        log_err = ws / "logs" / "session.err"
        started_at = now()
        started = time.monotonic()
        capped = interrupted = False
        interruption_signal: int | None = None
        codex_exit: int | None = None
        with prompt.open() as stdin, (ws / "logs" / "session.jsonl").open("w") as out, log_err.open("w") as err:
            proc = subprocess.Popen(
                cmd, stdin=stdin, stdout=out, stderr=err, env=env, start_new_session=True
            )
            try:
                proc.wait(timeout=seconds(meta["cap"]))
            except subprocess.TimeoutExpired:
                capped = True
            except KeyboardInterrupt as exc:
                interrupted = True
                if exc.args and exc.args[0] in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
                    interruption_signal = int(exc.args[0])
            finally:
                # Stop Codex with the signal the launcher got, so a Ctrl-C stays a Ctrl-C.
                stop_process_group(proc, term_signal=interruption_signal or signal.SIGTERM)
                codex_exit = proc.returncode
                proc = None
        elapsed = round(time.monotonic() - started, 1)
        origin = ws / "work" / "origin.git"
        commits, drafts = _delivery(origin, meta["base"])
        delivered = None if commits is None else commits != "0"
        exit_code, diagnostic = _choose_exit(capped, interrupted, codex_exit, delivered)
        if delivered is False and drafts:
            diagnostic += f"; unmerged draft branches in {origin}: {', '.join(drafts)}"
        record = {
            "started_at": started_at,
            "ended_at": now(),
            "seconds": elapsed,
            "command": cmd,
            "exit_code": exit_code,
            "codex_exit_code": codex_exit,
            "capped": capped,
            "interrupted": interrupted,
            "commits": commits,
            "delivered": delivered,
            "drafts": drafts,
            "diagnostic": diagnostic,
        }
        (ws / "logs" / "run.json").write_text(json.dumps(record, indent=2) + "\n")
        label = "capped" if capped else "interrupted" if interrupted else f"exit {codex_exit}"
        suffix = f", {commits} new commit(s)" if commits is not None else ""
        print(f"{ws.name}: {meta['mode']} finished in {elapsed / 60:.1f} min ({label}){suffix}")
        if exit_code != EXIT_OK:
            print(f"murmur: {diagnostic}", file=sys.stderr)
            print(f"murmur: log: {log_err}", file=sys.stderr)
        if delivered is False and drafts:
            print(_draft_hint(ws, meta, origin, drafts), file=sys.stderr)
        # With nothing new on main there is nothing to review and no point copying the folder.
        if delivered is not False and origin.exists():
            if meta.get("folder"):
                write_result(ws)
            else:
                print(f"review it: {_review_command(ws, meta, origin)}")
        raise SystemExit(exit_code)
    except KeyboardInterrupt:
        print("murmur: interrupted", file=sys.stderr)
        raise SystemExit(EXIT_INTERRUPTED) from None
    finally:
        if proc is not None:
            stop_process_group(proc)
        restore_interrupt_handlers(previous)


def main() -> None:
    parser = argparse.ArgumentParser(prog="murmur", description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)

    p_setup = commands.add_parser("setup", help="build an isolated workspace for one run")
    p_setup.add_argument("brief", nargs="?", help="markdown file with the objective")
    p_setup.add_argument("--config", help="TOML file with any of the options below")
    p_setup.add_argument("--repo", help="git repo to start from (default: current)")
    p_setup.add_argument("--base", help="commit or ref to start from (default: HEAD)")
    mode = p_setup.add_mutually_exclusive_group()
    mode.add_argument("--peers", type=int, help="number of peer agents (default: 4)")
    mode.add_argument("--solo", action="store_true", help="one agent, no swarm")
    p_setup.add_argument("--model", help="Codex model (default: gpt-6-astra)")
    p_setup.add_argument("--effort", help="reasoning effort (default: high)")
    p_setup.add_argument("--cap", help="hard time limit, e.g. 90m or 3h (default: 3h)")
    p_setup.add_argument(
        "--setup", action="append", metavar="CMD",
        help="shell command run once, then copied (repeatable). See --setup-per-agent",
    )
    p_setup.add_argument(
        "--setup-per-agent", action="store_true",
        help="run --setup in every clone. Use when the install embeds absolute paths",
    )
    p_setup.add_argument("--port-base", type=int, help="first agent's port range (default: 40000)")
    p_setup.add_argument("--into", default="~/.murmur/runs", help="parent dir for workspaces")
    p_setup.add_argument("--id", help="workspace id (default: random)")
    p_setup.add_argument("--max-file-mb", type=float,
                         help="plain-folder input: files larger than this stay out of git and are "
                              "linked read-only (default: 50)")
    p_setup.set_defaults(func=setup)

    p_run = commands.add_parser("run", help="run the Codex session for a workspace")
    p_run.add_argument("workspace")
    p_run.set_defaults(func=run)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
