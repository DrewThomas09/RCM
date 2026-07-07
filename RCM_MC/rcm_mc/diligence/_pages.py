"""HTTP page renderers for the four RCM Diligence tabs.

Phase 14 of the UI v2 editorial rework wires every tab to live
backends. Each tab accepts a ``?dataset=<fixture_name>`` query param;
when set, the page runs the real pipeline (ingest → KPI → cohort →
waterfall → advisory) and renders the results under the editorial
shell. With no param, each tab renders a "pick a fixture" empty state
plus a selector so the analyst can drive without leaving the page.

Available datasets (shipped as kpi_truth fixtures under
``tests/fixtures/kpi_truth/``):

- hospital_01_clean_acute
- hospital_02_denial_heavy
- hospital_03_censoring
- hospital_04_mixed_payer
- hospital_05_dental_dso
- hospital_06_waterfall_truth
- hospital_07_waterfall_concordant
- hospital_08_waterfall_critical

Auth-aware file uploads are deferred — this wiring uses the existing
kpi_truth fixtures as the demo corpus, so the tabs are immediately
usable without a partner touching the filesystem.

Glossary note: CCD always means Canonical Claims Dataset (the
versioned claim table produced by the Phase 1 ingester) — never the
clinical-document CCD.
"""
from __future__ import annotations

import html
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..ui._chartis_kit import (
    chartis_shell,
    ck_affirm_empty,
    ck_data_cell,
    ck_data_table,
    ck_editorial_head,
    ck_empty_state,
    ck_fmt_number,
    ck_illustrative_note,
    ck_kpi_block,
    ck_next_section,
    ck_panel,
    ck_provenance_tooltip,
    ck_section_header,
    ck_severity_panel,
    ck_signal_badge,
)


FIXTURE_ROOT = (
    Path(__file__).resolve().parent.parent.parent
    / "tests" / "fixtures" / "kpi_truth"
)

# Known fixtures + short labels for the selector. Expanding this list
# costs nothing; the page renderers iterate it.
AVAILABLE_FIXTURES: List[Tuple[str, str]] = [
    ("hospital_01_clean_acute",     "Hospital 01 — Clean acute baseline"),
    ("hospital_02_denial_heavy",    "Hospital 02 — Denial-heavy outpatient"),
    ("hospital_03_censoring",       "Hospital 03 — Cohort censoring (young + mature)"),
    ("hospital_04_mixed_payer",     "Hospital 04 — 5/5/5/5 mixed payer"),
    ("hospital_05_dental_dso",      "Hospital 05 — Dental DSO proxy (OOD test)"),
    ("hospital_06_waterfall_truth", "Hospital 06 — Waterfall hand-computed truth"),
    ("hospital_07_waterfall_concordant", "Hospital 07 — QoR concordant (IMMATERIAL)"),
    ("hospital_08_waterfall_critical",   "Hospital 08 — QoR critical (CRITICAL ~7%)"),
]


# ── Shared page-scoped CSS ──────────────────────────────────────────
#
# Raw CSS (no <style> wrapper) — every page routes it through
# chartis_shell's ``extra_css`` kwarg so it lands once in <head>.
# The benchmarks route, which delegates its shell to another module,
# wraps it in a <style> tag before splicing (see
# ``render_benchmarks_page``). Kit CSS custom properties with
# canonical fallbacks only — no ad-hoc hex.

_ERROR_CSS = """
  .ck-dil-error-row { font-family: var(--sc-sans, Inter, sans-serif);
    font-size: 13px; line-height: 1.55; color: var(--sc-text, #1a2332); }
  .ck-dil-error-detail { margin-top: 8px; }
  .ck-dil-error-detail summary { cursor: pointer;
    font-family: var(--sc-mono, monospace); font-size: 10.5px;
    letter-spacing: .08em; text-transform: uppercase;
    color: var(--sc-text-dim, #465366); }
  .ck-dil-error-detail summary:focus-visible {
    outline: 2px solid var(--sc-teal, #155752); outline-offset: 2px; }
  .ck-dil-error-detail code { display: block; margin-top: 6px;
    font-family: var(--sc-mono, monospace); font-size: 11.5px;
    color: var(--sc-negative, #b5321e); word-break: break-word; }
"""

