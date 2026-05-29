"""`/insights` — every cross-portfolio signal, ranked.

The dashboard's "Sharpest insight today" card surfaces only the
top-1 — fine for the morning glance, not enough when a partner
wants to walk through every signal the tool has flagged.

This page renders the full list of candidate insights from
``_all_insights()`` as a stack of color-tone cards, highest-priority
first, with a small explainer at the top of each tone group.

Public API:
    render_insights_page(db_path: str) -> str
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List


def render_insights_page(db_path: str) -> str:
    from . import _web_components as _wc
    from ._chartis_kit import chartis_shell, ck_page_title
    from .dashboard_page import _all_insights

    insights = _all_insights(db_path)

    header = ck_page_title(
        "All insights",
        eyebrow="PORTFOLIO · CROSS-DEAL SIGNALS",
        meta=(
            "Every cross-portfolio signal the tool can compute, "
            "ranked highest-priority first. The /dashboard card "
            "shows only the top one."
        ),
    )

    if not insights:
        from ._chartis_kit import ck_empty_state, ck_next_section
        body_html = (
            ck_empty_state(
                title="Quiet morning.",
                eyebrow="INSIGHTS",
                body=(
                    "No portfolio-wide signals firing right now. "
                    "When deals start flagging covenants, alerts "
                    "pile up, or chain concentration grows, the "
                    "cards will populate here."
                ),
                cta_label="Open the Monday brief",
                cta_href="/day-one",
            )
            + ck_next_section(
                "Open the v3 dashboard for the full data view",
                "/?v3=1",
                eyebrow="Continue —",
                italic_word="data",
            )
        )
        return chartis_shell(body_html, "All insights",
                             active_nav="/insights")

    # Tone palette — same as the dashboard headline card.
    palette = {
        "alert":    ("#fef2f2", "#f2ded7", "#8a2a1a", "⚠"),
        "warn":     ("#fffbeb", "#f2e7d1", "#7a4c16", "●"),
        "positive": ("#f0fdf4", "#d9ece2", "#0a6a48", "✓"),
        "neutral":  ("#f7f3ea", "#d0e3f0", "var(--sc-navy)", "◆"),
    }

    # Tone summary strip — count of insights per tone, so a partner
    # sees the shape of the day's signal mix at a glance.
    tone_counts: Dict[str, int] = {}
    for ins in insights:
        t = ins.get("tone", "neutral")
        tone_counts[t] = tone_counts.get(t, 0) + 1
    summary_chips: List[str] = []
    for tone in ("alert", "warn", "positive", "neutral"):
        n = tone_counts.get(tone, 0)
        if n == 0:
            continue
        bg, _, fg, icon = palette[tone]
        summary_chips.append(
            f'<span style="display:inline-flex;align-items:center;gap:6px;'
            f'padding:6px 12px;background:{bg};color:{fg};'
            f'border-radius:9999px;font-size:13px;font-weight:500;">'
            f'<span style="font-size:14px;">{icon}</span>'
            f'<span style="font-variant-numeric:tabular-nums;">{n}</span>'
            f'<span>{tone}</span></span>'
        )
    summary_strip = (
        '<div style="display:flex;gap:10px;flex-wrap:wrap;margin:12px 0 20px;">'
        + "".join(summary_chips) +
        '</div>'
    )

    # Render each insight as a full-width tone-colored card. Same
    # visual language as the dashboard headline so the partner reads
    # the page like a continuation of the morning view.
    cards: List[str] = []
    for i, ins in enumerate(insights):
        tone = ins.get("tone", "neutral")
        bg, border, fg, icon = palette.get(tone, palette["neutral"])
        href = ins.get("href") or "#"
        kind = ins.get("kind", "")
        rank_chip = (
            f'<span style="display:inline-block;padding:1px 8px;'
            f'background:rgba(0,0,0,0.05);color:{fg};border-radius:9999px;'
            f'font-size:10px;font-weight:600;font-variant-numeric:tabular-nums;'
            f'letter-spacing:0.04em;">#{i+1}</span>'
        )
        kind_chip = (
            f'<span style="display:inline-block;padding:1px 8px;'
            f'background:rgba(0,0,0,0.05);color:{fg};border-radius:9999px;'
            f'font-size:10px;font-family:monospace;'
            f'text-transform:uppercase;letter-spacing:0.05em;">'
            f'{_html.escape(kind)}</span>'
        )
        score_chip = (
            f'<span style="font-size:10px;color:{fg};opacity:0.65;'
            f'font-variant-numeric:tabular-nums;font-family:monospace;">'
            f'priority {int(ins.get("score", 0))}</span>'
        )

        cards.append(
            # 2026-05-28 batch 40 · Tier-4 trope removal — cap radius
            # at 2px. Semantic per-insight severity (border-left {fg})
            # preserved — it carries meaning.
            f'<a href="{_html.escape(href)}" '
            f'style="display:block;text-decoration:none;'
            f'margin:0 0 12px;padding:18px 22px;background:{bg};'
            f'border:1px solid {border};border-left:4px solid {fg};'
            f'border-radius:2px;color:{fg};'
            f'transition:transform 0.1s, border-color 0.1s;" '
            f'onmouseover="this.style.transform=\'translateX(2px)\';" '
            f'onmouseout="this.style.transform=\'\';">'
            f'<div style="display:flex;align-items:center;gap:8px;'
            f'margin-bottom:6px;flex-wrap:wrap;">'
            f'{rank_chip}{kind_chip}'
            f'<span style="flex:1;"></span>'
            f'{score_chip}'
            f'</div>'
            f'<div style="display:flex;align-items:baseline;gap:12px;">'
            f'<span style="font-size:20px;flex-shrink:0;">{icon}</span>'
            f'<div style="flex:1;">'
            f'<div style="font-size:16px;font-weight:600;color:{fg};">'
            f'{_html.escape(ins.get("headline", ""))}</div>'
            f'<div style="font-size:13px;margin-top:6px;opacity:0.85;">'
            f'{_html.escape(ins.get("body", ""))}</div>'
            f'</div>'
            f'<span style="flex-shrink:0;opacity:0.5;font-size:18px;">→</span>'
            f'</div></a>'
        )

    inner = (
        header
        + summary_strip
        + "".join(cards)
    )
    from ._chartis_kit import ck_next_section
    next_up = ck_next_section(
        "Open the day-one Monday brief",
        "/day-one",
        eyebrow="Continue —",
        italic_word="day",
    )
    body = (
        _wc.web_styles()
        + _wc.responsive_container(inner)
        + next_up
    )
    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from ._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(
        body, "All insights", active_nav="/insights",
        editorial_intro={
            "eyebrow": "INSIGHTS",
            "headline": "What the platform noticed that you didn't ask.",
            "italic_word": "noticed",
        },
    )
