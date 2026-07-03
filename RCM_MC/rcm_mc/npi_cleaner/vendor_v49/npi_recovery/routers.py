"""Step 1 (benefit router) and Step 2 (channel router).

Benefit router: decide whether a blank row's HCPCS is self-administered (SAD ->
Part D track, do NOT impute a medical biller) or attributable (Part B track).
Channel router: for attributable rows, decide whether the biller lives in the
Physician file or the DME-supplier file.

Both use the bundled seeds first, then fall back to empirical signals computed
later in the pipeline (e.g. no Part-B presence in any CMS file)."""

import re

import pandas as pd

from . import config

# Normalize a drug-name field for SAD matching: drop ®/™ and any punctuation,
# lowercase, collapse whitespace. "Stelara® (ustekinumab)" and "STELARA(ustekinumab)"
# both reduce to a clean token stream so the brand match stops missing on dirty
# strings. We deliberately match on brand keywords only (not bare generics),
# because a generic like "abatacept" or "vedolizumab" spans both a Part B IV form
# and a self-administered SC form — matching it would mis-route the IV claim.
_DRUG_PUNCT = re.compile(r"[^a-z0-9]+")


def _norm_drug(s):
    if s is None:
        return ""
    return _DRUG_PUNCT.sub(" ", str(s).lower()).strip()


class Router:
    def __init__(self):
        self.sad_codes, self.noc_codes = self._load_sad()
        self.partb_iv_codes = set()          # filled by _load_sad_brands
        self.sad_brands = self._load_sad_brands()
        # Dual-channel IV override set = config seed UNION any partb_iv_code
        # flagged in sad_noc_brands.csv, so the reference file is the single
        # place to extend dual-channel routing.
        self.partb_iv_override = set(config.PARTB_IV_OVERRIDE_CODES) | self.partb_iv_codes
        self.dme_codes = self._load_dme()

    def _load_sad(self):
        sad, noc = set(), set(config.NOC_CODES)
        path = config.REF_DIR / "sad_seed.csv"
        if path.exists():
            df = pd.read_csv(path, dtype=str).fillna("")
            for _, r in df.iterrows():
                code = r["hcpcs"].strip().upper()
                if r["status"].strip().lower() == "sad":
                    sad.add(code)
                elif r["status"].strip().lower() == "noc":
                    noc.add(code)
        return sad, noc

    def _load_sad_brands(self):
        path = config.REF_DIR / "sad_noc_brands.csv"
        if not path.exists():
            return []
        df = pd.read_csv(path, dtype=str).fillna("")
        if "partb_iv_code" in df.columns and "dual_channel" in df.columns:
            for _, r in df.iterrows():
                if r["dual_channel"].strip() in ("1", "true", "True") and r["partb_iv_code"].strip():
                    self.partb_iv_codes.add(r["partb_iv_code"].strip().upper())
        return [_norm_drug(b) for b in df["brand_keyword"].tolist() if str(b).strip()]

    def _load_dme(self):
        path = config.REF_DIR / "home_dme_hcpcs.csv"
        if not path.exists():
            return set()
        df = pd.read_csv(path, dtype=str).fillna("")
        return {c.strip().upper() for c in df["hcpcs"].tolist() if c.strip()}

    # -- benefit router ------------------------------------------------------
    def benefit(self, hcpcs, drug_name=None):
        """Return one of: 'sad' (Part D), 'noc' (drug indeterminate), 'part_b'."""
        code = ("" if hcpcs is None or hcpcs is pd.NA or (isinstance(hcpcs, float) and pd.isna(hcpcs))
                else str(hcpcs)).strip().upper()
        dn = "" if (drug_name is None or drug_name is pd.NA
                    or (isinstance(drug_name, float) and pd.isna(drug_name))) else str(drug_name)
        # Dual-channel IV override: a Part B IV J-code stays Part B even when the
        # molecule's brand also appears on the SAD list (Entyvio/Stelara/Simponi
        # IV). Route by HCPCS, never the molecule name. This must run BEFORE any
        # brand-name SAD match below.
        if code in self.partb_iv_override:
            return "part_b"
        if code in self.sad_codes:
            return "sad"
        if code in self.noc_codes:
            # NOC: the drug is in the name/NDC, not the code. If we can see a
            # self-administered brand in the name, route to Part D; else flag NOC.
            if dn:
                dl = _norm_drug(dn)
                if any(b in dl for b in self.sad_brands):
                    return "sad"
            return "noc"
        # A named drug on a normal code can still be self-administered.
        if dn:
            dl = _norm_drug(dn)
            if any(b in dl for b in self.sad_brands):
                return "sad"
        return "part_b"

    # -- channel router ------------------------------------------------------
    def channel(self, hcpcs):
        """Return 'dme' if the code is a home/DME-administered drug, else 'physician'."""
        code = ("" if hcpcs is None or hcpcs is pd.NA or (isinstance(hcpcs, float) and pd.isna(hcpcs))
                else str(hcpcs)).strip().upper()
        return "dme" if code in self.dme_codes else "physician"

    def route_frame(self, std):
        """Vectorised routing of every distinct (hcpcs, drug_name) in the panel."""
        sub = std[["hcpcs", "drug_name"]].copy()
        sub["drug_name"] = sub["drug_name"].astype("string").fillna("")
        uniq = sub.drop_duplicates()
        uniq["benefit"] = [self.benefit(h, d) for h, d in zip(uniq["hcpcs"], uniq["drug_name"])]
        uniq["channel"] = [self.channel(h) for h in uniq["hcpcs"]]
        return uniq
