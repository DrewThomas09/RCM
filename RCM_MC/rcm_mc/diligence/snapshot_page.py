"""UI for the V2 healthcare snapshot ingestion tab.

Two server-rendered pages, both through ``chartis_shell`` so they match
the rest of the app:

- :func:`render_snapshot_upload` — the upload form (files or a VDR ZIP)
  with the mandatory PHI warning.
- :func:`render_snapshot_result` — Data Confidence Score, findings, and
  the Markdown memo. Renders **aggregates only** — no patient-level data
  ever reaches this surface (the SnapshotResult is already PHI-safe).
"""
from __future__ import annotations

import html as _html
from typing import TYPE_CHECKING

from ..ui._chartis_kit import chartis_shell, ck_page_title

if TYPE_CHECKING:  # avoid import cost / cycles at module load
    from .snapshot import SnapshotResult

_PHI_WARNING = (
    "Healthcare claims and remittance files may contain PHI. Upload "
    "de-identified data unless appropriate agreements and permissions are "
    "in place. Patient identifiers are tokenized on ingest; outputs are "
    "aggregate-only."
)

_SUPPORTED = ".edi, .txt, .835, .837, .csv, .tsv, .xlsx, .parquet, or a .zip VDR package"


def _warning_banner(text: str) -> str:
    return (
        '<div style="background:var(--sc-bone);border:1px solid var(--sc-rule);'
        'border-left:3px solid var(--sc-warning);padding:12px 16px;'
        'margin:0 0 18px 0;font-size:13px;color:var(--sc-text);">'
        f'<strong>PHI notice.</strong> {_html.escape(text)}</div>'
    )


def render_snapshot_upload(*, notice: str = "", error: str = "") -> str:
    parts = [
        ck_page_title(
            "Healthcare Snapshot — Revenue Leakage Diligence",
            eyebrow="RCM DILIGENCE · V2",
            meta="Upload 835/837 from the VDR · snapshot-based · PHI-tokenized"),
        _warning_banner(_PHI_WARNING),
    ]
    if error:
        parts.append(
            '<div style="background:#fbeae7;border:1px solid var(--sc-negative);'
            f'padding:10px 14px;margin-bottom:14px;color:var(--sc-negative);">'
            f'{_html.escape(error)}</div>')
    if notice:
        parts.append(
            '<div style="background:var(--sc-bone);border:1px solid var(--sc-rule);'
            f'padding:10px 14px;margin-bottom:14px;">{_html.escape(notice)}</div>')
    parts.append(
        '<form method="POST" action="/diligence/snapshot" '
        'enctype="multipart/form-data" '
        'style="background:#fff;border:1px solid var(--sc-rule);padding:18px;'
        'max-width:640px;">'
        '<label style="display:block;font-size:12px;font-weight:600;'
        'margin-bottom:4px;">Deal / target name</label>'
        '<input type="text" name="deal_name" placeholder="Project Atlas" '
        'style="width:100%;padding:8px;margin-bottom:14px;border:1px solid '
        'var(--sc-rule);font-family:inherit;">'
        '<label style="display:block;font-size:12px;font-weight:600;'
        'margin-bottom:4px;">VDR files</label>'
        '<input type="file" name="files" multiple '
        'accept=".edi,.txt,.835,.837,.csv,.tsv,.xlsx,.xlsm,.parquet,.zip" '
        'style="margin-bottom:6px;">'
        f'<div style="font-size:11px;color:var(--sc-text-faint);margin-bottom:16px;">'
        f'Supported: {_SUPPORTED}</div>'
        '<button type="submit" class="ck-btn" '
        'style="background:var(--sc-navy);color:#fff;border:none;padding:10px 18px;'
        'font-weight:600;cursor:pointer;">Run revenue-leakage analysis</button>'
        '</form>')
    return chartis_shell(
        "\n".join(parts), "RCM Diligence — Healthcare Snapshot",
        subtitle="Snapshot-based 835/837 revenue-leakage diligence")


