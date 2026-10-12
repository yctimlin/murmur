"""What isolation murmur actually enforces, and the files that implement it."""

from __future__ import annotations

import os
import re
import shlex
import sys
from pathlib import Path

from murmur.errors import fail

# Git URL prefixes rewritten to a path that does not exist. This is not a
# network firewall: curl to github.com still works. It stops accidental
# fetches and pushes that use these URL shapes, including the ssh port form.
GITCONFIG = """\
[init]
\tdefaultBranch = main
[credential]
\thelper =
[url "file:///nonexistent/github-is-blocked/"]
\tinsteadOf = https://github.com/
\tinsteadOf = http://github.com/
\tinsteadOf = git://github.com/
\tinsteadOf = https://www.github.com/
\tinsteadOf = http://www.github.com/
\tinsteadOf = ssh://git@github.com/
\tinsteadOf = ssh://git@github.com:
\tinsteadOf = ssh://github.com/
\tinsteadOf = ssh://github.com:
\tinsteadOf = git@github.com:
\tinsteadOf = git@www.github.com:
"""

# Host variables a setup command may see without an explicit opt-in.
# Setup runs via `sh -c`, not a login shell, so user profiles are not sourced.
SETUP_INHERIT = (
    "PATH",
    "HOME",
    "USER",
    "LOGNAME",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "TMPDIR",
    "TERM",
)

SHELL_STARTUP_NAMES = (
    ".bash_profile",
    ".bashrc",
    ".profile",
    ".zshenv",
    ".zprofile",
    ".zshrc",
    ".zlogin",
)


def git_env(ws: Path) -> dict[str, str]:
    return {
        "GIT_CONFIG_GLOBAL": str(ws / "gitconfig"),
        "GIT_CONFIG_NOSYSTEM": "1",
    }


def setup_environment(
    ws: Path,
    *,
    inherit: list[str],
    store_env: dict[str, str] | None = None,
    agent_env: dict[str, str] | None = None,
) -> dict[str, str]:
    """Allowlisted environment for a setup command.

    Per-agent values are included only when `agent_env` is passed
    (`--setup-per-agent`). Shared setup and the copy-on-write fallback omit
    them so an install cannot bake one peer's ports into a tree. Each clone's
    runtime shell still loads its own `.murmur/env.sh`.
    """
    env: dict[str, str] = {}
    for key in SETUP_INHERIT:
        value = os.environ.get(key)
        if value:
            env[key] = value
    for key in inherit:
        if key not in os.environ:
            fail(f"setup_env {key!r} is not set in the environment")
        env[key] = os.environ[key]
    env.update(git_env(ws))
    if agent_env:
        env.update(agent_env)
    if store_env:
        # Wins over agent_env when that would point pnpm outside the workspace.
        env.update(store_env)
    return env


def npmrc_store(clone: Path) -> Path | None:
    npmrc = clone / ".npmrc"
    if not npmrc.is_file():
        return None
    for raw in npmrc.read_text().splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line.lower().startswith("store-dir"):
            continue
        _, _, value = line.partition("=")
        value = value.strip().strip('"').strip("'")
        if not value:
            return None
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = clone / path
        return path
    return None


def _inside_workspace(path: Path, ws: Path) -> bool:
    try:
        path.resolve().relative_to(ws.resolve())
    except ValueError:
        return False
    return True


def store_override(ws: Path, clone: Path, agent_env: dict[str, str]) -> dict[str, str]:
    """Keep pnpm's store inside the workspace unless the project already does.

    An in-workspace `store-dir` (or an in-workspace `npm_config_store_dir` in
    agent_env) is left alone. Anything else, including the user's global store,
    is overridden for setup and for agent shells. The directory is removed with
    the workspace.
    """
    candidates: list[Path] = []
    if agent_env.get("npm_config_store_dir"):
        candidates.append(Path(agent_env["npm_config_store_dir"]).expanduser())
    configured = npmrc_store(clone)
    if configured is not None:
        candidates.append(configured)
    for path in candidates:
        resolved = path if path.is_absolute() else (clone / path)
        if _inside_workspace(resolved, ws):
            return {}
    store = ws / "pnpm-store"
    store.mkdir(parents=True, exist_ok=True)
    return {"npm_config_store_dir": str(store)}


