"""Data models shared across the Episteme pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Optional


class Decision(str, Enum):
    INCLUDE = "include"
    EXCLUDE = "exclude"
    UNCERTAIN = "uncertain"


@dataclass
class Study:
    """A single bibliographic record (e.g. a PubMed article)."""

    pmid: str
    title: str = ""
    abstract: str = ""
    year: Optional[int] = None
    authors: List[str] = field(default_factory=list)
    journal: str = ""
    doi: str = ""
    language: str = ""
    # Optional pre-extracted effect size (supplied by the user / a human-in-the-loop
    # extraction step). yi = point estimate on the analysis scale (e.g. log OR),
    # vi = its variance. Left blank when not yet extracted.
    yi: Optional[float] = None
    vi: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Study":
        d = dict(d)
        d.setdefault("authors", [])
        return cls(**d)


@dataclass
class ScreenResult:
    """Outcome of screening one study."""

    study: Study
    decision: Decision
    # Human-readable reasons, one per rule that fired (exclusions) or note (inclusions).
    reasons: List[str] = field(default_factory=list)
    # Machine-readable rule keys that fired.
    rules: List[str] = field(default_factory=list)


@dataclass
class MetaResult:
    """Result of a meta-analysis combination."""

    measure: str
    k: int
    # Fixed-effects
    fixed_estimate: float
    fixed_se: float
    fixed_ci_low: float
    fixed_ci_high: float
    # Random-effects (DerSimonian-Laird)
    random_estimate: float
    random_se: float
    random_ci_low: float
    random_ci_high: float
    # Heterogeneity
    q: float
    q_df: int
    q_pvalue: float
    i2: float
    tau2: float
    h: float
    # Per-study (for plotting)
    studies: List[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)
