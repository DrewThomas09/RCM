"""Developer + demo utilities. NOT shipped in the production CLI surface.

Modules here are tools for developers, demo prep, and ad-hoc debugging —
they should never be imported by production code paths. The package
exists so they can be invoked via `python -m rcm_mc.dev.<tool>` without
polluting `rcm-mc --help`.
"""
