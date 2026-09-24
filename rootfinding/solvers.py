"""One bracket engine, pluggable selectors, and two unsafeguarded open methods.

Only abs(f(x)) <= ftol constitutes success. Precision exhaustion is a failure,
not an excuse to silently relax the requested tolerance.
"""

from collections import deque
from dataclasses import dataclass, field
import math
import sys
from typing import Callable


METHODS = (
    "bisection", "trisection", "false_position", "newton", "secant",
    "static_bf", "static_tf", "adaptive_threshold", "cost_aware", "stagnation_aware",
)
ADAPTIVE = METHODS[-3:]


@dataclass(frozen=True)
class Config:
    ftol: float = 1e-14
    max_iterations: int = 1000
    ratio_window: int = 3
    efficiency_window: int = 3
    reuse_limit: int = 3
    newton_start: str = "left"

    def __post_init__(self):
        if not math.isfinite(self.ftol) or self.ftol <= 0:
            raise ValueError("ftol must be finite and positive")
        for name in ("max_iterations", "ratio_window", "efficiency_window", "reuse_limit"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        if self.newton_start not in ("left", "midpoint", "right"):
            raise ValueError("newton_start must be left, midpoint or right")


@dataclass
class Result:
    method: str
    root: float | None
    f_root: float | None
    converged: bool
    status: str
    iterations: int
    function_evaluations: int
    derivative_evaluations: int
    bracket: tuple[float, float] | None
    selections: dict[str, int] = field(default_factory=dict)
    history: list[dict] = field(default_factory=list)

    @property
    def residual(self):
        return abs(self.f_root) if self.f_root is not None else None


class EvaluationError(Exception):
    pass


class Evaluator:
    """Exact-point caching is restricted to function evaluations, per solve."""

    def __init__(self, f, derivative=None):
        self.f, self.derivative = f, derivative
        self.nfev = self.ndev = 0
        self.cache = {}

    def value(self, x):
        if not math.isfinite(x):
            raise EvaluationError("nonfinite_iterate")
        if x not in self.cache:
            self.nfev += 1
            try:
                value = float(self.f(x))
            except (ArithmeticError, ValueError) as exc:
                raise EvaluationError("function_domain_error") from exc
            if not math.isfinite(value):
                raise EvaluationError("nonfinite_function")
            self.cache[x] = value
        return self.cache[x]

    def slope(self, x):
        self.ndev += 1
        try:
            value = float(self.derivative(x))
        except (ArithmeticError, ValueError) as exc:
            raise EvaluationError("derivative_domain_error") from exc
        if not math.isfinite(value):
            raise EvaluationError("nonfinite_derivative")
        return value


def opposite(x, y):
    # Avoid multiplication: f(a)*f(b) can underflow or overflow.
    return (x < 0 < y) or (y < 0 < x)


def interpolate(a, b, t):
    return (1-t)*a + t*b


@dataclass(frozen=True)
class Bracket:
    a: float
    b: float
    fa: float
    fb: float

    def narrow(self, points):
        """First adjacent sign-changing subinterval using ALL sampled points.

        For the paper benchmarks this is the intersection/max-min update.
        Selecting an adjacent sign change also stays valid for oscillatory
        functions where independently proposed intervals can be disjoint.
        """
        values = {self.a: self.fa, self.b: self.fb}
        values.update((x, fx) for x, fx in points if self.a <= x <= self.b)
        ordered = sorted(values.items())
        for x, fx in ordered:
            if fx == 0:
                return Bracket(x, x, fx, fx)
        for (a, fa), (b, fb) in zip(ordered, ordered[1:]):
            if opposite(fa, fb):
                return Bracket(a, b, fa, fb)
        raise RuntimeError("Internal error: lost sign-changing bracket")


class StepContext:
    """Lazy candidates: a selector only pays for the points it requests."""

    def __init__(self, bracket, evaluator, previous_residual, ftol):
        self.bracket = bracket
        self.evaluator = evaluator
        self.previous_residual = previous_residual
        self.ftol = ftol
        self.samples = {}

    def sample(self, kind):
        if kind in self.samples:
            return self.samples[kind]
        q = self.bracket
        if kind == "false_position":
            # Scale weights to avoid overflow in fb-fa or abs(fa)+abs(fb).
            scale = max(abs(q.fa), abs(q.fb))
            wa, wb = abs(q.fa)/scale, abs(q.fb)/scale
            xs = [interpolate(q.a, q.b, wa/(wa+wb))]
        elif kind == "trisection":
            xs = [interpolate(q.a, q.b, 1/3), interpolate(q.a, q.b, 2/3)]
        elif kind == "bisection":
            xs = [interpolate(q.a, q.b, .5)]
        else:
            raise ValueError(f"Unknown candidate kind: {kind}")
        points = [(x, self.evaluator.value(x)) for x in xs]
        self.samples[kind] = points
        return points

    def best(self, kind):
        return min(self.sample(kind), key=lambda p: abs(p[1]))

    def all_points(self):
        return [p for points in self.samples.values() for p in points]


class Selector:
    def choose(self, context):
        raise NotImplementedError

    def observe(self, old, new, old_residual, new_residual, kind, evaluations):
        pass


class StaticSelector(Selector):
    def __init__(self, kinds):
        self.kinds = kinds

    def choose(self, context):
        choices = [(kind, context.best(kind)) for kind in self.kinds]
        kind, point = min(choices, key=lambda item: abs(item[1][1]))
        return kind, point, {"reason": "minimum_residual"}


class AdaptiveThresholdSelector(Selector):
    def __init__(self, window=3):
        self.ratios = deque(maxlen=window)

    def choose(self, context):
        tau = sum(self.ratios)/len(self.ratios) if self.ratios else 1.
        point = context.best("false_position")
        ratio = abs(point[1])/context.previous_residual
        accept = ratio < tau or abs(point[1]) <= context.ftol
        kind = "false_position" if accept else "trisection"
        return kind, point if accept else context.best(kind), {
            "threshold": tau, "false_position_ratio": ratio,
            "reason": "ratio_below_threshold" if accept else "ratio_rejected",
        }

    def observe(self, old, new, old_residual, new_residual, kind, evaluations):
        self.ratios.append(new_residual/old_residual)


class CostAwareSelector(Selector):
    def __init__(self, window=3):
        self.scores = {kind: deque(maxlen=window) for kind in ("false_position", "trisection")}

    def choose(self, context):
        estimates = {k: sum(v)/len(v) if v else None for k, v in self.scores.items()}
        missing = [k for k, v in estimates.items() if v is None]
        kind = missing[0] if missing else max(estimates, key=estimates.get)
        return kind, context.best(kind), {
            "expected_efficiency": estimates,
            "reason": "warmup" if missing else "highest_expected_efficiency",
        }

    def observe(self, old, new, old_residual, new_residual, kind, evaluations):
        # Difference of logs is safer than forming old/new; retain negative gains.
        floor = sys.float_info.min
        gain = math.log(max(old_residual, floor))-math.log(max(new_residual, floor))
        self.scores[kind].append(gain/evaluations if evaluations else 0.)


class StagnationAwareSelector(Selector):
    def __init__(self, limit=3):
        self.limit = limit
        self.left_reuse = self.right_reuse = 0

    def choose(self, context):
        force = max(self.left_reuse, self.right_reuse) >= self.limit
        kind = "trisection" if force else "false_position"
        return kind, context.best(kind), {
            "left_reuse": self.left_reuse, "right_reuse": self.right_reuse,
            "reason": "endpoint_reuse" if force else "ordinary_false_position",
        }

    def observe(self, old, new, old_residual, new_residual, kind, evaluations):
        self.left_reuse = self.left_reuse+1 if old.a == new.a else 0
        self.right_reuse = self.right_reuse+1 if old.b == new.b else 0


def make_selector(method, config):
    if method == "adaptive_threshold":
        return AdaptiveThresholdSelector(config.ratio_window)
    if method == "cost_aware":
        return CostAwareSelector(config.efficiency_window)
    if method == "stagnation_aware":
        return StagnationAwareSelector(config.reuse_limit)
    kinds = {
        "bisection": ("bisection",), "trisection": ("trisection",),
        "false_position": ("false_position",),
        "static_bf": ("bisection", "false_position"),
        "static_tf": ("trisection", "false_position"),
    }
    return StaticSelector(kinds[method])


def solve(f: Callable, a: float, b: float, method="adaptive_threshold", *,
          derivative=None, config=None, trace=True, selector=None):
    """Solve with a fresh policy state. Newton starts at a by default.

    A custom Selector can replace a bracketed method's policy. The callable
    must be deterministic because repeated function values are cached.
    Invalid API arguments raise ValueError; numerical failures return Result.
    """
    config = config or Config()
    if method not in METHODS:
        raise ValueError(f"Unknown method {method!r}; choose one of {METHODS}")
    if not (math.isfinite(a) and math.isfinite(b) and a < b):
        raise ValueError("Require finite endpoints a < b")
    if method == "newton" and derivative is None:
        raise ValueError("Newton requires a derivative callable")
    if selector is not None and method in ("newton", "secant"):
        raise ValueError("Custom selectors require a bracketed method")
    ev = Evaluator(f, derivative)
    history, selections = [], {}
    best = None
    bracket = None
    iteration = 0

    def finish(status):
        return Result(method, best[0] if best else None, best[1] if best else None,
                      status == "converged", status, iteration, ev.nfev, ev.ndev,
                      (bracket.a, bracket.b) if bracket else None, selections, history)

    def record_best(point):
        nonlocal best
        if best is None or abs(point[1]) < abs(best[1]):
            best = point

    try:
        if method in ("newton", "secant"):
            x = {"left": a, "right": b, "midpoint": interpolate(a, b, .5)}[config.newton_start] if method == "newton" else b
            fx = ev.value(x)
            record_best((x, fx))
            if abs(fx) <= config.ftol:
                return finish("converged")
            prev, fprev = a, ev.value(a) if method == "secant" else fx
            if method == "secant":
                record_best((prev, fprev))
                if abs(fprev) <= config.ftol:
                    return finish("converged")
            for iteration in range(1, config.max_iterations+1):
                if method == "newton":
                    slope = ev.slope(x)
                    if slope == 0:
                        return finish("zero_derivative")
                    candidate = x-fx/slope
                else:
                    denominator = fx-fprev
                    if denominator == 0:
                        return finish("zero_secant_denominator")
                    candidate = x-(fx/denominator)*(x-prev)
                if not math.isfinite(candidate):
                    return finish("nonfinite_iterate")
                fc = ev.value(candidate)
                record_best((candidate, fc))
                selections[method] = selections.get(method, 0)+1
                if trace:
                    history.append({"iteration": iteration, "selected": method,
                                    "x": candidate, "fx": fc, "residual": abs(fc),
                                    "function_evaluations": ev.nfev, "derivative_evaluations": ev.ndev})
                if abs(fc) <= config.ftol:
                    return finish("converged")
                if candidate == x:
                    return finish("precision_limit")
                prev, fprev, x, fx = x, fx, candidate, fc
            return finish("max_iterations")

        fa = ev.value(a)
        record_best((a, fa))
        if abs(fa) <= config.ftol:
            bracket = Bracket(a, b, fa, fa)
            return finish("converged")
        fb = ev.value(b)
        record_best((b, fb))
        bracket = Bracket(a, b, fa, fb)
        if abs(fb) <= config.ftol:
            return finish("converged")
        if not opposite(fa, fb):
            return finish("invalid_bracket")
        policy = selector if selector is not None else make_selector(method, config)
        previous_residual = abs(best[1])
        for iteration in range(1, config.max_iterations+1):
            old = bracket
            before = ev.nfev
            context = StepContext(old, ev, previous_residual, config.ftol)
            kind, point, diagnostics = policy.choose(context)
            points = context.all_points()
            for sampled in points:
                record_best(sampled)
            # Any sampled root is valid, even if a policy would reject that method.
            terminal = min(points, key=lambda p: abs(p[1]))
            converged = abs(terminal[1]) <= config.ftol
            if converged:
                point = terminal
            else:
                bracket = old.narrow(points)
            spent = ev.nfev-before
            selections[kind] = selections.get(kind, 0)+1
            if trace:
                history.append({"iteration": iteration, "selected": kind,
                                "x": point[0], "fx": point[1], "residual": abs(point[1]),
                                "a_before": old.a, "b_before": old.b,
                                "a_after": bracket.a, "b_after": bracket.b,
                                "fa_after": bracket.fa, "fb_after": bracket.fb,
                                "width": bracket.b-bracket.a,
                                "step_evaluations": spent, "function_evaluations": ev.nfev,
                                "candidates": context.samples, "diagnostics": diagnostics,
                                "sampled_root_override": converged and kind not in [
                                    k for k, v in context.samples.items() if point in v]})
            if converged:
                return finish("converged")
            policy.observe(old, bracket, previous_residual, abs(point[1]), kind, spent)
            previous_residual = abs(point[1])
            if bracket.a == old.a and bracket.b == old.b:
                return finish("precision_limit")
        return finish("max_iterations")
    except EvaluationError as exc:
        return finish(str(exc))
