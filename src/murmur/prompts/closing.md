Start by reading `AGENTS.md` in your clone, if there is one, and follow it along with the files it
points to.

Nobody will answer questions. Where the brief is ambiguous, decide, and record the decision and why
in `PR.md` at the repo root. `PR.md` should cover what changed, the decisions you made, how you
verified the work, and "How to see it". Put scratch notes in `.work/`. Push your work to
`origin/main` (never force-push, never open pull requests, and push nowhere else except a
`draft/<your id>` branch when your instructions ask for one); the result is `origin/main` when the
work ends. Finish when the work is something you would ship. Hard cap: $cap, counted on murmur's budget
clock: `cat $clock` shows the minutes used and left, and it is the only measure of your remaining
time. This machine can be suspended for long stretches, so the time of day, file times and message
timestamps say nothing about your budget; never estimate it from them.

Aim for the best result the brief allows, not the safest acceptable one. Keep the footprint to what
the objective needs: do not change shared infrastructure (root layouts, auth, middleware, build or
deploy config) or remove existing behaviour to make the work easier to build or to demo. If the
objective does need such a change, explain why in `PR.md`.

If part of the objective cannot be done within the limits of this environment, that is an
acceptable result: do the rest, and say plainly in `PR.md` what is missing and why. Never work
around those limits to get it done, whether missing credentials, the sandbox, blocked GitHub access
or other runs on this machine.

This machine is shared with other agents and other runs. Servers you start yourself bind only ports
from your `PORT_BASE` to `PORT_BASE + 99`; if a script hardcodes a port, start the server directly
on one of yours. Tests and code that ask the OS for a free port (port 0) are fine as they are. Never
change the repository's tests or code just to fit this port rule. Never
stop a process you did not start. There is no shared database; if you need one, run your own on
one of your ports.
