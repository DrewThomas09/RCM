"""Huge claims files (up to ~10 GB) — streamed, chunked, merged.

The single-file pipeline parses the whole table into memory, which is fine
into the hundreds of megabytes and hopeless at 10 GB. Above
``STREAM_THRESHOLD_BYTES`` the cleaner switches to this module:

  1. the CSV is read from disk as complete records (quote-aware, so a
     newline inside a quoted cell never splits a row),
  2. records are grouped into ~``CHUNK_TARGET_BYTES`` chunks, and every
     chunk runs the EXACT same deterministic pipeline as a normal upload
     (``clean_bytes(..., _stream_chunk=True)``),
  3. chunk results merge the way zip-batch results already do — summed
     counters, one blended grade — and the cleaned rows append to ONE
     master output CSV as they are produced.

Memory stays bounded by the chunk size no matter how big the input is; a
10 GB file is simply many hours of chunks, which is the point — the job
runs in a background thread and the page polls progress.

Scope notes, deliberately explicit (all surfaced as warnings on the run):

  * Exact duplicates die across the WHOLE file: chunks share one bounded
    digest set (engine._STREAM_SEEN_CAP); saturation is warned, never
    silent.
  * The change-log FILE is complete at any scale: chunks write entries
    straight to the master CSV via a sink with file-global row indices;
    only the in-memory preview (engine._CHANGELOG_PREVIEW) is capped.
  * Online modes (NPPES verify, deep recovery) and the pandas suggestions
    companion are off, same as zip-batch mode: one upload must not fan out
    into N network sweeps or N DataFrame parses.
  * Report-only extras that need the whole table at once (payer variant
    clusters, charge outliers, claim rollup, data dictionary, xlsx
    workbook, population marts) are skipped. The quality grade is exact —
    all five score dimensions come from summed counters.

Only delimited text streams. An .xlsx / .zip / X12 file above the
threshold is rejected with instructions to export CSV — those formats
cannot be split without parsing the whole container.
"""
from __future__ import annotations

import csv
import os
import uuid
from pathlib import Path
from typing import BinaryIO, Dict, Iterator, List, Optional

from .engine import (
    CleanResult,
    ProgressCb,
    WORKDIR,
    _defang_cell,
    _out_name,
    clean_bytes,
)

# Files at or below this size go through the normal in-memory pipeline —
# identical behavior to a drag-and-drop upload, workbook and all. Above it,
# chunked streaming. Module-level so tests can force streaming on tiny files.
STREAM_THRESHOLD_BYTES = 96 * 1024 * 1024
# Target raw-bytes size of one cleaning chunk. Big enough that per-chunk
# fixed costs amortize; small enough that a chunk's parsed table + cleaned
# copy stay comfortably in memory.
CHUNK_TARGET_BYTES = 48 * 1024 * 1024
# Non-splittable formats (xlsx / zip / X12) keep the classic in-memory
# ceiling — matches the old NPI_UPLOAD_MAX_BYTES so nothing that worked
# before stops working.
_FORMAT_INMEM_MAX_BYTES = 200_000_000
# Caps come from the single-file pipeline so the merged result honours
# the same bounds the UI expects: the preview list is capped, the master
# change-log FILE is not (chunks write to it directly via the sink).
# Read as module attributes (engine._CHANGELOG_PREVIEW) at use sites so
# there is exactly one source of truth and tests can patch it.
from . import engine as _engine  # noqa: E402


def _iter_records(fh: BinaryIO) -> Iterator[bytes]:
    """Yield complete CSV records (physical lines joined while a quoted
    field is open). Quote-parity is the standard streaming heuristic: a
    record is complete only when it contains an even number of ``"``."""
    parts: List[bytes] = []
    quotes = 0
    for line in fh:
        parts.append(line)
        quotes += line.count(b'"')
        if quotes % 2 == 0:
            yield b"".join(parts)
            parts.clear()
            quotes = 0
    if parts:  # trailing record without a newline
        yield b"".join(parts)


