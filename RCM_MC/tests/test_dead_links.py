"""Regression: internal links found dead by a full-site crawl.

A crawl of every internal href across all routes surfaced three real
dead links:
  - model-validation page self-linked to /models/validation (the route
    is /model-validation, with a hyphen)
  - the login footer linked to /docs/deployment (no /docs route exists)
  - the scenarios page had a "Challenge Solver" button hardcoded to
    /models/challenge/se ("se" is not a real deal id)
"""
from __future__ import annotations

import pathlib
import unittest

from rcm_mc.ui.chartis.login_page import render_login_page
from rcm_mc.ui.scenarios_page import render_scenarios_page

_MODELVAL_SRC = (
    pathlib.Path(__file__).resolve().parents[1]
    / "rcm_mc" / "ui" / "model_validation_page.py"
).read_text()


class DeadLinkTests(unittest.TestCase):
    def test_login_no_docs_link(self):
        self.assertNotIn("/docs/deployment", render_login_page())

    def test_scenarios_no_bogus_challenge_link(self):
        self.assertNotIn("/models/challenge/se", render_scenarios_page([]))

    def test_model_validation_self_links_use_correct_route(self):
        # The page must not link to the non-existent /models/validation.
        self.assertNotIn('href="/models/validation"', _MODELVAL_SRC)
        self.assertNotIn('href="/models/validation?', _MODELVAL_SRC)
        self.assertIn('href="/model-validation"', _MODELVAL_SRC)


if __name__ == "__main__":
    unittest.main()
