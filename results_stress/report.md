# Adaptive switching study — measured results

Residual tolerance: `1e-14`. Maximum iterations: 1000. Timing repetitions: 10, after one warm-up. Binary64 arithmetic.

Success means the computed residual meets the requested tolerance. High-precision residuals and root errors are reported separately in `results.csv`. Open methods may converge outside the starting interval. Failed solves remain visible and are excluded from paired comparisons.

| Suite | Method | Successes | In interval | Iterations, all | f calls, all | f′ calls, all | Mean wall µs |
|---|---|---:|---:|---:|---:|---:|---:|
| stress | bisection | 4/5 | 4 | 124 | 133 | 0 | 114.65 |
| stress | trisection | 4/5 | 4 | 108 | 223 | 0 | 119.11 |
| stress | false_position | 2/5 | 2 | 2235 | 2244 | 0 | 1986.62 |
| stress | newton | 2/5 | 2 | 28 | 31 | 28 | 9.50 |
| stress | secant | 3/5 | 3 | 48 | 56 | 0 | 10.98 |
| stress | static_bf | 4/5 | 4 | 25 | 57 | 0 | 37.98 |
| stress | static_tf | 4/5 | 4 | 34 | 107 | 0 | 55.12 |
| stress | adaptive_threshold | 4/5 | 4 | 221 | 261 | 0 | 214.70 |
| stress | cost_aware | 4/5 | 4 | 89 | 143 | 0 | 116.11 |
| stress | stagnation_aware | 4/5 | 4 | 73 | 100 | 0 | 76.30 |

## Does adaptivity pay?

The following comparisons use function evaluations on problems where both methods succeed inside the original interval. A ratio below 1 favors the adaptive method. Iteration and timing comparisons are also available in `comparisons.csv`.

| Suite | Policy | Baseline | Wins / ties / losses | Median f-call ratio |
|---|---|---|---|---:|
| stress | adaptive_threshold | static_bf | 2 / 0 / 2 | 1.290 |
| stress | adaptive_threshold | static_tf | 2 / 0 / 2 | 0.896 |
| stress | cost_aware | static_bf | 1 / 0 / 3 | 1.155 |
| stress | cost_aware | static_tf | 3 / 0 / 1 | 0.767 |
| stress | stagnation_aware | static_bf | 1 / 0 / 3 | 1.544 |
| stress | stagnation_aware | static_tf | 3 / 0 / 1 | 0.832 |

These observations apply to the specified equations, tolerance, initialization and policy defaults. They do not establish a universal winner. Timing includes Python policy overhead and can favor a different method from evaluation counts; microsecond differences are noisy.

## Failures and roots outside the initial interval

- S1 / false_position: max_iterations; root=0; residual=1.0; in interval=True.
- S1 / newton: zero_derivative; root=0; residual=1.0; in interval=True.
- S1 / secant: zero_secant_denominator; root=0; residual=1.0; in interval=True.
- S2 / bisection: precision_limit; root=6.907755278982137; residual=2.2737367544323206e-13; in interval=True.
- S2 / trisection: precision_limit; root=6.907755278982137; residual=2.2737367544323206e-13; in interval=True.
- S2 / false_position: precision_limit; root=6.907755278982131; residual=6.480149750132114e-12; in interval=True.
- S2 / newton: function_domain_error; root=0; residual=999.0; in interval=True.
- S2 / secant: precision_limit; root=0.8863221048213414; residual=997.5738100505936; in interval=True.
- S2 / static_bf: precision_limit; root=6.907755278982137; residual=2.2737367544323206e-13; in interval=True.
- S2 / static_tf: precision_limit; root=6.907755278982137; residual=2.2737367544323206e-13; in interval=True.
- S2 / adaptive_threshold: precision_limit; root=6.907755278982137; residual=2.2737367544323206e-13; in interval=True.
- S2 / cost_aware: precision_limit; root=6.907755278982137; residual=2.2737367544323206e-13; in interval=True.
- S2 / stagnation_aware: precision_limit; root=6.907755278982137; residual=2.2737367544323206e-13; in interval=True.
- S3 / false_position: max_iterations; root=0.2847103127747116; residual=3.574339528223975e-06; in interval=True.
- S4 / newton: zero_derivative; root=0; residual=2e-12; in interval=True.

## Reproduction limits

The base paper reports 121 and 98 total iterations for static BF and TF, respectively. Its tables contain residual/rounding inconsistencies, and it does not supply executable code or fully specify Newton initialization. This implementation uses the listed equations, documented initialization, cached evaluations, and strict residual stopping. It does not force the published counts. See `paper_comparison.csv` and `../docs/methodology.md`.

The proposal specifies policy ideas rather than complete pseudocode. Bootstrap rules, rolling efficiency estimates, and reuse-counter semantics are documented in the methodology. No policy was tuned per equation. The trace exposes every decision and evaluated candidate.

Artifacts: results.csv, summary.csv, comparisons.csv, timings.csv, histories.json, metadata.json, paper_comparison.csv, and plots/ (unless disabled).
