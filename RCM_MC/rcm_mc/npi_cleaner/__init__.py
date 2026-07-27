"""NPI claims cleaner — the engine behind the ``/npi-cleaner`` page.

Public surface:
    engine.manager()          -> process-wide JobManager
    engine.clean_bytes(...)   -> synchronous clean of raw file bytes
    engine.classify_npi(...)  -> blank | malformed | checksum | valid
    engine.luhn_npi_valid(..) -> official NPI Luhn check

The ``NPI_Recovery_and_Cleaner v49`` deterministic engine is vendored under
``vendor_v49/`` and is live — ``vendor_adapter`` drives it
(``schema.standardize_any`` -> ``clean_orchestrator.clean_all``) and
``deep_pipeline`` runs its full networked recovery pipeline. See
``vendor_v49/README.md`` for the module map and reference CSVs.
"""
from . import engine

__all__ = ["engine"]
