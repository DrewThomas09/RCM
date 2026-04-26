"""Morning digest — the daily "comes to you" email.

A partner shouldn't have to remember to open the dashboard. At 8 AM
the tool emails them what's worth knowing about the portfolio:

  - Sharpest insight (one bold sentence)
  - Top 3 deals needing attention
  - Top 3 predicted exit outcomes from their watchlist
  - Recent overnight activity (alerts, refreshes, packets built)

Reuses the same compute as the /dashboard sections so the email
and the web view never disagree.

Public API::

    build_morning_digest(db_path) -> DigestPayload
    digest_to_html(payload) -> str
    digest_to_text(payload) -> str
    send_morning_digest(db_path, recipient) -> bool

Wired into:
  - GET /api/digest/morning  (JSON preview — no email sent)
  - POST /api/digest/morning/send  (renders + emails to a recipient)
  - CLI command (separate commit) for cron-driven scheduling
"""
from __future__ import annotations

import html as _html
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _safe_status_str(v: object) -> str:
    """Coerce possibly-NaN covenant_status to a string. Same fix as
    dashboard_page._safe_status_str — pandas NaN crashes .upper()."""
    if v is None:
        return ""
    if isinstance(v, float) and v != v:
        return ""
    s = str(v)
    return "" if s.lower() == "nan" else s


@dataclass
class DigestPayload:
    """Structured representation of the morning email's content."""
    generated_at: str = ""
    headline_insight: Optional[Dict[str, Any]] = None
    needs_attention: List[Dict[str, Any]] = field(default_factory=list)
    predicted_outcomes: List[Dict[str, Any]] = field(default_factory=list)
    recent_events: List[Dict[str, Any]] = field(default_factory=list)
    portfolio_size: int = 0


def build_morning_digest(db_path: str) -> DigestPayload:
    """Compose the digest payload from the same engines that power
    the dashboard. Single per-call _gather_per_deal scan threaded
    through every section — same perf pattern as the dashboard."""
    from ..ui.dashboard_page import (
        _all_insights, _since_yesterday_events,
    )
    from ..ui.portfolio_risk_scan_page import (
        _gather_per_deal, _priority_rank,
    )

    payload = DigestPayload(
        generated_at=datetime.now(timezone.utc).isoformat(),
    )

    try:
        deals = _gather_per_deal(db_path)
    except Exception:  # noqa: BLE001
        deals = []
    payload.portfolio_size = len(deals)

    # Headline insight
    insights = _all_insights(db_path, deals=deals)
    payload.headline_insight = insights[0] if insights else None

    # Top 3 needs-attention
    flagged = [(d, _priority_rank(d)) for d in deals]
    flagged = [(d, r) for d, r in flagged if r > 0]
    flagged.sort(key=lambda t: t[1], reverse=True)
    for d, priority in flagged[:3]:
        reasons: List[str] = []
        cov = _safe_status_str(d.get("covenant_status")).upper()
        if cov in ("TRIPPED", "TIGHT"):
            reasons.append(f"covenant {cov}")
        if (d.get("overdue_deadlines") or 0) > 0:
            reasons.append(
                f"{d['overdue_deadlines']} overdue deadline"
                f"{'s' if d['overdue_deadlines'] != 1 else ''}"
            )
        if (d.get("alerts") or 0) > 0:
            reasons.append(
                f"{d['alerts']} open alert"
                f"{'s' if d['alerts'] != 1 else ''}"
            )
        score = d.get("score")
        if isinstance(score, int) and score < 60:
            reasons.append(f"health score {score}")
        payload.needs_attention.append({
            "deal_id": d.get("deal_id"),
            "name": d.get("name"),
            "reasons": reasons,
            "priority": priority,
            "href": f"/deal/{d.get('deal_id')}",
        })

    # Top 3 predicted outcomes (watchlist deals)
    try:
        from ..deals.watchlist import list_starred
        from ..data_public.deals_corpus import DealsCorpus
        from ..diligence.comparable_outcomes import benchmark_deal
        from ..portfolio.store import PortfolioStore

        store = PortfolioStore(db_path)
        starred = list_starred(store)[:3]
        if starred:
            corpus = DealsCorpus(db_path)
            try:
                corpus.seed(skip_if_populated=True)
            except Exception:  # noqa: BLE001
                pass
            scan_by_id = {d.get("deal_id"): d for d in deals}
            for did in starred:
                scan_row = scan_by_id.get(did, {})
                target = {
                    "sector": scan_row.get("sector") or "hospital",
                    "ev_mm": None,
                    "year": 2024,
                    "buyer": "",
                }
                try:
                    result = benchmark_deal(corpus, target, top_n=10)
                except Exception:  # noqa: BLE001
                    continue
                outcome = result.get("outcome_distribution", {})
                moic = outcome.get("moic", {})
                if moic.get("median") is None:
                    continue
                payload.predicted_outcomes.append({
                    "deal_id": did,
                    "name": scan_row.get("name") or did,
                    "median_moic": moic.get("median"),
                    "p25_moic": moic.get("p25"),
                    "p75_moic": moic.get("p75"),
                    "win_rate": outcome.get("win_rate_2_5x"),
                    "n_comparables": outcome.get("n_comparables", 0),
                })
    except Exception:  # noqa: BLE001
        pass

    # Recent overnight events (last 24h, capped at 8)
    try:
        events = _since_yesterday_events(db_path, window_hours=24)[:8]
        payload.recent_events = events
    except Exception:  # noqa: BLE001
        pass

    return payload


