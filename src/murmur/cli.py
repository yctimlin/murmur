"""murmur: run a leaderless swarm of Codex agents on one objective.

  murmur setup BRIEF [--repo DIR] [--peers N | --solo] [--setup CMD]... [options]
  murmur run WORKSPACE
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import subprocess
import sys
import threading
import time
import tomllib
from concurrent.futures import ThreadPoolExecutor, as_completed
from importlib.resources import files
from pathlib import Path
from string import Template

from murmur.cow import CowCopyError, cow_copy
from murmur.errors import (
    EXIT_CAPPED,
    EXIT_CODEX_FAILED,
    EXIT_INCOMPLETE,
    EXIT_INTERRUPTED,
    EXIT_LAUNCHER,
    EXIT_OK,
    MurmurError,
    fail,
)
from murmur.gitutil import git
from murmur.isolate import (
    GITCONFIG,
    git_env,
    runtime_shell_env,
    setup_environment,
    store_override,
    write_bin,
    write_env_sh,
    write_shell_files,
)
from murmur.protocol import SPAWN_RETRY_LIMIT, evaluate_protocol, format_outcomes
from murmur.procutil import (
    install_interrupt_handlers,
    restore_interrupt_handlers,
    stop_process_group,
)
from murmur.state import (
    WorkspaceBusy,
    WorkspaceLock,
    begin_attempt,
    ensure_launchable,
    finalize_attempt,
    note_codex_process,
    ready_state,
    save_state,
)
from murmur.util import now, seconds, toml_value

DEFAULTS = {
    "peers": 4,
    "model": "gpt-6-astra",
    "effort": "high",
    "cap": "3h",
    "port_base": 40000,
    "port_stride": 100,
    "setup": [],
    "setup_env": [],
    "setup_per_agent": False,
    "agent_env": {},
}


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
    """
    out = subprocess.run(["codex", "debug", "models"], check=True, capture_output=True, text=True)
    catalog = json.loads(out.stdout)
    for entry in catalog["models"]:
        if solo:
            entry["multi_agent_version"] = None
        elif entry.get("slug") == model:
            entry["multi_agent_reasoning_effort"] = effort
    path.write_text(json.dumps(catalog, indent=2) + "\n")


def write_codex_home(home: Path, trusted: Path, catalog: Path) -> None:
    """A minimal CODEX_HOME that carries over only the user's model provider and auth.

    It has no plugins, notify hooks, memories, personal AGENTS.md or past sessions, so
    runs cannot see each other or act on the user's desktop.
    """
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
        f"Shell commands that start in this clone export {pairs}. "
        "You do not need to export them yourself."
    )


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
        "setup": args.setup or None,
        "setup_env": args.setup_env or None,
    }
    options |= {key: value for key, value in flags.items() if value is not None}
    if args.solo:
        options["peers"] = 1
    elif not isinstance(options["peers"], int) or isinstance(options["peers"], bool):
        fail("peers must be an integer")
    elif options["peers"] < 2:
        fail("a swarm needs at least 2 peers; use --solo for a single agent")
    if args.setup_per_agent:
        options["setup_per_agent"] = True
    elif "setup_per_agent" not in options:
        options["setup_per_agent"] = False
    if not isinstance(options["setup_per_agent"], bool):
        fail("setup_per_agent must be a boolean")
    options["setup"] = _as_string_list(options.get("setup"), "setup")
    options["setup_env"] = _as_string_list(options.get("setup_env"), "setup_env")
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


def _run_commands(commands: list[str], cwd: Path, env: dict[str, str], procs: _SetupProcs) -> None:
    for command in commands:
        _run_setup_command(command, cwd, env, procs)


def _clone(origin: Path, dest: Path, env: dict[str, str]) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    git("clone", "-q", str(origin), str(dest), env=env)


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
        exclude.write_text(current + ("" if current.endswith("\n") or not current else "\n") + ".murmur/\n")
    if template is None:
        return
    old = str(template)
    new = str(clone)
    if old == new:
        return
    paths = []
    git_entry = clone / ".git"
    if git_entry.is_file():
        paths.append(git_entry)
    config = clone / ".git" / "config"
    if config.is_file():
        paths.append(config)
    for path in paths:
        text = path.read_text()
        if old in text:
            path.write_text(text.replace(old, new))


