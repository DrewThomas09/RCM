"""Back-compat shim for `python -m rcm_mc.lookup`.

The real module now lives at ``rcm_mc.data.lookup``. This file
re-exports its public symbols so existing scripts and cron jobs
invoking the old path keep working.
"""
from .data.lookup import *  # noqa: F401, F403
from .data import lookup as _impl


def main() -> int:
    return _impl.main()


if __name__ == "__main__":
    import sys
    sys.exit(main())
