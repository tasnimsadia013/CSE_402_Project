# Adaptive switching study — measured results

Residual tolerance: `1e-06`. Maximum iterations: 1000. Timing repetitions: 10, after one warm-up. Binary64 arithmetic.

Success means the computed residual meets the requested tolerance. High-precision residuals and root errors are reported separately in `results.csv`. Open methods may converge outside the starting interval. Failed solves remain visible and are excluded from paired comparisons.

| Suite | Method | Successes | In interval | Iterations, all | f calls, all | f′ calls, all | Mean wall µs |
|---|---|---:|---:|---:|---:|---:|---:|
| paper | bisection | 15/15 | 15 | 317 | 347 | 0 | 102.48 |
| paper | trisection | 15/15 | 15 | 186 | 402 | 0 | 75.20 |
| paper | false_position | 15/15 | 15 | 233 | 263 | 0 | 78.70 |
| paper | newton | 12/15 | 11 | 68 | 80 | 68 | 9.07 |
| paper | secant | 14/15 | 14 | 80 | 109 | 0 | 9.15 |
| paper | static_bf | 15/15 | 15 | 83 | 196 | 0 | 42.92 |
| paper | static_tf | 15/15 | 15 | 67 | 229 | 0 | 40.35 |
| paper | adaptive_threshold | 15/15 | 15 | 233 | 265 | 0 | 80.59 |
| paper | cost_aware | 15/15 | 15 | 132 | 219 | 0 | 64.31 |
| paper | stagnation_aware | 15/15 | 15 | 134 | 189 | 0 | 51.92 |

## Does adaptivity pay?

The following comparisons use function evaluations on problems where both methods succeed inside the original interval. A ratio below 1 favors the adaptive method. Iteration and timing comparisons are also available in `comparisons.csv`.

| Suite | Policy | Baseline | Wins / ties / losses | Median f-call ratio |
|---|---|---|---|---:|
| paper | adaptive_threshold | static_bf | 7 / 1 / 7 | 1.000 |
| paper | adaptive_threshold | static_tf | 9 / 0 / 6 | 0.727 |
| paper | cost_aware | static_bf | 10 / 1 / 4 | 0.929 |
| paper | cost_aware | static_tf | 11 / 0 / 4 | 0.714 |
| paper | stagnation_aware | static_bf | 8 / 2 / 5 | 0.875 |
| paper | stagnation_aware | static_tf | 13 / 1 / 1 | 0.714 |

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
