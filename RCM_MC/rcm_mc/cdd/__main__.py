"""Module entrypoint: ``python -m rcm_mc.cdd``."""
from __future__ import annotations

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
