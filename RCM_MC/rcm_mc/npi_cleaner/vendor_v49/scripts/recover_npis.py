#!/usr/bin/env python3
"""Thin launcher. Run:  python recover_npis.py <claims file> [options]"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from npi_recovery.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
