"""v7 bulk reference engine: connectors as load-once local tables, not per-row APIs.

The v6 bottleneck is network round-trips — one NPPES/PECOS request per NPI. At
600K rows with referring-NPI enrichment plus more connectors, per-row calls
dominate runtime and every new connector makes it linearly slower. v7 inverts
this: each reference dataset is bulk-downloaded once, cached on disk as parquet
with a date stamp, refreshed on an interval (weekly by default), and resolved by
a single vectorized join. Live API calls are reserved for the long tail — the
handful of keys absent from the bulk snapshot.

A BulkTable wraps one dataset (download -> normalize the join key -> cache
parquet -> expose for hash-join). Adding the 9th or 20th connector is just
another table on the same engine, so breadth stops costing runtime. Every method
fails soft: if a download or cache read fails, ensure() returns None and the
caller falls back to the existing live client.
"""

import hashlib
import io
import json
import time
import zipfile
from pathlib import Path

import pandas as pd


def default_cache_dir():
    import os
    return Path(os.environ.get("NPI_BULK_CACHE", str(Path.home() / ".npi_bulk")))


class BulkTable:
    """One bulk reference dataset, cached locally and joined in-process."""

    def __init__(self, name, url, key_col, loader, cache_dir=None, refresh_days=7):
        self.name = name
        self.url = url
        self.key_col = key_col            # normalized join-key column the loader emits
        self.loader = loader              # bytes -> DataFrame (key already normalized)
        self.refresh_days = refresh_days
        self.cache_dir = Path(cache_dir) if cache_dir else default_cache_dir()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._df = None

    @property
    def _slug(self):
        return hashlib.md5(self.name.encode()).hexdigest()[:10]

    @property
    def _meta(self):
        return self.cache_dir / f"{self._slug}.json"

    def _cache_path(self, fmt):
        return self.cache_dir / f"{self._slug}.{fmt}"

    def _write_cache(self, df):
        """Prefer parquet (columnar, fast); fall back to pickle where no parquet
        engine is installed, so the tool never hard-depends on pyarrow."""
        try:
            self._cache_path("parquet").write_bytes(b"")  # touch-test writability
            df.to_parquet(self._cache_path("parquet"), index=False)
            return "parquet"
        except Exception:
            df.to_pickle(self._cache_path("pkl"))
            return "pkl"

    def _read_cache(self, fmt):
        p = self._cache_path(fmt)
        if not p.exists():
            return None
        return pd.read_parquet(p) if fmt == "parquet" else pd.read_pickle(p)

    def status(self):
        """(state, age_days, rows) for the health check — no download."""
        if not self._meta.exists():
            return ("absent", None, 0)
        try:
            meta = json.loads(self._meta.read_text())
            if not self._cache_path(meta.get("fmt", "parquet")).exists():
                return ("absent", None, 0)
            age = (time.time() - meta.get("fetched_at", 0)) / 86400
            return ("fresh" if age <= self.refresh_days else "stale", round(age, 2), meta.get("rows", 0))
        except Exception:
            return ("absent", None, 0)

    def _is_fresh(self):
        state, _, _ = self.status()
        return state == "fresh"

    def _meta_fmt(self):
        try:
            return json.loads(self._meta.read_text()).get("fmt", "parquet")
        except Exception:
            return "parquet"

    def ensure(self, session=None, force=False, allow_download=True):
        """Return the cached DataFrame, downloading + caching if missing/stale.
        Returns None (so the caller falls back to the live API) if it can't."""
        if self._df is not None and not force:
            return self._df
        if self._is_fresh() and not force:
            cached = self._read_cache(self._meta_fmt())
            if cached is not None:
                self._df = cached
                return self._df
        if not allow_download:
            return self._load_stale()
        try:
            import requests
            sess = session or requests
            r = sess.get(self.url, timeout=180)
            r.raise_for_status()
            df = self.loader(r.content)
            if df is None or df.empty or self.key_col not in df.columns:
                return self._load_stale()
            df[self.key_col] = df[self.key_col].astype("string").str.strip()
            df = df.dropna(subset=[self.key_col])
            fmt = self._write_cache(df)
            self._meta.write_text(json.dumps(
                {"fetched_at": time.time(), "url": self.url, "rows": int(len(df)),
                 "name": self.name, "fmt": fmt}))
            self._df = df
            return df
        except Exception:
            return self._load_stale()

    def _load_stale(self):
        """A stale snapshot beats nothing; only None when there is no cache."""
        cached = self._read_cache(self._meta_fmt())
        if cached is not None:
            self._df = cached
        return self._df

    def index(self, session=None):
        """key -> first matching row dict, for O(1) point lookups."""
        df = self.ensure(session=session)
        if df is None:
            return {}
        ddf = df.drop_duplicates(subset=[self.key_col])
        return dict(zip(ddf[self.key_col].astype(str), ddf.to_dict("records")))


