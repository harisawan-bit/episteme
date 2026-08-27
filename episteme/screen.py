"""Auditable, rule-based PRISMA screening.

Screening rules are transparent and machine-checkable: every decision records
the exact rule keys that fired and the human-readable reason, so the entire
screening pass is reproducible from the `rules` config + the source records.
This is intentionally deterministic (no LLM calls) so that a review can be
re-run and produce the same result -- satisfying the core requirement of
reproducible evidence synthesis.

An LLM/human can be layered on top for nuanced calls; Episteme keeps the
deterministic baseline in version control.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

from .models import Decision, ScreenResult, Study

# Language codes accepted as "English" (PubMed uses ISO-639-2, e.g. 'eng').
_ENGLISH = {"eng", "en", ""}


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", (text or "").lower())


@dataclass
class ScreenRules:
    """Deterministic screening configuration.

    include_all: study is INCLUDED only if every term here appears in
                 title+abstract (empty => no positive requirement).
    exclude_any: study is EXCLUDED if any term here appears.
    min_year:     exclude if publication year is before this.
    allow_languages: set of accepted language codes (default English + unknown).
    require_human: exclude animal-only studies (abstract mentions 'animal'/'rat'/
                   'mouse' but not 'human').
    max_included: cap on included studies (0 = unlimited).
    """

    include_all: List[str] = field(default_factory=list)
    exclude_any: List[str] = field(default_factory=list)
    min_year: Optional[int] = None
    allow_languages: set = field(default_factory=lambda: set(_ENGLISH))
    require_human: bool = False
    max_included: int = 0

    def to_dict(self) -> dict:
        d = {
            "include_all": self.include_all,
            "exclude_any": self.exclude_any,
            "min_year": self.min_year,
            "allow_languages": sorted(self.allow_languages),
            "require_human": self.require_human,
            "max_included": self.max_included,
        }
        return d


def screen_study(study: Study, rules: ScreenRules) -> ScreenResult:
    text = _norm(f"{study.title} {study.abstract}")
    reasons: List[str] = []
    rule_keys: List[str] = []

    # 1. Language filter
    if study.language not in rules.allow_languages:
        reasons.append(f"language '{study.language or 'unknown'}' not in allowed set")
        rule_keys.append("lang")
        return ScreenResult(study, Decision.EXCLUDE, reasons, rule_keys)

    # 2. Year filter
    if rules.min_year is not None and study.year is not None and study.year < rules.min_year:
        reasons.append(f"year {study.year} < min_year {rules.min_year}")
        rule_keys.append("year")
        return ScreenResult(study, Decision.EXCLUDE, reasons, rule_keys)

    # 3. Animal-only filter
    if rules.require_human and re.search(
        r"\b(animal|rats?|mice|mouse|canine|feline|porcine)\b", text
    ) and not re.search(r"\bhuman(s)?\b", text):
        reasons.append("animal-only study (no human participants mentioned)")
        rule_keys.append("animal")
        return ScreenResult(study, Decision.EXCLUDE, reasons, rule_keys)

    # 4. Explicit exclusion terms
    for term in rules.exclude_any:
        if _norm(term) in text:
            reasons.append(f"matched exclude term '{term}'")
            rule_keys.append(f"exclude:{term}")
            return ScreenResult(study, Decision.EXCLUDE, reasons, rule_keys)

    # 5. Positive requirement
    if rules.include_all:
        missing = [t for t in rules.include_all if _norm(t) not in text]
        if missing:
            reasons.append("missing required term(s): " + ", ".join(missing))
            rule_keys.append("require")
            return ScreenResult(study, Decision.EXCLUDE, reasons, rule_keys)

    reasons.append("passed all deterministic screen rules")
    rule_keys.append("pass")
    return ScreenResult(study, Decision.INCLUDE, reasons, rule_keys)


def screen(studies: List[Study], rules: ScreenRules) -> List[ScreenResult]:
    out: List[ScreenResult] = []
    included = 0
    for s in studies:
        r = screen_study(s, rules)
        if r.decision == Decision.INCLUDE:
            included += 1
            if rules.max_included and included > rules.max_included:
                # convert to uncertain (capped) rather than silently dropping
                r = ScreenResult(s, Decision.UNCERTAIN, ["included cap reached"], ["cap"])
        out.append(r)
    return out
