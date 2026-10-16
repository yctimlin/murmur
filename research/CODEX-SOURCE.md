# Codex 0.162.1: source audit and product comparison

Audit date: 2026-10-16. Scope: the supplied read-only checkout at
`/workspace/codex-src-0.162.1`, revision
`092d3acd6bec3e3a14bdc7e7a2810ab628ab759d`. Its workspace manifest declares
`0.162.1` ([manifest](https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/Cargo.toml#L163)).
The linked source locations were inspected in the supplied checkout; public availability of
this exact revision on GitHub was not verified. This is static source inspection, not execution
of the Rust tests or a live-model benchmark. No file in the source checkout was changed.

## Product comparison

OpenAI's official subagent documentation describes delegation to separate agent threads,
parallel execution, follow-up instructions, and collection of results in the main thread. It
recommends read-heavy parallel work such as exploration, tests, triage, and summarization,
and cautions about parallel writes. It explains that separate agent threads keep intermediate
logs and exploration out of the main conversation, while reporting higher token use than a
single agent. The fetched page provides mechanisms and guidance, not a controlled numerical
speed/quality/token comparison against murmur. This differs from murmur's equal peers and
shared private Git origin: Codex's documented workflow has a parent collecting delegated
results. [Official subagents documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents)
(accessed by following the redirect from `https://developers.openai.com/codex/multi-agent`).

Codex's Git-worktree documentation describes parallel chats with separate working trees and
branch ownership, plus handing a chat between a local checkout and a worktree. It explains
that Git does not let separate worktrees check out the same branch simultaneously. This is
an isolation mechanism; the page does not establish automatic semantic merge correctness
or a performance advantage for worktrees over murmur's clones.
[Official Git-worktree documentation](https://learn.chatgpt.com/docs/environments/git-worktrees)
(accessed by following the redirect from `https://developers.openai.com/codex/app/worktrees`).

## Mechanisms verified in source

| Mechanism | Verified behavior | Consequence for murmur |
|---|---|---|
| V2 context forking | Omitted or empty `fork_turns` defaults to `all`; `none` returns no fork mode. Legacy positive turn counts still mean full history, not a bounded slice. [spawn parser](https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/core/src/tools/handlers/multi_agents_v2/spawn.rs#L279) | Request `fork_turns="none"` explicitly when a peer's complete brief already lives in its instruction file. Do not implement a fake "last N turns" optimization. |
| Fresh child configuration | Child setup starts from the parent's effective config, copies captured model and reasoning settings, and copies live approval policy, cwd and permission profile. A fresh child still receives those runtime settings. [child config](https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/core/src/agent/child_config.rs#L109) | Dropping parent conversation history does not mean dropping sandbox configuration. Peer files must carry all task context. |
| Fresh thread startup | The no-fork branch starts a new thread, retains parent-tree identity, inherits environments and execution policy, and conditionally inherits dynamic tools. A source test checks that a fresh child's history lacks parent-only context. [startup](https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/core/src/agent/control/spawn.rs#L779), [test](https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/core/src/agent/control_tests.rs#L2234) | Fresh conversations remain part of the agent tree. Source tests were read, not run. |
| V2 waits | `WaitArgs` denies unknown fields and contains only optional `timeout_ms`; it takes no agent IDs. A wait returns on mailbox activity, steered user input, or timeout. [arguments and result](https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/core/src/tools/handlers/multi_agents_v2/wait.rs#L142), [wake behavior](https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/core/src/tools/handlers/multi_agents_v2/wait.rs#L202) | Correct the root instruction that requested every agent ID. A wake is not proof all peers finished; retain the `list_agents` check after each wake. |
| Wait bounds and thread capacity | The default V2 per-session thread setting is 4; wait default/max is 3,600,000 ms and the hard max equals it. `effective_agent_max_threads` subtracts one from the session limit for child capacity. [defaults](https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/core/src/config/mod.rs#L257), [child capacity](https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/core/src/config/mod.rs#L1633) | `peers + 1` remains the correct session limit; long root waits avoid needless polling. |
| Reasoning effort | The child copies the captured effective effort. In model normalization, `multi_agent_reasoning_effort` is consulted for the `Ultra` alias; ordinary efforts pass through. A test explicitly checks that `High` stays `High`. [inheritance](https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/core/src/agent/child_config.rs#L109), [normalization](https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/protocol/src/openai_models/reasoning_effort.rs#L8), [test](https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/core/tests/suite/subagent_notifications.rs#L577) | The old blanket README claim that all children use catalog effort instead of session effort is unsupported for this version. Avoid rewriting catalog effort merely to preserve ordinary configured effort. |
| Model-owned multi-agent mode | Effective multi-agent mode uses an explicit config override, then catalog model metadata, then feature fallback. [resolution](https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/core/src/config/mod.rs#L1624) | Disabling a legacy feature alone need not defeat model catalog mode; solo isolation must account for both. |
| Cache identity | `prompt_cache_key` normally uses the request metadata's session ID; an explicit override wins, and internal sessions can use a parent-scoped key. Non-root agents keep their own session identity for response headers. [cache key and response session ID](https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/core/src/client.rs#L581) | Do not assume every peer shares one cache or that forked history is free. Source does not prove actual backend cache-hit rates. |
| Request construction | Responses requests include input, tools, reasoning, and a prompt cache key. [request builder](https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/core/src/client.rs#L998) | Model-visible input and uncached input are different accounting quantities. Request construction alone does not establish billed cost. |
| Compaction threshold | Token status distinguishes full active context from tokens after a prefix, consults configured/model limits, and also enforces the model's full context window. [context accounting](https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/core/src/session/context_window.rs#L53) | A universal hardcoded compaction threshold would ignore these model/config differences; leave compaction with Codex and user configuration. |
| Compaction implementation | Auto-compaction chooses token-budget handling when enabled, otherwise remote V2 or local compaction based on provider capability. [dispatch](https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/core/src/session/turn.rs#L1434) | A remote compaction assumption does not generalize to every provider. No quality-preservation guarantee is established here. |
| Message-board delivery | The adapter never starts/restores recipients or queues notices for idle agents. It delivers to the current active turn with `trigger_turn=false`; inactive delivery is skipped. Posts are separate from notifications. [board adapter](https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/core/src/agent_message_board.rs#L1), [notify](https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/core/src/agent_message_board.rs#L204) | Posting on the board does not wake a finished peer. Coordination that requires another turn needs the explicit follow-up mechanism. |
| Board storage | Local non-ephemeral mode opens a local board using SQLite config; remote and explicitly in-memory variants also exist. [installation](https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/core/src/agent_message_board.rs#L36) | Do not confuse persistent post storage with guaranteed notification delivery. |

The deeper sandbox audit is owned by the separate coordination/source survey. This file's
sandbox conclusion is deliberately narrow: inherited permissions are verified; per-peer clones
are not proven security boundaries by the fresh-thread change.

## Ranked improvements from this audit

1. **Correct V2 wait arguments.** Strong source evidence: the current root prompt conflicts
   with a deny-unknown-fields parser. Prompt rendering tests cover the corrected call shape;
   no live-model compliance claim is made. Source: V2 wait links above.
2. **Use two peers by default, retain explicit overrides.** Moderate task-specific evidence:
   in both rows of the prior two-versus-three-peer lean comparison, the two-peer arm used less
   total and uncached input. The `lean2` and `lean3` arms used the same build, so peer count
   is the comparison of interest; their shared build differed from base. The sample is small,
   and neither outcome proves a general 1.5–2x token target or quality parity. Source:
   [prior lean2 results](evidence/lean2-RESULTS.md),
   [prior plan](evidence/lean2-PLAN.md). These repository-relative evidence URLs refer to
   supplied data, not independently reproduced experiments.
3. **Start peers with fresh conversation history.** Strong source evidence for removing
   inherited conversation; plausible, unmeasured efficiency benefit. The launcher has no
   task-solving content to preserve, while each peer already gets a full instruction file.
   This is a structural optimization, not another instruction to "use fewer tokens."
   Source: spawn parser, startup, and child-config links above; murmur regression test
   `test_default_swarm_launches_two_fresh_peers_with_complete_prompts`.
4. **Respect configured model/effort and leave compaction unpinned.** Strong correctness
   argument from the explicit project requirement plus source resolution behavior; no token
   reduction claimed. Source: child config, effort normalization, context accounting above.
5. **Measure child-thread total and cached usage before adding cache or context heuristics.**
   Strong need for measurement, weak evidence for any proposed heuristic: cache key construction
   does not disclose actual backend hit rates. Source: cache key and request-builder links above.

## Validation and limits

Draft `fb5ebaa` changes the default to two peers, requests fresh forks, and corrects the wait
instruction. ` .venv/bin/python -m pytest -q ` passed **34 tests in 9.41 seconds** in a2's clone
on 2026-10-16; these tests use the repository's fake Codex and temporary Git repositories.
The run used **zero model calls and zero model tokens** for validation; agent research and
implementation inference costs are not measured by that number. Exact new behavioral checks
are in [configuration tests](../tests/test_config.py) and [setup tests](../tests/test_setup_git.py)
in that draft. No live Codex swarm,
Rust test suite, server-side cache behavior, sandbox escape resistance, numerical speedup,
quality parity, or token-ratio improvement was validated.
