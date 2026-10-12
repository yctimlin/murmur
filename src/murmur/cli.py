"""murmur: run a leaderless swarm of Codex agents on one objective.

  murmur setup BRIEF [--repo DIR] [--peers N | --solo] [--setup CMD]... [options]
  murmur run WORKSPACE

`setup` builds an isolated workspace for one run:

- a bare `origin.git` holding a single commit of your repo,
- one clone per agent,
- a minimal CODEX_HOME,
- a git config that cannot reach GitHub,
- the rendered prompts.

`run` launches Codex and stops it at the cap. Nothing a run produces leaves the workspace;
fetch `origin.git`'s `main` into your repo to review the result.

A swarm is one Codex session whose root only spawns the peers and waits. The peers have equal
standing and coordinate through Codex's built-in message board and collaboration tools.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shutil
import signal
import subprocess
import sys
import time
import tomllib
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path
from string import Template

DURATION_RE = re.compile(r"^(\d+)([smh])$")
DEFAULTS = {
    "peers": 4,
    "model": "gpt-6-astra",
    "effort": "high",
    "cap": "3h",
    "port_base": 40000,
    "port_stride": 100,
    "setup": [],
    "agent_env": {},
}

# Agents get network access but no way to reach GitHub: no credential helper, and
# every GitHub URL is rewritten to a path that does not exist.
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
    sys.exit(f"murmur: {message}")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def seconds(duration: str) -> int:
    match = DURATION_RE.match(duration)
    if not match:
        fail(f"bad duration {duration!r} (use e.g. 45m or 3h)")
    return int(match[1]) * {"s": 1, "m": 60, "h": 3600}[match[2]]


def git(*args: str, cwd: Path | None = None, env: dict | None = None) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, env=env, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def toml_value(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, list):
        return "[" + ", ".join(toml_value(v) for v in value) + "]"
    if isinstance(value, dict):
        pairs = (f"{json.dumps(k)} = {toml_value(v)}" for k, v in value.items())
        return "{" + ", ".join(pairs) + "}"
    raise TypeError(f"cannot write {type(value).__name__} as TOML")


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
        lines += [f"{k} = {toml_value(v)}" for k, v in user["model_providers"][provider].items()]
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
    pairs = ", ".join(f"`{k}={v}`" for k, v in env.items())
    return f"Your environment values: {pairs}. Export them in commands that need them."


def resolve_options(args: argparse.Namespace) -> dict:
    """Defaults, then the optional config file, then flags."""
    options = dict(DEFAULTS)
    if args.config:
        config_path = Path(args.config).expanduser().resolve()
        config = tomllib.loads(config_path.read_text())
        for key in ("repo", "brief"):
            if key in config:
                config[key] = str((config_path.parent / config[key]).resolve())
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
    }
    options |= {k: v for k, v in flags.items() if v is not None}
    if args.solo:
        options["peers"] = 1
    elif options["peers"] < 2:
        fail("a swarm needs at least 2 peers; use --solo for a single agent")
    if not options.get("brief"):
        fail("give a brief file (or a config with `brief`)")
    seconds(options["cap"])
    return options


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
    work = ws / "work"
    home = ws / "codex-home"
    for directory in (ws / "logs", ws / "prompts", ws / "gh", ws / "zdot", work, home):
        directory.mkdir(parents=True)
    (ws / "gitconfig").write_text(GITCONFIG)
    write_model_catalog(home / "models.json", options["model"], options["effort"], solo)
    write_codex_home(home, work, home / "models.json")
    git_env = {**os.environ, "GIT_CONFIG_GLOBAL": str(ws / "gitconfig"), "GIT_CONFIG_NOSYSTEM": "1"}

    origin = work / "origin.git"
    git("init", "-q", "--bare", str(origin), env=git_env)
    git("config", "receive.denyNonFastForwards", "true", cwd=origin)
    git("config", "receive.denyDeletes", "true", cwd=origin)
    # A timestamped log of every update to main, so main at any moment can be rebuilt.
    git("config", "core.logAllRefUpdates", "always", cwd=origin)
    git("fetch", "-q", "--no-tags", str(repo), f"{base}:refs/heads/main", cwd=origin, env=git_env)

    brief = brief_file.read_text().strip()
    closing = render("closing.md", cap=options["cap"])
    # Exploratory drafts get a tenth of the cap, so choosing a design stays cheap.
    draft_minutes = max(10, seconds(options["cap"]) // 600)
    agents = []
    for index, agent_id in enumerate(ids):
        clone = work / ("repo" if solo else f"peers/{agent_id}")
        git("clone", "-q", str(origin), str(clone), env=git_env)
        git("config", "user.name", agent_id, cwd=clone)
        git("config", "user.email", f"{agent_id}@murmur.local", cwd=clone)
        values = {
            "run": run_id,
            "agent": agent_id,
            "index": str(index),
            "port_base": str(options["port_base"] + index * options["port_stride"]),
        }
        env = {"PORT_BASE": values["port_base"]}
        env |= {k: Template(v).substitute(values) for k, v in options["agent_env"].items()}
        for command in options["setup"]:
            print(f"murmur: [{agent_id}] {command}", file=sys.stderr)
            subprocess.run(
                command, shell=True, cwd=clone, check=True,
                env={**git_env, **env, "MURMUR_AGENT": agent_id},
            )
        if solo:
            appendix = render("solo.md", clone=str(clone), env=env_block(env))
        else:
            appendix = render(
                "peer.md", id=agent_id, n=str(len(ids)), peer_ids=", ".join(ids),
                clone=str(clone), env=env_block(env), draft=str(draft_minutes),
            )
        (ws / "prompts" / f"{agent_id}.md").write_text(f"{brief}\n\n{closing}\n\n{appendix}\n")
        agents.append({"id": agent_id, "clone": str(clone), "env": env})

    if not solo:
        spawns = "\n".join(
            f"   - `task_name`: `{a['id']}`, message: `Your instructions are in "
            f"{ws / 'prompts' / (a['id'] + '.md')}. Read the whole file first, then follow it.`"
            for a in agents
        )
        (ws / "prompts" / "root.md").write_text(
            render("root.md", n=str(len(ids)), spawns=spawns) + "\n"
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
        "agents": agents,
        "created_at": now(),
    }
    (ws / "murmur.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(ws)


def stop(proc: subprocess.Popen) -> None:
    for sig, grace in ((signal.SIGTERM, 15), (signal.SIGKILL, 5)):
        try:
            os.killpg(proc.pid, sig)
            proc.wait(timeout=grace)
            return
        except (ProcessLookupError, subprocess.TimeoutExpired):
            continue


def interrupt(signum, frame) -> None:
    raise KeyboardInterrupt


def codex_command(ws: Path, meta: dict, shell_env: dict) -> list[str]:
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
        "-c", f"shell_environment_policy.set={toml_value(shell_env)}",
        "-C", str(ws / "work"),
        "-o", str(ws / "logs" / "final.md"),
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


def run(args: argparse.Namespace) -> None:
    # Codex runs in its own process group, so a terminated murmur must stop it explicitly.
    signal.signal(signal.SIGTERM, interrupt)
    signal.signal(signal.SIGHUP, interrupt)
    ws = Path(args.workspace).expanduser().resolve()
    meta = json.loads((ws / "murmur.json").read_text())
    if (ws / "logs" / "run.json").exists():
        fail(f"{ws.name} has already run; set up a new workspace")
    # Agent commands run in a login zsh, which would re-read the user's dotfiles and
    # re-export their secrets; an empty ZDOTDIR keeps those files out.
    shell_env = {
        "GIT_CONFIG_GLOBAL": str(ws / "gitconfig"),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GH_CONFIG_DIR": str(ws / "gh"),
        "ZDOTDIR": str(ws / "zdot"),
    }
    cmd = codex_command(ws, meta, shell_env)
    env = {**os.environ, **shell_env, "CODEX_HOME": str(ws / "codex-home")}
    prompt = ws / "prompts" / ("solo.md" if meta["mode"] == "solo" else "root.md")
    record = {"started_at": now(), "command": cmd}
    started = time.monotonic()
    capped = interrupted = False
    with (
        prompt.open() as stdin,
        (ws / "logs" / "session.jsonl").open("w") as out,
        (ws / "logs" / "session.err").open("w") as err,
    ):
        proc = subprocess.Popen(
            cmd, stdin=stdin, stdout=out, stderr=err, env=env, start_new_session=True
        )
        try:
            proc.wait(timeout=seconds(meta["cap"]))
        except subprocess.TimeoutExpired:
            capped = True
            stop(proc)
        except KeyboardInterrupt:
            interrupted = True
            stop(proc)
    record |= {
        "ended_at": now(),
        "seconds": round(time.monotonic() - started, 1),
        "exit_code": proc.returncode,
        "capped": capped,
        "interrupted": interrupted,
    }
    (ws / "logs" / "run.json").write_text(json.dumps(record, indent=2) + "\n")

    origin = ws / "work" / "origin.git"
    commits = git("rev-list", "--count", f"{meta['base']}..main", cwd=origin)
    minutes = record["seconds"] / 60
    state = "capped" if capped else "interrupted" if interrupted else f"exit {proc.returncode}"
    print(f"{ws.name}: {meta['mode']} finished in {minutes:.1f} min ({state}), {commits} new commit(s)")
    print(f"review it: git -C {meta['repo']} fetch {origin} main:murmur/{ws.name}")
    if interrupted:
        sys.exit(130)


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
        help="shell command to run in every clone, e.g. 'pnpm install' (repeatable)",
    )
    p_setup.add_argument("--port-base", type=int, help="first agent's port range (default: 40000)")
    p_setup.add_argument("--into", default="~/.murmur/runs", help="parent dir for workspaces")
    p_setup.add_argument("--id", help="workspace id (default: random)")
    p_setup.set_defaults(func=setup)

    p_run = commands.add_parser("run", help="run the Codex session for a workspace")
    p_run.add_argument("workspace")
    p_run.set_defaults(func=run)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