_DILIGENCE_CSS = _ERROR_CSS + """
  .ck-diligence-fixture { display: flex; align-items: center; gap: 12px;
    padding: 12px 16px; margin: 0 0 22px;
    background: #fff; border: 1px solid var(--sc-rule, #d6cfc0);
    border-radius: 2px; box-shadow: var(--sc-shadow-1);
    flex-wrap: wrap; }
  .ck-diligence-fixture-label { font-family: var(--sc-mono, monospace);
    font-size: 10.5px; font-weight: 700; letter-spacing: 0.1em;
    text-transform: uppercase; color: var(--sc-text-dim, #465366); }
  .ck-diligence-fixture-select { padding: 7px 12px; min-width: 320px;
    border: 1px solid var(--sc-rule, #d6cfc0); background: #fff;
    color: var(--sc-text, #1a2332);
    font-family: var(--sc-sans, Inter, sans-serif); font-size: 13px;
    border-radius: 2px; }
  .ck-diligence-fixture-select:focus-visible {
    outline: 2px solid var(--sc-teal, #155752); outline-offset: 2px;
    border-color: var(--sc-teal, #155752); }
  .ck-diligence-fixture-go { padding: 7px 16px;
    background: var(--sc-navy, #0b2341); color: #fff; border: 0;
    font-family: var(--sc-sans, Inter, sans-serif); font-size: 11.5px;
    font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;
    cursor: pointer; border-radius: 2px; }
  .ck-diligence-fixture-go:hover { background: var(--sc-teal, #155752); }
  .ck-diligence-fixture-go:focus-visible {
    outline: 2px solid var(--sc-teal, #155752); outline-offset: 2px; }
  .ck-dil-info { padding: 14px 18px; margin: 0 0 18px;
    background: #fff; border: 1px solid var(--sc-rule, #d6cfc0);
    border-left: 3px solid var(--sc-teal, #155752); border-radius: 2px;
    font-family: var(--sc-serif, Georgia, serif); font-size: 13.5px;
    line-height: 1.6; color: var(--sc-text-dim, #465366);
    max-width: 72ch; }
  .ck-dil-note { font-family: var(--sc-mono, monospace);
    font-size: 10.5px; letter-spacing: .05em; text-transform: uppercase;
    color: var(--sc-text-dim, #465366); margin: 0 0 12px; }
  .ck-dil-note-after { margin: 8px 0 18px; }
  /* The provenance-tooltip card inherits the note's uppercase +
     tracking when the trigger sits inside .ck-dil-note — reset so
     the methodology explainer reads as sentence case, not caps. */
  .ck-dil-note .ck-prov-tt-card { text-transform: none;
    letter-spacing: normal; }
  .ck-dil-files { margin: 14px 0 0; padding: 0 0 0 18px; }
  .ck-dil-files li { font-family: var(--sc-mono, monospace);
    font-size: 11px; color: var(--sc-text-dim, #465366);
    line-height: 1.8; }
  .ck-dil-chips { display: flex; flex-wrap: wrap; gap: 6px;
    margin: 0 0 14px; }
  .ck-dil-chip { display: inline-flex; align-items: center; gap: 8px;
    padding: 3px 10px; background: #fff;
    border: 1px solid var(--sc-rule, #d6cfc0); border-radius: 2px;
    font-family: var(--sc-mono, monospace); font-size: 11px;
    color: var(--sc-text, #1a2332); }
  .ck-dil-chip b { color: var(--sc-teal, #155752); font-weight: 700;
    font-variant-numeric: tabular-nums; }
  .ck-dil-panel { background: #fff;
    border: 1px solid var(--sc-rule, #d6cfc0); border-radius: 2px;
    padding: 16px 18px; margin: 0 0 18px; }
  .ck-dil-pareto-row { margin-bottom: 12px; }
  .ck-dil-pareto-row:last-child { margin-bottom: 2px; }
  .ck-dil-pareto-meta { display: flex; justify-content: space-between;
    gap: 12px; font-family: var(--sc-sans, Inter, sans-serif);
    font-size: 12.5px; margin-bottom: 4px; }
  .ck-dil-pareto-cat { color: var(--sc-text, #1a2332);
    font-weight: 500; }
  .ck-dil-pareto-num { font-family: var(--sc-mono, monospace);
    font-variant-numeric: tabular-nums;
    color: var(--sc-text-dim, #465366); white-space: nowrap; }
  .ck-dil-pareto-track { background: var(--sc-bone, #ece5d6);
    height: 5px; border-radius: 1px; overflow: hidden; }
  .ck-dil-pareto-fill { background: var(--sc-teal, #155752);
    height: 100%; }
  .ck-dil-total td { border-top: 2px solid var(--sc-rule-2, #bfb6a2);
    font-weight: 700; }
  .ck-dil-2col { display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 16px; margin: 0 0 18px; }
  .ck-dil-subhead { font-family: var(--sc-mono, monospace);
    font-size: 10px; font-weight: 700; letter-spacing: .12em;
    text-transform: uppercase; color: var(--sc-text-dim, #465366);
    margin: 0 0 6px; }
"""

_QOE_CSS = _ERROR_CSS + """
  .qoe-form { max-width: 560px; }
  .qoe-form label { display: block; margin: 14px 0 6px;
    font-family: var(--sc-mono, JetBrains Mono, monospace);
    font-size: 11px; font-weight: 700; letter-spacing: 0.1em;
    text-transform: uppercase; color: var(--sc-text-dim, #465366); }
  .qoe-form select, .qoe-form input { width: 100%; padding: 9px 12px;
    font-size: 13.5px; border: 1px solid var(--sc-rule, #d6cfc0);
    background: #fff; color: var(--sc-text, #1a2332); border-radius: 2px;
    font-family: var(--sc-sans, Inter, sans-serif); }
  .qoe-form select:focus-visible, .qoe-form input:focus-visible {
    outline: 2px solid var(--sc-teal, #155752); outline-offset: 2px;
    border-color: var(--sc-teal, #155752); }
  .qoe-form button { margin-top: 24px; padding: 10px 22px;
    background: var(--sc-navy, #0b2341); color: #fff; border: 0;
    font-size: 12px; cursor: pointer; font-weight: 700;
    letter-spacing: 0.1em; text-transform: uppercase; border-radius: 2px;
    font-family: var(--sc-sans, Inter, sans-serif); }
  .qoe-form button:hover { background: var(--sc-teal, #155752); }
  .qoe-form button:focus-visible {
    outline: 2px solid var(--sc-teal, #155752); outline-offset: 2px; }
  .qoe-lead { font-family: var(--sc-serif, Georgia, serif);
    font-size: 14.5px; line-height: 1.6;
    color: var(--sc-text-dim, #465366);
    max-width: 640px; margin: 0 0 24px; }
"""


# ── Shared fragments ────────────────────────────────────────────────

def _masthead(
    *,
    phase: int,
    title: str,
    meta: str,
    lede_italic: str,
    lede_body: str,
    source_note: str = "",
) -> str:
    """Tier-1 editorial masthead for the diligence workflow pages.

    One place owns the phase labeling (the eyebrow) so the H1 stays a
    clean page name — the earlier 'Phase N — Title' H1s duplicated the
    shell subtitle and let two surfaces both claim Phase 3. The
    4-dot legend that ``ck_editorial_head`` ships doubles as the
    live/illustrative honesty key for the synthetic demo sections.
    """
    return ck_editorial_head(
        eyebrow=f"RCM DILIGENCE · PHASE {phase} OF 4",
        title=html.escape(title),
        meta=meta,
        lede_italic_phrase=lede_italic,
        lede_body=html.escape(lede_body),
        source_note=source_note,
    )


def _fixture_meta(dataset_loaded: str = "") -> str:
    """Mono meta line with the real fixture count + load state."""
    n = len(AVAILABLE_FIXTURES)
    if dataset_loaded:
        return f"{n} fixtures · loaded {dataset_loaded}"
    return f"{n} fixtures · no dataset loaded"


def _fixture_selector(
    current_tab_route: str,
    current_dataset: str = "",
    *,
    select_id: str = "ck-dil-dataset",
) -> str:
    """Editorial fixture picker — bone-bordered select + navy → teal
    hover Load button. Used as the dataset-gate at the top of every
    diligence tab so the partner can drive the page without leaving.
    ``select_id`` pairs the visible label with its control (a11y)."""
    options = "".join(
        f'<option value="{html.escape(name)}"'
        f'{" selected" if name == current_dataset else ""}>'
        f'{html.escape(label)}</option>'
        for name, label in AVAILABLE_FIXTURES
    )
    sid = html.escape(select_id)
    return (
        f'<form method="GET" action="{html.escape(current_tab_route)}" '
        f'class="ck-diligence-fixture">'
        f'<label class="ck-diligence-fixture-label" for="{sid}">'
        f'Dataset</label>'
        f'<select name="dataset" id="{sid}" '
        f'class="ck-diligence-fixture-select" aria-label="Dataset">'
        f'<option value="">— pick a fixture —</option>{options}'
        f'</select>'
        f'<button type="submit" class="ck-diligence-fixture-go">'
        f'Load &rarr;</button>'
        f'</form>'
    )


