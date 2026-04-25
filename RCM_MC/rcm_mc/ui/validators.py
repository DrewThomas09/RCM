"""Form input validation — composable validators with clear
error messages.

Recent UI sprint introduced forms (user preferences,
notifications, custom dashboard widgets) but validation was
scattered across ad-hoc try/except + raw ValueError raises.
This module centralizes validators so every form on the
platform produces consistent error copy ('Email must be a valid
email' / 'Items per page must be between 5 and 200') instead of
'invalid literal for int() with base 10'.

Architecture:

  • Each validator is a function: ``validate_X(value, **opts)
    -> ValidationResult``. Returns either ``ok(cleaned_value)``
    or ``err(message)``.
  • ``validate_form(spec, values)`` runs every validator in a
    spec dict, returning a FormResult with cleaned values +
    a per-field error map.
  • ``render_field_error(message)`` produces the inline error
    text the partner sees below a form field.

Pure stdlib; no extra deps.

Public API::

    from rcm_mc.ui.validators import (
        ValidationResult, FormResult,
        validate_email, validate_int_range,
        validate_choice, validate_required,
        validate_username, validate_ccn,
        validate_form, render_field_error,
    )
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ValidationResult:
    """Outcome of a single field validation."""
    ok: bool
    value: Any = None
    error: str = ""


def ok(value: Any) -> ValidationResult:
    return ValidationResult(ok=True, value=value)


def err(message: str) -> ValidationResult:
    return ValidationResult(ok=False, error=message)


# ── Single-field validators ─────────────────────────────────

# RFC 5322 simple subset — practical for partner-facing forms.
_EMAIL_RE = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def validate_email(
    value: Any, *, required: bool = True,
) -> ValidationResult:
    """Validate an email address."""
    if value is None or str(value).strip() == "":
        if required:
            return err("Email is required.")
        return ok(None)
    s = str(value).strip()
    if len(s) > 254:
        return err(
            "Email must be 254 characters or fewer.")
    if not _EMAIL_RE.match(s):
        return err(
            "Email must be a valid address "
            "(e.g. name@example.com).")
    return ok(s.lower())


def validate_int_range(
    value: Any,
    *,
    min_value: int,
    max_value: int,
    field_name: str = "Value",
) -> ValidationResult:
    """Integer in [min_value, max_value]."""
    if value is None or value == "":
        return err(f"{field_name} is required.")
    try:
        n = int(str(value).strip())
    except (TypeError, ValueError):
        return err(
            f"{field_name} must be a whole number.")
    if n < min_value or n > max_value:
        return err(
            f"{field_name} must be between "
            f"{min_value} and {max_value}.")
    return ok(n)


def validate_float_range(
    value: Any,
    *,
    min_value: float,
    max_value: float,
    field_name: str = "Value",
) -> ValidationResult:
    """Float in [min_value, max_value]."""
    if value is None or value == "":
        return err(f"{field_name} is required.")
    try:
        n = float(str(value).strip())
    except (TypeError, ValueError):
        return err(
            f"{field_name} must be a number.")
    if n < min_value or n > max_value:
        return err(
            f"{field_name} must be between "
            f"{min_value} and {max_value}.")
    return ok(n)


def validate_choice(
    value: Any,
    *,
    choices: List[Any],
    field_name: str = "Value",
) -> ValidationResult:
    """Value must be one of the listed choices."""
    if value is None or value == "":
        return err(f"{field_name} is required.")
    if value not in choices:
        return err(
            f"{field_name} must be one of: "
            f"{', '.join(str(c) for c in choices)}.")
    return ok(value)


def validate_required(
    value: Any, *, field_name: str = "Value",
    max_length: Optional[int] = None,
) -> ValidationResult:
    """Non-empty string with optional max-length cap."""
    if value is None:
        return err(f"{field_name} is required.")
    s = str(value).strip()
    if not s:
        return err(f"{field_name} is required.")
    if max_length and len(s) > max_length:
        return err(
            f"{field_name} must be {max_length} "
            f"characters or fewer.")
    return ok(s)


# Username: 3-32 chars, alphanumeric + underscore + dash.
_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_-]{3,32}$")


def validate_username(value: Any) -> ValidationResult:
    if value is None or str(value).strip() == "":
        return err("Username is required.")
    s = str(value).strip()
    if not _USERNAME_RE.match(s):
        return err(
            "Username must be 3-32 characters: "
            "letters, numbers, underscore, or dash.")
    return ok(s)


# CCN: CMS Certification Number — 6 digits.
_CCN_RE = re.compile(r"^\d{6}$")


def validate_ccn(value: Any) -> ValidationResult:
    if value is None or str(value).strip() == "":
        return err("CCN is required.")
    s = str(value).strip()
    if not _CCN_RE.match(s):
        return err(
            "CCN must be a 6-digit Medicare "
            "certification number.")
    return ok(s)


# NPI: National Provider Identifier — 10 digits.
_NPI_RE = re.compile(r"^\d{10}$")


def validate_npi(value: Any) -> ValidationResult:
    if value is None or str(value).strip() == "":
        return err("NPI is required.")
    s = str(value).strip()
    if not _NPI_RE.match(s):
        return err(
            "NPI must be a 10-digit National "
            "Provider Identifier.")
    return ok(s)


def validate_url(
    value: Any, *, required: bool = True,
) -> ValidationResult:
    """URL must start with http:// or https://."""
    if value is None or str(value).strip() == "":
        if required:
            return err("URL is required.")
        return ok(None)
    s = str(value).strip()
    if not (s.startswith("http://")
            or s.startswith("https://")):
        return err(
            "URL must start with http:// or https://.")
    if len(s) > 2048:
        return err(
            "URL must be 2048 characters or fewer.")
    return ok(s)


# ── Form-level orchestration ────────────────────────────────

@dataclass
class FormResult:
    """Outcome of validating a whole form."""
    ok: bool
    cleaned: Dict[str, Any] = field(default_factory=dict)
    errors: Dict[str, str] = field(default_factory=dict)


def validate_form(
    spec: Dict[str, Callable[[Any], ValidationResult]],
    values: Dict[str, Any],
) -> FormResult:
    """Run every validator in the spec.

    Args:
      spec: dict of field_name → validator function. Each
        validator takes one value and returns a
        ValidationResult.
      values: submitted values (typically request.form).

    Returns: FormResult with ok=True only when every field
    validated. cleaned is the per-field cleaned values
    (whatever the validator returned via ok()); errors is the
    per-field error message.
    """
    cleaned: Dict[str, Any] = {}
    errors: Dict[str, str] = {}
    for field_name, validator in spec.items():
        v = values.get(field_name)
        result = validator(v)
        if result.ok:
            cleaned[field_name] = result.value
        else:
            errors[field_name] = result.error
    return FormResult(
        ok=not errors,
        cleaned=cleaned,
        errors=errors)


# ── UI helper ───────────────────────────────────────────────

def render_field_error(message: str) -> str:
    """Inline error text under a form field. HTML-escaped.

    Intended to render directly below the input; partner sees
    'Email must be a valid address.' in red after submit fail.
    """
    import html as _html
    if not message:
        return ""
    return (
        f'<div role="alert" '
        f'style="color:#ef4444;font-size:12px;'
        f'margin-top:4px;">'
        f'{_html.escape(message)}</div>')
