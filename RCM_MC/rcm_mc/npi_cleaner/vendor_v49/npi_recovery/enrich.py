"""Enrichment layer — turns the cleaned claims into a self-contained dossier by
pulling every public source we can key on:

  • Provider_Directory : one deduped row per billing NPI (original-valid +
    recovered), with the full NPPES profile — entity type, credential, primary
    taxonomy/specialty, license, practice + mailing address, phone, authorized
    official, enumeration date, status. This is the "append a deep provider
    record" pattern the commercial NPI tools sell, built on the free registry.

  • Drug_Reference : one row per HCPCS on the file, cross-referenced across CMS —
    benefit track + channel (router), the national Medicare benchmark from the
    Physician-by-Geography dataset, and the Part-D footprint (by generic name).
    Makes the "we pulled from all the sources" claim literally true and visible.

Everything degrades gracefully: an NPI NPPES can't find still gets a row
(flagged not-found); a drug with no geography/Part-D hit still gets a row.
"""

import re

import pandas as pd

from concurrent.futures import ThreadPoolExecutor, as_completed

from . import config


def build_npi_index(npis, nppes, progress=None, max_workers=16):
    """Look up many NPIs in NPPES concurrently and return a compact index:
        {npi: {name, entity_type, specialty, taxonomy_code, affiliation, found}}
    Threaded because a large claims file can carry thousands of distinct
    providers; the on-disk cache is pickle-per-key, so concurrent lookups are
    safe and re-runs are instant. `affiliation` is the organization's own legal
    name for org NPIs (individuals have no public affiliation in NPPES)."""
    clean = []
    seen = set()
    for x in npis:
        s = str(x).strip()
        if config.npi_is_valid(s) and s not in seen:
            seen.add(s)
            clean.append(s)
    index = {}
    total = len(clean)
    if total == 0:
        return index

    def work(npi):
        r = nppes.lookup(npi) or {}
        ent = r.get("entity_type", "") or ""
        name = r.get("name", "") or ""
        return npi, {
            "name": name,
            "entity_type": ent,
            "specialty": r.get("taxonomy", "") or "",
            "taxonomy_code": r.get("taxonomy_code", "") or "",
            "all_taxonomies": r.get("all_taxonomies", "") or (r.get("taxonomy", "") or ""),
            "affiliation": (name if ent == "Organization" else ""),
            "found": bool(r),
        }

    done = 0
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(work, n) for n in clean]
        for fut in as_completed(futures):
            npi, rec = fut.result()
            index[npi] = rec
            done += 1
            if progress and (done % 50 == 0 or done == total):
                progress(f"Looking up providers ({done:,}/{total:,})", done / total)
    return index

# Map a messy claim drug-name string to a Part-D generic name for the footprint
# lookup. Starter list for common provider-administered biologics; extend freely.
GENERIC_HINTS = {
    "infliximab": "Infliximab", "ivig": "Immune globulin", "immune globulin": "Immune globulin",
    "ocrelizumab": "Ocrelizumab", "ocrevus": "Ocrelizumab", "natalizumab": "Natalizumab",
    "tysabri": "Natalizumab", "teprotumumab": "Teprotumumab", "tepezza": "Teprotumumab",
    "ustekinumab": "Ustekinumab", "stelara": "Ustekinumab", "vedolizumab": "Vedolizumab",
    "entyvio": "Vedolizumab", "rituximab": "Rituximab", "bevacizumab": "Bevacizumab",
    "eculizumab": "Eculizumab", "soliris": "Eculizumab", "ravulizumab": "Ravulizumab",
    "omalizumab": "Omalizumab", "xolair": "Omalizumab", "mepolizumab": "Mepolizumab",
    "benralizumab": "Benralizumab", "golimumab": "Golimumab", "certolizumab": "Certolizumab",
}


def _generic_for(name, desc=""):
    blob = f"{name or ''} {desc or ''}".lower()
    for key, generic in GENERIC_HINTS.items():
        if key in blob:
            return generic
    return ""


