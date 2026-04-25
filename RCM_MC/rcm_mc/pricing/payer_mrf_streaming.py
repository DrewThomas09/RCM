"""Streaming parser for Transparency in Coverage payer MRFs.

The original ``parse_payer_tic_mrf`` uses ``json.load(fh)`` which
materialises the entire document. Real production MRFs from
UHC / Cigna / Aetna routinely exceed 10GB unzipped — that
breaks json.load.

This module implements a streaming alternative:

  1. Opens the file as a text stream (transparently handles
     ``.json`` and ``.json.gz``).
  2. Reads the top-level header bytes (reporting_entity_name,
     plan_name, etc.) up to the start of ``"in_network": [``.
  3. From that point, reads one in_network entry at a time by
     tracking JSON brace + bracket depth. Each entry is the
     ONLY thing materialised in memory.
  4. Parses the entry with ``json.loads`` and yields the same
     ``PayerRateRecord`` shape the existing loader produces.

Pure stdlib — no ijson, no scipy. Handles arbitrarily large
files in bounded memory (~ size-of-largest-in_network-entry).

Public API::

    from rcm_mc.pricing.payer_mrf_streaming import (
        streaming_parse_payer_tic_mrf,
        load_payer_tic_mrf_streaming,
    )

The output records and the persistence call are bit-compatible
with the existing payer_mrf module — partners can swap the
parser without changing downstream consumers.
"""
from __future__ import annotations

import gzip
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

from .normalize import (
    classify_service_line,
    normalize_code,
    normalize_payer_name,
)
from .payer_mrf import PayerRateRecord, _safe_float

logger = logging.getLogger(__name__)


def _open_text(path: Path):
    """Open .json or .json.gz transparently as text."""
    if str(path).endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8",
                         errors="replace")
    return path.open("r", encoding="utf-8", errors="replace")


def _read_header_until_in_network(stream) -> str:
    """Read text until we've consumed the ``"in_network": [``
    opener. Return the header bytes (without the trailing
    in_network array contents).

    We slurp the header into a string so we can json.loads it
    for top-level metadata extraction (payer name, plan name)
    via a closing-brace synthesis trick.
    """
    buf = []
    needle = '"in_network"'
    while True:
        chunk = stream.read(8192)
        if not chunk:
            break
        buf.append(chunk)
        joined = "".join(buf)
        idx = joined.find(needle)
        if idx >= 0:
            # Found — now advance past the colon and opening [
            after = joined[idx + len(needle):]
            colon_idx = after.find("[")
            if colon_idx < 0:
                # Need more data
                continue
            # Trim everything from the chunk past the [
            before_array = joined[:idx + len(needle)
                                  + colon_idx + 1]
            remainder = after[colon_idx + 1:]
            # Push the remainder back via buffered read by
            # returning it through a synthetic field on the
            # stream — caller iterates by re-feeding it. We
            # pass remainder back via a tuple.
            return before_array, remainder
    return "".join(buf), ""


def _extract_top_level_metadata(header: str) -> dict:
    """Synthesise a closing brace + array bracket so we can
    json.loads() the header to grab reporting_entity_name +
    plan_name without writing a custom parser."""
    fragment = header.rstrip()
    # The header ends with `"in_network": [`. Replace the
    # opening `[` with `[]}` so the JSON is balanced.
    if fragment.endswith("["):
        fragment = fragment[:-1] + "[]}"
    else:
        fragment += "[]}"
    try:
        return json.loads(fragment)
    except json.JSONDecodeError:
        return {}


def _stream_in_network_entries(stream, prefix: str
                               ) -> Iterator[dict]:
    """Yield one in_network entry at a time. ``prefix`` is the
    text already read past the opening `[` (returned from
    _read_header_until_in_network).

    Tracks brace + bracket depth + skips over strings (with
    escape handling) so the boundaries fire on real entry ends,
    not braces inside string values.
    """
    buf = list(prefix)
    depth_brace = 0
    depth_bracket = 0
    in_string = False
    escape = False
    entry_start: Optional[int] = None
    pos = 0

    def _consume_chunk() -> bool:
        nonlocal pos, depth_brace, depth_bracket
        nonlocal in_string, escape, entry_start
        while pos < len(buf):
            ch = buf[pos]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
            else:
                if ch == '"':
                    in_string = True
                elif ch == "{":
                    if depth_brace == 0 and entry_start is None:
                        entry_start = pos
                    depth_brace += 1
                elif ch == "}":
                    depth_brace -= 1
                    if (depth_brace == 0
                            and entry_start is not None):
                        # Complete entry — yield it
                        text = "".join(
                            buf[entry_start:pos + 1])
                        try:
                            yield_payload = json.loads(text)
                        except json.JSONDecodeError:
                            yield_payload = None
                        # Trim consumed bytes from the buffer
                        del buf[:pos + 1]
                        pos = -1   # restart at 0 after del
                        entry_start = None
                        return yield_payload
                elif ch == "[":
                    depth_bracket += 1
                elif ch == "]":
                    depth_bracket -= 1
                    if depth_bracket < 0:
                        # End of in_network array
                        return False
            pos += 1
        return None  # need more data

    while True:
        produced = _consume_chunk()
        if produced is False:
            return        # array closed
        if produced is None:
            chunk = stream.read(8192)
            if not chunk:
                return
            buf.extend(chunk)
            continue
        # produced is the parsed dict — yield to caller
        yield produced


