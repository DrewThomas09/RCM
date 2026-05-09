"""Reproducible-artifact embedding for LP / IC / QoE exports.

PROMPTS.md Phase 5 / Prompts 66 + 67: an exported LP update or IC
memo HTML must include enough state for an LP analyst to verify
the math themselves — without the full RCM-MC runtime. The
exported HTML embeds:

* the full input set used to generate the artifact (canonical JSON)
* the packet hash + run_id
* a 50-line stdlib-only ``verify.py`` script that:
    1. parses the embedded JSON
    2. recomputes the SHA-256 over the canonicalised inputs
    3. compares against the embedded hash
    4. prints VERIFIED / MISMATCH

The script ships as a constant in this module so each artifact
embeds exactly the same verification logic. Callers pass any
payload dict; the helper computes the canonical hash and emits the
embedded markup.

Public API::

    from rcm_mc.exports.reproducibility import (
        canonical_hash, reproducibility_block, VERIFY_SCRIPT,
    )
"""
from __future__ import annotations

import hashlib
import html as _html
import json
from typing import Any


# Stdlib-only verification script, embedded in every artifact. The
# trailing ``__main__`` guard reads either the artifact itself or
# the embedded JSON (extracted from the artifact via a regex).
VERIFY_SCRIPT = r'''#!/usr/bin/env python3
"""Verify a SeekingChartis reproducible artifact.

Usage:
    python verify.py <artifact.html>

Reads the embedded inputs JSON, recomputes the SHA-256 over the
canonicalised inputs, and compares against the hash declared by
the exporter. Stdlib-only — no rcm_mc dependency.
"""
import hashlib
import json
import re
import sys

PAYLOAD_RE = re.compile(
    r'<script type="application/json" id="rcm-reproducibility-payload">'
    r'(.*?)'
    r'</script>',
    re.DOTALL,
)


def canonical_hash(payload):
    canon = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def main(argv):
    if len(argv) != 2:
        print("usage: verify.py <artifact.html>")
        return 2
    with open(argv[1], "r", encoding="utf-8") as f:
        html = f.read()
    m = PAYLOAD_RE.search(html)
    if not m:
        print("MISMATCH: no embedded payload found")
        return 1
    payload = json.loads(m.group(1))
    inputs = payload.get("inputs")
    declared = payload.get("inputs_hash")
    if inputs is None or declared is None:
        print("MISMATCH: payload missing 'inputs' or 'inputs_hash'")
        return 1
    recomputed = canonical_hash(inputs)
    if recomputed != declared:
        print("MISMATCH: declared", declared)
        print("          recomputed", recomputed)
        return 1
    print("VERIFIED:", payload.get("run_id", "<no-run-id>"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
'''


def canonical_hash(payload: Any) -> str:
    """SHA-256 of ``json.dumps(payload, sort_keys=True,
    separators=(",", ":"))``. Used to declare the inputs hash inside
    the embedded payload — verify.py recomputes the same form."""
    canon = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def reproducibility_block(
    inputs: Any,
    *,
    run_id: str,
    artifact_kind: str,
) -> str:
    """Render the embed: a JSON script tag + a hidden verify.py
    script reference. Caller embeds the result somewhere in the
    artifact HTML before serialising; verify.py extracts it.

    ``inputs`` must be JSON-serialisable. ``run_id`` identifies
    this specific export (typically the analysis_runs row id or
    a packet build id). ``artifact_kind`` is one of
    ``"lp_update"`` / ``"ic_memo"`` / ``"qoe_memo"`` for telemetry.
    """
    inputs_hash = canonical_hash(inputs)
    payload = {
        "inputs": inputs,
        "inputs_hash": inputs_hash,
        "run_id": run_id,
        "artifact_kind": artifact_kind,
    }
    payload_json = json.dumps(payload)
    # ``</script>`` inside the JSON would prematurely close the tag;
    # JSON encoders don't escape forward slashes by default. Apply
    # the standard precaution.
    payload_json = payload_json.replace("</", r"<\/")
    return (
        '<script type="application/json" '
        'id="rcm-reproducibility-payload">'
        f'{payload_json}'
        '</script>'
        # Visible footer note + verify.py download. The verify
        # script is base64-embedded in a data: URL so a partner can
        # download it without round-tripping through a server.
        '<aside class="reproducibility-block">'
        '<strong>Reproducible artifact.</strong> '
        f'Run id <code>{_html.escape(run_id)}</code>; '
        f'inputs hash <code>{_html.escape(inputs_hash[:16])}…</code>. '
        '<a download="verify.py" '
        f'href="data:text/x-python;charset=utf-8,'
        f'{_data_url_quote(VERIFY_SCRIPT)}">Download verify.py</a> '
        'and run it on this file to confirm the inputs match.'
        '</aside>'
    )


def _data_url_quote(s: str) -> str:
    """Minimal percent-encoding for a data: URL payload. Stdlib
    quote_plus would also escape the LF + #; we only need to
    escape #, %, &, ?, and space-as-plus is fine inside a data URL
    body."""
    import urllib.parse
    return urllib.parse.quote(s, safe="")
