import math
import unittest

from rootfinding.problems import paper_problems, reference_root
from rootfinding.solvers import (
    ADAPTIVE, METHODS, AdaptiveThresholdSelector, Bracket, Config,
    CostAwareSelector, Evaluator, StagnationAwareSelector, StepContext,
    opposite, solve,
)


class SolverTests(unittest.TestCase):
    def test_all_bracketed_methods_on_all_paper_equations(self):
        for p in paper_problems():
            root = float(reference_root(p))
            for method in METHODS:
                if method in ("newton", "secant"):
                    continue
                with self.subTest(problem=p.name, method=method):
                    r = solve(p.f, p.a, p.b, method)
                    self.assertTrue(r.converged, r.status)
                    self.assertLessEqual(abs(p.f(r.root)), 1e-14)
                    self.assertAlmostEqual(r.root, root, delta=2e-13)
                    for h in r.history:
                        self.assertLessEqual(h["a_before"], h["a_after"])
                        self.assertLessEqual(h["b_after"], h["b_before"])
                        self.assertTrue(opposite(h["fa_after"], h["fb_after"]))
                        self.assertLessEqual(h["a_before"], h["x"])
                        self.assertLessEqual(h["x"], h["b_before"])
                        self.assertGreaterEqual(root, h["a_after"]-2e-15)
                        self.assertLessEqual(root, h["b_after"]+2e-15)

    def test_actual_calls_match_counters_and_trace(self):
        for method in METHODS:
            calls, derivatives = [], []
            def f(x):
                calls.append(x)
                return x*x-2
            def df(x):
                derivatives.append(x)
                return 2*x
            result = solve(f, 1, 2, method, derivative=df)
            self.assertEqual(result.function_evaluations, len(calls))
            self.assertEqual(result.derivative_evaluations, len(derivatives))
            self.assertEqual(len(set(calls)), len(calls))
            if method not in ("newton", "secant"):
                self.assertEqual(2+sum(h["step_evaluations"] for h in result.history), len(calls))

    def test_exact_trisection_root_and_static_candidate_cost(self):
        f = lambda x: x*x-x-2
        for method, expected in (("trisection", 4), ("static_tf", 5)):
            r = solve(f, 1, 4, method)
            self.assertEqual(r.root, 2)
            self.assertEqual(r.iterations, 1)
            self.assertEqual(r.function_evaluations, expected)

    def test_endpoint_roots(self):
        for method in METHODS:
            for root in (1., 2.):
                r = solve(lambda x: x-root, 1, 2, method, derivative=lambda x: 1)
                self.assertTrue(r.converged)
                self.assertEqual(r.root, root)
                if method not in ("newton", "secant"):
                    self.assertEqual(r.iterations, 0)

    def test_numerical_failures_are_explicit(self):
        self.assertEqual(solve(lambda x: x*x+1, -1, 1).status, "invalid_bracket")
        self.assertEqual(solve(lambda x: math.nan, 0, 1).status, "nonfinite_function")
        self.assertEqual(solve(math.log, -1, 1).status, "function_domain_error")
        self.assertEqual(solve(lambda x: x**3-2, 0, 2, "newton", derivative=lambda x: 3*x*x).status, "zero_derivative")
        self.assertEqual(solve(lambda x: 1, 0, 1, "secant").status, "zero_secant_denominator")
        self.assertEqual(solve(lambda x: x*x-2, 1, 2, "bisection", config=Config(max_iterations=1)).status, "max_iterations")

    def test_precision_exhaustion_does_not_claim_convergence(self):
        a, b = 1., math.nextafter(1., 2.)
        r = solve(lambda x: -1. if x == a else 1., a, b, "bisection")
        self.assertFalse(r.converged)
        self.assertEqual(r.status, "precision_limit")

    def test_underflow_safe_signs_and_overflow_safe_interpolation(self):
        r = solve(lambda x: 1e-200*(x-.25), 0, 1, "bisection", config=Config(ftol=1e-215))
        self.assertTrue(r.converged)
        self.assertEqual(r.root, .25)
        r = solve(lambda x: x, -1e308, 1e308, "false_position")
        self.assertTrue(r.converged)
        self.assertEqual(r.root, 0.)

    def test_open_method_initialization_is_explicit(self):
        p = paper_problems()[5]
        left = solve(p.f, p.a, p.b, "newton", derivative=p.derivative)
        middle = solve(p.f, p.a, p.b, "newton", derivative=p.derivative, config=Config(newton_start="midpoint"))
        self.assertEqual(left.status, "zero_derivative")
        self.assertTrue(middle.converged)

    def test_derivatives_against_central_differences(self):
        for p in paper_problems():
            x = (p.a+p.b)/2
            h = 1e-5
            estimate = (p.f(x+h)-p.f(x-h))/(2*h)
            self.assertAlmostEqual(p.derivative(x), estimate, delta=1e-7*max(1, abs(estimate)))

    def test_tracing_and_repeated_solves_do_not_change_policy_state(self):
        for method in ADAPTIVE:
            p = paper_problems()[10]
            r1 = solve(p.f, p.a, p.b, method)
            r2 = solve(p.f, p.a, p.b, method, trace=False)
            r3 = solve(p.f, p.a, p.b, method)
            self.assertEqual(r1, r3)
            for key in ("root", "iterations", "function_evaluations", "status", "selections"):
                self.assertEqual(getattr(r1, key), getattr(r2, key))
            self.assertEqual(r2.history, [])

    def test_invalid_configuration(self):
        for kwargs in ({"ftol": 0}, {"ftol": math.nan}, {"max_iterations": 0}, {"ratio_window": 1.5}, {"reuse_limit": False}):
            with self.assertRaises(ValueError):
                Config(**kwargs)
        with self.assertRaises(ValueError):
            solve(lambda x: x, 1, 0)
        with self.assertRaises(ValueError):
            solve(lambda x: x, 0, 1, "newton")


