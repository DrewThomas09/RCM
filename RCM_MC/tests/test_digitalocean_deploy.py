"""Guardrails for the DigitalOcean deployment package (docs + scripts).

Asserts the deploy artifacts exist, carry no hardcoded secrets, and that the
docs hold the security boundaries (never expose Ollama 11434, never commit
the prod env, DO hosts the web app while the Mac hosts Ollama, via Tailscale).
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = ["scripts/do_bootstrap_server.sh", "scripts/do_preflight.sh",
            "scripts/do_run_pedesk.sh"]
_DOC = _ROOT / "docs" / "DIGITALOCEAN_DEPLOYMENT.md"


class DeployArtifactsTests(unittest.TestCase):
    def test_scripts_and_examples_exist(self):
        for s in _SCRIPTS:
            self.assertTrue((_ROOT / s).is_file(), s)
        self.assertTrue(_DOC.is_file())
        self.assertTrue((_ROOT / "docs" / "pedesk.service.example").is_file())
        self.assertTrue((_ROOT / "docs" / "Caddyfile.example").is_file())

    def test_scripts_have_no_hardcoded_secrets(self):
        # No assigned password/token/auth values; placeholders only.
        secretish = re.compile(
            r"(RCM_MC_AUTH|PASSWORD|TOKEN|SECRET)\s*=\s*['\"]?[A-Za-z0-9!@#$%^&*_\-]{6,}",
            re.IGNORECASE,
        )
        for s in _SCRIPTS + ["docs/pedesk.service.example", "docs/Caddyfile.example"]:
            text = (_ROOT / s).read_text()
            self.assertIsNone(secretish.search(text),
                              f"{s} appears to contain a hardcoded secret")

    def test_scripts_load_env_without_echoing_it(self):
        # Scripts must read .pedesk_prod.env but never `cat`/`echo` its contents.
        for s in ("scripts/do_preflight.sh", "scripts/do_run_pedesk.sh"):
            text = (_ROOT / s).read_text()
            self.assertIn(".pedesk_prod.env", text)
            self.assertNotIn("cat .pedesk_prod.env", text)
            self.assertNotIn("echo $RCM_MC_AUTH", text)


class DeployDocSecurityTests(unittest.TestCase):
    def setUp(self):
        self.doc = _DOC.read_text()

    def test_warns_never_expose_ollama_11434(self):
        low = self.doc.lower()
        self.assertIn("11434", self.doc)
        self.assertTrue("never expose" in low or "not expose" in low
                        or "never exposed" in low)
        # explicitly tied to Ollama
        self.assertIn("ollama", low)

    def test_mentions_tailscale_private_path(self):
        self.assertIn("Tailscale", self.doc)

    def test_prod_env_must_not_be_committed(self):
        low = self.doc.lower()
        self.assertIn(".pedesk_prod.env", self.doc)
        self.assertTrue("never commit" in low or "not commit" in low
                        or "git-ignored" in low)

    def test_split_responsibility_documented(self):
        low = self.doc.lower()
        self.assertIn("web app only", low)   # DO hosts the web app only
        self.assertIn("mac hosts ollama", low)


class GitignoreTests(unittest.TestCase):
    def test_prod_env_is_gitignored(self):
        gi = (_ROOT / ".gitignore").read_text()
        self.assertIn(".pedesk_prod.env", gi)
        self.assertIn(".pedesk_host_auth.env", gi)


if __name__ == "__main__":
    unittest.main()
