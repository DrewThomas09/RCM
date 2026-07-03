"""
source_adapters.py  (v40)
=========================

Naming note: "connector" already means two other things in this codebase, so
this module deliberately avoids the word in its name. `do_connectors` /
enrich.build_verified_connectors is the provider<->facility affiliation graph;
health.connector_status is the live-API reachability audit. This module is a
third thing: adapters that bind an external DATA SOURCE (a connected MCP tool,
a direct API wrapper, or a test double) to the exact contract a pipeline hook
expects, for seed refresh and validation.


The toolkit already reaches the public data it needs directly (clients.py hits
NPPES, data.cms.gov, RxNav; cms_rates.py hits the quarterly CMS flat files;
openpayments.py hits Open Payments). Those live calls stay the runtime path.

This module is the *seed-refresh and validation* layer on top of that: a set of
thin adapters that turn a supplied tool callable, in practice a connected MCP
tool (CMS Coverage, NPI Registry, ICD-10), but equally a direct API wrapper or a
test double, into the exact contract a given pipeline hook expects. The toolkit
never imports an MCP client and never depends on one at runtime; the callable is
injected, so the deterministic offline core is untouched. Supply nothing and
every adapter is an honest no-op.

Why this exists: three of the gaps the pipeline can only *flag* offline are
closable with a connector Andrew already has wired in Claude:

  gap                              connector (tool)                     hook
  -------------------------------  -----------------------------------  --------------------------
  SAD snapshot ages / partial      CMS Coverage (sad_exclusion_list)    sad_jurisdiction.refresh_from_cms
  recovered NPI not ground-truthed NPI Registry (npi_lookup)            enrich.build_npi_index
  diagnosis / therapy-area unsure  ICD-10 (validate_code, lookup_code)  therapy_area (referral dx)

Everything below maps a REAL tool response shape (verified 2026-07-02) to the
frame/row the hook consumes.
"""

from __future__ import annotations

import pandas as pd


# ---------------------------------------------------------------------------
# The gap -> source map, as data so it can be rendered in a report tab or the
# CLI. Each entry: the recoverable gap, the external source that closes it, the
# exact tool, and the pipeline hook that consumes the source output.
# ---------------------------------------------------------------------------
GAP_SOURCE_MAP = [
    {"gap": "SAD snapshot ages or is a partial slice",
     "connector": "CMS Coverage", "tool": "sad_exclusion_list",
     "hook": "sad_jurisdiction.refresh_from_cms(cms_sad_fetcher(tool))",
     "closes": "re-pulls the full 1502-row per-MAC exclusion list and normalizes "
               "it to the classifier seed shape for a diff-then-replace"},
    {"gap": "recovered/original billing NPI not ground-truthed in NPPES",
     "connector": "NPI Registry", "tool": "npi_lookup",
     "hook": "enrich.build_npi_index(..., lookup=nppes_enricher(tool))",
     "closes": "confirms the NPI is assigned and active, and returns the "
               "authoritative name, taxonomy, license, and practice state"},
    {"gap": "referral diagnosis / therapy-area inference unverified",
     "connector": "ICD-10", "tool": "validate_code + lookup_code",
     "hook": "therapy_area referral-dx annotation via icd10_annotator(tool)",
     "closes": "validates the ICD-10-CM code and returns its description and "
               "chapter so therapy-area rollups rest on real codes, not guesses"},
    {"gap": "MAC roster / jurisdiction drift",
     "connector": "CMS Coverage", "tool": "get_contractors",
     "hook": "reference/mac_jurisdictions_seed.csv refresh",
     "closes": "confirms the eight active MAC organizations and their SAD "
               "article ids behind the state->MAC map"},
]


def adapter_registry_frame() -> pd.DataFrame:
    """The gap->connector map as a frame, for a report tab or --connectors."""
    return pd.DataFrame(GAP_SOURCE_MAP)[["gap", "connector", "tool", "closes", "hook"]]


# ---------------------------------------------------------------------------
# CMS Coverage -> SAD refresh
# ---------------------------------------------------------------------------
def cms_sad_fetcher(tool_callable, **fixed_kwargs):
    """Adapt the CMS Coverage `sad_exclusion_list` tool into the fetch_callable
    that sad_jurisdiction.refresh_from_cms expects (it calls fetch(limit=..,
    page_token=..) and reads resp['items'] / resp['next_page_token']).

    The MCP tool already returns exactly that shape, so this is a passthrough
    that (a) forwards limit/page_token, (b) merges any fixed filters the caller
    wants pinned (e.g. keyword='infusion', date_option='current'), and (c)
    tolerates the tool returning a bare list instead of a dict.
    """
    if tool_callable is None:
        return None

    def _fetch(**kw):
        args = dict(fixed_kwargs)
        if "limit" in kw and kw["limit"] is not None:
            args["limit"] = kw["limit"]
        if kw.get("page_token"):
            args["page_token"] = kw["page_token"]
        resp = tool_callable(**args)
        if isinstance(resp, list):
            return {"items": resp, "next_page_token": None}
        return resp if isinstance(resp, dict) else {"items": [], "next_page_token": None}

    return _fetch


