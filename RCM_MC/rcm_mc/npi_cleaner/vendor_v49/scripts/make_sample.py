"""Synthetic messy-claims generator used by the self-test and as a demo input.

build() returns a DataFrame with the same column shape a real medical-claims
extract uses (ClaimNumber, ServiceDate, BillingProviderNPI, ReferringNPI,
ProcedureCode, DrugName, POS, PatientZip, ServiceState, AllowedAmt, Qty,
PlanName). It deliberately seeds *learnable* referral->biller patterns so the
imputer has something to recover, plus (when messy=True) the kinds of dirt a
real data team produces: sentinel "blank" tokens, invalid NPIs, float/scientific
NPI coercion, and leading apostrophes.

The drug menu includes the dual-channel molecules the router must get right:
an IV J-code whose brand name also appears on the SAD list (Entyvio J3380,
ustekinumab/Stelara IV J3358, Simponi Aria J1602) must stay Part B, while the
true subcutaneous self-administered codes (J3357) must route to Part D.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _check_digit(nine: str) -> str:
    """Luhn check digit for an NPI, using the 80840 card-issuer prefix."""
    payload = "80840" + nine
    total, alt = 0, True
    for ch in reversed(payload):
        d = int(ch)
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        alt = not alt
    return str((10 - (total % 10)) % 10)


def valid_npi(rng) -> str:
    """A random, Luhn-valid 10-digit NPI (first digit 1 or 2, per NPPES)."""
    first = rng.choice(["1", "2"])
    rest = "".join(str(int(d)) for d in rng.integers(0, 10, size=8))
    nine = first + rest
    return nine + _check_digit(nine)


# (HCPCS, drug name, channel, unit-price-ish, dual-channel note). "sad" rows are
# self-administered; "noc" rows are unclassified; the rest are Part B billable.
_MENU = [
    ("J1745", "INFLIXIMAB INJECTION", "part_b", 95.0, ""),
    ("J2350", "OCRELIZUMAB (OCREVUS)", "part_b", 78.8, ""),
    ("J1459", "IMMUNE GLOBULIN IVIG (PRIVIGEN)", "part_b", 64.85, ""),
    ("J1561", "IMMUNE GLOBULIN IVIG (GAMUNEX-C)", "part_b", 64.0, ""),
    ("J1568", "IMMUNE GLOBULIN IVIG (OCTAGAM)", "part_b", 63.0, ""),
    ("J3380", "VEDOLIZUMAB (ENTYVIO)", "part_b", 30.0, "dual_channel_iv"),     # brand also on SAD list
    ("J3358", "USTEKINUMAB INTRAVENOUS (STELARA)", "part_b", 32.0, "dual_channel_iv"),  # IV; brand SAD
    ("J1602", "GOLIMUMAB IV (SIMPONI ARIA)", "part_b", 28.0, "dual_channel_iv"),
    ("J3357", "USTEKINUMAB SUBCUTANEOUS (STELARA)", "sad", 1400.0, ""),         # true SAD
    ("J1551", "IMMUNE GLOBULIN SCIG (CUTAQUIG)", "dme", 60.0, ""),              # home/DME channel
    ("J3590", "UNCLASSIFIED BIOLOGIC (RISANKIZUMAB)", "noc", 120.0, ""),        # NOC, resolvable -> SAD-ish
    ("J3590", "UNCLASSIFIED BIOLOGIC (INFLIXIMAB BIOSIMILAR)", "noc", 90.0, ""),# NOC, Part-B-ish drug
]

# A spread of states with a representative ZIP3 each, for national=True.
_GEO = {
    "TX": ["75201", "77002", "78229", "77030", "78701"],
    "CA": ["90017", "94110", "92101", "95814"],
    "NY": ["10001", "10016", "11201"],
    "FL": ["33101", "33602", "32801"],
    "IL": ["60601", "60607"],
    "PA": ["19103", "15213"],
    "OH": ["44101", "43215"],
    "GA": ["30303", "30312"],
}

_PLANS = ["Aetna", "Anthem", "BCBS", "Centene", "Cigna", "Humana", "UnitedHealthcare"]

# Real NDC-11s (from the FDA NDC Directory) for some menu drugs, keyed by HCPCS.
# Only a subset of claims carry an NDC -- realistic -- so NDC enrichment fills a
# blank drug name where present and is a no-op elsewhere.
_HCPCS_NDC = {
    "J1745": "00069080901",   # infliximab-dyyb
    "J2350": "50242015001",   # ocrelizumab
    "J3380": "64764010701",   # vedolizumab
    "J3358": "00143916801",   # ustekinumab IV
    "J3357": "00143916801",   # ustekinumab SC
    "J1602": "57894007001",   # golimumab
}


def build(rows: int = 1200, seed: int = 7, national: bool = False,
          messy: bool = True) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    states = list(_GEO.keys()) if national else ["TX"]

    # A fixed roster of referring providers and, per (state, drug), a dominant
    # billing provider — this is the learnable signal the imputer recovers.
    referrers = [valid_npi(rng) for _ in range(max(12, rows // 40))]
    billers = {}
    for st in states:
        for code, *_ in _MENU:
            # 1-2 plausible billers per (state, code); first is dominant.
            billers[(st, code)] = [valid_npi(rng) for _ in range(rng.integers(1, 3))]

    # Most infusion volume is CHRONIC patients returning ~monthly for the same
    # drug at the same site, billed by their usual provider. That gives the
    # two-hop layers real signal: same-patient visit sequences (continuity) and
    # referrer/drug/area clusters dominated by one biller (cluster dominance).
    n_patients = max(rows // 4, 60)
    patients = []
    for _ in range(n_patients):
        st = rng.choice(states)
        code, drug, channel, unit, note = _MENU[rng.integers(0, len(_MENU))]
        pool = billers[(st, code)]
        patients.append(dict(
            st=st, code=code, drug=drug, unit=unit, ref=rng.choice(referrers),
            zip5=rng.choice(_GEO[st]), pool=pool, dom=pool[0],
            pos=rng.choice(["O", "F", "12", "11", "22"]),
            start=pd.Timestamp("2025-01-01") + pd.Timedelta(days=int(rng.integers(0, 150))),
            n_visits=int(rng.integers(1, 9))))

    recs, i = [], 0
    for pid, pt in enumerate(patients):
        dt = pt["start"]
        for _v in range(pt["n_visits"]):
            if i >= rows:
                break
            bill = pt["dom"] if rng.random() < 0.85 else rng.choice(pt["pool"])
            qty = int(rng.integers(1, 24))
            allowed = round(float(pt["unit"]) * qty * float(rng.uniform(0.85, 1.25)), 2)
            ndc = _HCPCS_NDC.get(pt["code"], "") if rng.random() < 0.45 else ""
            # pharmacy-sourced lines often carry an NDC but no drug name -> let the
            # NDC join fill it (realistic, and demonstrates the v8/v9 NDC layer)
            drug = pt["drug"]
            if ndc and rng.random() < 0.40:
                drug = ""
            recs.append({
                "ClaimNumber": f"CLM{i:06d}",
                "PatientID": f"PT{pid:05d}",
                "ServiceDate": dt,
                "BillingProviderNPI": bill,
                "ReferringNPI": pt["ref"],
                "ProcedureCode": pt["code"],
                "NDC": ndc,
                "DrugName": drug,
                "POS": pt["pos"],
                "PatientZip": pt["zip5"],
                "ServiceState": pt["st"],
                "AllowedAmt": allowed,
                "Qty": qty,
                "PlanName": rng.choice(_PLANS),
            })
            dt = dt + pd.Timedelta(days=int(rng.integers(21, 45)))  # ~monthly cadence
            i += 1
        if i >= rows:
            break
    df = pd.DataFrame(recs)

    # Knock out ~30% of billing NPIs -> the gaps the tool must recover. Bias the
    # blanking toward rows whose (referrer, code, zip) also appears with a NPI
    # present, so a meaningful share is point-recoverable.
    blank_idx = rng.choice(df.index, size=int(0.30 * len(df)), replace=False)
    df.loc[blank_idx, "BillingProviderNPI"] = ""

    if not messy:
        return df

    # -- inject the dirt a real extract carries -----------------------------
    # 1) sentinel blank tokens in the billing NPI (not just empty string)
    tok_idx = rng.choice(blank_idx, size=max(1, len(blank_idx) // 4), replace=False)
    for j, idx in enumerate(tok_idx):
        df.at[idx, "BillingProviderNPI"] = ["NULL", "N/A", "(blank)", "#N/A", "-"][j % 5]

    # 2) invalid NPIs (right length, bad check digit) -> must be caught + recovered
    present = df.index[df["BillingProviderNPI"].astype(str).str.fullmatch(r"\d{10}")]
    if len(present):
        bad_idx = rng.choice(present, size=max(1, len(present) // 25), replace=False)
        for idx in bad_idx:
            df.at[idx, "BillingProviderNPI"] = "1234567890"  # fails Luhn

    # 3) float / scientific-notation coercion + leading apostrophes on referring
    df["ReferringNPI"] = df["ReferringNPI"].astype(float)  # 2.0000e9 style
    appo_idx = rng.choice(df.index, size=len(df) // 10, replace=False)
    for idx in appo_idx:
        v = df.at[idx, "BillingProviderNPI"]
        if isinstance(v, str) and v.isdigit():
            df.at[idx, "BillingProviderNPI"] = "'" + v  # leading apostrophe

    # 4) a few sentinel tokens in state / drug to exercise field repair
    drop_state = rng.choice(df.index, size=len(df) // 30, replace=False)
    df.loc[drop_state, "ServiceState"] = ""  # recoverable from ZIP
    drop_drug = rng.choice(df.index, size=len(df) // 30, replace=False)
    df.loc[drop_drug, "DrugName"] = ""  # recoverable from HCPCS description

    # 5) HCPCS modifiers (JW/JZ wastage, JG/TB 340B) glued or separated onto the
    # code -> must be preserved in a side column, not silently stripped.
    mod_idx = rng.choice(df.index, size=max(4, len(df) // 25), replace=False)
    mods = ["JW", "JZ", "JG", "TB", "-JG", " TB", "JW"]
    for j, idx in enumerate(mod_idx):
        base = str(df.at[idx, "ProcedureCode"])
        df.at[idx, "ProcedureCode"] = base + mods[j % len(mods)]

    # 6) reversal / adjustment rows: negative allowed $ -> must be segregated,
    # never pooled into gross-up or HHI as if they were new volume.
    rev_idx = rng.choice(df.index, size=max(3, len(df) // 60), replace=False)
    for idx in rev_idx:
        df.at[idx, "AllowedAmt"] = -abs(float(df.at[idx, "AllowedAmt"]))

    return df


# --------------------------------------------------------------------------- #
# v29 helpers — exercise the dual-feed + site-reclassification paths
# --------------------------------------------------------------------------- #
# CPT/HCPCS administration ("nine") + home-infusion codes co-billed with J-codes.
_INCLINIC_ADMIN = ["96365", "96366", "96413", "96415", "96372", "96374"]
_HOME_ADMIN = ["99601", "99602", "S9494", "S9500", "G0068"]


def build_with_admin(rows: int = 1000, seed: int = 23, national: bool = True,
                     messy: bool = True, admin_frac: float = 0.55,
                     year_span=(2023, 2025)) -> pd.DataFrame:
    """A medical extract that ALSO carries the companion administration codes on
    a share of claims (what the readout asked the extract to be expanded to),
    spans multiple years, and seeds an Ocrevus (J2350) slug that bills POS office
    but is really AIC — the reattribution proof point. Same columns as build()."""
    rng = np.random.default_rng(seed)
    base = build(rows=rows, seed=seed, national=national, messy=messy)
    # spread service dates across the requested span (build() is single-year)
    y0, y1 = year_span
    spans = (pd.Timestamp(f"{y1}-12-15") - pd.Timestamp(f"{y0}-01-01")).days
    base["ServiceDate"] = [pd.Timestamp(f"{y0}-01-01") + pd.Timedelta(days=int(d))
                           for d in rng.integers(0, spans, size=len(base))]

    # companion admin/home rows: same ClaimNumber/Patient/Date/biller/site as a
    # sampled set of J-code rows, but the code is an administration code.
    real = base[base["BillingProviderNPI"].astype(str).str.fullmatch(r"\d{10}")]
    take = real.sample(frac=admin_frac, random_state=seed) if len(real) else real.iloc[:0]
    extra = []
    for _, r in take.iterrows():
        home_like = str(r["POS"]) in ("12", "32", "34")
        code = (rng.choice(_HOME_ADMIN) if home_like else rng.choice(_INCLINIC_ADMIN))
        extra.append({**r.to_dict(), "ProcedureCode": code, "NDC": "",
                      "DrugName": "", "AllowedAmt": round(float(rng.uniform(40, 320)), 2),
                      "Qty": int(rng.integers(1, 4))})
    admin_df = pd.DataFrame(extra)

    # Ocrevus mislabeled-office slug: a real AIC operator billing J2350 at POS 11
    # (office) with in-clinic admin companions -> should reattribute office->AIC.
    aic_npi = valid_npi(rng)
    ref = valid_npi(rng)
    oc = []
    for k in range(40):
        cn = f"OCR{k:05d}"
        zip5 = "77030"
        dt = pd.Timestamp(f"{y0}-01-01") + pd.Timedelta(days=int(rng.integers(0, spans)))
        qty = int(rng.integers(6, 18))
        oc.append({"ClaimNumber": cn, "PatientID": f"OCRP{k%12:04d}", "ServiceDate": dt,
                   "BillingProviderNPI": aic_npi, "ReferringNPI": float(ref),
                   "ProcedureCode": "J2350", "NDC": "50242015001",
                   "DrugName": "OCRELIZUMAB (OCREVUS)", "POS": "11", "PatientZip": zip5,
                   "ServiceState": "TX", "AllowedAmt": round(78.8 * qty, 2), "Qty": qty,
                   "PlanName": rng.choice(_PLANS)})
        oc.append({"ClaimNumber": cn, "PatientID": f"OCRP{k%12:04d}", "ServiceDate": dt,
                   "BillingProviderNPI": aic_npi, "ReferringNPI": float(ref),
                   "ProcedureCode": rng.choice(_INCLINIC_ADMIN), "NDC": "",
                   "DrugName": "", "POS": "11", "PatientZip": zip5, "ServiceState": "TX",
                   "AllowedAmt": round(float(rng.uniform(120, 300)), 2),
                   "Qty": 1, "PlanName": rng.choice(_PLANS)})
    out = pd.concat([base, admin_df, pd.DataFrame(oc)], ignore_index=True)
    return out


def build_pharmacy(rows: int = 500, seed: int = 41, national: bool = True,
                   year_span=(2023, 2025), shared_billers=None,
                   style: str = "jcode", cost_fee: bool = False) -> pd.DataFrame:
    """A separate PHARMACY (RX) benefit extract, growing year over year so adding
    it back lifts the medical-only trend. No referring NPI on the slim pull.
    shared_billers: optional NPIs so the same operator shows up in both feeds.

    style controls how the drug is identified, to mirror how RX really arrives:
      "jcode" — pre-mapped to a J-code (the optimistic case the readout assumed)
      "ndc"   — NDC-keyed, no J-code (the realistic raw pharmacy case; resolved live)
      "name"  — free-text drug name only, no J-code/NDC (offline-resolvable via seed)
    cost_fee: if True, emit IngredientCost + DispensingFee instead of a single
      AllowedAmt (the toolkit sums them) — the common pharmacy money layout.
    """
    rng = np.random.default_rng(seed)
    y0, y1 = year_span
    # (jcode, drug name, NDC, per-unit $) — NDCs are real product codes for the
    # live-resolution path; the name path resolves the same molecules offline.
    pharm_menu = [
        ("J3357", "USTEKINUMAB SUBCUTANEOUS (STELARA)", "57894006003", 1400.0),
        ("J1551", "IMMUNE GLOBULIN SCIG (CUTAQUIG)", "", 60.0),
        ("J1561", "IMMUNE GLOBULIN IVIG (GAMUNEX-C)", "13533080071", 64.0),
        ("J3380", "VEDOLIZUMAB (ENTYVIO)", "64764030020", 30.0),
        ("J2350", "OCRELIZUMAB (OCREVUS)", "50242015001", 78.8),
        ("",      "EFGARTIGIMOD SUBCUTANEOUS (VYVGART HYTRULO)", "", 1200.0),
        ("",      "DUPILUMAB (DUPIXENT)", "", 1800.0),
    ]
    billers = list(shared_billers) if shared_billers else [valid_npi(rng) for _ in range(6)]
    zips = [z for zz in _GEO.values() for z in zz] if national else _GEO["TX"]
    recs = []
    per_year = {y: int(rows * w) for y, w in zip(range(y0, y1 + 1),
                                                 np.linspace(0.7, 1.4, y1 - y0 + 1))}
    i = 0
    for y, ny in per_year.items():
        for _ in range(ny):
            code, drug, ndc, unit = pharm_menu[rng.integers(0, len(pharm_menu))]
            qty = int(rng.integers(1, 20))
            allowed = round(unit * qty * float(rng.uniform(0.85, 1.2)), 2)
            rec = {
                "ClaimNumber": f"RX{i:06d}", "PatientID": f"RXP{i%200:05d}",
                "ServiceDate": pd.Timestamp(f"{y}-01-01") + pd.Timedelta(days=int(rng.integers(0, 360))),
                "DispensingPharmacyNPI": rng.choice(billers),
                "PrescriberNPI": "",                      # slim RX pull
                "POS": rng.choice(["01", "12"]),          # 01 pharmacy / 12 home
                "PatientZip": rng.choice(zips), "ServiceState": "TX",
                "DaysSupply": int(rng.choice([28, 30, 56, 84])),
                "QuantityDispensed": qty, "PlanName": rng.choice(_PLANS)}
            # drug identity per style
            if style == "jcode":
                rec["ProcedureCode"] = code or ""
                rec["DrugName"] = drug
                rec["NDC"] = ""
            elif style == "ndc":
                rec["ProcedureCode"] = ""                 # no J-code on raw pharmacy
                rec["DrugName"] = drug                     # keep name as a fallback
                rec["NDC"] = ndc
            else:  # name-only
                rec["ProcedureCode"] = ""
                rec["DrugName"] = drug
                rec["NDC"] = ""
            # money layout
            if cost_fee:
                fee = round(float(rng.uniform(1.0, 12.0)), 2)
                rec["IngredientCost"] = round(allowed - fee, 2)
                rec["DispensingFee"] = fee
            else:
                rec["AllowedAmt"] = allowed
            recs.append(rec)
            i += 1
    return pd.DataFrame(recs)


if __name__ == "__main__":
    out = build(rows=1200, seed=7, national=True, messy=True)
    out.to_excel("examples/sample_claims.xlsx", index=False)
    print(f"Wrote examples/sample_claims.xlsx  ({len(out)} rows, "
          f"{int((out['BillingProviderNPI'].astype(str).str.strip()=='').sum())} blank billing NPIs)")