class PolicyTests(unittest.TestCase):
    def test_threshold_uses_only_previous_three_ratios(self):
        policy = AdaptiveThresholdSelector()
        q = Bracket(0, 1, -1, 2)
        for ratio in (.8, .6, .4, .2):
            policy.observe(q, q, 1, ratio, "false_position", 1)
        ev = Evaluator(lambda x: x*x*3-1)
        ev.value(0)
        ev.value(1)
        context = StepContext(q, ev, 1, 1e-14)
        kind, point, info = policy.choose(context)
        self.assertAlmostEqual(info["threshold"], .4)
        self.assertEqual(kind, "trisection")
        self.assertEqual(ev.nfev, 4)  # FP coincides with the first third: cached.
        self.assertEqual(set(context.samples), {"false_position", "trisection"})

    def test_cost_policy_warmup_and_gain_per_evaluation(self):
        policy = CostAwareSelector()
        q = Bracket(0, 1, -1, 2)
        def ctx():
            return StepContext(q, Evaluator(lambda x: 3*x*x-1), 1, 1e-14)
        self.assertEqual(policy.choose(ctx())[0], "false_position")
        policy.observe(q, q, 1, .1, "false_position", 1)
        self.assertEqual(policy.choose(ctx())[0], "trisection")
        policy.observe(q, q, 1, .01, "trisection", 2)
        self.assertAlmostEqual(policy.scores["false_position"][0], policy.scores["trisection"][0])
        # FP wins exact score ties by the specified stable order.
        self.assertEqual(policy.choose(ctx())[0], "false_position")

    def test_stagnation_forces_step_at_limit_and_keeps_true_reuse_counts(self):
        for limit in (2, 3):
            p = paper_problems()[10]
            r = solve(p.f, p.a, p.b, "stagnation_aware", config=Config(reuse_limit=limit))
            self.assertTrue(r.converged)
            self.assertEqual([h["selected"] for h in r.history[:limit]], ["false_position"]*limit)
            self.assertEqual(r.history[limit]["selected"], "trisection")
            for h in r.history:
                d = h["diagnostics"]
                if max(d["left_reuse"], d["right_reuse"]) >= limit:
                    self.assertEqual(h["selected"], "trisection")

    def test_bracket_update_is_safe_with_multiple_sign_changes(self):
        q = Bracket(0, 4, -1, 1)
        narrow = q.narrow([(1, 1), (2, -1), (3, 1)])
        self.assertTrue(opposite(narrow.fa, narrow.fb))
        self.assertEqual((narrow.a, narrow.b), (0, 1))


if __name__ == "__main__":
    unittest.main()
