"""Vendored NPI_Recovery_and_Cleaner v49 (complete package).

The original package ``__init__`` (kept as ``__init__.py.full``) eagerly imports
``.pipeline`` → ``.clients`` → ``requests``. ``requests`` is not a base RCM
dependency, so this lazy marker replaces it: the offline deterministic engine
(``schema`` + ``clean_orchestrator``, which the /npi-cleaner page uses) imports
with zero third-party deps beyond pandas/numpy.

To run the full networked recovery pipeline, ``pip install requests`` and import
explicitly::

    from rcm_mc.npi_cleaner.vendor_v49.npi_recovery.pipeline import run_pipeline
    from rcm_mc.npi_cleaner.vendor_v49.npi_recovery import report as _rpt

(That path is a batch/CLI job — it constructs live CMS + NPPES clients and can
run for minutes; it is intentionally NOT invoked from the web request.)
"""
__version__ = "49.0.0"
