#!/usr/bin/env python3
"""Single entry point for the Group-1B1 comparative study."""

import argparse
from pathlib import Path

from rootfinding.experiment import run_experiment
from rootfinding.problems import paper_problems, stress_problems
from rootfinding.solvers import Config, METHODS


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=("paper", "stress", "all"), default="paper")
    parser.add_argument("--methods", nargs="+", choices=METHODS, default=list(METHODS))
    parser.add_argument("--problems", nargs="+", help="Problem IDs, e.g. P2 P11")
    parser.add_argument("--tol", type=float, default=1e-14, help="Absolute residual tolerance")
    parser.add_argument("--tolerances", nargs="+", type=float, help="Run a tolerance sweep in separate subdirectories")
    parser.add_argument("--max-iterations", type=int, default=1000)
    parser.add_argument("--repeats", type=int, default=10)
    parser.add_argument("--reuse-limit", type=int, default=3)
    parser.add_argument("--ratio-window", type=int, default=3)
    parser.add_argument("--efficiency-window", type=int, default=3)
    parser.add_argument("--newton-start", choices=("left", "midpoint", "right"), default="left")
    parser.add_argument("--seed", type=int, default=402)
    parser.add_argument("--output", type=Path, default=Path("results"))
    parser.add_argument("--no-plots", action="store_true")
    args = parser.parse_args(argv)
    problems = (paper_problems() if args.suite in ("paper", "all") else [])+(stress_problems() if args.suite in ("stress", "all") else [])
    if args.problems:
        unknown = set(args.problems)-{p.name for p in problems}
        if unknown:
            parser.error(f"Unknown IDs in selected suite: {', '.join(sorted(unknown))}")
        problems = [p for p in problems if p.name in args.problems]
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    tolerances = list(dict.fromkeys(args.tolerances or [args.tol]))
    for tolerance in tolerances:
        try:
            config = Config(tolerance, args.max_iterations, args.ratio_window,
                            args.efficiency_window, args.reuse_limit, args.newton_start)
        except ValueError as exc:
            parser.error(str(exc))
        out = args.output/f"tol_{tolerance:g}" if args.tolerances else args.output
        rows, summaries = run_experiment(problems, list(dict.fromkeys(args.methods)), config, out,
                                        args.repeats, args.seed, not args.no_plots)
        print(f"\nTolerance {tolerance:g} — {len(rows)} solves")
        print(f"{'Suite':7} {'Method':22} {'Success':9} {'Iter':>7} {'f calls':>9} {'df calls':>9}")
        for s in summaries:
            print(f"{s['suite']:7} {s['method']:22} {s['successes']:2}/{s['problems']:<6} {s['iterations_all']:7} {s['function_evaluations_all']:9} {s['derivative_evaluations_all']:9}")
        print(f"Report: {(out/'report.md').resolve()}")


if __name__ == "__main__":
    main()
