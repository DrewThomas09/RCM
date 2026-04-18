"""Canonical loader for the deals corpus with provenance filtering.

Call ``load_corpus_deals(mode=...)`` to get a list of deal dicts,
each enriched with an injected ``provenance`` field. The loader
enumerates every seed group registered in
``rcm_mc.data_public.corpus_provenance.PROVENANCE_REGISTRY``, imports
the corresponding module, and tags each row with the registry's tag.

Why a new loader when ``ui/chartis/_helpers.py::load_corpus_deals``
already exists?
    The legacy loader (and the dozen ad-hoc copies sprinkled across
    ``ui/data_public/``) iterates ``range(2, 32)`` / ``range(2, 40)``
    / ``range(2, 104)`` with no provenance awareness. They remain in
    place for backwards compatibility with existing page renders,
    but new callers (``/demo-real`` mode in Phase D, provenance-aware
    analytics in Phase E) must use this module.

Modes:
    "all"       — everything in the registry. Same cardinality as the
                  current corpus (~1,815 deals).
    "real"      — only groups tagged "real" in the registry
                  (~55 deals).
    "synthetic" — only groups tagged "synthetic" in the registry
                  (~1,760 deals).
"""
from __future__ import annotations

import importlib
from typing import Any, Dict, List

from .corpus_provenance import PROVENANCE_REGISTRY, tag_for_group


_VALID_MODES = ("all", "real", "synthetic")


def _import_group(group: str) -> List[Dict[str, Any]]:
    """Return the raw deal list for a named group.

    Group name maps to module + list-variable as follows:
      "_SEED_DEALS"           → deals_corpus._SEED_DEALS
      "extended_seed"         → extended_seed.EXTENDED_SEED_DEALS
      "extended_seed_{N}"     → extended_seed_{N}.EXTENDED_SEED_DEALS_{N}

    Missing module or missing variable → empty list. Seed files
    occasionally get deleted or renamed; we don't want the whole
    corpus to fail loading because one file is absent.
    """
    try:
        if group == "_SEED_DEALS":
            mod = importlib.import_module("rcm_mc.data_public.deals_corpus")
            return list(getattr(mod, "_SEED_DEALS", []))
        if group == "extended_seed":
            mod = importlib.import_module("rcm_mc.data_public.extended_seed")
            return list(getattr(mod, "EXTENDED_SEED_DEALS", []))
        if group.startswith("extended_seed_"):
            n = group[len("extended_seed_"):]
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{n}")
            return list(getattr(mod, f"EXTENDED_SEED_DEALS_{n}", []))
    except ImportError:
        return []
    return []


def load_corpus_deals(mode: str = "all") -> List[Dict[str, Any]]:
    """Load the corpus with ``provenance`` injected on every row.

    Args:
        mode: "all" (default), "real", or "synthetic".

    Returns:
        List of deal dicts, each guaranteed to have a
        ``provenance`` key equal to "real" or "synthetic".

    Raises:
        ValueError: on an unknown mode.
    """
    if mode not in _VALID_MODES:
        raise ValueError(
            f"mode must be one of {_VALID_MODES!r}, got {mode!r}"
        )

    out: List[Dict[str, Any]] = []
    for group, tag in PROVENANCE_REGISTRY.items():
        if mode != "all" and tag != mode:
            continue
        rows = _import_group(group)
        for row in rows:
            # Shallow copy so we don't mutate the module-level lists.
            # Injecting into the shared list would cross-contaminate
            # callers that still use the legacy loaders.
            enriched = dict(row)
            enriched["provenance"] = tag
            enriched.setdefault("source_group", group)
            out.append(enriched)
    return out


def corpus_counts() -> Dict[str, int]:
    """Return {mode: count} summary for reporting/debug. O(corpus)."""
    return {
        "all": len(load_corpus_deals("all")),
        "real": len(load_corpus_deals("real")),
        "synthetic": len(load_corpus_deals("synthetic")),
    }