def _agent_env(options: dict, run_id: str, agent_id: str, index: int, store: dict[str, str]) -> dict[str, str]:
    port_base = str(options["port_base"] + index * options["port_stride"])
    values = {"run": run_id, "agent": agent_id, "index": str(index), "port_base": port_base}
    env = {"PORT_BASE": port_base, "MURMUR_AGENT": agent_id}
    for key, template in options["agent_env"].items():
        if not isinstance(key, str) or not isinstance(template, str):
            fail("agent_env keys and values must be strings")
        env[key] = Template(template).substitute(values)
    forced = store.get("npm_config_store_dir")
    if forced:
        current = env.get("npm_config_store_dir")
        if not current or not _store_inside(Path(current), options["_ws"]):
            env["npm_config_store_dir"] = forced
    elif "npm_config_store_dir" in env and not _store_inside(Path(env["npm_config_store_dir"]), options["_ws"]):
        env["npm_config_store_dir"] = str(options["_ws"] / "pnpm-store")
    return env


def _store_inside(path: Path, ws: Path) -> bool:
    candidate = path.expanduser()
    if not candidate.is_absolute():
        return True
    try:
        candidate.resolve().relative_to(ws.resolve())
    except ValueError:
        return False
    return True


def _prepare_clones(ws: Path, origin: Path, options: dict, run_id: str, ids: list[str], procs: _SetupProcs):
    work = ws / "work"
    solo = len(ids) == 1
    isolated = {**setup_environment(ws, inherit=[]), **git_env(ws)}
    # git itself needs PATH and HOME; setup_environment already allowlists those.
    clones = []
    for index, agent_id in enumerate(ids):
        dest = work / ("repo" if solo else f"peers/{agent_id}")
        clones.append((index, agent_id, dest))

    first_index, first_id, first = clones[0]
    _clone(origin, first, isolated)
    _configure_clone(first, first_id, origin, isolated)
    store = store_override(ws, first, options["agent_env"])
    options = dict(options)
    options["_ws"] = ws
    shared_env = setup_environment(ws, inherit=options["setup_env"], store_env=store)
    per_agent = solo or options["setup_per_agent"] or len(ids) == 1

    def one(index: int, agent_id: str, dest: Path, *, include_agent: bool) -> dict:
        if dest != first:
            _clone(origin, dest, isolated)
            _configure_clone(dest, agent_id, origin, isolated)
        agent = {
            "id": agent_id,
            "clone": str(dest),
            "env": _agent_env(options, run_id, agent_id, index, store),
        }
        if include_agent:
            _run_commands(
                options["setup"],
                dest,
                setup_environment(
                    ws,
                    inherit=options["setup_env"],
                    store_env=store,
                    agent_env=agent["env"],
                ),
                procs,
            )
        return agent

    if per_agent:
        if options["setup_per_agent"] and not solo:
            print("murmur: running setup in each clone (--setup-per-agent)", file=sys.stderr)
        agents = [one(index, agent_id, dest, include_agent=True) for index, agent_id, dest in clones]
        return agents, "solo" if solo else "per-agent"

    print(f"murmur: running setup once in {first_id}", file=sys.stderr)
    _run_commands(options["setup"], first, shared_env, procs)
    agents = [{
        "id": first_id,
        "clone": str(first),
        "env": _agent_env(options, run_id, first_id, first_index, store),
    }]
    copied: list[Path] = []
    try:
        for index, agent_id, dest in clones[1:]:
            cow_copy(first, dest)
            copied.append(dest)
            _configure_clone(dest, agent_id, origin, isolated, template=first)
            agents.append({
                "id": agent_id,
                "clone": str(dest),
                "env": _agent_env(options, run_id, agent_id, index, store),
            })
    except CowCopyError as exc:
        print(
            f"murmur: copy-on-write clone failed ({exc}); "
            "running setup in the remaining clones in parallel",
            file=sys.stderr,
        )
        for dest in copied:
            shutil.rmtree(dest, ignore_errors=True)
        # cow_copy already removes the destination that failed.
        jobs = []
        rest = []
        for index, agent_id, dest in clones[1:]:
            if dest.exists():
                shutil.rmtree(dest)
            def job(index=index, agent_id=agent_id, dest=dest):
                _clone(origin, dest, isolated)
                _configure_clone(dest, agent_id, origin, isolated)
                agent_env = _agent_env(options, run_id, agent_id, index, store)
                # Same shared environment as the first clone. Per-agent ports are
                # applied later by each clone's runtime shell, not by this install.
                _run_commands(options["setup"], dest, shared_env, procs)
                return {
                    "id": agent_id,
                    "clone": str(dest),
                    "env": agent_env,
                }
            jobs.append(job)
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