def _warning_result(src_name: str, message: str,
                    progress: Optional[ProgressCb]) -> CleanResult:
    from .engine import _write_output
    res = CleanResult(delimiter="stream", headers=[])
    res.warnings.append(message)
    res.out_name = _out_name(src_name)
    _write_output(res, [], [])
    if progress:
        progress("Done", 1.0)
    return res


def clean_path(
    path: str,
    src_name: str,
    *,
    drop_duplicates: bool = True,
    enrich: bool = False,
    deep: bool = False,
    deid: bool = False,
    profile: Optional[Dict[str, object]] = None,
    overrides: Optional[Dict[str, str]] = None,
    progress: Optional[ProgressCb] = None,
) -> CleanResult:
    """Clean a claims file already on disk. Small files delegate to the
    normal in-memory pipeline; big delimited files stream in chunks."""
    size = os.path.getsize(path)

    def _in_memory() -> CleanResult:
        data = Path(path).read_bytes()
        return clean_bytes(data, src_name, drop_duplicates=drop_duplicates,
                           enrich=enrich, deep=deep, deid=deid,
                           profile=profile, overrides=overrides,
                           progress=progress)

    if size <= STREAM_THRESHOLD_BYTES:
        return _in_memory()

    # Above the streaming threshold, only delimited text can be split into
    # chunks. Container formats (xlsx/zip — both start with the PK zip
    # magic) and X12 interchanges still clean in memory up to the classic
    # ceiling; past that, streaming can't help and the honest answer is
    # instructions, not an OOM.
    with open(path, "rb") as fh:
        head = fh.read(4096)
    non_splittable = head[:2] == b"PK"
    if not non_splittable:
        try:
            from . import x12 as _x12
            non_splittable = _x12.looks_like_x12(head)
        except Exception:  # noqa: BLE001 — probe failure → treat as CSV
            non_splittable = False
    if non_splittable:
        if size <= _FORMAT_INMEM_MAX_BYTES:
            return _in_memory()
        return _warning_result(
            src_name,
            f"This file is {size / 1e9:.1f} GB in a format that can't be "
            "split (Excel workbook, zip archive, or X12 EDI). Streamed "
            "cleaning needs delimited text — export as CSV and re-upload, "
            "or split the file and upload the pieces.", progress)

    # UTF-16/32 (Excel "Unicode Text" exports): the byte-level record
    # iterator splits on \n BYTES and is blind to wide encodings, so a big
    # wide file is transcoded to a temp UTF-8 copy first (bounded memory,
    # incremental decoder) and streamed from there. Small-enough ones just
    # take the in-memory path, which decodes properly already.
    wide = _engine._wide_probe(head)
    if wide is not None:
        if size <= _FORMAT_INMEM_MAX_BYTES:
            return _in_memory()
        enc, bom_len, label = wide
        tmp = WORKDIR / f"transcode_{uuid.uuid4().hex}.csv"
        try:
            import codecs
            dec = codecs.getincrementaldecoder(enc)(errors="replace")
            with open(path, "rb") as src, \
                    open(tmp, "w", encoding="utf-8", newline="") as dst:
                src.seek(bom_len)
                while True:
                    blk = src.read(1 << 20)
                    if not blk:
                        dst.write(dec.decode(b"", True))
                        break
                    dst.write(dec.decode(blk))
            res = _clean_csv_stream(
                str(tmp), src_name, os.path.getsize(tmp),
                drop_duplicates=drop_duplicates, deid=deid,
                profile=profile, overrides=overrides, progress=progress)
            res.warnings.insert(0, (
                f"File was {label}-encoded — transcoded to UTF-8 before "
                "streaming. Prefer CSV UTF-8 exports."))
            return res
        finally:
            try:
                Path(tmp).unlink(missing_ok=True)
            except OSError:
                pass

    return _clean_csv_stream(
        path, src_name, size, drop_duplicates=drop_duplicates, deid=deid,
        profile=profile, overrides=overrides, progress=progress)


