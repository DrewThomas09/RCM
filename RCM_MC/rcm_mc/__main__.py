"""Allow ``python -m rcm_mc`` to invoke the top-level CLI dispatcher.

Mirrors ``rcm-mc`` (the console-script entry point). Useful when the venv
isn't on PATH, or when scripting from inside the package.
"""
from __future__ import annotations

import sys

from .cli import main


if __name__ == "__main__":
    sys.exit(main() or 0)
