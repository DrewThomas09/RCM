"""Vendored NPI_Recovery_and_Cleaner v48 modules (reference/runtime-subset).

The original __init__ (kept as __init__.py.orig) eagerly imported .pipeline /
.entity / .report — modules absent from the delivered zip — so it is replaced
with this lazy package marker. Import individual runnable modules directly.
"""