def build_provider_directory(npis, nppes, progress=None, cms=None, max_workers=16):
    """One deduped, fully-enriched row per distinct NPI. When a CMS client is
    given, each NPI is also cross-checked against the Medicare FFS Public Provider
    Enrollment file (PECOS) — so the directory shows both what NPPES self-reports
    and whether the provider is actually Medicare-enrolled (and its PECOS type).

    The per-NPI work (NPPES + PECOS enrollment + opt-out) is independent across
    providers, so it runs concurrently; results are sorted by NPI at the end, so
    the output is identical to the serial version — only faster."""
    uniq = sorted({str(n).strip() for n in npis if str(n).strip() and str(n).strip().lower() != "nan"})
    total = max(len(uniq), 1)

    def worker(npi):
        r = nppes.lookup(npi)
        enr = cms.enrollment_lookup(npi) if cms is not None else {}
        oo = cms.opt_out_lookup(npi) if cms is not None else {}
        enrolled = bool(enr.get("enrolled"))
        opted_out = bool(oo.get("opted_out"))
        if r:
            crosscheck = "NPPES + PECOS" if enrolled else "NPPES only"
            return {
                "NPI": npi, "Found_In_NPPES": True,
                "Entity_Type": r.get("entity_type", ""), "Provider_Name": r.get("name", ""),
                "Credential": r.get("credential", ""), "Primary_Specialty": r.get("taxonomy", ""),
                "Taxonomy_Code": r.get("taxonomy_code", ""), "License": r.get("license", ""),
                "License_State": r.get("license_state", ""), "Practice_Address": r.get("addr_line", ""),
                "Practice_City": r.get("city", ""), "Practice_State": r.get("state", ""),
                "Practice_ZIP": r.get("postal", ""), "Phone": r.get("phone", ""),
                "Mailing_Address": r.get("mail_line", ""), "Authorized_Official": r.get("official", ""),
                "Enumeration_Date": r.get("enumeration_date", ""), "Last_Updated": r.get("last_updated", ""),
                "Status": r.get("status", ""), "Medicare_Enrolled": enrolled,
                "PECOS_Provider_Type": enr.get("provider_type", ""), "PECOS_Org_Name": enr.get("org_name", ""),
                "PECOS_Enroll_State": enr.get("enrollment_state", ""), "Opted_Out_Medicare": opted_out,
                "OptOut_Effective": oo.get("optout_effective", ""), "Identity_Crosscheck": crosscheck,
            }
        crosscheck = "PECOS only" if enrolled else "not found"
        return {"NPI": npi, "Found_In_NPPES": False, "Entity_Type": "",
                "Provider_Name": (enr.get("org_name") or "(not found in NPPES)"), "Credential": "",
                "Primary_Specialty": "", "Taxonomy_Code": "", "License": "",
                "License_State": "", "Practice_Address": "", "Practice_City": "",
                "Practice_State": "", "Practice_ZIP": "", "Phone": "",
                "Mailing_Address": "", "Authorized_Official": "",
                "Enumeration_Date": "", "Last_Updated": "", "Status": "",
                "Medicare_Enrolled": enrolled, "PECOS_Provider_Type": enr.get("provider_type", ""),
                "PECOS_Org_Name": enr.get("org_name", ""), "PECOS_Enroll_State": enr.get("enrollment_state", ""),
                "Opted_Out_Medicare": opted_out, "OptOut_Effective": oo.get("optout_effective", ""),
                "Identity_Crosscheck": crosscheck}

    rows, done = [], 0
    if uniq:
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = [ex.submit(worker, n) for n in uniq]
            for fut in as_completed(futures):
                rows.append(fut.result())
                done += 1
                if progress and (done % 25 == 0 or done == total):
                    progress(f"Enriching providers ({done:,}/{total:,})", done / total)
    cols = ["NPI", "Found_In_NPPES", "Entity_Type", "Provider_Name", "Credential",
            "Primary_Specialty", "Taxonomy_Code", "License", "License_State",
            "Practice_Address", "Practice_City", "Practice_State", "Practice_ZIP",
            "Phone", "Mailing_Address", "Authorized_Official", "Enumeration_Date",
            "Last_Updated", "Status", "Medicare_Enrolled", "PECOS_Provider_Type",
            "PECOS_Org_Name", "PECOS_Enroll_State", "Opted_Out_Medicare",
            "OptOut_Effective", "Identity_Crosscheck"]
    df = pd.DataFrame(rows, columns=cols)
    if not df.empty:
        df = df.sort_values("NPI").reset_index(drop=True)
    return df


