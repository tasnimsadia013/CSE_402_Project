import csv
import json
from pathlib import Path
import tempfile
import unittest

from rootfinding.experiment import paired_comparisons, run_experiment
from rootfinding.problems import paper_problems
from rootfinding.solvers import Config


class ExperimentTests(unittest.TestCase):
    def test_complete_artifacts_and_independent_accuracy(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            rows, summaries = run_experiment([paper_problems()[0]], ["static_tf", "stagnation_aware"], Config(), out, repeats=2, plots=False)
            self.assertEqual(len(rows), 2)
            self.assertEqual(len(summaries), 2)
            for name in ("results.csv", "summary.csv", "comparisons.csv", "timings.csv", "histories.json", "metadata.json", "paper_comparison.csv", "report.md"):
                self.assertTrue((out/name).is_file())
            with (out/"timings.csv").open() as f:
                self.assertEqual(len(list(csv.DictReader(f))), 4)
            metadata = json.loads((out/"metadata.json").read_text())
            self.assertEqual(metadata["repeats"], 2)
            self.assertTrue(metadata["source_sha256"])
            for row in rows:
                self.assertLess(row["absolute_root_error"], 1e-13)
                self.assertIsNotNone(row["high_precision_residual"])

    def test_failures_are_not_counted_as_pairwise_wins(self):
        rows = [dict(suite="paper", problem="P1", method=m, converged=c,
                     in_initial_interval=True, iterations=i, function_evaluations=i, wall_median_us=i)
                for m, c, i in (("static_tf", True, 10), ("cost_aware", False, 1))]
        pairs = paired_comparisons(rows)
        relevant = [r for r in pairs if r["adaptive"] == "cost_aware" and r["baseline"] == "static_tf"]
        self.assertTrue(all(r["paired_successes"] == 0 for r in relevant))


if __name__ == "__main__":
    unittest.main()
