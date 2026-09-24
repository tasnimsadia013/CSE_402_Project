# Adaptive switching study — measured results

Residual tolerance: `1e-10`. Maximum iterations: 1000. Timing repetitions: 10, after one warm-up. Binary64 arithmetic.

Success means the computed residual meets the requested tolerance. High-precision residuals and root errors are reported separately in `results.csv`. Open methods may converge outside the starting interval. Failed solves remain visible and are excluded from paired comparisons.

| Suite | Method | Successes | In interval | Iterations, all | f calls, all | f′ calls, all | Mean wall µs |
|---|---|---:|---:|---:|---:|---:|---:|
| paper | bisection | 15/15 | 15 | 512 | 542 | 0 | 198.63 |
| paper | trisection | 15/15 | 15 | 306 | 642 | 0 | 144.22 |
| paper | false_position | 15/15 | 15 | 363 | 393 | 0 | 143.96 |
| paper | newton | 12/15 | 11 | 75 | 87 | 75 | 10.92 |
| paper | secant | 14/15 | 14 | 93 | 122 | 0 | 11.11 |
| paper | static_bf | 15/15 | 15 | 104 | 238 | 0 | 63.11 |
| paper | static_tf | 15/15 | 15 | 84 | 280 | 0 | 58.86 |
| paper | adaptive_threshold | 15/15 | 15 | 329 | 383 | 0 | 139.95 |
| paper | cost_aware | 15/15 | 15 | 194 | 303 | 0 | 110.32 |
| paper | stagnation_aware | 15/15 | 15 | 184 | 253 | 0 | 84.90 |

## Does adaptivity pay?

The following comparisons use function evaluations on problems where both methods succeed inside the original interval. A ratio below 1 favors the adaptive method. Iteration and timing comparisons are also available in `comparisons.csv`.

| Suite | Policy | Baseline | Wins / ties / losses | Median f-call ratio |
|---|---|---|---|---:|
| paper | adaptive_threshold | static_bf | 5 / 1 / 9 | 1.200 |
| paper | adaptive_threshold | static_tf | 8 / 0 / 7 | 0.947 |
| paper | cost_aware | static_bf | 7 / 2 / 6 | 1.000 |
| paper | cost_aware | static_tf | 11 / 0 / 4 | 0.706 |
| paper | stagnation_aware | static_bf | 6 / 2 / 7 | 1.000 |
| paper | stagnation_aware | static_tf | 11 / 3 / 1 | 0.824 |

These observations apply to the specified equations, tolerance, initialization and policy defaults. They do not establish a universal winner. Timing includes Python policy overhead and can favor a different method from evaluation counts; microsecond differences are noisy.

## Failures and roots outside the initial interval

- P6 / newton: zero_derivative; root=0; residual=2.0; in interval=True.
- P9 / newton: zero_derivative; root=0; residual=1.0; in interval=True.
- P10 / newton: converged; root=-4.917185925287297; residual=8.277822871605167e-13; in interval=False.
- P11 / newton: zero_derivative; root=0; residual=1.0; in interval=True.
- P11 / secant: precision_limit; root=0.1817588726989925; residual=0.9999999606489609; in interval=True.

## Reproduction limits

The base paper reports 121 and 98 total iterations for static BF and TF, respectively. Its tables contain residual/rounding inconsistencies, and it does not supply executable code or fully specify Newton initialization. This implementation uses the listed equations, documented initialization, cached evaluations, and strict residual stopping. It does not force the published counts. See `paper_comparison.csv` and `../docs/methodology.md`.

The proposal specifies policy ideas rather than complete pseudocode. Bootstrap rules, rolling efficiency estimates, and reuse-counter semantics are documented in the methodology. No policy was tuned per equation. The trace exposes every decision and evaluated candidate.

Artifacts: results.csv, summary.csv, comparisons.csv, timings.csv, histories.json, metadata.json, paper_comparison.csv, and plots/ (unless disabled).
