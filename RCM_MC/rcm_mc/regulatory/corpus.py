"""Regulatory document corpus — the input to TF-IDF + topic scoring.

Each document is one regulatory artefact:
  • A Federal Register entry (proposed/final rule)
  • An OIG enforcement action (settlement / exclusion)
  • An FTC notice (consent order, complaint, policy statement)
  • A state legislative bill (CON repeal, CPOM amendment, etc.)
  • A CMS rule or sub-regulatory guidance

The corpus is pluggable — the package ships a small fixture
corpus for testing, but the real deployment ingests RSS feeds
+ manual curation into the same shape.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Iterable, List, Optional


_VALID_SOURCES = (
    "federal_register",
    "oig_enforcement",
    "ftc_notice",
    "state_legislation",
    "cms_rule",
    "cms_guidance",
)


@dataclass
class RegulatoryDocument:
    doc_id: str
    source: str             # one of _VALID_SOURCES
    title: str
    body: str               # full text or summary
    date: str = ""          # ISO YYYY-MM-DD
    states: List[str] = field(default_factory=list)
    citation: str = ""      # e.g. "89 FR 38342", "OIG Civil Settlement"
    sector_tags: List[str] = field(default_factory=list)


@dataclass
class RegulatoryCorpus:
    """Holds the document set + provides simple iteration."""
    documents: List[RegulatoryDocument] = field(default_factory=list)

    def add(self, doc: RegulatoryDocument) -> None:
        self.documents.append(doc)

    def add_many(self, docs: Iterable[RegulatoryDocument]) -> None:
        for d in docs:
            self.add(d)

    def __len__(self) -> int:
        return len(self.documents)

    def filter(
        self,
        *,
        source: Optional[str] = None,
        state: Optional[str] = None,
        sector: Optional[str] = None,
    ) -> List[RegulatoryDocument]:
        out: List[RegulatoryDocument] = []
        for d in self.documents:
            if source and d.source != source:
                continue
            if state and (state.upper() not in
                          {s.upper() for s in d.states}):
                continue
            if sector and (sector.lower() not in
                           {s.lower() for s in d.sector_tags}):
                continue
            out.append(d)
        return out
