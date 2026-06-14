"""PEDesk connectors namespace.

Each subpackage is one source vertical (NPPES, CMS/DKAN, openFDA, RxNorm,
...). A connector lands raw source data, normalizes it to the canonical
crosswalk dimensions, and registers its datasets in a declarative registry
so the ``/v1/query/{dataset}`` surface can expose them without bespoke
routing code.

This namespace package is intentionally dependency-light so a single source
slice can be built, tested, and shipped on its own.
"""
