"""Per-subsector market-report modules.

Each module in this package authors exactly one :class:`~rcm_mc.market_reports.MarketReport`
and ends with ``register(REPORT)`` so it self-registers on import. The parent
package's ``all_reports()`` autoloads every module here via
``pkgutil.iter_modules`` — you never wire a module into a manifest; dropping the
file in this directory is the whole registration step.

To add one: copy ``hospice.py`` (deals-only pattern) or ``dialysis.py`` (rich
vendored-facility pattern), rename to ``<slug>.py``, and follow the recipe in
``rcm_mc/market_reports/__init__.py``.
"""
from __future__ import annotations


def load_all() -> None:
    """Force-import every report module (thin re-export of the parent
    autoloader, handy for scripts/tests that want the side effect explicitly)."""
    from .. import _autoload
    _autoload()
