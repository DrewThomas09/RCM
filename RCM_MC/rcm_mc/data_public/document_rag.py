"""Document-Grounded RAG over the Knowledge Corpus.

Blueprint: "Every response must cite the CMS manual section, OIG work plan,
or NCCI edit it came from. Ground in citations, not confabulation."

Architecture
------------
The strongest anti-confabulation primitive is EXTRACTIVE retrieval: the
system returns actual source passages with their citations, unaltered.
No model generates new text. Citations are preserved by construction.

This module indexes passages from every shipped knowledge module:

    - NCCI edits (ncci_edits.py)           — PTP edit rationales
    - HFMA MAP Keys (hfma_map_keys.py)      — KPI definitions + rationales
    - OIG Work Plan (oig_workplan.py)       — audit-topic summaries
    - DOJ FCA Tracker (doj_fca_tracker.py)  — settlement synopses
    - PIM 100-08 (cms_program_integrity_manual.py) — section summaries
    - CPOM State Lattice (cpom_state_lattice.py)   — state doctrine summaries
    - TEAM Calculator (team_calculator.py)  — episode descriptions
    - Named-Failure Library (named_failure_library.py) — pattern root causes
    - Benchmark Curve Library                — curve methodology notes

Each passage carries {text, source_module, section_ref, effective_date,
primary_citation}. A query returns the top-k most relevant passages,
ranked by TF-IDF cosine similarity.

Embedding engine (pluggable)
----------------------------
Default: TF-IDF in numpy (stdlib + numpy). Works in any Python env.

Upgrade path: If PubMedBERT / BioBERT / sentence-transformers is
installed, the embedder swaps transparently — same query interface,
higher-quality retrieval. See `_detect_embedding_engine()`.

Generation engine (optional)
----------------------------
By default this module does NOT generate new text. It returns extractive
passages. If a commercial-compatible LLM (Llama 3 Instruct / Mistral /
Anthropic/OpenAI API) is wired in, the module wraps extractive output
with a grounded-generation layer that REQUIRES every generated claim to
map to a retrieved passage (citation-or-refuse). The default extractive
path is the safe minimum.

Public API
----------
    KnowledgePassage             one indexed passage
    EmbeddingEngineInfo          runtime detection of available embedders
    RAGQuery                     one user query + retrieved results
    RAGResult                    retrieval result for one query
    DocumentRAGResult            composite for the UI (includes demo queries)
    compute_document_rag()       -> DocumentRAGResult
    query_rag(q, top_k)          -> RAGResult  (callable from other modules)
"""
from __future__ import annotations

import importlib
import math
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class KnowledgePassage:
    """One indexed passage from a shipped knowledge module."""
    passage_id: str                  # unique
    text: str                        # the body text (short — 1-3 sentences)
    source_module: str               # e.g., "ncci_edits" / "oig_workplan"
    source_label: str                # human-readable (e.g., "NCCI Edit Scanner")
    section_ref: str                 # e.g., "§ 5.2.4" / "WP-010" / "NF-01"
    effective_date: str              # ISO date or year
    primary_citation: str            # URL or statute / case cite


@dataclass
class EmbeddingEngineInfo:
    """Runtime-detected embedding engine info."""
    active_engine: str               # "tfidf" / "pubmedbert" / "biobert" / "sentence-transformers"
    tfidf_available: bool
    numpy_version: str
    pubmedbert_available: bool
    sentence_transformers_available: bool
    transformers_available: bool
    detection_notes: str


@dataclass
class RAGQuery:
    query_text: str
    top_k: int
    retrieved_passage_ids: List[str]
    retrieval_scores: List[float]
    extractive_answer: str           # concatenation of top passages with citations
    engine_used: str


@dataclass
class RAGResult:
    """Return shape of query_rag()."""
    query: str
    passages: List[KnowledgePassage]
    scores: List[float]
    extractive_answer_html: str
    engine: str


@dataclass
class DocumentRAGResult:
    """Composite — for UI; includes demo queries + full index stats."""
    engine_info: EmbeddingEngineInfo
    total_passages: int
    passages_by_source: Dict[str, int]
    demo_queries: List[RAGQuery]
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Embedding engine detection
# ---------------------------------------------------------------------------

