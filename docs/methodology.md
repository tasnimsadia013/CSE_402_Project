# Methodology and source interpretation

## Sources and scope

Primary specification: `Group-1B1.pdf`, especially pages 3–4. Baseline source:
`numerical base paper.pdf`, Badr et al., *A Comparative Study among New Hybrid
Root Finding Algorithms and Traditional Methods*, 2021, Algorithms 1–7,
Table 1, and Tables 3–9. The project implements the proposed **comparative
study**, not merely a root-finding demonstration.

There is no pre-existing code in the supplied directory. The proposal does not
give complete pseudocode for its three policies. The definitions below are
explicit implementation assumptions, not extra claims attributed to the PDFs.

## Common numerical rules

Given a finite ordered interval `[a,b]`, evaluate its endpoints and accept an
endpoint immediately if `abs(f(endpoint)) <= ftol`. Otherwise, bracketed
methods require strictly opposite signs. Signs are compared directly, avoiding
the underflow/overflow possible in `f(a)*f(b)`.

The candidate locations are:

```text
Bisection:      xB = (a+b)/2
Trisection:     x1 = (2*a+b)/3, x2 = (a+2*b)/3
False position: xF = a - f(a)*(b-a)/(f(b)-f(a))
```

The code uses equivalent convex combinations, with scaled absolute function
weights for false position, to avoid unnecessary overflow. These algebraic
rearrangements can change the final few bits and thus an iteration count.

One routine maintains the bracket for **all eight bracketed methods**. It
sorts the endpoints and all evaluated candidates and retains the first adjacent
pair with opposite signs. On the paper equations, this is the base paper's
intersection update: maximum lower bound and minimum upper bound. Both
trisection points participate, not just the one with the smaller residual.
An evaluated but rejected false-position point also participates: it has
already cost a function call and is valid bracketing information.

For functions with several sign changes among sampled points, independent
trisection and false-position intervals can be disjoint; a literal intersection
would be invalid. The adjacent-sign-change rule remains valid in that case,
selecting the leftmost observed sign-changing subinterval. This is an explicit
robustness extension outside the supplied benchmark, not a reproduction claim.

Function values are cached at exactly equal floating-point coordinates for the
duration of each solve. Endpoints are not evaluated again after a bracket
update. A shared candidate is charged once, not twice. All distinct trial
evaluations count, including rejected threshold probes and terminal candidates.
The two static hybrids evaluate their entire candidate set before deciding,
as in the paper. Initialization and failed evaluation attempts count too.

Termination is **only** `abs(f(x)) <= ftol`. Width and successive-iterate changes
do not silently substitute for the paper's residual test. Iteration exhaustion,
invalid brackets, nonfinite values, domain errors, zero derivatives/denominators
and floating-point non-progress are reported explicitly. A terminal iteration
is counted; an endpoint solution takes zero iterations. For open methods, an
attempt ending in a zero derivative/denominator counts as an attempted iteration.

The result stores the best evaluated point so far. On failure this is a useful
estimate, not a successful root certificate, and it need not lie inside the
last narrowed bracket. Trace `x` is the policy-selected point of that iteration;
it can likewise be outside the **post-update** interval but is inside the
pre-update interval. On a successful step the trace retains the pre-update
bracket, matching the source's check-before-update ordering.

## Static and classical methods

- Bisection evaluates its midpoint; trisection evaluates both thirds and
  selects the smaller residual; false position evaluates its interpolated point.
- Static BF evaluates the midpoint and FP point, selects the smallest residual,
  and updates with both.
- Static TF evaluates both thirds and FP, selects the smallest residual, and
  updates with all three.
- Newton uses the supplied analytic derivative and starts at the left endpoint
  by default. `--newton-start midpoint|right` changes it explicitly. The paper
  does not fully specify initialization, but its P6/P9/P11 zero-derivative
  failures are consistent with starting at the left endpoint.
- Secant uses the original endpoints as its two initial guesses, then applies
  the ordinary secant recurrence. Newton and secant are not clipped to the
  interval or repaired with a bracketed fallback; such a repair would change
  the classical baselines. A root outside the initial interval is flagged.

Ties use stable candidate order: first third before second third; geometric
candidate before FP in a static hybrid. Algorithm 6 chooses FP on exact ties;
this implementation uses the common stable tie convention. Except when a
different exact root is present, equal residuals do not change the all-candidate
bracket update. This convention is documented rather than hidden.

