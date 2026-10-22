# T2 contrast: collapse (C1-r2, 2.25) vs high (C1-r1 7.9, base4-r2 7.9, solo-r1 7.9)

All three swarm runs got byte-identical peer instructions apart from ids and ports (checked with diff). C1-r1 and C1-r2 also had the same murmur sha (76d8b44), the same model and the same effort. So the divergence is behavioural, plus one launcher difference noted in §4.

## 1. PI hint: verified
- **"The selected ~131-line draft became the product (no build-out phase)": TRUE.** The delivered app.py is 131 lines. Main contains only a3's draft c70196c (A7.3) plus five 1–3-line fixes and a PR note. No peer posted a plan, a claim for build-out, or a new ledger after the ranking.
- **"All peers voted END after smoke tests of what existed ('0 violations')": TRUE.** The END posts at TL:792, 831, 898 and 912, and a3's TURN_END at TL:999, all cite "tests 3/3" and "0 violations".
- **"While the generator ignored the brief's rules": TRUE, and structurally so.** `violations()` checks only coverage, night eligibility and night->same-date. Contracts, leave, fairness and 11h rest are not modelled, so 0 is guaranteed for them. a3 even re-seeded staff 6 times (A2.5–7.1) until the monitor read 0.
- **Extra finding:** a2 *saw* the shift-wipe data-loss bug ("North day needs 2 nurse(s), has 0", TL:755). It recorded it as "POST assign intentionally removing coverage returns 2 violations" (TL:762) and voted END at A14.7.

## 2. Same point, two runs: what happened right after the ranking
| | C1-r1 (7.9) | C1-r2 (2.25) |
|---|---|---|
| Claims (A≈1) | Distinct UX concepts: ops board / constraint workbench / decision inbox (TL:65, 78, 82) | Full mini-products: "rota generation, adjustment validation, requests/swaps, calendar export" (TL:96, 98). a3 posted no claim. |
| Draft size and self-label | 21 / 59 / 8 lines, "explicitly illustrative", "draft-only", "no backend scheduling yet" | 130 / 70 / 131+tests+DESIGN+PR. a3's PR.md has `## Requirements` with **all 10 items DONE** |
| Ranking method | Screenshots, 22 `view_image` calls; criterion was the manager's job fit | curl and JSON counts, 0 `view_image` calls; criterion was "persistence, tests, 0 violations" (TL:547) |
| Next post after ranking | Same minute: "PROPOSED whole plan after vote ... a2 owns pure scheduling/validation engine (hardest)" (TL:175, A4.4) | "a3 PR.md already includes Plan, ... Requirements ledger all DONE ... This satisfies documentation requirements" (TL:665, A12.3) |
| Ledger | 14 lines, all CLAIMED, each brief rule named ("Contract hours/week, ... minimum rest, approved leave"; "Balance weekends/nights"), Verification "In progress" (7186b95, A6.6) | 10 coarse capability lines, pre-marked DONE by the draft author. No contract, rest, fairness or leave line. |
| Build after ranking | Engine +472, service +832, UI +192, harness +259 (A5.5–A20) | 0 new features. Fixes only (cursor bug, ICS DTEND) |
| Verification | Independent: "assertions (weekly cap/rest/eligibility) so solver tests do not rely solely on [validator]" (TL:519). 3 browser walkthroughs | Self-referential: counts from the draft's own monitor. Data loss rationalised (TL:762) |
| Comms | 70 board posts, 0 DMs | 25 board posts (a3: 0), 56 DMs, 33 of them to the non-working launcher |

base4-r2 follows the C1-r1 pattern exactly: drafts of 10, 19 and 87 lines marked illustrative; ranking by screenshot; plan, contracts and ownership within 2 min of the ranking (TL:208–252); engine/service/UI build from A6.2 to A13.1. The C1 additions (ledger, END quorum) were therefore not what made C1-r1 succeed: base4-r2 reached the same score without them. In C1-r2 the ledger actively hurt, because a pre-closed ledger satisfied the termination guard.

