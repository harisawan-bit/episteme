"""PubMed retrieval via NCBI E-utilities (no API key required).

Pipeline: esearch -> efetch (XML) -> list[Study].
Respects NCBI's rate limit (~3 req/s without a key) with a small delay.
"""

from __future__ import annotations

import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import List, Optional

from .models import Study

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
_TOOL = "episteme"
_EMAIL = "episteme@example.com"

_HEADERS = {"User-Agent": "episteme/0.1 (+https://github.com/harisawan-bit/episteme)"}


def _get(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def search(query: str, retmax: int = 200, retstart: int = 0) -> dict:
    """Run esearch. Returns {'count': int, 'ids': list[str]}."""
    params = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": retmax,
        "retstart": retstart,
        "tool": _TOOL,
        "email": _EMAIL,
    }
    url = f"{EUTILS}/esearch.fcgi?{urllib.parse.urlencode(params)}"
    # json comes back inside a browser-toggle; parse robustly
    import json

    data = json.loads(_get(url))
    res = data["esearchresult"]
    return {"count": int(res["count"]), "ids": list(res.get("idlist", []))}


def _parse_year(article) -> Optional[int]:
    for tag in ("ArticleDate", "Journal/JournalIssue/PubDate"):
        el = article.find(tag)
        if el is not None:
            y = el.findtext("Year")
            if y and y.isdigit():
                return int(y)
    return None


def fetch_records(ids: List[str]) -> List[Study]:
    """Fetch full records for a list of PMIDs (batched by 200)."""
    studies: List[Study] = []
    for i in range(0, len(ids), 200):
        batch = ids[i : i + 200]
        params = {
            "db": "pubmed",
            "id": ",".join(batch),
            "rettype": "full",
            "retmode": "xml",
            "tool": _TOOL,
            "email": _EMAIL,
        }
        url = f"{EUTILS}/efetch.fcgi?{urllib.parse.urlencode(params)}"
        root = ET.fromstring(_get(url))
        for art in root.iter("PubmedArticle"):
            pmid = art.findtext(".//PMID")
            if not pmid:
                continue
            title = (art.findtext(".//ArticleTitle") or "").strip()
            abstract = " ".join(
                (t.text or "") for t in art.findall(".//Abstract/AbstractText")
            ).strip()
            authors = []
            for a in art.findall(".//AuthorList/Author"):
                fore = a.findtext("ForeName") or ""
                last = a.findtext("LastName") or ""
                name = (fore + " " + last).strip()
                if name:
                    authors.append(name)
            journal = (art.findtext(".//Journal/Title") or "").strip()
            language = (art.findtext(".//Language") or "").strip()
            doi = ""
            for idnode in art.findall(".//ArticleId"):
                if idnode.get("IdType") == "doi":
                    doi = (idnode.text or "").strip()
            year = _parse_year(art)
            studies.append(
                Study(
                    pmid=pmid,
                    title=title,
                    abstract=abstract,
                    year=year,
                    authors=authors,
                    journal=journal,
                    doi=doi,
                    language=language,
                )
            )
        time.sleep(0.34)  # be polite to NCBI
    return studies


def collect(query: str, max_results: int = 200) -> dict:
    """End-to-end: search + fetch + deduplicate by PMID.

    Returns {'count': total_pubmed_hits, 'studies': list[Study]} where
    `studies` is the fetched (deduplicated) sample up to `max_results`.
    """
    total = search(query, retmax=1)["count"]
    ids: List[str] = []
    fetched = 0
    while fetched < max_results:
        batch = search(query, retmax=min(200, max_results - fetched), retstart=fetched)
        if not batch["ids"]:
            break
        ids.extend(batch["ids"])
        fetched += len(batch["ids"])
        time.sleep(0.34)
    seen = set()
    studies = []
    for s in fetch_records(ids):
        if s.pmid in seen:
            continue
        seen.add(s.pmid)
        studies.append(s)
    return {"count": total, "studies": studies}
