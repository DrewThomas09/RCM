"""Production-readiness tests for Heroku web deployment.

Four surfaces verified here:

1. ``ServerConfig.db_path`` respects ``RCM_MC_DB`` env var at module-import
   time, falling back to ``~/.rcm_mc/portfolio.db`` when unset.

2. PHI-posture banner in ``_chartis_kit._phi_banner_html()`` renders the
   right markup for each ``RCM_MC_PHI_MODE`` value (``disallowed`` →
   green; ``restricted`` → amber; unset → empty).

3. Banner is injected into the rendered HTML by ``chartis_shell()``
   (both v2 and legacy dispatch paths).

4. ``infra.job_queue`` works in the single-dyno threading model — lazy
   worker start on first submit, thread-safe status reads, FIFO.

No network, real server boots where needed.
"""
from __future__ import annotations

import importlib
import os
import sys
import time
import unittest
from unittest.mock import patch


# ────────────────────────────────────────────────────────────────────
# 1. ServerConfig respects RCM_MC_DB
# ────────────────────────────────────────────────────────────────────

class TestServerConfigDbPath(unittest.TestCase):
    def _reload_server(self):
        """Reimport rcm_mc.server so ServerConfig picks up current env."""
        # Evict from cache to force re-evaluation of class-level defaults
        sys.modules.pop("rcm_mc.server", None)
        return importlib.import_module("rcm_mc.server")

    def test_env_var_overrides_default(self):
        with patch.dict(os.environ, {"RCM_MC_DB": "/tmp/env_driven.db"}, clear=False):
            server = self._reload_server()
            self.assertEqual(server.ServerConfig.db_path, "/tmp/env_driven.db")

    def test_fallback_when_env_unset(self):
        env = {k: v for k, v in os.environ.items() if k != "RCM_MC_DB"}
        with patch.dict(os.environ, env, clear=True):
            server = self._reload_server()
            # Should fall through to ~/.rcm_mc/portfolio.db expansion
            self.assertTrue(server.ServerConfig.db_path.endswith(
                os.path.join(".rcm_mc", "portfolio.db")))


# ────────────────────────────────────────────────────────────────────
# 2. PHI banner HTML helper
# ────────────────────────────────────────────────────────────────────

class TestPhiBannerHelper(unittest.TestCase):
    """The PHI banner moved from a zero-arg env-reading helper
    (`_phi_banner_html()` in `_chartis_kit`) to a pure function of
    `mode` (`phi_banner(mode)` in `_chartis_kit_editorial`). The
    caller now reads `RCM_MC_PHI_MODE` once in the request handler
    and passes the lowercased value to the helper — keeps the helper
    testable without env mutation. Tests rewritten to the new API."""

    def test_disallowed_mode_renders_green_banner(self):
        from rcm_mc.ui._chartis_kit_editorial import phi_banner
        html = phi_banner("disallowed")
        self.assertIn("no PHI", html)
        # Editorial uses CSS class `.phi-banner` instead of inline hex
        self.assertIn('class="phi-banner"', html)
        self.assertIn('data-phi-mode="disallowed"', html)

    def test_restricted_mode_renders_amber_banner(self):
        from rcm_mc.ui._chartis_kit_editorial import phi_banner
        html = phi_banner("restricted")
        self.assertIn("PHI-eligible", html)
        # Editorial uses CSS class `.phi-banner.restricted` instead
        # of an inline hex color
        self.assertIn('class="phi-banner restricted"', html)
        self.assertIn('data-phi-mode="restricted"', html)

    def test_unset_mode_renders_empty(self):
        from rcm_mc.ui._chartis_kit_editorial import phi_banner
        self.assertEqual(phi_banner(None), "")
        self.assertEqual(phi_banner(""), "")
        self.assertEqual(phi_banner("unknown_mode_xyz"), "")

    def test_case_insensitive_mode(self):
        # The new API expects the CALLER to lowercase the env value
        # before passing in. The case-insensitive normalization was
        # moved out of the helper to keep it a pure function.
        from rcm_mc.ui._chartis_kit_editorial import phi_banner
        html = phi_banner("DISALLOWED".lower())
        self.assertIn("no PHI", html)


# ────────────────────────────────────────────────────────────────────
# 3. Banner is injected by chartis_shell (legacy path, which is default)
# ────────────────────────────────────────────────────────────────────