def setup(args: argparse.Namespace) -> None:
    if not shutil.which("codex"):
        fail("the `codex` CLI is not on PATH")
    options = resolve_options(args)
    solo = options["peers"] == 1
    brief_file = Path(options["brief"]).expanduser().resolve()
    start = Path(options.get("repo") or ".").expanduser().resolve()
    repo = Path(git("rev-parse", "--show-toplevel", cwd=start))
    base_ref = options.get("base") or "HEAD"
    base = git("rev-parse", "--verify", f"{base_ref}^{{commit}}", cwd=repo)
    if base_ref == "HEAD" and git("status", "--porcelain", cwd=repo):
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
        for directory in (ws / "logs", ws / "prompts", ws / "gh", ws / "protocol", work, home):
            directory.mkdir(parents=True)
        (ws / "gitconfig").write_text(GITCONFIG)
        write_shell_files(ws)
        write_bin(ws)
        write_model_catalog(home / "models.json", options["model"], options["effort"], solo)
        write_codex_home(home, work, home / "models.json")
        isolated = {**setup_environment(ws, inherit=[]), **git_env(ws)}
        origin = work / "origin.git"
        git("init", "-q", "--bare", str(origin), env=isolated)
        git("config", "receive.denyNonFastForwards", "true", cwd=origin, env=isolated)
        git("config", "receive.denyDeletes", "true", cwd=origin, env=isolated)
        git("config", "core.logAllRefUpdates", "always", cwd=origin, env=isolated)
        git(
            "fetch", "-q", "--no-tags", str(repo), f"{base}:refs/heads/main",
            cwd=origin, env=isolated,
        )
        if not brief_file.is_file():
            fail(f"brief not found: {brief_file}")
        brief = brief_file.read_text().strip()
        agents, strategy = _prepare_clones(ws, origin, options, run_id, ids, procs)
        closing = render("closing.md", cap=options["cap"])
        draft_minutes = max(10, seconds(options["cap"]) // 600)
        attest = str(ws / "bin" / "murmur-attest")
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
                    attest=attest,
                    protocol_dir=str(ws / "protocol"),
                )
            (ws / "prompts" / f"{agent['id']}.md").write_text(f"{brief}\n\n{closing}\n\n{appendix}\n")
        if not solo:
            spawns = "\n".join(
                f"   - `task_name`: `{agent['id']}`, message: `Your instructions are in "
                f"{ws / 'prompts' / (agent['id'] + '.md')}. Read the whole file first, then follow it.`"
                for agent in agents
            )
            (ws / "prompts" / "root.md").write_text(
                render(
                    "root.md",
                    n=str(len(ids)),
                    spawns=spawns,
                    retries=str(SPAWN_RETRY_LIMIT),
                )
                + "\n"
            )
        meta = {
            "run_id": run_id,
            "mode": "solo" if solo else "swarm",
            "peers": len(ids),
            "brief": str(brief_file),
            "repo": str(repo),
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
        save_state(ws, ready_state())
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


def codex_command(ws: Path, meta: dict, final: Path) -> list[str]:
    # The session starts in work/, which is not a repository, so it never auto-loads the
    # repo's AGENTS.md or .codex hooks; the closing prompt sends each agent to AGENTS.md.
    shell_env = runtime_shell_env(ws)
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
        "-c", "shell_environment_policy.ignore_default_excludes=false",
        "-c", "shell_environment_policy.experimental_use_profile=false",
        "-c", f"shell_environment_policy.set={toml_value(shell_env)}",
        "-C", str(ws / "work"),
        "-o", str(final),
    ]
    if meta["mode"] == "solo":
        cmd += ["--disable", "multi_agent", "--disable", "multi_agent_v2"]
    else:
        # V2 allows 4 threads per session by default, counting the root, so a fourth peer
        # would fail with "agent thread limit reached". Make room for the root plus every peer.
        threads = {"enabled": True, "max_concurrent_threads_per_session": meta["peers"] + 1}
        cmd += ["-c", f"features.multi_agent_v2={toml_value(threads)}"]
        cmd += ["--enable", "agent_message_board"]
    return [*cmd, "-"]


