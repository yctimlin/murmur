# One-peer protocol instrumentation

- Question: Can the protocol be measured with one peer while retaining the full swarm root and board behavior?
- Method: Gate `--peers 1` behind `MURMUR_ONE_PEER_PROTOCOL=1`. When enabled, setup writes swarm metadata, creates an `a1` clone, and renders `root.md`; without the switch, `--solo` retains solo mode and ordinary swarm validation still requires at least two peers.
- Prediction: The switch should isolate protocol overhead from parallelism while leaving default CLI behavior unchanged.
- Raw-data path: `tests/test_one_peer_protocol.py`.
- Result: Commit `2256a2a` implements the switch and its setup validation. Both regression tests pass (`2 passed`), confirming swarm metadata/root prompt with the switch and solo behavior by default.
- Decision: Keep the switch internal and environment-controlled as required; use it only for the phase's paired protocol-vs-parallelism batch.