# ── Renderers ─────────────────────────────────────────────────────

def _fmt_moic(v: Optional[float]) -> str:
    return f"{v:.2f}x" if v is not None else "—"


def _fmt_pct(v: Optional[float]) -> str:
    return f"{v * 100:.0f}%" if v is not None else "—"


def digest_to_text(payload: DigestPayload, *,
                   base_url: str = "") -> str:
    """Plain-text rendering — for SMS, fallback email body, or a
    terminal `rcm-mc digest` print. Easy to scan, no markup."""
    lines: List[str] = []
    today = (payload.generated_at or "")[:10]
    lines.append(f"=== RCM-MC morning digest · {today} ===")
    lines.append("")
    lines.append(f"Portfolio size: {payload.portfolio_size} active deals")
    lines.append("")

    if payload.headline_insight:
        ins = payload.headline_insight
        lines.append(f">>> {ins.get('headline', '')}")
        lines.append(f"    {ins.get('body', '')}")
        if ins.get("href"):
            lines.append(f"    → {base_url}{ins['href']}")
        lines.append("")

    if payload.needs_attention:
        lines.append("Needs attention today")
        lines.append("-" * 21)
        for d in payload.needs_attention:
            reasons = " · ".join(d.get("reasons") or [])
            lines.append(
                f"  · {d.get('name')} ({d.get('deal_id')})"
                f" — {reasons}"
            )
        lines.append("")

    if payload.predicted_outcomes:
        lines.append("Predicted exit outcomes (your watchlist)")
        lines.append("-" * 41)
        for d in payload.predicted_outcomes:
            lines.append(
                f"  · {d.get('name')} ({d.get('deal_id')})"
                f" — median {_fmt_moic(d.get('median_moic'))}"
                f" · p25 {_fmt_moic(d.get('p25_moic'))}"
                f" · p75 {_fmt_moic(d.get('p75_moic'))}"
                f" · {_fmt_pct(d.get('win_rate'))} clear 2.5x"
            )
        lines.append("")

    if payload.recent_events:
        lines.append("Last 24 hours")
        lines.append("-" * 13)
        for ev in payload.recent_events:
            ts = (ev.get("at") or "")[:16]
            lines.append(f"  {ts}  {ev.get('icon', '·')} "
                         f"{ev.get('label', '')}")
        lines.append("")

    return "\n".join(lines)


