"""End-to-end tests: demo run produces valid artifacts, and live PubMed works."""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from episteme.cli import main
from episteme.report import prisma_svg
from episteme import pubmed


def test_demo_end_to_end(tmp_path):
    out = str(tmp_path / "demo")
    rc = main(["demo", "--out", out])
    assert rc == 0
    for f in ("summary.md", "audit.json", "prisma.svg", "forest.svg", "funnel.svg"):
        assert os.path.exists(os.path.join(out, f)), f
    # audit is valid JSON with decisions
    audit = json.load(open(os.path.join(out, "audit.json")))
    assert audit["summary"]["total_fetched"] == 8
    assert audit["summary"]["included"] >= 1
    # summary mentions pooled estimate
    md = open(os.path.join(out, "summary.md")).read()
    assert "Random-effects" in md


def test_prisma_svg_writes():
    import tempfile

    p = tempfile.mktemp(suffix=".svg")
    prisma_svg({"identified": 47, "screened": 8, "excluded": 5, "included": 3}, p)
    assert os.path.getsize(p) > 200


def test_pubmed_live_smoke():
    """Live check that PubMed E-utilities returns real records."""
    res = pubmed.collect("caffeine sleep randomized controlled trial", max_results=10)
    assert res["count"] > 0
    assert len(res["studies"]) > 0
    s = res["studies"][0]
    assert s.pmid
    assert s.title