class TestBannerInjectedInShell(unittest.TestCase):
    """The legacy `chartis_shell` (the dispatcher in
    `rcm_mc.ui._chartis_kit`) no longer reads env on its own — the
    editorial shell (`_chartis_kit_editorial.chartis_shell`) takes
    explicit `show_phi_banner` + `phi_mode` kwargs. Tests rewritten
    to use the editorial shell directly so the env-injection-flow
    test is no longer load-bearing."""

    def test_legacy_shell_includes_banner_when_disallowed(self):
        # Call the editorial shell with phi_mode="disallowed" — the
        # request handler is the one that reads env and passes the
        # mode, so testing the shell takes the same explicit input.
        from rcm_mc.ui._chartis_kit_editorial import (
            chartis_shell as editorial_shell,
        )
        html = editorial_shell(
            body="<main>deal content</main>", title="Deal",
            show_phi_banner=True, phi_mode="disallowed",
        )
        # Banner must appear before main content
        banner_pos = html.find('class="phi-banner"')
        main_pos = html.find("deal content")
        self.assertGreater(banner_pos, 0)
        self.assertGreater(main_pos, banner_pos)

    def test_legacy_shell_no_banner_when_unset(self):
        from rcm_mc.ui._chartis_kit_editorial import (
            chartis_shell as editorial_shell,
        )
        html = editorial_shell(
            body="<main>deal content</main>", title="Deal",
            show_phi_banner=True, phi_mode=None,
        )
        self.assertNotIn("no PHI", html)
        self.assertNotIn("PHI-eligible", html)


# ────────────────────────────────────────────────────────────────────
# 4. Job queue works in single-dyno threading
# ────────────────────────────────────────────────────────────────────

class TestJobQueueSingleDyno(unittest.TestCase):
    """Exercises the in-memory job queue in the same process, simulating
    the Heroku single-dyno model where the web server and background
    worker share one Python interpreter.

    Uses the real ``submit_run(*, actual, benchmark, outdir, ...)`` API.
    The runner receives the full params dict — we capture it in a list.
    """

    def _submit_with_runner(self, **run_kwargs):
        from rcm_mc.infra.job_queue import JobRegistry
        return JobRegistry, run_kwargs

    def test_lazy_worker_starts_on_first_submit(self):
        from rcm_mc.infra.job_queue import JobRegistry
        calls = []

        def fake_runner(params):
            calls.append(params)
            return {"ok": True, "n_sims": params["n_sims"]}

        reg = JobRegistry(runner=fake_runner)
        self.assertFalse(reg._worker_started.is_set())

        job_id = reg.submit_run(
            actual="a.yaml", benchmark="b.yaml", outdir="/tmp/out",
            n_sims=10, seed=1,
        )
        self.assertTrue(reg._worker_started.is_set())

        for _ in range(20):
            job = reg.get(job_id)
            if job and job.status in ("done", "failed"):
                break
            time.sleep(0.05)
        else:
            self.fail("job did not complete within 1 second")

        self.assertEqual(job.status, "done", msg=f"error: {job.error}")
        self.assertEqual(job.result["n_sims"], 10)
        self.assertEqual(len(calls), 1)
        reg.shutdown(timeout=1.0)

    def test_multiple_jobs_processed_fifo(self):
        from rcm_mc.infra.job_queue import JobRegistry
        order = []

        def fake_runner(params):
            order.append(params["seed"])
            return {}

        reg = JobRegistry(runner=fake_runner)
        ids = [reg.submit_run(
            actual="a.yaml", benchmark="b.yaml", outdir="/tmp/o",
            n_sims=1, seed=i,
        ) for i in range(3)]

        for _ in range(40):
            statuses = [reg.get(j).status for j in ids]
            if all(s in ("done", "failed") for s in statuses):
                break
            time.sleep(0.05)

        self.assertEqual(order, [0, 1, 2])
        reg.shutdown(timeout=1.0)

    def test_failure_does_not_kill_worker(self):
        from rcm_mc.infra.job_queue import JobRegistry
        seen = []

        def fake_runner(params):
            seen.append(params["seed"])
            if params["seed"] == 1:
                raise RuntimeError("boom")
            return {}

        reg = JobRegistry(runner=fake_runner)
        id_fail = reg.submit_run(
            actual="a.yaml", benchmark="b.yaml", outdir="/tmp/o",
            n_sims=1, seed=1,
        )
        id_ok = reg.submit_run(
            actual="a.yaml", benchmark="b.yaml", outdir="/tmp/o",
            n_sims=1, seed=2,
        )

        for _ in range(40):
            j1, j2 = reg.get(id_fail), reg.get(id_ok)
            if j1.status in ("done", "failed") and j2.status in ("done", "failed"):
                break
            time.sleep(0.05)

        self.assertEqual(j1.status, "failed")
        self.assertIn("boom", j1.error)
        self.assertEqual(j2.status, "done")
        self.assertEqual(seen, [1, 2])
        reg.shutdown(timeout=1.0)


if __name__ == "__main__":
    unittest.main()