def _resolve_dataset(dataset: str) -> Optional[Path]:
    if not dataset:
        return None
    valid = {name for name, _ in AVAILABLE_FIXTURES}
    if dataset not in valid:
        return None
    path = FIXTURE_ROOT / dataset
    if not path.exists():
        return None
    return path


def _error_panel(headline: str, exc: Exception) -> str:
    """Partner-readable failure panel. The raw exception is preserved
    for the analyst inside a collapsed <details> block instead of
    being dumped headline-level (a KeyError string is a debugging
    artifact, not a partner message)."""
    detail = html.escape(f"{type(exc).__name__}: {exc}")
    row = (
        '<li class="ck-dil-error-row">'
        'This fixture could not be processed. Re-select the dataset '
        'or check the source files, then reload the page.'
        '<details class="ck-dil-error-detail">'
        '<summary>Technical detail</summary>'
        f'<code>{detail}</code>'
        '</details></li>'
    )
    return ck_severity_panel(
        tone="red", label=headline, count=1, rows_html=row,
    )


def _note(text: str, *, after: bool = False) -> str:
    """Quiet mono caption (truncation notices, ingest IDs, match
    counts). ``after=True`` adds bottom margin for use under tables."""
    cls = "ck-dil-note ck-dil-note-after" if after else "ck-dil-note"
    return f'<div class="{cls}">{html.escape(text)}</div>'


def _info_strip(text: str) -> str:
    """Serif context footnote under a table/section — NOT an empty
    state (empty states go through ck_empty_state/ck_affirm_empty)."""
    return f'<div class="ck-dil-info">{html.escape(text)}</div>'


def _next_dataset_qs(ds_path: Optional[Path], dataset: str) -> str:
    """Carry a *validated* fixture name to the next phase's URL.

    Only appended once ``_resolve_dataset`` accepted the value, so an
    arbitrary query string never round-trips into the next href."""
    return f"?dataset={dataset}" if ds_path is not None else ""


# ── Phase 1: /diligence/ingest ─────────────────────────────────────

def render_ingest_page(dataset: str = "") -> str:
    ds_path = _resolve_dataset(dataset)
    body = [
        _masthead(
            phase=1,
            title="Ingestion & Normalization",
            meta=_fixture_meta(dataset if ds_path is not None else ""),
            lede_italic=(
                "Ingest the source data, see every transformation."
            ),
            lede_body=(
                "Raw 837 / 835 EDI, Epic / Cerner / Athena exports, and "
                "messy Excel funnel into a single versioned CCD "
                "(Canonical Claims Dataset). The full transformation "
                "log renders below — field mappings, normalizations, "
                "dropped rows, derived columns — so data quality is "
                "auditable before any analytic surface trusts the "
                "ingested table."
            ),
            source_note=(
                "Fixture upload or CCD feed (per-deal); current "
                "fixtures are synthetic for prototype."
            ),
        ),
        (
            '<div class="ck-dil-info">'
            'Have real files? Upload 835/837 remittances or a full VDR '
            'ZIP for revenue-leakage findings and a diligence memo '
            '(PHI-tokenized, aggregate output). '
            '<a class="ck-arrow" href="/diligence/snapshot">'
            'Open Healthcare Snapshot</a>'
            '</div>'
        ),
        _fixture_selector(
            "/diligence/ingest", dataset,
            select_id="ck-dil-dataset-ingest",
        ),
    ]

    if ds_path is not None:
        try:
            from . import ingest_dataset
            ccd = ingest_dataset(ds_path)
            body.append(_ccd_summary_card(ccd))
            body.append(_transformation_log_preview(ccd))
        except Exception as exc:
            body.append(_error_panel("Ingestion failed", exc))
    else:
        body.append(ck_empty_state(
            "Pick a fixture to run the ingester.",
            "Each fixture is canonical truth data with a locked "
            "expected output, so the CCD summary and transformation "
            "log below always reflect a verified pipeline run.",
            eyebrow="NO DATASET LOADED",
            icon="▦",
            cta_label="Load the clean acute baseline",
            cta_href="/diligence/ingest?dataset=hospital_01_clean_acute",
        ))

    body.append(ck_next_section(
        "Continue to Benchmarks",
        "/diligence/benchmarks" + _next_dataset_qs(ds_path, dataset),
        eyebrow="Phase 2 of 4",
        italic_word="Benchmarks",
    ))
    return chartis_shell(
        "\n".join(body), "RCM Diligence — Ingestion",
        active_nav="/diligence/ingest",
        subtitle="Phase 1 of 4 · Canonical Claims Dataset",
        extra_css=_DILIGENCE_CSS,
    )


def _ccd_summary_card(ccd: Any) -> str:
    """CCD summary as an editorial KPI grid — claims, schema, source
    files, content hash (with provenance) — plus the ingest ID as a
    quiet mono caption and the source-file inventory list."""
    hash12 = html.escape(ccd.content_hash()[:12])
    hash_value = ck_provenance_tooltip(
        "Content hash",
        f"{hash12}…",
        explainer=(
            "First 12 hex characters of the SHA-256 digest over the "
            "canonical claim rows. Re-ingesting byte-identical source "
            "files yields the same hash; any upstream edit changes it "
            "— this is the audit anchor for the dataset version."
        ),
    )
    kpis = (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block(
            "Claims", ck_fmt_number(len(ccd.claims)),
            "canonical claim rows",
        )
        + ck_kpi_block(
            "Schema", html.escape(ccd.ccd_schema_version),
            "CCD schema version",
        )
        + ck_kpi_block(
            "Source files", ck_fmt_number(len(ccd.source_files)),
            "ingested this run",
        )
        + ck_kpi_block(
            "Content hash", hash_value,
            "SHA-256 · first 12 chars",
        )
        + '</div>'
    )
    files = "".join(
        f'<li>{html.escape(str(f))}</li>'
        for f in (ccd.source_files or [])
    )
    files_html = (
        f'<ul class="ck-dil-files">{files}</ul>' if files else ""
    )
    return (
        ck_section_header(
            "Canonical Claims Dataset", eyebrow="PHASE 1 OUTPUT",
        )
        + _note(f"Ingest ID {ccd.ingest_id}")
        + kpis
        + files_html
    )


