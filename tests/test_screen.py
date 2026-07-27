"""Tests for deterministic PRISMA screening."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from episteme.models import Study, Decision
from episteme.screen import ScreenRules, screen


def _s(pmid, title, abstract="", year=2020, lang="eng", human=True):
    a = abstract + (" human participants." if human else " in rats.")
    return Study(pmid=pmid, title=title, abstract=a, year=year, language=lang)


def test_exclude_non_english():
    r = screen([_s("1", "Coffee sleep", lang="ger")], ScreenRules())
    assert r[0].decision == Decision.EXCLUDE
    assert "lang" in r[0].rules


def test_exclude_old_year():
    r = screen([_s("1", "Coffee sleep", year=2005)], ScreenRules(min_year=2015))
    assert r[0].decision == Decision.EXCLUDE
    assert "year" in r[0].rules


def test_exclude_animal_only():
    r = screen([_s("1", "Coffee sleep", human=False)], ScreenRules(require_human=True))
    assert r[0].decision == Decision.EXCLUDE
    assert "animal" in r[0].rules


def test_exclude_term():
    r = screen([_s("1", "Coffee sleep review", abstract="this is a review")], ScreenRules(exclude_any=["review"]))
    assert r[0].decision == Decision.EXCLUDE


def test_include_with_requirement():
    rules = ScreenRules(include_all=["sleep", "coffee"])
    r = screen([_s("1", "Coffee and sleep", abstract="coffee affects sleep")], rules)
    assert r[0].decision == Decision.INCLUDE


def test_requirement_missing():
    rules = ScreenRules(include_all=["sleep", "coffee"])
    r = screen([_s("1", "Tea and sleep", abstract="tea affects sleep")], rules)
    assert r[0].decision == Decision.EXCLUDE


def test_full_pipeline_counts():
    studies = [
        _s("1", "Coffee sleep", "caffeine and sleep", human=True),
        _s("2", "Coffee review", "a review of coffee", human=True),
        _s("3", "Coffee rats", "rats given caffeine", human=False),
        _s("4", "Coffee sleep ger", "kaffee schlaf", year=2021, lang="ger"),
    ]
    rules = ScreenRules(include_all=["sleep"], exclude_any=["review"], require_human=True)
    results = screen(studies, rules)
    incl = [x for x in results if x.decision == Decision.INCLUDE]
    excl = [x for x in results if x.decision == Decision.EXCLUDE]
    assert len(incl) == 1
    assert len(excl) == 3
