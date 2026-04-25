"""Static validation of the Azure VM deploy files.

Doesn't boot Docker (not worth the CI cost). Instead, validates that:

  1. Dockerfile's CMD includes --host 0.0.0.0 — the origin must bind
     to all interfaces or Caddy can't reach it. This is the exact
     bug DEPLOYMENT_PLAN.md flagged.

  2. docker-compose.yml is valid YAML and includes the Caddy sidecar
     gated behind the `tls` profile (opt-in).

  3. Caddyfile references the DOMAIN placeholder and sets
     X-Forwarded-Proto: https on the upstream — required for the
     origin to detect HTTPS and emit HSTS + Secure cookies.

  4. vm_setup.sh accepts an optional domain argument and wires it
     through to docker compose --profile tls.

These are cheap unit tests — they fail fast if someone edits a
deploy file in a way that breaks the production path without
realizing it.
"""
from __future__ import annotations

import os
import pathlib
import re
import unittest


DEPLOY_DIR = (pathlib.Path(__file__).parent.parent / "deploy").resolve()


class TestDockerfile(unittest.TestCase):
    def test_host_flag_in_cmd(self):
        """Critical regression: the container must bind 0.0.0.0."""
        src = (DEPLOY_DIR / "Dockerfile").read_text()
        # The CMD line should carry `--host 0.0.0.0` somewhere, in any
        # quoting style ("--host", "0.0.0.0" is what we wrote).
        cmd_line = next(
            (ln for ln in src.splitlines() if ln.startswith("CMD")),
            "",
        )
        self.assertIn("--host", cmd_line,
                      msg="Dockerfile CMD must pass --host (0.0.0.0) "
                          "or Caddy can't reach the origin")
        self.assertIn("0.0.0.0", cmd_line,
                      msg="Dockerfile CMD must bind to 0.0.0.0")


class TestComposeFile(unittest.TestCase):
    def setUp(self):
        self.src = (DEPLOY_DIR / "docker-compose.yml").read_text()

    def test_caddy_service_defined(self):
        self.assertIn("caddy:", self.src,
                      msg="compose should define a caddy service")
        self.assertIn("caddy:2-alpine", self.src,
                      msg="caddy image pin should be present")

    def test_caddy_gated_behind_tls_profile(self):
        """The caddy service must be in the `tls` profile so
        `docker compose up` alone starts only the origin, not the
        TLS terminator. Avoids surprise LE challenges on local test."""
        # Look for "profiles:" followed by the tls entry inside the
        # caddy block. Simple substring match is robust to YAML
        # formatting changes.
        self.assertIn("profiles:", self.src)
        self.assertIn("- tls", self.src)

    def test_origin_has_host_0_0_0_0_implied(self):
        """The rcm-mc service entry should expose 8080 (even if
        it doesn't publish to the host). `expose:` means the port
        is reachable on the Docker internal network."""
        self.assertIn("rcm-mc:", self.src)
        self.assertRegex(self.src,
                         r"expose:\s*\n\s*-\s*['\"]?8080['\"]?")

    def test_domain_env_is_required_when_caddy_up(self):
        """The DOMAIN var uses `${DOMAIN:?...}` syntax so compose
        fails fast with a clear error when someone tries to bring
        Caddy up without setting the domain."""
        self.assertIn("${DOMAIN:?", self.src,
                      msg="caddy service must require DOMAIN env")

    def test_caddy_data_volume_persists(self):
        """Persisted volume for Let's Encrypt certs — rate limits
        make re-issuing on every restart painful."""
        self.assertIn("caddy_data:", self.src)


class TestCaddyfile(unittest.TestCase):
    def setUp(self):
        self.src = (DEPLOY_DIR / "Caddyfile").read_text()

    def test_domain_placeholder(self):
        self.assertIn("{$DOMAIN}", self.src,
                      msg="Caddyfile must use {$DOMAIN} so compose "
                          "substitutes at startup")

    def test_reverse_proxy_to_origin(self):
        self.assertRegex(self.src,
                         r"reverse_proxy\s+rcm-mc:8080")

    def test_forwards_proto_header(self):
        """Origin relies on X-Forwarded-Proto to detect HTTPS —
        without this, _is_https() returns False and HSTS / Secure
        cookies never fire even behind Caddy."""
        self.assertRegex(
            self.src,
            r"header_up\s+X-Forwarded-Proto\s+https",
            msg="Caddyfile must forward X-Forwarded-Proto: https "
                "so the origin emits HSTS + Secure cookies",
        )

    def test_security_headers_at_edge(self):
        # Belt-and-suspenders headers at the edge in case the origin
        # ever forgets them.
        self.assertIn("Strict-Transport-Security", self.src)
        self.assertIn("X-Frame-Options", self.src)


class TestVmSetupScript(unittest.TestCase):
    def setUp(self):
        self.src = (DEPLOY_DIR / "vm_setup.sh").read_text()

    def test_accepts_domain_arg(self):
        # Domain is the 3rd positional — optional
        self.assertRegex(self.src, r'DOMAIN="\$\{3:-\}"')

    def test_uses_tls_profile_when_domain_set(self):
        self.assertRegex(
            self.src,
            r'--profile\s+tls',
            msg="vm_setup must bring up the tls profile when DOMAIN is set",
        )

    def test_branches_on_domain(self):
        # The script must handle both "with domain" and "without domain"
        # branches — otherwise running without a domain breaks.
        self.assertIn('if [ -n "$DOMAIN" ]', self.src)


if __name__ == "__main__":
    unittest.main()
