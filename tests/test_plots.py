"""Tests for SVG plot generation (forest + funnel) and the CLI entry point.

These run entirely on bundled data — no network required.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from episteme import meta as meta_mod
from episteme.cli import main
from episteme.plots import forest_plot, funnel_plot

_DEMO_JSON = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "episteme",
    "data",
    "coffee_sleep_demo.json",
)


def _build_demo_meta(measure="lnOR"):
    with open(_DEMO_JSON) as _f:
        data = json.load(_f)
    studies = []
    for e in data["effects"]:
        yi, vi = meta_mod.effect_from_2x2("OR", *e["table"])
        studies.append({"label": e["label"], "yi": yi, "vi": vi})
    return meta_mod.combine(studies, measure=measure)


def test_forest_plot_generated(tmp_path):
    res = _build_demo_meta()
    out = str(tmp_path / "forest.svg")
    path = forest_plot(res, out, "OR")
    assert os.path.exists(path)
    with open(path) as _f:
        svg = _f.read()
    assert svg.lstrip().startswith("<svg")
    assert "Pooled" in svg
    assert "<line" in svg  # CI whiskers present


def test_funnel_plot_generated(tmp_path):
    res = _build_demo_meta()
    out = str(tmp_path / "funnel.svg")
    path = funnel_plot(res, out, "lnOR")
    assert os.path.exists(path)
    with open(path) as _f:
        svg = _f.read()
    assert svg.lstrip().startswith("<svg")
    assert "<circle" in svg  # study points drawn


def test_demo_produces_plots(tmp_path):
    out = str(tmp_path / "demo")
    rc = main(["demo", "--out", out])
    assert rc == 0
    assert os.path.exists(os.path.join(out, "forest.svg"))
    assert os.path.exists(os.path.join(out, "funnel.svg"))


def test_cli_main_callable():
    assert callable(main)
    # No subcommand -> prints help and returns 1 (does not raise).
    assert main([]) == 1
