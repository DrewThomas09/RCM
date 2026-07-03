"""Fill missing cells in the ORIGINAL claims file from public data, deduplicate
the rows, and mark genuinely-unfillable cells "N/A" — producing the "filled"
deliverable alongside the analysis report.

v6 confidence rewrite — the headline change:
  The billing-NPI column is the field with the gaps, and not every recovery is
  equally trustworthy. A point-attributed recovery (referral-anchored, tiers
  T1-T3) is a near-certain biller; a distributional recovery (drug/ZIP or
  CMS-pool share, tiers T4-T6) is a 20-40%-accurate guess. v5 wrote BOTH into
  the real billing-NPI column, so a guess looked identical to a verified biller
  — and names / specialty / affiliation were then derived off those guesses.

  v6 keeps the channel honest:
    • Only point-attributed (or original-present) NPIs land in the real billing
      column. Distributional recoveries go to a separate _NPI_BestGuess column
      (top-3 candidates); the main column is N/A for those rows.
    • name / entity_type / specialty / affiliation are derived ONLY from trusted
      NPIs (original-present or point-recovered) — never from a guess.
    • _NPI_Confidence grades every billing cell (original / high [Tn] /
      low-guess [Tn] / not-attributed [reason]).
    • _Benefit_Channel says, per row, why a cell is what it is (Part B medical
      biller / Part B DME-home / Part D self-administered / unclassified code).
    • Fill_Summary's headline is dollar-weighted and split three ways
      (high-confidence vs low-confidence-guess vs not-attributed) instead of one
      blended "% reduction" that hid the guesses.

v4 trust upgrades (retained):
  • Convention matching — a filled ENTITY_TYPE / specialty matches the column's
    own style (1/2, I/O, NPI-1/NPI-2, code-vs-description).
  • Per-row provenance — _Cells_Filled (which columns were filled) and
    _NPI_Source (original / recovered / best-guess / missing).
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

from . import config

NA = "N/A"

_BILLING_GENERIC = {"billing_name": "name", "billing_affiliation": "affiliation"}
_REFERRING_GENERIC = {"referring_name": "name", "referring_affiliation": "affiliation"}
_NO_SOURCE = {"payer": "no public per-claim source for payer name"}

# --------------------------------------------------------------------------- #
# v21: complete labeling. Every DATA cell ends non-blank — an observed value, a
# recovered value, or a SPECIFIC self-documenting token explaining why no value
# is observable. Nothing is fabricated. The token IS the confidence/honesty tag;
# Token_Legend in the report maps each one to its meaning and confidence band.
# --------------------------------------------------------------------------- #
NAP = "\u2014"  # em-dash: audit (_-prefixed) cell that is not applicable to the row

# token vocabulary -> documented in report.Token_Legend
TOK = {
    "payer":            "UNRECOVERABLE_PAYER_ERISA",        # no public per-claim payer; self-funded ERISA out of reach
    "sad":              "PHARMACY_BENEFIT_NO_MEDICAL_NPI",  # Part-D self-administered; biller is a pharmacy, no medical NPI
    "bestguess":        "BESTGUESS_BELOW_BAR",              # ranked candidates exist in _NPI_BestGuess, none above the accuracy bar
    "nocand":           "NO_CANDIDATE_IN_PUBLIC_DATA",      # no plausible biller found in public data
    "unclass":          "UNCLASSIFIED_HCPCS_CODE",          # J3490/J3590-type code; drug/biller indeterminate
    "bill_notrust":     "NO_TRUSTED_BILLING_NPI",           # identity field can't derive off a guessed/absent NPI
    "npi_nonppes":      "NPI_NOT_IN_NPPES",                 # the row's NPI is real but absent from NPPES
    "ref_missing":      "NO_REFERRING_NPI_ON_CLAIM",        # source claim carried no referring NPI
    "verif_bill":       "NOT_POINT_ATTRIBUTABLE",           # verified mode: blank billing left unrecovered by design
    "src_missing":      "DATA_MISSING_IN_SOURCE",           # safety net: blank in a source column the tool doesn't fill
}

_SRC_TRUSTED_PREFIX = ("original", "recovered", "inferred")
_NPI10 = re.compile(r"^\d{10}$")


def _looks_real_npi(series):
    s = series.astype("string").str.strip().str.replace(r"\.0$", "", regex=True)
    return s.fillna("").str.match(_NPI10)


def relabel_unrecoverable(filled, mapping, verified=False):
    """Swap the generic N/A for specific reason tokens so NO data cell is blank,
    and normalize audit-column blanks to an em-dash. Runs AFTER all accounting so
    the Fill_Summary / Could_Not_Fill counts are unchanged — only the displayed
    token changes. Returns the same frame, mutated in place.
    """
    if filled is None or filled.empty:
        return filled
    col_of = {canon: mapping.get(canon) for canon in mapping}

    src = (filled["_NPI_Source"].astype("string").str.strip().str.lower()
           if "_NPI_Source" in filled.columns else pd.Series("", index=filled.index))
    chan = (filled["_Benefit_Channel"].astype("string").str.strip().str.lower()
            if "_Benefit_Channel" in filled.columns else pd.Series("", index=filled.index))
    bestg = (filled["_NPI_BestGuess"].astype("string").str.strip()
             if "_NPI_BestGuess" in filled.columns else pd.Series("", index=filled.index))
    trusted_npi = src.fillna("").str.startswith(_SRC_TRUSTED_PREFIX)

    def _set(col, mask, value):
        if col and col in filled.columns and mask.any():
            filled.loc[mask, col] = value

    # ---- PAYER: structural floor ----------------------------------------
    pcol = col_of.get("payer")
    if pcol and pcol in filled.columns:
        _set(pcol, _is_blank(filled[pcol]), TOK["payer"])

    # ---- BILLING NPI: per-row reason ------------------------------------
    bcol = col_of.get("billing_npi")
    if bcol and bcol in filled.columns:
        blank = _is_blank(filled[bcol])
        if verified:
            _set(bcol, blank, TOK["verif_bill"])
        else:
            is_sad = chan.fillna("").str.contains("part d")
            is_unclass = chan.fillna("").str.contains("unclassified")
            has_guess = bestg.fillna("").str.len() > 0
            _set(bcol, blank & is_sad, TOK["sad"])
            _set(bcol, blank & ~is_sad & has_guess, TOK["bestguess"])
            _set(bcol, blank & ~is_sad & ~has_guess & is_unclass, TOK["unclass"])
            _set(bcol, blank & ~is_sad & ~has_guess & ~is_unclass, TOK["nocand"])

    # ---- BILLING identity fields (name / entity / specialty / affil) ----
    for canon in ("billing_name", "billing_affiliation", "entity_type", "billing_specialty"):
        c = col_of.get(canon)
        if c and c in filled.columns:
            blank = _is_blank(filled[c])
            _set(c, blank & trusted_npi, TOK["npi_nonppes"])      # NPI real, NPPES had no value
            _set(c, blank & ~trusted_npi, TOK["bill_notrust"])    # no trusted NPI to derive from

    # ---- REFERRING NPI + identity fields --------------------------------
    rcol = col_of.get("referring_npi")
    ref_real = _looks_real_npi(filled[rcol]) if (rcol and rcol in filled.columns) else pd.Series(False, index=filled.index)
    if rcol and rcol in filled.columns:
        _set(rcol, _is_blank(filled[rcol]), TOK["ref_missing"])
    for canon in ("referring_name", "referring_affiliation", "referring_specialty"):
        c = col_of.get(canon)
        if c and c in filled.columns:
            blank = _is_blank(filled[c])
            _set(c, blank & ref_real, TOK["npi_nonppes"])
            _set(c, blank & ~ref_real, TOK["ref_missing"])

    # ---- zero-blank safety net on every remaining DATA column -----------
    audit = [c for c in filled.columns if str(c).startswith("_")]
    data_cols = [c for c in filled.columns if c not in audit]
    for c in data_cols:
        blank = _is_blank(filled[c])
        if blank.any():
            filled.loc[blank, c] = TOK["src_missing"]

    # ---- audit columns: blank -> em-dash (not-applicable), never empty --
    for c in audit:
        m = _is_blank(filled[c])
        if m.any():
            filled.loc[m, c] = NAP
    return filled


_NUCC = re.compile(r"^[0-9A-Za-z]{9}[Xx]$")  # NUCC taxonomy code, e.g. 207W00000X

# A billing NPI is trustworthy enough for the real column (and to derive
# names/specialty/affiliation from) only when it was present in the source and
# valid, point-attributed by the referral-anchored imputer, or inferred from
# agreeing sibling rows (cluster dominance / visit continuity). Inferred fills
# are labelled distinctly in _NPI_Confidence — they are in the column, but never
# presented as a verified lookup.
_TRUSTED_STATUS = {"original", "recovered_point",
                   "recovered_inferred_cluster", "recovered_inferred_continuity"}


def _is_blank(series):
    s = series.astype("string")
    stripped = s.str.strip()
    return s.isna() | stripped.str.lower().isin(config.BLANK_TOKENS)


def _existing_values(series):
    s = series.astype("string").str.strip()
    s = s[~s.isna()]
    s = s[~s.str.lower().isin(config.BLANK_TOKENS)]
    return s


def _entity_formatter(existing):
    """Map NPPES entity_type (Individual/Organization) to the column's style."""
    ev = _existing_values(existing)
    vals = ev.str.lower()
    sample = set(vals.unique()[:80].tolist())

    def for_code(ent):
        return "1" if ent == "Individual" else ("2" if ent == "Organization" else "")

    def for_letter(ent):
        return "I" if ent == "Individual" else ("O" if ent == "Organization" else "")

    if sample and sample <= {"1", "2", "1.0", "2.0"}:
        return for_code
    if sample and sample <= {"i", "o"}:
        return for_letter
    if sample and all(("npi-1" in s or "npi-2" in s or "npi 1" in s or "npi 2" in s)
                      for s in sample):
        return lambda ent: ("NPI-1" if ent == "Individual"
                            else ("NPI-2" if ent == "Organization" else ""))
    caser = (str.upper if (sample and next(iter(sample)).isupper()) else str.title)
    return lambda ent: (caser(ent) if ent in ("Individual", "Organization") else "")


