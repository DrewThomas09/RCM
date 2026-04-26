"""Back-compat shim for `rcm-intake` / `python -m rcm_mc.intake`.

The real module now lives at ``rcm_mc.data.intake``. This file
re-exports its public symbols so ``pyproject.toml``'s
``rcm-intake = "rcm_mc.intake:main"`` console-script entry-point keeps
working after the data/ refactor moved the implementation.
"""
from .data.intake import *  # noqa: F401, F403
from .data import intake as _impl


def main() -> int:
    return _impl.main()


if __name__ == "__main__":
    import sys
    sys.exit(main())