def _confidence_card(result: "SnapshotResult") -> str:
    c = result.confidence
    tone = ("var(--sc-positive)" if c.score >= 85
            else "var(--sc-warning)" if c.score >= 70 else "var(--sc-negative)")
    summaries = "".join(
        f'<li>{_html.escape(s)}</li>' for s in c.summaries)
    issues = "".join(
        f'<li><em>{_html.escape(i.severity)}</em> — {_html.escape(i.message)}</li>'
        for i in c.issues) or "<li>No data-quality issues flagged.</li>"
    return (
        '<div style="background:#fff;border:1px solid var(--sc-rule);'
        'border-left:3px solid ' + tone + ';padding:16px;margin-bottom:18px;">'
        '<div style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'text-transform:uppercase;color:var(--sc-text-dim);">Data Confidence</div>'
        f'<div style="font-family:var(--sc-serif);font-size:28px;font-weight:600;'
        f'color:{tone};">{c.score}/100</div>'
        f'<ul style="margin:8px 0;font-size:13px;">{summaries}</ul>'
        '<div style="font-size:11px;font-weight:600;color:var(--sc-text-dim);'
        'margin-top:8px;">Open issues</div>'
        f'<ul style="margin:4px 0;font-size:12px;color:var(--sc-text-dim);">{issues}</ul>'
        '</div>')


def _findings_cards(result: "SnapshotResult") -> str:
    if not result.findings:
        return ('<div style="font-size:13px;color:var(--sc-text-dim);'
                'margin-bottom:18px;">No findings raised for this snapshot.</div>')
    cards = []
    for f in result.findings:
        impact = (f"${f.estimated_impact_amount:,.0f} (estimate)"
                  if f.estimated_impact_amount is not None else "—")
        caveats = "".join(
            f'<li>{_html.escape(lim)}</li>' for lim in f.limitations)
        cards.append(
            '<div style="background:#fff;border:1px solid var(--sc-rule);'
            'padding:14px;margin-bottom:12px;">'
            f'<div style="font-weight:600;font-size:14px;">{_html.escape(f.title)}</div>'
            f'<div style="font-size:11px;color:var(--sc-text-dim);margin:2px 0 8px;">'
            f'confidence: {_html.escape(f.confidence)} · estimated impact: '
            f'{_html.escape(impact)}</div>'
            f'<div style="font-size:13px;margin-bottom:6px;">{_html.escape(f.summary)}</div>'
            f'<ul style="font-size:11px;color:var(--sc-text-faint);">{caveats}</ul>'
            '</div>')
    return "".join(cards)


def render_snapshot_result(result: "SnapshotResult", *, deal_name: str = "Target") -> str:
    t = result.analytics.totals
    parts = [
        ck_page_title(
            f"Revenue-Leakage Findings — {deal_name}",
            eyebrow="RCM DILIGENCE · V2",
            meta=(f"{t.claim_count:,} claim lines · ${t.gross_charges:,.0f} "
                  f"charges · est. ${t.potentially_preventable_leakage:,.0f} "
                  f"potentially preventable · parser: {result.parser_used}")),
        _warning_banner(
            "Aggregate output only — no patient-level data is displayed. "
            "Figures are directional and subject to validation."),
        _confidence_card(result),
        '<h3 style="font-size:13px;text-transform:uppercase;letter-spacing:.08em;'
        'color:var(--sc-text-dim);">Findings</h3>',
        _findings_cards(result),
        '<h3 style="font-size:13px;text-transform:uppercase;letter-spacing:.08em;'
        'color:var(--sc-text-dim);">Diligence memo (Markdown)</h3>',
        '<p style="font-size:12px;color:var(--sc-text-dim);">Copy into the deal '
        'workstream or IC memo.</p>',
        '<pre style="background:#fff;border:1px solid var(--sc-rule);padding:16px;'
        'overflow:auto;font-family:var(--sc-mono);font-size:12px;line-height:1.5;'
        f'white-space:pre-wrap;">{_html.escape(result.memo_markdown)}</pre>',
        '<p style="margin-top:16px;"><a href="/diligence/snapshot" '
        'style="color:var(--sc-teal-ink);">&larr; Run another snapshot</a></p>',
    ]
    return chartis_shell(
        "\n".join(parts), "RCM Diligence — Revenue-Leakage Findings",
        subtitle="Snapshot-based 835/837 revenue-leakage diligence")