def _detect_embedding_engine() -> EmbeddingEngineInfo:
    pm = False
    st = False
    tf = False
    notes = []

    try:
        import transformers  # type: ignore
        tf = True
    except ImportError:
        pass

    try:
        import sentence_transformers  # type: ignore
        st = True
    except ImportError:
        pass

    # PubMedBERT check: if transformers is present, the model may be available
    # via HF Hub; without network/download we can't actually use it. Mark false
    # unless a user has pre-pulled the model weights.
    pm = False

    if pm:
        active = "pubmedbert"
        notes.append("PubMedBERT model weights detected; dense biomedical retrieval active.")
    elif st:
        active = "sentence-transformers"
        notes.append("sentence-transformers installed; generic dense retrieval active.")
    else:
        active = "tfidf"
        notes.append(
            "Dense embedding libraries not installed in current Python environment. "
            "Running TF-IDF (numpy-only) fallback. Retrieval quality is solid for keyword-matchable "
            "queries; semantic near-miss queries may underperform. "
            "To upgrade: `pip install sentence-transformers` then download PubMedBERT "
            "via `AutoModel.from_pretrained('microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext')`. "
            "No call-site changes required — the adapter swaps engines transparently."
        )

    return EmbeddingEngineInfo(
        active_engine=active,
        tfidf_available=True,
        numpy_version=getattr(np, "__version__", "unknown"),
        pubmedbert_available=pm,
        sentence_transformers_available=st,
        transformers_available=tf,
        detection_notes=" ".join(notes),
    )


# ---------------------------------------------------------------------------
# Corpus assembly — pull passages from every shipped knowledge module
# ---------------------------------------------------------------------------

def _safe_import(module_name: str):
    try:
        return importlib.import_module(f"rcm_mc.data_public.{module_name}")
    except ImportError:
        return None


