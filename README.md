# Episteme

[![CI](https://github.com/harisawan-bit/episteme/actions/workflows/ci.yml/badge.svg)](https://github.com/harisawan-bit/episteme/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/episteme.svg)](https://pypi.org/project/episteme/)
[![Python](https://img.shields.io/pypi/pyversions/episteme.svg)](https://pypi.org/project/episteme/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> Reproducible, dependency-free systematic-review & meta-analysis engine.

**PubMed → PRISMA screening → meta-analysis → publication figures, in one command — no paid APIs, no numpy, no R.**

Evidence synthesis (systematic reviews, meta-analyses) is the backbone of
evidence-based medicine, yet the tooling is fragmented: you jump between
literature databases, a screening spreadsheet, R/RevMan for statistics, and a
diagram tool for the PRISMA flow. **Episteme collapses that into one
auditable, reproducible pipeline you can re-run and put in version control.**

This matters because the defining crisis in evidence synthesis is
**reproducibility**: most reviews cannot be re-executed from a script. Episteme
makes the entire screening + analysis pass deterministic and machine-checkable.

## Why this is different

| Existing tools | Episteme |
|---|---|
| One-off project scripts / notebooks | Reusable, packaged engine |
| LLM "agent skills" (non-deterministic) | Deterministic, auditable baseline by default |
| R/RevMan (heavy install) | Pure Python stdlib — zero hard deps |
| Manual PRISMA diagrams | Generated SVG PRISMA flow |
| Paid literature APIs | PubMed E-utilities (free, no key) |
| Stats locked in GUI | Forest + funnel plots as editable SVG |

The "revolutionary" claim is modest but real: **a review becomes a command
plus a config file, not a months-long manual effort** — and anyone can
re-run it and get the same result.

## Features

- **PubMed retrieval** via NCBI E-utilities — free, no API key, polite rate-limiting.
- **Deterministic PRISMA screening** with auditable rules (language, year,
  animal-only, exclusion terms, required terms). Every decision records the
  exact rule keys that fired.
- **Meta-analysis statistics** implemented from scratch in pure Python:
  - Fixed-effect (inverse-variance) and random-effects (DerSimonian–Laird) pooling
  - Cochran Q test (chi-square p-value via regularized incomplete gamma)
  - Heterogeneity: I², H², τ²
  - Effect sizes from 2×2 tables: OR, RR, RD (log scale for ratios)
- **Dependency-free plots** rendered as SVG: forest plot (per-study + pooled
  CI whiskers) and funnel plot (small-study bias).
- **PRISMA 2020 flow diagram** as SVG.
- **Full audit log** (JSON) + markdown summary — everything needed to reproduce.

## Install

```bash
pip install -e .
```

Requires Python ≥ 3.8. No third-party packages needed at runtime.

## Quick start

```bash
# A self-contained demo (no network) — runs on bundled data:
episteme demo --out ./out

# A live, reproducible review from PubMed:
episteme run \
  --query "coffee sleep randomized controlled trial" \
  --max 200 \
  --require sleep \
  --exclude review commentary editorial \
  --min-year 2015 \
  --human \
  --out ./review
```

Artifacts written to `--out`:
- `audit.json` — every decision + the rule keys that fired (reproducibility proof)
- `prisma.svg` — PRISMA 2020 flow diagram
- `forest.svg` / `funnel.svg` — meta-analysis figures
- `summary.md` — human-readable summary

### Adding a quantitative meta-analysis

Supply extracted effect sizes as JSON (2×2 tables or pre-computed `yi`/`vi`):

```bash
episteme run --query "..." --effects effects.json
```

```json
[
  {"label": "Smith 2021", "measure": "OR", "table": [10, 30, 22, 18]},
  {"label": "Lee 2019",   "yi": -0.55, "vi": 0.08}
]
```

## Architecture

```
episteme/
  pubmed.py   # NCBI E-utilities fetch + de-duplication
  screen.py   # deterministic PRISMA rule engine
  meta.py     # pure-Python meta-analysis statistics
  plots.py    # SVG forest + funnel (no matplotlib)
  report.py   # PRISMA SVG + audit log + markdown
  cli.py      # command-line entry point
  data/       # bundled demo dataset
tests/        # unit + e2e (incl. live PubMed smoke test)
```

## Reproducibility

The deterministic screening pass is fully reproducible from a config + the
source records; `audit.json` captures both. Human/LLM adjudication of
`UNCERTAIN` records is intended to layer on top and is logged separately.

## Limitations

- PubMed only (extend `pubmed.py` with Europe PMC / Cochrane for breadth).
- Statistics cover the common binary/continuous effect sizes; network
  meta-analysis, meta-regression, and publication-bias tests (Egger/Begg) are
  planned.
- Screening is keyword/rule-based; it is a transparent baseline, not a
  substitute for full human review of included studies.

## License

MIT — see [LICENSE](LICENSE).
