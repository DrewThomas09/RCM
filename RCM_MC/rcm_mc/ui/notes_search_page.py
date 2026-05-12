"""Notes Search page — /notes.

Editorial port of the legacy `_route_notes_search` inline renderer
to the chartis.com Insights triplet pattern: search hero (italic
"Search" navy panel) + filter sidebar (BY TAG eyebrow rail with
multi-checkbox tag selection) + results header (count + active-tag
chips + Clear all). Mirrors the same shape as `/library`.

The legacy `deal_id` filter is preserved through hidden inputs in
both forms so partner navigation from a deal page (e.g. clicking a
note pill that links here with `?deal_id=…`) still scopes results
correctly. Server-side search + tag-AND semantics unchanged — this
file only changes the chrome.
"""
from __future__ import annotations

import html as _html
import re
import urllib.parse
from typing import Any, Dict, List, Optional


def _highlight_query(body: str, query: str) -> str:
    """Wrap query matches in a <mark> for partner skim. Case-insensitive."""
    esc = _html.escape(body)
    if not query:
        return esc
    try:
        return re.sub(
            "(" + re.escape(_html.escape(query)) + ")",
            r'<mark class="ck-mark">\1</mark>',
            esc, flags=re.IGNORECASE,
        )
    except re.error:
        return esc


def _build_url(
    *,
    base: str = "/notes",
    q: str = "",
    deal_id: str = "",
    tags: Optional[List[str]] = None,
) -> str:
    """Reconstruct /notes?... from a target state. Empty values omitted."""
    pairs: List[tuple] = []
    if q:
        pairs.append(("q", q))
    if deal_id:
        pairs.append(("deal_id", deal_id))
    if tags:
        pairs.append(("tags", " ".join(tags)))
    if not pairs:
        return base
    return base + "?" + urllib.parse.urlencode(pairs)