def _continuation(attempt_dir: Path, index: int, root_prompt: Path, protocol: dict) -> Path:
    path = attempt_dir / f"continuation-{index}.md"
    path.write_text(
        root_prompt.read_text().rstrip()
        + "\n\nThis is a bounded launcher retry. Previous attestations were archived "
        + "and do not count.\nSpawn every peer again. Each peer must attest the current "
        + "origin/main. Peers stay equal; do not appoint a lead.\n\nPrevious result: "
        + format_outcomes(protocol)
        + "\n"
    )
    return path


def _clear_attestations(ws: Path, archive: Path) -> None:
    archive.mkdir(parents=True, exist_ok=True)
    live = ws / "protocol"
    for path in live.glob("*"):
        if not path.is_file() or path.name == "attempt":
            continue
        shutil.copy2(path, archive / path.name)
        if path.suffix == ".json":
            path.unlink()


def _new_commits(meta: dict, ws: Path) -> int | None:
    origin = ws / "work" / "origin.git"
    if not origin.exists():
        return None
    try:
        return int(git("rev-list", "--count", f"{meta['base']}..main", cwd=origin) or "0")
    except subprocess.CalledProcessError:
        return None


def _last_line(path: Path | None) -> str:
    if path is None or not path.is_file():
        return ""
    for line in reversed(path.read_text(errors="replace").splitlines()):
        if line.strip():
            return line.strip()
    return ""


def _choose_exit(outcome: dict, mode: str) -> tuple[int, str, str | None]:
    if outcome["interrupted"]:
        return EXIT_INTERRUPTED, "interrupted", "interrupted"
    if outcome["capped"]:
        return EXIT_CAPPED, "capped", "capped"
    if outcome["launcher_error"]:
        return EXIT_LAUNCHER, "failed", outcome["launcher_error"]
    if outcome["codex_exit"] not in (0, None):
        return EXIT_CODEX_FAILED, "failed", "codex-exit"
    if mode == "swarm" and not (outcome.get("protocol") or {}).get("complete"):
        return EXIT_INCOMPLETE, "failed", "incomplete"
    return EXIT_OK, "succeeded", None