def vectorized_fill(df, table, left_key, fields, session=None, prefix=""):
    """Fill `fields` on df via a single left-join against the bulk table on
    left_key <-> table.key_col. Returns (filled_df, miss_mask): miss_mask is True
    for rows the bulk snapshot didn't cover, i.e. the live-API long tail. This is
    the v7 hot path — 600K rows resolved in one merge instead of 600K calls."""
    ref = table.ensure(session=session)
    if ref is None or left_key not in df.columns:
        return df, pd.Series(True, index=df.index)
    keep = [table.key_col] + [c for c in fields if c in ref.columns]
    ref = ref[keep].drop_duplicates(subset=[table.key_col]).copy()
    # Rename the right-hand key to a sentinel so it can't collide with a same-named
    # column on the left (e.g. an "ndc" claims column vs the table's "ndc" key) —
    # a collision would suffix both and silently break miss-detection.
    ref = ref.rename(columns={table.key_col: "_rk"})
    if prefix:
        ref = ref.rename(columns={c: prefix + c for c in fields if c in ref.columns})
    out = df.copy()
    out["_bk"] = out[left_key].astype("string").str.strip()
    merged = out.merge(ref, left_on="_bk", right_on="_rk", how="left")
    merged.index = df.index
    miss = merged["_rk"].isna()
    merged = merged.drop(columns=[c for c in ["_bk", "_rk"] if c in merged.columns])
    return merged, miss


# --------------------------------------------------------------------------- #
# Loaders: bytes -> normalized DataFrame. One per bulk dataset. Each emits a    #
# normalized join-key column so the engine can hash-join without per-row work.  #
# --------------------------------------------------------------------------- #

def load_nucc_taxonomy(content):
    """NUCC provider taxonomy CSV -> taxonomy_code + human grouping/class/spec.
    Turns the bare taxonomy code NPPES returns into a readable specialty group
    by local join, instead of a description lookup per provider."""
    df = pd.read_csv(io.BytesIO(content), dtype=str)
    df.columns = [c.strip().lower() for c in df.columns]
    if "code" not in df.columns:
        return None
    return pd.DataFrame({
        "taxonomy_code": df["code"].astype(str).str.strip(),
        "taxonomy_grouping": df.get("grouping", "").fillna(""),
        "taxonomy_classification": df.get("classification", "").fillna(""),
        "taxonomy_specialization": df.get("specialization", "").fillna(""),
    })


