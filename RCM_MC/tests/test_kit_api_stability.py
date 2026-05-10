"""Stability guard for the kit's public API.

Many UI pages import these primitives by name. Removing or
renaming any of them silently breaks 50+ pages at import time —
the failure surfaces as ``ImportError`` from each consumer
instead of a single clear "you removed the kit primitive" error.

This guard imports every primitive directly and asserts each is
callable. If a contributor renames or deletes one, this single
test fails with a clear message before the rest of the suite
goes red.

The list is the canonical kit API surface. Adding a new primitive
here documents its public-API status; removing one requires a
deprecation migration (block legacy callers + provide the new
primitive in parallel).
"""
from __future__ import annotations

import unittest


# (module_path, attribute_name)
KIT_PRIMITIVES = [
    # _ui_kit — the rendering helpers
    ("rcm_mc.ui._ui_kit", "format_value"),
    ("rcm_mc.ui._ui_kit", "kpi_strip"),
    ("rcm_mc.ui._ui_kit", "data_table"),
    ("rcm_mc.ui._ui_kit", "empty_state"),
    ("rcm_mc.ui._ui_kit", "preview_panel"),
    ("rcm_mc.ui._ui_kit", "recent_runs"),
    ("rcm_mc.ui._ui_kit", "recommendation_block"),
    ("rcm_mc.ui._ui_kit", "provenance_marker"),
    ("rcm_mc.ui._ui_kit", "section_header"),
    ("rcm_mc.ui._ui_kit", "metric_with_interval"),
    ("rcm_mc.ui._ui_kit", "metric_with_delta"),

    # _chartis_kit — the dispatching shell
    ("rcm_mc.ui._chartis_kit", "chartis_shell"),

    # brand — the palette
    ("rcm_mc.ui.brand", "PALETTE"),

    # voice_audit — the audit functions used by compliance rules
    ("rcm_mc.ui.voice_audit", "audit_string"),
    ("rcm_mc.ui.voice_audit", "audit_button_label"),
    ("rcm_mc.ui.voice_audit", "audit_number_format"),

    # compliance_sweep — the rule registry + scorer
    ("rcm_mc.ui.compliance_sweep", "RULES"),
    ("rcm_mc.ui.compliance_sweep", "compliance_check"),
]


class KitPrimitivesAreImportable(unittest.TestCase):
    """Each primitive on the canonical-API list must be importable
    from its declared module."""

    def test_each_primitive_resolves(self) -> None:
        import importlib
        missing: list[str] = []
        for mod_path, attr in KIT_PRIMITIVES:
            try:
                mod = importlib.import_module(mod_path)
            except ImportError as e:
                missing.append(f"{mod_path}: import failed ({e})")
                continue
            if not hasattr(mod, attr):
                missing.append(f"{mod_path}.{attr}: attribute missing")
        self.assertEqual(
            missing, [],
            f"{len(missing)} kit primitives are missing or "
            f"un-importable. The kit API has shrunk — either "
            f"restore the symbol or remove it from "
            f"KIT_PRIMITIVES with a deprecation rationale.\n"
            + "\n".join(f"  {m}" for m in missing),
        )

    def test_callable_primitives_are_callable(self) -> None:
        """Function primitives must remain callable. Catches the
        case where a primitive gets converted to a value-only
        attribute (e.g., a class instance) without callers being
        notified."""
        import importlib
        non_callable: list[str] = []
        # Subset of primitives that must be callable (i.e. functions,
        # not constants). PALETTE is a dict; RULES is a list — both
        # are values.
        CALLABLE = {
            "format_value", "kpi_strip", "data_table", "empty_state",
            "preview_panel", "recent_runs", "recommendation_block",
            "provenance_marker", "section_header",
            "metric_with_interval", "metric_with_delta",
            "chartis_shell",
            "audit_string", "audit_button_label", "audit_number_format",
            "compliance_check",
        }
        for mod_path, attr in KIT_PRIMITIVES:
            if attr not in CALLABLE:
                continue
            try:
                mod = importlib.import_module(mod_path)
            except ImportError:
                continue
            obj = getattr(mod, attr, None)
            if obj is not None and not callable(obj):
                non_callable.append(f"{mod_path}.{attr}: not callable")
        self.assertEqual(
            non_callable, [],
            f"Kit primitives expected to be callable are not:\n"
            + "\n".join(f"  {m}" for m in non_callable),
        )


if __name__ == "__main__":
    unittest.main()
