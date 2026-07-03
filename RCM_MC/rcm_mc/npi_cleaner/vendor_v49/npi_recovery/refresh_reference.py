"""
refresh_reference.py  (v42)
===========================

Refresh the shipped coding-edit reference seeds to the current CMS quarter and
fiscal year. Everything the toolkit needs ships as a dated seed so it runs fully
offline; this module is the opt-in path (`--fix-refresh`) that pulls the live
CMS files and rewrites the seeds in place.

Network-optional and defensive: any download failure leaves the existing seed
untouched and is reported, never raised. The CMS page HTML is a shell, so the
current filenames are discovered by scraping the .zip hrefs off the index pages
rather than guessing dated URLs.

Sources (all free / public):
  NCCI MUE tables               cms.gov NCCI MUE page
  NCCI PTP quarterly changes    cms.gov NCCI PTP page
  ICD-10-CM order files         cms.gov ICD-10-CM year pages
  JW/JZ single-dose HCPCS list  cms.gov Discarded Drugs page (PDF)
  NPPES deactivation file       download.cms.gov/nppes index
"""
from __future__ import annotations

import io
import os
import re
import zipfile
import urllib.request
import pandas as pd

_UA = {"User-Agent": "Mozilla/5.0 (compatible; npi-recovery/42)"}
_MUE_PAGE = ("https://www.cms.gov/medicare/coding-billing/"
             "national-correct-coding-initiative-ncci-edits/"
             "medicare-ncci-medically-unlikely-edits-mues")
_PTP_PAGE = ("https://www.cms.gov/medicare/coding-billing/"
             "national-correct-coding-initiative-ncci-edits/"
             "medicare-ncci-procedure-procedure-ptp-edits")
_JWJZ_PDF = "https://www.cms.gov/files/document/jw-modifier-and-jz-modifier-policy-hcpcs-codes.pdf"
_NPPES_INDEX = "https://download.cms.gov/nppes/NPI_Files.html"


def _get(url, timeout=90):
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _log(console, msg):
    if console is not None:
        console.print(msg)
    else:
        print(msg)


def _scrape_zip_hrefs(page_url):
    html = _get(page_url, timeout=45).decode("utf-8", errors="replace")
    hrefs = re.findall(r'href="([^"]+\.zip)"', html)
    out = []
    for h in hrefs:
        if h.startswith("/"):
            h = "https://www.cms.gov" + h
        out.append(h)
    return out


def _refresh_mue(ref_dir, console):
    hrefs = _scrape_zip_hrefs(_MUE_PAGE)
    want = {"practitioner": None, "outpatient_hospital": None}
    for h in hrefs:
        low = h.lower()
        if "practitioner-services-mue-table" in low and "quarterly" not in low:
            want["practitioner"] = h
        elif "outpatient-hospital-services-mue-table" in low and "quarterly" not in low:
            want["outpatient_hospital"] = h
    frames = []
    for service, url in want.items():
        if not url:
            continue
        z = zipfile.ZipFile(io.BytesIO(_get(url)))
        member = next(n for n in z.namelist() if n.lower().endswith(".xlsx"))
        df = pd.read_excel(io.BytesIO(z.read(member)), dtype=str, header=1)
        df.columns = [str(c).replace("\n", " ").strip() for c in df.columns]
        code_c = next(c for c in df.columns if "HCPCS" in c or "CPT Code" in c)
        val_c = next(c for c in df.columns if "MUE Value" in c)
        mai_c = next(c for c in df.columns if "Adjudication" in c)
        rat_c = next((c for c in df.columns if "Rationale" in c), None)
        frames.append(pd.DataFrame({
            "hcpcs": df[code_c].str.strip(), "service": service,
            "mue_value": pd.to_numeric(df[val_c], errors="coerce").astype("Int64"),
            "mai": df[mai_c].str.extract(r"(\d)")[0],
            "rationale": df[rat_c].str.strip() if rat_c else "",
        }).dropna(subset=["hcpcs"]).query("hcpcs != 'nan'"))
    if frames:
        out = pd.concat(frames, ignore_index=True)
        out["source"] = "CMS NCCI MUE (refreshed live)"
        out.to_csv(os.path.join(ref_dir, "ncci_mue_seed.csv"), index=False)
        _log(console, f"  MUE refreshed: {len(out)} rows")


