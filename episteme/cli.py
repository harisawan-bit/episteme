"""Episteme command-line interface.

Usage:
  episteme demo            # run a self-contained demo (no network) on bundled data
  episteme run --query "..." [--max 200] [--out DIR] [--effort 2x2 ...]
  episteme --help

The `run` command performs a full reproducible pipeline:
  PubMed search -> fetch -> deterministic PRISMA screen -> (optional) meta-analysis
  -> PRISMA diagram + forest/funnel plots + audit log + markdown summary.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

from . import __version__
from .models import Decision, Study
from .screen import ScreenRules, screen
from .pubmed import collect
from .meta import combine, effect_from_2x2
from .plots import forest_plot, funnel_plot
from .report import prisma_svg, audit_log, markdown_summary

HERE = os.path.dirname(os.path.abspath(__file__))
DEMO_JSON = os.path.join(HERE, "data", "coffee_sleep_demo.json")


def _load_demo_studies() -> list:
    with open(DEMO_JSON) as f:
        data = json.load(f)
    return [Study.from_dict(d) for d in data["studies"]]


def cmd_demo(args) -> int:
    studies = _load_demo_studies()
    rules = ScreenRules(
        include_all=["sleep"],
        exclude_any=["review", "commentary", "editorial"],
        min_year=2015,
        require_human=True,
    )
    results = screen(studies, rules)
    out = args.out or os.path.join(os.getcwd(), "episteme_demo_out")
    os.makedirs(out, exist_ok=True)
    audit = audit_log("(demo) coffee sleep", rules, results, os.path.join(out, "audit.json"))

    # Build a synthetic 2x2 meta-analysis from the demo effect table.
    eff = json.load(open(DEMO_JSON))["effects"]
    meta_studies = [
        {"label": e["label"], "yi": effect_from_2x2("OR", *e["table"])[0],
         "vi": effect_from_2x2("OR", *e["table"])[1]}
        for e in eff
    ]
    if len(meta_studies) >= 2:
        meta = combine(meta_studies, measure="lnOR")
        forest_plot(meta, os.path.join(out, "forest.svg"), "OR")
        funnel_plot(meta, os.path.join(out, "funnel.svg"), "lnOR")
        prisma_svg(
            {"identified": 47, "screened": len(results), "excluded": audit["summary"]["excluded"],
             "included": audit["summary"]["included"]},
            os.path.join(out, "prisma.svg"),
        )
        md = markdown_summary("(demo) coffee & sleep", {"identified": 47, "screened": len(results),
                                                        "excluded": audit["summary"]["excluded"],
                                                        "included": audit["summary"]["included"]}, audit, meta)
    else:
        md = markdown_summary("(demo) coffee & sleep",
                              {"identified": 47, "screened": len(results),
                               "excluded": audit["summary"]["excluded"],
                               "included": audit["summary"]["included"]}, audit)
    with open(os.path.join(out, "summary.md"), "w") as f:
        f.write(md)
    print(md)
    print(f"\n[demo] artifacts written to {out}")
    return 0


def cmd_run(args) -> int:
    if not args.query:
        print("error: --query is required", file=sys.stderr)
        return 2
    out = args.out or os.path.join(os.getcwd(), "episteme_run_out")
    os.makedirs(out, exist_ok=True)

    print(f"[run] searching PubMed: {args.query!r}")
    res = collect(args.query, max_results=args.max)
    total = res["count"]
    studies = res["studies"]
    print(f"[run] PubMed reports {total} hits; fetched {len(studies)} records.")

    rules = ScreenRules(
        include_all=args.require or [],
        exclude_any=args.exclude or [],
        min_year=args.min_year,
        require_human=args.human,
    )
    if args.language:
        rules.allow_languages = set(args.language)

    results = screen(studies, rules)
    audit = audit_log(args.query, rules, results, os.path.join(out, "audit.json"))

    included = [r for r in results if r.decision == Decision.INCLUDE]

    # Optional meta-analysis from a supplied effects JSON file.
    meta = None
    if args.effects and os.path.exists(args.effects):
        eff = json.load(open(args.effects))
        meta_studies = []
        for e in eff:
            if "table" in e:
                yi, vi = effect_from_2x2(e.get("measure", "OR"), *e["table"])
            else:
                yi, vi = e["yi"], e["vi"]
            meta_studies.append({"label": e["label"], "yi": yi, "vi": vi})
        if len(meta_studies) >= 2:
            meta = combine(meta_studies, measure=args.measure)
            forest_plot(meta, os.path.join(out, "forest.svg"), args.measure)
            funnel_plot(meta, os.path.join(out, "funnel.svg"), args.measure)

    prisma_svg(
        {"identified": total, "screened": len(studies),
         "excluded": audit["summary"]["excluded"], "included": audit["summary"]["included"]},
        os.path.join(out, "prisma.svg"),
    )
    md = markdown_summary(args.query,
                          {"identified": total, "screened": len(studies),
                           "excluded": audit["summary"]["excluded"],
                           "included": audit["summary"]["included"]}, audit, meta)
    with open(os.path.join(out, "summary.md"), "w") as f:
        f.write(md)
    print(md)
    print(f"\n[run] artifacts written to {out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="episteme", description="Reproducible systematic-review + meta-analysis engine")
    p.add_argument("--version", action="version", version=f"episteme {__version__}")
    sub = p.add_subparsers(dest="cmd")

    d = sub.add_parser("demo", help="run a self-contained demo (no network)")
    d.add_argument("--out", default=None)
    d.set_defaults(func=cmd_demo)

    r = sub.add_parser("run", help="run a live PubMed pipeline")
    r.add_argument("--query", default=None, help="PubMed search query")
    r.add_argument("--max", type=int, default=200, help="max records to fetch")
    r.add_argument("--require", nargs="*", default=[], help="terms that must all appear")
    r.add_argument("--exclude", nargs="*", default=[], help="terms that cause exclusion")
    r.add_argument("--min-year", type=int, default=None)
    r.add_argument("--language", nargs="*", default=None, help="allowed language codes")
    r.add_argument("--human", action="store_true", help="exclude animal-only studies")
    r.add_argument("--effects", default=None, help="path to effects JSON for meta-analysis")
    r.add_argument("--measure", default="lnOR", help="effect measure (lnOR/OR/lnRR/RR/rd)")
    r.add_argument("--out", default=None)
    r.set_defaults(func=cmd_run)
    return p


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "cmd", None):
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
