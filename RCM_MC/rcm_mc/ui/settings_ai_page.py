"""Settings → AI Assistant (Local Ollama) page.

Surfaces the status of the Anthropic Claude integration that backs
the AI-assist features:

  - Presence of ``ANTHROPIC_API_KEY``
  - Default model id (with latest Claude 4 line)
  - Recent call volume + cost totals from the ``llm_calls`` table
  - Which platform features use Claude today
  - Copy-paste snippet for setting the key locally
"""
from __future__ import annotations

import html as _html
import os
from typing import Any, Dict, List, Optional

from ._chartis_kit import (
    P,
    chartis_shell,
    ck_kpi_block,
    ck_next_section,
    ck_panel,
    ck_section_header,
)


def _related_views(items: List[tuple]) -> str:
    links = " · ".join(
        f'<a class="ck-link" href="{_html.escape(u)}">{_html.escape(l)}</a>'
        for l, u in items
    )
    return ck_panel(
        f'<p class="ck-section-body">{links}</p>',
        title="Related views",
    )


# Latest Claude model ids as of Anthropic's current lineup. The
# llm_client picks one of these via ANTHROPIC_DEFAULT_MODEL env var
# or falls back to sonnet for most calls.
_CLAUDE_MODELS = [
    ("claude-opus-4-7",            "Opus 4.7",   "Highest-capability; deep reasoning."),
    ("claude-sonnet-4-6",          "Sonnet 4.6", "Balanced cost / quality. Default."),
    ("claude-haiku-4-5-20251001",  "Haiku 4.5",  "Fast / cheap. Good for bulk fact-checking."),
]


def _env_key_fingerprint() -> str:
    """Return a non-secret fingerprint of the configured key for
    display — first 8 chars + last 4 — so ops can confirm the key
    is the one they expect without leaking it.
    """
    key = os.environ.get("ANTHROPIC_API_KEY") or ""
    if not key:
        return ""
    if len(key) <= 12:
        return key[:3] + "…" + key[-2:]
    return f"{key[:8]}…{key[-4:]}"


def _call_stats(store: Any) -> Dict[str, Any]:
    """Pull rolled-up stats from the llm_calls + llm_response_cache
    tables. Safe no-op if the tables aren't created yet (fresh db)."""
    stats = {"total_calls": 0, "total_cost": 0.0, "by_model": [], "cached_hits": 0}
    try:
        with store.connect() as con:
            row = con.execute(
                "SELECT COUNT(*) AS n, "
                "COALESCE(SUM(cost_usd_estimate),0) AS cost "
                "FROM llm_calls"
            ).fetchone()
            if row:
                stats["total_calls"] = int(row["n"] or 0)
                stats["total_cost"] = float(row["cost"] or 0.0)
            model_rows = con.execute(
                "SELECT model, COUNT(*) AS n, "
                "COALESCE(SUM(cost_usd_estimate),0) AS cost "
                "FROM llm_calls GROUP BY model ORDER BY n DESC"
            ).fetchall()
            for r in model_rows:
                stats["by_model"].append({
                    "model": r["model"],
                    "calls": int(r["n"] or 0),
                    "cost": float(r["cost"] or 0.0),
                })
            try:
                c = con.execute(
                    "SELECT COUNT(*) AS n FROM llm_response_cache"
                ).fetchone()
                stats["cached_hits"] = int(c["n"] or 0) if c else 0
            except Exception:
                pass
    except Exception:
        pass
    return stats