def _print_report(ws: Path, meta: dict, outcome: dict, elapsed: float, exit_code: int) -> None:
    labels = {
        EXIT_OK: "succeeded",
        EXIT_CODEX_FAILED: f"codex exit {outcome['codex_exit']}",
        EXIT_CAPPED: "capped",
        EXIT_LAUNCHER: "launcher error",
        EXIT_INCOMPLETE: "incomplete",
        EXIT_INTERRUPTED: "interrupted",
    }
    commits = _new_commits(meta, ws)
    commit_text = f"{commits} new commit(s)" if commits is not None else "unknown commits"
    print(
        f"{ws.name}: {meta['mode']} finished in {elapsed / 60:.1f} min "
        f"({labels[exit_code]}), {commit_text}"
    )
    if exit_code == EXIT_OK and meta.get("mode") == "swarm":
        head = (outcome.get("protocol") or {}).get("head")
        print(f"protocol: complete {head}", file=sys.stderr)
    elif exit_code == EXIT_CODEX_FAILED:
        detail = f"codex exited {outcome['codex_exit']}"
        last = _last_line(outcome.get("log_path"))
        if last:
            detail += f": {last}"
        print(f"murmur: {detail}", file=sys.stderr)
    elif exit_code == EXIT_CAPPED:
        print(f"murmur: reached the time cap ({meta['cap']})", file=sys.stderr)
    elif exit_code == EXIT_INTERRUPTED:
        print("murmur: interrupted", file=sys.stderr)
    elif exit_code == EXIT_INCOMPLETE:
        print(f"murmur: {format_outcomes(outcome.get('protocol'))}", file=sys.stderr)
    elif exit_code == EXIT_LAUNCHER and outcome.get("launcher_error"):
        print(f"murmur: {outcome['launcher_error']}", file=sys.stderr)
    if exit_code != EXIT_OK:
        final = outcome.get("final")
        partial = (commits or 0) > 0 or (final is not None and final.is_file() and final.stat().st_size > 0)
        print(
            "murmur: partial result, not a completed run" if partial else "murmur: not a completed run",
            file=sys.stderr,
        )
        if outcome.get("log_path"):
            print(f"log: {outcome['log_path']}", file=sys.stderr)
    origin = ws / "work" / "origin.git"
    if origin.exists():
        print(f"review it: git -C {meta['repo']} fetch {origin} main:murmur/{ws.name}")


def run(args: argparse.Namespace) -> None:
    if args.protocol_retries < 0:
        fail("--protocol-retries must be >= 0")
    ws = Path(args.workspace).expanduser().resolve()
    meta_path = ws / "murmur.json"
    if not meta_path.is_file():
        fail(f"no workspace at {ws}")
    try:
        meta = json.loads(meta_path.read_text())
    except json.JSONDecodeError as exc:
        fail(f"unreadable {meta_path}: {exc}")
    previous = install_interrupt_handlers()
    lock = WorkspaceLock(ws / "run.lock")
    try:
        try:
            lock.acquire()
        except WorkspaceBusy as exc:
            fail(f"{ws.name} is in use by pid {exc.holder}; refusing a concurrent run")
        try:
            _run_locked(args, ws, meta)
        finally:
            lock.release()
    except KeyboardInterrupt:
        print("murmur: interrupted", file=sys.stderr)
        raise SystemExit(EXIT_INTERRUPTED) from None
    finally:
        restore_interrupt_handlers(previous)


