"""VDR ZIP package processing.

A deal team drops a ZIP exported from the data room. We extract the
supported files to a temp dir for the snapshot pipeline, with guards
against the usual archive hazards:

- path traversal (``../`` / absolute members) — rejected
- zip bombs — total uncompressed size + member count caps
- unsupported members — skipped, recorded

Snapshot-only: nothing here polls or fetches; it just unpacks a file
the user already uploaded.
"""
from __future__ import annotations

import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

_SUPPORTED = {".edi", ".txt", ".835", ".837", ".csv", ".tsv", ".xlsx", ".xlsm",
              ".parquet"}
_MAX_MEMBERS = 5_000
_MAX_TOTAL_UNCOMPRESSED = 1_024 * 1024 * 1024  # 1 GiB


@dataclass
class ZipExtractResult:
    extracted_files: List[Path] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def _is_safe_member(name: str) -> bool:
    if name.endswith("/"):
        return False  # directory entry
    p = Path(name)
    if p.is_absolute() or ".." in p.parts:
        return False
    return True


def extract_zip(zip_path: Path | str, dest_dir: Path | str) -> ZipExtractResult:
    """Extract supported files from ``zip_path`` into ``dest_dir`` (flat,
    name-collision-safe). Returns the extracted file paths + a record of
    what was skipped/flagged. Never raises on a bad member — records it.
    """
    res = ZipExtractResult()
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    try:
        zf = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile:
        res.warnings.append("not a valid ZIP archive")
        return res

    with zf:
        infos = zf.infolist()
        if len(infos) > _MAX_MEMBERS:
            res.warnings.append(
                f"archive has {len(infos)} members (cap {_MAX_MEMBERS}); "
                f"processing the first {_MAX_MEMBERS}")
            infos = infos[:_MAX_MEMBERS]
        total = 0
        used_names: set = set()
        for info in infos:
            name = info.filename
            if not _is_safe_member(name):
                res.skipped.append(f"{name} (unsafe path)")
                continue
            suffix = Path(name).suffix.lower()
            if suffix not in _SUPPORTED:
                res.skipped.append(f"{name} (unsupported type)")
                continue
            total += info.file_size
            if total > _MAX_TOTAL_UNCOMPRESSED:
                res.warnings.append("uncompressed size cap reached; stopping")
                break
            # Flatten + de-collide on basename.
            base = Path(name).name
            out_name = base
            n = 1
            while out_name in used_names:
                out_name = f"{Path(base).stem}_{n}{Path(base).suffix}"
                n += 1
            used_names.add(out_name)
            out_path = dest / out_name
            with zf.open(info) as src, open(out_path, "wb") as dst:
                dst.write(src.read())
            res.extracted_files.append(out_path)

    res.extracted_files.sort()
    if not res.extracted_files and not res.warnings:
        res.warnings.append("no supported files found in archive")
    return res
