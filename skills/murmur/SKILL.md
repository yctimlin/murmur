---
name: murmur
description: Run a leaderless swarm of Codex agents (murmur) on one objective in an isolated copy of a repo, then review the result as a branch. Use when the user asks for a swarm, peer agents, "murmur", several Codex agents working together on one feature, or wants a large or broad task done faster by parallel agents. Also covers watching a running swarm and reviewing what it delivered.
---

# murmur: a leaderless Codex swarm

`murmur` starts N Codex agents as equal peers on one objective. They share a private git `origin`
and Codex's built-in message board, claim work, and attest one final commit. There is no
manager: a root session only spawns the peers and waits. The launcher, not a peer, checks that
every peer attested that same commit. Nothing leaves the workspace until you fetch the result
into the user's repo as a branch.

## When to use it

- **Good fit:** broad work that splits into parts, such as a feature spanning API, UI, docs and
  tests, or many independent changes. In a pilot on a real UI feature, 4 peers finished in 46 min
  where a single agent took 120 min.
- **Weigh it:** for work where craft matters more than speed, especially visual polish. In the same
  pilot the single agent's UI was richer and better on mobile; the swarm's was safer but plainer.
- **Poor fit:** small or tightly coupled changes. Use one agent, for example the `codex` skill.
- `murmur setup --solo` runs one agent with the same isolation, as a baseline.

## Prerequisites

```bash
murmur --help                  # installed? if not: uv tool install --editable <murmur repo>
codex --version                # needs 0.162 or later (built-in message board)
codex login status
```

## 1. Write the brief

The brief is the only thing the agents read about the task. Agents cannot ask questions, so:

- State the problem, the outcome the user wants and hard constraints: what must not change, what
  is out of scope, what "done" looks like.
- Leave design decisions to the agents, unless the user has made them.
- Name the open questions you want answered, and ask for the decisions to be justified in `PR.md`.
- Say how the result can be verified locally. Agents have network access. GitHub git URLs are
  rewritten to a dead path and `gh` is not logged in; that is not a network firewall, and there
  are no credentials for third-party APIs.

Save it as a markdown file outside the repo, or in a scratch location. Show it to the user before
the run when the task is large.

## 2. Set up the workspace

```bash
murmur setup brief.md --repo <repo> --peers 4 \
  --setup "cp .env.example .env" --setup "pnpm install --frozen-lockfile"
```

- The agents start from `HEAD` (or `--base <ref>`). Uncommitted changes are not included; murmur
  warns when there are some.
- `--setup` runs once in the first clone; the other clones are copy-on-write copies of that
  tree (`cp -c -R` on macOS, `cp --reflink=always -R` on Linux). If the copy fails, murmur
  keeps the first clone and runs setup in the remaining clones in parallel. It does not fall
  back to a plain copy. If the install embeds absolute paths (virtualenvs, node shebangs), pass
  `--setup-per-agent` so the command runs in every clone instead.
- Setup sees an allowlisted environment, not the host's secrets. Pass a variable through only
  with `--setup-env VAR` when the install truly needs it. Never pass secrets.
- `--peers 2` is often as good as 4. `--cap` defaults to `3h`.
- Each agent's `PORT_BASE` is exported for shells that start in its clone. You do not paste it
  into the setup command.
- The last line of the output is the workspace path, under `~/.murmur/runs/<id>`.

## 3. Run and watch

Launch with the Bash tool and `run_in_background: true`, so you are notified when it ends:

```bash
murmur run <workspace>
```

Check progress every few minutes, and give the user a one-line update after each check:

```bash
~/.claude/skills/murmur/scripts/status <workspace>
```

It shows elapsed time, `spawned N/N peers`, each agent's last activity and tokens, the latest
board posts and new commits on `origin/main`.

- `murmur run` exits 0 only when a solo Codex run exits 0, or when every peer attested the same
  `origin/main` commit. Exit 1 is a Codex failure, 2 is the time cap, 3 is a launcher error,
  4 means the protocol is incomplete, and 130 means the run was interrupted. A non-zero exit
  still prints the fetch command and the log path.
- If `spawned` is below N, stop the run: the peers would be working short-handed. The durable
  result is `logs/state.json` (`protocol`), not the spawn line alone.
