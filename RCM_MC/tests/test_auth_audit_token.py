"""Tests for ``rcm_mc/auth/audit_token.py`` — time-boxed read-only
audit access.

This is an **auth bypass mechanism** with a deliberately narrow surface
+ fail-closed posture. Every contract in this module is security-
critical:

  * OFF BY DEFAULT (env var unset → mint/verify both return None)
  * TIME-BOXED (24h max; signed expiry baked into the token)
  * SIGNED (HMAC-SHA256 with constant-time compare — cannot be forged
    or extended without the secret)
  * INSTANT KILL (clear env var → every outstanding token dies on
    next verify call, no server action needed)

Module had no direct unit-test coverage. Locking the contract before
any tweak silently weakens the security posture is worth doing —
every assertion in here is also documenting the intended behavior
for a reviewer.
"""
from __future__ import annotations

import os
import time
import unittest
from unittest import mock

from rcm_mc.auth.audit_token import (
    audit_enabled,
    mint,
    verify,
)


# Helper to scope an env-var override to a single test.
class _SecretScope:
    def __init__(self, value):
        self.value = value

    def __enter__(self):
        self._prev = os.environ.get("RCM_MC_AUDIT_SECRET")
        if self.value is None:
            os.environ.pop("RCM_MC_AUDIT_SECRET", None)
        else:
            os.environ["RCM_MC_AUDIT_SECRET"] = self.value
        return self

    def __exit__(self, *exc):
        if self._prev is None:
            os.environ.pop("RCM_MC_AUDIT_SECRET", None)
        else:
            os.environ["RCM_MC_AUDIT_SECRET"] = self._prev


# ---------------------------------------------------------------------------
# audit_enabled — the master on/off
# ---------------------------------------------------------------------------


class AuditEnabledTests(unittest.TestCase):

    def test_disabled_when_no_secret(self):
        with _SecretScope(None):
            self.assertFalse(audit_enabled())

    def test_disabled_when_empty_secret(self):
        # Empty string env var → treated as unset (whitespace stripped).
        with _SecretScope(""):
            self.assertFalse(audit_enabled())

    def test_disabled_when_whitespace_only_secret(self):
        # Whitespace-only secret is dangerous-looking but inert.
        with _SecretScope("   "):
            self.assertFalse(audit_enabled())

    def test_enabled_when_secret_set(self):
        with _SecretScope("my-secret-value-32-chars-long-token"):
            self.assertTrue(audit_enabled())


# ---------------------------------------------------------------------------
# mint — token minting
# ---------------------------------------------------------------------------


class MintTests(unittest.TestCase):

    def test_returns_none_when_disabled(self):
        with _SecretScope(None):
            self.assertIsNone(mint())

    def test_returns_string_when_enabled(self):
        with _SecretScope("test-secret"):
            tok = mint()
            self.assertIsInstance(tok, str)

    def test_token_format_is_expiry_dot_signature(self):
        with _SecretScope("test-secret"):
            tok = mint(hours=1)
            self.assertIn(".", tok)
            exp_str, _, sig = tok.partition(".")
            # Expiry parses to int.
            self.assertEqual(str(int(exp_str)), exp_str)
            # Signature is 64-char hex (sha256 hexdigest).
            self.assertEqual(len(sig), 64)
            int(sig, 16)  # raises if not hex

    def test_default_hours_is_2(self):
        # mint() with no args → ~2 hours from now.
        with _SecretScope("test-secret"):
            now = int(time.time())
            tok = mint()
            exp = int(tok.split(".")[0])
            # Allow a small skew (1-2 seconds).
            self.assertAlmostEqual(exp - now, 2 * 3600, delta=5)

    def test_custom_hours(self):
        with _SecretScope("test-secret"):
            now = int(time.time())
            tok = mint(hours=6)
            exp = int(tok.split(".")[0])
            self.assertAlmostEqual(exp - now, 6 * 3600, delta=5)

    def test_caps_at_24_hours(self):
        # The 24h cap is a security guarantee — locked.
        with _SecretScope("test-secret"):
            now = int(time.time())
            tok = mint(hours=72)
            exp = int(tok.split(".")[0])
            # Should be ~24h, not 72h.
            self.assertAlmostEqual(exp - now, 24 * 3600, delta=5)

    def test_floors_at_short_window(self):
        # Below 0.1h is floored to 0.1h (6 minutes) to keep behavior
        # consistent — locked.
        with _SecretScope("test-secret"):
            now = int(time.time())
            tok = mint(hours=0.001)
            exp = int(tok.split(".")[0])
            # 0.1 * 3600 = 360 seconds.
            self.assertAlmostEqual(exp - now, 360, delta=5)


