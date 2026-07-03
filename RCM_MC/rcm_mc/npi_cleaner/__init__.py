"""NPI claims cleaner — the engine behind the ``/npi-cleaner`` page.

Public surface:
    engine.manager()          -> process-wide JobManager
    engine.clean_bytes(...)   -> synchronous clean of raw file bytes
    engine.classify_npi(...)  -> blank | malformed | checksum | valid
    engine.luhn_npi_valid(..) -> official NPI Luhn check

The uploaded ``NPI_Recovery_and_Cleaner_v48`` modules are vendored under
``vendor_v48/`` for provenance; see ``vendor_v48/README.md`` for why they are
reference-only (missing engine core + heavy deps).
"""
from . import engine

__all__ = ["engine"]