def runtime_shell_env(ws: Path) -> dict[str, str]:
    """Environment Codex injects into every agent shell command.

    Per-agent values are not here: one session cannot hold every peer's
    PORT_BASE. Shell startup in the clone loads `.murmur/env.sh` instead.
    HOME points at the workspace so login bash and zsh do not read the
    user's dotfiles. Codex is also told not to source the user shell profile.
    """
    path = os.environ.get("PATH", "")
    env = {
        "HOME": str(ws / "home"),
        "ZDOTDIR": str(ws / "shell"),
        "BASH_ENV": str(ws / "shell" / "bash-startup"),
        "ENV": str(ws / "shell" / "bash-startup"),
        "MURMUR_WORKSPACE": str(ws),
        "PATH": path,
    }
    env.update(git_env(ws))
    env["GH_CONFIG_DIR"] = str(ws / "gh")
    return env


def write_shell_files(ws: Path) -> None:
    shell = ws / "shell"
    home = ws / "home"
    shell.mkdir(parents=True, exist_ok=True)
    home.mkdir(parents=True, exist_ok=True)
    agent_env = shell / "agent-env.sh"
    agent_env.write_text(_agent_env_script(ws))
    agent_env.chmod(0o755)
    startup = "#!/bin/sh\n" + _source_line(agent_env) + "\n"
    (shell / "bash-startup").write_text(startup)
    for name in SHELL_STARTUP_NAMES:
        text = "# murmur workspace shell startup\n" + _source_line(agent_env) + "\n"
        (home / name).write_text(text)
        if name.startswith(".z"):
            (shell / name).write_text(text)


def _source_line(path: Path) -> str:
    return f". {shlex.quote(str(path))}"


def _agent_env_script(ws: Path) -> str:
    root = shlex.quote(str(ws))
    return f"""#!/bin/sh
# Generated by murmur. Sources `<clone>/.murmur/env.sh` when the working
# directory is inside this workspace, so each peer gets its own ports.
_murmur_root={root}
_murmur_dir="$PWD"
case "$_murmur_dir" in
  "$_murmur_root"|"$_murmur_root"/*)
    while :; do
      if [ -f "$_murmur_dir/.murmur/env.sh" ]; then
        . "$_murmur_dir/.murmur/env.sh"
        break
      fi
      if [ "$_murmur_dir" = "$_murmur_root" ]; then
        break
      fi
      _murmur_dir=$(dirname "$_murmur_dir")
    done
    ;;
esac
unset _murmur_dir _murmur_root
"""


def write_env_sh(clone: Path, env: dict[str, str]) -> None:
    lines = ["# Generated by murmur. Sourced for shells started in this clone.", ""]
    for key, value in env.items():
        if not _ENV_NAME.fullmatch(key):
            fail(f"invalid environment variable name {key!r}")
        lines.append(f"export {key}={shlex.quote(str(value))}")
    lines.append("")
    path = clone / ".murmur" / "env.sh"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))


def write_bin(ws: Path) -> None:
    bin_dir = ws / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    python = shlex.quote(sys.executable)
    pythonpath = os.environ.get("PYTHONPATH")
    export = f"export PYTHONPATH={shlex.quote(pythonpath)}\n" if pythonpath else ""
    attest = bin_dir / "murmur-attest"
    attest.write_text(
        "#!/bin/sh\n"
        "set -eu\n"
        f"{_source_line(ws / 'shell' / 'agent-env.sh')}\n"
        'if [ -z "${MURMUR_AGENT:-}" ]; then\n'
        '  echo "murmur: MURMUR_AGENT is not set; run this from your clone" >&2\n'
        "  exit 3\n"
        "fi\n"
        f"{export}"
        f"exec {python} -m murmur attest --workspace {shlex.quote(str(ws))} "
        '--agent "$MURMUR_AGENT" "$@"\n'
    )
    attest.chmod(0o755)
    runner = bin_dir / "murmur-sh"
    runner.write_text(
        "#!/bin/sh\n"
        "set -eu\n"
        f"{_source_line(ws / 'shell' / 'agent-env.sh')}\n"
        'exec "$@"\n'
    )
    runner.chmod(0o755)


_ENV_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
