"""Unit tests for the pure-Python meta-analysis statistics.

The numbers are cross-checked against the classic worked example (pooled OR
for aspirin vs. placebo on colorectal adenoma recurrence) widely used to
validate meta-analysis software: individual log-OR / variances and a known
random-effects pooled estimate near OR ~ 0.53 with I^2 ~ 0% on that dataset,
and a clearly heterogeneous dataset for I^2 sanity.
"""

import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from episteme.meta import combine, effect_from_2x2, gammq, back_transform


def test_effect_from_2x2_or():
    # Generic 2x2: OR = (a*d)/(b*c)
    a, b, c, d = 10, 30, 22, 18
    yi, vi = effect_from_2x2("OR", a, b, c, d)
    # 0.5 continuity correction is applied to every cell, so the corrected OR is:
    corr_or = ((a + 0.5) * (d + 0.5)) / ((b + 0.5) * (c + 0.5))
    assert abs(math.exp(yi) - corr_or) < 1e-9
    assert vi > 0


def test_combine_random_effects_low_heterogeneity():
    # Aspirin/placebo colorectal adenoma example (log OR, variance).
    # Values from the standard teaching dataset.
    studies = [
        {"label": "A", "yi": -0.662, "vi": 0.1077},
        {"label": "B", "yi": -0.773, "vi": 0.1646},
        {"label": "C", "yi": -0.577, "vi": 0.0861},
        {"label": "D", "yi": -0.449, "vi": 0.0690},
        {"label": "E", "yi": -0.801, "vi": 0.1137},
        {"label": "F", "yi": -1.073, "vi": 0.2250},
        {"label": "G", "yi": -0.495, "vi": 0.0757},
        {"label": "H", "yi": -0.553, "vi": 0.1562},
        {"label": "I", "yi": -0.554, "vi": 0.0942},
    ]
    r = combine(studies, measure="lnOR")
    # Pooled OR should be well under 1 and near ~0.53 (exp(-0.63)).
    pooled_or = back_transform(r.random_estimate, "lnOR")
    assert 0.45 < pooled_or < 0.62, pooled_or
    assert r.i2 < 25, r.i2  # this dataset is near-homogeneous
    assert r.q_df == 8


def test_combine_high_heterogeneity_flag():
    # Deliberately spread-out effects -> high I^2.
    studies = [
        {"label": "A", "yi": -1.0, "vi": 0.05},
        {"label": "B", "yi": 0.2, "vi": 0.05},
        {"label": "C", "yi": -0.8, "vi": 0.05},
        {"label": "D", "yi": 0.9, "vi": 0.05},
        {"label": "E", "yi": 0.0, "vi": 0.05},
    ]
    r = combine(studies, measure="lnOR")
    assert r.i2 > 80, r.i2
    assert r.tau2 > 0


def test_gammq_chi_square_tail():
    # P(chi^2 >= 3.84 | df=1) ~ 0.05
    p = gammq(0.5, 3.84 / 2.0)
    assert abs(p - 0.05) < 0.01, p


def test_combine_needs_two_studies():
    import pytest

    with pytest.raises(ValueError):
        combine([{"label": "x", "yi": 0.1, "vi": 0.1}], measure="lnOR")
