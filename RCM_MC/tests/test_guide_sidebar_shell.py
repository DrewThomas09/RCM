"""Regression tests for the PEdesk Guide sidebar in the global shell.

The sidebar is server-rendered markup + a vanilla-JS shim injected by
``chartis_shell``. These tests assert the static contract (trigger,
closed-by-default panel, ARIA, sections, endpoint wiring, read-only copy,
and the absence of upload/action/mutation affordances). The dynamic
rendering (metric/source cards, answers) is JS-built and verified
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

    def test_all_sections_present(self):
        for sec in ("Page overview", "Key metrics", "Data sources",
                    "Limitations &amp; caveats", "Suggested questions",
                    "Ask PEdesk Guide"):
            self.assertIn(sec, self.html)

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
        # The disabled/unavailable state is now built from the health
        # payload: a plain primary line + a collapsible Setup details.
        self.assertIn("Ask PEdesk Guide is unavailable.", self.html)
        self.assertIn("requires local Ollama to be enabled", self.html)
        self.assertIn("Setup details", self.html)

    def test_read_only_copy_present(self):
        # Now a collapsible in-body card (was a sticky footer). Whitespace-
        # normalize so HTML line-wrapping doesn't break the assertions.
        flat = " ".join(self.html.split())
        self.assertIn("PEdesk Guide is read-only", flat)
        self.assertIn("cannot change assumptions", flat)
        self.assertIn("make final investment recommendations", flat)

    def test_no_upload_or_action_affordances_in_panel(self):
        # Scope to real affordances, not the read-only disclaimer text
        # (which intentionally lists the forbidden verbs in the negative).
        frag = _guide_fragment(self.html)
        self.assertTrue(frag)
        self.assertNotIn('type="file"', frag)            # no uploads
        self.assertNotIn("multipart/form-data", frag)
        # The ask <form> has no action= and no method=post — it submits via
        # JS fetch only, so there's no mutation-form affordance in the panel.
        self.assertNotIn("<form action=", frag)
        self.assertNotIn('method="post"', frag.lower())

    def test_uses_csrf_safe_plain_fetch(self):
        # The endpoint POST is a plain fetch(); the global CSRF patch adds
        # X-CSRF-Token. The sidebar must NOT roll its own CSRF system.
        self.assertIn("method:'POST'", self.html)
        self.assertNotIn("X-CSRF", _guide_fragment(self.html) or "")

    def test_absent_on_bare_pages(self):
        bare = chartis_shell("<p>x</p>", title="Login", show_chrome=False)
        self.assertNotIn("ck-guide-panel", bare)
        self.assertNotIn("data-ck-guide-open", bare)


class GuideSidebarHardeningTests(unittest.TestCase):
    """Task 7 hardening contract (static — the JS behavior is verified
    manually; these assert the guard constructs are present in the shim)."""

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
        # answers preserve readable whitespace
        self.assertIn("white-space:pre-wrap", self.html)

    def test_safe_rendering_no_unescaped_answer(self):
        # answer rendered via textContent (never innerHTML of model text)
        self.assertIn("aEl.textContent=b.answer", self.html)
        # error text via textContent too (failBubble sets p.textContent)
        self.assertIn("aEl.querySelector('p').textContent=msg", self.html)
        # there is an HTML-escape helper for any interpolated dynamic text
        self.assertIn("function esc(", self.html)

    def test_failed_request_preserves_question_for_retry(self):
        self.assertIn("lastQuestion", self.html)
        self.assertIn("data-ck-guide-retry-ask", self.html)
        self.assertIn("ask(lastQuestion)", self.html)


class GuideSidebarPolishTests(unittest.TestCase):
    """Task 9 — card-based presentation polish (static contract; the
    rendered cards are JS-built and verified manually)."""

    def setUp(self):
        self.html = chartis_shell("<p>b</p>", title="T", active_nav="/app")
        self.flat = " ".join(self.html.split())

    def test_card_based_layout(self):
        self.assertIn(".ck-guide-card{", self.html)        # card CSS
        self.assertIn('class="ck-guide-card"', self.html)  # card markup
        self.assertIn("ck-guide-card-title", self.html)
        self.assertIn(">Page overview<", self.html)

    def test_read_only_policy_is_collapsible_in_body_not_sticky_footer(self):
        # A <details> card inside the scroll body...
        self.assertIn('<details class="ck-guide-card ck-guide-policy"',
                      self.html)
        self.assertIn("ck-guide-policy-summary", self.html)
        # ...and the old sticky footer rule is gone.
        self.assertNotIn(".ck-guide-readonly{", self.html)

    def test_ask_card_after_content_with_body_bottom_padding(self):
        # Ask section is its own card, present in the scrollable body.
        self.assertIn("ck-guide-ask-card", self.html)
        # Body has real bottom padding so the Ask card is fully visible.
        self.assertIn("padding:14px 14px 28px", self.html)

    def test_data_source_metadata_labels(self):
        for label in (">Type<", ">Update cadence<", ">Freshness<"):
            self.assertIn(label, self.html)
        self.assertIn("ck-guide-meta-grid", self.html)

    def test_metric_show_more_toggle(self):
        self.assertIn("data-more-toggle", self.html)
        self.assertIn("Show all ", self.html)
        self.assertIn("Show fewer ", self.html)

    def test_caveat_rendered_as_pill_not_raw_repeated_line(self):
        # Formula sentinel becomes a pill, not "Caveats: Needs source ..."
        self.assertIn("ck-guide-pill", self.html)
        self.assertIn("Formula not yet documented", self.html)
        # The needs-doc sentinel is collapsed into one calm limitations line.
        self.assertIn("still need source documentation", self.html)
        # Old raw repeated rendering is gone.
        self.assertNotIn("Caveats: Needs source documentation.", self.html)

    def test_disabled_qa_copy_is_full_and_actionable(self):
        # Primary user message + secondary + collapsible technical setup.
        self.assertIn("Ask PEdesk Guide is unavailable.", self.flat)
        self.assertIn("The page guide still works, but question answering "
                      "requires local Ollama to be enabled.", self.flat)
        self.assertIn("Setup details", self.flat)
        # The env-var detail comes from the health payload (required_env),
        # rendered inside the collapsed disclosure.
        self.assertIn("required_env", self.flat)
        self.assertIn("run_with_guide_ollama.sh", self.flat)

    def test_answer_card_class_and_safe_render(self):
        self.assertIn(".ck-guide-a{", self.html)          # answer bubble CSS
        self.assertIn("white-space:pre-wrap", self.html)  # readable line breaks
        self.assertIn("aEl.textContent=b.answer", self.html)  # XSS-safe

    def test_surfaces_rag_sources_and_warning(self):
        # Sidebar renders RAG provenance + any rag_warning from the ask
        # response (both escaped).
        self.assertIn("rag_sources_used", self.html)
        self.assertIn("Guide context used:", self.html)
        self.assertIn("rag_warning", self.html)
        self.assertIn("esc(b.rag_warning)", self.html)


if __name__ == "__main__":
    unittest.main()
