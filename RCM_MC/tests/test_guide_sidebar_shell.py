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
        for sec in ("Overview", "Key metrics", "Data sources",
                    "Limitations", "Suggested questions", "Ask PEdesk Guide"):
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
        self.assertIn("Local PEdesk Guide Q&A is disabled.", self.html)
        self.assertIn("PEdesk Guide local model is unavailable.", self.html)

    def test_read_only_copy_present(self):
        self.assertIn("PEdesk Guide is read-only.", self.html)
        self.assertIn("cannot change assumptions", self.html)
        self.assertIn("make final investment recommendations", self.html)

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


if __name__ == "__main__":
    unittest.main()
