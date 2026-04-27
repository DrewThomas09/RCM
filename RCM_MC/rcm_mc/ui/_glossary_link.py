"""Shared anchor-link helper for /metric-glossary references.

Phase 4A of the v3 transformation campaign requires that every
page mentioning a metric link to ``/metric-glossary#<key>``.
The destination page lives at ``ui/metric_glossary_page.py``
(loop 104). This module provides one helper used by every
caller that wants to wrap a metric's display label in an
anchor link to its canonical glossary card.

Why a shared helper:
  - Single source of truth for the link visual (dotted
    underline, color:inherit) so the look is consistent
    across the bridge, data room, hospital profile, and any
    future page that adopts metric→glossary linking.
  - Single place to handle key aliasing (e.g., the bridge's
    short ``cmi`` mapping to the glossary's ``case_mix_
    index``) so the alias table doesn't get duplicated.
  - Single place to handle the "unknown metric" fallthrough
    so we never ship a dead anchor.

Public API:
    metric_label_link(label, metric_key, *, alias=None) -> str
"""
from __future__ import annotations

import html as _html
from typing import Mapping, Optional


def metric_label_link(
    label: str,
    metric_key: str,
    *,
    alias: Optional[Mapping[str, str]] = None,
) -> str:
    """Wrap a metric's display label in an anchor link to
    /metric-glossary#<resolved_key>.

    Args:
        label: User-visible metric label (e.g., "Denial Rate
            Reduction"). Will be HTML-escaped.
        metric_key: Canonical metric key as known to the
            caller (e.g., "denial_rate", or the bridge's
            short "cmi"). Will be HTML-escaped if it survives
            the alias and glossary lookup.
        alias: Optional mapping from caller-local keys to
            glossary keys. Use this when the caller stores a
            short or shadowed name (e.g., the bridge has
            "cmi"; the glossary has "case_mix_index").

    Returns:
        HTML string. If the resolved key exists in the
        metric_glossary registry, returns an `<a href=...>`
        anchor with a dotted underline. Otherwise returns
        plain escaped label text — no dead links shipped.
    """
    from .metric_glossary import get_metric_definition

    resolved = (alias or {}).get(metric_key, metric_key)
    if not resolved or get_metric_definition(resolved) is None:
        return _html.escape(label)
    return (
        f'<a href="/metric-glossary#{_html.escape(resolved)}" '
        f'style="color:inherit;text-decoration:none;'
        f'border-bottom:1px dotted var(--cad-text3);">'
        f'{_html.escape(label)}</a>'
    )
