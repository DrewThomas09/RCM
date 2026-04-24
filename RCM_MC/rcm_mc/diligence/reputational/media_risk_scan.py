"""Media-risk keyword scanner.

Regex-based scan over caller-supplied text corpora (ProPublica /
STAT / NYT / Kaiser Health News / Fierce Healthcare / Modern
Healthcare / PESP archives) for target-name mentions + risk
keywords.

The scanner does NOT fetch — callers pass already-retrieved text.
This keeps the module stateless, testable, and free of network
dependencies.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional


# Risk-keyword lexicon — healthcare / PE / regulatory concerns.
RISK_KEYWORDS = [
    r"\bbankruptcy\b", r"\bChapter\s*11\b", r"\bChapter\s*7\b",
    r"\binvestigat\w+\b", r"\bsubpoena\w*\b", r"\bfraud\w*\b",
    r"\bkickback\w*\b", r"\bStark\b", r"\bwhistleblow\w*\b",
    r"\blawsuit\w*\b", r"\bclass[- ]action\b",
    r"\bconsent\s+order\b", r"\bsettle\w+\s+with\s+DOJ\b",
    r"\bNLRB\b", r"\bstrik\w+\b", r"\bunion\b",
    r"\boverbilling\b", r"\bupcoding\b",
    r"\bhospital\s+closure\b", r"\bclosing\s+hospital\b",
    r"\bCPOM\b", r"\bcorporate\s+practice\s+of\s+medicine\b",
    r"\bFTC\s+complaint\b",
]


@dataclass
class MediaRiskFinding:
    source: str
    hit_count: int
    keyword_counts: Dict[str, int]
    excerpts: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


def scan_media_mentions(
    target_name: str,
    articles: Iterable[Dict[str, Any]],
    *,
    extra_keywords: Optional[List[str]] = None,
    max_excerpts_per_source: int = 3,
) -> List[MediaRiskFinding]:
    """Scan each article for target-name + risk-keyword pairs.

    Each article dict: {source, text}. Returns one
    :class:`MediaRiskFinding` per source whose text mentions the
    target AND at least one risk keyword."""
    target_pat = re.compile(
        re.escape(target_name), re.IGNORECASE,
    )
    all_keywords = list(RISK_KEYWORDS) + list(extra_keywords or [])
    compiled = [
        (pat, re.compile(pat, re.IGNORECASE))
        for pat in all_keywords
    ]
    by_source: Dict[str, MediaRiskFinding] = {}
    for art in articles:
        src = str(art.get("source", "unknown"))
        text = str(art.get("text", "") or "")
        if not target_pat.search(text):
            continue
        # Per-keyword counts + sample excerpts.
        counts: Dict[str, int] = {}
        excerpts: List[str] = []
        for pat_raw, pat in compiled:
            matches = list(pat.finditer(text))
            if not matches:
                continue
            counts[pat_raw] = len(matches)
            for m in matches[:max_excerpts_per_source]:
                start = max(0, m.start() - 40)
                end = min(len(text), m.end() + 40)
                excerpts.append(
                    text[start:end].replace("\n", " ").strip()
                )
        if not counts:
            continue
        if src not in by_source:
            by_source[src] = MediaRiskFinding(
                source=src, hit_count=0, keyword_counts={},
                excerpts=[],
            )
        finding = by_source[src]
        finding.hit_count += sum(counts.values())
        for k, v in counts.items():
            finding.keyword_counts[k] = finding.keyword_counts.get(k, 0) + v
        finding.excerpts.extend(
            excerpts[:max_excerpts_per_source - len(finding.excerpts)]
        )
    return list(by_source.values())