def _run_locked(args: argparse.Namespace, ws: Path, meta: dict) -> None:
    previous = ensure_launchable(ws, recover=args.recover, retry=args.retry)
    attempt_id, attempt_dir = begin_attempt(ws, previous)
    started = time.monotonic()
    deadline = started + seconds(meta["cap"])
    outcome: dict = {
        "capped": False,
        "interrupted": False,
        "launcher_error": None,
        "codex_exit": None,
        "command": None,
        "protocol": None,
        "log_path": None,
        "final": None,
    }
    proc: subprocess.Popen | None = None
    try:
        rounds = 1 + (args.protocol_retries if meta.get("mode") == "swarm" else 0)
        root_prompt = ws / "prompts" / ("solo.md" if meta["mode"] == "solo" else "root.md")
        for index in range(rounds):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                outcome["capped"] = True
                break
            final = attempt_dir / ("final.md" if index == 0 else f"final.retry{index}.md")
            outcome["final"] = final
            command = codex_command(ws, meta, final)
            outcome["command"] = command
            if index == 0:
                prompt = root_prompt
                log_out = attempt_dir / "session.jsonl"
                log_err = attempt_dir / "session.err"
            else:
                prompt = _continuation(attempt_dir, index, root_prompt, outcome["protocol"] or {})
                log_out = attempt_dir / f"session.retry{index}.jsonl"
                log_err = attempt_dir / f"session.retry{index}.err"
                _clear_attestations(ws, attempt_dir / f"protocol-round-{index - 1}")
            outcome["log_path"] = log_err
            with prompt.open() as stdin, log_out.open("w") as stdout, log_err.open("w") as stderr:
                proc = subprocess.Popen(
                    command,
                    stdin=stdin,
                    stdout=stdout,
                    stderr=stderr,
                    env={**os.environ, "CODEX_HOME": str(ws / "codex-home"), **git_env(ws)},
                    start_new_session=True,
                )
                try:
                    note_codex_process(ws, proc.pid)
                    proc.wait(timeout=remaining)
                except subprocess.TimeoutExpired:
                    outcome["capped"] = True
                except KeyboardInterrupt:
                    outcome["interrupted"] = True
                finally:
                    stop_process_group(proc)
                    outcome["codex_exit"] = proc.returncode
                    proc = None
            if outcome["capped"] or outcome["interrupted"] or outcome["codex_exit"] not in (0, None):
                break
            if meta.get("mode") != "swarm":
                break
            outcome["protocol"] = evaluate_protocol(ws, meta, attempt_id)
            if outcome["protocol"].get("complete") or index == rounds - 1:
                break
        if meta.get("mode") == "swarm" and outcome["protocol"] is None:
            try:
                outcome["protocol"] = evaluate_protocol(ws, meta, attempt_id)
            except Exception as exc:
                outcome["protocol"] = {"complete": False, "error": str(exc), "outcomes": {}}
    except KeyboardInterrupt:
        outcome["interrupted"] = True
    except MurmurError as exc:
        outcome["launcher_error"] = str(exc)
    except Exception as exc:
        outcome["launcher_error"] = f"{type(exc).__name__}: {exc}"
    finally:
        if proc is not None:
            stop_process_group(proc)
            if outcome["codex_exit"] is None:
                outcome["codex_exit"] = proc.returncode
    exit_code, terminal, reason = _choose_exit(outcome, meta.get("mode", "solo"))
    try:
        finalize_attempt(
            ws,
            terminal=terminal,
            reason=reason,
            exit_code=exit_code,
            codex_exit=outcome["codex_exit"],
            command=outcome["command"],
            protocol=outcome["protocol"],
            log=str(outcome["log_path"]) if outcome["log_path"] else None,
        )
    except Exception as exc:
        print(f"murmur: could not record run state: {exc}", file=sys.stderr)
        if exit_code == EXIT_OK:
            exit_code = EXIT_LAUNCHER
    _print_report(ws, meta, outcome, time.monotonic() - started, exit_code)
    raise SystemExit(exit_code)


def main(argv: list[str] | None = None) -> None:
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
        help="shell command to run before the clock starts (repeatable)",
    )
    p_setup.add_argument(
        "--setup-per-agent", action="store_true",
        help="run setup in every clone; use when the install embeds absolute paths",
    )
    p_setup.add_argument(
        "--setup-env", action="append", metavar="VAR",
        help="host environment variable to pass through to setup commands",
    )
    p_setup.add_argument("--port-base", type=int, help="first agent's port range (default: 40000)")
    p_setup.add_argument("--into", default="~/.murmur/runs", help="parent dir for workspaces")
    p_setup.add_argument("--id", help="workspace id (default: random)")
    p_setup.set_defaults(func=setup)

    p_run = commands.add_parser("run", help="run the Codex session for a workspace")
    p_run.add_argument("workspace")
    p_run.add_argument(
        "--recover", action="store_true",
        help="close a stale run, stopping leftover Codex processes, and start again",
    )
    p_run.add_argument(
        "--retry", action="store_true",
        help="start another attempt after a finished run, keeping its logs",
    )
    p_run.add_argument(
        "--protocol-retries", type=int, default=0,
        help="extra Codex sessions if a swarm exits 0 with an incomplete protocol (default: 0)",
    )
    p_run.set_defaults(func=run)

    from murmur.protocol import add_attest_parser
    add_attest_parser(commands)

    try:
        args = parser.parse_args(argv)
        args.func(args)
    except MurmurError as exc:
        print(f"murmur: {exc}", file=sys.stderr)
        raise SystemExit(exc.code) from None
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        print(f"murmur: command failed ({exc.returncode}): {' '.join(map(str, exc.cmd))}", file=sys.stderr)
        if detail:
            print(detail, file=sys.stderr)
        raise SystemExit(EXIT_LAUNCHER) from None


if __name__ == "__main__":
    main()
