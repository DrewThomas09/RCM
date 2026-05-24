"""Regression tests for the PEdesk Guide sidebar in the global shell.

The sidebar is server-rendered markup + a vanilla-JS shim injected by
``chartis_shell``. As of the "Variant B — Tabbed" redesign (design handoff)
the panel is a navy header + tab strip (Overview · Metrics · Sources · Ask),
a scrolling paper body, and a sticky cream composer. These tests assert the
static contract (trigger, closed-by-default panel, ARIA tablist/tabpanel,
the four tabs, endpoint wiring, read-only copy, no upload/action/mutation
affordances, no external CDN/fonts) plus the JS hardening guards. The
dynamic rendering (tab content, cards, answers) is JS-built and verified
manually — see PROGRESS.md.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import chartis_shell


def _guide_fragment(html: str) -> str:
    """The aside markup only (so 'no upload field' checks are scoped)."""
    start = html.find('id="ck-guide-panel"')
    end = html.find("</aside>", start)
    return html[start:end] if start != -1 and end != -1 else ""


class GuideSidebarShellTests(unittest.TestCase):
    def setUp(self):
        self.html = chartis_shell(
            "<p>body</p>", title="HCRIS X-Ray", active_nav="/portfolio"
        )

    def test_trigger_present_and_keyboard_accessible(self):
        self.assertIn("data-ck-guide-open", self.html)
        self.assertIn(">Guide<", self.html)
        # It's a real <button> (focusable / keyboard-activatable).
        self.assertIn('class="ck-guide-trigger" type="button"', self.html)
        self.assertIn('aria-controls="ck-guide-panel"', self.html)

    def test_panel_closed_by_default(self):
        self.assertIn('class="ck-guide-panel" hidden', self.html)

    def test_panel_aria_and_heading(self):
        self.assertIn('aria-label="PEdesk Guide"', self.html)
        self.assertIn('role="dialog"', self.html)
        self.assertIn("data-ck-guide-page-title", self.html)
        self.assertIn("data-ck-guide-close", self.html)
        self.assertIn('aria-label="Close PEdesk Guide"', self.html)

    def test_tabbed_layout_aria(self):
        # Navy block carries an ARIA tablist with four roving tabs, each
        # controlling a labelled tabpanel.
        self.assertIn('role="tablist"', self.html)
        for tab in ("overview", "metrics", "sources", "ask"):
            self.assertIn(f'data-ck-guide-tab="{tab}"', self.html)
            self.assertIn(f'id="ck-guide-panel-{tab}"', self.html)
            self.assertIn(f'data-ck-guide-panel="{tab}"', self.html)
        # role=tab and role=tabpanel both present
        self.assertIn('role="tab"', self.html)
        self.assertIn('role="tabpanel"', self.html)
        # Default tab selected; others not.
        self.assertIn('aria-selected="true"', self.html)
        self.assertIn('aria-selected="false"', self.html)

    def test_tab_keyboard_navigation_and_switching(self):
        # Roving-tabindex arrow/Home/End nav + click switch + select keys.
        self.assertIn("function activateTab(", self.html)
        self.assertIn("ArrowRight", self.html)
        self.assertIn("ArrowLeft", self.html)
        self.assertIn("'Home'", self.html)
        self.assertIn("'End'", self.html)

    def test_metrics_sources_tabs_have_count_badges(self):
        self.assertIn("data-ck-guide-count-metrics", self.html)
        self.assertIn("data-ck-guide-count-sources", self.html)
        # Counts only show when > 0 (no alarming "0").
        self.assertIn("function setCount(", self.html)

    def test_context_strength_badge_in_header(self):
        # Pill + dot in the navy header, label set from context_quality.
        self.assertIn("ck-guide-ctx-badge", self.html)
        self.assertIn("ck-guide-ctx-dot", self.html)
        self.assertIn("data-ck-guide-quality-label", self.html)
        self.assertIn("' context'", self.html)

    def test_sticky_composer_footer(self):
        frag = _guide_fragment(self.html)
        self.assertIn('class="ck-guide-composer"', frag)
        self.assertIn("data-ck-guide-input", frag)
        self.assertIn("data-ck-guide-send", frag)
        # Footer status line: read-only + RAG + model id slot.
        self.assertIn("data-ck-guide-rag-status", frag)
        self.assertIn("data-ck-guide-model", frag)

    def test_wires_all_three_endpoints(self):
        self.assertIn("/api/guide/context?route=", self.html)
        self.assertIn("/api/guide/ollama-health", self.html)
        self.assertIn("fetch('/api/guide/ask'", self.html)

    def test_route_uses_path_and_query_without_hash(self):
        # route() = pathname + search; comment documents the hash omission.
        self.assertIn("location.pathname+location.search", self.html)

    def test_ask_form_and_deliberate_loading_copy(self):
        self.assertIn("data-ck-guide-ask-form", self.html)
        self.assertIn("data-ck-guide-input", self.html)
        self.assertIn("data-ck-guide-send", self.html)
        # 20s-aware loading state
        self.assertIn("PEdesk Guide is answering from the page context",
                      self.html)

    def test_disabled_and_unavailable_copy_present(self):
        # AI-mode status: a ready badge, a "not fully configured" card, and a
        # collapsible Setup details — all driven by health.ai_ready.
        self.assertIn("AI Q&amp;A ready &middot; RAG enabled", self.html)
        self.assertIn("Ask PEdesk Guide is not fully configured.", self.html)
        self.assertIn("Setup details", self.html)

    def test_read_only_copy_present(self):
        # Collapsible read-only policy at the foot of the Ask tab. Whitespace-
        # normalize so HTML line-wrapping doesn't break the assertions.
        flat = " ".join(self.html.split())
        self.assertIn("PEdesk Guide is read-only", flat)
        self.assertIn("cannot change assumptions", flat)
        self.assertIn("make final investment recommendations", flat)
        # Composer footer also carries the read-only signal.
        self.assertIn("PEdesk &middot; read-only", self.html)

    def test_no_upload_or_action_affordances_in_panel(self):
        # Scope to real affordances, not the read-only disclaimer text
        # (which intentionally lists the forbidden verbs in the negative).
        frag = _guide_fragment(self.html)
        self.assertTrue(frag)
        self.assertNotIn('type="file"', frag)            # no uploads
        self.assertNotIn("multipart/form-data", frag)
        # The composer <form> has no action= and no method=post — it submits
        # via JS fetch only, so there's no mutation-form affordance.
        self.assertNotIn("<form action=", frag)
        self.assertNotIn('method="post"', frag.lower())

    def test_uses_csrf_safe_plain_fetch(self):
        # The endpoint POST is a plain fetch(); the global CSRF patch adds
        # X-CSRF-Token. The sidebar must NOT roll its own CSRF system.
        self.assertIn("method:'POST'", self.html)
        self.assertNotIn("X-CSRF", _guide_fragment(self.html) or "")

    def test_no_external_cdn_or_prototype_artifacts(self):
        # The prototype shipped React/Babel via unpkg + Google Fonts; the
        # production sidebar must NOT pull any external script/font/CDN.
        frag = _guide_fragment(self.html)
        for bad in ("unpkg.com", "babel", "react-dom", "cdn.jsdelivr",
                    "fonts.googleapis", "fonts.gstatic"):
            self.assertNotIn(bad, frag.lower())

    def test_absent_on_bare_pages(self):
        bare = chartis_shell("<p>x</p>", title="Login", show_chrome=False)
        self.assertNotIn("ck-guide-panel", bare)
        self.assertNotIn("data-ck-guide-open", bare)


class GuideSidebarHardeningTests(unittest.TestCase):
    """Hardening contract (static — the JS behavior is verified manually;
    these assert the guard constructs are present in the shim)."""

    def setUp(self):
        self.html = chartis_shell("<p>b</p>", title="T", active_nav="/portfolio")

    def test_slow_response_copy_after_10s(self):
        self.assertIn("PEdesk Guide is answering from the page context",
                      self.html)
        self.assertIn("Local model responses can take a little while on this "
                      "machine", self.html)
        self.assertIn("10000", self.html)  # 10s timer

    def test_duplicate_submit_guard(self):
        # one request at a time: pending guard blocks re-entry
        self.assertIn("if(pending||!q.trim())return;", self.html)
        # send button disabled while pending
        self.assertIn("send.disabled=true", self.html)
        # Enter sends but the guard still applies; Shift+Enter = newline
        self.assertIn("e.key==='Enter'&&!e.shiftKey", self.html)

    def test_cmd_ctrl_enter_submits(self):
        # The design spec's composer shortcut: Cmd/Ctrl+Enter submits.
        self.assertIn("e.metaKey||e.ctrlKey", self.html)

    def test_stale_response_protection(self):
        # request sequence token + invalidate-on-close/route-change
        self.assertIn("reqSeq", self.html)
        self.assertIn("invalidateInFlight", self.html)
        self.assertIn("if(myseq!==reqSeq) return", self.html)
        # AbortController used when available
        self.assertIn("AbortController", self.html)
        self.assertIn("activeAbort.abort()", self.html)

    def test_route_change_and_close_reset_state(self):
        # both close() and loadContext() clear the session Q&A history
        self.assertIn("clearHistory()", self.html)
        # close invalidates in-flight before hiding
        self.assertIn("invalidateInFlight();\n    clearHistory();\n    panel.hidden=true",
                      self.html)

    def test_layout_safety_css(self):
        self.assertIn("overflow-wrap:break-word", self.html)
        self.assertIn("word-break:break-word", self.html)
        self.assertIn("overflow-x:hidden", self.html)

    def test_answer_rendered_via_safe_markdown(self):
        # Answers go through mdToHtml, which escapes the model text FIRST
        # then whitelists a few markdown marks — XSS-safe AND no raw
        # "**bold**" literals (the old textContent path showed them).
        self.assertIn("function mdToHtml(", self.html)
        self.assertIn("ck-guide-a-body", self.html)
        self.assertIn("mdToHtml(b.answer", self.html)
        # error text still via textContent (failBubble sets p.textContent)
        self.assertIn("aEl.querySelector('p').textContent=msg", self.html)
        # escape helpers exist for any interpolated dynamic text
        self.assertIn("function esc(", self.html)
        self.assertIn("function escAttr(", self.html)

    def test_failed_request_preserves_question_for_retry(self):
        self.assertIn("lastQuestion", self.html)
        self.assertIn("data-ck-guide-retry-ask", self.html)
        self.assertIn("ask(lastQuestion)", self.html)


class GuideSidebarDesignTests(unittest.TestCase):
    """Variant B tabbed-redesign contract: design tokens, editorial type
    hierarchy (serif/sans/mono using already-loaded fonts), chip→composer
    interaction, and the no-external-font invariant."""

    def setUp(self):
        self.html = chartis_shell("<p>b</p>", title="T", active_nav="/app")
        self.flat = " ".join(self.html.split())

    def _guide_css(self):
        a = self.html.find(".ck-guide-panel{")
        b = self.html.find("@media print{.ck-guide-panel")
        return self.html[a:b]

    def test_design_tokens_present(self):
        css = self._guide_css()
        for token, hexv in (("--ck-g-navy", "#0d2336"),
                            ("--ck-g-paper", "#fbf7ee"),
                            ("--ck-g-cream", "#f4ecd9"),
                            ("--ck-g-green", "#1f7a5a"),
                            ("--ck-g-amber", "#c2853a"),
                            ("--ck-g-rule", "#d9cfb8")):
            self.assertIn(f"{token}:{hexv}", css)
        # 440px shell, 14px outer radius.
        self.assertIn("width:min(440px,94vw)", css)
        self.assertIn("border-radius:14px", css)

    def test_editorial_type_hierarchy(self):
        css = self._guide_css()
        # Serif headlines (Source Serif 4), mono labels/meta (JetBrains Mono),
        # house sans body (Inter Tight) — all fonts already loaded by the shell.
        self.assertIn("Source Serif 4", css)
        self.assertIn("JetBrains Mono", css)
        self.assertIn("Inter Tight", css)
        # Title + metric name use the serif family var.
        self.assertIn(".ck-guide-title{font-family:var(--ck-g-serif)", css)
        self.assertIn(".ck-guide-metric-name{font-family:var(--ck-g-serif)",
                      css)

    def test_no_external_font_added_by_guide(self):
        # System/house fonts only — no @import, no Google-fonts link inside
        # the Guide CSS block.
        css = self._guide_css()
        self.assertNotIn("@import", css)
        self.assertNotIn("fonts.googleapis", css)

    def test_chip_drops_into_composer_without_autosubmit(self):
        # Chip click fills the composer textarea + focuses it; it must NOT
        # call ask()/submitQuestion().
        self.assertIn("function wireChips(", self.html)
        self.assertIn("inp.value=b.getAttribute('data-q')", self.html)
        self.assertIn("inp.focus();", self.html)
        # Both Overview ("try asking") and Ask (full set) chip rails exist.
        self.assertIn("data-ck-guide-suggested-overview", self.html)
        self.assertIn("data-ck-guide-suggested-ask", self.html)

    def test_submit_switches_to_ask_tab(self):
        # Asking from any tab surfaces the answer in the Ask panel.
        self.assertIn("activateTab('ask'); ask(v)", self.html)

    def test_data_source_inline_meta_format(self):
        # Sources render as diamond + name + "<type> · <cadence> · <freshness>"
        # inline meta (replaces the old labelled meta-grid).
        self.assertIn("ck-guide-ds-gem", self.html)
        self.assertIn("ck-guide-ds-meta", self.html)
        self.assertIn("ck-guide-ds-lim", self.html)

    def test_metric_formula_chip_and_fallback(self):
        self.assertIn("ck-guide-metric-formula", self.html)
        self.assertIn("formula not documented", self.html)
        self.assertIn("ck-guide-metric-why", self.html)

    def test_caveat_collapses_needs_doc_sentinel(self):
        # The needs-doc sentinel is collapsed into one calm line in the
        # Overview caveat callout (not repeated alarmingly).
        self.assertIn("still need source documentation", self.html)
        self.assertIn("function renderCaveat(", self.html)

    def test_disabled_qa_copy_is_full_and_actionable(self):
        self.assertIn("Ask PEdesk Guide is not fully configured.", self.flat)
        self.assertIn("The page guide still works.", self.flat)
        self.assertIn("Setup details", self.flat)
        self.assertIn("aiReason(", self.flat)
        self.assertIn("h.setup_commands", self.flat)

    def test_ask_gated_on_ai_ready(self):
        self.assertIn("var ready=!!(h&&h.ai_ready);", self.html)
        self.assertIn("input.disabled=!ready; send.disabled=!ready;", self.html)

    def test_surfaces_rag_sources_and_warning(self):
        self.assertIn("rag_sources_used", self.html)
        self.assertIn("Also used local Guide RAG sources", self.html)
        self.assertIn("Answered from current page context", self.html)
        self.assertIn("Metric Registry", self.html)
        self.assertIn("Data Source Registry", self.html)
        self.assertIn("ck-guide-src-title", self.html)
        self.assertIn("ck-guide-src-score", self.html)
        self.assertIn("s.score.toFixed(2)", self.html)
        self.assertIn("esc(s.title)", self.html)
        self.assertIn("esc(b.rag_warning)", self.html)

    def test_latency_feedback_and_slow_note(self):
        self.assertIn("var t0=Date.now();", self.html)
        self.assertIn("(Date.now()-t0)/1000", self.html)
        self.assertIn("+secs+'s</span>'", self.html)
        self.assertIn("can take a little while", self.html)
        self.assertIn("ask(lastQuestion)", self.html)

    def test_copy_answer_is_clipboard_only_no_persistence(self):
        self.assertIn("ck-guide-copy", self.html)
        self.assertIn("navigator.clipboard.writeText(b.answer", self.html)
        self.assertIn("copyBtn.hidden=true", self.html)


if __name__ == "__main__":
    unittest.main()