def _transformation_log_preview(ccd: Any) -> str:
    """Transformation-log summary chips + the first 20 entries as an
    editorial data table with humanized headers and toned severity
    badges. An empty log is the good outcome, so it renders as an
    affirmative band rather than a bare notice."""
    summary = ccd.log.summary()
    if not summary:
        return ck_affirm_empty(
            headline="No coercions logged.",
            body=(
                "Every row in this fixture passed through the ingester "
                "without field coercion — the transformation log is "
                "empty."
            ),
        )
    ranked = sorted(summary.items(), key=lambda kv: -kv[1])[:8]
    chips = "".join(
        f'<span class="ck-dil-chip">{html.escape(rule)}'
        f'<b>{count:,}</b></span>'
        for rule, count in ranked
    )
    tone_map = {"INFO": "neutral", "WARN": "warning", "ERROR": "negative"}
    rows = []
    for e in ccd.log.entries[:20]:
        sev = str(e.severity or "INFO").upper()
        badge = ck_signal_badge(sev, tone=tone_map.get(sev, "neutral"))
        rows.append(
            "<tr>"
            + ck_data_cell(html.escape(e.ccd_row_id), mono=True,
                           tone="dim")
            + ck_data_cell(html.escape(e.source_file), mono=True,
                           tone="dim")
            + ck_data_cell(html.escape(str(e.source_row)),
                           align="right", mono=True)
            + ck_data_cell(html.escape(e.rule), mono=True)
            + ck_data_cell(html.escape(e.target_field))
            + ck_data_cell(badge)
            + "</tr>"
        )
    table = ck_data_table(
        headers=[
            {"label": "Row ID"},
            {"label": "Source file"},
            {"label": "Line", "align": "right"},
            {"label": "Rule"},
            {"label": "Target field"},
            {"label": "Severity"},
        ],
        rows_html="".join(rows),
    )
    total = len(ccd.log.entries)
    trunc = (
        _note(
            f"Showing 20 of {total:,} entries — every entry traces a "
            "coerced value back to its source file and row.",
            after=True,
        )
        if total > 20 else ""
    )
    return (
        ck_section_header(
            "Transformation log",
            eyebrow="ROW-LEVEL AUDIT TRAIL",
            count=total,
        )
        + f'<div class="ck-dil-chips">{chips}</div>'
        + table
        + trunc
    )


# ── Phase 2: /diligence/benchmarks ─────────────────────────────────

def _inject_after_main(page_html: str, fragment: str) -> str:
    """Splice ``fragment`` immediately after the opening <main> tag.

    Used by the benchmarks route, whose shell is rendered by
    ``rcm_mc.ui.diligence_benchmarks`` (another owner). Both the
    placeholder and the live branch go through this ONE helper so the
    fixture selector lands in the same top-of-page position in every
    state — it previously appended before </main> in the empty state
    (bottom of page) and after <main> in the live state (top)."""
    idx = page_html.find("<main")
    if idx >= 0:
        close = page_html.find(">", idx)
        if close > 0:
            return page_html[:close + 1] + fragment + page_html[close + 1:]
    return page_html


def render_benchmarks_page(
    dataset: str = "",
    *,
    bundle=None, cohort_report=None, cash_waterfall=None,
) -> str:
    """Delegates to ``rcm_mc.ui.diligence_benchmarks`` for the full
    rendering when a bundle is available. When ``dataset`` is supplied,
    ingests + computes KPIs + cohort + waterfall live and passes them
    through.
    """
    from ..ui.diligence_benchmarks import render_benchmarks_page as _render

    # Fast path: caller passed a pre-computed bundle (old API).
    if bundle is not None:
        return _render(
            bundle=bundle, cohort_report=cohort_report,
            cash_waterfall=cash_waterfall,
        )

    # The delegated page's shell doesn't carry our extra_css, so the
    # selector travels with its own <style> block.
    selector = (
        "<style>" + _DILIGENCE_CSS + "</style>"
        + _fixture_selector(
            "/diligence/benchmarks", dataset,
            select_id="ck-dil-dataset-benchmarks",
        )
    )

    ds_path = _resolve_dataset(dataset)
    if ds_path is None:
        placeholder = _render()  # renders the placeholder
        return _inject_after_main(placeholder, selector)

    try:
        from . import (
            compute_cohort_liquidation, compute_kpis, ingest_dataset,
        )
        from .benchmarks import compute_cash_waterfall
        ccd = ingest_dataset(ds_path)
        as_of = date(2025, 1, 1)
        bundle = compute_kpis(ccd, as_of_date=as_of, provider_id=dataset)
        cohort = compute_cohort_liquidation(ccd.claims, as_of_date=as_of)
        waterfall = compute_cash_waterfall(ccd.claims, as_of_date=as_of)
    except Exception as exc:
        err_body = (
            _masthead(
                phase=2,
                title="Benchmarks",
                meta=_fixture_meta(),
                lede_italic="Computation failed on this fixture.",
                lede_body=(
                    "The KPI pipeline could not complete. Pick another "
                    "dataset, or expand the technical detail below."
                ),
            )
            + _fixture_selector(
                "/diligence/benchmarks", dataset,
                select_id="ck-dil-dataset-benchmarks",
            )
            + _error_panel(f"Pipeline error on {dataset!r}", exc)
        )
        return chartis_shell(
            err_body, "RCM Diligence — Benchmarks",
            active_nav="/diligence/benchmarks",
            subtitle="Phase 2 of 4",
            extra_css=_DILIGENCE_CSS,
        )

    live_html = _render(bundle=bundle, cohort_report=cohort,
                        cash_waterfall=waterfall)
    return _inject_after_main(live_html, selector)


# ── Partner-signed QoE memo: /diligence/qoe-memo ───────────────────

