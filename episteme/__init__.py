"""Episteme: reproducible, dependency-free evidence synthesis.

A systematic-review + meta-analysis engine that pulls records from PubMed
(E-utilities, no API key), screens them with auditable PRISMA rules, runs the
statistics with a pure-Python implementation of standard meta-analysis methods,
and emits a PRISMA flow diagram, forest/funnel plots, and a full audit log.

Zero hard dependencies -- Python 3.8+ standard library only.
"""

__version__ = "0.2.0"
