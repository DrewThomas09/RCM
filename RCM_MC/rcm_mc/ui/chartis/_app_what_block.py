"""WhatBlock — page-summary + sources block on the editorial /app.

Direct port of the WhatBlock component from cc-app.jsx (design handoff
reference). Two-column layout: large-serif page summary on the left,
compact "SOURCES" list on the right (mono, deeper-parchment surface).

CSS lives in static/v3/chartis.css under the WHAT/SOURCES BLOCK header.
"""
from __future__ import annotations

import html as _html
from typing import Sequence


def render_what_block(
    *,
    summary: str,
    sources: Sequence[str],
) -> str:
    """Render the WhatBlock + Sources two-column block.

    Args:
        summary: Single paragraph describing what the page does.
            Set in serif at 1.4rem, max-width 560px, dark-ink color.
        sources: Iterable of data-source names (table names, file paths,
            registry handles). Rendered as a mono bullet list.

    Returns:
        HTML string. The block is bordered-bottom by var(--rule) so it
        separates cleanly from the next section without explicit margin
        from the caller.
    """
    sources_html = "".join(
        f"<li>{_html.escape(str(src))}</li>"
        for src in sources
    )
    return (
        '<div class="info-grid">'
        '<div class="info-block">'
        '<div class="micro">WHAT THIS PAGE DOES</div>'
        f'<p>{_html.escape(summary)}</p>'
        '</div>'
        '<div class="sources-block">'
        '<div class="micro">SOURCES</div>'
        f'<ul>{sources_html}</ul>'
        '</div>'
        '</div>'
    )