def _clean_csv_stream(
    path: str,
    src_name: str,
    size: int,
    *,
    drop_duplicates: bool,
    deid: bool,
    profile: Optional[Dict[str, object]],
    overrides: Optional[Dict[str, str]],
    progress: Optional[ProgressCb],
) -> CleanResult:
    def cb(msg: str, frac: float) -> None:
        if progress:
            progress(msg, frac)

    res = CleanResult(delimiter=",", headers=[])
    token = uuid.uuid4().hex
    res.out_name = _out_name(src_name)
    out_path = WORKDIR / f"{token}_{res.out_name}"
    stem = (res.out_name[:-len("_cleaned.csv")]
            if res.out_name.endswith("_cleaned.csv")
            else res.out_name.rsplit(".", 1)[0]) or "claims"
    res.changelog_name = f"{stem}_changelog.csv"
    log_path = WORKDIR / f"{token}_{res.changelog_name}"

    # Per-column fill counters across all chunks (column → filled cells);
    # recomputed into res.column_fill at the end over total rows in.
    fill_counts: Dict[str, int] = {}
    # Merged-panel accumulators. Per-chunk results carry each panel's top
    # entries; summing those across ~48 MB chunks is honest granularity —
    # far better than the panels silently rendering empty on streamed runs.
    pq_acc: Dict[str, Dict[str, object]] = {}     # payer-quality split
    den_counts: Dict[str, int] = {}               # denial code → count
    den_meta: Dict[str, Dict[str, object]] = {}   # code → playbook fields
    den_col: Optional[str] = None
    den_distinct = 0
    spec_acc: Dict[str, Dict[str, object]] = {}   # taxonomy code → {n,name}
    n_log_rows = 0
    rows_in_offset = 0    # changelog rows are 1-based INPUT indices
    rows_out_offset = 0   # worklist rows are 1-based OUTPUT indices
    wrote_header = False
    chunk_i = 0

    cb("Reading file (streaming mode)", 0.01)
    with open(path, "rb") as fh, \
            open(out_path, "w", newline="", encoding="utf-8") as out_fh, \
            open(log_path, "w", newline="", encoding="utf-8") as log_fh:
        out_writer = csv.writer(out_fh)
        log_writer = csv.writer(log_fh)
        log_writer.writerow(["row", "column", "before", "after", "rule"])

        records = _iter_records(fh)
        header = next(records, None)
        if header is None or not header.strip():
            res.warnings.append(
                "File appears to be empty — no header row found.")
            header = None
        bytes_done = len(header) if header else 0
        # One digest set shared by every chunk → duplicates die across
        # chunk boundaries too. Growth is capped inside the engine
        # (_STREAM_SEEN_CAP); saturation is surfaced as a warning below.
        stream_seen: set = set()
        # Same idea for the case/whitespace-folded near-duplicate signal:
        # a shared digest set means a "SMITH" row in chunk 1 still pairs
        # with its "Smith" twin in chunk 9.
        stream_fold_seen: set = set()
        # Master-changelog sink health: once a write fails, the sink goes
        # quiet and the run finishes with changelog_truncated instead of
        # dying mid-flight.
        sink_state = {"failed": False}

        while header is not None:
            chunk: List[bytes] = []
            chunk_bytes = 0
            for rec in records:
                chunk.append(rec)
                chunk_bytes += len(rec)
                if chunk_bytes >= CHUNK_TARGET_BYTES:
                    break
            if not chunk:
                break
            chunk_i += 1
            bytes_done += chunk_bytes
            pct = min(99.0, 100.0 * bytes_done / max(size, 1))
            cb(f"Cleaning chunk {chunk_i} — {pct:.0f}% of file",
               min(0.95, bytes_done / max(size, 1) * 0.95))

            # Chunks write change-log entries straight to the master file
            # (with the input-row offset applied) — the audit CSV stays
            # complete no matter how many cells a 10M-row run changes,
            # and no chunk ever holds more than the preview in memory.
            # The sink MUST NOT raise: a disk error on the audit log
            # would otherwise abort an hours-long cleaning run — the
            # right outcome is a truncated-log flag, not a dead job.
            _off = rows_in_offset
            _sunk = [0]

            def _sink(entry, _off=_off, _sunk=_sunk):
                if sink_state["failed"]:
                    return
                try:
                    ri0, col0, before0, after0, rule0 = entry
                    log_writer.writerow(
                        [ri0 + _off, _defang_cell(col0),
                         _defang_cell(before0), _defang_cell(after0),
                         rule0])
                    _sunk[0] += 1
                except OSError:
                    sink_state["failed"] = True

            sub = clean_bytes(
                header + b"".join(chunk), src_name,
                drop_duplicates=drop_duplicates, deid=deid,
                profile=profile, overrides=overrides, _stream_chunk=True,
                _stream_seen=(stream_seen if drop_duplicates else None),
                _stream_fold_seen=stream_fold_seen,
                _changelog_sink=_sink)
            payload = sub.chunk_payload
            if payload is None:
                # The chunk took an error path inside clean_bytes (garbage
                # bytes, undecodable). Surface it and stop — silently
                # skipping rows would make the output lie about coverage.
                res.warnings.append(
                    f"Streaming stopped at chunk {chunk_i}: "
                    + ("; ".join(sub.warnings) or "unreadable data")
                    + f" — output contains the first {rows_out_offset:,} "
                    "cleaned rows only.")
                break

            headers, cleaned = payload
            if not wrote_header:
                wrote_header = True
                out_writer.writerow([_defang_cell(h) for h in headers])
                res.headers = list(headers)
                res.delimiter = sub.delimiter
                res.npi_columns = sub.npi_columns
                res.billing_column = sub.billing_column
                res.accepted_rules = sub.accepted_rules
                res.profile_name = sub.profile_name
            for row in cleaned:
                out_writer.writerow([_defang_cell(c) for c in row])

            # ---- merge: the zip-batch counter pattern -------------------
            res.n_rows_out += sub.n_rows_out
            res.n_rows_in += sub.n_rows_in
            res.n_dupes_removed += sub.n_dupes_removed
            res.n_cells_trimmed += sub.n_cells_trimmed
            res.n_changes += sub.n_changes
            res.n_cells_total += sub.n_cells_total
            res.n_cells_filled += sub.n_cells_filled
            for k, v in sub.repairs.items():
                res.repairs[k] = res.repairs.get(k, 0) + v
            for k, v in sub.sanity.items():
                res.sanity[k] = res.sanity.get(k, 0) + v
            for k, v in sub.credentials.items():
                res.credentials[k] = res.credentials.get(k, 0) + v
            for col, st in sub.column_stats.items():
                agg = res.column_stats.setdefault(
                    col, {"valid": 0, "blank": 0, "malformed": 0,
                          "checksum": 0, "cells": 0})
                for k, v in st.items():
                    agg[k] = agg.get(k, 0) + v
            for cf in sub.column_fill:
                col = str(cf.get("column") or "")
                fill_counts[col] = (fill_counts.get(col, 0)
                                    + int(cf.get("filled") or 0))
            # Structural findings: duplicate headers / sniffed NPI columns
            # are identical in every chunk (same header line) — first chunk
            # wins; ragged-row counts sum. empty_columns is recomputed from
            # the merged fill counts at the end.
            for sk, sv in (sub.structure or {}).items():
                if sk == "ragged_rows" and isinstance(sv, dict):
                    agg_rr = res.structure.setdefault(
                        "ragged_rows", {"padded": 0, "truncated": 0})
                    agg_rr["padded"] += int(sv.get("padded") or 0)
                    agg_rr["truncated"] += int(sv.get("truncated") or 0)
                elif sk != "empty_columns" and sk not in res.structure:
                    res.structure[sk] = sv
            # Merged panels: payer quality, denials, specialty mix — summed
            # from each chunk's top entries (per-chunk truncation makes the
            # tail approximate; the heads, which the UI shows, are exact).
            for pe in sub.payer_quality:
                acc = pq_acc.setdefault(str(pe.get("payer")), {
                    "rows": 0, "flagged": 0, "rules": {}})
                acc["rows"] += int(pe.get("rows") or 0)
                acc["flagged"] += int(pe.get("flagged") or 0)
                for tr in (pe.get("top_rules") or []):
                    r_id = str(tr.get("rule"))
                    acc["rules"][r_id] = (acc["rules"].get(r_id, 0)
                                          + int(tr.get("n") or 0))
            if sub.denials:
                den_col = den_col or str(sub.denials.get("column") or "")
                den_distinct = max(den_distinct,
                                   int(sub.denials.get("distinct") or 0))
                for de in (sub.denials.get("top") or []):
                    code = str(de.get("code"))
                    den_counts[code] = (den_counts.get(code, 0)
                                        + int(de.get("count") or 0))
                    if code not in den_meta:
                        den_meta[code] = {k: de[k] for k in
                                          ("category", "linked_rule",
                                           "action") if k in de}
            for se in sub.specialties:
                code = str(se.get("code"))
                sa = spec_acc.setdefault(code, {"n": 0,
                                                "name": se.get("name")})
                sa["n"] += int(se.get("n") or 0)
            if sub.deid_applied:
                res.deid_applied = True
                res.deid_cells += sub.deid_cells
                for _dc in sub.deid_columns:
                    if _dc not in res.deid_columns:
                        res.deid_columns.append(_dc)

            # The sink already streamed every entry to the master CSV;
            # here we only top up the in-memory preview for the UI.
            n_log_rows += _sunk[0]
            for ri, col, before, after, rule in sub.changelog:
                if len(res.changelog) >= _engine._CHANGELOG_PREVIEW:
                    break
                res.changelog.append((ri + rows_in_offset, col,
                                      before, after, rule))
            if sub.changelog_truncated or sink_state["failed"]:
                res.changelog_truncated = True

            # Worklists: chunk indices are 1-based OUTPUT rows — offset by
            # the rows already written so the download slices the master
            # output correctly.
            for rule, idxs in sub.flag_rows.items():
                lst = res.flag_rows.setdefault(rule, [])
                for i in idxs:
                    if len(lst) >= _engine._WORKLIST_CAP:
                        break
                    lst.append(i + rows_out_offset)
            for fam, idxs in sub.payer_flag_rows.items():
                lst = res.payer_flag_rows.setdefault(fam, [])
                for i in idxs:
                    if len(lst) >= _engine._WORKLIST_CAP:
                        break
                    lst.append(i + rows_out_offset)

            rows_in_offset += sub.n_rows_in
            rows_out_offset += sub.n_rows_out

    res.out_path = str(out_path)
    if n_log_rows:
        res.changelog_path = str(log_path)
    else:
        Path(log_path).unlink(missing_ok=True)
    if fill_counts and res.n_rows_in:
        res.column_fill = [
            {"column": col, "filled": n,
             "pct": round(100.0 * n / max(res.n_rows_in, 1), 1)}
            for col, n in fill_counts.items()]
        # Headered-but-empty columns, from the merged fill counts — exact
        # across the whole file, unlike the per-chunk panels.
        _empty = [col for col, n in fill_counts.items() if n == 0]
        if _empty and res.n_rows_out:
            res.structure["empty_columns"] = _empty
    # Merged panels (summed per-chunk tops — heads exact, tails approx).
    if pq_acc:
        for fam, acc in sorted(pq_acc.items(),
                               key=lambda kv: -int(kv[1]["rows"]))[:10]:
            rows_n = max(int(acc["rows"]), 1)
            top_r = sorted(acc["rules"].items(),
                           key=lambda kv: -kv[1])[:3]
            res.payer_quality.append({
                "payer": fam,
                "rows": int(acc["rows"]),
                "flagged": int(acc["flagged"]),
                "clean_pct": round(
                    100 * (1 - int(acc["flagged"]) / rows_n), 1),
                "top_rules": [{"rule": r, "n": n} for r, n in top_r],
            })
    if den_counts and den_col:
        _top = sorted(den_counts.items(), key=lambda kv: -kv[1])[:10]
        _entries = []
        for code, n in _top:
            e: Dict[str, object] = {"code": code, "count": n}
            e.update(den_meta.get(code) or {})
            _entries.append(e)
        res.denials = {"column": den_col,
                       "distinct": max(den_distinct, len(den_counts)),
                       "top": _entries,
                       "note": "streamed: merged from per-chunk top codes"}
        try:
            from . import refdata as _rd
            _known = _prev = 0
            for code, n in den_counts.items():
                pb = _rd.carc_playbook(code)
                if pb:
                    _known += n
                    if pb["category"] == "preventable":
                        _prev += n
            if _known:
                res.denials["preventable_pct"] = round(
                    100 * _prev / _known, 1)
        except Exception:  # noqa: BLE001 — playbook never blocks merging
            pass
    if spec_acc:
        res.specialties = [
            {"code": c, "n": int(sa["n"]), "name": sa.get("name")}
            for c, sa in sorted(spec_acc.items(),
                                key=lambda kv: (-int(kv[1]["n"]),
                                                kv[0]))[:15]]
    if chunk_i:
        from .engine import _STREAM_SEEN_CAP
        if len(stream_seen) >= _STREAM_SEEN_CAP:
            res.warnings.append(
                f"Duplicate tracking capped at {_STREAM_SEEN_CAP:,} "
                "distinct rows — rows first seen after the cap aren't "
                "tracked, so their later duplicates may remain.")
        _rr = res.structure.get("ragged_rows") or {}
        if int(_rr.get("truncated") or 0):
            res.warnings.append(
                f"{int(_rr['truncated']):,} row(s) carried MORE cells "
                "than the header — the overflow cells were dropped (see "
                "the ragged-row worklist). Unquoted delimiters inside a "
                "text field are the usual cause.")
        res.warnings.insert(0, (
            f"Streaming mode: {size / 1e9:.1f} GB file cleaned in "
            f"{chunk_i} chunk(s) with bounded memory. Exact duplicates "
            "AND near-duplicates are tracked across the whole file "
            "(bounded digest sets); the suspected-duplicate-claim, "
            "conflicting-amount, possible-duplicate-service, "
            "charge-outlier and NPI-name-conflict scans reset at each "
            "chunk boundary, so cross-chunk repeats of THOSE may be "
            "missed. Payer quality, "
            "denial reasons and the specialty mix are merged from "
            "per-chunk tallies. NPPES verification, deep recovery, the "
            "suggestions companion, the xlsx workbook and the remaining "
            "whole-file analytics (payer variant clusters, claim rollup, "
            "dictionary, population marts) are skipped in this mode. The "
            "grade, repairs, row-level findings, change log and "
            "worklists cover every row."))
        # One history record for the whole run — the chunks recorded
        # nothing.
        try:
            from . import history as _history
            res.trend_alerts = _history.trend_alerts(res.as_scorecard(),
                                                     src_name)
            _history.record_run(res.as_scorecard(), src_name)
        except Exception:  # noqa: BLE001 — observability never blocks
            pass
        try:
            _engine._autofile_gaps(res)
        except Exception:  # noqa: BLE001
            pass
    cb("Done", 1.0)
    return res
