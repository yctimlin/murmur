# Contributing to murmur

Thanks for helping. Bug reports, reports from real runs, and pull requests are all welcome.

## Reporting a problem

Open an issue with the bug report template. The most useful things to attach from the workspace
(`~/.murmur/runs/<id>`) are `murmur.json` and `logs/run.json`, plus `codex --version`, your OS and
the filesystem the workspace is on (copy-on-write setup needs APFS, btrfs or xfs). Do not attach
anything from `codex-home/` (its `auth.json` links to your Codex login), API keys, or anything
from your brief or repository you would not post in public.

Reports of real runs are welcome too, good or bad: the task size, peers, time, tokens and how the
result compared with a single agent. murmur's claims are only as good as the measurements behind
them.

## Development setup

You need Python 3.11 or later and git. Codex is not needed to run the tests.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[test]"
python -m pytest -q
```

## How the tests work

The tests never call a model. `tests/conftest.py` puts `tests/fake_codex.py` on `PATH` as `codex`
for every test and gives each test its own `HOME` and temporary directory. The fake answers
`codex debug models` with a small catalog, and its behaviour for `codex exec` is chosen with
`MURMUR_FAKE_CODEX_MODE`: exit cleanly, fail, push a commit to `main` or to a draft branch, hang
until signalled, and so on. The docstring at the top of `fake_codex.py` lists the modes.

`tests/support.py` has the helpers most tests need: `init_repo` makes a throwaway git repo with a
brief, `setup_workspace` runs `murmur setup` against it, and `run_cli` runs `python -m murmur` as a
subprocess. To cover a new Codex behaviour, add a mode to the fake rather than mocking inside
`murmur`.

## Pull requests

- Keep each pull request to one change, and add or update a test for every behaviour change.
- Run `python -m pytest -q` before pushing. CI builds the wheel on Linux and macOS, installs it in
  a clean virtualenv, and runs the same suite.
- Update `README.md` and `skills/murmur/SKILL.md` when you change options, exit codes or
  workspace files.
- Claims about speed, quality or cost need evidence. Say what you ran (task, peers, model,
  repetitions) and link the data. A single run is an anecdote, not a result.
- Say in the description what changed, why, and how you tested it.

By contributing, you agree that your contributions are licensed under the [MIT License](LICENSE).
