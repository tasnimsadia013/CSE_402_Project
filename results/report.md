# Adaptive switching study — measured results

Residual tolerance: `1e-14`. Maximum iterations: 1000. Timing repetitions: 10, after one warm-up. Binary64 arithmetic.

Success means the computed residual meets the requested tolerance. High-precision residuals and root errors are reported separately in `results.csv`. Open methods may converge outside the starting interval. Failed solves remain visible and are excluded from paired comparisons.

| Suite | Method | Successes | In interval | Iterations, all | f calls, all | f′ calls, all | Mean wall µs |
|---|---|---:|---:|---:|---:|---:|---:|
| paper | bisection | 15/15 | 15 | 706 | 736 | 0 | 219.57 |
| paper | trisection | 15/15 | 15 | 416 | 862 | 0 | 155.52 |
| paper | false_position | 15/15 | 15 | 492 | 522 | 0 | 159.62 |
| paper | newton | 12/15 | 11 | 80 | 92 | 80 | 9.98 |
| paper | secant | 14/15 | 14 | 104 | 133 | 0 | 10.42 |
| paper | static_bf | 15/15 | 15 | 122 | 273 | 0 | 59.49 |
| paper | static_tf | 15/15 | 15 | 99 | 325 | 0 | 56.33 |
| paper | adaptive_threshold | 15/15 | 15 | 382 | 458 | 0 | 136.58 |
| paper | cost_aware | 15/15 | 15 | 245 | 367 | 0 | 110.77 |
| paper | stagnation_aware | 15/15 | 15 | 222 | 300 | 0 | 81.28 |

## Does adaptivity pay?

The following comparisons use function evaluations on problems where both methods succeed inside the original interval. A ratio below 1 favors the adaptive method. Iteration and timing comparisons are also available in `comparisons.csv`.

| Suite | Policy | Baseline | Wins / ties / losses | Median f-call ratio |
|---|---|---|---|---:|
| paper | adaptive_threshold | static_bf | 5 / 1 / 9 | 1.250 |
| paper | adaptive_threshold | static_tf | 6 / 0 / 9 | 1.118 |
| paper | cost_aware | static_bf | 7 / 0 / 8 | 1.150 |
| paper | cost_aware | static_tf | 8 / 2 / 5 | 0.824 |
| paper | stagnation_aware | static_bf | 4 / 3 / 8 | 1.038 |
| paper | stagnation_aware | static_tf | 11 / 0 / 4 | 0.885 |

These observations apply to the specified equations, tolerance, initialization and policy defaults. They do not establish a universal winner. Timing includes Python policy overhead and can favor a different method from evaluation counts; microsecond differences are noisy.

## Failures and roots outside the initial interval

- P6 / newton: zero_derivative; root=0; residual=2.0; in interval=True.
- P9 / newton: zero_derivative; root=0; residual=1.0; in interval=True.
- P10 / newton: converged; root=-4.917185925287132; residual=1.1102230246251565e-15; in interval=False.
- P11 / newton: zero_derivative; root=0; residual=1.0; in interval=True.
- P11 / secant: precision_limit; root=0.1817588726989925; residual=0.9999999606489609; in interval=True.

## Reproduction limits

The base paper reports 121 and 98 total iterations for static BF and TF, respectively. Its tables contain residual/rounding inconsistencies, and it does not supply executable code or fully specify Newton initialization. This implementation uses the listed equations, documented initialization, cached evaluations, and strict residual stopping. It does not force the published counts. See `paper_comparison.csv` and `../docs/methodology.md`.

The proposal specifies policy ideas rather than complete pseudocode. Bootstrap rules, rolling efficiency estimates, and reuse-counter semantics are documented in the methodology. No policy was tuned per equation. The trace exposes every decision and evaluated candidate.

Artifacts: results.csv, summary.csv, comparisons.csv, timings.csv, histories.json, metadata.json, paper_comparison.csv, and plots/ (unless disabled).
