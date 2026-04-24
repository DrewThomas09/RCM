"""Document-Grounded RAG — /rag."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _engine_panel(e) -> str:
    panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]
    pos = P["positive"]; warn = P["warning"]
    rows = [
        ("Active engine",                 e.active_engine.upper(), acc),
        ("TF-IDF (numpy)",                "AVAILABLE" if e.tfidf_available else "MISSING",
         pos if e.tfidf_available else warn),
        ("sentence-transformers",         "INSTALLED" if e.sentence_transformers_available else "not installed",
         pos if e.sentence_transformers_available else text_dim),
        ("transformers (HuggingFace)",    "INSTALLED" if e.transformers_available else "not installed",
         pos if e.transformers_available else text_dim),
        ("PubMedBERT model weights",      "AVAILABLE" if e.pubmedbert_available else "not downloaded",
         pos if e.pubmedbert_available else text_dim),
        ("numpy version",                 e.numpy_version, text_dim),
    ]
    trs = ""
    for k, v, c in rows:
        trs += (f'<tr><td style="padding:6px 12px;border-bottom:1px solid {border};'
                f'font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">'
                f'{_html.escape(k)}</td>'
                f'<td style="padding:6px 12px;border-bottom:1px solid {border};'
                f'font-family:JetBrains Mono,monospace;font-variant-numeric:tabular-nums;font-size:11px;'
                f'color:{c};font-weight:700">{_html.escape(str(v))}</td></tr>')
    notes = (f'<div style="margin-top:12px;padding:10px 12px;background:{panel_alt};border:1px solid {border};'
             f'font-size:10px;color:{text_dim};font-family:JetBrains Mono,monospace;line-height:1.5">'
             f'<strong style="color:{text}">Engine detection:</strong> {_html.escape(e.detection_notes)}</div>')
    return f'<table style="width:100%;border-collapse:collapse;margin-top:12px">{trs}</table>{notes}'


def _sources_panel(by_source: dict) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Source Module", "left"), ("Indexed Passages", "right"), ("Share", "right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    total = sum(by_source.values())
    trs = []
    items = sorted(by_source.items(), key=lambda x: -x[1])
    for i, (src, n) in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        share = (n / total * 100) if total else 0
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(src)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">{n}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{share:.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _query_form(current_query: str = "") -> str:
    panel = P["panel"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]
    input_style = (f"background:{P['bg']};border:1px solid {border};color:{text};"
                   f"font-family:'Inter',sans-serif;font-size:12px;padding:10px 12px;"
                   f"width:100%;box-sizing:border-box")
    return f"""
<form method="get" action="/rag" style="background:{panel};border:1px solid {border};padding:14px 16px;margin-bottom:16px">
  <label style="display:block;font-size:11px;font-weight:700;color:{text};letter-spacing:0.08em;text-transform:uppercase;margin-bottom:8px">
    Query the knowledge corpus — every answer cites source + section + effective date
  </label>
  <div style="display:grid;grid-template-columns:1fr 120px 160px;gap:10px">
    <input type="text" name="q" placeholder="e.g., 'modifier 59 audit risk', 'Steward MPT pattern', 'Two-Midnight Rule', 'V28 MA-risk exposure'" value="{_html.escape(current_query, quote=True)}" style="{input_style}">
    <input type="number" name="k" value="8" min="1" max="20" placeholder="top k" style="{input_style};text-align:center">
    <button type="submit" style="background:{acc};color:white;border:none;padding:10px 18px;font-family:JetBrains Mono,monospace;font-size:11px;letter-spacing:0.08em;text-transform:uppercase;cursor:pointer;font-weight:700">▶ Retrieve</button>
  </div>
  <div style="margin-top:6px;font-size:10px;color:{text_dim};font-family:JetBrains Mono,monospace">Extractive retrieval — no generation. Every retrieved passage is verbatim from a shipped knowledge module.</div>
