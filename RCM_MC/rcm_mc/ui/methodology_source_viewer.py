"""Methodology source-code viewer — ``/methodology/<module>``.

PROMPTS.md Phase 5 / Prompt 63: partners can't see how a number was
computed. This route renders the source of the platform's
analytical modules in-browser so the methodology link on each
analytical page leads somewhere real, not to a marketing page.

A whitelist constrains which files can be served — this is not a
``/etc/passwd`` viewer; it's a curated set of modules that
materially drive the platform's outputs. Modules outside the list
return 404. The relative paths are computed at render time so a
refactor that moves a file leaves the registry pointing at the new
location (caller updates the path).

Lives alongside the existing ``methodology_page.py`` (which renders
partner-facing prose explanations); both are reachable via
``/methodology`` and ``/methodology/<key>`` respectively.
"""
from __future__ import annotations

import html as _html
import os
from typing import Optional


# Methodology registry: short key → (module path, partner-facing label).
# Keep paths relative to the repo root.
METHODOLOGY_MODULES: dict[str, dict[str, str]] = {
    "pe_math": {
        "path": "rcm_mc/pe/pe_math.py",
        "label": "PE-math (bridge / MOIC / IRR / covenant headroom)",
    },
    "simulator": {
        "path": "rcm_mc/core/simulator.py",
        "label": "Monte Carlo simulator (per-deal value-creation paths)",
    },
    "rcm_ebitda_bridge": {
        "path": "rcm_mc/pe/rcm_ebitda_bridge.py",
        "label": "RCM EBITDA bridge — 7-lever decomposition",
    },
    "ebitda_mc": {
        "path": "rcm_mc/mc/ebitda_mc.py",
        "label": "EBITDA Monte Carlo — two-source distribution",
    },
    "ridge_predictor": {
        "path": "rcm_mc/ml/ridge_predictor.py",
        "label": "Ridge regression predictor",
    },
    "conformal": {
        "path": "rcm_mc/ml/conformal.py",
        "label": "Conformal prediction intervals (P10/P90 bands)",
    },
    "health_score": {
        "path": "rcm_mc/deals/health_score.py",
        "label": "Health score (composite 0-100 per deal)",
    },
}


def _resolve_path(rel_path: str) -> Optional[str]:
    """Compute an absolute path under the ``rcm_mc`` package root,
    refusing any traversal outside it. Returns None when the file
    doesn't exist or escapes the package root."""
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # ``here`` is the package root (rcm_mc/). The rel_path is from
    # the *parent* of the package, e.g. "rcm_mc/pe_math.py", so we
    # join against ``here``'s parent.
    repo_root = os.path.dirname(here)
    candidate = os.path.normpath(os.path.join(repo_root, rel_path))
    # Refuse anything that escapes the package directory.
    if not candidate.startswith(here):
        return None
    if not os.path.isfile(candidate):
        return None
    return candidate


def render_methodology_module(module_key: str) -> Optional[str]:
    """Render a methodology source-code page, or None if the key is
    unknown. The caller (server.py) maps None to a 404."""
    from ._chartis_kit import chartis_shell

    spec = METHODOLOGY_MODULES.get(module_key)
    if not spec:
        return None
    abs_path = _resolve_path(spec["path"])
    if not abs_path:
        return None
    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            source = f.read()
    except OSError:
        return None
    body = (
        '<h1 class="page-title">Methodology</h1>'
        f'<div class="page-subtitle">{_html.escape(spec["label"])} · '
        f'<code>{_html.escape(spec["path"])}</code></div>'
        '<p class="muted" style="font-family:var(--sc-mono);font-size:11px;'
        'margin:8px 0 16px;">'
        'No other PE tool ships its model code as documentation. '
        'Read the source the platform actually runs.'
        '</p>'
        '<pre class="methodology-source">'
        f'{_html.escape(source)}'
        '</pre>'
        '<style>'
        '.methodology-source { background:var(--sc-bone); padding:18px 22px; '
        'font-family:var(--sc-mono); font-size:12px; line-height:1.55; '
        'color:var(--sc-text); border:1px solid var(--sc-rule); '
        'overflow-x:auto; max-width:1080px; }'
        '</style>'
    )
    return chartis_shell(body, f"Methodology — {spec['label']}",
                         active_nav="/methodology")
