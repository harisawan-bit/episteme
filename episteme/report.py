"""Report generation: PRISMA flow diagram (SVG), audit log, markdown summary."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import List

from .models import ScreenResult, MetaResult, Decision
from .screen import ScreenRules
from .meta import back_transform, ci_back_transform

_FLOW = [
    ("Identification", "Records identified from PubMed search", "identified"),
    ("Screening", "Records screened (deduplicated)", "screened"),
    ("Screening", "Records excluded by deterministic rules", "excluded"),
    ("Eligibility", "Studies included for quantitative synthesis", "included"),
]


def prisma_svg(counts: dict, path: str) -> str:
    """counts keys: identified, screened, excluded, included."""
    rows = [
        ("Identification", "Records identified in PubMed search", counts.get("identified", 0)),
        ("Screening", "Records after de-duplication (screened)", counts.get("screened", 0)),
        ("Screening", "Records excluded by deterministic rules", counts.get("excluded", 0)),
        ("Eligibility", "Studies included for quantitative synthesis", counts.get("included", 0)),
    ]
    W, H = 720, 320
    x0, x1 = 40, 560
    bw = 360
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="Helvetica,Arial,sans-serif" font-size="13">']
    parts.append(f'<rect width="{W}" height="{H}" fill="white"/>')
    parts.append(f'<text x="20" y="24" font-weight="bold" font-size="15" fill="#222">PRISMA 2020 flow</text>')
    y = 50
    for stage, label, n in rows:
        parts.append(f'<rect x="{x0}" y="{y}" width="{bw}" height="40" fill="#f4f6f8" stroke="#cdd6df"/>')
        parts.append(f'<text x="{x0+10}" y="{y+25}" fill="#222">{label}</text>')
        parts.append(f'<rect x="{x1}" y="{y}" width="100" height="40" fill="#dbe7f3" stroke="#9bb8d6"/>')
        parts.append(f'<text x="{x1+50}" y="{y+25}" text-anchor="middle" font-weight="bold" fill="#1c3d5a">{n}</text>')
        y += 60
    parts.append("</svg>")
    svg = "\n".join(parts)
    with open(path, "w") as f:
        f.write(svg)
    return path


def audit_log(query: str, rules: ScreenRules, results: List[ScreenResult], path: str) -> dict:
    """Write a machine-readable audit JSON capturing everything needed to reproduce."""
    included = [r for r in results if r.decision == Decision.INCLUDE]
    excluded = [r for r in results if r.decision == Decision.EXCLUDE]
    uncertain = [r for r in results if r.decision == Decision.UNCERTAIN]
    audit = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "query": query,
        "rules": rules.to_dict(),
        "summary": {
            "total_fetched": len(results),
            "included": len(included),
            "excluded": len(excluded),
            "uncertain": len(uncertain),
        },
        "decisions": [
            {
                "pmid": r.study.pmid,
                "title": r.study.title,
                "year": r.study.year,
                "decision": r.decision.value,
                "rules": r.rules,
                "reasons": r.reasons,
            }
            for r in results
        ],
    }
    with open(path, "w") as f:
        json.dump(audit, f, indent=2)
    return audit


def markdown_summary(query: str, counts: dict, audit: dict, meta: MetaResult = None) -> str:
    lines = ["# Episteme systematic-review summary", ""]
    lines.append(f"- **Query:** `{query}`")
    lines.append(f"- **Generated (UTC):** {audit.get('generated_utc', '')}")
    lines.append("")
    lines.append("## PRISMA flow")
    lines.append("")
    lines.append("| Stage | Count |")
    lines.append("|---|---|")
    lines.append(f"| Identified (PubMed hits) | {counts.get('identified', 0)} |")
    lines.append(f"| Fetched & screened | {counts.get('screened', 0)} |")
    lines.append(f"| Excluded by rules | {counts.get('excluded', 0)} |")
    lines.append(f"| Included | {counts.get('included', 0)} |")
    lines.append("")
    if meta is not None:
        m = meta.measure
        re_est = back_transform(meta.random_estimate, m)
        re_lo, re_hi = ci_back_transform(meta.random_ci_low, meta.random_ci_high, m)
        fe_est = back_transform(meta.fixed_estimate, m)
        fe_lo, fe_hi = ci_back_transform(meta.fixed_ci_low, meta.fixed_ci_high, m)
        unit = " (ratio)" if m in ("lnOR", "OR", "lnRR", "RR") else ""
        lines.append("## Meta-analysis")
        lines.append("")
        lines.append(f"- **Measure:** {m}{unit}")
        lines.append(f"- **Studies (k):** {meta.k}")
        lines.append(
            f"- **Random-effects (DL):** {re_est:.3f} "
            f"95% CI [{re_lo:.3f}, {re_hi:.3f}]"
        )
        lines.append(
            f"- **Fixed-effect:** {fe_est:.3f} 95% CI [{fe_lo:.3f}, {fe_hi:.3f}]"
        )
        lines.append(
            f"- **Heterogeneity:** I²={meta.i2:.1f}%, Q={meta.q:.2f} "
            f"(df={meta.q_df}, p={meta.q_pvalue:.3f}), τ²={meta.tau2:.4f}"
        )
        lines.append("")
    lines.append("## Screening decisions")
    lines.append("")
    for d in audit["decisions"]:
        tag = d["decision"].upper()
        lines.append(f"- **{tag}** `PMID:{d['pmid']}` {d['title'][:80]} — {', '.join(d['rules'])}")
    return "\n".join(lines)