def _specialty_uses_code(existing):
    vals = _existing_values(existing)
    if len(vals) == 0:
        return False
    return float(vals.str.match(_NUCC).mean()) >= 0.6


def _confidence_label(status, tier, reason, tier_acc=None, tier_std=None):
    """Per-row grade for the billing NPI cell. When a measured holdout accuracy
    is known for the row's tier, it grades the band (high vs medium) and is shown
    with its fold-to-fold spread, so 'high' is backed by a number, not asserted."""
    st = "" if status is None or pd.isna(status) else str(status)
    tr = "" if tier is None or pd.isna(tier) else str(tier)
    meas = ""
    acc = float(tier_acc[tr]) if (tier_acc and tr in tier_acc) else None
    if acc is not None:
        spread = ""
        if tier_std and tr in tier_std and float(tier_std[tr]) > 0:
            spread = f" \u00b1{round(100 * float(tier_std[tr]))}%"
        meas = f", {round(100 * acc)}% measured{spread}"
    if st == "original":
        return "original"
    if st == "recovered_point":
        # graduated band: at/above HIGH_CONF_ACC reads "high", else "medium"
        band = "high"
        if acc is not None and acc < config.HIGH_CONF_ACC:
            band = "medium"
        return f"{band} ({tr}{meas})" if tr else band
    if st == "recovered_inferred_continuity":
        return "inferred-continuity (same patient/drug/site within 90d)"
    if st == "recovered_inferred_cluster":
        return "inferred-cluster (dominant biller in referrer/drug/area group)"
    if st == "recovered_distributional":
        return f"low-guess ({tr}{meas})" if tr else "low-guess"
    if st == "not_attributed_partD":
        return "not-attributed (self-administered / Part D)"
    if st == "not_attributed_NOC":
        return "not-attributed (unclassified drug code)"
    if st == "not_attributed_no_partB":
        return "not-attributed (no Part B presence)"
    if st == "not_attributed_no_candidate":
        return "not-attributed (no candidate biller)"
    return st or ""