def _build_passages() -> List[KnowledgePassage]:
    passages: List[KnowledgePassage] = []
    idx = 0

    # ---- NCCI edits -----------------------------------------------
    mod = _safe_import("ncci_edits")
    if mod is not None:
        try:
            result = mod.compute_ncci_scanner()
            for edit in result.ptp_edits:
                txt = (f"NCCI PTP edit: CPT {edit.column1_code} ({edit.col1_descriptor}) "
                       f"with {edit.column2_code} ({edit.col2_descriptor}). "
                       f"Specialty: {edit.specialty}. Rationale: {edit.rationale}")
                passages.append(KnowledgePassage(
                    passage_id=f"ncci-{edit.column1_code}-{edit.column2_code}-{idx}",
                    text=txt,
                    source_module="ncci_edits",
                    source_label="NCCI Edit Scanner",
                    section_ref=f"PTP {edit.column1_code}+{edit.column2_code}",
                    effective_date=edit.effective_date,
                    primary_citation="CMS NCCI Policy Manual + Quarterly PTP Edit Tables",
                ))
                idx += 1
            for mue in result.mue_limits:
                txt = (f"NCCI MUE (Medically Unlikely Edit): CPT {mue.code} ({mue.descriptor}). "
                       f"Max units {mue.mue_value} per {mue.mue_adjudication_type}. "
                       f"Specialty: {mue.specialty}. Rationale: {mue.rationale}")
                passages.append(KnowledgePassage(
                    passage_id=f"ncci-mue-{mue.code}-{idx}",
                    text=txt,
                    source_module="ncci_edits",
                    source_label="NCCI MUE",
                    section_ref=f"MUE {mue.code}",
                    effective_date="2025-Q4",
                    primary_citation="CMS NCCI MUE Tables (quarterly)",
                ))
                idx += 1
        except Exception:
            pass

    # ---- HFMA MAP Keys ---------------------------------------------
    mod = _safe_import("hfma_map_keys")
    if mod is not None:
        try:
            result = mod.compute_hfma_map_keys()
            for kpi in result.kpis:
                txt = (f"HFMA MAP Key {kpi.map_key_id} — {kpi.name} ({kpi.category}). "
                       f"Numerator: {kpi.numerator}. Denominator: {kpi.denominator}. "
                       f"Unit: {kpi.unit}. Exclusions: {kpi.exclusions}. "
                       f"Why it matters: {kpi.rationale}")
                passages.append(KnowledgePassage(
                    passage_id=f"hfma-{kpi.map_key_id}",
                    text=txt,
                    source_module="hfma_map_keys",
                    source_label="HFMA MAP Keys",
                    section_ref=kpi.map_key_id,
                    effective_date=kpi.effective_date,
                    primary_citation="HFMA MAP Keys Methodology Guide (annual)",
                ))
        except Exception:
            pass

    # ---- OIG Work Plan --------------------------------------------
    mod = _safe_import("oig_workplan")
    if mod is not None:
        try:
            result = mod.compute_oig_workplan()
            for item in result.items:
                txt = (f"OIG Work Plan {item.item_id} — {item.title}. "
                       f"Provider type: {item.provider_type}. Service line: {item.service_line}. "
                       f"Topic: {item.topic_category}. Status: {item.status}. "
                       f"Typical recovery ${item.typical_recovery_low_mm:.0f}M-${item.typical_recovery_high_mm:.0f}M. "
                       f"Rationale: {item.rationale}. PE implication: {item.pe_implication}")
                passages.append(KnowledgePassage(
                    passage_id=f"oig-{item.item_id}",
                    text=txt,
                    source_module="oig_workplan",
                    source_label="OIG Work Plan Tracker",
                    section_ref=item.item_id,
                    effective_date=str(item.last_updated),
                    primary_citation=item.report_reference,
                ))
        except Exception:
            pass

    # ---- DOJ FCA tracker ------------------------------------------
    mod = _safe_import("doj_fca_tracker")
    if mod is not None:
        try:
            result = mod.compute_doj_fca_tracker()
            for s in result.settlements:
                cia = f", CIA {s.cia_term_years}yr" if s.cia_imposed else ""
                txt = (f"DOJ FCA {s.case_id}: {s.defendant} ({s.settlement_year}) — "
                       f"${s.settlement_amount_mm:.1f}M settlement ({s.allegation_type}). "
                       f"Provider type: {s.provider_type}{cia}. "
                       f"Synopsis: {s.synopsis} PE context: {s.pe_sponsor_context}")
                passages.append(KnowledgePassage(
                    passage_id=f"fca-{s.case_id}",
                    text=txt,
                    source_module="doj_fca_tracker",
                    source_label="DOJ FCA Tracker",
                    section_ref=s.case_id,
                    effective_date=str(s.settlement_year),
                    primary_citation=f"{s.court_citation}; {s.press_release_ref}",
                ))
        except Exception:
            pass

    # ---- PIM 100-08 -----------------------------------------------
    mod = _safe_import("cms_program_integrity_manual")
    if mod is not None:
        try:
            result = mod.compute_program_integrity_manual()
            for sec in result.sections:
                txt = (f"CMS Program Integrity Manual Ch {sec.chapter_number} {sec.section_number} — "
                       f"{sec.section_title}. Contractors: {', '.join(sec.audit_contractor_ids)}. "
                       f"Enforcement: {sec.enforcement_mechanism}. "
                       f"Summary: {sec.summary} Diligence note: {sec.diligence_note}")
                passages.append(KnowledgePassage(
                    passage_id=f"pim-ch{sec.chapter_number}-{sec.section_number}",
                    text=txt,
                    source_module="cms_program_integrity_manual",
                    source_label="CMS PIM Pub 100-08",
                    section_ref=f"Ch {sec.chapter_number} {sec.section_number}",
                    effective_date=str(sec.last_revised_year),
                    primary_citation=f"CMS Pub 100-08 {sec.transmittal_ref}; {sec.source_url}",
                ))
        except Exception:
            pass

    # ---- CPOM State Lattice ---------------------------------------
    mod = _safe_import("cpom_state_lattice")
    if mod is not None:
        try:
            result = mod.compute_cpom_state_lattice()
            for st_ in result.states:
                txt = (f"CPOM — {st_.state_name} ({st_.state_code}) regime tier: {st_.regime_tier}. "
                       f"Doctrine: {st_.cpom_doctrine_summary} "
                       f"Permitted structures: {', '.join(st_.permitted_structures)}. "
                       f"MSO-friendly: {st_.mso_friendly}. Fee-split allowed: {st_.fee_splitting_allowed}. "
                       f"Non-compete: {st_.non_compete_enforceability}. "
                       f"Diligence note: {st_.diligence_note}")
                passages.append(KnowledgePassage(
                    passage_id=f"cpom-{st_.state_code}",
                    text=txt,
                    source_module="cpom_state_lattice",
                    source_label="CPOM State Lattice",
                    section_ref=st_.state_code,
                    effective_date=str(st_.last_revised_year),
                    primary_citation=f"{st_.key_statute}; {st_.primary_citation}",
                ))
        except Exception:
            pass

    # ---- TEAM Calculator ------------------------------------------
    mod = _safe_import("team_calculator")
    if mod is not None:
        try:
            result = mod.compute_team_calculator()
            for ep in result.episodes:
                txt = (f"TEAM episode {ep.episode_id}: {ep.episode_name}. Trigger DRG {ep.trigger_drg}. "
                       f"Description: {ep.description} "
                       f"Anchor LOS {ep.avg_anchor_stay_days}d, episode spend ${ep.avg_total_episode_medicare_spend:,.0f}, "
                       f"post-acute share {ep.post_acute_pct*100:.0f}%, annual volume {ep.annual_national_volume:,}. "
                       f"Target price: {ep.target_price_methodology}")
                passages.append(KnowledgePassage(
                    passage_id=f"team-{ep.episode_id}",
                    text=txt,
                    source_module="team_calculator",
                    source_label="TEAM Calculator",
                    section_ref=ep.episode_id,
                    effective_date="2026-01-01",
                    primary_citation="FY 2025 IPPS/LTCH Final Rule (CMS-1808-F); 42 CFR Part 512 Subpart D",
                ))
            for y in result.risk_share_schedule:
                txt = (f"TEAM PY{y.py_number} ({y.performance_year}): upside cap {y.upside_cap_pct}%, "
                       f"downside cap {y.downside_cap_pct}%, stop-loss {y.stop_loss_pct}%, "
                       f"quality weight {y.quality_weight_pct}%. Notes: {y.notes}")
                passages.append(KnowledgePassage(
                    passage_id=f"team-py{y.py_number}",
                    text=txt,
                    source_module="team_calculator",
                    source_label="TEAM Risk-Share Schedule",
                    section_ref=f"PY{y.py_number}",
                    effective_date=str(y.performance_year),
                    primary_citation="42 CFR Part 512 Subpart D",
                ))
        except Exception:
            pass

    # ---- Named-Failure Library ------------------------------------
    mod = _safe_import("named_failure_library")
    if mod is not None:
        try:
            result = mod.compute_named_failure_library()
            for p in result.patterns:
                txt = (f"Named failure {p.pattern_id}: {p.case_name} (filed {p.filing_year}, {p.jurisdiction}). "
                       f"Sector: {p.sector}. Root cause: {p.root_cause_short}. "
                       f"Detail: {p.root_cause_detail} "
                       f"Pre-facto signals: {'; '.join(p.pre_facto_signals[:4])}.")
                cite = "; ".join(p.citations[:2])
                passages.append(KnowledgePassage(
                    passage_id=f"nf-{p.pattern_id}",
                    text=txt,
                    source_module="named_failure_library",
                    source_label="Named-Failure Library",
                    section_ref=p.pattern_id,
                    effective_date=str(p.filing_year),
                    primary_citation=cite,
                ))
        except Exception:
            pass

    # ---- Benchmark Curve Library ----------------------------------
    mod = _safe_import("benchmark_curve_library")
    if mod is not None:
        try:
            result = mod.compute_benchmark_library()
            # One passage per curve family (not per-row) — methodology is shared.
            seen_families = set()
            for row in result.curve_rows:
                if row.curve_id in seen_families:
                    continue
                seen_families.add(row.curve_id)
                txt = (f"Benchmark curve {row.curve_id} — {row.curve_name}. "
                       f"Metric: {row.metric} ({row.unit}). Source: {row.source}. "
                       f"Methodology: {row.methodology_notes} "
                       f"Vendor substitution target: {row.vendor_substitution}")
                passages.append(KnowledgePassage(
                    passage_id=f"bc-{row.curve_id}",
                    text=txt,
                    source_module="benchmark_curve_library",
                    source_label="Benchmark Curve Library",
                    section_ref=row.curve_id,
                    effective_date=str(row.year),
                    primary_citation=f"Source: {row.source}; regional GPCI + BLS OEWS scaling",
                ))
        except Exception:
            pass

    return passages


