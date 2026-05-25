#!/usr/bin/env python3
"""Offline extractor — licensed IBISWorld PDFs → normalized PEdesk derived data.

BUILD-TIME ONLY. Reads the licensed reports from the licensee's machine
(default ``~/Desktop/Industry Information Pages/``), extracts STRUCTURED facts
(metrics, segments, drivers, cost-structure benchmarks, codes, definitions),
and writes normalized JSON/CSV under ``data/industry_intel/``. Raw PDFs are
never copied into the repo. Long verbatim narrative is NOT stored — summary
fields are length-capped (see ``_MAX_SUMMARY`` / the guardrail test).

Every record carries provenance (source_file, report_title, publisher,
publication_date, industry_code, section, page, value_type, confidence,
license_note). Loaders read the committed derived files only.

Run:  python scripts/extract_industry_report_intel.py
      python scripts/extract_industry_report_intel.py --folder /path/to/pdfs
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import re
from pathlib import Path

import pdfplumber

_OUT = Path(__file__).resolve().parent.parent / "data" / "industry_intel"
_DEFAULT_FOLDER = os.path.expanduser("~/Desktop/Industry Information Pages")
_PUBLISHER = "IBISWorld"
_LICENSE = "Licensed business report (IBISWorld); derived structured facts only."
_MAX_SUMMARY = 400  # chars — guardrail against verbatim narrative

# IBIS code → (naics, slug, pedesk_verticals)
_CODE_MAP = {
    "62": ("62", "healthcare-social-assistance", ["all"]),
    "62111a": ("621111", "primary-care-doctors", ["primary_care", "physician"]),
    "62111b": ("621112", "specialist-doctors", ["specialist", "physician"]),
    "62149": ("621498", "outpatient-care-centers", ["outpatient", "asc", "dialysis"]),
    "62211": ("622110", "hospitals", ["hospital"]),
}

_NUM = r"\$?([\d,]+(?:\.\d+)?)\s*(bn|m|k|%)?"


def _money_to_float(s: str, unit: str) -> float | None:
    try:
        v = float(s.replace(",", ""))
    except ValueError:
        return None
    return {"bn": v * 1e3, "m": v, "k": v / 1e3}.get(unit or "", v)  # normalize to $M


def _code_for(fname: str) -> str:
    base = os.path.basename(fname)
    m = re.match(r"(\d{2,5}[ab]?)\b", base)
    code = (m.group(1) if m else "").lower()
    return code if code in _CODE_MAP else base.split()[0].lower()


def _find_section_page(pdf, *headers: str) -> int:
    for i, pg in enumerate(pdf.pages):
        t = pg.extract_text() or ""
        if any(h in t for h in headers):
            return i
    return -1


def _extract_at_a_glance(text: str, ctx: dict) -> tuple[list, list, list]:
    """Returns (metrics, segments, drivers) from the At a Glance page.

    Headline LEVELS (revenue/employment/etc.) come from Key Statistics, which
    parses far more reliably than the multi-column At-a-Glance block; here we
    take only Profit Margin (clean) plus the segment mix and driver list.
    """
    metrics, segments, drivers = [], [], []
    mm = re.search(r"Profit Margin.*?([\d.]+)\s*%", text) or re.search(r"([\d.]+)%\s*’21-’26", text)
    if mm:
        metrics.append({**ctx, "metric_name": "Profit Margin", "value": float(mm.group(1)),
                        "unit": "%", "value_type": "ratio", "source_section": "At a Glance",
                        "confidence": "high"})
    # Segments: "<name> $142.8bn 38.5%" — name may start lowercase (line wrap).
    for m in re.finditer(r"([A-Za-z][A-Za-z/&'’\- ]{3,48}?)\s+\$([\d,.]+)\s*(bn|m|k)\s+([\d.]+)%", text):
        rev = _money_to_float(m.group(2), m.group(3))
        seg = re.sub(r"\s+", " ", m.group(1).strip())
        if rev and seg.lower() not in ("profit margin", "profit", "wages"):
            segments.append({**ctx, "segment_name": seg, "revenue": round(rev, 1),
                             "share": float(m.group(4)), "unit": "$M",
                             "source_section": "Products and Services"})
    # Drivers: "<driver> Positive|Negative|Steady|Mixed"
    for m in re.finditer(r"([A-Z][A-Za-z0-9/,’'&\-\. ]{6,70}?)\s+(Positive|Negative|Steady|Mixed|Increasing|Decreasing)\b", text):
        d = m.group(1).strip()
        if "Key External Drivers" not in d and len(d) > 6:
            drivers.append({**ctx, "driver": d, "direction": m.group(2),
                            "source_section": "Key External Drivers",
                            "diligence_implication": ""})
    return metrics, segments, drivers


def _extract_cost_structure(text: str, ctx: dict) -> list:
    rows = []
    for m in re.finditer(r"^(Wages|Purchases|Profit|Depreciation|Rent|Marketing|Utilities)\s+([\d.]+)\s+([\d.]+|-)\s*$",
                         text, re.MULTILINE):
        ind = float(m.group(2))
        sec = None if m.group(3) == "-" else float(m.group(3))
        rows.append({**ctx, "benchmark_name": f"Cost: {m.group(1)}", "value": ind,
                     "sector_value": sec, "unit": "% of revenue",
                     "source_section": "Financial Benchmarks", "caveat": "industry vs sector share"})
    return rows


def _extract_key_stats_latest(text: str, ctx: dict, current_year: str = "") -> list:
    """Current-year row from Key Statistics (Revenue/Estab/Employment/Wages).

    Picks the row matching the report's publication year (the industry's
    'current' figures) when present, else the latest year in the table.
    """
    rows = []
    best = None
    matches = list(re.finditer(
        r"^((?:19|20)\d{2})\s+([\d,]+\.\d)\s+([\d,]+\.\d)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+\.\d)",
        text, re.MULTILINE))
    for m in matches:
        if current_year and m.group(1) == current_year:
            best = m
            break
        best = m  # fallback: keep last (latest year present)
    if best:
        yr = best.group(1)
        for idx, (mname, unit, vt) in ((2, ("Revenue", "$M", "level")), (4, ("Establishments", "units", "count")),
                                       (5, ("Enterprises", "units", "count")), (6, ("Employment", "units", "count")),
                                       (7, ("Wages", "$M", "level"))):
            raw = best.group(idx).replace(",", "")
            try:
                rows.append({**ctx, "metric_name": mname, "value": float(raw), "unit": unit,
                             "value_type": vt, "period": yr, "source_section": "Key Statistics",
                             "confidence": "high"})
            except ValueError:
                pass
    return rows


def _extract_about(pdf, ctx: dict) -> dict:
    """Definition (paraphrase-capped), included services, related industries/terms."""
    out = {"summary_nonverbatim": "", "included_services": [], "related_industries": [],
           "related_terms": [], "major_players": []}
    for pg in pdf.pages[2:9]:
        t = pg.extract_text() or ""
        # Skip the Table of Contents page (dotted leaders) — require real prose.
        if "Table of Contents" in t or t.count("....") > 3:
            continue
        if "Definition" in t and "Codes" in t:
            dm = re.search(r"Definition\s+(.*?)\s+Codes", t, re.DOTALL)
            if dm:
                summ = re.sub(r"\s+", " ", dm.group(1)).strip()
                if "." in summ and not summ.startswith("."):
                    out["summary_nonverbatim"] = summ[:_MAX_SUMMARY]
            inc = re.search(r"What's Included\s+(.*?)\s+(Companies|Related Industries)", t, re.DOTALL)
            if inc:
                out["included_services"] = [x.strip(" •\t") for x in inc.group(1).split("\n")
                                            if x.strip(" •\t")][:12]
            if "No single company accounts" in t:
                out["major_players"] = ["Fragmented — no company >5% market share"]
            break
    return out


# PEdesk-authored diligence questions per industry (NOT verbatim from report).
# source_basis = PEDESK marks these as PEdesk value-add grounded on the report's
# structure, to be answered by joining CMS/HCRIS/provider/deal data.
_QUESTIONS = {
    "_common": [
        ("How does the target's revenue growth compare to the industry CAGR in this report?", "growth", "metrics"),
        ("Is the target's profit margin above or below the industry benchmark?", "margin", "benchmarks"),
        ("Which report-cited external drivers most affect this target, and in which direction?", "drivers", "drivers"),
        ("What public CMS/HCRIS data can validate or challenge this industry thesis?", "validation", "public-data"),
        ("Which metrics here are report-derived vs provider-specific?", "provenance", "labeling"),
    ],
    "62211": [
        ("Does the target's cost structure match the industry wage/supply share?", "cost", "benchmarks"),
        ("How do the target's HCRIS margins compare to the industry profit benchmark?", "margin", "hcris-xray"),
    ],
    "621111": [
        ("Is the target exposed to the primary-care physician shortage cited as a driver?", "workforce", "hrsa"),
        ("How does the target's payer mix track the private-insurance/Medicare drivers?", "payer", "payer-stress"),
    ],
    "621112": [
        ("Which specialist segments drive the target's revenue vs the industry mix?", "segments", "segments"),
        ("How does specialist supply/density in the target's geography compare?", "supply", "cms"),
    ],
    "62149": [
        ("Which outpatient segment (ASC/dialysis/emergency) is the target in, and its share trend?", "segments", "segments"),
        ("How do CMS ASC/dialysis provider data validate the target's volumes?", "validation", "cms"),
    ],
    "62": [
        ("Which sub-sector verticals drive the broad-sector thesis for this deal?", "sector", "verticals"),
    ],
}


def _questions_for(ctx: dict, code: str) -> list:
    rows = []
    for q, cat, applies in _QUESTIONS["_common"] + _QUESTIONS.get(code, []):
        rows.append({**ctx, "question": q, "category": cat, "source_basis": "PEDESK",
                     "applies_to": applies, "suggested_use": "diligence/Guide"})
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder", default=_DEFAULT_FOLDER)
    args = ap.parse_args(argv)
    _OUT.mkdir(parents=True, exist_ok=True)

    pdfs = sorted(glob.glob(os.path.join(args.folder, "*.pdf")))
    if not pdfs:
        print(f"No PDFs in {args.folder}", flush=True)
        return 1

    reports, metrics, segments, drivers, benchmarks, questions = [], [], [], [], [], []
    log = []
    for path in pdfs:
        code = _code_for(path)
        naics, slug, verticals = _CODE_MAP.get(code, (code, code, []))
        with pdfplumber.open(path) as pdf:
            p1 = pdf.pages[0].extract_text() or ""
            title = p1.split("\n")[0].strip()
            # report title is the second line block ("Primary Care Doctors in the US")
            rep_title = next((l.strip() for l in p1.split("\n")[1:4]
                              if l.strip() and "•" not in l and "IBIS" not in l), title)
            pub = ""
            pm = re.search(r"Published:\s*([A-Za-z]+ \d{4})", p1)
            if pm:
                pub = pm.group(1)
            ctx = {"industry_id": code, "naics_code": naics, "report_title": rep_title,
                   "publisher": _PUBLISHER, "publication_date": pub,
                   "source_file": os.path.basename(path), "license_note": _LICENSE}

            about = _extract_about(pdf, ctx)
            gi = _find_section_page(pdf, "At a Glance")
            gtext = ""
            # the *content* At-a-Glance page (not the TOC mention) — search after page 4
            for i in range(4, len(pdf.pages)):
                t = pdf.pages[i].extract_text() or ""
                if "At a Glance" in t and ("Revenue" in t and "Profit" in t):
                    gtext = t
                    gi = i
                    break
            m, s, d = _extract_at_a_glance(gtext, {**ctx, "page": gi + 1}) if gtext else ([], [], [])

            ci = _find_section_page(pdf, "Cost Structure Benchmarks")
            ctext = pdf.pages[ci].extract_text() if ci >= 0 else ""
            b = _extract_cost_structure(ctext or "", {**ctx, "page": ci + 1})

            ki = _find_section_page(pdf, "Key Statistics")
            ktext = ""
            for i in range(max(ki, 0), len(pdf.pages)):
                t = pdf.pages[i].extract_text() or ""
                if "Industry Data" in t and "Revenue" in t and re.search(r"(?:19|20)\d{2}\s+[\d,]+\.\d", t):
                    ktext = t
                    ki = i
                    break
            cur_yr = pub.split()[-1] if pub else ""
            ks = _extract_key_stats_latest(ktext, {**ctx, "page": ki + 1}, cur_yr) if ktext else []

            reports.append({"industry_id": code, "slug": slug, "naics_code": naics,
                            "code_label": code, "title": rep_title, "report_title": rep_title,
                            "publisher": _PUBLISHER, "publication_date": pub,
                            "source_file": os.path.basename(path),
                            "source_kind": "LICENSED_REPORT_DERIVED", "license_note": _LICENSE,
                            "pedesk_verticals": verticals, **about})
            metrics.extend(m + ks)
            segments.extend(s)
            drivers.extend(d)
            benchmarks.extend(b)
            questions.extend(_questions_for(ctx, code))
            log.append(f"{code}: {len(m)+len(ks)} metrics, {len(s)} segments, "
                       f"{len(d)} drivers, {len(b)} benchmarks")

    # de-dup drivers (regex can double-match)
    seen = set()
    drivers = [x for x in drivers if (k := (x["industry_id"], x["driver"])) not in seen
               and not seen.add(k)]

    (_OUT / "industry_reports.json").write_text(json.dumps(reports, indent=2))
    _write_csv(_OUT / "industry_metrics.csv", metrics)
    _write_csv(_OUT / "industry_segments.csv", segments)
    _write_csv(_OUT / "industry_drivers.csv", drivers)
    _write_csv(_OUT / "industry_benchmarks.csv", benchmarks)
    _write_csv(_OUT / "industry_questions.csv", questions)
    (_OUT / "extraction_log.txt").write_text("\n".join(log) + "\n")
    print("\n".join(log))
    print(f"Wrote {len(reports)} reports → {_OUT}")
    return 0


def _write_csv(path: Path, rows: list) -> None:
    if not rows:
        path.write_text("")
        return
    keys = list({k for r in rows for k in r})
    # stable column order: provenance last
    front = [k for k in ("industry_id", "naics_code", "metric_name", "segment_name",
                         "driver", "benchmark_name", "value", "sector_value", "unit",
                         "share", "direction", "period", "value_type") if k in keys]
    rest = [k for k in keys if k not in front]
    cols = front + rest
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)


if __name__ == "__main__":
    raise SystemExit(main())