def render_qoe_memo_page(
    dataset: str = "",
    qs: Optional[dict] = None,
    *,
    store: Optional[Any] = None,
) -> str:
    """Render the partner-signed QoE memo as a standalone HTML page.

    Returns a full <html>...</html> document (not the editorial shell)
    so "Print → Save as PDF" from a browser produces a clean memo
    without Chartis nav chrome. When ``dataset`` is empty, renders a
    minimal landing with a fixture selector + instructions.

    Optional query-string fields read from ``qs``:
        deal_name, target_entity, engagement_id, partner_name,
        preparer_name, mgmt_revenue (cohort-month → USD, one-shot
        form: ``cohort=2024-03,value=6850``), created_by.

    Engagement integration: when ``engagement_id`` AND ``created_by``
    are supplied AND ``store`` is non-None, the render also writes a
    DRAFT engagement deliverable so the memo shows up in the
    engagement's deliverable list. The created_by user must be a
    PARTNER/LEAD/ANALYST member of the engagement; a PermissionError
    is caught and surfaced in the landing page rather than raising
    past the route.
    """
    qs = qs or {}
    ds_path = _resolve_dataset(dataset)
    if ds_path is None:
        return _qoe_memo_landing(dataset)

    try:
        from . import compute_kpis, ingest_dataset
        from .benchmarks import compute_cash_waterfall
        from ..exports.qoe_memo import (
            QoEMemoMetadata, render_qoe_memo_html,
        )
        ccd = ingest_dataset(ds_path)
        as_of = date(2025, 1, 1)
        bundle = compute_kpis(ccd, as_of_date=as_of, provider_id=dataset)

        mgmt_map = _parse_mgmt_revenue(qs)
        waterfall = compute_cash_waterfall(
            ccd.claims, as_of_date=as_of,
            management_reported_revenue_by_cohort_month=mgmt_map,
        )

        engagement_id = (qs.get("engagement_id") or [""])[0] or None
        created_by = (qs.get("created_by") or [""])[0] or None

        meta = QoEMemoMetadata(
            deal_name=(qs.get("deal_name") or [dataset])[0] or None,
            target_entity=(qs.get("target_entity") or [""])[0] or None,
            engagement_id=engagement_id,
            partner_name=(qs.get("partner_name") or [""])[0] or None,
            preparer_name=(qs.get("preparer_name") or [""])[0] or None,
        )

        # Optional: write a DRAFT engagement deliverable for this
        # memo render. Silent on failure — rendering the memo always
        # succeeds even if the engagement link fails.
        if (store is not None and engagement_id and created_by):
            _link_memo_as_deliverable(
                store, engagement_id=engagement_id,
                created_by=created_by,
                title=meta.deal_name or dataset or "QoE Memo",
                content_ref=f"/diligence/qoe-memo?dataset={dataset}",
            )

        # Counterfactual section — when query params give us the
        # metadata a CCD can't supply (legal_structure, states,
        # landlord, etc.), run the advisor + attach to the memo.
        counterfactuals = None
        try:
            from .counterfactual import run_counterfactuals_from_ccd
            cf_meta: Dict[str, Any] = {}
            for k in (
                "legal_structure", "specialty", "landlord",
                "geography",
            ):
                val = (qs.get(k) or [""])[0]
                if val:
                    cf_meta[k] = val
            for k in ("states", "msas", "cbsa_codes"):
                raw = (qs.get(k) or [""])[0]
                if raw:
                    cf_meta[k] = [
                        t.strip() for t in raw.split(",") if t.strip()
                    ]
            if cf_meta.get("specialty") in {
                "EMERGENCY_MEDICINE", "ANESTHESIOLOGY", "RADIOLOGY",
                "PATHOLOGY", "NEONATOLOGY", "HOSPITALIST",
            }:
                cf_meta["is_hospital_based_physician"] = True
            if cf_meta:
                counterfactuals = run_counterfactuals_from_ccd(
                    ccd, metadata=cf_meta,
                )
        except Exception:  # noqa: BLE001 — counterfactuals are additive
            counterfactuals = None

        return render_qoe_memo_html(
            bundle=bundle, cash_waterfall=waterfall, metadata=meta,
            counterfactuals=counterfactuals,
        )
    except Exception as exc:
        return _qoe_memo_landing(
            dataset,
            error=f"{type(exc).__name__}: {exc}",
        )


def _link_memo_as_deliverable(
    store: Any,
    *,
    engagement_id: str,
    created_by: str,
    title: str,
    content_ref: str,
) -> None:
    """Best-effort: create a DRAFT QOE_MEMO deliverable on the
    engagement. Swallows errors (non-member, missing engagement) so a
    broken engagement link never fails the memo render."""
    try:
        from ..engagement import create_deliverable
        create_deliverable(
            store, engagement_id=engagement_id,
            kind="QOE_MEMO", title=title,
            created_by=created_by,
            content_ref=content_ref,
        )
    except Exception:  # noqa: BLE001 — engagement link is opportunistic
        pass


def _parse_mgmt_revenue(qs: dict) -> Optional[Dict[str, float]]:
    """Parse ``?mgmt_cohort=2024-03&mgmt_value=6850`` into
    ``{'2024-03': 6850.0}``. Also accepts repeated pairs. Missing or
    unparsable input returns None so QoR renders as UNKNOWN."""
    cohorts = qs.get("mgmt_cohort") or []
    values = qs.get("mgmt_value") or []
    if not cohorts or not values:
        return None
    out: Dict[str, float] = {}
    for c, v in zip(cohorts, values):
        try:
            out[str(c)] = float(v)
        except (TypeError, ValueError):
            continue
    return out or None


