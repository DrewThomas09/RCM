"""Tests for the TTL cache decorator."""
from __future__ import annotations

import time
import unittest


class TestTTLCache(unittest.TestCase):
    def test_basic_cache_hit(self):
        from rcm_mc.infra.cache import ttl_cache

        calls = [0]

        @ttl_cache(seconds=10)
        def expensive(x):
            calls[0] += 1
            return x * 2

        self.assertEqual(expensive(5), 10)
        self.assertEqual(expensive(5), 10)
        self.assertEqual(expensive(5), 10)
        # Function only called once — others were cache hits
        self.assertEqual(calls[0], 1)
        info = expensive.cache_info()
        self.assertEqual(info.hits, 2)
        self.assertEqual(info.misses, 1)

    def test_different_args_separate_cache(self):
        from rcm_mc.infra.cache import ttl_cache

        calls = [0]

        @ttl_cache(seconds=10)
        def f(x):
            calls[0] += 1
            return x

        f(1)
        f(2)
        f(1)
        f(2)
        self.assertEqual(calls[0], 2)

    def test_kwargs_in_key(self):
        from rcm_mc.infra.cache import ttl_cache
        calls = [0]

        @ttl_cache(seconds=10)
        def f(x, *, mode="default"):
            calls[0] += 1
            return f"{x}-{mode}"

        f(1, mode="default")
        f(1, mode="default")
        f(1, mode="other")  # different kwarg → miss
        self.assertEqual(calls[0], 2)

    def test_ttl_expiry(self):
        from rcm_mc.infra.cache import ttl_cache

        calls = [0]

        @ttl_cache(seconds=0.05)
        def f(x):
            calls[0] += 1
            return x

        f(1)
        f(1)
        self.assertEqual(calls[0], 1)
        time.sleep(0.07)
        f(1)  # expired → miss
        self.assertEqual(calls[0], 2)

    def test_cache_clear(self):
        from rcm_mc.infra.cache import ttl_cache
        calls = [0]

        @ttl_cache(seconds=60)
        def f(x):
            calls[0] += 1
            return x

        f(1)
        f(1)
        self.assertEqual(calls[0], 1)
        f.cache_clear()
        f(1)
        self.assertEqual(calls[0], 2)
        info = f.cache_info()
        # Stats reset on clear
        self.assertEqual(info.misses, 1)
        self.assertEqual(info.hits, 0)

    def test_maxsize_evicts_oldest(self):
        from rcm_mc.infra.cache import ttl_cache

        @ttl_cache(seconds=60, maxsize=3)
        def f(x):
            return x

        f(1)
        time.sleep(0.001)
        f(2)
        time.sleep(0.001)
        f(3)
        time.sleep(0.001)
        f(4)  # forces eviction
        info = f.cache_info()
        self.assertEqual(info.currsize, 3)

    def test_zero_or_negative_seconds_rejected(self):
        from rcm_mc.infra.cache import ttl_cache
        with self.assertRaises(ValueError):
            @ttl_cache(seconds=0)
            def _f(x): return x
        with self.assertRaises(ValueError):
            @ttl_cache(seconds=-1)
            def _g(x): return x


class TestPanelCaching(unittest.TestCase):
    """Verify the bottleneck panels actually use the cache."""

    def test_quality_panel_cached(self):
        from rcm_mc.ml.model_quality import (
            _build_default_quality_panel,
        )
        # Reset
        _build_default_quality_panel.cache_clear()
        t0 = time.perf_counter()
        first = _build_default_quality_panel()
        first_elapsed = time.perf_counter() - t0
        t0 = time.perf_counter()
        second = _build_default_quality_panel()
        second_elapsed = time.perf_counter() - t0
        # Same object identity (cache hit)
        self.assertIs(first, second)
        # Second call dramatically faster
        self.assertLess(
            second_elapsed,
            first_elapsed * 0.5,
            f"cached call ({second_elapsed*1000:.1f}ms) "
            f"should be <50% of first "
            f"({first_elapsed*1000:.1f}ms)")
        # cache_info reports the hit
        info = (
            _build_default_quality_panel.cache_info())
        self.assertEqual(info.hits, 1)
        self.assertEqual(info.misses, 1)

    def test_importance_panel_cached(self):
        from rcm_mc.ui.feature_importance_viz import (
            _build_default_importance_panel,
        )
        _build_default_importance_panel.cache_clear()
        first = _build_default_importance_panel()
        second = _build_default_importance_panel()
        self.assertIs(first, second)
        info = (
            _build_default_importance_panel.cache_info())
        self.assertEqual(info.hits, 1)


if __name__ == "__main__":
    unittest.main()
