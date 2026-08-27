# Contributing to Episteme

Thanks for your interest in improving Episteme! This document explains how to
set up a development environment and how to propose changes.

## Development Setup

Episteme has **no runtime dependencies** (Python 3.8+ standard library only).
The `dev` extra installs the tools used for testing and linting.

```bash
# Clone and enter the repo
git clone https://github.com/harisawan-bit/episteme.git
cd episteme

# Editable install with dev tools (pytest, ruff)
pip install -e ".[dev]"
```

## Running the Tests

```bash
pytest
```

or, quietly:

```bash
pytest -q
```

The suite includes:

- `tests/test_screen.py` — deterministic PRISMA screening rules.
- `tests/test_meta.py` — pure-Python meta-analysis statistics (cross-checked
  against a known teaching dataset).
- `tests/test_e2e.py` — end-to-end demo run plus a **live PubMed smoke test**
  (requires network access to NCBI E-utilities).
- `tests/test_plots.py` — SVG forest/funnel plot generation on bundled data.

> The live PubMed smoke test hits the network. If you are offline, use
> `pytest -q -k "not live"` to skip it.

## Linting

Code is checked with [ruff](https://docs.astral.sh/ruff/):

```bash
ruff check .
```

Please keep new code ruff-clean (trivial fixes only; do not rewrite logic to
satisfy the linter).

## Pull Request Flow

1. **Fork** the repo and create a feature branch from `main`:
   ```bash
   git checkout -b feat/my-improvement main
   ```
2. Make your change with **logical, conventional commits**
   (e.g. `feat:`, `fix:`, `docs:`, `test:`, `chore:`).
3. Ensure the **full local suite passes**:
   ```bash
   pip install -e ".[dev]" && pytest -q
   ```
4. Push your branch and open a PR against `main`:
   ```bash
   gh pr create --base main --fill
   ```
5. Wait for CI to go **all green**. A maintainer (or the bot) will review and
   merge. **Red CI is never merged.**
6. After merge, version bumps and tags are handled by maintainers
   (`git tag vX.Y.Z && git push origin vX.Y.Z`).

## Code Style

- Keep it dependency-free at runtime. New third-party runtime dependencies
  require explicit maintainer approval.
- Prefer deterministic, auditable behavior (this is the whole point of the
  tool).
- Add or update tests for any behavioral change.

## License

By contributing, you agree that your contributions will be licensed under the
MIT License.