- To stop a run, stop the background task. murmur signals the Codex process group and records
  `interrupted`.
- A second `murmur run` on the same workspace exits 3 while the first holds the lock. If the
  launcher died, `murmur run --recover <workspace>` closes the stale attempt and starts another.

## 4. Bring the result back

`murmur run` ends by printing the fetch command:

```bash
git -C <repo> fetch <workspace>/work/origin.git main:murmur/<id>
```

This only creates a local branch. Do not merge, commit or push for the user. `PR.md` at the
branch root is the agents' summary: in a swarm it opens with the plan the peers agreed on and the
drafts they chose between, then covers what changed, their decisions, how they verified it, and
"How to see it". The drafts that lost stay on `draft/<id>` branches in `origin.git`; fetch them
too when the user wants to see the alternatives. Use it as the PR description, and drop the file from the branch before merging.

## 5. Review it properly

Green tests written by the same agents are not acceptance. Review the diff line by line, and for
UI work, open "How to see it" and look at it: desktop and phone widths, reduced motion, every
state. Check the result against the plan in `PR.md`. Things the pilot swarm got wrong, which are
worth checking first:

- **Plain, safe choices.** Peers converge on the least risky option. Judge whether it is good
  enough, not just correct.
- **Layout at narrow widths.** Pieces built by different peers are rarely checked together on a
  phone.
- **Invasive plumbing.** The swarm changed the app's root layout and auth middleware to host a
  demo page. Look for edits to shared infrastructure made only for convenience.
- **Unreachable states.** Check that every state the UI can show is fed by real data, not only by
  fixtures. A single agent shipped a stage that real runs could never fill.

Run the repo's own checks yourself (typecheck, lint, tests, build) on the fetched branch.

Read what `PR.md` says could not be done, then check that no agent worked around the
environment's limits to do it anyway: search the rollouts in `codex-home/sessions/` for commands
that touch paths outside the workspace, credential files, `~/.codex` or GitHub.

## Safety model

- Each agent works in its own clone; the only remote is the workspace's `origin.git`.
- GitHub git URLs (`https`, `http`, `git://`, `ssh://`, `git@github.com:`) are rewritten to a
  dead path, and `gh` has an empty config directory so it is not logged in. This is not a
  network block: Codex still has network access, and `curl https://github.com` can succeed.
- Agent shells inherit Codex's core environment, not the full host environment. Their `HOME` is
  the workspace home, `ZDOTDIR` is the workspace shell directory, and `BASH_ENV` / `ENV` point at
  workspace scripts, so bash and zsh do not read the user's dotfiles. Names containing `KEY`,
  `SECRET`, or `TOKEN` are dropped. Setup commands see an allowlist plus any `--setup-env` names.
- Each run has its own `CODEX_HOME` with only the model provider and auth: no plugins, memories or
  past sessions.
- This guards against accidents, not a determined agent: the Codex sandbox can still read the
  disk. The Codex process itself still receives the launcher environment.

## Where things are

| Path in the workspace | Contents |
|---|---|
| `murmur.json` | Run settings, base commit, agents, ports |
| `prompts/` | The exact prompt each agent received |
| `logs/state.json` | Versioned state: `ready`, `running`, `succeeded`, `failed`, `capped`, `interrupted`, plus the protocol |
| `logs/attempts/<id>/` | That attempt's `session.jsonl`, `session.err`, and `record.json`. Later attempts do not truncate these |
| `logs/run.json` | Summary of the latest attempt only |
| `protocol/<id>.json` | That peer's attestation for this attempt |
| `codex-home/sessions/` | One rollout per agent: commands, edits, tokens |
| `codex-home/agent_message_board_1.sqlite` | Board posts (`posts` table, plain text) |
| `work/origin.git` | The result; its reflog has a timestamp for every push to `main` |

Workspaces with installed dependencies are large. Delete `~/.murmur/runs/<id>` once the result is
fetched and reviewed.

## Known limits

- Codex's agent message board is still marked "under development".
- The root's spawn messages are encrypted in the logs; each agent's first action is reading its
  own prompt file, which shows what it received.
- The swarm is tuned for `gpt-6-astra`. With other models, check `status` early for spawn
  failures.
