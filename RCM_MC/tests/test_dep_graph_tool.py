"""Unit tests for RCM_MC/tools/build_dep_graph.py.

Exercises the pure-function parsing layer against synthetic inputs.
Doesn't actually run the tool on the live repo — that would be a
smoke test, not a unit test.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

# Load the tool as a module since it's a script, not a package member
_TOOL_PATH = pathlib.Path(__file__).resolve().parent.parent / "tools" / "build_dep_graph.py"
_spec = importlib.util.spec_from_file_location("build_dep_graph", _TOOL_PATH)
assert _spec is not None and _spec.loader is not None
build_dep_graph = importlib.util.module_from_spec(_spec)
sys.modules["build_dep_graph"] = build_dep_graph
_spec.loader.exec_module(build_dep_graph)


class TestFileToModule(unittest.TestCase):
    def test_nested_file(self):
        p = pathlib.Path("x/RCM_MC/rcm_mc/ui/chartis/home_page.py")
        self.assertEqual(build_dep_graph._file_to_module(p),
                         "rcm_mc.ui.chartis.home_page")

    def test_top_level_file(self):
        p = pathlib.Path("x/RCM_MC/rcm_mc/cli.py")
        self.assertEqual(build_dep_graph._file_to_module(p), "rcm_mc.cli")

    def test_not_in_rcm_mc(self):
        p = pathlib.Path("x/some/other/path/foo.py")
        self.assertEqual(build_dep_graph._file_to_module(p), "")


class TestResolveRelative(unittest.TestCase):
    def test_level_one_sibling_module(self):
        # inside rcm_mc/ui/foo.py: `from .bar import X` -> rcm_mc.ui.bar
        out = build_dep_graph._resolve_relative("rcm_mc.ui.foo", 1, "bar")
        self.assertEqual(out, "rcm_mc.ui.bar")

    def test_level_two_nested(self):
        # inside rcm_mc/ui/chartis/X.py: `from .._chartis_kit` -> rcm_mc.ui._chartis_kit
        out = build_dep_graph._resolve_relative(
            "rcm_mc.ui.chartis.home_page", 2, "_chartis_kit"
        )
        self.assertEqual(out, "rcm_mc.ui._chartis_kit")

    def test_level_one_no_module(self):
        # `from . import X` inside rcm_mc/ui/foo.py -> rcm_mc.ui
        out = build_dep_graph._resolve_relative("rcm_mc.ui.foo", 1, None)
        self.assertEqual(out, "rcm_mc.ui")

    def test_level_too_deep(self):
        # Asking for level deeper than file path -> None
        out = build_dep_graph._resolve_relative("rcm_mc.cli", 5, "X")
        self.assertIsNone(out)

    def test_empty_file_mod(self):
        self.assertIsNone(build_dep_graph._resolve_relative("", 1, "X"))


class TestSubpkgOfModule(unittest.TestCase):
    def test_subpackage_member(self):
        self.assertEqual(build_dep_graph._subpkg_of_module("rcm_mc.ui._chartis_kit"), "ui")

    def test_deeply_nested(self):
        self.assertEqual(
            build_dep_graph._subpkg_of_module("rcm_mc.diligence.hcris_xray.metrics"),
            "diligence",
        )

    def test_top_level_file(self):
        # rcm_mc.cli is a top-level file, not a sub-package
        self.assertEqual(build_dep_graph._subpkg_of_module("rcm_mc.cli"), "cli")
        # (cli gets tagged as "cli" — the tool treats it as a pseudo-subpkg;
        # in practice it's filtered by _subpkg_of(path) returning None for
        # top-level files, so cli edges don't appear in the graph.)

    def test_not_rcm_mc(self):
        self.assertIsNone(build_dep_graph._subpkg_of_module("numpy"))
        self.assertIsNone(build_dep_graph._subpkg_of_module("some.other.pkg"))


class TestSubpkgOfPath(unittest.TestCase):
    def test_nested_in_subpackage(self):
        p = pathlib.Path("RCM_MC/rcm_mc/diligence/hcris_xray/metrics.py")
        self.assertEqual(build_dep_graph._subpkg_of(p), "diligence")

    def test_top_level_file(self):
        p = pathlib.Path("RCM_MC/rcm_mc/cli.py")
        self.assertIsNone(build_dep_graph._subpkg_of(p))

    def test_not_in_rcm_mc(self):
        p = pathlib.Path("some/other/path/foo.py")
        self.assertIsNone(build_dep_graph._subpkg_of(p))


class TestCollectImportsFromSource(unittest.TestCase):
    """Exercise collect_imports_from_file by writing a tiny fixture file."""

    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name) / "RCM_MC" / "rcm_mc" / "ui"
        self.root.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_absolute_import(self):
        f = self.root / "test_page.py"
        f.write_text(
            "from rcm_mc.core import simulator\n"
            "from rcm_mc.pe.pe_math import bridge\n"
        )
        out = build_dep_graph.collect_imports_from_file(f)
        self.assertEqual(sorted(out), ["core", "pe"])

    def test_relative_import_within_package(self):
        f = self.root / "test_page.py"
        f.write_text(
            "from ._chartis_kit import shell\n"
            "from ..core import simulator\n"
        )
        out = build_dep_graph.collect_imports_from_file(f)
        # from . -> rcm_mc.ui (-> ui); from ..core -> rcm_mc.core (-> core)
        self.assertIn("ui", out)
        self.assertIn("core", out)

    def test_syntax_error_returns_empty(self):
        f = self.root / "broken.py"
        f.write_text("this is not valid python :::: ")
        out = build_dep_graph.collect_imports_from_file(f)
        self.assertEqual(out, [])

    def test_external_imports_skipped(self):
        f = self.root / "test_page.py"
        f.write_text(
            "import numpy\n"
            "from pandas import DataFrame\n"
            "from rcm_mc.data import hcris\n"
        )
        out = build_dep_graph.collect_imports_from_file(f)
        self.assertEqual(out, ["data"])


if __name__ == "__main__":
    unittest.main()
