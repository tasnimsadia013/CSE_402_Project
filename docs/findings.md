# Findings from the supplied benchmark

These results use the documented defaults, not per-equation tuning. Raw data
and reproducibility metadata are in the linked output directories.

## Main comparison at 10^-14

All eight bracketed methods solve all fifteen paper equations. Among the three
proposed policies, **endpoint stagnation is the most effective signal in total
function evaluations** in this implementation. It uses 300 calls versus 325
for static TF, a 7.7% reduction, and beats static TF on 11 of 15 equations.
However, static BF uses only 273 calls, and the default adaptive methods do not
beat its aggregate cost. Static TF still takes far fewer iterations: 99 versus
222 for the stagnation-aware policy.

| Method | Total iterations | Total f calls | Successes |
|---|---:|---:|---:|
| Static BF | 122 | 273 | 15/15 |
| Static TF | 99 | 325 | 15/15 |
| Adaptive threshold | 382 | 458 | 15/15 |
| Cost-aware | 245 | 367 | 15/15 |
| Stagnation-aware | 222 | 300 | 15/15 |

Cost-aware switching beats static TF on eight problems, ties two, and loses
five. Its median per-problem cost ratio is 0.824 even though its **total** cost
is higher. These metrics answer different questions: a few costly cases can
outweigh small gains on many others. The rolling estimator's warm-up and stale
unselected-method estimates are plausible limitations of this precise greedy
implementation; these results do not reject every possible cost-aware design.

Adaptive threshold performs worst of the three in aggregate on this benchmark.
P11's trace shows why a residual-progress signal can miss endpoint locking:
small improvements keep passing the moving threshold for many iterations.
Rejected probes can then cost three evaluations. By contrast, the endpoint
counter intervenes directly in the failure mode specified by the proposal.

The measured Python timings in [the main report](../results/report.md) favor
the static hybrids over the adaptive variants in this run. Saving expensive
function calls could matter more for another workload, but no such workload
is claimed here. The benchmark equations themselves are cheap to evaluate.

## Sensitivity checks

All three policies still solve all fifteen equations at each tested tolerance.
The table counts all initial endpoint calls as well as candidate calls.

| Residual tolerance | Static BF | Static TF | Threshold | Cost-aware | Stagnation-aware |
|---|---:|---:|---:|---:|---:|
| 1e-6 | 196 | 229 | 265 | 219 | 189 |
| 1e-10 | 238 | 280 | 383 | 303 | 253 |
| 1e-14 | 273 | 325 | 458 | 367 | 300 |

At 1e-6, stagnation-aware switching also beats static BF in aggregate. At the
tighter tolerances it does not. This is evidence that the answer to “does
adaptivity pay?” depends on the stopping accuracy as well as the comparator.
See [the sweep outputs](../results_sweep).

Changing the reuse limit from three to two reduces stagnation-aware iterations
from 222 to 208 at 1e-14, but leaves its total f-call count at 300. Again, fewer
iterations need not mean less work. See [the limit-two run](../results_reuse2/report.md).

Sensitivity runs were initially generated concurrently and their wall times
may include competition between experiment processes. Use their deterministic
work counts for this comparison; run configurations serially on an otherwise
quiet machine before drawing timing conclusions from the sensitivity runs.

## Failures and accuracy

Newton fails immediately on P6, P9 and P11 with its documented left-endpoint
initialization, due to zero derivatives. On P10 it converges to a valid root
outside the original interval. Secant fails on P11. These behaviors are
reported, not hidden by a fallback that would change the baseline algorithm.

The separate [stress run](../results_stress/report.md) demonstrates limits that
the fifteen original equations do not expose. For `exp(x)-1000`, the best
nearby binary64 result reached has a computed residual around 2.27e-13; the
strict 1e-14 test therefore reports precision exhaustion. Small residuals on
the flat cubic and scaled quadratic do not necessarily mean equally small
root errors, which is why independent high-precision root errors are included.

The implementation's static BF/TF totals are 122/99 versus the paper's 121/98.
The experiment preserves and reports this difference. It does not alter the
algorithms or tolerance to force a match to inconsistent printed tables.

The supported conclusion is narrow: **the proposed endpoint-reuse signal
provides the best aggregate evaluation cost of the three implemented policies
on these equations, and it improves on static TF, but adaptivity is not an
unconditional improvement over both static hybrids.**