def render_notes_search(
    *,
    store: Any,
    q: str = "",
    deal_id: str = "",
    tags_raw: str = "",
) -> str:
    """Render /notes via the cycle-18 Insights-triplet helper.

    ``tags_raw`` is the space-separated tag string from the URL —
    we split, dedupe, and use AND semantics against the data layer
    via the existing ``search_notes`` helper.

    The tags facet is multi-select: the URL state carries a
    space-separated string but each tag chip drops independently.
    The helper's auto-chip-builder can't know how to drop one tag
    from a list-valued URL, so we omit ``tags`` from auto-chips and
    pass the per-tag chips via ``extra_chips``. Everything else
    (search hero, filter sidebar, results header, deal_id chip,
    keyword chip, Clear all, intro) the helper builds for free.
    """
    from rcm_mc.ui._chartis_kit import (
        ck_next_section, ck_provenance_tooltip, render_insights_page,
    )
    from rcm_mc.deals.deal_notes import search_notes
    from rcm_mc.deals.note_tags import tags_for_notes, all_note_tags

    active_tags = [t for t in tags_raw.split() if t]

    # Run the search early so the count is available to the results
    # header. Tag-validation errors come back as ValueError; surface
    # those inline instead of 500ing the page.
    df = None
    tag_err: Optional[str] = None
    try:
        df = search_notes(store, q, deal_id=deal_id or None,
                          tags=active_tags or None)
    except ValueError as exc:
        tag_err = str(exc)

    # All known tags for the filter sidebar (most-used first).
    try:
        known_tags = all_note_tags(store)
    except Exception:
        known_tags = []
    tag_options: List[Dict[str, Any]] = [
        {
            "label": f"{tag} ({count})",
            "value": tag,
            "checked": tag in active_tags,
        }
        for tag, count in known_tags
    ]

    # Per-tag remove chips: each drops just that tag, preserving
    # the others.
    extra_chips: List[Dict[str, str]] = []
    for tag in active_tags:
        remaining = [t for t in active_tags if t != tag]
        extra_chips.append({
            "label": tag,
            "remove_href": _build_url(
                q=q, deal_id=deal_id, tags=remaining,
            ),
        })

    # Results body — mirrors the legacy list shape but with editorial
    # tokens. Empty / no-query / error states each render their own
    # affirmative band so the partner never sees a void.
    if tag_err:
        results_body = (
            '<div class="ck-affirm-empty" style="border-left-color:var(--sc-warning);">'
            '<h3 style="color:var(--sc-warning);">Tag rejected</h3>'
            f'<p>{_html.escape(tag_err)}</p>'
            '</div>'
        )
    elif df is None or df.empty:
        if not q and not active_tags and not deal_id:
            results_body = (
                '<div class="ck-affirm-empty" style="border-left-color:var(--sc-teal);">'
                '<h3 style="color:var(--sc-teal-ink);">Start typing to search notes</h3>'
                '<p>Searches are case-insensitive and match any substring of '
                'the note body. Pick one or more tags from the filter rail '
                'for AND-semantics scoping, or follow a deal-page link to '
                'narrow to a single deal.</p>'
                '</div>'
            )
        else:
            results_body = (
                '<div class="ck-affirm-empty">'
                '<h3>No notes match.</h3>'
                '<p>Drop a filter from the chip row, or broaden the keyword '
                'and try again.</p>'
                '</div>'
            )
    else:
        # Notes list — one row per note, each with deal anchor +
        # timestamp + author + tag pills + highlighted body.
        note_ids = [int(r["note_id"]) for _, r in df.iterrows()]
        try:
            tags_map = tags_for_notes(store, note_ids)
        except Exception:
            tags_map = {}

        rows_html = []
        for _, r in df.iterrows():
            note_id = int(r["note_id"])
            author = str(r.get("author") or "—")
            d_id = str(r["deal_id"])
            d_id_q = urllib.parse.quote(d_id)
            ts = str(r["created_at"])[:19]
            pills = "".join(
                f'<a class="ck-chip" '
                f'href="/notes?tags={urllib.parse.quote(t)}">{_html.escape(t)}</a>'
                for t in tags_map.get(note_id, [])
            )
            author_html = (
                f' · <span class="ck-note-author">{_html.escape(author)}</span>'
                if author != "—" else ""
            )
            rows_html.append(
                '<li class="ck-note-row">'
                '<div class="ck-note-meta">'
                f'<a class="ck-note-deal" href="/deal/{d_id_q}">'
                f'{_html.escape(d_id)}</a>'
                f'<span class="ck-note-ts">{_html.escape(ts)}</span>'
                f'{author_html}'
                f'<span class="ck-note-pills">{pills}</span>'
                '</div>'
                f'<div class="ck-note-body">{_highlight_query(str(r["body"]), q)}</div>'
                '</li>'
            )
        results_body = (
            '<ul class="ck-note-list">'
            + "".join(rows_html)
            + '</ul>'
        )

    count = 0 if df is None else len(df)

    facets = (
        [{
            "title": "By tag",
            "name": "tags",
            "input_type": "checkbox",
            "options": tag_options,
        }] if tag_options else []
    )

    # Cycle 35 — wrap the result count with an explainer so partners
    # see the search semantics (case-insensitive substring + AND-tag
    # scoping) without leaving the page.
    count_display = ck_provenance_tooltip(
        "Note search",
        f"{count:,}",
        explainer=(
            "Case-insensitive substring match against note bodies. "
            "Tag filters AND together (a note must carry every "
            "selected tag). Soft-deleted notes are excluded."
        ),
    )
    return render_insights_page(
        action="/notes",
        state={"q": q, "deal_id": deal_id, "tags": tags_raw},
        facets=facets,
        count=count_display,
        count_label="Notes" if count != 1 else "Note",
        body_html=results_body,
        title="Notes Search",
        active_nav="research",
        keyword_placeholder="Note text…",
        section_title="Full-text search across deal notes",
        section_eyebrow="NOTES",
        intro={
            "eyebrow": "NOTES SEARCH",
            "headline": "Where the analyst voice finds its archive.",
            "italic_word": "finds",
            "body": (
                "Full-text search across every deal note in the "
                "portfolio, scoped by tag or by deal. Note bodies "
                "render with case-insensitive keyword highlighting "
                "in the results below."
            ),
        },
        chip_label_overrides={
            "deal_id": lambda v: f"deal: {v}",
        },
        # Tags are multi-value — the helper can't auto-build chips
        # for them. ``extra_chips`` adds one chip per active tag,
        # each dropping just that tag from the URL.
        omit_auto_chips=("tags",),
        extra_chips=extra_chips,
        subtitle=(
            f'{count:,} match{"es" if count != 1 else ""}'
            + (f' for "{q}"' if q else "")
        ),
        next_section_html=ck_next_section(
            "Open the portfolio-wide question ledger",
            "/diligence/questions",
            eyebrow="Continue —",
            italic_word="question",
        ),
    )