def _features_card() -> str:
    items = [
        ("Partner review confirmation",
         "/deal/&lt;id&gt;/partner-review",
         "Runs a cached Claude second-pass over the PE verdict so the UI "
         "can show a concise confirm / watch-items summary."),
        ("IC Memo drafting",
         "/api/deals/&lt;id&gt;/memo?llm=1",
         "Generates the memo narrative sections with fact-checking "
         "against packet dollar amounts and percentages."),
        ("Document Q&amp;A",
         "/api/deals/&lt;id&gt;/qa?q=…",
         "Search indexed deal documents and return answers with "
         "confidence scores."),
        ("Multi-turn chat",
         "POST /api/chat",
         "Conversational interface with tool-calling — asks the "
         "platform for portfolio data and synthesizes answers."),
    ]
    rows = "".join(
        f'<tr>'
        f'<td style="padding:6px 10px;color:{P["text"]};font-weight:600;font-size:11.5px;">{lbl}</td>'
        f'<td style="padding:6px 10px;font-family:var(--ck-mono);font-size:10.5px;color:{P["accent"]};">{endpoint}</td>'
        f'<td style="padding:6px 10px;color:{P["text_dim"]};font-size:11px;line-height:1.5;">{desc}</td>'
        f'</tr>'
        for (lbl, endpoint, desc) in items
    )
    return (
        f'<div style="background:{P["panel"]};border:1px solid {P["border"]};'
        f'border-radius:3px;padding:14px 16px;">'
        f'<div style="font-family:var(--ck-mono);font-size:10px;'
        f'letter-spacing:0.12em;color:{P["text_faint"]};margin-bottom:10px;">'
        f'FEATURES THAT USE CLAUDE</div>'
        f'<table class="ck-table">'
        f'<thead><tr>'
        f'<th style="text-align:left;">Feature</th>'
        f'<th style="text-align:left;">Endpoint</th>'
        f'<th style="text-align:left;">What it does</th>'
        f'</tr></thead>'
        f'<tbody>{rows}</tbody></table>'
        f'<div style="color:{P["text_faint"]};font-size:10.5px;margin-top:10px;'
        f'line-height:1.55;">'
        f'Every feature falls back to a non-LLM template when the key '
        f'is not set, so the platform keeps working — just without '
        f'synthesized prose.</div>'
        f'</div>'
    )


def _models_table(active_id: Optional[str]) -> str:
    rows = []
    for mid, label, note in _CLAUDE_MODELS:
        is_default = (mid == "claude-sonnet-4-6")
        tag = (
            f'<span class="ck-chip ck-chip-active" style="margin-left:6px;">DEFAULT</span>'
            if is_default else ""
        )
        rows.append(
            f'<tr>'
            f'<td style="padding:6px 10px;font-family:var(--ck-mono);'
            f'font-size:11px;color:{P["text"]};">{_html.escape(mid)}{tag}</td>'
            f'<td style="padding:6px 10px;color:{P["text"]};font-weight:600;'
            f'font-size:11.5px;">{_html.escape(label)}</td>'
            f'<td style="padding:6px 10px;color:{P["text_dim"]};'
            f'font-size:11px;line-height:1.5;">{_html.escape(note)}</td>'
            f'</tr>'
        )
    return (
        f'<div style="background:{P["panel"]};border:1px solid {P["border"]};'
        f'border-radius:3px;padding:14px 16px;">'
        f'<div style="font-family:var(--ck-mono);font-size:10px;'
        f'letter-spacing:0.12em;color:{P["text_faint"]};margin-bottom:10px;">'
        f'AVAILABLE MODELS</div>'
        f'<table class="ck-table"><thead><tr>'
        f'<th style="text-align:left;">Model ID</th>'
        f'<th style="text-align:left;">Name</th>'
        f'<th style="text-align:left;">Notes</th>'
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table>'
        f'<div style="color:{P["text_faint"]};font-size:10.5px;margin-top:10px;'
        f'line-height:1.55;">'
        f'Override per-feature via the ``model`` kwarg on '
        f'<code style="color:{P["accent"]};">LLMClient.generate()</code> '
        f'or set the <code style="color:{P["accent"]};">'
        f'ANTHROPIC_DEFAULT_MODEL</code> env var.</div>'
        f'</div>'
    )


def _setup_instructions() -> str:
    # 2026-05-28 batch 31 · Tier-4 trope removal — drops decorative
    # 3px accent stripe; caps radius at 2px.
    return (
        f'<div style="background:{P["panel"]};border:1px solid {P["border"]};'
        f'border-radius:2px;'
        f'padding:14px 16px;">'
        f'<div style="font-family:var(--ck-mono);font-size:10px;'
        f'letter-spacing:0.12em;color:{P["text_faint"]};margin-bottom:10px;">'
        f'HOW TO CONNECT</div>'
        f'<ol style="color:{P["text"]};font-size:12px;line-height:1.7;'
        f'padding-left:18px;margin:0 0 8px;">'
        f'<li>Get an API key from '
        f'<a href="https://console.anthropic.com/" target="_blank" '
        f'style="color:{P["accent"]};">console.anthropic.com</a>.</li>'
        f'<li>Export it in the shell before launching the server:'
        f'<pre style="background:{P["panel_alt"]};border:1px solid {P["border"]};'
        f'border-radius:2px;padding:8px 10px;margin:6px 0;'
        f'font-family:var(--ck-mono);font-size:11px;'
        f'color:{P["accent"]};overflow-x:auto;">'
        f'export ANTHROPIC_API_KEY="sk-ant-…"\n'
        f'.venv/bin/python seekingchartis.py --port 8090'
        f'</pre></li>'
        f'<li>Reload this page. The status badge will flip to CONNECTED '
        f'and the key fingerprint will show at the top of this panel.</li>'
        f'</ol>'
        f'<div style="color:{P["text_faint"]};font-size:10.5px;'
        f'line-height:1.55;margin-top:6px;">'
        f'The key is read from process env only — never stored on disk '
        f'or logged. Cost tracking in <code style="color:{P["accent"]};">'
        f'llm_calls</code> records model + token counts, not prompts.</div>'
        f'</div>'
    )


