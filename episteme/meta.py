"""Meta-analysis statistics, implemented in pure Python (no numpy / scipy).

Supports fixed-effect (inverse-variance) and random-effects
(DerSimonian-Laird) pooling, the Cochran Q test, the I^2 and H^2
heterogeneity statistics, and tau^2. Effect sizes may be supplied directly
(yi, vi) or derived from 2x2 contingency tables for binary outcomes
(risk ratio, odds ratio, risk difference).

Ratio measures are handled on the log scale; pooled estimates are
back-transformed (exp) for reporting.
"""

from __future__ import annotations

import math
from typing import Sequence, Tuple

from .models import MetaResult

_Z95 = 1.959963984540054  # 97.5% quantile of the standard normal

# Measures handled on the log scale (so CIs must be exponentiated on report).
# Stored lowercase so comparison with measure.lower() works regardless of input case.
_RATIO_MEASURES = {"lnor", "lnrr", "or", "rr"}


# ---------------------------------------------------------------------------
# Regularized incomplete gamma functions (Numerical Recipes), for chi-square p.
# ---------------------------------------------------------------------------
def _gser(a: float, x: float) -> float:
    gln = math.lgamma(a)
    if x <= 0.0:
        return 0.0
    ap = a
    total = 1.0 / a
    delta = total
    for _ in range(1000):
        ap += 1.0
        delta *= x / ap
        total += delta
        if abs(delta) < abs(total) * 1e-12:
            break
    return total * math.exp(-x + a * math.log(x) - gln)


def _gcf(a: float, x: float) -> float:
    gln = math.lgamma(a)
    FPMIN = 1e-300
    b = x + 1.0 - a
    c = 1.0 / FPMIN
    d = 1.0 / b
    h = d
    for i in range(1, 1000):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < FPMIN:
            d = FPMIN
        c = b + an / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-12:
            break
    return math.exp(-x + a * math.log(x) - gln) * h


def gammp(a: float, x: float) -> float:
    """Regularized lower incomplete gamma function P(a, x)."""
    if x < 0 or a <= 0:
        raise ValueError("gammp invalid args")
    if x == 0.0:
        return 0.0
    if x < a + 1.0:
        return _gser(a, x)
    return 1.0 - _gcf(a, x)


def gammq(a: float, x: float) -> float:
    """Regularized upper incomplete gamma function Q(a, x)."""
    if x < 0 or a <= 0:
        raise ValueError("gammq invalid args")
    if x == 0.0:
        return 1.0
    if x < a + 1.0:
        return 1.0 - _gser(a, x)
    return _gcf(a, x)


# ---------------------------------------------------------------------------
# Effect-size derivation from 2x2 tables
# ---------------------------------------------------------------------------
def effect_from_2x2(
    measure: str, a: int, b: int, c: int, d: int
) -> Tuple[float, float]:
    """Return (yi, vi) for a 2x2 table.

    Cells: a = events in treatment, b = non-events in treatment,
           c = events in control,   d = non-events in control.
    A 0.5 continuity correction is applied to any zero cell for OR/RR.
    """
    m = measure.lower()
    if m in ("lnor", "or", "logor"):
        A, B, C, D = (x + 0.5 for x in (a, b, c, d))
        yi = math.log((A * D) / (B * C))
        vi = 1.0 / A + 1.0 / B + 1.0 / C + 1.0 / D
        return yi, vi
    if m in ("lnrr", "rr", "logrr"):
        A, B, C, D = (x + 0.5 for x in (a, b, c, d))
        p1 = A / (A + B)
        p2 = C / (C + D)
        yi = math.log(p1 / p2)
        vi = 1.0 / A - 1.0 / (A + B) + 1.0 / C - 1.0 / (C + D)
        return yi, vi
    if m in ("rd", "riskdiff", "riskdifference"):
        n1 = a + b
        n2 = c + d
        p1 = a / n1
        p2 = c / n2
        yi = p1 - p2
        vi = p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2
        return yi, vi
    raise ValueError(f"unknown 2x2 measure: {measure}")


# ---------------------------------------------------------------------------
# Pooling
# ---------------------------------------------------------------------------
def _pool(studies: Sequence[Tuple[float, float]], tau2: float = 0.0) -> Tuple[float, float]:
    """Inverse-variance pool with a given between-study variance tau2.

    Returns (estimate, se).
    """
    num = 0.0
    den = 0.0
    for yi, vi in studies:
        w = 1.0 / (vi + tau2)
        num += w * yi
        den += w
    est = num / den
    se = math.sqrt(1.0 / den)
    return est, se


def combine(
    studies: Sequence[dict],
    measure: str = "lnOR",
    method: str = "DL",
) -> MetaResult:
    """Combine studies into a meta-analysis.

    `studies` is a list of dicts each with keys 'label', 'yi', 'vi'
    (yi on the analysis scale; for ratio measures that is the log).
    Returns a MetaResult.
    """
    if len(studies) < 2:
        raise ValueError("need at least 2 studies to combine")

    pairs = [(float(s["yi"]), float(s["vi"])) for s in studies]
    k = len(pairs)

    # Fixed-effect pooling (tau2 = 0)
    fe_est, fe_se = _pool(pairs, tau2=0.0)
    fe_low = fe_est - _Z95 * fe_se
    fe_high = fe_est + _Z95 * fe_se

    # Cochran Q (using fixed-effect weights)
    Q = sum((1.0 / vi) * (yi - fe_est) ** 2 for yi, vi in pairs)
    df = k - 1
    q_p = gammq(df / 2.0, Q / 2.0)

    # DerSimonian-Laird tau^2
    w_fixed = [1.0 / vi for _, vi in pairs]
    W = sum(w_fixed)
    C = W - sum(w * w for w in w_fixed) / W
    tau2 = max(0.0, (Q - df) / C) if C > 0 else 0.0

    # Random-effects pooling
    re_est, re_se = _pool(pairs, tau2=tau2)
    re_low = re_est - _Z95 * re_se
    re_high = re_est + _Z95 * re_se

    # Heterogeneity
    I2 = max(0.0, (Q - df) / Q * 100.0) if Q > 0 else 0.0
    H = math.sqrt(Q / df) if df > 0 else 0.0

    per_study = []
    for s, (yi, vi) in zip(studies, pairs):
        w_fe = 1.0 / vi
        w_re = 1.0 / (vi + tau2) if tau2 > 0 else w_fe
        per_study.append(
            {
                "label": s.get("label", ""),
                "yi": yi,
                "vi": vi,
                "se": math.sqrt(vi),
                "weight_fixed": w_fe / W,
                "weight_random": w_re / sum(1.0 / (v + tau2) for _, v in pairs),
            }
        )

    return MetaResult(
        measure=measure,
        k=k,
        fixed_estimate=fe_est,
        fixed_se=fe_se,
        fixed_ci_low=fe_low,
        fixed_ci_high=fe_high,
        random_estimate=re_est,
        random_se=re_se,
        random_ci_low=re_low,
        random_ci_high=re_high,
        q=Q,
        q_df=df,
        q_pvalue=q_p,
        i2=I2,
        tau2=tau2,
        h=H,
        studies=per_study,
    )


def back_transform(est: float, measure: str) -> float:
    """Exponentiate pooled estimates for ratio measures for reporting."""
    if measure.lower() in _RATIO_MEASURES:
        return math.exp(est)
    return est


def ci_back_transform(low: float, high: float, measure: str) -> Tuple[float, float]:
    if measure.lower() in _RATIO_MEASURES:
        return math.exp(low), math.exp(high)
    return low, high