def fill_workbook(raw, std, cleaned, mapping, npi_index, route_map=None, tier_acc=None,
                  tier_std=None, deactivated_map=None, drug_ident=None, affil_map=None,
                  owner_map=None, parent_map=None, parent_size=None, paid_map=None,
                  mode="statistical", progress=None):
    """Return (filled_df, fill_summary_df, gaps_df).

    mode="statistical" (default): the full recovery stack — point-attributed,
    sibling-inferred, and (in _NPI_BestGuess) distributional billers, with
    calibrated confidence bands. mode="verified": ONLY values that come from a
    direct authoritative lookup — the billing NPI is kept only where it was
    present in the source (a blank one stays N/A, because no public dataset
    records who billed a given claim), and every other filled cell is a registry
    lookup (NPPES on an NPI already in the row, the CMS HCPCS descriptor, the FDA
    NDC Directory, etc.). Nothing is inferred or statistically estimated."""
    verified = (mode == "verified")
    progress = progress or (lambda m, f: None)
    filled = raw.copy().reset_index(drop=True)

    def _col(name):
        if name in cleaned:
            return cleaned[name].astype("string").reset_index(drop=True)
        return pd.Series(pd.NA, index=filled.index, dtype="string")

    final_bill = _col("Billing_NPI_Final")
    status = _col("Recovery_Status")
    tier = _col("Recovery_Tier")
    reason = _col("Recovery_Reason")
    top3 = _col("Recovery_Top3_NPIs")
    ref_npi = (std["referring_npi"] if "referring_npi" in std
               else pd.Series(pd.NA, index=raw.index)).astype("string").reset_index(drop=True)
    allowed = (pd.to_numeric(std["allowed_amt"], errors="coerce")
               if "allowed_amt" in std else pd.Series(0.0, index=raw.index)).fillna(0.0).reset_index(drop=True)

    # Trust gate: which billing NPIs land in the real column / derive names from.
    # statistical -> original + point + sibling-inferred; verified -> original only.
    trusted_status = {"original"} if verified else _TRUSTED_STATUS
    is_trusted = status.isin(trusted_status)
    trusted_npi = final_bill.where(is_trusted, other=pd.NA)
    is_distributional = status.eq("recovered_distributional")
    # best-guess is a statistical artifact; the verified output never shows one.
    best_guess = (pd.Series("", index=filled.index, dtype="object") if verified
                  else top3.where(is_distributional, other="").fillna(""))

    filled_flags = {}

    def lookup(npi_series, field):
        def g(x):
            if pd.isna(x):
                return ""
            return npi_index.get(str(x).strip(), {}).get(field, "") or ""
        return npi_series.map(g)

    def write_fill(col, blank, values, canonical):
        vals = values.where(values.astype(str).str.len() > 0, other=pd.NA)
        target_idx = blank[blank].index
        got = vals.notna()
        filled.loc[target_idx, col] = vals.values
        mask = pd.Series(False, index=filled.index)
        mask.loc[target_idx] = got.values
        prev = filled_flags.get(canonical)
        filled_flags[canonical] = mask if prev is None else (prev | mask)

    # 1) billing NPI — point-attributed (or original-valid) only -------------
    # Rows that need a billing fill = those the pipeline flagged blank/invalid.
    # For those rows we write the TRUSTED NPI (NA for distributional / not-
    # attributed, so the main column stays N/A and the guess goes to BestGuess).
    bill_col = mapping.get("billing_npi")
    if "is_blank_billing" in std:
        need_bill = std["is_blank_billing"].fillna(False).reset_index(drop=True)
    elif bill_col and bill_col in filled:
        need_bill = _is_blank(filled[bill_col])
    else:
        need_bill = pd.Series(False, index=filled.index)
    if bill_col and bill_col in filled.columns:
        tgt = need_bill[need_bill].index
        vals = trusted_npi.where(trusted_npi.astype(str).str.len() > 0, other=pd.NA)
        filled.loc[tgt, bill_col] = vals.loc[tgt].values
        bill_mask = pd.Series(False, index=filled.index)
        bill_mask.loc[tgt] = vals.loc[tgt].notna().values
        filled_flags["billing_npi"] = bill_mask

    # 2) repaired field values (state / hcpcs / drug name / pos) -------------
    for canon in ("state", "hcpcs", "drug_name", "pos"):
        col = mapping.get(canon)
        if col and col in filled.columns and canon in std.columns:
            rep = std[canon].astype("string").reset_index(drop=True)
            blank = _is_blank(filled[col])
            if blank.any():
                vals = rep[blank].where(rep[blank].notna(), filled.loc[blank, col])
                filled.loc[blank[blank].index, col] = vals.values

    # 3) generic NPPES fills (names, affiliation) — TRUSTED NPIs only --------
    def apply_generic(fill_map, key_series):
        for canon, field in fill_map.items():
            col = mapping.get(canon)
            if not col or col not in filled.columns:
                continue
            blank = _is_blank(filled[col])
            if blank.any():
                write_fill(col, blank, lookup(key_series[blank], field), canon)

    apply_generic(_BILLING_GENERIC, trusted_npi)   # was final_bill in v5
    apply_generic(_REFERRING_GENERIC, ref_npi)

    # 4) entity type — match the column's convention; TRUSTED NPIs only ------
    ecol = mapping.get("entity_type")
    if ecol and ecol in filled.columns:
        fmt = _entity_formatter(filled[ecol])
        blank = _is_blank(filled[ecol])
        if blank.any():
            ent = lookup(trusted_npi[blank], "entity_type").map(lambda e: fmt(e) if e else "")
            write_fill(ecol, blank, ent, "entity_type")

    # 5) specialties — code or description to match the column ---------------
    for canon, key_series in (("billing_specialty", trusted_npi),   # was final_bill
                              ("referring_specialty", ref_npi)):
        col = mapping.get(canon)
        if not col or col not in filled.columns:
            continue
        field = "taxonomy_code" if _specialty_uses_code(filled[col]) else "specialty"
        blank = _is_blank(filled[col])
        if blank.any():
            write_fill(col, blank, lookup(key_series[blank], field), canon)

    progress("Fills applied", 0.6)

    # 6) confidence + best-guess + benefit-channel columns -------------------
    filled["_NPI_BestGuess"] = best_guess.values
    if verified:
        # verified output: the billing NPI is either as-provided or genuinely
        # unknowable from public data — no tiers, no measured accuracy.
        conf = ["verified \u2014 billing NPI as provided in source" if str(s) == "original"
                else "N/A \u2014 no public source records who billed this claim (see statistical output)"
                for s in status.tolist()]
    else:
        conf = [
            _confidence_label(s, t, r, tier_acc=tier_acc, tier_std=tier_std)
            for s, t, r in zip(status.tolist(), tier.tolist(), reason.tolist())
        ]
    filled["_NPI_Confidence"] = conf

    # v8: flag a final billing NPI deactivated AS OF the service date. For a
    # recovered biller this means the recovery is almost certainly wrong (that NPI
    # wasn't billing then); for an original it's a data anomaly. Flagged, not
    # excluded — CMS deactivations can later be reversed, so this is for review.
    deact_note = pd.Series("", index=filled.index, dtype="object")
    if deactivated_map:
        fb = final_bill.reset_index(drop=True)
        deact_date_raw = fb.map(lambda x: deactivated_map.get(str(x).strip(), "") if pd.notna(x) else "")
        dd = pd.to_datetime(deact_date_raw, errors="coerce")
        svc = (pd.to_datetime(std["date"], errors="coerce").reset_index(drop=True)
               if "date" in std.columns else pd.Series(pd.NaT, index=filled.index))
        # deactivated, and either we have no service date or it post-dates deactivation
        flagged = dd.notna() & (svc.isna() | (dd <= svc))
        deact_note = deact_date_raw.where(flagged, other="").fillna("")
        if flagged.any():
            # annotate the confidence cell for trusted (recovered/original) rows
            ann = filled["_NPI_Confidence"].astype(str)
            filled.loc[flagged.values, "_NPI_Confidence"] = (
                ann[flagged.values] + " [NPI deactivated " + deact_date_raw[flagged].astype(str) + " — review]")
    filled["_NPI_Deactivated"] = deact_note.values

    # per-row benefit channel from the route map (keyed on hcpcs + drug name)
    bchan = pd.Series("", index=filled.index, dtype="object")
    if route_map is not None and not route_map.empty and "hcpcs" in std:
        pair_benefit, pair_channel = {}, {}
        for _, rr in route_map.iterrows():
            k = (str(rr.get("hcpcs")), str(rr.get("drug_name", "")))
            pair_benefit[k] = rr.get("benefit", "part_b")
            pair_channel[k] = rr.get("channel", "physician")
        hc = std["hcpcs"].astype("string").reset_index(drop=True)
        dn = (std["drug_name"].astype("string") if "drug_name" in std
              else pd.Series("", index=std.index)).fillna("").reset_index(drop=True)
        labels = []
        for h, d in zip(hc.tolist(), dn.tolist()):
            k = (str(h), str(d))
            b = pair_benefit.get(k, pair_benefit.get((str(h), ""), "part_b"))
            c = pair_channel.get(k, pair_channel.get((str(h), ""), "physician"))
            labels.append(config.benefit_channel_label(b, c))
        bchan = pd.Series(labels, index=filled.index, dtype="object")
    filled["_Benefit_Channel"] = bchan.values

    # v11: authoritative direct-lookup enrichment — RxNorm drug identity (NDC or
    # drug name -> ingredient + ATC therapeutic class) and the CMS Facility
    # Affiliation file (NPI -> facility type + CCN). Pure registry lookups on
    # identifiers already in the row; present in BOTH the verified and the
    # statistical output. drug_name (if mapped) is filled authoritatively from
    # the RxNorm ingredient when blank.
    di = drug_ident or {}
    ndc_col = (std["ndc"].astype("string").reset_index(drop=True)
               if "ndc" in std.columns else pd.Series(pd.NA, index=filled.index, dtype="string"))
    dn_std = ((std["drug_name"].astype("string") if "drug_name" in std.columns
               else pd.Series(pd.NA, index=raw.index)).reset_index(drop=True))

    def _drug_rec(i):
        if di:
            n = ndc_col.iloc[i] if i < len(ndc_col) else pd.NA
            if pd.notna(n):
                digits = "".join(ch for ch in str(n) if ch.isdigit())
                rec = di.get(("ndc", digits))
                if rec is None and len(digits) >= 11:
                    rec = di.get(("ndc", digits[:9]))
                if rec:
                    return rec
            d = dn_std.iloc[i] if i < len(dn_std) else pd.NA
            if pd.notna(d):
                return di.get(("name", str(d).strip().lower()))
        return None

    recs = [_drug_rec(i) for i in range(len(filled))]
    ingr = [((r or {}).get("ingredient", "") or "") for r in recs]
    clss = [((r or {}).get("atc_class", "") or "") for r in recs]

    def _brand(r):
        # RxNorm SBD names look like "infliximab-dyyb 100 MG Injection [Inflectra]";
        # the brand sits in the trailing brackets. Free to surface — already fetched.
        nm = (r or {}).get("name", "") or ""
        if "[" in nm and "]" in nm:
            b = nm[nm.rfind("[") + 1:nm.rfind("]")].strip()
            return b if b else ""
        return ""
    brand = [_brand(r) for r in recs]
    filled["_Drug_Ingredient"] = ingr
    filled["_Drug_Brand"] = brand

    # v18: Open Payments — does the REFERRING physician have a financial
    # relationship with the maker of the drug on this claim? A free signal for
    # the referring gap and a real KOL/steering flag for diligence.
    if paid_map:
        def _digits2(x):
            return "".join(ch for ch in str(x) if ch.isdigit()) if pd.notna(x) else ""
        paid_flags = []
        for rn, bd in zip(ref_npi.tolist(), brand):
            s = paid_map.get(str(bd or "").lower())
            paid_flags.append("Y" if (s and _digits2(rn) in s) else "")
        filled["_Referring_PaidByDrugMaker"] = paid_flags
    filled["_Drug_Class"] = clss
    dncol = mapping.get("drug_name")
    if dncol and dncol in filled.columns:
        ing_s = pd.Series(ingr, index=filled.index, dtype="object")
        blankd = _is_blank(filled[dncol])
        if blankd.any():
            write_fill(dncol, blankd, ing_s[blankd], "drug_name")

    am = affil_map or {}

    def _affil(series):
        return series.map(lambda x: am.get("".join(ch for ch in str(x) if ch.isdigit()), "")
                          if pd.notna(x) else "")
    filled["_Billing_Facility_Affil"] = _affil(trusted_npi).values
    filled["_Referring_Facility_Affil"] = _affil(ref_npi).values

    # v12: hospital OWNERSHIP across a provider's affiliations (Proprietary /
    # Voluntary non-profit / Government) — a PE-relevant signal resolved from the
    # CCN via CMS Hospital General Information. Billing provider first, else
    # referring. And the provider's FULL specialty set from NPPES (all
    # taxonomies, not just the primary that drives routing).
    om = owner_map or {}

    def _digits(x):
        return "".join(ch for ch in str(x) if ch.isdigit()) if pd.notna(x) else ""
    own_vals = []
    for b, r in zip(trusted_npi.tolist(), ref_npi.tolist()):
        own_vals.append(om.get(_digits(b), "") or om.get(_digits(r), ""))
    filled["_Facility_Ownership"] = own_vals
    filled["_Billing_All_Specialties"] = lookup(trusted_npi, "all_taxonomies").values

    # v17: economic-owner roll-up. Many scattered NPIs across states belong to one
    # platform (shared address / shared org names / DBA threads). This labels the
    # billing provider's parent group WITHOUT touching the original NPI or name —
    # a separate analysis column so a consultant can group rows by true operator.
    pm = parent_map or {}
    psz = parent_size or {}

    def _parent(x):
        return pm.get(_digits(x), "") if pd.notna(x) else ""
    filled["_Billing_Parent_Group"] = trusted_npi.map(_parent).values
    filled["_Billing_Parent_NPI_Count"] = trusted_npi.map(
        lambda x: (psz.get(_digits(x), "") if pd.notna(x) else "")).values

    # 7) per-row provenance (_Cells_Filled) ---------------------------------
    prov = pd.Series("", index=filled.index, dtype="object")
    for canon, mask in filled_flags.items():
        col = mapping.get(canon, canon)
        add = pd.Series("", index=filled.index, dtype="object")
        add[mask.values] = col
        sep = np.where((prov.values != "") & (add.values != ""), "; ", "")
        prov = pd.Series(prov.values + sep + add.values, index=filled.index)
    filled["_Cells_Filled"] = prov.values

    # _NPI_Source: how the billing NPI cell was formed.
    is_inferred = status.isin(["recovered_inferred_cluster", "recovered_inferred_continuity"])
    if verified:
        src = np.where(status.eq("original").values, "original",
                       "missing (no authoritative source)")
    else:
        src = np.select(
            [status.eq("original").values,
             status.eq("recovered_point").values,
             is_inferred.values,
             is_distributional.values],
            ["original", "recovered", "inferred", "best-guess"],
            default="missing",
        )
    if not (bill_col and bill_col in raw.columns):
        src = np.array([""] * len(filled))
    filled["_NPI_Source"] = src

    # 8) deduplicate exact original rows ------------------------------------
    dup_mask = raw.reset_index(drop=True).duplicated(keep="first")
    n_dupes = int(dup_mask.sum())
    keep = ~dup_mask.values
    filled = filled.loc[keep].reset_index(drop=True)
    raw_dedup = raw.reset_index(drop=True).loc[keep].reset_index(drop=True)
    status_d = status.loc[keep].reset_index(drop=True)
    allowed_d = allowed.loc[keep].reset_index(drop=True)
    need_bill_d = need_bill.loc[keep].reset_index(drop=True)

    # 9) N/A the still-blank fillable cells; gaps + summary ------------------
    fillable = {}
    for canon in (list(_BILLING_GENERIC) + list(_REFERRING_GENERIC) +
                  ["entity_type", "billing_specialty", "referring_specialty",
                   "billing_npi"] + list(_NO_SOURCE)):
        col = mapping.get(canon)
        if col and col in filled.columns and col not in fillable.values():
            fillable[canon] = col

    gaps, summary = [], []
    for canon, col in fillable.items():
        blank = _is_blank(filled[col])
        n_blank = int(blank.sum())
        if canon == "billing_npi":
            reason_txt = ("no public dataset records who billed a given claim, so a "
                          "blank billing NPI is left N/A in the verified output; the "
                          "statistical output supplies a recovered estimate"
                          if verified else
                          "not point-attributable: distributional best-guess in "
                          "_NPI_BestGuess, self-administered (Part D), unclassified "
                          "code, or no candidate — see _NPI_Confidence")
        elif canon in _NO_SOURCE:
            reason_txt = _NO_SOURCE[canon]
        elif canon in _BILLING_GENERIC or canon in ("entity_type", "billing_specialty"):
            reason_txt = "billing NPI not trusted (distributional/unrecovered), or NPI not in NPPES"
        else:
            reason_txt = "referring NPI missing, or NPI not in NPPES"
        if n_blank:
            filled.loc[blank[blank].index, col] = NA
        gaps.append({"column": col, "field": canon, "cells_set_to_NA": n_blank, "reason": reason_txt})

        before = int(_is_blank(raw_dedup[col]).sum()) if col in raw_dedup else 0
        got = before - n_blank
        summary.append({"column": col, "missing_before": before, "filled": got,
                        "still_NA": n_blank,
                        "pct_reduction": round(100 * got / before, 1) if before else 0.0})

    fill_summary = (pd.DataFrame(summary).sort_values("missing_before", ascending=False)
                    if summary else pd.DataFrame())
    gaps_df = (pd.DataFrame(gaps).sort_values("cells_set_to_NA", ascending=False)
               if gaps else pd.DataFrame())

    # --- dollar-weighted billing-NPI confidence breakdown (the honest headline) ---
    # Computed over deduplicated rows. "blank" = rows that needed a billing fill.
    bd = pd.DataFrame({"status": status_d.fillna(""), "amt": allowed_d, "need": need_bill_d})
    need = bd[bd["need"]]
    orig_present = bd[~bd["need"]]

    def _agg(mask):
        sub = need[mask]
        return int(len(sub)), float(sub["amt"].sum())

    high_n, high_d = _agg(need["status"].eq("recovered_point"))
    inf_mask = need["status"].isin(["recovered_inferred_cluster", "recovered_inferred_continuity"])
    inf_n, inf_d = _agg(inf_mask)
    inf_cluster_n, inf_cluster_d = _agg(need["status"].eq("recovered_inferred_cluster"))
    inf_cont_n, inf_cont_d = _agg(need["status"].eq("recovered_inferred_continuity"))
    low_n, low_d = _agg(need["status"].eq("recovered_distributional"))
    na_reasons = ["not_attributed_partD", "not_attributed_NOC",
                  "not_attributed_no_partB", "not_attributed_no_candidate"]
    na_mask = need["status"].isin(na_reasons)
    na_n, na_d = _agg(na_mask)
    na_by_reason = {}
    for rr in na_reasons:
        sub = need[need["status"].eq(rr)]
        if len(sub):
            na_by_reason[rr] = {"rows": int(len(sub)), "dollars": round(float(sub["amt"].sum()), 2)}

    if verified:
        # nothing is recovered/inferred/guessed: every blank billing NPI is N/A
        # because no public source records the biller of a claim.
        high_n = inf_n = inf_cluster_n = inf_cont_n = low_n = 0
        high_d = inf_d = inf_cluster_d = inf_cont_d = low_d = 0.0
        na_n = int(len(need))
        na_d = float(need["amt"].sum())
        na_by_reason = ({"no_public_source_for_billing_npi":
                         {"rows": na_n, "dollars": round(na_d, 2)}} if na_n else {})

    blank_rows = int(len(need))
    blank_dollars = float(need["amt"].sum())

    total_before = int(sum(s["missing_before"] for s in summary)) if summary else 0
    total_filled = int(sum(s["filled"] for s in summary)) if summary else 0
    fill_summary.attrs["n_dupes_removed"] = n_dupes
    fill_summary.attrs["rows_out"] = len(filled)
    fill_summary.attrs["rows_in"] = len(raw)
    fill_summary.attrs["total_missing_before"] = total_before
    fill_summary.attrs["total_filled"] = total_filled
    fill_summary.attrs["overall_pct_reduction"] = (round(100 * total_filled / total_before, 1)
                                                   if total_before else 0.0)
    # billing-NPI specific, dollar-weighted
    fill_summary.attrs["bill_blank_rows"] = blank_rows
    fill_summary.attrs["bill_blank_dollars"] = round(blank_dollars, 2)
    fill_summary.attrs["bill_orig_present_rows"] = int(len(orig_present))
    fill_summary.attrs["bill_orig_present_dollars"] = round(float(orig_present["amt"].sum()), 2)
    fill_summary.attrs["bill_high_rows"] = high_n
    fill_summary.attrs["bill_high_dollars"] = round(high_d, 2)
    fill_summary.attrs["bill_inferred_rows"] = inf_n
    fill_summary.attrs["bill_inferred_dollars"] = round(inf_d, 2)
    fill_summary.attrs["bill_inferred_cluster_rows"] = inf_cluster_n
    fill_summary.attrs["bill_inferred_continuity_rows"] = inf_cont_n
    fill_summary.attrs["bill_lowguess_rows"] = low_n
    fill_summary.attrs["bill_lowguess_dollars"] = round(low_d, 2)
    fill_summary.attrs["bill_na_rows"] = na_n
    fill_summary.attrs["bill_na_dollars"] = round(na_d, 2)
    fill_summary.attrs["bill_na_by_reason"] = na_by_reason
    fill_summary.attrs["bill_high_pct_rows"] = round(100 * high_n / blank_rows, 1) if blank_rows else 0.0
    fill_summary.attrs["bill_high_pct_dollars"] = round(100 * high_d / blank_dollars, 1) if blank_dollars else 0.0
    fill_summary.attrs["bill_inferred_pct_dollars"] = round(100 * inf_d / blank_dollars, 1) if blank_dollars else 0.0
    fill_summary.attrs["bill_lowguess_pct_dollars"] = round(100 * low_d / blank_dollars, 1) if blank_dollars else 0.0
    fill_summary.attrs["bill_na_pct_dollars"] = round(100 * na_d / blank_dollars, 1) if blank_dollars else 0.0
    fill_summary.attrs["mode"] = "verified" if verified else "statistical"
    fill_summary.attrs["method_note"] = (
        "VERIFIED OUTPUT — every value here is a direct lookup from an authoritative "
        "source: provider name / specialty / entity type from NPPES (with the full "
        "specialty set in _Billing_All_Specialties) keyed on an NPI already in your row; "
        "facility affiliation from CMS, with the CCN resolved to a NAMED hospital and its "
        "ownership (Proprietary / Voluntary non-profit / Government) via CMS Hospital "
        "General Information in _Billing_Facility_Affil / _Referring_Facility_Affil / "
        "_Facility_Ownership; drug identity from RxNorm/NLM (NDC or drug name -> ingredient "
        "+ ATC class) in _Drug_Ingredient / _Drug_Class; drug name from the CMS HCPCS "
        "descriptor or FDA NDC Directory; deactivation from the CMS Deactivated-NPI file. "
        "Nothing is inferred. A blank BILLING NPI is left N/A because no public dataset "
        "records who billed a given claim — see the statistical output for a recovered estimate."
        if verified else
        "STATISTICAL OUTPUT — billing NPIs are recovered: 'high'/'medium' are point-attributed "
        "from referral patterns (with a k-fold-MEASURED hit-rate shown per row), 'inferred' are "
        "borrowed from agreeing sibling rows (cluster dominance / visit continuity), and "
        "distributional best-guesses sit in _NPI_BestGuess (never the billing column). Tiers "
        "whose measured holdout accuracy fell below the bar were demoted. See _NPI_Source and "
        "_NPI_Confidence on every row, and the Caveats tab of the analysis report.")
    # v21: complete labeling — guarantee zero blank data cells with specific,
    # self-documenting tokens (after all accounting, so counts are unchanged).
    filled = relabel_unrecoverable(filled, mapping, verified=verified)
    return filled, fill_summary, gaps_df
