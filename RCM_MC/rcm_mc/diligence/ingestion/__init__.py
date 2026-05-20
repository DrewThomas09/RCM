"""VDR upload ingestion helpers for the healthcare snapshot module."""
from __future__ import annotations

from .zip_processor import ZipExtractResult, extract_zip

__all__ = ["ZipExtractResult", "extract_zip"]
