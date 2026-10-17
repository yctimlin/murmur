# Final raw noise audit, planning sensitivity, and full suite (a3)

- Question: Can the final report reproduce the actual A/A cost noise, provide honest sealed-evaluation sizing inputs, and document a green bug-fix foundation?
- Method: Independently loaded immutable C1/C2 `jobs.json` and result JSON files without importing the primary analyzer. Recomputed same-treatment means, sample SDs, CVs, paired log ratios and differences; kept task boundaries and three independent blocks per C1 comparison. Ran `.venv/bin/python -m pytest -q` in the a3 clone at `8f77689`. Compared source/tests with base3 using `git diff f95eaa1..HEAD -- src tests`.
- Prediction: The independent values will agree with the reviewed C1/C2 analyses; n=3 paired cost variability will imply substantially more than three pairs for modest cost changes. This is a post-experiment arithmetic audit and planning sensitivity, not a new preregistered claim or lab run.
- Raw-data paths: `research/data/raw/C1/`, `research/data/raw/C2/`. Reproduction: `python3 research/tools/final_noise_audit.py`; derived output: `research/data/final-noise-audit.json`.

## Result and sizing assumptions

C1 paired A/B log-ratio sample SDs, each from **three independent blocks**:

| Task | Endpoint | SD ln(A/B) | Illustrative pairs: 10% lower cost | Illustrative pairs: 20% lower cost |
|---|---|---:|---:|---:|
| ledger_replay | active minutes | .312076 | 69 | 16 |
| ledger_replay | input tokens | .286958 | 59 | 13 |
| ledger_replay | uncached tokens | .213865 | 33 | 8 |
| reserveplan | active minutes | .497428 | 175 | 40 |
| reserveplan | input tokens | .709067 | 356 | 80 |
| reserveplan | uncached tokens | .147051 | 16 | 4 |

The explicit planning model is a normal paired-log contrast with two-sided alpha=.05, power=.80, independent blocks, and unchanged variance: `N=ceil(((z(.975)+z(.80))*s/abs(ln(1-r)))^2)`, with z-sum=2.801585 and target reduction r. N is pairs, so N requires 2N run slots for a two-arm comparison. This plugs an estimated SD into a known-variance normal approximation. It is **not exact t-test power, a guaranteed minimum, a recommendation for four pairs, a multiple-endpoint correction, or a transportable long-task estimate**. Practical planning must re-estimate variance on admitted long tasks, allow across-task heterogeneity, and choose multiplicity and margins before evaluation. C2's three within-block pairwise differences are dependent and never provide three independent paired blocks.

With only three normal independent contrasts, an illustrative one-sided 95% upper SD bound multiplies s by `sqrt(2/(-2*ln(.95)))=4.4154` (chi-square df=2 CDF is `1-exp(-x/2)`). Substitution in the same formula multiplies unrounded N by 19.4957: the 20% reduction stress counts are ledger 300/254/141 and reserve 761/1546/67. This is a sensitivity to variance uncertainty under the model, not a required evaluation budget. It explains why the point sample-size outputs should not be taken as precise.

The per-run six-replicate C1 CVs reproduce ledger .1554/.1612/.1596 and reserve .2375/.3509/.1519 for active/input/uncached. C2 mean active=16.5267, SD=2.9010; input=1,025,845, SD=177,805.8; uncached=67,893, SD=8,904.7. All hidden-test scores equal 1, so the zero empirical score SD cannot size unsaturated quality evaluation. Delivery is 6/6 per base3 task and 3/3 for C2. Under an independent Bernoulli model, zero failures imply one-sided 95% failure-probability upper bounds `1-.05^(1/n)` = .3930 (n=6) and .6316 (n=3), already broad; shared concurrent blocks weaken independence further. Do not pool tasks to advertise stronger delivery reliability.

All 21 jobs total 95,707,328 input tokens, leaving 15 jobs and 354,292,672 tokens by raw arithmetic. Ledger bug-fix geometric ratios reproduce .966329/.900532/.830566; one-sided cost upper bounds remain 1.6452/1.5297/1.0171. Zero confirmatory eligible pairs means no noninferiority conclusion.

## Full suite and bug-fix foundation

The initial `python` command was unavailable and system `python3` lacked pytest; the existing repository virtual environment was used without changing dependencies. `.venv/bin/python -m pytest -q` returned **39 passed in 11.29s**. Source/tests have no changes after base3. Existing regressions cover no-work delivery detection, transient 429 retry, empty wait instructions and interruption cleanup, empty model catalog failure, and opt-in one-peer protocol construction. Phase-0 notebooks record independent peer reviews and runnable failing baseline comparisons. These deterministic regressions support the fixes' specified behavior; they do not establish long-task performance or reliability noninferiority.

## Decision

Provide these descriptive statistics and explicit planning assumptions to the final report; retain a null candidate. Require fresh long-task calibration and replicated paired experiments before protocol, peer-count, or quality claims. Peer a2 will independently review this audit and its arithmetic; a3 will review a1's final report against these raw numbers.