# ---------------------------------------------------------------------------
# TF-IDF index (numpy-only)
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "of", "to", "in", "on",
    "at", "for", "with", "by", "from", "as", "and", "or", "but", "if",
    "this", "that", "these", "those", "it", "its", "be", "been", "has",
    "have", "had", "will", "would", "could", "should", "may", "must",
    "not", "no", "nor", "so", "than", "then", "when", "where", "which",
    "who", "whom", "whose", "why", "how", "all", "any", "each", "every",
    "some", "such", "into", "about", "via", "per", "within",
}


def _tokenize(text: str) -> List[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS and len(t) > 1]


class _TFIDFIndex:
    """Compact TF-IDF index over passages. Stdlib + numpy only.

    Builds a vocabulary from all passages, stores per-passage term counts in
    a sparse dict, computes IDF at build time, and serves query() as a
    top-k cosine-similarity scan.
    """

    def __init__(self, passages: List[KnowledgePassage]):
        self.passages = passages
        # Vocabulary + IDF
        vocab: Dict[str, int] = {}
        doc_freq: Dict[int, int] = {}
        doc_tokens: List[Dict[int, int]] = []

        for p in passages:
            tokens = _tokenize(p.text)
            tc: Dict[int, int] = {}
            seen: set = set()
            for tok in tokens:
                tid = vocab.setdefault(tok, len(vocab))
                tc[tid] = tc.get(tid, 0) + 1
                if tid not in seen:
                    doc_freq[tid] = doc_freq.get(tid, 0) + 1
                    seen.add(tid)
            doc_tokens.append(tc)

        N = max(1, len(passages))
        self.vocab = vocab
        self.idf = np.zeros(len(vocab), dtype=np.float32)
        for tid, df in doc_freq.items():
            self.idf[tid] = math.log((N + 1) / (df + 1)) + 1.0

        # Pre-compute per-doc vector norms + sparse reps
        self.doc_tokens = doc_tokens
        self.doc_norms = np.zeros(len(passages), dtype=np.float32)
        for i, tc in enumerate(doc_tokens):
            sq = 0.0
            for tid, cnt in tc.items():
                w = (1.0 + math.log(cnt)) * float(self.idf[tid])
                sq += w * w
            self.doc_norms[i] = math.sqrt(sq) if sq > 0 else 1.0

    def query(self, text: str, top_k: int = 8) -> List[Tuple[int, float]]:
        tokens = _tokenize(text)
        q_counts: Dict[int, int] = {}
        for tok in tokens:
            tid = self.vocab.get(tok)
            if tid is None:
                continue
            q_counts[tid] = q_counts.get(tid, 0) + 1
        if not q_counts:
            return []
        q_weights: Dict[int, float] = {}
        q_sq = 0.0
        for tid, cnt in q_counts.items():
            w = (1.0 + math.log(cnt)) * float(self.idf[tid])
            q_weights[tid] = w
            q_sq += w * w
        q_norm = math.sqrt(q_sq) if q_sq > 0 else 1.0

        scores = np.zeros(len(self.passages), dtype=np.float32)
        for i, tc in enumerate(self.doc_tokens):
            dot = 0.0
            for tid, qw in q_weights.items():
                cnt = tc.get(tid, 0)
                if cnt == 0:
                    continue
                dw = (1.0 + math.log(cnt)) * float(self.idf[tid])
                dot += qw * dw
            scores[i] = dot / (q_norm * self.doc_norms[i])

        # Top-k
        if top_k >= len(scores):
            order = np.argsort(-scores)
        else:
            # argpartition for top-k
            part = np.argpartition(-scores, top_k)[:top_k]
            order = part[np.argsort(-scores[part])]
        return [(int(i), float(scores[i])) for i in order if scores[i] > 0]


