"""Dependency-free SVG plotting for meta-analysis figures.

Produces publication-quality-ish SVGs without matplotlib/plotly/numpy.
- forest_plot: per-study + pooled effects on a log scale, with CI whiskers.
- funnel_plot: standard error vs effect, for asymmetry / small-study bias.
"""

from __future__ import annotations

import math
from typing import List

from .meta import _Z95, back_transform

_W = 820
_H = 440
_ML = 220  # left margin for labels
_MR = 40
_MT = 30
_MB = 50


def _nice_ticks(lo: float, hi: float, n: int = 5) -> List[float]:
    if hi <= lo:
        return [lo]
    span = hi - lo
    step = span / n
    mag = 10 ** math.floor(math.log10(step))
    norm = step / mag
    if norm < 1.5:
        step = 1 * mag
    elif norm < 3:
        step = 2 * mag
    elif norm < 7:
        step = 5 * mag
    else:
        step = 10 * mag
    start = math.ceil(lo / step) * step
    ticks = []
    v = start
    while v <= hi + 1e-9:
        ticks.append(v)
        v += step
    return ticks


def forest_plot(res, path: str, measure_label: str = "Effect") -> str:
    k = len(res.studies)
    h = _MT + _MB + max(40, k * 26) + 60
    studies = res.studies
    pts = []
    for s in studies:
        pts.append((s["yi"], s["vi"]))
    # pooled (random effects)
    pts.append((res.random_estimate, res.random_se ** 2))
    pts.append((res.fixed_estimate, res.fixed_se ** 2))
    all_lo = min(p[0] - _Z95 * math.sqrt(p[1]) for p in pts)
    all_hi = max(p[0] + _Z95 * math.sqrt(p[1]) for p in pts)
    # pad
    lo, hi = all_lo - 0.15 * (all_hi - all_lo), all_hi + 0.15 * (all_hi - all_lo)
    if measure_label.lower() in ("lnor", "or", "lnrr", "rr"):
        lo = max(lo, -3.0)
        hi = min(hi, 3.0)
    x0 = _ML
    x1 = _W - _MR
    sx = lambda v: x0 + (v - lo) / (hi - lo) * (x1 - x0)

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{_W}" height="{h}" font-family="Helvetica,Arial,sans-serif" font-size="12">']
    parts.append(f'<rect width="{_W}" height="{h}" fill="white"/>')
    # gridlines
    for t in _nice_ticks(lo, hi, 6):
        x = sx(t)
        parts.append(f'<line x1="{x:.1f}" y1="{_MT}" x2="{x:.1f}" y2="{_MT + k*26 + 20}" stroke="#e5e5e5"/>')
        if measure_label.lower() in ("lnor", "or", "lnrr", "rr"):
            lbl = f"{back_transform(t, measure_label):.2f}"
        else:
            lbl = f"{t:.2f}"
        parts.append(f'<text x="{x:.1f}" y="{_MT - 8}" text-anchor="middle" fill="#555">{lbl}</text>')
    # zero / null line
    if lo < 0 < hi:
        parts.append(f'<line x1="{sx(0):.1f}" y1="{_MT}" x2="{sx(0):.1f}" y2="{_MT + k*26 + 20}" stroke="#999" stroke-dasharray="4 3"/>')

    y = _MT + 14
    for s in studies:
        est = s["yi"]
        se = s["se"]
        xc = sx(est)
        xl = sx(est - _Z95 * se)
        xr = sx(est + _Z95 * se)
        parts.append(f'<text x="{_ML - 8}" y="{y+4}" text-anchor="end" fill="#222">{_esc(s["label"])[:34]}</text>')
        parts.append(f'<line x1="{xl:.1f}" y1="{y}" x2="{xr:.1f}" y2="{y}" stroke="#333" stroke-width="1.5"/>')
        parts.append(f'<rect x="{xc-3:.1f}" y="{y-3:.1f}" width="6" height="6" fill="#222"/>')
        y += 26

    # pooled random-effects
    re_y = y + 6
    re_lbl = f"{back_transform(res.random_estimate, measure_label):.3f}"
    xc = sx(res.random_estimate)
    xl = sx(res.random_ci_low)
    xr = sx(res.random_ci_high)
    parts.append(f'<line x1="{xl:.1f}" y1="{re_y}" x2="{xr:.1f}" y2="{re_y}" stroke="#c0392b" stroke-width="2.5"/>')
    parts.append(f'<rect x="{xc-4:.1f}" y="{re_y-4:.1f}" width="8" height="8" fill="#c0392b"/>')
    parts.append(f'<text x="{_ML - 8}" y="{re_y+4}" text-anchor="end" fill="#c0392b" font-weight="bold">Pooled (RE)</text>')
    parts.append(f'<text x="{_W - _MR}" y="{re_y+4}" text-anchor="end" fill="#c0392b" font-weight="bold">{re_lbl}</text>')

    # pooled fixed-effect
    fe_y = re_y + 20
    fe_lbl = f"{back_transform(res.fixed_estimate, measure_label):.3f}"
    xc = sx(res.fixed_estimate)
    xl = sx(res.fixed_ci_low)
    xr = sx(res.fixed_ci_high)
    parts.append(f'<line x1="{xl:.1f}" y1="{fe_y}" x2="{xr:.1f}" y2="{fe_y}" stroke="#2c7be5" stroke-width="2"/>')
    parts.append(f'<rect x="{xc-4:.1f}" y="{fe_y-4:.1f}" width="8" height="8" fill="#2c7be5"/>')
    parts.append(f'<text x="{_ML - 8}" y="{fe_y+4}" text-anchor="end" fill="#2c7be5" font-weight="bold">Pooled (FE)</text>')
    parts.append(f'<text x="{_W - _MR}" y="{fe_y+4}" text-anchor="end" fill="#2c7be5" font-weight="bold">{fe_lbl}</text>')

    parts.append(f'<text x="{_ML}" y="{h-14}" fill="#555">Heterogeneity: I²={res.i2:.0f}%  Q={res.q:.1f} (df={res.q_df}, p={res.q_pvalue:.3f})  τ²={res.tau2:.4f}</text>')
    parts.append("</svg>")
    svg = "\n".join(parts)
    with open(path, "w") as f:
        f.write(svg)
    return path


