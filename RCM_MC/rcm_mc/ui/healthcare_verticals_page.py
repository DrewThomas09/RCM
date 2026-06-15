"""Library reference page: US Healthcare Verticals.

GET /healthcare-verticals renders ``RCM_MC/docs/HEALTHCARE_VERTICALS_REFERENCE.md``
— the granular per-vertical operational/clinical/epidemiological reference
(code fingerprints, payment systems, facility/workforce counts, access,
benchmarks, data sources) — inside ``chartis_shell`` so partners can read it
in-app instead of opening the markdown file.

Exempt from the DealAnalysisPacket invariant for the same reason as
``/v3-status`` and ``/methodology``: this is static domain-reference content,
not analytical output about a specific deal. The page reads the vendored
markdown at request time (cheap, ~hundreds of KB) and converts the limited
markdown subset the document uses — ATX headings, ``**bold**``, ``-`` bullets,
and numbered lists — into editorial HTML. No network, no DB.
"""
from __future__ import annotations

import html as _html
import re
from datetime import datetime, timezone
from pathlib import Path

from ._chartis_kit import (
    chartis_shell,
    ck_editorial_head,
    ck_page_actions,
)

# parents[2] is the RCM_MC package root (ui → rcm_mc → RCM_MC); the
# reference markdown is vendored under RCM_MC/docs/, not the repo-root docs/.
PACKAGE_ROOT = Path(__file__).resolve().parents[2]
DOC_PATH = PACKAGE_ROOT / "docs" / "HEALTHCARE_VERTICALS_REFERENCE.md"

# Inline span formatting: **bold** → <strong>. Applied AFTER html-escape, so
# the regex operates on escaped text and only the literal ** markers remain.
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")


def _inline(text: str) -> str:
    """Escape a line then promote ``**bold**`` runs to <strong>.

    The source document uses inline bold heavily (metric callouts, vertical
    names). Escaping first keeps any ``<>&`` in code fingerprints literal;
    the bold pass then runs on the safe, escaped string.
    """
    escaped = _html.escape(text)
    return _BOLD_RE.sub(r"<strong>\1</strong>", escaped)


def _md_to_html(md: str) -> str:
    """Convert the document's markdown subset to editorial HTML.

    Deliberately small — the reference uses only ATX headings (H1 through H6),
    unordered ``-`` bullets, ``1.`` ordered items, and bold/plain paragraphs.
    A full markdown engine would be a new runtime dependency (forbidden) for
    no gain, so we handle exactly the constructs present.
    """
    lines = md.splitlines()
    out: list[str] = []
    # list_kind tracks an open <ul>/<ol> so consecutive items group and we
    # close the block when a non-item line arrives.
    list_kind: str | None = None

    def _close_list() -> None:
        nonlocal list_kind
        if list_kind is not None:
            out.append(f"</{list_kind}>")
            list_kind = None

    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()

        if not stripped:
            _close_list()
            continue

        # Headings — count leading '#'. The document's single H1 is the page
        # title (rendered by the editorial head), so demote it to an H2-level
        # section break to avoid two <h1>s competing in the shell.
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            _close_list()
            level = len(m.group(1))
            tag = "h2" if level <= 2 else f"h{min(level, 6)}"
            out.append(f"<{tag}>{_inline(m.group(2))}</{tag}>")
            continue

        # Ordered list item ("1. ", "2. ", …)
        m = re.match(r"^\d+\.\s+(.*)$", stripped)
        if m:
            if list_kind != "ol":
                _close_list()
                out.append('<ol class="ck-prose-list">')
                list_kind = "ol"
            out.append(f"<li>{_inline(m.group(1))}</li>")
            continue

        # Unordered list item ("- ")
        if stripped.startswith("- "):
            if list_kind != "ul":
                _close_list()
                out.append('<ul class="ck-prose-list">')
                list_kind = "ul"
            out.append(f"<li>{_inline(stripped[2:])}</li>")
            continue

        # Plain paragraph.
        _close_list()
        out.append(f"<p>{_inline(stripped)}</p>")

    _close_list()
    return "\n".join(out)