def digest_to_html(payload: DigestPayload, *,
                   base_url: str = "") -> str:
    """HTML email body — minimal CSS (inline only — most email
    clients strip <style> blocks), readable on Outlook + Gmail
    + Apple Mail."""
    today = (payload.generated_at or "")[:10]
    parts: List[str] = []

    parts.append(
        '<div style="font-family:-apple-system,BlinkMacSystemFont,'
        '\'Segoe UI\',Roboto,sans-serif;max-width:680px;margin:0 auto;'
        'color:#1f2937;line-height:1.5;">'
    )
    parts.append(
        f'<h1 style="font-size:20px;color:#0f172a;margin:0 0 4px;">'
        f'Morning digest · {_html.escape(today)}</h1>'
        f'<p style="color:#6b7280;margin:0 0 16px;font-size:13px;">'
        f'{payload.portfolio_size} active deals</p>'
    )

    # Headline insight as a tone-colored box
    if payload.headline_insight:
        ins = payload.headline_insight
        tone = ins.get("tone", "neutral")
        bg, fg = {
            "alert":    ("#fef2f2", "#991b1b"),
            "warn":     ("#fffbeb", "#92400e"),
            "positive": ("#f0fdf4", "#065f46"),
            "neutral":  ("#f0f6fc", "#1F4E78"),
        }.get(tone, ("#f0f6fc", "#1F4E78"))
        href = (base_url + (ins.get("href") or "#")) if base_url else ""
        link_open = (f'<a href="{_html.escape(href)}" '
                     f'style="color:{fg};text-decoration:none;">'
                     if href else "")
        link_close = "</a>" if href else ""
        parts.append(
            f'<div style="background:{bg};border-left:4px solid {fg};'
            f'padding:14px 18px;border-radius:6px;margin:12px 0;">'
            f'{link_open}'
            f'<div style="font-size:11px;text-transform:uppercase;'
            f'letter-spacing:0.08em;font-weight:600;color:{fg};'
            f'opacity:0.8;">Sharpest insight today</div>'
            f'<div style="font-size:16px;font-weight:600;color:{fg};'
            f'margin-top:4px;">{_html.escape(ins.get("headline", ""))}</div>'
            f'<div style="font-size:13px;color:{fg};margin-top:6px;'
            f'opacity:0.85;">{_html.escape(ins.get("body", ""))}</div>'
            f'{link_close}'
            f'</div>'
        )

    if payload.needs_attention:
        parts.append('<h2 style="font-size:14px;color:#0f172a;'
                     'margin:18px 0 8px;font-weight:600;'
                     'text-transform:uppercase;letter-spacing:0.04em;">'
                     'Needs attention</h2>')
        parts.append('<ul style="list-style:none;padding:0;margin:0;">')
        for d in payload.needs_attention:
            href = (base_url + (d.get("href") or "")) if base_url else ""
            link_open = (f'<a href="{_html.escape(href)}" '
                         f'style="color:#1F4E78;font-weight:500;'
                         f'text-decoration:none;">'
                         if href else
                         f'<span style="color:#1F4E78;font-weight:500;">')
            link_close = "</a>" if href else "</span>"
            reasons = " · ".join(
                _html.escape(r) for r in (d.get("reasons") or []))
            parts.append(
                f'<li style="padding:6px 0;border-bottom:1px solid #f3f4f6;">'
                f'{link_open}{_html.escape(d.get("name") or "")}'
                f'{link_close}'
                f' <span style="font-family:monospace;font-size:11px;'
                f'color:#6b7280;">{_html.escape(d.get("deal_id") or "")}</span>'
                f'<div style="font-size:12px;color:#6b7280;'
                f'margin-top:2px;">{reasons}</div>'
                f'</li>'
            )
        parts.append('</ul>')

    if payload.predicted_outcomes:
        parts.append('<h2 style="font-size:14px;color:#0f172a;'
                     'margin:18px 0 8px;font-weight:600;'
                     'text-transform:uppercase;letter-spacing:0.04em;">'
                     'Predicted exit outcomes (watchlist)</h2>')
        parts.append('<ul style="list-style:none;padding:0;margin:0;">')
        for d in payload.predicted_outcomes:
            parts.append(
                f'<li style="padding:6px 0;border-bottom:1px solid #f3f4f6;">'
                f'<span style="font-weight:500;">'
                f'{_html.escape(d.get("name") or "")}</span>'
                f' <span style="font-family:monospace;font-size:11px;'
                f'color:#6b7280;">{_html.escape(d.get("deal_id") or "")}</span>'
                f'<div style="font-size:12px;color:#374151;margin-top:2px;'
                f'font-variant-numeric:tabular-nums;">'
                f'<span style="color:#1F4E78;font-weight:600;">'
                f'{_fmt_moic(d.get("median_moic"))}</span> median · '
                f'p25 {_fmt_moic(d.get("p25_moic"))} · '
                f'p75 {_fmt_moic(d.get("p75_moic"))} · '
                f'{_fmt_pct(d.get("win_rate"))} clear 2.5x'
                f'</div>'
                f'</li>'
            )
        parts.append('</ul>')

    if payload.recent_events:
        parts.append('<h2 style="font-size:14px;color:#0f172a;'
                     'margin:18px 0 8px;font-weight:600;'
                     'text-transform:uppercase;letter-spacing:0.04em;">'
                     'Last 24 hours</h2>')
        parts.append('<ul style="list-style:none;padding:0;margin:0;'
                     'font-size:12px;">')
        for ev in payload.recent_events:
            ts = _html.escape((ev.get("at") or "")[:16])
            label = _html.escape(ev.get("label", ""))
            parts.append(
                f'<li style="padding:4px 0;color:#374151;">'
                f'<span style="color:#6b7280;font-family:monospace;'
                f'font-size:11px;margin-right:8px;">{ts}</span>'
                f'{label}</li>'
            )
        parts.append('</ul>')

    parts.append(
        '<p style="margin:24px 0 0;padding-top:12px;'
        'border-top:1px solid #e5e7eb;font-size:11px;color:#9ca3af;">'
        'Sent by RCM-MC. Reply to opt out, or update your '
        'preferences in /settings/integrations.</p>'
        '</div>'
    )
    return "".join(parts)


def send_morning_digest(
    db_path: str, recipient: str,
    *, base_url: str = "",
) -> bool:
    """Build the digest and email it. Returns True on send,
    False on no-op (SMTP not configured) or failure. Never raises."""
    from . import notifications
    payload = build_morning_digest(db_path)
    today = (payload.generated_at or "")[:10]
    subject = f"RCM-MC morning digest · {today}"
    if payload.headline_insight:
        subject += f" — {payload.headline_insight.get('headline', '')[:60]}"
    body_html = digest_to_html(payload, base_url=base_url)
    return notifications._send_email(recipient, subject, body_html)