def apply_bulk_enrichment(directory, cache_dir=None, session=None, progress=None):
    """v7 vectorized-join layer: enrich the provider directory from bulk LOCAL
    tables — one merge each instead of per-NPI calls. Adds deactivation status
    (CMS Deactivated-NPI file) and a human specialty grouping (NUCC taxonomy,
    joined on the bare taxonomy code NPPES already returned). Fail-soft: a table
    that can't load leaves its columns blank and the live path is unaffected.

    This is the v7 inversion in miniature — the same engine that swaps per-row
    NPPES/PECOS for a bulk join in production, demonstrated here on two small,
    real bulk files. Returns (directory, info) with per-table coverage."""
    from . import bulk
    info = {}
    if directory is None or directory.empty:
        return directory, info
    out = directory.copy()
    if progress:
        progress("Bulk join: deactivation + taxonomy", 0.0)

    # Deactivated-NPI: a deactivated billing NPI dates an operator's exit, so
    # cohort attrition is not misread as share loss in concentration work.
    deact = bulk.get_table("deactivated_npi", cache_dir=cache_dir)
    merged, miss = bulk.vectorized_fill(out, deact, left_key="NPI",
                                        fields=["deactivation_date", "npi_deactivated"], session=session)
    if "npi_deactivated" in merged.columns:
        out["Deactivated"] = merged["npi_deactivated"].fillna(False).astype(bool)
        out["Deactivation_Date"] = merged["deactivation_date"].fillna("")
        info["deactivated_npi"] = {"rows_flagged": int(out["Deactivated"].sum()),
                                   "coverage_pct": round(100 * (1 - float(miss.mean())), 1)}
    else:
        out["Deactivated"] = False
        out["Deactivation_Date"] = ""

    # NUCC taxonomy: turn the taxonomy code into a readable specialty grouping.
    nucc = bulk.get_table("nucc_taxonomy", cache_dir=cache_dir)
    merged2, miss2 = bulk.vectorized_fill(out, nucc, left_key="Taxonomy_Code",
                                          fields=["taxonomy_classification", "taxonomy_grouping"], session=session)
    if "taxonomy_classification" in merged2.columns:
        out["Specialty_Group"] = merged2["taxonomy_grouping"].fillna("")
        out["Specialty_Class"] = merged2["taxonomy_classification"].fillna("")
        info["nucc_taxonomy"] = {"coverage_pct": round(100 * (1 - float(miss2.mean())), 1)}
    else:
        out["Specialty_Group"] = ""
        out["Specialty_Class"] = ""

    return out, info


def apply_ndc_enrichment(std, cache_dir=None, session=None):
    """v8 NDC drug-identity layer. When the claims carry an NDC, vectorized-join
    against the FDA NDC Directory to (a) FILL a blank drug name from the labeled
    product, and (b) FLAG rows where the present drug name disagrees with the NDC
    (a miscoding signal). It never overwrites a drug name that's already there —
    a present value is left as-is and only flagged — so this is pure upside.
    Returns (std, info). No-op if there's no ndc column. Activates NOC routing
    downstream because the filled generic name feeds the brand/SAD matcher."""
    from . import bulk
    info = {}
    if std is None or std.empty or "ndc" not in std.columns or std["ndc"].isna().all():
        return std, info
    fda = bulk.get_table("fda_ndc", cache_dir=cache_dir)
    out = std.copy()
    out["_ndc9"] = out["ndc"].map(bulk.normalize_ndc9)
    merged, miss = bulk.vectorized_fill(out, fda, left_key="_ndc9",
                                        fields=["ndc_generic_name", "ndc_route"], session=session)
    gen = merged.get("ndc_generic_name")
    if gen is None:
        return std, info
    gen = gen.fillna("").astype(str).str.strip()
    have_ndc_name = gen.str.len() > 0
    dn = out["drug_name"].astype("string") if "drug_name" in out.columns else pd.Series(pd.NA, index=out.index, dtype="string")
    blank_dn = dn.isna() | (dn.astype(str).str.strip() == "")

    # (a) fill blank drug names from the NDC product
    fill_mask = (blank_dn & have_ndc_name).values
    if "drug_name" not in out.columns:
        out["drug_name"] = pd.NA
    out.loc[fill_mask, "drug_name"] = gen[fill_mask].str.upper().values

    # (b) flag drug_name <-> NDC mismatch on rows that HAD a name (token overlap)
    def _toks(s):
        return {t for t in re.split(r"[^a-z]+", str(s).lower()) if len(t) >= 5}
    present = (~blank_dn) & have_ndc_name
    mismatch = pd.Series(False, index=out.index)
    if present.any():
        for i in out.index[present.values]:
            a, b = _toks(dn.get(i, "")), _toks(gen.get(i, ""))
            if a and b and not (a & b):
                mismatch.at[i] = True
    out["ndc_drug_mismatch"] = mismatch.values
    out = out.drop(columns=[c for c in ["_ndc9"] if c in out.columns])
    info = {"rows_with_ndc": int(out["ndc"].notna().sum()),
            "drug_name_filled_from_ndc": int(fill_mask.sum()),
            "ndc_drug_mismatch_flagged": int(mismatch.sum()),
            "ndc_coverage_pct": round(100 * (1 - float(miss.mean())), 1)}
    return out, info


