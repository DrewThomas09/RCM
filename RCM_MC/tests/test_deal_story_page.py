"""tests for ``/deal/<id>/story``.

PROMPTS.md Phase 4 / Prompt 55: narrative view of a deal. Renders
even when the underlying packet is missing — falls back to a
graceful empty state with a CTA pointing at the workbench.
"""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.request


class StoryPageRenders(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.server import build_server

        cls.tmp = tempfile.mkdtemp(prefix="rcm_p55_")
        cls.db = os.path.join(cls.tmp, "p.db")
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        cls.server, _ = build_server(port=port, db_path=cls.db)
        cls.base = f"http://127.0.0.1:{port}"
        t = threading.Thread(target=cls.server.serve_forever, daemon=True)
        t.start()
        time.sleep(0.05)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()

    def test_unknown_deal_renders_empty_state(self) -> None:
        with urllib.request.urlopen(
            self.base + "/deal/never-heard-of/story", timeout=5,
        ) as r:
            body = r.read().decode()
        self.assertEqual(r.status, 200)
        # Empty state CTA points at the workbench.
        self.assertIn("Open analysis workbench", body)
        self.assertIn("/analysis/never-heard-of", body)


class RenderStoryDirectly(unittest.TestCase):

    def test_renders_with_present_deal(self) -> None:
        import sqlite3
        from rcm_mc.ui.deal_story_page import render_story

        with tempfile.NamedTemporaryFile(suffix=".db") as tf:
            con = sqlite3.connect(tf.name)
            con.execute(
                "CREATE TABLE deals (deal_id TEXT PRIMARY KEY, "
                "name TEXT, created_at TEXT)"
            )
            con.execute(
                "INSERT INTO deals (deal_id, name) VALUES (?, ?)",
                ("aurora", "Project Aurora"),
            )
            con.commit()
            con.close()

            html = render_story(tf.name, "aurora")
        self.assertIn("Project Aurora", html)
        # All four narrative sections present.
        for label in ("Thesis", "What we found", "What we believe",
                      "Recommendation"):
            with self.subTest(label=label):
                self.assertIn(label, html)

    def test_renders_with_missing_db(self) -> None:
        # Renderer must not crash if the deals table doesn't exist.
        from rcm_mc.ui.deal_story_page import render_story

        with tempfile.NamedTemporaryFile(suffix=".db") as tf:
            html = render_story(tf.name, "aurora")
        # Empty-state CTA renders.
        self.assertIn("No story for this deal yet", html)


if __name__ == "__main__":
    unittest.main()