def _ollama_config_card() -> str:
    """Config-only snapshot of the local-Ollama connection (no network calls,
    so the page stays fast). Shows the failover host order + the knobs that
    make it work across environments, so an operator can wire it up anywhere."""
    try:
        from rcm_mc.assistant.ollama_client import (
            ollama_base_urls, ollama_default_model, ollama_num_ctx,
            ollama_keep_alive, ollama_max_retries, ollama_timeout_seconds,
            is_ollama_enabled,
        )
    except Exception:  # noqa: BLE001
        return ""
    on = is_ollama_enabled()
    hosts = ollama_base_urls()
    rows = [
        ("Status", "Enabled" if on
         else "Disabled — set PEDESK_GUIDE_OLLAMA_ENABLED=1 to turn on"),
        ("Candidate hosts (tried in order, with failover)", " · ".join(hosts)),
        ("Model", ollama_default_model()),
        ("Context window (num_ctx)", str(ollama_num_ctx() or "model default")),
        ("Keep model warm (keep_alive)", ollama_keep_alive()),
        ("Timeout / retries per host",
         f"{ollama_timeout_seconds()}s · {ollama_max_retries()} retries"),
    ]
    trs = "".join(
        f'<tr><td style="padding:5px 12px;color:{P["text_dim"]};font-size:12px;">'
        f'{_html.escape(k)}</td>'
        f'<td style="padding:5px 12px;font-family:var(--ck-mono);font-size:12px;'
        f'color:{P["text"]};">{_html.escape(v)}</td></tr>'
        for k, v in rows
    )
    note = (
        f'<div style="color:{P["text_dim"]};font-size:11px;line-height:1.5;'
        f'margin-top:8px;">Set <code>OLLAMA_HOST</code> (standard) or a '
        f'comma-separated <code>PEDESK_GUIDE_OLLAMA_BASE_URL</code> to reach '
        f'Ollama wherever it runs — local, a Tailscale box, or a sidecar. The '
        f'client tries each host in order and retries a slow first call.</div>'
    )
    return (
        f'<div style="background:{P["panel"]};border:1px solid {P["border"]};'
        f'border-radius:3px;padding:8px 8px 12px;margin-bottom:14px;">'
        f'<table style="width:100%;border-collapse:collapse;">{trs}</table>'
        f'{note}</div>'
    )


