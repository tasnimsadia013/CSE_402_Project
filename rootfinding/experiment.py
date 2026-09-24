"""Reproducible experiments; file I/O and trace recording are outside timings."""

from collections import Counter
from dataclasses import asdict
import csv
import hashlib
import json
from pathlib import Path
import platform
import random
import statistics
import sys
import time

from .problems import reference_root
from .solvers import ADAPTIVE, solve


PAPER_BF = [8, 10, 7, 2, 5, 9, 11, 8, 6, 10, 12, 8, 9, 9, 7]
PAPER_TF = [7, 8, 6, 1, 7, 8, 7, 7, 5, 8, 9, 6, 7, 7, 5]


def write_csv(path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def accuracy(problem, result, reference):
    import mpmath as mp
    if result.root is None:
        return None, None
    with mp.workdps(80):
        # mp.mpf(float) preserves the actual binary64 value, rather than rounding
        # it through the shortened decimal representation.
        x = mp.mpf(result.root)
        return float(abs(x-mp.mpf(reference))), float(abs(problem.reference_f(x, mp)))


def summarize(rows):
    summaries = []
    for suite in dict.fromkeys(r["suite"] for r in rows):
        for method in dict.fromkeys(r["method"] for r in rows):
            group = [r for r in rows if r["suite"] == suite and r["method"] == method]
            passed = [r for r in group if r["converged"]]
            summaries.append({
                "suite": suite, "method": method, "problems": len(group),
                "successes": len(passed), "failures": len(group)-len(passed),
                "target_interval_successes": sum(r["in_initial_interval"] and r["converged"] for r in group),
                "iterations_all": sum(r["iterations"] for r in group),
                "function_evaluations_all": sum(r["function_evaluations"] for r in group),
                "derivative_evaluations_all": sum(r["derivative_evaluations"] for r in group),
                "mean_function_evaluations_success": statistics.mean(r["function_evaluations"] for r in passed) if passed else None,
                "mean_wall_us_all": statistics.mean(r["wall_mean_us"] for r in group),
                "mean_cpu_us_all": statistics.mean(r["cpu_mean_us"] for r in group),
            })
    return summaries


def paired_comparisons(rows):
    output = []
    for suite in dict.fromkeys(r["suite"] for r in rows):
        lookup = {(r["problem"], r["method"]): r for r in rows if r["suite"] == suite}
        names = list(dict.fromkeys(p for p, m in lookup))
        for adaptive in ADAPTIVE:
            for baseline in ("static_bf", "static_tf"):
                for metric in ("iterations", "function_evaluations", "wall_median_us"):
                    wins = ties = losses = 0
                    ratios = []
                    for name in names:
                        a, b = lookup.get((name, adaptive)), lookup.get((name, baseline))
                        if not a or not b or not (a["converged"] and b["converged"] and a["in_initial_interval"] and b["in_initial_interval"]):
                            continue
                        av, bv = a[metric], b[metric]
                        wins += av < bv
                        ties += av == bv
                        losses += av > bv
                        if bv:
                            ratios.append(av/bv)
                    output.append({"suite": suite, "adaptive": adaptive, "baseline": baseline,
                                   "metric": metric, "paired_successes": wins+ties+losses,
                                   "wins": wins, "ties": ties, "losses": losses,
                                   "median_ratio_to_baseline": statistics.median(ratios) if ratios else None})
    return output


def make_report(out, rows, summaries, comparisons, config, repeats):
    lines = ["# Adaptive switching study — measured results", "",
             f"Residual tolerance: `{config.ftol:g}`. Maximum iterations: {config.max_iterations}. "
             f"Timing repetitions: {repeats}, after one warm-up. Binary64 arithmetic.", "",
             "Success means the computed residual meets the requested tolerance. High-precision residuals "
             "and root errors are reported separately in `results.csv`. Open methods may converge outside "
             "the starting interval. Failed solves remain visible and are excluded from paired comparisons.", "",
             "| Suite | Method | Successes | In interval | Iterations, all | f calls, all | f′ calls, all | Mean wall µs |",
             "|---|---|---:|---:|---:|---:|---:|---:|"]
    for s in summaries:
        lines.append(f"| {s['suite']} | {s['method']} | {s['successes']}/{s['problems']} | {s['target_interval_successes']} | {s['iterations_all']} | {s['function_evaluations_all']} | {s['derivative_evaluations_all']} | {s['mean_wall_us_all']:.2f} |")
    lines += ["", "## Does adaptivity pay?", "",
              "The following comparisons use function evaluations on problems where both methods succeed "
              "inside the original interval. A ratio below 1 favors the adaptive method. "
              "Iteration and timing comparisons are also available in `comparisons.csv`.", "",
              "| Suite | Policy | Baseline | Wins / ties / losses | Median f-call ratio |",
              "|---|---|---|---|---:|"]
    for c in comparisons:
        if c["metric"] == "function_evaluations":
            ratio = c["median_ratio_to_baseline"]
            ratio_text = f"{ratio:.3f}" if ratio is not None else "n/a"
            lines.append(f"| {c['suite']} | {c['adaptive']} | {c['baseline']} | {c['wins']} / {c['ties']} / {c['losses']} | {ratio_text} |")
    lines += ["", "These observations apply to the specified equations, tolerance, initialization and policy "
              "defaults. They do not establish a universal winner. Timing includes Python policy overhead "
              "and can favor a different method from evaluation counts; microsecond differences are noisy.", "",
              "## Failures and roots outside the initial interval", ""]
    exceptional = [r for r in rows if not r["converged"] or not r["in_initial_interval"]]
    if not exceptional:
        lines.append("None in this run.")
    for r in exceptional:
        lines.append(f"- {r['problem']} / {r['method']}: {r['status']}; root={r['root']}; residual={r['residual']}; in interval={r['in_initial_interval']}.")
    lines += ["", "## Reproduction limits", "",
              "The base paper reports 121 and 98 total iterations for static BF and TF, respectively. "
              "Its tables contain residual/rounding inconsistencies, and it does not supply executable code "
              "or fully specify Newton initialization. This implementation uses the listed equations, "
              "documented initialization, cached evaluations, and strict residual stopping. It does not "
              "force the published counts. See `paper_comparison.csv` and `../docs/methodology.md`.", "",
              "The proposal specifies policy ideas rather than complete pseudocode. Bootstrap rules, "
              "rolling efficiency estimates, and reuse-counter semantics are documented in the methodology. "
              "No policy was tuned per equation. The trace exposes every decision and evaluated candidate.", "",
              "Artifacts: results.csv, summary.csv, comparisons.csv, timings.csv, histories.json, "
              "metadata.json, paper_comparison.csv, and plots/ (unless disabled).", ""]
    (out/"report.md").write_text("\n".join(lines), encoding="utf-8")


def run_experiment(problems, methods, config, out, repeats=10, seed=402, plots=True):
    if repeats < 1:
        raise ValueError("repeats must be positive")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    results, histories, timings = [], {}, []
    for problem in problems:
        reference = reference_root(problem)
        traced = {}
        samples = {m: [] for m in methods}
        for method in methods:
            kwargs = dict(derivative=problem.derivative, config=config)
            traced[method] = solve(problem.f, problem.a, problem.b, method, **kwargs)
            solve(problem.f, problem.a, problem.b, method, trace=False, **kwargs)
        for repetition in range(repeats):
            order = list(methods)
            rng.shuffle(order)
            for method in order:
                wall_start, cpu_start = time.perf_counter_ns(), time.process_time_ns()
                result = solve(problem.f, problem.a, problem.b, method,
                               derivative=problem.derivative, config=config, trace=False)
                cpu_ns, wall_ns = time.process_time_ns()-cpu_start, time.perf_counter_ns()-wall_start
                expected = traced[method]
                if (result.root, result.status, result.iterations, result.function_evaluations) != (expected.root, expected.status, expected.iterations, expected.function_evaluations):
                    raise RuntimeError("Non-deterministic solve or tracing altered numerical behavior")
                samples[method].append((wall_ns/1000, cpu_ns/1000))
                timings.append({"suite": problem.suite, "problem": problem.name, "method": method,
                                "repetition": repetition+1, "wall_us": wall_ns/1000, "cpu_us": cpu_ns/1000})
        for method, result in traced.items():
            wall, cpu = zip(*samples[method])
            error, hp_residual = accuracy(problem, result, reference)
            row = {"suite": problem.suite, "problem": problem.name, "expression": problem.expression,
                   "a": problem.a, "b": problem.b, "method": method, "ftol": config.ftol,
                   "root": result.root, "f_root": result.f_root, "residual": result.residual,
                   "reference_root": reference, "absolute_root_error": error,
                   "high_precision_residual": hp_residual,
                   "converged": result.converged, "status": result.status,
                   "in_initial_interval": result.root is not None and problem.a <= result.root <= problem.b,
                   "iterations": result.iterations, "function_evaluations": result.function_evaluations,
                   "derivative_evaluations": result.derivative_evaluations,
                   "final_a": result.bracket[0] if result.bracket else None,
                   "final_b": result.bracket[1] if result.bracket else None,
                   "false_position_steps": result.selections.get("false_position", 0),
                   "trisection_steps": result.selections.get("trisection", 0),
                   "wall_mean_us": statistics.mean(wall), "wall_median_us": statistics.median(wall),
                   "wall_stdev_us": statistics.stdev(wall) if len(wall) > 1 else 0,
                   "cpu_mean_us": statistics.mean(cpu), "cpu_median_us": statistics.median(cpu)}
            results.append(row)
            histories[f"{problem.name}/{method}"] = asdict(result)
    summaries = summarize(results)
    comparisons = paired_comparisons(results)
    for name, rows in (("results", results), ("summary", summaries), ("comparisons", comparisons), ("timings", timings)):
        write_csv(out/f"{name}.csv", rows)
    paper_rows = []
    for row in results:
        if row["suite"] == "paper" and row["method"] in ("static_bf", "static_tf"):
            published = (PAPER_BF if row["method"] == "static_bf" else PAPER_TF)[int(row["problem"][1:])-1]
            paper_rows.append({"problem": row["problem"], "method": row["method"],
                               "published_iterations": published, "measured_iterations": row["iterations"],
                               "difference": row["iterations"]-published, "status": row["status"]})
    write_csv(out/"paper_comparison.csv", paper_rows)
    (out/"histories.json").write_text(json.dumps(histories, indent=2, allow_nan=False), encoding="utf-8")
    project = Path(__file__).resolve().parent.parent
    source_paths = list((project/"rootfinding").glob("*.py"))+[project/"main.py"]
    source_paths += [project/"Group-1B1.pdf", project/"numerical base paper.pdf"]
    metadata = {"config": asdict(config), "repeats": repeats, "seed": seed,
                "methods": list(methods), "problems": [p.name for p in problems],
                "python": sys.version, "platform": platform.platform(), "processor": platform.processor(),
                "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "timing": "One warm-up; randomized method order per repetition; traces disabled; wall and process CPU clocks",
                "source_sha256": {str(p.relative_to(project)): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths if p.exists()},
                "statuses": dict(Counter(r["status"] for r in results))}
    (out/"metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    make_report(out, results, summaries, comparisons, config, repeats)
    if plots:
        from .plotting import make_plots
        make_plots(out, results, histories)
    return results, summaries