def _qoe_memo_landing(dataset: str, error: Optional[str] = None) -> str:
    """Small landing rendered when no fixture was picked (or the
    pipeline errored). Wraps in chartis_shell so the partner gets
    the editorial topbar + sub-nav + Cmd+K palette during the
    setup step. The rendered memo itself remains a standalone
    printable document — only this picker is editorial-chromed.

    NOTE: the H1 markup ('Quality of Earnings <em>Memorandum</em>.')
    is deliberately hand-built — tests pin the '<em>' structure, and
    ``ck_page_title`` would escape it. Do not route it through the
    helper.
    """
    err_block = ""
    if error:
        detail = html.escape(error)
        err_block = ck_severity_panel(
            tone="red",
            label="Could not render the memo",
            count=1,
            rows_html=(
                '<li class="ck-dil-error-row">'
                'The selected dataset did not produce a memo. Re-check '
                'the fixture and the management-revenue inputs, then '
                'render again.'
                '<details class="ck-dil-error-detail">'
                '<summary>Technical detail</summary>'
                f'<code>{detail}</code>'
                '</details></li>'
            ),
        )
    options = "".join(
        f'<option value="{html.escape(name)}"'
        f'{" selected" if name == dataset else ""}>'
        f'{html.escape(label)}</option>'
        for name, label in AVAILABLE_FIXTURES
    )
    form = (
        '<form class="qoe-form" method="GET" action="/diligence/qoe-memo">'
        '<label for="qoe-dataset">Dataset</label>'
        f'<select name="dataset" id="qoe-dataset" aria-label="Dataset">'
        f'<option value="">— pick a fixture —</option>{options}</select>'
        '<label for="qoe-deal-name">Deal name (shown on cover)</label>'
        '<input name="deal_name" id="qoe-deal-name" '
        'placeholder="Project Aurora">'
        '<label for="qoe-engagement-id">Engagement ID</label>'
        '<input name="engagement_id" id="qoe-engagement-id" '
        'placeholder="RCM-2025-042">'
        '<label for="qoe-partner-name">Partner name</label>'
        '<input name="partner_name" id="qoe-partner-name" '
        'placeholder="Partner A">'
        '<label for="qoe-preparer-name">Preparer name</label>'
        '<input name="preparer_name" id="qoe-preparer-name" '
        'placeholder="Senior Associate B">'
        '<label for="qoe-mgmt-cohort">Management cohort '
        '(optional, e.g. 2024-03)</label>'
        '<input name="mgmt_cohort" id="qoe-mgmt-cohort" '
        'placeholder="2024-03">'
        '<label for="qoe-mgmt-value">Management-reported revenue, USD '
        '(optional)</label>'
        '<input name="mgmt_value" id="qoe-mgmt-value" '
        'placeholder="e.g. 6850.00">'
        '<button type="submit">Render Memo &rarr;</button>'
        '</form>'
    )
    body = (
        '<header class="ck-page-title">'
        '<div class="ck-eyebrow">RCM DILIGENCE · QOE MEMO</div>'
        '<h1>Quality of Earnings <em>Memorandum</em>.</h1>'
        '<div class="ck-page-title-meta">'
        'Partner deliverable · standalone printable HTML</div>'
        '</header>'
        '<p class="qoe-lead">Pick a canonical claims dataset and '
        '(optionally) provide management-reported revenue for the QoR '
        'reconciliation. The memo renders as a standalone, printable '
        'HTML document. Use your browser&rsquo;s <em>Print → Save as '
        'PDF</em> to produce the partner deliverable.</p>'
        + err_block
        + ck_panel(form, title="Render parameters")
    )
    return chartis_shell(
        body, "QoE Memo",
        active_nav="/diligence/qoe-memo",
        subtitle="Pick a dataset to render the partner deliverable",
        extra_css=_QOE_CSS,
    )


# ── Phase 3: /diligence/root-cause ─────────────────────────────────

def render_root_cause_page(dataset: str = "") -> str:
    ds_path = _resolve_dataset(dataset)
    body = [
        _masthead(
            phase=3,
            title="Root Cause Analysis",
            meta=_fixture_meta(dataset if ds_path is not None else ""),
            lede_italic=(
                "Where the denial dollars actually come from."
            ),
            lede_body=(
                "Stratifies the deal's denied dollars by claim "
                "adjustment reason code (CARC) category and lists "
                "every zero-balance write-off with its charge → "
                "allowed → adjustment trail preserved — sizing the "
                "recoverable denial bucket per workstream before the "
                "100-day plan is drafted."
            ),
            source_note=(
                "Per-deal denial ledger (live once a CCD is loaded)."
            ),
        ),
        _fixture_selector(
            "/diligence/root-cause", dataset,
            select_id="ck-dil-dataset-root-cause",
        ),
    ]

    if ds_path is None:
        body.append(ck_empty_state(
            "Pick a fixture to run the denial stratification.",
            "The denial Pareto and ZBA autopsy below compute live "
            "from the selected fixture's claim set.",
            eyebrow="NO DATASET LOADED",
            icon="◈",
            cta_label="Load the denial-heavy fixture",
            cta_href=(
                "/diligence/root-cause?dataset=hospital_02_denial_heavy"
            ),
        ))
    else:
        try:
            from . import compute_kpis, ingest_dataset
            ccd = ingest_dataset(ds_path)
            bundle = compute_kpis(ccd, as_of_date=date(2025, 1, 1),
                                   provider_id=dataset)
            body.append(_denial_pareto(bundle.denial_stratification))
            body.append(_zba_autopsy(ccd.claims))
        except Exception as exc:
            body.append(_error_panel(
                "Root-cause computation failed", exc,
            ))

    body.append(ck_next_section(
        "Continue to Value Creation",
        "/diligence/value" + _next_dataset_qs(ds_path, dataset),
        eyebrow="Phase 4 of 4",
        italic_word="Value",
    ))
    return chartis_shell(
        "\n".join(body), "RCM Diligence — Root Cause",
        active_nav="/diligence/root-cause",
        subtitle="Phase 3 of 4",
        extra_css=_DILIGENCE_CSS,
    )


def _denial_pareto(rows) -> str:
    """Mini Pareto — category × dollars. Full drill-through is the
    Phase 2 benchmarks surface; this is the compact Phase-3 view."""
    rows = list(rows or [])
    if not rows:
        return ck_affirm_empty(
            headline="No denials in this fixture's claim set.",
            body=(
                "Every claim in the selected fixture paid without a "
                "denial event — there is no denial gap to decompose."
            ),
        )
    total = sum(r.dollars_denied for r in rows) or 1.0
    items = []
    for r in rows:
        pct = r.dollars_denied / total
        bar = max(pct * 100, 2)
        items.append(
            '<div class="ck-dil-pareto-row">'
            '<div class="ck-dil-pareto-meta">'
            f'<span class="ck-dil-pareto-cat">'
            f'{html.escape(r.category)}</span>'
            f'<span class="ck-dil-pareto-num">'
            f'${r.dollars_denied:,.2f} · {r.count:,} claims · '
            f'{pct * 100:.1f}%</span>'
            '</div>'
            '<div class="ck-dil-pareto-track">'
            f'<div class="ck-dil-pareto-fill" style="width:{bar:.1f}%">'
            '</div></div>'
            '</div>'
        )
    return (
        ck_section_header(
            "Denial Pareto",
            eyebrow="BY CLAIM ADJUSTMENT REASON CODE (CARC) CATEGORY",
            count=len(rows),
        )
        + '<div class="ck-dil-panel">' + "".join(items) + '</div>'
    )


