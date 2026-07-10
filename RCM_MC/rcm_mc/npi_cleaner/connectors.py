"""Live public-data connectors for the NPI cleaner's online mode.

Cross-uses the connectors PE Desk already ships in ``rcm_mc.data_public`` —
NPPES, RxNorm/RxNav, openFDA — plus the shared public-API catalog, rather than
standing up new clients. Everything here is **opt-in** (the page's online-mode
box), **bounded** (distinct values only, capped per run), and **guarded**: a
missing module or a blocked network degrades to a note, never an exception into
the pipeline. Every network entry point accepts an ``opener`` so tests inject a
fake transport and never touch the internet.

Connectors, by the column they light up:

  * **RxNorm / RxNav** — NDC and drug-name columns → RxCUI + normalized
    ingredient/brand (``rxcui``, ``name``, ``tty``). The join that turns a raw
    NDC or free-text drug into a stable concept.
  * **openFDA** — NDC → drug product label (brand / generic / labeler).
  * **NPPES** — NPI columns → verify (active vs. deactivated) + recover a
    candidate NPI from a provider/org name (delegated to ``nppes_bridge``).

``catalog()`` also exposes the full ~19-source public-data catalog so the page
can show every connection available for wiring.
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional

# Per-run caps so a huge file can't fan out into thousands of calls.
_MAX_RXNORM = 40
_MAX_OPENFDA = 20

# Machine-readable data-status values for connector_status()/health().
# LIVE-PACK   — full offline data on disk, ready to act on a run.
# DEGRADED    — data present but sampled/stale; results are a floor.
# UNAVAILABLE — nothing on disk; the source cannot act offline.
STATUS_LIVE = "LIVE-PACK"
STATUS_DEGRADED = "DEGRADED"
STATUS_UNAVAILABLE = "UNAVAILABLE"


def available() -> bool:
    try:
        from ..data_public import public_api_clients  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


# Sources that actually DO something in a cleaning run today. NPPES,
# RxNorm and openFDA fire in enrich mode (see engine._enrich_via_nppes +
# connectors.resolve_drugs); OIG LEIE screens offline once its pack is
# installed; PECOS runs behind the deep flag. Everything else in the
# catalog is reachable elsewhere in PE Desk but is NOT wired to a claims
# clean — the panel used to imply all of them were, which is misleading
# on a compliance-adjacent surface. "rxnav" was dropped from this set:
# no resolver ever produced that id (resolve_drugs emits "rxnorm" and
# "openfda" only), so it was a ghost connector the panel advertised but
# that could never fire. The RxNav crosswalk rides the "rxnorm" id.
_CLEANING_WIRED = frozenset({
    "nppes", "rxnorm", "openfda", "oig_leie", "pecos",
    # data.cms.gov Medicare enrichments (enrich.py) — selected per upload
    # on the Enrichment panel: national per-HCPCS benchmark + per-NPI
    # Medicare volumes.
    "cms_geo_service", "cms_by_provider",
})


def catalog() -> List[dict]:
    """Every public-data source PE Desk can reach, for the connections
    panel. ``cleaning_wired`` is the honest per-source claim for THIS
    tool; ``is_wired`` is the platform-wide "has a client" flag."""
    try:
        from ..data_public import public_api_catalog as cat
    except Exception:  # noqa: BLE001
        return []
    out = []
    for s in cat.all_sources():
        out.append({
            "id": s.id, "name": s.name, "operator": s.operator,
            "category": getattr(s, "category", ""),
            "cost": getattr(s, "cost", ""),
            "docs_url": getattr(s, "docs_url", ""),
            "status": getattr(s, "status", ""),
            "is_wired": bool(getattr(s, "is_wired", False)),
            "cleaning_wired": s.id in _CLEANING_WIRED,
        })
    # PECOS is wired for cleaning (compliance.screen_cms behind the deep
    # flag) but the shared public-API catalog defines no ApiSource for it,
    # so the connections panel could never show the source that actually
    # runs. Append a synthetic entry so the panel matches reality.
    if not any(d["id"] == "pecos" for d in out):
        try:
            from . import compliance as _compliance
            _pecos_live = _compliance._build_cms_client() is not None
        except Exception:  # noqa: BLE001
            _pecos_live = False
        out.append({
            "id": "pecos",
            "name": "Medicare PECOS (enrollment · opt-out)",
            "operator": "CMS",
            "category": "providers",
            "cost": "free",
            "docs_url": "https://data.cms.gov/provider-characteristics",
            "status": "live" if _pecos_live else "planned",
            "is_wired": _pecos_live,
            "cleaning_wired": True,
        })
    # The Medicare enrichment connectors (enrich.py) run against
    # data.cms.gov's Data API directly; the shared catalog has no
    # ApiSource for those two datasets, so append synthetic entries the
    # same way PECOS gets one — the panel must show what can actually run.
    for cid, cname, cdocs in (
        ("cms_geo_service",
         "Medicare Physician & Other Practitioners — by Geography and "
         "Service (rate benchmark)",
         "https://data.cms.gov/provider-summary-by-type-of-service/"
         "medicare-physician-other-practitioners"),
        ("cms_by_provider",
         "Medicare Physician & Other Practitioners — by Provider "
         "(NPI volumes)",
         "https://data.cms.gov/provider-summary-by-type-of-service/"
         "medicare-physician-other-practitioners"),
    ):
        if not any(d["id"] == cid for d in out):
            out.append({
                "id": cid, "name": cname, "operator": "CMS",
                "category": "providers", "cost": "free",
                "docs_url": cdocs, "status": "live",
                "is_wired": True, "cleaning_wired": True,
            })
    # Wired-for-cleaning first, then alphabetical — the sources that act
    # on a run should lead the panel.
    out.sort(key=lambda d: (not d["cleaning_wired"], d["name"].lower()))
    return out


def _pack_status_map() -> Dict[str, dict]:
    """Reference-pack install state keyed by pack id, or {} when the
    packs module is unavailable. Reads pack_meta only (cheap) — never
    loads the code sets themselves."""
    try:
        from . import refdata_packs
        return {str(d.get("id")): d for d in refdata_packs.status()}
    except Exception:  # noqa: BLE001
        return {}


def _leie_data_source() -> tuple:
    """(available, source_label) for the offline LEIE screen. The plan
    panel used to claim 'Screen billing NPIs against the OIG exclusions
    list' without checking any LEIE data existed — a silent nothing on a
    compliance-adjacent claim. Checks the same two sources the screen
    itself uses (compliance.screen_leie): the RCM_MC_LEIE_CSV file, then
    the installed reference pack."""
    p = os.environ.get("RCM_MC_LEIE_CSV") or ""
    try:
        if p and Path(p).exists():
            return True, "local CSV via RCM_MC_LEIE_CSV"
    except OSError:
        pass
    info = _pack_status_map().get("leie") or {}
    if info.get("installed"):
        label = "installed reference pack"
        if info.get("fetched_iso"):
            label += f", pulled {info['fetched_iso']}"
        return True, label
    return False, ""


# The connector "recommendation engine": given the shape of THIS file (which
# roles were detected, how blank the NPIs are, how drug-heavy it is), decide
# which of the wired connectors should fire and say why in plain language.
# Surfaced on the Live-connectors tab so a run that only lights 2 of the
# catalog is legible ("openFDA — no NDC/J-code column in this file") instead of
# looking broken. ``mode`` gates *when* it runs: offline always, network in
# enrich mode, deep behind the deep flag.
def plan(signals: Dict[str, object]) -> List[dict]:
    """Return an ordered recommendation for each wired connector.

    ``signals`` keys (all optional): ``has_npi``, ``has_billing``,
    ``blank_npi_pct`` (0-100), ``has_ndc``, ``has_drug_name``,
    ``jcode_pct`` (0-100 of HCPCS rows that are J-codes), ``has_hcpcs``,
    ``has_dx``, ``has_taxonomy``, ``rows``.
    """
    s = signals or {}
    has_npi = bool(s.get("has_npi"))
    has_billing = bool(s.get("has_billing"))
    blank = float(s.get("blank_npi_pct") or 0.0)
    has_ndc = bool(s.get("has_ndc"))
    has_drug = bool(s.get("has_drug_name"))
    jcode = float(s.get("jcode_pct") or 0.0)
    has_hcpcs = bool(s.get("has_hcpcs"))
    has_dx = bool(s.get("has_dx"))
    has_taxonomy = bool(s.get("has_taxonomy"))
    try:
        rows = int(s.get("rows") or 0)
    except (TypeError, ValueError):
        rows = 0
    drug_signal = has_ndc or has_drug or jcode > 0
    out: List[dict] = []

    # ``state`` is the honest data claim behind ``applies``: "ready"
    # (will actually run), "needs_data" (applicable, but no offline data
    # is installed so it will do NOTHING until the user acts), "n/a".
    def add(cid, name, applies, mode, reason, state=None):
        out.append({"id": cid, "name": name, "applies": bool(applies),
                    "mode": mode, "reason": reason,
                    "state": state or ("ready" if applies else "n/a")})

    # --- NPPES: verify every NPI; recover blanks when the file is gappy ---
    _cap_note = (" Large file: live verification is capped per run and "
                 "prioritizes the highest-dollar NPIs." if rows >= 5000
                 else "")
    if has_npi:
        if blank >= 1.0:
            add("nppes", "NPPES NPI Registry", True, "network",
                f"{blank:.1f}% of billing NPIs are blank — verify present "
                "NPIs and recover the blanks from provider name + state."
                + _cap_note)
        else:
            add("nppes", "NPPES NPI Registry", True, "network",
                "Verify each distinct NPI is active (not deactivated)."
                + _cap_note)
    else:
        add("nppes", "NPPES NPI Registry", False, "network",
            "No NPI column detected in this file.")

    # --- Drug connectors: NDC, free-text drug name, or J-codes.
    # One row for the RxNorm/RxNav pair — the old separate "rxnav" row
    # advertised a connector no resolver implements (resolve_drugs emits
    # ids "rxnorm"/"openfda" only), so the panel promised a source that
    # could never fire. The HCPCS/J-code crosswalk IS RxNav and runs
    # under the rxnorm id.
    why_drug = []
    if has_ndc:
        why_drug.append("NDC column")
    if has_drug:
        why_drug.append("drug-name column")
    if jcode > 0:
        why_drug.append(f"{jcode:.0f}% J-codes")
    drug_reason = (", ".join(why_drug)
                   + " → resolve to RxNorm concepts (RxNav crosswalk)."
                   if drug_signal else
                   "No NDC, drug-name, or J-code column in this file.")
    add("rxnorm", "RxNorm / RxNav", drug_signal, "network", drug_reason)
    if has_ndc:
        add("openfda", "openFDA drug label", True, "network",
            "Match NDC / J-code drugs to an FDA product label.")
    elif jcode > 0:
        # Honest ghost-claim guard: openFDA matches by NDC, and the engine
        # feeds it the NDC column only — on a J-code file with no NDC
        # column the connector sits idle, so saying "ready" here promised
        # a lookup that never fires.
        add("openfda", "openFDA drug label", True, "network",
            "J-codes present but no NDC column — openFDA labels match by "
            "NDC, so this connector sits idle on this file (RxNorm's "
            "HCPCS crosswalk covers the J-codes).", state="needs_data")
    else:
        add("openfda", "openFDA drug label", False, "network",
            "No NDC or J-code column to label.")

    # --- Compliance: billing NPI screens ---
    if not has_billing:
        add("oig_leie", "OIG LEIE exclusions", False, "offline",
            "No billing NPI column to screen.")
    else:
        _leie_ok, _leie_src = _leie_data_source()
        if _leie_ok:
            _leie_reason = ("Screen billing NPIs against the OIG "
                            f"exclusions list ({_leie_src}).")
            _leie_info = _pack_status_map().get("leie") or {}
            if _leie_info.get("installed") and _leie_info.get("stale"):
                _leie_reason += (
                    f" Pack is {_leie_info.get('age_days', 0):.0f} days old"
                    " — OIG refreshes monthly; re-pull for a current list.")
            add("oig_leie", "OIG LEIE exclusions", True, "offline",
                _leie_reason, state="ready")
        else:
            add("oig_leie", "OIG LEIE exclusions", True, "offline",
                "LEIE data not installed — nothing will be screened. Pull "
                "the leie pack (Reference data packs) or set RCM_MC_LEIE_CSV "
                "to a downloaded UPDATED.csv.", state="needs_data")
    add("pecos", "Medicare PECOS enrollment", has_billing, "deep",
        ("Confirm Medicare enrollment / opt-out for billing NPIs "
         "(deep mode)." if has_billing else "No billing NPI column."))

    # --- Reference packs: the highest-leverage OFFLINE enrichment for a
    # code-heavy file. These signals were documented and passed by the
    # engine but never read, so a dx-heavy file was never told the one
    # thing that would validate its codes.
    packs = _pack_status_map()
    for pid, pname, signal, why, miss in (
        ("icd10cm", "ICD-10-CM code set (reference pack)", has_dx,
         "Diagnosis column present — validate against the full ICD-10-CM "
         "set to catch shaped-but-nonexistent codes.",
         "No diagnosis column in this file."),
        ("hcpcs", "HCPCS Level II set (reference pack)",
         has_hcpcs or jcode > 0,
         "Procedure column present — validate letter-led HCPCS Level II "
         "codes against the CMS quarterly set.",
         "No HCPCS/procedure column in this file."),
        ("taxonomy", "NUCC taxonomy (reference pack)", has_taxonomy,
         "Taxonomy column present — validate codes and display full "
         "specialty names from the complete NUCC set.",
         "No taxonomy column in this file."),
    ):
        info = packs.get(pid) or {}
        if not signal:
            add(f"pack_{pid}", pname, False, "offline", miss)
        elif info.get("installed"):
            extra = ""
            if info.get("stale"):
                extra = (f" Pack is {info.get('age_days', 0):.0f} days old —"
                         " past its refresh cadence; consider re-pulling.")
            add(f"pack_{pid}", pname, True, "offline",
                why + f" Installed ({int(info.get('rows') or 0):,} rows)."
                + extra, state="ready")
        else:
            _hint = (" or bootstrap it offline from the vendored v49 table"
                     if pid == "icd10cm" else "")
            add(f"pack_{pid}", pname, True, "offline",
                why + " Pack not installed — pull it from Reference data "
                "packs" + _hint + ".", state="needs_data")

    # --- Medicare enrichment connectors (enrich.py) — run only when the
    # upload SELECTS them on the Enrichment panel, so the coverage table
    # says "selectable" rather than promising an automatic run. Their own
    # mode value keeps them out of the network set the drug/NPPES
    # resolvers own.
    add("cms_geo_service", "Medicare rate benchmark (data.cms.gov)",
        has_hcpcs or jcode > 0, "enrichment",
        ("Procedure codes present — select 'Medicare rate benchmark' in "
         "Enrichment to price the top codes at the CMS national average "
         "allowed amount." if (has_hcpcs or jcode > 0) else
         "No procedure-code column to benchmark."))
    add("cms_by_provider", "Medicare provider volumes (data.cms.gov)",
        has_billing, "enrichment",
        ("Billing NPIs present — select 'Medicare volumes for key "
         "providers' in Enrichment to size file volume against each "
         "provider's Medicare book." if has_billing else
         "No billing NPI column."))
    return out


def _fold_drug_key(value: str, by: str) -> str:
    """Fold a drug identifier to a match key so a row's cell resolves to the
    resolved concept regardless of surface form: NDC → digits only, HCPCS/
    J-code → uppercase alphanumerics, drug name → case/space-folded."""
    v = str(value or "")
    if by == "ndc":
        return "".join(c for c in v if c.isdigit())
    if by == "hcpcs":
        return "".join(c for c in v.upper() if c.isalnum())
    return " ".join(v.split()).casefold()


def _distinct(values: List[str], cap: int) -> tuple:
    """Distinct non-empty, order-preserving, with a truncation flag."""
    seen: List[str] = []
    for v in values:
        s = str(v or "").strip()
        if s and s not in seen:
            seen.append(s)
    return (seen[:cap], len(seen) > cap)


def _ndc_candidates(raw: object) -> List[str]:
    """Candidate hyphenated package-NDC forms for an openFDA lookup.

    Claims files overwhelmingly carry unhyphenated 11-digit NDCs (the
    CMS 5-4-2 billing format), while openFDA's ``package_ndc`` is the
    FDA *native* hyphenated form (4-4-2 / 5-3-2 / 5-4-1 — 10 digits).
    The old digits-only exact-phrase query therefore matched nothing on
    real files ("0 of N NDCs matched" read as a data problem when it was
    a query-shape bug). Derive the native candidates by removing the
    billing pad zero from whichever segment carries it, plus the 5-4-2
    form itself. A 10-digit hyphenated input is already the native form
    and passes through as-is; an 11-digit hyphenated input is the billing
    form with hyphens, so it goes through the same derivation as bare
    digits (passing it through unchanged left hyphenated claims NDCs as
    dead as the digits-only query this function replaced). Bare 10-digit
    values are ambiguous — native with hyphens stripped (4-4-2 / 5-3-2 /
    5-4-1) or billing with a dropped leading zero — so ALL readings are
    queried in the one OR group rather than guessing one."""
    s = str(raw or "").strip()
    if not s:
        return []
    if "-" in s:
        parts = [re.sub(r"\D", "", p) for p in s.split("-")]
        digits = "".join(parts)
        if len(parts) == 3 and all(parts) and len(digits) == 10:
            return ["-".join(parts)]     # already the FDA native form
    else:
        digits = "".join(c for c in s if c.isdigit())
    cands: List[str] = []
    if len(digits) == 10:
        # Native readings of the bare 10 digits, most common first.
        cands.append(f"{digits[:4]}-{digits[4:8]}-{digits[8:]}")   # 4-4-2
        cands.append(f"{digits[:5]}-{digits[5:8]}-{digits[8:]}")   # 5-3-2
        cands.append(f"{digits[:5]}-{digits[5:9]}-{digits[9:]}")   # 5-4-1
        digits = digits.zfill(11)        # billing reading: dropped pad zero
    if len(digits) != 11:
        return []
    lab, prod, pkg = digits[:5], digits[5:9], digits[9:]
    if lab.startswith("0"):
        cands.append(f"{lab[1:]}-{prod}-{pkg}")      # native 4-4-2
    if prod.startswith("0"):
        cands.append(f"{lab}-{prod[1:]}-{pkg}")      # native 5-3-2
    if pkg.startswith("0"):
        cands.append(f"{lab}-{prod}-{pkg[1:]}")      # native 5-4-1
    cands.append(f"{lab}-{prod}-{pkg}")              # billing 5-4-2
    seen: set = set()
    return [c for c in cands if not (c in seen or seen.add(c))]


def _ndc_search_expr(keys: List[str], field: str = "package_ndc") -> str:
    """openFDA search expression matching ANY of ``keys`` on ``field``
    (openFDA treats space-separated quoted terms in a group as OR)."""
    if len(keys) == 1:
        return f'{field}:"{keys[0]}"'
    return f"{field}:(" + " ".join(f'"{k}"' for k in keys) + ")"


def _is_http_404(exc: Exception) -> bool:
    """True when an openFDA lookup failure is the API's zero-results
    answer. openFDA replies HTTP 404 when a search matches NOTHING, and
    the shared client raises on 4xx — so without this check every
    honestly-unmatched NDC counted as a lookup ERROR, and a connected
    run over unlabeled NDCs reported 'Could not reach openFDA' (a
    fabricated outage) instead of '0 of N matched'."""
    for e in (exc, getattr(exc, "__cause__", None)):
        if e is not None and getattr(e, "code", None) == 404:
            return True
    return "HTTP 404" in str(exc)


def resolve_drugs(
    ndcs: List[str], names: List[str], *,
    hcpcs: Optional[List[str]] = None,
    opener: Optional[Callable] = None,
    rxnorm_cap: int = _MAX_RXNORM, openfda_cap: int = _MAX_OPENFDA,
) -> List[dict]:
    """Run the drug connectors (RxNorm, openFDA) over distinct NDCs, drug
    names, and HCPCS/J-codes.

    J-codes are HCPCS Level II drug codes (``J1745`` = infliximab): an
    infusion-pharmacy or oncology extract is often *all* J-codes with no NDC
    and no free-text drug name, so resolving them through RxNav's
    ``idtype=HCPCS`` crosswalk is the difference between the drug connectors
    firing and sitting idle. Returns a list of connector-result dicts (one per
    connector that had inputs), each with counts + a small sample.
    """
    results: List[dict] = []
    try:
        from ..data_public import public_api_clients as pac
    except Exception:  # noqa: BLE001
        return results

    ndc_list, ndc_trunc = _distinct(ndcs, rxnorm_cap)
    name_list, name_trunc = _distinct(names, rxnorm_cap)
    hcpcs_list, hcpcs_trunc = _distinct(hcpcs or [], rxnorm_cap)

    # ---- RxNorm / RxNav: NDC / drug name / HCPCS J-code → concept ----
    if ndc_list or name_list or hcpcs_list:
        resolved, unresolved, sample = 0, 0, []
        errors = 0
        # Normalized concept map for deterministic blanks-only fills back on
        # the engine: keyed by folded value so a row's cell matches regardless
        # of NDC punctuation / J-code case / drug-name spacing.
        concepts: Dict[str, dict] = {"ndc": {}, "name": {}, "hcpcs": {}}
        for value, by, kind in (
                [(v, "ndc", "NDC") for v in ndc_list]
                + [(v, "name", "name") for v in name_list]
                + [(v, "hcpcs", "J-code") for v in hcpcs_list]):
            try:
                concept = pac.rxnorm_normalize(value, by=by, opener=opener)
            except Exception:  # noqa: BLE001
                errors += 1
                continue
            if concept:
                resolved += 1
                ckey = _fold_drug_key(value, by)
                if ckey:
                    concepts[by][ckey] = {
                        "name": concept.get("name", ""),
                        "ndcs": list(concept.get("ndcs", []) or []),
                        "rxcui": concept.get("rxcui", "")}
                if len(sample) < 12:
                    sample.append({"input": value, "kind": kind,
                                   "rxcui": concept.get("rxcui", ""),
                                   "name": concept.get("name", ""),
                                   "tty": concept.get("tty", "")})
            else:
                unresolved += 1
        queried = len(ndc_list) + len(name_list) + len(hcpcs_list)
        if queried and errors == queried:
            # Every lookup failed → connectivity/outage, not unresolvable
            # inputs. Say so plainly instead of "0 of N resolved".
            note = (f"Could not reach RxNorm/RxNav — all {errors} drug "
                    "lookups failed (network/connectivity)")
        else:
            note = (f"{resolved} of {queried} distinct drug values "
                    "resolved to an RxNorm concept")
            if ndc_trunc or name_trunc or hcpcs_trunc:
                note += f" (capped at {rxnorm_cap} each)"
            if errors:
                note += f"; {errors} lookup errors (skipped)"
        # Row-level coverage: how many CELLS of this file the resolved
        # concepts cover, not just how many distinct values were queried
        # — the number the scorecard needs to say what the connector
        # actually earned on this run.
        rows_seen = 0
        rows_enriched = 0
        for values, by in ((ndcs, "ndc"), (names, "name"),
                           (hcpcs or [], "hcpcs")):
            for v in values:
                if not str(v or "").strip():
                    continue
                rows_seen += 1
                if _fold_drug_key(v, by) in concepts[by]:
                    rows_enriched += 1
        results.append({
            "id": "rxnorm", "label": "RxNorm / RxNav",
            "source": "rxnav.nlm.nih.gov via data_public.public_api_clients",
            "queried": queried,
            "resolved": resolved, "unresolved": unresolved,
            "rows_seen": rows_seen, "rows_enriched": rows_enriched,
            "sample": sample, "note": note + ".",
            "concepts": concepts,
        })

    # ---- openFDA: NDC → drug label (brand / generic / labeler) ----
    ofda_list, ofda_trunc = _distinct(ndcs, openfda_cap)
    if ofda_list:
        labeled, sample, errors = 0, [], 0
        labeled_keys: set = set()
        for ndc in ofda_list:
            cands = _ndc_candidates(ndc)
            if not cands:
                continue  # not NDC-shaped; honestly unresolved, no call
            rec = None
            failures = 0
            # Primary: package_ndc across the native-form candidates;
            # fallback: product_ndc on the labeler-product prefix (some
            # labels list packages the directory row omits).
            prod_keys = sorted({c.rsplit("-", 1)[0] for c in cands})
            for field, keys in (("package_ndc", cands),
                                ("product_ndc", prod_keys)):
                try:
                    res = pac.openfda_search(
                        "drug", "ndc", search=_ndc_search_expr(keys, field),
                        limit=1, opener=opener)
                except Exception as exc:  # noqa: BLE001
                    # HTTP 404 is openFDA's "no matches" — a miss, not an
                    # outage; only transport failures feed the
                    # connectivity note.
                    if not _is_http_404(exc):
                        failures += 1
                    continue
                if isinstance(res, list) and res:
                    rec = res[0]
                    break
            if rec is None and failures == 2:
                errors += 1
                continue
            if rec:
                labeled += 1
                labeled_keys.add(_fold_drug_key(ndc, "ndc"))
                if len(sample) < 12:
                    sample.append({
                        "ndc": ndc,
                        "brand": rec.get("brand_name", ""),
                        "generic": rec.get("generic_name", ""),
                        "labeler": rec.get("labeler_name", ""),
                    })
        if ofda_list and errors == len(ofda_list):
            note = (f"Could not reach openFDA — all {errors} NDC lookups "
                    "failed (network/connectivity)")
        else:
            note = f"{labeled} of {len(ofda_list)} NDCs matched an openFDA label"
            if ofda_trunc:
                note += f" (capped at {openfda_cap})"
            if errors:
                note += f"; {errors} lookup errors (skipped)"
        _ndc_cells = [v for v in ndcs if str(v or "").strip()]
        results.append({
            "id": "openfda", "label": "openFDA drug label",
            "source": "api.fda.gov via data_public.public_api_clients",
            "queried": len(ofda_list), "resolved": labeled,
            "unresolved": len(ofda_list) - labeled,
            "rows_seen": len(_ndc_cells),
            "rows_enriched": sum(
                1 for v in _ndc_cells
                if _fold_drug_key(v, "ndc") in labeled_keys),
            "sample": sample, "note": note + ".",
        })

    return results


# --------------------------------------------------------------------------
# Machine-readable connector/data status — the honest inventory of what can
# actually act on a run in THIS deployment. Reports and analytics render it;
# nothing here touches the network, ever.
# --------------------------------------------------------------------------

# Vendored v49 reference seeds: (id, filename, display name, what it powers,
# full-set?, universe disclosure when sampled). "Full" means the shipped
# table is the complete public set at its vintage; a sample means the screen
# is a floor — a clean pass proves nothing about the uncovered rows.
_VENDOR_SEEDS = (
    ("ncci_mue", "ncci_mue_seed.csv", "CMS NCCI MUE units table",
     "v49 screen: units above the MUE limit", True, ""),
    ("ncci_ptp", "ncci_ptp_sample.csv", "CMS NCCI PTP pair edits",
     "v49 screen: PTP code-pair conflicts", False,
     "sample of the ~4M-pair NCCI PTP set"),
    ("icd10cm_validity", "icd10cm_validity_seed.csv",
     "ICD-10-CM validity (FY2025-26)",
     "v49 screen: diagnosis validity by service date", True, ""),
    ("jw_jz_policy", "jw_jz_single_dose_seed.csv",
     "CMS JW/JZ single-dose drug list",
     "v49 screen: JW/JZ wastage-modifier policy", True, ""),
    ("nppes_deactivated", "nppes_deactivated_seed.csv",
     "NPPES deactivated NPIs",
     "v49 screen: claim lines billing a deactivated NPI", False,
     "sample of the ~290k-row CMS deactivation file"),
    ("sad_snapshot", "sad_exclusion_seed.csv",
     "CMS SAD exclusion snapshot",
     "SAD jurisdiction/route classification + gap inventory", False,
     "slice of the ~1,502-row CMS SAD exclusion list"),
    ("mac_jurisdictions", "mac_jurisdictions_seed.csv",
     "Medicare MAC jurisdiction roster",
     "state → MAC map behind the SAD classifier", True, ""),
)

# Live (network) connectors: opt-in, so offline their honest status is
# UNAVAILABLE — never a fabricated "ok".
_NETWORK_SOURCES = (
    ("nppes", "NPPES NPI Registry (live)",
     "verify NPIs · recover blanks · fill name/state/taxonomy"),
    ("rxnorm", "RxNorm / RxNav (live)",
     "NDC / drug-name / J-code → RxNorm concept + blank fills"),
    ("openfda", "openFDA drug labels (live)",
     "NDC → FDA product label (brand / generic / labeler)"),
    ("pecos", "Medicare PECOS (live, deep mode)",
     "billing-NPI enrollment + opt-out screen"),
    ("cms_geo_service", "Medicare rate benchmark (data.cms.gov, live)",
     "top HCPCS → national Medicare avg allowed + gross-up basis"),
    ("cms_by_provider", "Medicare provider volumes (data.cms.gov, live)",
     "key billing NPIs → Medicare services / benes / payments"),
)

_SEED_CACHE: Dict[str, dict] = {}
_ISO_DATE = re.compile(r"20\d{2}-\d{2}-\d{2}")
_YEAR = re.compile(r"20\d{2}")


def _vendored_ref_dir() -> Optional[Path]:
    p = Path(__file__).parent / "vendor_v49" / "npi_recovery" / "reference"
    return p if p.is_dir() else None


def _seed_info(path: Path) -> Optional[dict]:
    """(rows, vintage) for one vendored seed CSV, cached by mtime. The
    vintage is the newest date the first data row discloses (the seeds
    carry their CMS release date in a source/effective column)."""
    key = str(path)
    try:
        mt = path.stat().st_mtime
    except OSError:
        return None
    cached = _SEED_CACHE.get(key)
    if cached and cached.get("_mtime") == mt:
        return cached
    rows = 0
    first = ""
    try:
        with path.open(encoding="utf-8", errors="replace") as fh:
            fh.readline()  # header
            for line in fh:
                if rows == 0:
                    first = line
                rows += 1
    except OSError:
        return None
    dates = _ISO_DATE.findall(first)
    vintage = max(dates) if dates else ""
    if not vintage:
        years = _YEAR.findall(first)
        vintage = max(years) if years else ""
    info = {"_mtime": mt, "rows": rows, "vintage": vintage}
    _SEED_CACHE[key] = info
    return info


def connector_status() -> List[dict]:
    """Per-source data status, machine-readable and strictly offline.

    One entry per data source the cleaner can act on: reference packs,
    vendored v49 seeds, and the opt-in live connectors. Each carries
    ``status`` (LIVE-PACK / DEGRADED / UNAVAILABLE), a ``vintage`` date
    when one is known, ``rows`` on disk, what the source ``powers``, and
    a plain-language ``note``. A source with no data says so — it is
    never presented as quietly working."""
    out: List[dict] = []

    # --- Reference packs (refdata_packs) ---
    packs = _pack_status_map()
    for pid in ("taxonomy", "icd10cm", "hcpcs", "leie", "zip_cbsa"):
        info = packs.get(pid) or {}
        entry = {
            "id": f"pack_{pid}",
            "name": str(info.get("title") or f"{pid} reference pack"),
            "kind": "pack",
            "powers": str(info.get("enables") or ""),
            "rows": int(info.get("rows") or 0),
            "vintage": str(info.get("fetched_iso") or ""),
        }
        if pid == "leie":
            # screen_leie reads RCM_MC_LEIE_CSV FIRST (it beats the pack),
            # so when that file exists the honest status is live-via-file —
            # reporting "Not installed — its checks stay off" here while
            # plan() said "ready" and the screen actually ran was a direct
            # self-contradiction on a compliance surface.
            _env = os.environ.get("RCM_MC_LEIE_CSV") or ""
            try:
                _env_ok = bool(_env) and Path(_env).exists()
            except OSError:
                _env_ok = False
            if _env_ok:
                entry.update(
                    status=STATUS_LIVE,
                    note=(f"Active via RCM_MC_LEIE_CSV ({Path(_env).name})"
                          " — the screen reads this file (it takes "
                          "precedence over the reference pack); freshness "
                          "follows the file."))
                out.append(entry)
                continue
        if not info:
            entry.update(status=STATUS_UNAVAILABLE,
                         note="Reference-pack store unavailable.")
        elif not info.get("installed"):
            hint = ("Pull it from Reference data packs"
                    + (", install from a downloaded file, or bootstrap "
                       "offline from the vendored v49 validity table"
                       if pid == "icd10cm" else
                       " or install from a downloaded file")
                    + (" (or set RCM_MC_LEIE_CSV)" if pid == "leie" else "")
                    + ".")
            entry.update(status=STATUS_UNAVAILABLE,
                         note="Not installed — its checks stay off. " + hint)
        elif info.get("stale"):
            entry.update(
                status=STATUS_DEGRADED,
                note=(f"Installed but {info.get('age_days', 0):.0f} days old"
                      f" — past its ~{int(info.get('cadence_days') or 0)}d"
                      " refresh cadence; re-pull for a current set."))
        else:
            entry.update(status=STATUS_LIVE,
                         note=f"Installed ({entry['rows']:,} rows).")
        out.append(entry)

    # --- Vendored v49 seeds ---
    ref = _vendored_ref_dir()
    for sid, fname, name, powers, full, universe in _VENDOR_SEEDS:
        entry = {"id": f"vendored_{sid}", "name": name, "kind": "vendored",
                 "powers": powers, "rows": 0, "vintage": ""}
        info = _seed_info(ref / fname) if ref else None
        if not info or not info.get("rows"):
            entry.update(status=STATUS_UNAVAILABLE,
                         note="Vendored seed not shipped in this build.")
        else:
            entry["rows"] = int(info["rows"])
            entry["vintage"] = str(info.get("vintage") or "")
            if full:
                entry.update(
                    status=STATUS_LIVE,
                    note=f"Vendored, {entry['rows']:,} rows"
                         + (f", vintage {entry['vintage']}"
                            if entry["vintage"] else "") + ".")
            else:
                entry.update(
                    status=STATUS_DEGRADED,
                    note=(f"Vendored {universe} ({entry['rows']:,} rows"
                          + (f", vintage {entry['vintage']}"
                             if entry["vintage"] else "")
                          + ") — a clean pass is a floor, not a clearance."))
        out.append(entry)

    # --- Live connectors (opt-in; nothing offline to stand on) ---
    _client_ok = available()
    try:
        from . import nppes_bridge as _nb
        _nppes_ok = _nb.available()
    except Exception:  # noqa: BLE001
        _nppes_ok = False
    for cid, name, powers in _NETWORK_SOURCES:
        if cid == "nppes":
            importable = _nppes_ok
        elif cid in ("cms_geo_service", "cms_by_provider"):
            # enrich.py talks to data.cms.gov with stdlib urllib — always
            # importable; reachability is only proven by an opt-in run.
            importable = True
        else:
            importable = _client_ok
        out.append({
            "id": cid, "name": name, "kind": "network",
            "powers": powers, "rows": 0, "vintage": "",
            "client_available": bool(importable),
            "status": STATUS_UNAVAILABLE,
            "note": ("Opt-in live connector — no vendored fallback; runs "
                     "only in online mode on a host with outbound access."
                     if importable else
                     "Client module unavailable in this deployment."),
        })
    return out


def health() -> Dict[str, object]:
    """Offline-safe connector-health rollup for panels and reports:
    ``connector_status()`` plus generated-at and per-status counts. No
    live probes — reachability is only ever proven by an actual opt-in
    run, so this reports evidence on disk, not guesses."""
    sources = connector_status()
    counts = {STATUS_LIVE: 0, STATUS_DEGRADED: 0, STATUS_UNAVAILABLE: 0}
    for s in sources:
        st = str(s.get("status") or "")
        if st in counts:
            counts[st] += 1
    return {
        "generated": datetime.now(timezone.utc).isoformat(
            timespec="seconds"),
        "counts": counts,
        "sources": sources,
    }