# ---------------------------------------------------------------------------
# verify — token verification (the fail-closed surface)
# ---------------------------------------------------------------------------


class VerifyHappyPathTests(unittest.TestCase):

    def test_valid_token_returns_expiry(self):
        with _SecretScope("test-secret"):
            tok = mint(hours=1)
            exp = verify(tok)
            self.assertIsInstance(exp, int)

    def test_returned_expiry_matches_token_expiry(self):
        with _SecretScope("test-secret"):
            tok = mint(hours=1)
            exp_from_token = int(tok.split(".")[0])
            exp_from_verify = verify(tok)
            self.assertEqual(exp_from_verify, exp_from_token)


class VerifyFailClosedTests(unittest.TestCase):
    """Fail-closed: ANY abnormal input → None. No exceptions raised."""

    def test_none_token_returns_none(self):
        with _SecretScope("test-secret"):
            self.assertIsNone(verify(None))

    def test_empty_token_returns_none(self):
        with _SecretScope("test-secret"):
            self.assertIsNone(verify(""))

    def test_token_without_dot_returns_none(self):
        with _SecretScope("test-secret"):
            self.assertIsNone(verify("no-dot-here"))

    def test_token_with_non_int_expiry_returns_none(self):
        with _SecretScope("test-secret"):
            self.assertIsNone(verify("not-a-number.fakehex"))

    def test_token_with_wrong_signature_returns_none(self):
        # Build a token by hand with an expiry but garbage signature.
        with _SecretScope("test-secret"):
            future = int(time.time()) + 3600
            bad = f"{future}." + "0" * 64
            self.assertIsNone(verify(bad))

    def test_expired_token_returns_none(self):
        # Mint a token at hours=0.1 (~6 minutes), then simulate that
        # time has passed by mocking time.time.
        with _SecretScope("test-secret"):
            tok = mint(hours=0.1)
            exp = int(tok.split(".")[0])
            with mock.patch("rcm_mc.auth.audit_token.time.time",
                             return_value=exp + 100):
                self.assertIsNone(verify(tok))

    def test_disabled_invalidates_existing_tokens(self):
        # 'INSTANT KILL' security promise: mint with one secret, then
        # clear the secret → all existing tokens are dead immediately.
        with _SecretScope("first-secret"):
            tok = mint(hours=1)
            self.assertIsNotNone(verify(tok))  # valid right now
        # Secret unset → previously-valid token now invalid.
        with _SecretScope(None):
            self.assertIsNone(verify(tok))

    def test_rotating_secret_invalidates_old_tokens(self):
        # 'panic button' — rotate secret → outstanding tokens die.
        with _SecretScope("old-secret"):
            tok = mint(hours=1)
        # Server rotates to a new secret.
        with _SecretScope("new-secret"):
            self.assertIsNone(verify(tok))


class VerifyConstantTimeTests(unittest.TestCase):
    """The signature compare uses hmac.compare_digest (constant-time)
    so timing side-channels can't leak the secret. We can't test
    timing directly, but we CAN assert that two signatures of equal
    length but different content both return None — a regression to
    a naive == comparison would still return None, but the docstring
    contract is what matters here. This test exists as documentation
    + a sentinel against the obvious shortcut."""

    def test_different_signatures_both_rejected(self):
        with _SecretScope("test-secret"):
            future = int(time.time()) + 3600
            # Two tokens with identical expiry but different fake sigs.
            sig1 = "a" * 64
            sig2 = "b" * 64
            self.assertIsNone(verify(f"{future}.{sig1}"))
            self.assertIsNone(verify(f"{future}.{sig2}"))


class CrossSecretTests(unittest.TestCase):

    def test_token_minted_with_one_secret_verifies_only_with_same(self):
        with _SecretScope("alpha"):
            tok = mint(hours=1)
        with _SecretScope("alpha"):
            self.assertIsNotNone(verify(tok))
        with _SecretScope("beta"):
            self.assertIsNone(verify(tok))


if __name__ == "__main__":
    unittest.main()