# Section anchors surfaced as a quick-jump rail. Mirrors the document's three
# top-level groupings so a partner can land on the vertical family they need.
_JUMP_SECTIONS = (
    ("PHYSICIAN SPECIALTIES / PRACTICE TYPES", "physician-specialties-practice-types"),
    ("FACILITY & SITE TYPES", "facility-site-types"),
    ("OTHER HEALTHCARE SERVICE TYPES", "other-healthcare-service-types"),
)


def render_healthcare_verticals() -> str:
    """GET /healthcare-verticals — full HTML via chartis_shell."""
    if not DOC_PATH.is_file():
        body = (
            '<section style="max-width:62rem;">'
            "<h2>Reference missing</h2>"
            "<p><code>docs/HEALTHCARE_VERTICALS_REFERENCE.md</code> is not "
            "present in this deployment. It ships with the repository under "
            "<code>RCM_MC/docs/</code>.</p>"
            "</section>"
        )
        return chartis_shell(
            body,
            "Healthcare Verticals — Reference Missing",
            active_nav="library",
            subtitle="library · reference",
        )

    md = DOC_PATH.read_text(encoding="utf-8")
    mtime = datetime.fromtimestamp(DOC_PATH.stat().st_mtime, tz=timezone.utc)

    # Drop the document's own H1 (the editorial head renders the title) and
    # the leading scope-note / TL;DR is kept as body prose.
    body_md = re.sub(r"^#\s+.*\n", "", md, count=1)
    article = _md_to_html(body_md)

    # Count the verticals (#### headings) for the meta strip — a real count
    # from the source, per the editorial-head convention (never hard-coded).
    vertical_count = len(re.findall(r"^####\s+", md, flags=re.MULTILINE))

    head = ck_editorial_head(
        eyebrow="LIBRARY · DOMAIN REFERENCE",
        title="US Healthcare Verticals",
        meta=(
            f"{vertical_count} VERTICALS · "
            "CPT/HCPCS · ICD-10 · DRG · CDT · NUCC TAXONOMY · "
            f"UPDATED {mtime.date().isoformat()}"
        ),
        lede_italic_phrase=(
            "A granular operational, clinical, and epidemiological reference "
            "for every US healthcare vertical"
        ),
        lede_body=(
            " — each profiled across its code fingerprint, patient "
            "epidemiology, provider/facility/workforce counts, geographic "
            "access, operational benchmarks, governing payment system, and "
            "primary data sources. Operational reference, not an investment "
            "document."
        ),
        source_note=(
            "SOURCES: CMS · CDC · HRSA · AAMC · SEER · USRDS · "
            "SAMHSA · ADA HPI · BLS · MEDPAC"
        ),
    )

    jump = (
        '<nav class="ck-jump-rail" aria-label="Jump to vertical family" '
        'style="margin:1.25rem 0;display:flex;flex-wrap:wrap;gap:.5rem;">'
        + "".join(
            f'<a href="#{anchor}" class="ck-chip" '
            f'style="font-family:var(--font-mono,monospace);font-size:.7rem;'
            f'text-transform:uppercase;letter-spacing:.04em;padding:.3rem .6rem;'
            f'border:1px solid var(--rule,#d8d0c2);border-radius:4px;'
            f'text-decoration:none;">{_html.escape(label)}</a>'
            for label, anchor in _JUMP_SECTIONS
        )
        + "</nav>"
    )

    # Slug the three group headings so the jump rail anchors resolve. The
    # group headings are H3 in the source (### …) → h3 after conversion.
    for label, anchor in _JUMP_SECTIONS:
        article = article.replace(
            f"<h3>{_html.escape(label)}</h3>",
            f'<h3 id="{anchor}">{_html.escape(label)}</h3>',
        )

    body = (
        head
        + jump
        + f'<section class="prose" style="max-width:62rem;">{article}</section>'
        + ck_page_actions()
    )

    return chartis_shell(
        body,
        "US Healthcare Verticals",
        active_nav="library",
        subtitle="library · domain reference",
    )