def load_deactivated_npi(content):
    """CMS NPPES Deactivated NPI report (zip of xlsx/csv) -> npi + deactivation
    date. New connector: a deactivated billing NPI dates an operator's EXIT, so
    cohort attrition isn't misread as share loss in concentration analysis."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(content))
    except Exception:
        return None
    names = [n for n in zf.namelist() if n.lower().endswith((".xlsx", ".xls", ".csv"))]
    if not names:
        return None
    raw = zf.read(names[0])
    if names[0].lower().endswith(".csv"):
        df = pd.read_csv(io.BytesIO(raw), dtype=str, header=None)
    else:
        df = pd.read_excel(io.BytesIO(raw), dtype=str, header=None)
    # The report carries title rows; find the column that holds 10-digit NPIs.
    best_col, best_hits = None, 0
    for c in df.columns:
        s = df[c].astype(str).str.strip()
        hits = s.str.fullmatch(r"\d{10}").sum()
        if hits > best_hits:
            best_col, best_hits = c, hits
    if best_col is None or best_hits == 0:
        return None
    npi = df[best_col].astype(str).str.strip()
    mask = npi.str.fullmatch(r"\d{10}")
    # the deactivation date is usually the neighbouring column
    date_col = None
    for c in df.columns:
        if c == best_col:
            continue
        sample = df.loc[mask, c].astype(str)
        if sample.str.contains(r"\d{1,4}[/-]\d{1,2}", na=False).mean() > 0.3:
            date_col = c
            break
    out = pd.DataFrame({"npi": npi[mask].values})
    out["deactivation_date"] = (df.loc[mask, date_col].astype(str).values if date_col is not None else "")
    out["npi_deactivated"] = True
    return out.drop_duplicates(subset=["npi"])


def normalize_ndc9(x):
    """Normalize any NDC to a 9-digit labeler(5)+product(4) key, dropping the
    package segment. Claims NDC-11 is reliably 5-4-2, so its first 9 digits are
    labeler+product; FDA productNDC is hyphenated (labeler-product) in a native
    format, so we pad each segment. This is the join key both sides share."""
    if x is None:
        return None
    s = str(x).strip()
    import re as _re
    if "-" in s:
        parts = s.split("-")
        if len(parts) >= 2:
            lab, prod = _re.sub(r"\D", "", parts[0]), _re.sub(r"\D", "", parts[1])
            if lab and prod:
                return lab.zfill(5) + prod.zfill(4)
    s = _re.sub(r"\D", "", s)
    if len(s) == 11:
        return s[:5] + s[5:9]          # 5-4-2 -> labeler + product
    if len(s) == 10:
        s = s.zfill(11)
        return s[:5] + s[5:9]
    if len(s) == 9:
        return s
    return None


def load_fda_ndc(content):
    """FDA NDC Directory (zip) -> normalized ndc9 + generic/brand name + route.
    Lets a row with an NDC but a non-specific J-code be routed by drug identity,
    and fills a blank drug name from the labeled product."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(content))
    except Exception:
        return None
    prod = next((n for n in zf.namelist() if "product" in n.lower() and n.lower().endswith(".txt")), None)
    if not prod:
        return None
    df = pd.read_csv(io.BytesIO(zf.read(prod)), sep="\t", dtype=str,
                     encoding="latin-1", on_bad_lines="skip")
    df.columns = [c.strip().upper() for c in df.columns]
    code = next((c for c in df.columns if c == "PRODUCTNDC"), None)
    if not code:
        return None
    out = pd.DataFrame({
        "ndc": df[code].map(normalize_ndc9),
        "ndc_generic_name": df.get("NONPROPRIETARYNAME", "").fillna(""),
        "ndc_brand_name": df.get("PROPRIETARYNAME", "").fillna(""),
        "ndc_route": df.get("ROUTENAME", "").fillna(""),
    })
    return out.dropna(subset=["ndc"]).drop_duplicates(subset=["ndc"])


# Registry of the bulk connectors v7 ships. NPPES-full and PECOS-bulk use the
# same engine in production; they are not pre-registered here because their
# multi-GB downloads are validated out-of-sandbox (the live clients remain the
# long-tail fallback until a snapshot is staged).
REGISTRY = {
    "nucc_taxonomy": dict(
        url="https://www.nucc.org/images/stories/CSV/nucc_taxonomy_250.csv",
        key_col="taxonomy_code", loader=load_nucc_taxonomy, refresh_days=90),
    "deactivated_npi": dict(
        url="https://download.cms.gov/nppes/NPPES_Deactivated_NPI_Report_060925.zip",
        key_col="npi", loader=load_deactivated_npi, refresh_days=30),
    "fda_ndc": dict(
        url="https://www.accessdata.fda.gov/cder/ndctext.zip",
        key_col="ndc", loader=load_fda_ndc, refresh_days=30),
}


def get_table(name, cache_dir=None):
    """Build a BulkTable from the registry by name, or None if unknown."""
    spec = REGISTRY.get(name)
    if not spec:
        return None
    return BulkTable(name=name, cache_dir=cache_dir, **spec)
