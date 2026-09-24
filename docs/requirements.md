# Coverage of the supplied PDFs

All four proposal pages and all fifteen base-paper pages were read. The formula
table and the policy slide were additionally inspected as rendered pages.

| Source / requirement | Implementation | Verification / artifact |
|---|---|---|
| Proposal p. 2: static trisection + false position | `StaticSelector`, `static_tf` | `paper_comparison.csv`, Tables 8–9 counts preserved |
| Proposal p. 3: comparative study on common benchmark | `paper_problems`, `run_experiment` | 15 equations × 10 methods; shared tolerance and counting rules |
| Proposal p. 3: two static hybrids | `static_bf`, `static_tf` | Per-equation results and paired adaptive comparisons |
| Proposal p. 3: classical methods | Bisection, trisection, regula falsi, Newton, secant | Explicit successes, failures, function and derivative counts |
| Proposal p. 4: last-three convergence-ratio threshold | `AdaptiveThresholdSelector` | Unit test, per-step threshold and FP ratio in histories |
| Proposal p. 4: log progress per function evaluation | `CostAwareSelector` | Per-method efficiency histories, warm-up and cost-normalization test |
| Proposal p. 4: endpoint reused two–three times forces trisection | `StagnationAwareSelector` | Limits 2 and 3 tested; reuse counters and decisions recorded |
| Proposal p. 4: one Python driver | `main.py` | Default run, CLI subset/sweep/stress configurations |
| Proposal p. 4: shared bracket maintenance | `Bracket.narrow`, common bracketed loop | Nested interval / sign / root-containment checks for all 15 equations |
| Proposal p. 4: three pluggable selectors | `Selector.choose` and `Selector.observe` | Fresh state per solve; custom selector API |
| Proposal deliverable: empirical answer on adaptivity | `report.md`, `comparisons.csv` | Work counts, timing, failures, policy traces, plots |
| Base paper Algorithms 1–7 | Five classical + two static methods | Exact P4 root, all bracketing methods, open-method failures |
| Base paper Table 1 | `paper_problems()` | Exact intervals and formulas, analytic derivatives checked numerically |
| Base paper p. 12: eps = 10^-14 | Default `Config.ftol` | Strict computed residual stopping; no hidden tolerance relaxation |
| Base paper: ten timing runs | `run_experiment(repeats=10)` | One extra warm-up; ten recorded CPU/wall samples per pair |
| Base paper: iterations, function value, final bounds, CPU time | `results.csv` | Additional evaluation costs and independent accuracy checks |

Implementation choices needed to turn the proposal into runnable algorithms
are explicitly specified in [methodology.md](methodology.md). Additional stress
cases and tolerance sweeps are clearly separated from the original benchmark.
