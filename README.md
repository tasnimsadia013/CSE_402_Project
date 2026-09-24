# Group 1B1 — Adaptive Switching Strategies

Complete Python implementation of **Group-1B1.pdf**, using the fifteen equations
in **numerical base paper.pdf** (Badr, Almotairi and El Ghamry, *Mathematics* 2021,
9, 1306). Both original PDFs are preserved.

The experiment compares three adaptive policies, two static hybrids, and five
classical solvers. All eight bracketed methods use one bracket-maintenance
engine. Newton and secant retain their classical, unsafeguarded behavior.

## Run

Python 3.10 or later:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

The numerical solvers themselves use only the standard library. The experiment
uses mpmath for independent, 80-digit reference roots, and NumPy/Matplotlib for
figures. With these packages already installed, simply run `python3 main.py`.

Default: all ten methods, all fifteen paper equations, residual tolerance
`1e-14`, maximum 1,000 iterations, ten timing repetitions, reuse limit three.

```bash
# Run tests (no pytest required)
python3 -m unittest discover -s tests -v

# Inspect the stagnation benchmark with only the proposed policies
python3 main.py --problems P11 --methods adaptive_threshold cost_aware stagnation_aware --output results_p11

# Include five separately labelled stress cases
python3 main.py --suite all --output results_all

# Sensitivity to tolerance
python3 main.py --tolerances 1e-6 1e-10 1e-14 --output results_sweep --no-plots

# The proposal's alternative endpoint-reuse limit
python3 main.py --reuse-limit 2 --output results_reuse2 --no-plots

# Sensitivity of Newton to the initial guess
python3 main.py --methods newton --newton-start midpoint --output results_newton_midpoint --no-plots

python3 main.py --help
```

Each output directory contains generated files with fixed names; rerunning that
directory replaces those files. Use a distinct `--output` for each configuration.

## Read the results

- [Measured report](results/report.md): success rates and empirical comparisons.
- [Findings and sensitivity analysis](docs/findings.md): what the results mean
  for the proposal's research question.
- [Full results](results/results.csv): per-problem roots, residuals, independent
  root errors, counts, times, final intervals and failure reasons.
- [Policy comparisons](results/comparisons.csv): wins/ties/losses against both
  static hybrids, on common successful problems.
- [Iteration histories](results/histories.json): every sampled candidate,
  selection reason, threshold/efficiency estimate, and bracket update.
- [Figures](results/plots): PNG and PDF work-count, timing, convergence and
  switching plots.
- [Methodology](docs/methodology.md): precise mathematical definitions,
  proposal ambiguities, experimental controls and source discrepancies.
- [Requirements checklist](docs/requirements.md): proposal-to-code mapping.

`summary.csv` includes failed solves in totals, with success counts alongside
them. `timings.csv` preserves every measured repetition. `metadata.json` records
configuration, platform, seed, and hashes of the code and original PDFs.
`paper_comparison.csv` compares the two static hybrids with Tables 8–9.

The checked-in/generated default run finds all fifteen roots with every
bracketed method. Newton succeeds on twelve and secant on fourteen. With the
documented policy defaults, adaptivity does **not** always save work; read the
report rather than assuming fewer iterations means lower cost. Numerical
counts are deterministic in the tested environment; timings vary by machine.

## Use a solver directly

```python
from rootfinding import Config, solve

result = solve(
    lambda x: x**10 - 1,
    0.0, 1.3,
    method="stagnation_aware",
    config=Config(ftol=1e-14, reuse_limit=3),
)
print(result.root, result.residual, result.function_evaluations, result.status)
for step in result.history:
    print(step["iteration"], step["selected"], step["diagnostics"])
```

Accepted method names: `bisection`, `trisection`, `false_position`, `newton`,
`secant`, `static_bf`, `static_tf`, `adaptive_threshold`, `cost_aware`,
`stagnation_aware`. Newton needs `derivative=...`. A new policy can subclass
`Selector` in `rootfinding/solvers.py` and be passed with `selector=...` to a
bracketed solve. A new benchmark is a `Problem` in `rootfinding/problems.py`.

## Project layout

```text
main.py                    Single experiment driver / CLI
rootfinding/solvers.py     Shared bracket engine, selectors, classical methods
rootfinding/problems.py    All paper equations, derivatives, stress cases
rootfinding/experiment.py  Timings, independent validation, tables and report
rootfinding/plotting.py    Publication/export figures
tests/                    Numerical, policy and experiment tests
docs/                     Methodology and requirement coverage
results/                  Default paper experiment and figures
```

The solver assumes deterministic real-valued functions and, for bracketing
guarantees, continuity on the interval. A small residual is not necessarily a
small root error; the stress cases explicitly demonstrate this distinction.