def funnel_plot(res, path: str, measure_label: str = "Effect") -> str:
    studies = res.studies
    se_max = max(s["se"] for s in studies) * 1.15
    w, h = 600, 460
    ml, mr, mt, mb = 70, 30, 30, 50
    est = res.random_estimate

    # effect x-range
    lo = est - 1.6 * se_max
    hi = est + 1.6 * se_max
    x0, x1 = ml, w - mr
    y0, y1 = mt, h - mb
    sx = lambda v: x0 + (v - lo) / (hi - lo) * (x1 - x0)
    sy = lambda se: y1 - (se / se_max) * (y1 - y0)

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" font-family="Helvetica,Arial,sans-serif" font-size="12">']
    parts.append(f'<rect width="{w}" height="{h}" fill="white"/>')
    # pooled effect line
    parts.append(f'<line x1="{sx(est):.1f}" y1="{y0}" x2="{sx(est):.1f}" y2="{y1}" stroke="#c0392b" stroke-dasharray="4 3"/>')
    # 95% pseudo-CI funnel (est ± f*1.96*se) for f = 1, 2
    for f in (1.0, 2.0):
        for sgn in (-1, 1):
            x_b = est + sgn * f * _Z95 * se_max
            parts.append(
                f'<line x1="{sx(x_b):.1f}" y1="{sy(se_max):.1f}" '
                f'x2="{sx(est):.1f}" y2="{sy(0):.1f}" '
                f'stroke="#e74c3c" stroke-opacity="0.35"/>'
            )
    # points
    for s in studies:
        x = sx(s["yi"])
        y = sy(s["se"])
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#34495e" fill-opacity="0.7"/>')
    # axes labels
    parts.append(f'<text x="{(x0+x1)/2:.1f}" y="{h-14}" text-anchor="middle" fill="#555">Effect ({measure_label})</text>')
    parts.append(f'<text x="16" y="{(y0+y1)/2:.1f}" text-anchor="middle" fill="#555" transform="rotate(-90 16 {(y0+y1)/2:.1f})">Standard error</text>')
    parts.append("</svg>")
    svg = "\n".join(parts)
    with open(path, "w") as f:
        f.write(svg)
    return path


def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