# ---------------------------------------------------------------------------
# NPI Registry -> NPPES enrichment
# ---------------------------------------------------------------------------
def nppes_record_to_index_row(resp: dict) -> dict:
    """Map one NPI Registry `npi_lookup` response to the compact index row the
    enrichment layer keys on: {name, entity_type, specialty, taxonomy_code,
    license, state, status, found}. Robust to the not-found and error shapes."""
    if not isinstance(resp, dict) or not resp.get("found"):
        return {"found": False}
    rec = resp.get("record", {}) or {}
    basic = rec.get("basic", {}) or {}
    tax = rec.get("primary_taxonomy", {}) or {}
    addr = rec.get("primary_practice_address", {}) or {}
    return {
        "found": True,
        "name": rec.get("name", ""),
        "entity_type": rec.get("enumeration_type", ""),          # Individual / Organization
        "credential": basic.get("credential", ""),
        "status": basic.get("status", ""),                       # A active / D deactivated
        "taxonomy_code": tax.get("code", ""),
        "specialty": tax.get("desc", ""),
        "license": tax.get("license", ""),
        "state": addr.get("state", "") or tax.get("state", ""),
        "enumeration_date": basic.get("enumeration_date", ""),
    }


def nppes_enricher(tool_callable):
    """Return a callable npi -> index_row backed by the NPI Registry tool.
    Honest no-op factory: returns None when no tool is supplied, so callers can
    fall back to clients.py's direct NPPES path. The returned callable never
    raises, a lookup failure yields {found: False}."""
    if tool_callable is None:
        return None

    def _lookup(npi):
        try:
            return nppes_record_to_index_row(tool_callable(npi=str(npi).strip()))
        except Exception:
            return {"found": False}

    return _lookup


# ---------------------------------------------------------------------------
# ICD-10 -> diagnosis / therapy-area annotation
# ---------------------------------------------------------------------------
def icd10_annotator(validate_callable=None, lookup_callable=None):
    """Return a callable code -> {code, valid, hipaa, description, category} that
    validates and describes an ICD-10-CM diagnosis code via the ICD-10 tool.

    validate_callable wraps `validate_code`; lookup_callable wraps `lookup_code`.
    Either may be supplied alone. Returns None when neither is given. The callable
    never raises; an unknown code yields valid=False so therapy-area rollups can
    exclude it rather than trust a bad code."""
    if validate_callable is None and lookup_callable is None:
        return None

    def _annotate(code):
        c = str(code or "").strip().upper()
        out = {"code": c, "valid": False, "hipaa": False, "description": "", "category": ""}
        if not c:
            return out
        try:
            if lookup_callable is not None:
                r = lookup_callable(code=c, code_type="diagnosis")
                if isinstance(r, dict) and r.get("found"):
                    cc = r.get("code", {}) or {}
                    out.update(valid=True,
                               hipaa=bool(cc.get("valid_for_hipaa_transactions")),
                               description=cc.get("long_description")
                               or cc.get("short_description", ""),
                               category=cc.get("category", ""))
                    return out
            if validate_callable is not None:
                r = validate_callable(code=c, code_type="diagnosis")
                if isinstance(r, dict):
                    out["valid"] = bool(r.get("valid") or r.get("found"))
                    out["hipaa"] = bool(r.get("valid_for_hipaa_transactions")
                                        or r.get("hipaa"))
                    out["description"] = r.get("description") or r.get("long_description", "")
        except Exception:
            return out
        return out

    return _annotate


def annotate_referral_dx(codes, annotator) -> pd.DataFrame:
    """Validate a set of referral diagnosis codes and return a frame with the
    verdict per code. With no annotator, returns an honest note frame so the
    caller can proceed on the offline therapy-area map. Deduplicates input."""
    uniq = sorted({str(c).strip().upper() for c in codes if str(c).strip()})
    if annotator is None:
        return pd.DataFrame({"note": ["no ICD-10 connector supplied; therapy-area "
                                      "rollup runs on the shipped therapy_area map"]})
    rows = [annotator(c) for c in uniq]
    out = pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["code", "valid", "hipaa", "description", "category"])
    if len(out):
        out.attrs["note"] = ("{} of {} referral diagnosis codes validate against "
                             "ICD-10-CM.".format(int(out["valid"].sum()), len(out)))
    return out
