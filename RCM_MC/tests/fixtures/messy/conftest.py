"""Marker file so pytest treats this dir as a package. Also re-exports
the generator registry so tests can regenerate fixtures on demand.
"""
from __future__ import annotations

from .generate_fixtures import FIXTURES, regenerate_all, regenerate_one

__all__ = ["FIXTURES", "regenerate_all", "regenerate_one"]
