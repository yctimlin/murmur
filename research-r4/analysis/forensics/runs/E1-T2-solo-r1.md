# E1-T2-solo-r1 (T2 clinic shift planner, solo) — HIGH 7.9

## 1. Outcome
- Score 7.9 (j1 7.9, j2 7.9). No severe issues.
- Top penalties:
  - Code 7: "44 lines run past 200 characters and the stylesheet is a single minified line".
  - "the 'Regenerate draft' button still shows on a published month".
  - When leave conflicts, "only blocks the approval and does not suggest a reassignment".
  - "Hours fall short of contract targets (21 soft warnings, up to −43h for one nurse). This is the stated design".
  - README links to a PR.md the judge did not see. PR.md is in delivered/ (41 lines), so this is packaging.
- Delivered: about 2,037 lines of code. Main parts: domain.py 225, solver.py 198, service.py 332, db.py 96, exports.py 97, web.py 125, app.js 229, tests 567 (47 tests).
- 1 commit, b5ec4f4 (+2385). Active 26.0 timeline span (result.json 36.24), wall 133.8. Tokens: input 1.82M (about 1/9 of the swarms), output 60k. Mutation 0.63 (highest of the four).

## 2. Phase timeline (active minutes)
| Phase | A | What happened |
|---|---|---|
| Probe env | 0.1–1.4 | Checked Python, scipy and ortools availability (TL:20–29). |
| Rule-first design | 1.4 | "One rule checker will cover generation, manual edits, leave approvals, and swaps. Coverage, rest, eligibility, and hour limits will block publication; fairness and contract targets will be visible goals" (TL:29). |
| Build core | 3.1–9.2 | pyproject/domain (TL:30), db.py (TL:32), service.py (TL:34), first generation "multistart greedy + displacement repair ... unfilled: 0" (TL:36–37), exports (TL:39). |
| Check result vs rules | 10.2 | "filled all 450 required positions ... zero hard-rule violations ... some staff remain below their contract targets because the clinic needs fewer shift hours than it has contracted. I'll show that gap clearly" (TL:43). |
| UI | 12.2–14.2 | index.html, app.js (TL:44, 46). |
| Browser attempt | 14.4–16.0 | Socket creation blocked in sandbox. Chrome exit 133. "I'll test the HTTP handlers directly and record the live-browser verification limit" (TL:52). |
| Tests + fixes | 18.0–22.6 | 47 tests: DST, month-boundary rest, rollback, concurrency, leave, swap consent, stale swap, ICS cancellations (TL:53, 71). |
| Docs, commit | 24.6–26.0 | README, PR.md, commit b5ec4f4 (TL:72–83). TURN_END "47 tests pass ... Live-browser verification was blocked by sandbox socket restrictions" (TL:87). |

## 3. Agent account
A single agent. It built the whole product. It ran `date -u` 3 times (TL:41, 57, 74), so it was aware of wall time, but there was no visible rushing: it kept writing tests and docs after each check. It ended after a full test pass and documentation, with limits stated.

## 4. Coordination costs
None. Single agent.

## 5. Penalty -> cause map
| Penalty | Cause |
|---|---|
| Under-contract hours | A conscious design decision at A10.2 (TL:43): fill minima only and display the shortfall. |
| No reassignment suggestion | Never planned. Leave approval was designed as block-only. |
| Regenerate button on published month | UI detail. No browser check possible (socket blocked, TL:52). |
| Dense code | Single-shot file writes of 11–37k characters (TL:44, 46). |

## 6. Decision points
1. A1.4: one rule checker shared by generation, edits, leave and swaps, with hard vs soft rules enumerated from the brief (TL:29).
2. A10.2: generated output inspected against contract targets, not only the violation count (TL:43).
3. A16.0: substituted handler-level tests when the browser was impossible (TL:52).

## 7. Failure-mode tags
NONE of substance. WALLCLOCK_RUSH: not observed (3 `date -u` checks, no shortcutting). Verification was limited by the sandbox (no live browser) and this was disclosed.

## 8. Time accounting (active min, estimates)
Building about 15, testing about 7, environment probing about 2, docs about 1.5, idle/long generation about 1 (gap A14.6+3.3 is the app.js write).