def _refresh_ptp(ref_dir, console):
    hrefs = _scrape_zip_hrefs(_PTP_PAGE)
    frames = []
    for h in hrefs:
        low = h.lower()
        service = ("practitioner" if "practitioner" in low else
                   "outpatient_hospital" if "hospital" in low else None)
        if service is None or "quarterly-additions" not in low:
            continue
        z = zipfile.ZipFile(io.BytesIO(_get(h)))
        member = next((n for n in z.namelist() if n.lower().endswith(".xlsx")), None)
        if member is None:
            continue
        df = pd.read_excel(io.BytesIO(z.read(member)), dtype=str, header=1)
        df.columns = [str(c).replace("\n", " ").strip()[:40] for c in df.columns]
        frames.append(pd.DataFrame({
            "col1": df.iloc[:, 0].str.strip(), "col2": df.iloc[:, 1].str.strip(),
            "modifier_indicator": df.iloc[:, 2].str.extract(r"(\d)")[0],
            "service": service,
        }).dropna(subset=["col1", "col2"]).query("col1 != 'nan' and col2 != 'nan'"))
    if frames:
        out = pd.concat(frames, ignore_index=True)
        out["source"] = "CMS NCCI PTP quarterly change (refreshed live)"
        out.to_csv(os.path.join(ref_dir, "ncci_ptp_sample.csv"), index=False)
        _log(console, f"  PTP refreshed: {len(out)} rows")


def _refresh_jwjz(ref_dir, console):
    try:
        import pdfplumber
    except Exception:
        _log(console, "  JW/JZ skipped: pdfplumber not installed")
        return
    data = _get(_JWJZ_PDF, timeout=60)
    codes = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for pg in pdf.pages:
            for m in re.findall(r'\b([JQ]\d{4}|C\d{4})\b', pg.extract_text() or ""):
                codes.append(m)
    codes = sorted(set(codes))
    if codes:
        pd.DataFrame({"hcpcs": codes, "single_dose": True,
                      "effective_note": "JZ (no waste) or JW (waste) for DOS >= 2023-07-01",
                      "source": "CMS JW/JZ Policy HCPCS list (refreshed live)"}).to_csv(
            os.path.join(ref_dir, "jw_jz_single_dose_seed.csv"), index=False)
        _log(console, f"  JW/JZ refreshed: {len(codes)} codes")


def _refresh_deactivation(ref_dir, console):
    html = _get(_NPPES_INDEX, timeout=45).decode("utf-8", errors="replace")
    m = re.search(r"href='(\./NPPES_Deactivated_NPI_Report_[^']+\.zip)'", html)
    if not m:
        _log(console, "  deactivation skipped: link not found on index")
        return
    url = "https://download.cms.gov/nppes/" + m.group(1).lstrip("./")
    z = zipfile.ZipFile(io.BytesIO(_get(url, timeout=180)))
    member = z.namelist()[0]
    dd = pd.read_excel(io.BytesIO(z.read(member)), dtype=str, header=1)
    dd.columns = ["npi", "deactivation_date"]
    dd = dd[dd["npi"].str.fullmatch(r"\d{10}", na=False)].copy()
    dd["source"] = "CMS NPPES Monthly Deactivation (refreshed live)"
    dd.to_csv(os.path.join(ref_dir, "nppes_deactivated_seed.csv"), index=False)
    _log(console, f"  deactivation refreshed: {len(dd)} NPIs")


def refresh_all(ref_dir, console=None):
    """Refresh every coding-edit reference seed. Each source is independent and
    defensive: a failure logs and moves on, leaving the shipped seed in place."""
    os.makedirs(ref_dir, exist_ok=True)
    _log(console, "[bold]Refreshing CMS reference data[/bold]"
                  if console else "Refreshing CMS reference data")
    for name, fn in (("MUE", _refresh_mue), ("PTP", _refresh_ptp),
                     ("JW/JZ", _refresh_jwjz), ("deactivation", _refresh_deactivation)):
        try:
            fn(ref_dir, console)
        except Exception as e:
            _log(console, f"  {name} refresh failed ({type(e).__name__}: {e}); kept existing seed")
