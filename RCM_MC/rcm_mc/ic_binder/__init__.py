"""IC binder — render a SynthesisResult into partner-ready artefacts.

The capstone over the 13-packet stack. Takes a SynthesisResult
(produced by ``rcm_mc.diligence_synthesis.run_full_diligence``)
and emits two artefacts a partner can drop straight into the
Sunday-night IC prep:

  • A markdown binder (paste into Notion / Confluence / Word /
    the email body of an IC pre-read)
  • A standalone HTML page (open in a browser, print to PDF for
    the physical binder)

The binder lays out every section that ran, in a fixed canonical
order, with each section's headline + supporting detail. Skipped
sections are listed in a "Data gaps" appendix so the partner
sees exactly what's still needed for the next iteration.

Public API::

    from rcm_mc.ic_binder import (
        render_markdown_binder,
        render_html_binder,
    )
"""
from .markdown import render_markdown_binder
from .html import render_html_binder

__all__ = [
    "render_markdown_binder",
    "render_html_binder",
]