def render_ai_settings(store: Any) -> str:
    key_set = bool(os.environ.get("ANTHROPIC_API_KEY"))
    fp = _env_key_fingerprint()
    stats = _call_stats(store)

    # Local Ollama is the PRIMARY brain (free, on-box); Anthropic is a legacy
    # fallback used only when Ollama is off.
    try:
        from rcm_mc.assistant.ollama_client import (
            is_ollama_enabled, ollama_default_model,
        )
        ollama_on = is_ollama_enabled()
        ollama_model = ollama_default_model() if ollama_on else ""
    except Exception:  # noqa: BLE001 — assistant layer optional
        ollama_on, ollama_model = False, ""

    configured = ollama_on or key_set
    if ollama_on:
        backend_name = "Local Ollama"
        backend_desc = (
            f"Running fully on-box via local Ollama (model "
            f"<code>{_html.escape(ollama_model)}</code>) — no deal data leaves "
            f"the host and there is no per-call API cost."
        )
    elif key_set:
        backend_name = "Anthropic Claude API"
        backend_desc = (
            "Using the Anthropic Claude API (legacy fallback). Enable local "
            "Ollama (PEDESK_GUIDE_OLLAMA_ENABLED=1) to keep deal data on-box "
            "and remove API cost."
        )
    else:
        backend_name = "AI assistant"
        backend_desc = (
            "Not configured. Enable local Ollama "
            "(PEDESK_GUIDE_OLLAMA_ENABLED=1, preferred) or set an "
            "ANTHROPIC_API_KEY. Every feature degrades gracefully meanwhile."
        )

    status_color = P["positive"] if configured else P["text_faint"]
    status_text = "CONNECTED" if configured else "NOT CONFIGURED"
    status_badge = (
        f'<span style="display:inline-block;padding:3px 10px;'
        f'font-family:var(--ck-mono);font-size:10px;font-weight:700;'
        f'letter-spacing:0.12em;background:{P["panel"]};'
        f'border:1px solid {status_color};color:{status_color};'
        f'border-radius:2px;">{status_text}</span>'
    )

    key_line = (
        f'<div style="color:{P["text_dim"]};font-size:11px;margin-top:8px;'
        f'font-family:var(--ck-mono);">Anthropic key fingerprint: '
        f'<span style="color:{P["accent"]};">{_html.escape(fp)}</span>'
        f'{" · local Ollama active (key unused)" if ollama_on else ""}</div>'
        if key_set else ""
    )

    # 2026-05-28 batch 31 · header card keeps semantic status-color
    # left stripe (carries meaning: connected/disconnected/error);
    # radius capped at 2px.
    header_card = (
        f'<div style="background:{P["panel"]};border:1px solid {P["border"]};'
        f'border-left:3px solid {status_color};border-radius:2px;'
        f'padding:16px 20px;margin-bottom:14px;">'
        f'<div style="display:flex;gap:12px;align-items:baseline;flex-wrap:wrap;">'
        f'<div style="font-size:15px;font-weight:600;color:{P["text"]};">'
        f'{_html.escape(backend_name)}</div>'
        f'{status_badge}</div>'
        f'<div style="color:{P["text_dim"]};font-size:12px;line-height:1.55;'
        f'margin-top:6px;">'
        f'Backs the AI-assist features on this platform — IC memo '
        f'drafting, document Q&amp;A, conversational portfolio queries. '
        f'{backend_desc}</div>'
        f'{key_line}</div>'
    )

    kpis = (
        ck_kpi_block("Total calls", f'{stats["total_calls"]:,}', "since install")
        + ck_kpi_block("Est. cost", f'${stats["total_cost"]:.2f}', "USD")
        + ck_kpi_block("Cached", f'{stats["cached_hits"]:,}',
                       "prompts re-served")
        + ck_kpi_block("Models in use", f'{len(stats["by_model"])}', "seen in history")
    )
    kpi_strip = f'<div class="ck-kpi-grid">{kpis}</div>'

    related = _related_views([
        ("Integrations",      "/settings/integrations"),
        ("Automation Rules",  "/settings/automations"),
        ("API Docs",          "/api/docs"),
        ("Audit Log",         "/audit"),
        ("System Info",       "/api/system/info"),
    ])

    # 2026-05-28 batch 28 · Phase 3 · universal strict 5-block head.
    from ._chartis_kit import ck_editorial_head
    head = ck_editorial_head(
        eyebrow="AI ASSISTANT",
        title="Where the local AI assistant plugs into the deal work.",
        meta=(
            f"{'CONNECTED' if key_set else 'NOT CONNECTED'} · "
            f"{stats['total_calls']:,} CALL"
            f"{'S' if stats['total_calls'] != 1 else ''} · "
            f"{stats['cached_hits']:,} CACHED · "
            f"{len(stats['by_model'])} MODEL"
            f"{'S' if len(stats['by_model']) != 1 else ''}"
        ),
        lede_italic_phrase=(
            "On-box Ollama plus the Anthropic API back the "
            "platform's AI-assist features — IC memo drafting, "
            "document Q&amp;A, and conversational portfolio "
            "queries."
        ),
        lede_body=(
            "Cost, cache hit-rate, and per-model "
            "volume live in the strip below; rotate the key "
            "or change the Ollama host without leaving this page."
        ),
    )
    body = (
        head
        + header_card
        + kpi_strip
        + ck_section_header("LOCAL OLLAMA", "on-box model — connection & config")
        + _ollama_config_card()
        + ck_section_header("FEATURES", "what the assistant powers on this platform")
        + _features_card()
        + ck_section_header("MODELS", "local Ollama models · Anthropic fallback")
        + _models_table(active_id=None)
        + ck_section_header("SETUP", "how to connect your key")
        + _setup_instructions()
        + related
        + ck_next_section(
            "Back to settings",
            "/settings",
            eyebrow="Continue —",
            italic_word="settings",
        )
    )
    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from ._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(
        body,
        title="AI Assistant — Local Ollama",
        active_nav="/settings",
        subtitle=("Connected" if key_set else "Not yet connected"),
    )