</form>
"""


def _live_query_result(params) -> str:
    """If the user submitted a query via ?q=..., render the result inline."""
    from rcm_mc.data_public.document_rag import query_rag
    q = (params.get("q") or "").strip()
    if not q:
        return ""
    try:
        k = int(params.get("k", 8))
    except (TypeError, ValueError):
        k = 8
    k = max(1, min(20, k))
    result = query_rag(q, top_k=k)
    panel = P["panel"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]
    hits = len(result.passages)
    avg_score = (sum(result.scores) / hits) if hits else 0
    head = (f'<div style="padding:10px 14px;background:{P["panel_alt"]};border:1px solid {border};'
            f'margin-bottom:10px;font-size:11px;color:{text_dim};font-family:JetBrains Mono,monospace">'
            f'<strong style="color:{text}">Query:</strong> "{_html.escape(q)}" · '
            f'Engine: <strong style="color:{acc}">{_html.escape(result.engine)}</strong> · '
            f'Retrieved <strong style="color:{acc}">{hits}</strong> passage(s) · '
            f'Avg relevance <strong style="color:{acc}">{avg_score:.3f}</strong>'
            f'</div>')
    return (f'<div style="background:{panel};border:1px solid {border};padding:14px 18px;margin-bottom:16px">'
            f'<div style="font-size:11px;font-weight:700;color:{text};letter-spacing:0.08em;text-transform:uppercase;margin-bottom:6px">Live Query Result (Extractive + Cited)</div>'
            f'{head}{result.extractive_answer_html}</div>')


def _demo_queries(demos) -> str:
    panel = P["panel"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]
    items = []
    for q in demos:
        top_score = q.retrieval_scores[0] if q.retrieval_scores else 0
        # Link to /rag?q=...
        import urllib.parse
        qs = urllib.parse.urlencode({"q": q.query_text, "k": 4})
        items.append(
            f'<div style="padding:10px 12px;border-top:1px solid {border};font-size:11px">'
            f'<div style="display:grid;grid-template-columns:1fr 80px 120px;gap:12px;align-items:baseline">'
            f'<div><a href="/rag?{qs}" style="color:{acc};text-decoration:none">{_html.escape(q.query_text)}</a></div>'
            f'<div style="text-align:right;font-family:JetBrains Mono,monospace;color:{acc};font-weight:700">{top_score:.3f}</div>'
            f'<div style="text-align:right;font-family:JetBrains Mono,monospace;color:{text_dim};font-size:10px">{len(q.retrieved_passage_ids)} cited</div>'
            f'</div>'
            f'<div style="margin-top:4px;color:{text_dim};font-size:10px;font-family:JetBrains Mono,monospace;line-height:1.5">'
            f'{_html.escape(q.extractive_answer[:400])}...</div>'
            f'</div>'
        )
    return (f'<div style="background:{panel};border:1px solid {border};padding:14px 18px;margin-bottom:16px">'
            f'<div style="font-size:11px;font-weight:700;color:{text};letter-spacing:0.08em;text-transform:uppercase;margin-bottom:6px">'
            f'Demo queries — click any row to run it live</div>'
            f'{"".join(items)}</div>')


def render_document_rag(params: dict = None) -> str:
    params = params or {}
    from rcm_mc.data_public.document_rag import compute_document_rag
    r = compute_document_rag()

    panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Indexed Passages", f"{r.total_passages:,}", "", "") +
        ck_kpi_block("Source Modules", str(len(r.passages_by_source)), "", "") +
        ck_kpi_block("Active Engine", r.engine_info.active_engine.upper(), "", "") +
        ck_kpi_block("Demo Queries", str(len(r.demo_queries)), "", "") +
        ck_kpi_block("Avg Demo Score", f"{sum(q.retrieval_scores[0] if q.retrieval_scores else 0 for q in r.demo_queries) / max(1, len(r.demo_queries)):.3f}", "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    q_value = (params.get("q") or "").strip()
    form = _query_form(q_value)
    live = _live_query_result(params)
    demos = _demo_queries(r.demo_queries)
    engine_panel = _engine_panel(r.engine_info)
    sources_panel = _sources_panel(r.passages_by_source)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Document-Grounded RAG — Citation-First Retrieval</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">{r.total_passages:,} passages indexed across {len(r.passages_by_source)} shipped knowledge modules · extractive retrieval · every answer cites its source module, section ref, effective date, and primary citation · no generation = no confabulation</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  {form}
  {live}
  {demos}
  <div style="{cell}"><div style="{h3}">Indexed Source Modules — All Shipped Knowledge Passages</div>{sources_panel}</div>
  <div style="{cell}"><div style="{h3}">Embedding Engine — Runtime Detection + Upgrade Path</div>{engine_panel}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">RAG Thesis — Cite, Don't Confabulate:</strong>
    The strongest anti-confabulation primitive is EXTRACTIVE retrieval. This module
    returns actual source passages from shipped knowledge modules — text that already
    exists, verbatim, with its citations preserved. No LLM generates new text.
    A user asking about "Steward MPT pattern" gets back the Named-Failure Library entry
    NF-01 with its primary citation. A user asking about "two-midnight rule" gets back
    CMS PIM Pub 100-08 Ch 5 § 5.2.4 with its CMS transmittal reference. Grounding
    is enforced at the architecture level, not as an instruction.
    <br><br>
    <strong style="color:{text}">Engine pluggability:</strong>
    Default engine is TF-IDF in numpy — works in any Python env, no downloads, no
    external deps. Quality is solid for keyword-matchable queries (precision + recall
    strong when the query shares terminology with source passages). Semantic near-miss
    queries (e.g., "indirect corporate employment of doctors") may underperform.
    <br><br>
    When <code style="color:{acc};font-family:JetBrains Mono,monospace">sentence-transformers</code>
    is installed, the adapter swaps to dense retrieval transparently. When PubMedBERT
    weights are downloaded (<code style="color:{acc};font-family:JetBrains Mono,monospace">microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext</code>),
    biomedical-domain retrieval activates. Same query interface, higher-quality results.
    <br><br>
    <strong style="color:{text}">Generation layer (optional, not default):</strong>
    Wiring Llama 3 Instruct / Mistral / API-based generation is straightforward on top
    of <code style="color:{acc};font-family:JetBrains Mono,monospace">query_rag(q, top_k)</code>
    — the contract is: given retrieved passages + query, generate a narrative answer
    that cites each claim back to a passage_id. The module exposes passage_id
    deterministically so any generated claim is traceable. If a generation layer is
    wrapped here later, the citation-preservation rule MUST be enforced at
    response-construction time (refuse to emit text that doesn't map to a retrieved
    passage).
    <br><br>
    <strong style="color:{text}">Integration points:</strong>
    Every module shipped to <code style="color:{acc};font-family:JetBrains Mono,monospace">data_public/</code>
    that carries citations is automatically a RAG-indexable source. Future modules
    inherit this capability by exposing structured fields (item_id + section_ref +
    effective_date + primary_citation). Use
    <code style="color:{acc};font-family:JetBrains Mono,monospace">from rcm_mc.data_public.document_rag import query_rag</code>
    to retrieve within other modules — IC Brief and Adversarial Engine will benefit
    from citation-grounded rationale lookups in the next iteration.
  </div>
</div>"""

    return chartis_shell(body, "Document-Grounded RAG", active_nav="/rag")
