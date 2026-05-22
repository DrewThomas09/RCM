"""Read-only RAG document sources for the PEdesk Guide.

Indexes ONLY safe, internal, in-repo context: every PageContext, the
metric and data-source registries, the read-only Guide policy, and a
curated allow-list of methodology/reference docs. Never indexes secrets,
credentials, audit logs, sessions, runtime data, or user uploads.
"""
from __future__ import annotations

import pathlib
import re
from typing import Iterable, List

from ..context.data_source_registry import DATA_SOURCE_REGISTRY
from ..context.guide_prompt_policy import GUIDE_PROMPT_POLICY
from ..context.metric_registry import METRIC_REGISTRY
from ..context.page_context_registry import PAGE_CONTEXT_REGISTRY
from .types import RagDocument

_NEEDS = "Needs source documentation."

# Repo root (…/RCM_MC), where docs/ and the context README live.
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]

# Curated doc allow-list (keyword match over docs/). Only .md, only these
# topics; anything mentioning secrets/credentials/sessions is excluded.
_DOC_KEYWORDS = (
    "methodology", "metric", "glossary", "benchmark", "provenance",
    "data_public", "data_acquisition", "hcris", "payer", "bridge",
    "provider", "physician", "attrition", "system_flow", "diligence",
    "portfolio", "screening", "library_corpus", "research_tooling",
)
_DOC_DENY = ("secret", "credential", "session", "password", "token", "auth_")
_MAX_DOC_FILES = 40


def _join(label: str, val) -> str:
    """A 'Label: value' line; skips empties and the needs-doc sentinel."""
    if val is None:
        return ""
    if isinstance(val, (list, tuple)):
        items = [str(x).strip() for x in val
                 if x and str(x).strip() and str(x).strip() != _NEEDS]
        if not items:
            return ""
        return f"{label}: " + "; ".join(items)
    s = str(val).strip()
    if not s or s == _NEEDS:
        return ""
    return f"{label}: {s}"


def _page_documents() -> Iterable[RagDocument]:
    for route, ctx in PAGE_CONTEXT_REGISTRY.items():
        parts = [
            f"PEdesk page: {ctx.title} ({route})",
            _join("What it does", ctx.short_description),
            _join("Primary purpose", ctx.primary_purpose),
            _join("Why it matters", ctx.why_it_matters),
            _join("Inputs", ctx.inputs),
            _join("Outputs", ctx.outputs),
            _join("Interpretation guidance", ctx.interpretation_guidance),
            _join("Limitations", ctx.limitations),
            _join("Related routes", ctx.related_routes),
        ]
        text = "\n".join(p for p in parts if p)
        yield RagDocument(
            source_id=f"page:{route}",
            source_type="page_context",
            title=ctx.title,
            text=text,
            route=route,
            source_confidence=ctx.source_confidence.value,
            data_confidence=ctx.data_confidence.value,
        )


def _metric_documents() -> Iterable[RagDocument]:
    for mid, m in METRIC_REGISTRY.items():
        parts = [
            f"Metric: {m.label} ({mid})",
            _join("Definition", m.definition),
            _join("Formula", m.formula),
            _join("Formula confidence", m.formula_confidence.value),
            _join("Why it matters", m.why_it_matters),
            _join("Diligence interpretation", m.diligence_interpretation),
            _join("Common misread", m.common_misread),
            _join("Caveats", m.caveats),
            _join("Related routes", m.related_routes),
        ]
        text = "\n".join(p for p in parts if p)
        yield RagDocument(
            source_id=f"metric:{mid}",
            source_type="metric",
            title=m.label,
            text=text,
            metric_id=mid,
        )


def _data_source_documents() -> Iterable[RagDocument]:
    for sid, s in DATA_SOURCE_REGISTRY.items():
        parts = [
            f"Data source: {s.label} ({sid})",
            _join("Description", s.description),
            _join("Type", s.source_type.value),
            _join("Update cadence", s.update_cadence),
            _join("Freshness lag", s.freshness_lag),
            _join("Provenance notes", s.provenance_notes),
            _join("Strengths", s.strengths),
            _join("Limitations", s.limitations),
            _join("Used for", s.used_for),
            _join("Related routes", s.related_routes),
            _join("Related metrics", s.related_metrics),
        ]
        text = "\n".join(p for p in parts if p)
        yield RagDocument(
            source_id=f"source:{sid}",
            source_type="data_source",
            title=s.label,
            text=text,
            data_source_id=sid,
        )


def _policy_document() -> RagDocument:
    pol = GUIDE_PROMPT_POLICY
    text = "\n".join([
        "PEdesk Guide read-only policy.",
        pol.identity,
        "May: " + "; ".join(pol.allowed_behavior) + ".",
        "May not: " + "; ".join(pol.disallowed_behavior) + ".",
        "When unsure: " + pol.default_uncertainty_message,
    ])
    return RagDocument(
        source_id="policy:read-only",
        source_type="guide_policy",
        title="PEdesk Guide read-only policy",
        text=text,
    )


def _curated_doc_paths() -> List[pathlib.Path]:
    docs_dir = _REPO_ROOT / "docs"
    found: List[pathlib.Path] = []
    if docs_dir.is_dir():
        for p in sorted(docs_dir.rglob("*.md")):
            name = p.name.lower()
            if any(d in name for d in _DOC_DENY):
                continue
            if any(k in name for k in _DOC_KEYWORDS):
                found.append(p)
    # Always include the Guide's own README (setup + behavior docs).
    readme = _REPO_ROOT / "rcm_mc" / "assistant" / "context" / "README.md"
    if readme.is_file():
        found.append(readme)
    return found[:_MAX_DOC_FILES]


def _doc_documents() -> Iterable[RagDocument]:
    for p in _curated_doc_paths():
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if not text.strip():
            continue
        rel = str(p.relative_to(_REPO_ROOT))
        title = _doc_title(text) or p.stem.replace("_", " ").title()
        yield RagDocument(
            source_id=f"doc:{rel}",
            source_type="doc",
            title=title,
            text=text,
            file_path=rel,
        )


def _doc_title(text: str) -> str:
    for line in text.splitlines():
        m = re.match(r"^#\s+(.+)", line.strip())
        if m:
            return m.group(1).strip()
    return ""


def iter_guide_documents() -> List[RagDocument]:
    """All read-only RAG source documents (registries + policy + docs)."""
    docs: List[RagDocument] = []
    docs.extend(_page_documents())
    docs.extend(_metric_documents())
    docs.extend(_data_source_documents())
    docs.append(_policy_document())
    docs.extend(_doc_documents())
    return docs
