"""Table 1 of Badr et al. (2021), plus separately labelled stress cases."""

from dataclasses import dataclass
import math
from typing import Callable


@dataclass(frozen=True)
class Problem:
    name: str
    expression: str
    a: float
    b: float
    f: Callable[[float], float]
    derivative: Callable[[float], float]
    # Backend-independent expression for independent high-precision verification.
    reference_f: Callable
    suite: str = "paper"


def paper_problems():
    return [
        Problem("P1", "x^2 - 3", 1, 2, lambda x: x*x-3, lambda x: 2*x, lambda x, m: x*x-3),
        Problem("P2", "x^2 - 5", 2, 7, lambda x: x*x-5, lambda x: 2*x, lambda x, m: x*x-5),
        Problem("P3", "x^2 - 10", 3, 4, lambda x: x*x-10, lambda x: 2*x, lambda x, m: x*x-10),
        Problem("P4", "x^2 - x - 2", 1, 4, lambda x: x*x-x-2, lambda x: 2*x-1, lambda x, m: x*x-x-2),
        Problem("P5", "x^2 + 2*x - 7", 1, 3, lambda x: x*x+2*x-7, lambda x: 2*x+2, lambda x, m: x*x+2*x-7),
        Problem("P6", "x^3 - 2", 0, 2, lambda x: x**3-2, lambda x: 3*x*x, lambda x, m: x**3-2),
        Problem("P7", "x*exp(x) - 7", 0, 2, lambda x: x*math.exp(x)-7, lambda x: (1+x)*math.exp(x), lambda x, m: x*m.exp(x)-7),
        Problem("P8", "x - cos(x)", 0, 1, lambda x: x-math.cos(x), lambda x: 1+math.sin(x), lambda x, m: x-m.cos(x)),
        Problem("P9", "x*sin(x) - 1", 0, 2, lambda x: x*math.sin(x)-1, lambda x: math.sin(x)+x*math.cos(x), lambda x, m: x*m.sin(x)-1),
        Problem("P10", "x*cos(x) + 1", -2, 4, lambda x: x*math.cos(x)+1, lambda x: math.cos(x)-x*math.sin(x), lambda x, m: x*m.cos(x)+1),
        Problem("P11", "x^10 - 1", 0, 1.3, lambda x: x**10-1, lambda x: 10*x**9, lambda x, m: x**10-1),
        Problem("P12", "x^2 + exp(x/2) - 5", 1, 2, lambda x: x*x+math.exp(x/2)-5, lambda x: 2*x+math.exp(x/2)/2, lambda x, m: x*x+m.exp(x/2)-5),
        Problem("P13", "sin(x)*sinh(x) + 1", 3, 4, lambda x: math.sin(x)*math.sinh(x)+1, lambda x: math.cos(x)*math.sinh(x)+math.sin(x)*math.cosh(x), lambda x, m: m.sin(x)*m.sinh(x)+1),
        Problem("P14", "exp(x) - 3*x - 2", 2, 3, lambda x: math.exp(x)-3*x-2, lambda x: math.exp(x)-3, lambda x, m: m.exp(x)-3*x-2),
        Problem("P15", "sin(x) - x^2", .5, 1, lambda x: math.sin(x)-x*x, lambda x: math.cos(x)-2*x, lambda x, m: m.sin(x)-x*x),
    ]


def stress_problems():
    return [
        Problem("S1", "x^20 - 1", 0, 2, lambda x: x**20-1, lambda x: 20*x**19, lambda x, m: x**20-1, "stress"),
        Problem("S2", "exp(x) - 1000", 0, 10, lambda x: math.exp(x)-1000, math.exp, lambda x, m: m.exp(x)-1000, "stress"),
        Problem("S3", "(x - 0.3)^3", 0, 1, lambda x: (x-.3)**3, lambda x: 3*(x-.3)**2, lambda x, m: (x-m.mpf("0.3"))**3, "stress"),
        Problem("S4", "1e-12*(x^2 - 2)", 0, 2, lambda x: 1e-12*(x*x-2), lambda x: 2e-12*x, lambda x, m: m.mpf("1e-12")*(x*x-2), "stress"),
        Problem("S5", "x - 0.123456789", 0, 1, lambda x: x-.123456789, lambda x: 1., lambda x, m: x-m.mpf("0.123456789"), "stress"),
    ]


def reference_root(problem):
    """80-digit bisection, independent of the tested double-precision solvers."""
    import mpmath as mp
    with mp.workdps(80):
        a, b = mp.mpf(str(problem.a)), mp.mpf(str(problem.b))
        f = lambda x: problem.reference_f(x, mp)
        fa = f(a)
        if fa == 0:
            return str(a)
        if f(b) == 0:
            return str(b)
        if mp.sign(fa) == mp.sign(f(b)):
            raise ValueError("Reference interval does not bracket a root")
        for _ in range(270):
            x = (a+b)/2
            fx = f(x)
            if fx == 0:
                return str(x)
            if mp.sign(fa) != mp.sign(fx):
                b = x
            else:
                a, fa = x, fx
        return str((a+b)/2)
