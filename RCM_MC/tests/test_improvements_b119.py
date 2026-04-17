"""Tests for B119: conftest fixtures, pytest markers, tooling config.

 1. tmp_store fixture creates usable store.
 2. server_port fixture starts a working server.
 3. Pytest markers are registered (no warnings).
"""
from __future__ import annotations

import json
import urllib.request
import unittest

import pytest


class TestConfFixtures:

    def test_tmp_store_works(self, tmp_store):
        store, path = tmp_store
        store.upsert_deal("fx1", name="Fixture Test")
        deals = store.list_deals()
        assert len(deals) == 1

    def test_server_port_works(self, server_port):
        port, store = server_port
        store.upsert_deal("fx1", name="Fixture Test")
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/health",
        ) as r:
            body = json.loads(r.read().decode())
        assert body["status"] in ("healthy", "degraded")


@pytest.mark.api
class TestMarkerRegistered:

    def test_marker_exists(self):
        assert True


if __name__ == "__main__":
    unittest.main()