def _zba_autopsy(claims) -> str:
    """List every ZBA-flagged row — claims with nonzero adjustment +
    zero paid — showing the preserved original balance. Totals cover
    the FULL set even when the table truncates at 50 rows."""
    zba = [c for c in claims
           if (c.paid_amount or 0) == 0
           and (c.adjustment_amount or 0) > 0]
    if not zba:
        return ck_affirm_empty(
            headline="No zero-balance write-offs in this fixture.",
            body=(
                "No claim carries a nonzero adjustment with zero "
                "payment — there is no silently written-off balance "
                "to autopsy."
            ),
        )
    rows = []
    for c in zba[:50]:
        carcs = ", ".join(c.adjustment_reason_codes or ()) or "—"
        rows.append(
            "<tr>"
            + ck_data_cell(html.escape(c.claim_id), mono=True)
            + ck_data_cell(
                html.escape(c.payer_canonical or c.payer_raw or "—"),
                tone="dim",
            )
            + ck_data_cell(f"${c.charge_amount or 0:,.2f}",
                           align="right", mono=True)
            + ck_data_cell(f"${c.allowed_amount or 0:,.2f}",
                           align="right", mono=True)
            + ck_data_cell(f"${c.adjustment_amount or 0:,.2f}",
                           align="right", mono=True, tone="neg")
            + ck_data_cell(html.escape(carcs), mono=True, tone="dim")
            + "</tr>"
        )
    tot_charge = sum((c.charge_amount or 0) for c in zba)
    tot_allowed = sum((c.allowed_amount or 0) for c in zba)
    tot_adj = sum((c.adjustment_amount or 0) for c in zba)
    rows.append(
        '<tr class="ck-dil-total">'
        + ck_data_cell(f"Total · {len(zba):,} write-offs", weight=700)
        + ck_data_cell("")
        + ck_data_cell(f"${tot_charge:,.2f}",
                       align="right", mono=True, weight=700)
        + ck_data_cell(f"${tot_allowed:,.2f}",
                       align="right", mono=True, weight=700)
        + ck_data_cell(f"${tot_adj:,.2f}",
                       align="right", mono=True, tone="neg", weight=700)
        + ck_data_cell("")
        + "</tr>"
    )
    table = ck_data_table(
        headers=[
            {"label": "Claim"},
            {"label": "Payer"},
            {"label": "Charge", "align": "right"},
            {"label": "Allowed", "align": "right"},
            {"label": "Adjustment", "align": "right"},
            {"label": "CARCs"},
        ],
        rows_html="".join(rows),
    )
    trunc = (
        _note(
            f"Showing 50 of {len(zba):,} write-offs — the totals row "
            "covers the full set.",
            after=True,
        )
        if len(zba) > 50 else ""
    )
    return (
        ck_section_header(
            "ZBA autopsy",
            eyebrow="RECOVERABLE WRITE-OFFS · TRAIL PRESERVED",
            count=len(zba),
        )
        + table
        + trunc
        + _info_strip(
            "Each row preserves the original charge, allowed, and "
            "adjustment amounts, so a written-off balance can be "
            "re-pursued with its full trail."
        )
    )


# ── Phase 4: /diligence/value ──────────────────────────────────────

def render_value_page(dataset: str = "") -> str:
    ds_path = _resolve_dataset(dataset)
    body = [
        _masthead(
            phase=4,
            title="Value Creation Model",
            meta=_fixture_meta(dataset if ds_path is not None else ""),
            lede_italic=(
                "What the RCM levers are worth on this deal."
            ),
            lede_body=(
                "Two previews render today: the contract re-pricer "
                "derives payer-leverage factors by pricing the "
                "fixture's claims against a demonstration contract "
                "schedule, and a CMS advisory overlay demonstrates the "
                "regime + consensus-rank classifiers on a synthetic "
                "frame. Both are marked illustrative until a real "
                "contract schedule and CMS extract are supplied."
            ),
            source_note=(
                "Demo contract schedule + synthetic CMS frame "
                "(illustrative); claims from the selected fixture."
            ),
        ),
        _fixture_selector(
            "/diligence/value", dataset,
            select_id="ck-dil-dataset-value",
        ),
    ]

    if ds_path is None:
        body.append(ck_empty_state(
            "Pick a fixture to derive payer leverage.",
            "The contract re-pricer prices the selected fixture's "
            "claims against a demonstration schedule; the CMS "
            "advisory overlay previews market posture on a synthetic "
            "frame.",
            eyebrow="NO DATASET LOADED",
            icon="⬦",
            cta_label="Load the mixed-payer fixture",
            cta_href="/diligence/value?dataset=hospital_04_mixed_payer",
        ))
    else:
        try:
            from . import ingest_dataset
            ccd = ingest_dataset(ds_path)
            body.append(_repricer_summary(ccd))
            body.append(_cms_advisory_summary())
        except Exception as exc:
            body.append(_error_panel("Value computation failed", exc))

    body.append(ck_next_section(
        "Render the QoE Memorandum",
        "/diligence/qoe-memo" + _next_dataset_qs(ds_path, dataset),
        eyebrow="Partner deliverable",
        italic_word="Memorandum",
    ))
    return chartis_shell(
        "\n".join(body), "RCM Diligence — Value Creation",
        active_nav="/diligence/value",
        subtitle="Phase 4 of 4",
        extra_css=_DILIGENCE_CSS,
    )


