"""Sweep all README.md and docs/*.md files for broken relative markdown links.

Catches link rot when a file moves or a typo slips into a path.
External (http/https/mailto) links and pure #-anchor links are skipped.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path


_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "README.md").exists() and (parent / "docs").exists():
            return parent
    raise RuntimeError("could not locate repo root from tests/")


def _scan(p: Path) -> list[tuple[str, Path]]:
    """Return [(raw_link, resolved_path), ...] for every relative md link."""
    out: list[tuple[str, Path]] = []
    for m in _LINK_RE.finditer(p.read_text()):
        raw = m.group(1).strip()
        target = raw.split("#")[0].strip()
        if not target:
            continue
        if target.startswith(("http://", "https://", "mailto:", "tel:")):
            continue
        out.append((raw, (p.parent / target).resolve()))
    return out


class TestReadmeLinks(unittest.TestCase):
    """Every relative link in a README or doc must resolve to an existing path."""

    def test_package_surface_readmes_resolve(self) -> None:
        root = _repo_root()
        files = [
            root / "README.md",
            root / "docs" / "README.md",
            root / "rcm_mc" / "ml" / "README.md",
            root / "rcm_mc" / "data" / "README.md",
            root / "rcm_mc" / "ui" / "README.md",
        ]
        broken = []
        for f in files:
            if not f.exists():
                continue
            for raw, resolved in _scan(f):
                if not resolved.exists():
                    broken.append(f"{f.relative_to(root)} -> {raw}")
        self.assertEqual(broken, [], f"broken links: {broken}")

    def test_strategy_docs_resolve(self) -> None:
        root = _repo_root()
        docs_dir = root / "docs"
        if not docs_dir.exists():
            self.skipTest("docs/ not present")
        broken = []
        for f in sorted(docs_dir.glob("*.md")):
            for raw, resolved in _scan(f):
                if not resolved.exists():
                    broken.append(f"{f.name} -> {raw}")
        self.assertEqual(broken, [], f"broken links: {broken}")


if __name__ == "__main__":
    unittest.main()
