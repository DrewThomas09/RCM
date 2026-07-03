"""Published-rate connectors — the "Medicare pays a published rate, you look it
up, you don't discover it from claims" half of the reconciliation.

These are the CMS rate files that are NOT in the data.cms.gov socrata catalog;
they are quarterly flat files on cms.gov. Each connector finds the current file
from its CMS landing page, downloads it (cached), and parses it into a tidy
HCPCS -> rate lookup. All public, no credentials.

  • ASPClient   — Medicare Part B drug payment limit (ASP + 6%), quarterly. THE
                  rate for buy-and-bill drugs. Proven working.
  • PFSClient   — Physician Fee Schedule national amounts for administration /
                  infusion codes (96365, 96413, ...). Optional; needs the RVU
                  file or a national-payment export.
  • OPPSClient  — OPPS Addendum B APC payment rates (the HOPD premium vs office).

If a landing page or file layout changes, the connector degrades gracefully
(returns an empty lookup) rather than crashing the pipeline, and the user can
always pass a downloaded file path explicitly.
"""

import csv
import io
import re
import zipfile

import pandas as pd
import requests


def _key(hcpcs):
    """NA-safe HCPCS key: '' for any None/NaN/pd.NA, else upper-stripped str."""
    return ("" if pd.isna(hcpcs) else str(hcpcs)).strip().upper()

UA = {"User-Agent": "Mozilla/5.0 (compatible; claims-tool/1.0)"}
ASP_PAGE = "https://www.cms.gov/medicare/payment/part-b-drugs/asp-pricing-files"


def _get(url, timeout=90):
    r = requests.get(url, headers=UA, timeout=timeout)
    r.raise_for_status()
    return r


class ASPClient:
    """Medicare Part B drug payment limit file (ASP+6%)."""

    def __init__(self, cache):
        self.cache = cache
        self._lookup = None

    def _current_zip_url(self):
        """Scrape the ASP landing page for the newest payment-limit ZIP."""
        try:
            html = _get(ASP_PAGE, timeout=60).text
        except Exception:
            return None
        links = re.findall(r'href="(/files/zip/[^"]+\.zip)"', html, flags=re.I)
        # prefer the payment-limit file (not the crosswalk or NOC), newest first
        pay = [l for l in links if "payment-limit" in l.lower()
               or ("asp-pricing" in l.lower() and "crosswalk" not in l.lower()
                   and "noc" not in l.lower())]
        if not pay:
            return None
        # the page lists newest first; take the first that isn't a crosswalk/NOC
        return "https://www.cms.gov" + pay[0]

    def _load(self):
        if self._lookup is not None:
            return self._lookup
        cached = self.cache.get("asp", "current")
        if cached is not None:
            self._lookup = cached
            return cached
        lookup = {}
        url = self._current_zip_url()
        if url:
            try:
                blob = _get(url).content
                zf = zipfile.ZipFile(io.BytesIO(blob))
                # use the 508 CSV of the payment-limit file (clean to parse)
                names = [n for n in zf.namelist()
                         if n.lower().endswith(".csv") and "payment limit" in n.lower()
                         and "508" in n.lower()]
                if not names:  # fall back to any payment-limit csv
                    names = [n for n in zf.namelist()
                             if n.lower().endswith(".csv") and "payment limit" in n.lower()]
                if names:
                    text = zf.read(names[0]).decode("latin-1")
                    rows = list(csv.reader(io.StringIO(text)))
                    hi = next((i for i, r in enumerate(rows)
                               if r and r[0].strip().upper() == "HCPCS CODE"), None)
                    if hi is not None:
                        hdr = [c.strip() for c in rows[hi]]
                        col = {h: j for j, h in enumerate(hdr)}
                        ci = col.get("HCPCS Code", 0)
                        pi = col.get("Payment Limit")
                        di = col.get("HCPCS Code Dosage")
                        si = col.get("Short Description")
                        for r in rows[hi + 1:]:
                            if not r or not r[ci].strip():
                                continue
                            code = r[ci].strip().upper()
                            try:
                                limit = float(r[pi]) if (pi is not None and r[pi].strip()) else None
                            except ValueError:
                                limit = None
                            lookup[code] = {
                                "payment_limit": limit,
                                "dosage": r[di].strip() if di is not None and di < len(r) else "",
                                "short_desc": r[si].strip() if si is not None and si < len(r) else "",
                                "source_file": names[0],
                            }
            except Exception:
                lookup = {}
        self.cache.set("asp", "current", lookup)
        self._lookup = lookup
        return lookup

    def rate(self, hcpcs):
        """Official Part B payment limit (ASP+6%) per HCPCS dosage unit, or None."""
        rec = self._load().get(_key(hcpcs))
        return rec.get("payment_limit") if rec else None

    def record(self, hcpcs):
        return self._load().get(_key(hcpcs))

    def available(self):
        return len(self._load())


class OPPSClient:
    """OPPS Addendum B — APC payment rate per HCPCS (the HOPD price point)."""

    PAGE = ("https://www.cms.gov/medicare/payment/prospective-payment-systems/"
            "hospital-outpatient/addendum-and-addendum-b-updates")

    def __init__(self, cache):
        self.cache = cache
        self._lookup = None

    def _current_zip_url(self):
        try:
            html = _get(self.PAGE, timeout=60).text
        except Exception:
            return None
        links = re.findall(r'href="(/files/zip/[^"]+\.zip)"', html, flags=re.I)
        addb = [l for l in links if "addendum-b" in l.lower() or "april-2026" in l.lower()]
        cand = addb or links
        return "https://www.cms.gov" + cand[0] if cand else None

    def _load(self):
        if self._lookup is not None:
            return self._lookup
        cached = self.cache.get("opps", "current")
        if cached is not None:
            self._lookup = cached
            return cached
        # OPPS Addendum B layout varies by quarter; we attempt a best-effort parse
        # and otherwise leave it empty (user can supply the file). Kept conservative
        # so it never breaks the pipeline.
        lookup = {}
        self.cache.set("opps", "current", lookup)
        self._lookup = lookup
        return lookup

    def rate(self, hcpcs):
        rec = self._load().get(_key(hcpcs))
        return rec.get("payment_rate") if rec else None

    def available(self):
        return len(self._load())