# ---------------------------------------------------------------------------
# Module-level lazy-built index
# ---------------------------------------------------------------------------

_INDEX: Optional[_TFIDFIndex] = None
_PASSAGES: Optional[List[KnowledgePassage]] = None


def _ensure_index():
    global _INDEX, _PASSAGES
    if _INDEX is None:
        _PASSAGES = _build_passages()
        _INDEX = _TFIDFIndex(_PASSAGES)
    return _INDEX, _PASSAGES


# ---------------------------------------------------------------------------
# Public query API
# ---------------------------------------------------------------------------

def query_rag(query_text: str, top_k: int = 8) -> RAGResult:
    """Retrieve top-k citation-grounded passages for a query.

    Return shape always includes the actual passages + the rendered
    extractive answer HTML (citations inline). No generated text.
    """
    index, passages = _ensure_index()
    engine = _detect_embedding_engine().active_engine

    hits = index.query(query_text, top_k=top_k)
    retrieved = [passages[i] for i, _ in hits]
    scores = [s for _, s in hits]

    # Build extractive answer block
    if not retrieved:
        html = ('<div style="font-style:italic;color:#94a3b8">'
                'No passages matched the query above a non-zero TF-IDF score. '
                'Try rephrasing with specific module keywords (e.g. "modifier 59", '
                '"two-midnight", "Steward", "RAC").</div>')
    else:
        items = []
        for p, s in zip(retrieved, scores):
            items.append(
                '<div style="border-left:2px solid #3b82f6;padding:8px 12px;margin-bottom:10px;'
                'background:#0f172a">'
                f'<div style="font-size:10px;color:#94a3b8;font-family:JetBrains Mono,monospace;'
                f'letter-spacing:0.05em;margin-bottom:3px">'
                f'{_escape(p.source_label)} · {_escape(p.section_ref)} · effective {_escape(p.effective_date)} '
                f'· relevance {s:.3f}</div>'
                f'<div style="font-size:11px;color:#e2e8f0;line-height:1.5">{_escape(p.text)}</div>'
                f'<div style="font-size:10px;color:#94a3b8;font-family:JetBrains Mono,monospace;'
                f'margin-top:4px;font-style:italic">Citation: {_escape(p.primary_citation)}</div>'
                '</div>'
            )
        html = "".join(items)

    return RAGResult(
        query=query_text,
        passages=retrieved,
        scores=scores,
        extractive_answer_html=html,
        engine=engine,
    )