def streaming_parse_payer_tic_mrf(
    path: Any,
) -> Iterator[PayerRateRecord]:
    """Stream-parse a TiC MRF file → PayerRateRecord iterator.

    Bounded memory: only the current in_network entry sits in
    RAM at any time. The caller iterates and persists.

    Output records are bit-compatible with parse_payer_tic_mrf:
    the same downstream loaders consume them without changes.
    """
    p = Path(str(path))
    if not p.is_file():
        raise FileNotFoundError(f"Payer TiC MRF not found at {p}")

    with _open_text(p) as stream:
        header, remainder = _read_header_until_in_network(stream)
        meta = _extract_top_level_metadata(header)
        payer = normalize_payer_name(
            meta.get("reporting_entity_name"))
        plan = str(meta.get("plan_name") or "").strip()

        for entry in _stream_in_network_entries(
                stream, remainder):
            ctype = str(entry.get("billing_code_type")
                        or "CPT").upper()
            normed = normalize_code(
                entry.get("billing_code"), ctype)
            if not normed:
                continue
            service_line = classify_service_line(normed, ctype)
            for nr in (entry.get("negotiated_rates") or []):
                npis: list = []
                for pg in (nr.get("provider_groups") or []):
                    for npi in (pg.get("npi") or []):
                        if npi:
                            npis.append(str(npi))
                for price in (nr.get("negotiated_prices") or []):
                    rate = _safe_float(
                        price.get("negotiated_rate"))
                    arrangement = str(
                        price.get("negotiated_type")
                        or "ffs").lower()
                    basis = price.get("billing_class")
                    expires = price.get("expiration_date")
                    emit_npis = npis or [""]
                    for npi in emit_npis:
                        yield PayerRateRecord(
                            payer_name=payer,
                            plan_name=plan,
                            npi=npi,
                            code=normed,
                            code_type=ctype,
                            negotiation_arrangement=arrangement,
                            negotiated_rate=rate,
                            negotiation_basis=basis,
                            expiration_date=expires,
                            service_line=service_line,
                        )


def load_payer_tic_mrf_streaming(
    store: Any,
    path: Any,
    *,
    source_key: Optional[str] = None,
    chunk_commit: int = 5000,
) -> int:
    """Stream a TiC MRF + persist in chunks.

    Commits every ``chunk_commit`` rows so a 10GB file doesn't
    sit on a single open transaction. Returns total rows
    persisted.
    """
    store.init_db()
    now = datetime.now(timezone.utc).isoformat()
    n = 0
    seen_payer: Optional[str] = None
    seen_plan: Optional[str] = None
    pending: list = []

    def _flush(con) -> None:
        nonlocal pending
        if not pending:
            return
        con.execute("BEGIN IMMEDIATE")
        try:
            for r in pending:
                con.execute(
                    """INSERT OR REPLACE INTO pricing_payer_rates
                    (payer_name, plan_name, npi, code, code_type,
                     negotiation_arrangement, negotiated_rate,
                     negotiation_basis, expiration_date,
                     service_line, loaded_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (r.payer_name, r.plan_name, r.npi, r.code,
                     r.code_type, r.negotiation_arrangement,
                     r.negotiated_rate, r.negotiation_basis,
                     r.expiration_date, r.service_line, now))
            con.commit()
            pending = []
        except Exception:
            con.rollback()
            raise

    with store.connect() as con:
        for r in streaming_parse_payer_tic_mrf(path):
            if seen_payer is None:
                seen_payer = r.payer_name
                seen_plan = r.plan_name
            pending.append(r)
            n += 1
            if len(pending) >= chunk_commit:
                _flush(con)
        _flush(con)
        # Final load-log entry
        key = source_key or (
            f"{seen_payer or 'unknown'}|{seen_plan or ''}")
        con.execute("BEGIN IMMEDIATE")
        try:
            con.execute(
                "INSERT OR REPLACE INTO pricing_load_log "
                "(source, key, record_count, loaded_at, notes) "
                "VALUES (?, ?, ?, ?, ?)",
                ("payer_tic", key, n, now, "streaming"),
            )
            con.commit()
        except Exception:
            con.rollback()
            raise
    return n
