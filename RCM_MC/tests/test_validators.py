"""Tests for form input validators."""
from __future__ import annotations

import unittest


class TestValidateEmail(unittest.TestCase):
    def test_valid_email(self):
        from rcm_mc.ui.validators import validate_email
        r = validate_email("user@example.com")
        self.assertTrue(r.ok)
        self.assertEqual(r.value, "user@example.com")

    def test_lowercased(self):
        from rcm_mc.ui.validators import validate_email
        r = validate_email("User@Example.COM")
        self.assertEqual(r.value, "user@example.com")

    def test_missing_at(self):
        from rcm_mc.ui.validators import validate_email
        r = validate_email("notanemail")
        self.assertFalse(r.ok)
        self.assertIn("valid", r.error)

    def test_missing_tld(self):
        from rcm_mc.ui.validators import validate_email
        r = validate_email("user@host")
        self.assertFalse(r.ok)

    def test_required_empty_fails(self):
        from rcm_mc.ui.validators import validate_email
        r = validate_email("", required=True)
        self.assertFalse(r.ok)
        self.assertIn("required", r.error)

    def test_optional_empty_passes(self):
        from rcm_mc.ui.validators import validate_email
        r = validate_email("", required=False)
        self.assertTrue(r.ok)
        self.assertIsNone(r.value)

    def test_too_long_rejected(self):
        from rcm_mc.ui.validators import validate_email
        long_email = "a" * 250 + "@x.co"
        r = validate_email(long_email)
        self.assertFalse(r.ok)
        self.assertIn("254", r.error)


class TestValidateIntRange(unittest.TestCase):
    def test_in_range(self):
        from rcm_mc.ui.validators import (
            validate_int_range,
        )
        r = validate_int_range(
            25, min_value=5, max_value=200)
        self.assertTrue(r.ok)
        self.assertEqual(r.value, 25)

    def test_below_min(self):
        from rcm_mc.ui.validators import (
            validate_int_range,
        )
        r = validate_int_range(
            3, min_value=5, max_value=200,
            field_name="Items per page")
        self.assertFalse(r.ok)
        self.assertIn("Items per page", r.error)
        self.assertIn("5", r.error)
        self.assertIn("200", r.error)

    def test_not_an_integer(self):
        from rcm_mc.ui.validators import (
            validate_int_range,
        )
        r = validate_int_range(
            "abc", min_value=0, max_value=10)
        self.assertFalse(r.ok)
        self.assertIn("whole number", r.error)

    def test_string_int_accepted(self):
        from rcm_mc.ui.validators import (
            validate_int_range,
        )
        r = validate_int_range(
            "42", min_value=0, max_value=100)
        self.assertTrue(r.ok)
        self.assertEqual(r.value, 42)

    def test_empty_required(self):
        from rcm_mc.ui.validators import (
            validate_int_range,
        )
        r = validate_int_range(
            "", min_value=0, max_value=10)
        self.assertFalse(r.ok)


class TestValidateChoice(unittest.TestCase):
    def test_valid(self):
        from rcm_mc.ui.validators import validate_choice
        r = validate_choice(
            "dashboard_v3",
            choices=["dashboard_v3", "legacy_dashboard"])
        self.assertTrue(r.ok)

    def test_invalid(self):
        from rcm_mc.ui.validators import validate_choice
        r = validate_choice(
            "purple",
            choices=["red", "blue"])
        self.assertFalse(r.ok)
        self.assertIn("red", r.error)
        self.assertIn("blue", r.error)


class TestValidateRequired(unittest.TestCase):
    def test_basic(self):
        from rcm_mc.ui.validators import (
            validate_required,
        )
        self.assertTrue(
            validate_required("hello").ok)
        self.assertFalse(
            validate_required("").ok)
        self.assertFalse(
            validate_required("   ").ok)
        self.assertFalse(
            validate_required(None).ok)

    def test_strips_whitespace(self):
        from rcm_mc.ui.validators import (
            validate_required,
        )
        r = validate_required("  hi  ")
        self.assertEqual(r.value, "hi")

    def test_max_length(self):
        from rcm_mc.ui.validators import (
            validate_required,
        )
        r = validate_required(
            "a" * 100,
            field_name="Note", max_length=50)
        self.assertFalse(r.ok)
        self.assertIn("Note", r.error)
        self.assertIn("50", r.error)