Derivative calls are counted separately. A derivative evaluation is not assumed
to cost exactly one function evaluation; wall/CPU times capture the actual
implementation cost. Reference-root work is excluded from solver counts.

## 1. Adaptive threshold

Let `e_old` be the absolute residual of the previously **selected** candidate,
initialized to `min(abs(f(a)), abs(f(b)))`. Define the convergence ratio as
`r = e_new/e_old`, so a smaller ratio is better.

At the beginning of iteration k:

1. Set `tau` to the arithmetic mean of the last three selected-step ratios.
   With fewer than three observations, use all available observations; with
   none, use `tau = 1` (any strict improvement is initially acceptable).
2. Evaluate FP and compute `rF = abs(f(xF))/e_old`.
3. Choose FP if `rF < tau`; otherwise evaluate both thirds and select the one
   with the smaller residual. The rejected FP probe is still charged.
4. Update the shared bracket with all evaluated points. Append the actual
   selected-step ratio to the window **after** the decision.

An evaluated point already satisfying tolerance terminates the solve regardless
of the policy comparison. This common terminal check avoids rejecting a root.
The window contains no future information. It is not the last three FP trials
and not the ratio to a hidden known root. `--ratio-window` allows sensitivity
studies; the proposal's value three is the default.

Cost: normally one new function call if FP is accepted, up to three if rejected.
This policy may fail to identify one-sided stagnation when tiny improvements
consistently beat its rolling average. That behavior is a legitimate empirical
finding; no extra endpoint safeguard is added to this policy.

## 2. Cost-aware switching

For a step made by method m, estimate its realized efficiency as

```text
E_m = [log(max(e_old, tiny)) - log(max(e_new, tiny))] / n_new_function_calls
```

Here `tiny` is the smallest positive normal binary64 value, used only in the
logarithm. Stopping uses the unmodified residual. Negative efficiencies are
retained, since a step can worsen the selected residual.

Expected efficiency is the arithmetic mean of the last three observed
efficiencies **for that method**. This rolling estimator is a design choice
needed because the proposal specifies an expected efficiency without defining
an estimator. `--efficiency-window` exposes that choice.

The first step samples FP; the second samples trisection unless the solve has
already finished. These are actual solving steps and their work is counted.
After both methods have an observation, choose the method with the larger
expected efficiency, evaluating only its candidate(s). FP wins exact score
ties. No simultaneous trial of both methods, periodic exploration, per-equation
tuning or hidden fallback is used. An observation with zero new evaluations
receives score zero; precision exhaustion then ends the solve if the bracket
has not moved.

This literal greedy policy can retain stale expectations for an unselected
method and can remain committed to one choice. The study reports that
limitation rather than adding an unproposed fourth mechanism. It has no general
global convergence guarantee beyond the evaluated stopping/failure conditions.

## 3. Stagnation-aware false position

Maintain separate left- and right-endpoint reuse counters, initially zero.
After each nonterminal bracket update, increment a counter if that endpoint
has exactly the same coordinate; otherwise reset it to zero.

At the next iteration, if either counter is at least `reuse_limit`, evaluate
both trisection points and choose the smaller residual. Otherwise use FP.
Default limit: three. Limit two is exposed through `--reuse-limit 2`, reflecting
the proposal's “2–3” range. Both values are tested.

Counters measure actual endpoint reuse. They do not reset merely because a
trisection step was forced. If that step leaves the same endpoint, another
trisection step is appropriate. No unused FP point is computed on a forced
trisection step. Thus the normal/forced costs are one/two new evaluations.

## Benchmark transcription

All functions and intervals below come from Table 1. Angles are in radians.

| ID | f(x) | Interval |
|---|---|---|
| P1 | x² − 3 | [1, 2] |
| P2 | x² − 5 | [2, 7] |
| P3 | x² − 10 | [3, 4] |
| P4 | x² − x − 2 | [1, 4] |
| P5 | x² + 2x − 7 | [1, 3] |
| P6 | x³ − 2 | [0, 2] |
| P7 | x exp(x) − 7 | [0, 2] |
| P8 | x − cos(x) | [0, 1] |
| P9 | x sin(x) − 1 | [0, 2] |
| P10 | x cos(x) + 1 | [−2, 4] |
| P11 | x¹⁰ − 1 | [0, 1.3] |
| P12 | x² + exp(x/2) − 5 | [1, 2] |
| P13 | sin(x) sinh(x) + 1 | [3, 4] |
| P14 | exp(x) − 3x − 2 | [2, 3] |
| P15 | sin(x) − x² | [0.5, 1] |

