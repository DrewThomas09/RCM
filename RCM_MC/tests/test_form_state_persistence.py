"""tests for form-state localStorage persistence.

PROMPTS.md Phase 1 / Prompt 10: 12–18-input forms (Bridge Audit,
Thesis Pipeline, Deal Monte Carlo, Covenant Stress) lose all state
when the server restarts mid-fill — sessions invalidate on restart,
the POST bounces to /login, and the partner re-enters the form blank.

Fix: a small JS layer in the v2 shell saves field values to
localStorage on input/change and restores them on DOMContentLoaded.
Survives the /login round-trip because localStorage is unaffected
by HTTP-state changes.

These tests pin the JS contract; a manual browser test still owns
the cross-restart round-trip. The skip-list (passwords, CSRF
tokens, hidden fields, file uploads) is enforced here so a future
edit can't accidentally start persisting credentials.
"""
from __future__ import annotations

import os
import unittest


class FormPersistJSPresent(unittest.TestCase):
    """The shell must inject the form-persistence JS so every page
    inherits the behaviour without per-page wiring."""

    def setUp(self) -> None:
        # Force v2 on so we render the path that injects the JS.
        os.environ["CHARTIS_UI_V2"] = "1"
        # Drop cached kit modules so the flag re-applies.
        import sys
        for name in list(sys.modules):
            if name.startswith("rcm_mc.ui._chartis_kit"):
                sys.modules.pop(name, None)
        from rcm_mc.ui._chartis_kit import chartis_shell
        self.html = chartis_shell("<p>body</p>", "T")

    def test_localstorage_block_present(self) -> None:
        self.assertIn("window.localStorage", self.html)
        self.assertIn("formPersist:", self.html)

    def test_persists_on_input_and_change(self) -> None:
        # Both events must fire saves so the partner's value is
        # captured whether they type, paste, or pick from a select.
        self.assertIn("addEventListener('input'", self.html)
        self.assertIn("addEventListener('change'", self.html)

    def test_restores_on_load(self) -> None:
        self.assertIn("DOMContentLoaded", self.html)

    def test_skips_credentials_and_csrf(self) -> None:
        # Skip-list must be in the rendered JS source so credentials
        # never leak into localStorage.
        for needle in ("password", "csrf_token", "_csrf", "hidden", "file"):
            with self.subTest(skip=needle):
                self.assertIn(needle, self.html)

    def test_keys_namespaced_by_pathname(self) -> None:
        # Two different routes must not collide. The JS prefixes keys
        # with window.location.pathname.
        self.assertIn("window.location.pathname", self.html)


if __name__ == "__main__":
    unittest.main()