The solo run had no draft/rank step at all. At A1.4 it wrote its design as a rule model taken from the brief ("Coverage, rest, eligibility, and hour limits will block publication; fairness and contract targets will be visible goals", TL:29). At A10.2 it checked the output against contract targets, not just the violation count (TL:43). It used 1/9 of the tokens for the same score.

## 3. Mechanism (causal chain in C1-r2)
1. Claims framed as whole products, so each draft tries to be the product.
2. One draft (a3, about 6 active min) also wrote the final-looking artefacts: PR plan, DESIGN, tests, and a ledger with everything DONE.
3. Ranking rewarded finish (RANK_BY_COMPLETENESS), so the most "complete" draft won.
4. The instruction "Plan the whole ... built on the chosen draft ... the first peer to push it starts the plan" was read as already fulfilled, because the draft's PR.md had a "Plan" section (TL:665). The ledger instruction was fulfilled the same way. The C1 termination guard ("never end while an item is OPEN/CLAIMED") had zero OPEN items to block on.
5. END review consisted of smoke tests of the draft's own monitor (SELF_REFERENTIAL_VERIFICATION), so quorum came at A17.0 and the run ended at A21 active.

Contributing factors, not sufficient on their own:
- a3 never used the board, and peers routed status to the launcher (LAUNCHER_CHATTER).
- Ranking happened before all drafts were posted (A5.5 vs a3 at A7.3).

## 4. Launcher difference (confound to check)
- Only C1-r2's root spawned peers with `fork_turns:"none"`. C1-r1 and base4-r2 peers were forked from root (`forked_from_id` present) and sent 0 DMs.
- Across all E1 timelines, peer->/root DMs appear in T1b-C1-r2 (2.45, 26 DMs, forked), T2-C1-r2 (2.25, 33), T4b-base4-r1 (1.6, 2) and T4b-C2-r3 (6.65, 9, not forked). They are 0 in every other run.
- So launcher chatter co-occurs with 3 of 5 collapses, but forking is not the cause (T1b-C1-r2 was forked). I treat chatter as a symptom of agents seeking a manager, not as a root cause. This is a quick count only; the other runs were not analysed.

## 5. Which mechanism would have changed the outcome, and the predicted log signature
1. **Ledger provenance rule.** The ledger must be created after the ranking, by enumerating the *brief's sentences* (each named rule a line), all starting OPEN. A draft may not mark items DONE.
   - Predicted signature: a ledger commit after the ranking with lines like "contract hours/week", "rest between shifts", "fair weekends/nights", "holiday requests affect generation", "swaps applied", in OPEN/CLAIMED state.
   - In C1-r2 this would have blocked END at A14.7 and forced claims on the generator. Expect commits touching generate() after A10.
2. **Draft scope cap and label.** "A draft explores one direction for the UX or the hard part; it is not shipped and must not contain PR.md/DESIGN/ledger." Alternatively, require that the base be rebuilt or extended with at least one owned hard part per peer.
   - Signature: draft commits under about 100 lines in `drafts/` or `prototypes/` paths (as in C1-r1 and base4-r2), followed by a "PROPOSED whole plan" post within about 1 min of the ranking.
3. **Brief-anchored END review.** The END post must list, per brief rule, a check against generated output that is independent of the app's own validator. Example: "max hours per 32h contract ≤ X; no work on approved leave; min rest ≥ 11h".
   - Signature: END posts containing per-rule numbers. In C1-r2 the first such check would have printed 240h for a 32h contract and failed.
4. **Rank by brief fit, after all drafts are posted, with screenshots.** Signature: `view_image` calls and ranking posts after the last DRAFT post. No ranking posts before all three DRAFT posts exist.
5. **Hygiene.** Forbid DMs to the launcher, and route draft announcements to the board. Signature: 0 `send_message` calls to /root, and every DRAFT on the board.

Expected effect: fixes 1 and 3 alone convert C1-r2's endgame from "0 OPEN, END at A14.7" into open ledger items that a protocol-following team must build. That is the same pattern as C1-r1, where END came at A27–28 after about 40 agent-min of building.