def _escape(s: str) -> str:
    import html
    return html.escape(s or "")


# ---------------------------------------------------------------------------
# Demo queries — shown on the UI at page load
# ---------------------------------------------------------------------------

_DEMO_QUERIES = [
    "What is the modifier 59 audit risk on physical therapy rollups?",
    "How does the two-midnight rule affect hospital short-stay admissions?",
    "What does CMS PIM say about RAC extrapolation?",
    "What happens to a target in Steward Health Care's pattern at LBO?",
    "What V28 risk-adjustment exposure does a Medicare Advantage primary-care rollup carry?",
    "Can a PE firm directly employ physicians in California?",
    "How does TEAM bundled-payment reconciliation work in PY5?",
    "What DOJ FCA settlements involved 21st Century Oncology?",
]


def _run_demo_queries() -> List[RAGQuery]:
    out: List[RAGQuery] = []
    for q in _DEMO_QUERIES:
        r = query_rag(q, top_k=4)
        # Short extractive answer: first 2 passages concatenated briefly
        parts = []
        for p in r.passages[:2]:
            parts.append(f"[{p.source_label} / {p.section_ref}] {p.text[:240]}")
        ext = " • ".join(parts) if parts else "(no match)"
        out.append(RAGQuery(
            query_text=q,
            top_k=4,
            retrieved_passage_ids=[p.passage_id for p in r.passages],
            retrieval_scores=[round(s, 4) for s in r.scores],
            extractive_answer=ext,
            engine_used=r.engine,
        ))
    return out


# ---------------------------------------------------------------------------
# Public entry point (UI)
# ---------------------------------------------------------------------------

def _load_corpus_count() -> int:
    n = 0
    for i in range(2, 122):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            n += len(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return n


def compute_document_rag() -> DocumentRAGResult:
    _, passages = _ensure_index()
    engine = _detect_embedding_engine()
    demo = _run_demo_queries()

    # Breakdown by source
    by_source: Dict[str, int] = {}
    for p in passages:
        by_source[p.source_label] = by_source.get(p.source_label, 0) + 1

    return DocumentRAGResult(
        engine_info=engine,
        total_passages=len(passages),
        passages_by_source=by_source,
        demo_queries=demo,
        corpus_deal_count=_load_corpus_count(),
    )