class TestValidateUsername(unittest.TestCase):
    def test_valid(self):
        from rcm_mc.ui.validators import (
            validate_username,
        )
        for u in ["alice", "alice_smith",
                  "alice-smith", "user123"]:
            self.assertTrue(
                validate_username(u).ok,
                f"{u} should be valid")

    def test_too_short(self):
        from rcm_mc.ui.validators import (
            validate_username,
        )
        self.assertFalse(validate_username("ab").ok)

    def test_too_long(self):
        from rcm_mc.ui.validators import (
            validate_username,
        )
        self.assertFalse(
            validate_username("a" * 33).ok)

    def test_invalid_chars(self):
        from rcm_mc.ui.validators import (
            validate_username,
        )
        for bad in ["alice smith", "alice@x",
                    "alice.smith", "<script>"]:
            self.assertFalse(
                validate_username(bad).ok,
                f"{bad} should be rejected")


class TestValidateCCN(unittest.TestCase):
    def test_valid(self):
        from rcm_mc.ui.validators import validate_ccn
        self.assertTrue(validate_ccn("450001").ok)

    def test_too_few_digits(self):
        from rcm_mc.ui.validators import validate_ccn
        self.assertFalse(validate_ccn("4500").ok)

    def test_non_digits(self):
        from rcm_mc.ui.validators import validate_ccn
        self.assertFalse(validate_ccn("4500AB").ok)


class TestValidateNPI(unittest.TestCase):
    def test_valid(self):
        from rcm_mc.ui.validators import validate_npi
        self.assertTrue(validate_npi("1003456789").ok)

    def test_wrong_length(self):
        from rcm_mc.ui.validators import validate_npi
        self.assertFalse(validate_npi("123").ok)


class TestValidateURL(unittest.TestCase):
    def test_https_ok(self):
        from rcm_mc.ui.validators import validate_url
        self.assertTrue(
            validate_url(
                "https://example.com/path").ok)

    def test_http_ok(self):
        from rcm_mc.ui.validators import validate_url
        self.assertTrue(
            validate_url("http://example.com").ok)

    def test_ftp_rejected(self):
        from rcm_mc.ui.validators import validate_url
        self.assertFalse(
            validate_url("ftp://example.com").ok)

    def test_javascript_rejected(self):
        """XSS guard — javascript: URLs blocked."""
        from rcm_mc.ui.validators import validate_url
        self.assertFalse(
            validate_url("javascript:alert(1)").ok)

    def test_optional_empty(self):
        from rcm_mc.ui.validators import validate_url
        r = validate_url("", required=False)
        self.assertTrue(r.ok)


class TestValidateForm(unittest.TestCase):
    def test_all_valid(self):
        from rcm_mc.ui.validators import (
            validate_form, validate_email,
            validate_int_range, validate_choice,
        )
        spec = {
            "email": validate_email,
            "items_per_page": (
                lambda v: validate_int_range(
                    v, min_value=5,
                    max_value=200,
                    field_name="Items per page")),
            "default_view": (
                lambda v: validate_choice(
                    v, choices=["dashboard_v3",
                                "legacy_dashboard"],
                    field_name="Default view")),
        }
        result = validate_form(spec, {
            "email": "alice@example.com",
            "items_per_page": "50",
            "default_view": "dashboard_v3",
        })
        self.assertTrue(result.ok)
        self.assertEqual(
            result.cleaned["email"],
            "alice@example.com")
        self.assertEqual(
            result.cleaned["items_per_page"], 50)
        self.assertEqual(result.errors, {})

    def test_partial_failure_collects_all_errors(self):
        from rcm_mc.ui.validators import (
            validate_form, validate_email,
            validate_int_range,
        )
        spec = {
            "email": validate_email,
            "items_per_page": (
                lambda v: validate_int_range(
                    v, min_value=5, max_value=200,
                    field_name="Items per page")),
        }
        result = validate_form(spec, {
            "email": "bad",
            "items_per_page": "9999",
        })
        self.assertFalse(result.ok)
        # Both errors present
        self.assertIn("email", result.errors)
        self.assertIn(
            "items_per_page", result.errors)


class TestRenderFieldError(unittest.TestCase):
    def test_renders_in_red(self):
        from rcm_mc.ui.validators import (
            render_field_error,
        )
        html = render_field_error(
            "Email is required.")
        self.assertIn("Email is required", html)
        self.assertIn("#ef4444", html)
        self.assertIn('role="alert"', html)

    def test_html_escape(self):
        from rcm_mc.ui.validators import (
            render_field_error,
        )
        html = render_field_error("<script>alert(1)</script>")
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_empty_returns_empty(self):
        from rcm_mc.ui.validators import (
            render_field_error,
        )
        self.assertEqual(render_field_error(""), "")


if __name__ == "__main__":
    unittest.main()