def build_drug_reference(std, route_map, cms, code_desc=None, progress=None,
                         top_n=40, do_partd=True, asp=None):
    """One cross-referenced row per HCPCS on the file."""
    if "hcpcs" not in std:
        return pd.DataFrame()
    code_desc = code_desc or {}
    benefit_of = dict(zip(route_map["hcpcs"].astype(str), route_map["benefit"]))
    channel_of = dict(zip(route_map["hcpcs"].astype(str), route_map["channel"]))

    # rank codes by dollars on the file so we spend pulls where they matter
    vol = (std.assign(_amt=std["allowed_amt"].fillna(0))
           .groupby("hcpcs")["_amt"].agg(["sum", "size"]).sort_values("sum", ascending=False))
    codes = [str(c) for c in vol.index if str(c).strip() and str(c).lower() != "nan"][:top_n]

    name_of = {}
    if "drug_name" in std:
        for c in codes:
            nm = std.loc[std["hcpcs"].astype(str) == c, "drug_name"].dropna()
            name_of[c] = (nm.iloc[0] if len(nm) else "")

    rows, total = [], max(len(codes), 1)
    for i, code in enumerate(codes):
        if progress:
            progress(f"Drug ref {code}", (i + 1) / total)
        benefit = benefit_of.get(code, "part_b")
        desc = code_desc.get(code, "")
        bench = cms.geography_benchmark(code)
        generic = _generic_for(name_of.get(code, ""), bench.get("desc") or desc)
        partd = cms.partd_presence(generic) if (do_partd and benefit in ("sad", "noc")) else {}
        asp_rec = asp.record(code) if asp is not None else None

        rows.append({
            "HCPCS": code,
            "Drug_Name": name_of.get(code, "") or (bench.get("desc") or desc),
            "CMS_Description": bench.get("desc") or desc,
            "Benefit_Track": {"part_b": "Part B (billable)", "sad": "Self-administered (Part D)",
                              "noc": "Unclassified (NOC)"}.get(benefit, benefit),
            "Channel": channel_of.get(code, "physician"),
            "Rows_In_File": int(vol.loc[code, "size"]) if code in vol.index else 0,
            "Dollars_In_File": float(vol.loc[code, "sum"]) if code in vol.index else 0.0,
            "Medicare_ASP_Limit_Per_Unit": (asp_rec or {}).get("payment_limit"),
            "ASP_Dosage_Unit": (asp_rec or {}).get("dosage", ""),
            "Natl_Medicare_Providers": bench.get("natl_providers"),
            "Natl_Medicare_Benes": bench.get("natl_benes"),
            "Avg_Allowed_Per_Unit": bench.get("avg_allowed_unit"),
            "PartD_Generic_Checked": partd.get("generic", ""),
            "PartD_Prescriber_Rows": partd.get("partd_rows"),
            "PartD_Total_Claims": partd.get("partd_claims"),
        })
    return pd.DataFrame(rows)