def _repricer_summary(ccd: Any) -> str:
    """Run the contract re-pricer against a synthetic default schedule
    to demonstrate the derived-leverage output. Honestly labeled: the
    schedule is a demo, not the deal's contracts."""
    from .benchmarks import (
        ContractRate, ContractSchedule, payer_leverage_for_bridge,
        reprice_claims,
    )
    # Synthetic default schedule covering the common CPTs in our fixtures.
    rates = [
        ContractRate("COMMERCIAL",         "99213", allowed_amount_usd=100.0),
        ContractRate("COMMERCIAL",         "99214", allowed_amount_usd=150.0),
        ContractRate("MEDICARE",           "99213", allowed_amount_usd=75.0),
        ContractRate("MEDICARE",           "99214", allowed_amount_usd=115.0),
        ContractRate("MEDICARE_ADVANTAGE", "99213", allowed_amount_usd=80.0),
        ContractRate("MEDICAID",           "99213", allowed_amount_usd=50.0),
        ContractRate("SELF_PAY",           "D1110", allowed_amount_usd=125.0),
    ]
    schedule = ContractSchedule(rates=rates, name="demo_default")
    report = reprice_claims(ccd.claims, schedule)
    leverage = payer_leverage_for_bridge(report)
    rows = []
    for pc, lev in sorted(leverage.items(), key=lambda x: -x[1]):
        rows.append(
            "<tr>"
            + ck_data_cell(html.escape(pc), mono=True)
            + ck_data_cell(f"{lev:.2f}x", align="right", mono=True)
            + "</tr>"
        )
    if not rows:
        rows.append(
            "<tr>"
            + ck_data_cell(
                "No matched claims — the demo schedule lacks rates "
                "for this fixture's CPT codes.",
                tone="dim",
            )
            + ck_data_cell("—", align="right", mono=True, tone="dim")
            + "</tr>"
        )
    table = ck_data_table(
        headers=[
            {"label": "Payer class (bridge vocabulary)"},
            {"label": "Leverage vs Commercial", "align": "right"},
        ],
        rows_html="".join(rows),
    )
    prov = ck_provenance_tooltip(
        "Leverage vs Commercial",
        "How leverage is derived",
        explainer=(
            "Per payer class: repriced allowed amounts under the demo "
            "contract schedule, expressed as a multiple of the "
            "Commercial payer class (Commercial = 1.00x). On a live "
            "deal these factors feed the value bridge's payer revenue "
            "assumptions."
        ),
    )
    return (
        ck_section_header(
            "Contract re-pricer",
            eyebrow="DERIVED PAYER LEVERAGE",
        )
        + ck_illustrative_note(
            "payer-leverage factors (priced against a demo contract "
            "schedule, not this deal's contracts)"
        )
        + _note(
            f"{report.matched_claims:,} matched · "
            f"{report.unmatched_claims:,} unmatched of "
            f"{report.total_claims:,} claims"
        )
        + table
        + f'<div class="ck-dil-note ck-dil-note-after">{prov}</div>'
        + _info_strip(
            "Once a real contract schedule is attached, these "
            "leverage factors feed the value bridge's payer revenue "
            "assumptions directly."
        )
    )


def _cms_advisory_summary() -> str:
    """Run the CMS advisory pipeline on a small synthetic frame to
    demonstrate the consensus rank + regime classifier. Honestly
    labeled illustrative — the frame is fabricated in code."""
    try:
        import pandas as pd
        from ..pe.cms_advisory import (
            consensus_rank, momentum_profile, provider_volatility,
            regime_classification, screen_providers, yearly_trends,
        )
        df = pd.DataFrame([
            {"provider_type": "Internal Medicine", "year": y,
             "total_medicare_payment_amt": 1_000_000 * (1 + 0.08) ** i,
             "total_services": 10_000 * (1 + 0.06) ** i,
             "total_unique_benes": 2_000 * (1 + 0.04) ** i,
             "beneficiary_average_risk_score": 1.08,
             "payment_per_service": 100.0 * (1 + 0.02) ** i,
             "payment_per_bene": 500.0 * (1 + 0.04) ** i}
            for i, y in enumerate([2021, 2022, 2023])
        ] + [
            {"provider_type": "Cardiology", "year": y,
             "total_medicare_payment_amt": 3_000_000 * (1 + 0.15) ** i,
             "total_services": 5_000 * (1 + 0.1) ** i,
             "total_unique_benes": 1_000 * (1 + 0.05) ** i,
             "beneficiary_average_risk_score": 1.55,
             "payment_per_service": 600.0 * (1 + 0.05) ** i,
             "payment_per_bene": 3_000.0 * (1 + 0.1) ** i}
            for i, y in enumerate([2021, 2022, 2023])
        ])
        screen = screen_providers(df)
        trends = yearly_trends(df)
        vol = provider_volatility(trends)
        mom = momentum_profile(trends, min_years=2)
        regimes = regime_classification(mom, vol)
        cons = consensus_rank(screen, mom, vol)
    except Exception as exc:
        return _error_panel("CMS advisory demo failed", exc)

    reg_rows = "".join(
        "<tr>"
        + ck_data_cell(html.escape(str(r.get("provider_type", ""))))
        + ck_data_cell(html.escape(str(r.get("regime", ""))),
                       tone="dim")
        + "</tr>"
        for _, r in regimes.iterrows()
    )
    cons_rows = "".join(
        "<tr>"
        + ck_data_cell(html.escape(str(r.get("provider_type", ""))))
        + ck_data_cell(f"{float(r.get('consensus_score', 0)):.2f}",
                       align="right", mono=True, tone="dim")
        + ck_data_cell(f"#{int(r.get('consensus_rank', 0))}",
                       align="right", mono=True, weight=600)
        + "</tr>"
        for _, r in cons.iterrows()
    )
    reg_table = ck_data_table(
        headers=[
            {"label": "Provider type"},
            {"label": "Regime"},
        ],
        rows_html=reg_rows,
        scrollable=False,
    )
    cons_table = ck_data_table(
        headers=[
            {"label": "Provider type"},
            {"label": "Score", "align": "right"},
            {"label": "Rank", "align": "right"},
        ],
        rows_html=cons_rows,
        scrollable=False,
    )
    prov = ck_provenance_tooltip(
        "Consensus score",
        "How the consensus score composes",
        explainer=(
            "Equal-weight blend of the growth screen, the multi-year "
            "momentum profile, and payment volatility — higher scores "
            "rank first. A screen-only leader with erratic payments "
            "ranks below a steady compounder."
        ),
    )
    return (
        ck_section_header(
            "CMS advisory overlay",
            eyebrow="MARKET POSTURE · REGIME + CONSENSUS RANK",
        )
        + ck_illustrative_note(
            "advisory rankings (synthetic two-specialty, three-year "
            "CMS frame built in code)"
        )
        + '<div class="ck-dil-2col">'
        + '<div><div class="ck-dil-subhead">Regime classification</div>'
        + reg_table + '</div>'
        + '<div><div class="ck-dil-subhead">Consensus rank</div>'
        + cons_table + '</div>'
        + '</div>'
        + f'<div class="ck-dil-note ck-dil-note-after">{prov}</div>'
        + _info_strip(
            "On a live deal, the regime and consensus rank flow into "
            "the deal's risk flags on the analysis packet."
        )
    )
