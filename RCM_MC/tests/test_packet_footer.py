"""tests for ``packet_footer`` (P61)."""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from rcm_mc.ui._ui_kit import packet_footer


def _meta(**overrides) -> dict:
    base = {
        "id": "20260415T092300Z-ab12cd",
        "inputs_hash":
            "deadbeef12345678cafe90abcdef01234567890fedcba0987654321abcdef01",
        "last_rebuilt_at": (
            datetime.now(timezone.utc) - timedelta(minutes=14)
        ).isoformat(),
    }
    base.update(overrides)
    return base


class FooterRendering(unittest.TestCase):

    def test_full_metadata_renders(self) -> None:
        html = packet_footer(_meta())
        self.assertIn("packet-footer", html)
        self.assertIn("20260415T092300Z-ab12cd", html)
        self.assertIn("sha256:deadbeef1234", html)
        self.assertTrue("m ago" in html or "h ago" in html)

    def test_hash_truncated_with_full_in_title(self) -> None:
        full_hash = (
            "deadbeef12345678cafe90abcdef01234567890fedcba0987654321abcdef01"
        )
        html = packet_footer(_meta(inputs_hash=full_hash))
        # Title attribute should carry the full hash for copy-paste.
        self.assertIn(f'title="{full_hash}"', html)

    def test_rebuild_button_when_href_supplied(self) -> None:
        html = packet_footer(
            _meta(),
            rebuild_href="/api/analysis/aurora/rebuild",
        )
        self.assertIn("Force rebuild", html)
        self.assertIn('action="/api/analysis/aurora/rebuild"', html)

    def test_no_rebuild_button_by_default(self) -> None:
        html = packet_footer(_meta())
        self.assertNotIn("Force rebuild", html)

    def test_download_link_when_href_supplied(self) -> None:
        html = packet_footer(
            _meta(),
            download_href="/api/analysis/aurora/packet.json",
        )
        self.assertIn("Download packet JSON", html)
        self.assertIn('href="/api/analysis/aurora/packet.json"', html)


class GracefulMissing(unittest.TestCase):

    def test_none_packet_returns_empty(self) -> None:
        self.assertEqual(packet_footer(None), "")
        self.assertEqual(packet_footer({}), "")

    def test_missing_hash_renders_no_hash_marker(self) -> None:
        html = packet_footer(_meta(inputs_hash=""))
        self.assertIn("no hash", html)

    def test_missing_rebuild_renders_never(self) -> None:
        html = packet_footer(_meta(last_rebuilt_at=""))
        self.assertIn("never", html)


if __name__ == "__main__":
    unittest.main()