P12 was checked visually: the exponent is **x/2**, not a division of exp(x).
P4's root in its interval is **2**, not 1. The five optional stress cases are
not from the paper: a high-power polynomial, steep exponential, flat cubic,
scaled quadratic and linear equation. Their tables are separate so they do not
alter claims about the original fifteen problems.

## Experimental design

Every problem/method uses the same tolerance, iteration cap and starting
interval. Each policy has fresh state. The default paper experiment is 150
problem/method pairs, each with a trace run, one untimed warm-up and ten timed
runs. The trace run is not included in timing statistics. Method order within
each repetition is shuffled with seed 402 to reduce fixed-order timing bias.

`perf_counter_ns` gives elapsed wall time; `process_time_ns` gives process CPU
time. Solver construction, evaluation caching and policy decisions are timed;
JSON/CSV output, reference solving, plotting and history recording are not.
The driver checks that timed and traced numerical results agree. Individual
samples, means, medians and wall-time standard deviations are retained.
These cheap functions have microsecond-scale timings; evaluation counts are
the more portable measure of work, while timing captures selector overhead.

Reference roots are obtained independently using 80-digit mpmath bisection
for 270 iterations. Each returned binary64 root is evaluated again using the
high-precision equation to report both actual root error and high-precision
residual. Those diagnostics do not affect any policy or solver stopping rule.
In a multiple-root problem, error is relative to the root selected by reference
bisection; it is not necessarily distance to the nearest root.

Report successes and failures before comparing costs. Aggregate totals include
failed work and are labelled accordingly. Pairwise wins/ties/losses and median
adaptive/baseline ratios use only problems on which **both** methods converge
inside the starting interval; sample counts are supplied. Derivative costs
are not folded into function-call rankings. No statistical-significance claims
or universal superiority claims are made from fifteen chosen equations.

Tolerance sweeps, the two reuse limits, and optional Newton initialization
checks support sensitivity analysis. The implementation does not tune policy
parameters after observing a particular equation's performance.

## Source limitations and corrections

- The proposal says prior comparisons ignore iteration cost. The base paper
  actually also measures average CPU time; what it does not tabulate is an
  explicit function-evaluation budget. This implementation records all three.
- The paper labels some nonzero printed-root residuals as zero. For example,
  substituting the displayed P1 bisection root in x²−3 does not give zero.
  Such printed values are not used as test expectations.
- Table 2 discusses a different apparent accuracy level and its prose calls
  “Error” the difference between iterates, while algorithm stopping uses
  `abs(f(x))`. This project consistently labels residual, root error and bracket
  width separately and uses the algorithmic stopping condition.
- The text around Figures 4–5 attributes root 1 and nine/twelve iterations to
  problem 4. Table 1 and Tables 8–9 identify that behavior with **P11**;
  P4's trisection root is 2 in one iteration.
- Tables 8–9 report BF/TF totals of 121/98. A sound binary64 implementation is
  not required to reproduce these exact totals, given expression ordering,
  rounding, stopping ambiguities and absent source code. Published values and
  measured values are stored side by side, never substituted for one another.
- The geometric bounds `ceil(log_2((b-a)/epsilon))` and
  `ceil(log_3((b-a)/epsilon))` bound **interval width**, not arbitrary function
  residuals. Without additional function information they do not establish the
  iteration count for the residual stopping criterion.
- The paper's broad convergence/superiority statements are not adopted as
  proofs for the new adaptive selectors. A maintained sign-changing bracket
  alone does not establish a useful rate for a greedy switching rule.

## Verification

Tests cover all fifteen equations for each bracketed method; numerical root
accuracy; nested, sign-changing brackets; all analytic derivatives; actual
function/derivative-call accounting; P4's exact root; endpoint roots; zero
derivatives and secant denominators; invalid input; nonfinite/domain failures;
iteration/precision exhaustion; tiny function values and large endpoints;
window ordering; cost normalization; both reuse limits; repeated-run isolation;
and experiment artifact generation and failure-aware comparisons.