def build_verified_connectors(std, mapping, rxnorm=None, affil=None, hospital=None,
                              npi_index=None, max_drugs=500, max_npis=4000,
                              max_workers=8, progress=None):
    """Authoritative direct-lookup enrichment for the VERIFIED build.

    Returns (drug_ident, affil_map, owner_map).

    Speed: all lookups run concurrently (I/O-bound), each distinct CCN is
    resolved exactly once, and — because the CMS Facility Affiliation file is
    keyed on individual clinicians — NPIs that NPPES says are Organizations are
    skipped for affiliation (they're never in that file), which removes the bulk
    of wasted calls on a real claims book. The on-disk cache is pickle-per-key,
    so concurrent access is safe and re-runs are instant."""
    from concurrent.futures import ThreadPoolExecutor
    from .clients import summarize_affiliations
    progress = progress or (lambda m, f: None)
    npi_index = npi_index or {}
    drug_ident, affil_map, owner_map = {}, {}, {}

    def pmap(fn, items, label, lo, hi):
        """Run fn over items concurrently, reporting a moving fraction lo..hi."""
        items = list(items)
        out = {}
        if not items:
            return out
        done = 0
        step = max(1, len(items) // 20)
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futs = {ex.submit(fn, it): it for it in items}
            for fu in futs:
                pass
            from concurrent.futures import as_completed
            for fu in as_completed(futs):
                it = futs[fu]
                try:
                    out[it] = fu.result()
                except Exception:
                    out[it] = None
                done += 1
                if done % step == 0 or done == len(items):
                    progress(f"{label} ({done:,}/{len(items):,})", lo + (hi - lo) * done / len(items))
        return out

    # ---- drug identity (RxNorm): distinct NDCs + names, in parallel ----------
    if rxnorm is not None:
        ndc_keys = []
        if "ndc" in std.columns:
            ndcs = (std["ndc"].dropna().astype(str).map(
                lambda x: "".join(ch for ch in x if ch.isdigit())).loc[lambda s: s.str.len() >= 9])
            ndc_keys = list(dict.fromkeys(ndcs.tolist()))[:max_drugs]
        ndc_recs = pmap(rxnorm.lookup_ndc, ndc_keys, "Drug identity (NDC)", 0.90, 0.915)
        for n, rec in ndc_recs.items():
            if rec:
                drug_ident[("ndc", n[:9] if len(n) >= 11 else n)] = rec
                drug_ident[("ndc", n)] = rec
        dn_col = "drug_name" if "drug_name" in std.columns else mapping.get("drug_name")
        name_keys = []
        if dn_col and dn_col in std.columns:
            names = std[dn_col].dropna().astype(str).str.strip()
            names = names[names.str.len() >= 3]
            name_keys = list(dict.fromkeys(names.tolist()))[:max_drugs]
        name_recs = pmap(rxnorm.lookup_name, name_keys, "Drug identity (name)", 0.915, 0.93)
        for nm, rec in name_recs.items():
            if rec and ("name", nm.lower()) not in drug_ident:
                drug_ident[("name", nm.lower())] = rec

    # ---- facility affiliation: parallel, individuals only --------------------
    if affil is not None:
        raw_npis = []
        for c in ("billing_npi", "referring_npi"):
            col = c if c in std.columns else mapping.get(c)
            if col and col in std.columns:
                raw_npis += std[col].dropna().astype(str).tolist()
        cand = []
        seen = set()
        for n in raw_npis:
            n = "".join(ch for ch in str(n) if ch.isdigit())
            if not config.npi_is_valid(n) or n in seen:
                continue
            seen.add(n)
            # the affiliation file is clinician-keyed; skip known Organizations.
            ent = (npi_index.get(n, {}) or {}).get("entity_type", "")
            if ent == "Organization":
                continue
            cand.append(n)
        cand = cand[:max_npis]
        npi_rows = pmap(affil.affiliations, cand, "Facility affiliation", 0.93, 0.965)

        # resolve every distinct CCN once, in parallel
        ccns = []
        cseen = set()
        for rows in npi_rows.values():
            for r in (rows or []):
                ccn = (r.get("ccn") or "").strip()
                if ccn and ccn not in cseen:
                    cseen.add(ccn)
                    ccns.append(ccn)
        ccn_map = {}
        if hospital is not None and ccns:
            ccn_map = pmap(hospital.hospital, ccns, "Resolving facilities", 0.965, 0.985)

        # assemble summaries — no network here
        for n, rows in npi_rows.items():
            label, owners = summarize_affiliations(rows, ccn_map=ccn_map)
            if label:
                affil_map[n] = label
            if owners:
                owner_map[n] = owners
        progress("Connectors resolved", 0.99)

    return drug_ident, affil_map, owner_map
