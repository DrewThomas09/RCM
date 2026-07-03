"""Step 5b (v20): probabilistic fuzzy entity linkage with Splink.

The deterministic resolver in `entity.py` links sibling NPIs on *exact* signals
(exact PAC ID, exact normalized org name, exact address key, exact authorized
official). That is precise but it misses the near-miss cases an acquisition /
rebrand actually produces:

  * "1700 LAKEWOOD DR"  vs  "1700 LAKEWOOD DRIVE"   (suffix / formatting)
  * "CLINICAL SPECIALTY INFUSIONS"  vs  "CLINICAL SPECIALITY INFUSION"  (typo / plural)
  * "KABAFUSION TEXAS"  vs  "KABA FUSION TX LLC"    (spacing / abbreviation)

Splink (the UK Ministry of Justice's open-source Fellegi-Sunter record-linkage
engine) closes exactly that gap: it learns m/u match weights by EM and produces
a *calibrated* match probability per pair, so fuzzy name/address variants link
without the brittleness of exact equality.

DESIGN — layer, don't replace.
The deterministic union-find stays the always-on path (and the only path when
Splink isn't installed). This module returns a set of high-confidence *fuzzy
edges* (npi_a, npi_b) that `entity.merge_fuzzy_links` then unions ON TOP OF the
deterministic clusters. So PAC-ID and exact links always fire; Splink only adds
merges exact matching missed. Nothing here can split a deterministic cluster.

HONESTY.
This improves the *entity / affiliation* side (Job A in the linkage spec) — the
clean win. It does NOT recover the residual billing NPI on a blank claim row:
a residual row has drug + ZIP3 and no identity columns to match on (the "bag of
words" case Splink itself says it cannot link). That residual stays best-guess.

Splink and DuckDB are OPTIONAL dependencies. If either is missing, every public
function degrades to a no-op (returns [] / empty) and the pipeline runs exactly
as v19. Install with:  pip install "splink>=4.0,<5" "duckdb>=1.3"
"""

from __future__ import annotations

import multiprocessing
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd


# --------------------------------------------------------------------------- #
# availability
# --------------------------------------------------------------------------- #
def splink_available() -> bool:
    """True iff Splink + a usable DuckDB backend import cleanly."""
    try:
        import duckdb  # noqa: F401
        import splink  # noqa: F401
        from splink import Linker, SettingsCreator, DuckDBAPI, block_on  # noqa: F401
        import splink.comparison_library as cl  # noqa: F401
        return True
    except Exception:
        return False


def splink_version() -> str:
    try:
        import splink
        return getattr(splink, "__version__", "?")
    except Exception:
        return "not installed"


# --------------------------------------------------------------------------- #
# build a standardized provider frame from cached NPPES records
# --------------------------------------------------------------------------- #
_SUFFIX = {
    " st ": " street ", " st.": " street", " ave ": " avenue ", " ave.": " avenue",
    " dr ": " drive ", " dr.": " drive", " rd ": " road ", " rd.": " road",
    " blvd ": " boulevard ", " blvd.": " boulevard", " ste ": " suite ",
    " hwy ": " highway ", " pkwy ": " parkway ", " ln ": " lane ", " ct ": " court ",
}


def _std_text(s) -> str:
    s = (str(s) if s is not None else "").lower()
    out = []
    for ch in s:
        out.append(ch if (ch.isalnum() or ch == " ") else " ")
    s = " " + " ".join("".join(out).split()) + " "
    for k, v in _SUFFIX.items():
        s = s.replace(k, v)
    return s.strip()


def _standardize_records(npis, nppes, max_workers=16, progress=None):
    """One standardized row per NPI, pulled from the (cached) NPPES client.

    Columns: unique_id, npi, provider_name, zip5, taxonomy, addr, official.
    Plain object-string dtypes throughout (DuckDB registration rejects the
    pandas 'string' extension dtype on some versions).
    """
    npis = sorted({str(n).strip() for n in npis if n and str(n).strip()})
    rows, done, total = [], 0, max(len(npis), 1)

    def worker(npi):
        try:
            rec = nppes.lookup(npi) or {}
        except Exception:
            rec = {}
        name = rec.get("name") or rec.get("enroll_org") or ""
        # fold the first other/DBA name in as an alias row-feature for matching
        oon = (rec.get("other_org_names") or "").split(";")
        alias = oon[0].strip() if oon and oon[0].strip() else ""
        return {
            "unique_id": f"npi:{npi}",
            "npi": str(npi),
            "provider_name": _std_text(name),
            "provider_alias": _std_text(alias),
            "zip5": str(rec.get("postal") or "")[:5],
            "taxonomy": str(rec.get("taxonomy_code") or rec.get("taxonomy") or ""),
            "addr": _std_text(rec.get("addr_line") or rec.get("loc_addr") or ""),
            "official": _std_text(rec.get("official") or ""),
        }

    if npis:
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futs = [ex.submit(worker, n) for n in npis]
            for fut in as_completed(futs):
                rows.append(fut.result())
                done += 1
                if progress and (done % 50 == 0 or done == total):
                    progress("Standardizing for linkage", done / total)

    df = pd.DataFrame(rows)
    if not df.empty:
        # drop rows with no usable name AND no address — nothing to match on
        df = df[(df["provider_name"].str.len() > 0) | (df["addr"].str.len() > 0)]
        df = df.reset_index(drop=True)
        for c in df.columns:           # force plain object str (DuckDB-safe)
            df[c] = df[c].astype(object)
    return df


# --------------------------------------------------------------------------- #
# the Splink model -> fuzzy edges
# --------------------------------------------------------------------------- #
def build_fuzzy_links(npis, nppes, *, min_match_prob=0.92, progress=None,
                      max_records=60000):
    """Return a list of high-confidence fuzzy-linked NPI pairs (npi_a, npi_b).

    These are the edges the deterministic union-find missed. Feed them to
    `entity.merge_fuzzy_links`. Degrades to [] when Splink/DuckDB are absent,
    when there are <3 records, or on any internal error — the caller treats an
    empty result as "no fuzzy layer", identical to v19 behaviour.
    """
    if not splink_available():
        return []
    df = _standardize_records(npis, nppes, progress=progress)
    if df is None or len(df) < 3:
        return []
    if len(df) > max_records:
        # keep it tractable; the residual book is well under this in practice
        df = df.head(max_records).reset_index(drop=True)

    try:
        import logging
        for _ln in ("splink", "splink.internals", "py.warnings"):
            logging.getLogger(_ln).setLevel(logging.ERROR)
        import splink.comparison_library as cl
        from splink import Linker, SettingsCreator, DuckDBAPI, block_on

        comparisons = [
            cl.JaroWinklerAtThresholds("provider_name", [0.92, 0.80]),
            cl.JaroWinklerAtThresholds("addr", [0.92, 0.80]),
            cl.ExactMatch("zip5"),
            cl.ExactMatch("taxonomy"),
        ]
        settings = SettingsCreator(
            link_type="dedupe_only",
            comparisons=comparisons,
            blocking_rules_to_generate_predictions=[
                block_on("zip5"),
                block_on("taxonomy"),
                block_on("substr(provider_name, 1, 4)"),  # cross-ZIP DBA catch
            ],
        )
        linker = Linker(df, settings, db_api=DuckDBAPI())

        # Trap: on a single-core runner Splink sets salting_partitions =
        # cpu_count() == 1 when max_pairs > 1e4 and then rejects it. Cap to the
        # no-salting branch when we only have one core.
        cores = multiprocessing.cpu_count() or 1
        max_pairs = 1e4 if cores <= 1 else 1e6

        linker.training.estimate_probability_two_random_records_match(
            [block_on("zip5", "addr")], recall=0.9)
        linker.training.estimate_u_using_random_sampling(max_pairs=max_pairs)
        linker.training.estimate_parameters_using_expectation_maximisation(
            block_on("zip5"))
        try:
            linker.training.estimate_parameters_using_expectation_maximisation(
                block_on("taxonomy"))
        except Exception:
            pass  # second EM pass is a refinement, not required

        pairs = linker.inference.predict(
            threshold_match_probability=max(0.5, min_match_prob - 0.2))
        pdf = pairs.as_pandas_dataframe()
    except Exception:
        return []

    if pdf is None or pdf.empty:
        return []
    prob_col = "match_probability" if "match_probability" in pdf.columns else None
    if prob_col is None:
        return []
    keep = pdf[pdf[prob_col] >= float(min_match_prob)]
    edges = []
    for a, b in zip(keep["unique_id_l"].astype(str), keep["unique_id_r"].astype(str)):
        na, nb = a.replace("npi:", ""), b.replace("npi:", "")
        if na and nb and na != nb:
            edges.append((na, nb))
    return edges


# --------------------------------------------------------------------------- #
# validation harness — the Vivo / CSI ground-truth gate
# --------------------------------------------------------------------------- #
def pairwise_prf(crosswalk, truth_clusters):
    """Pairwise precision / recall / F1 of the resolved clusters vs a labeled
    truth set, restricted to the NPIs named in the truth set.

    `crosswalk`      output of entity.make_crosswalk (needs legacy_npi, parent_key).
    `truth_clusters` list of sets/lists of NPIs that SHOULD share an operator.

    Returns dict(precision, recall, f1, tp, fp, fn, n_truth_npis). This is the
    entity layer's analogue of the recovery engine's measured hit rate: gate the
    Splink layer on reconstructing the Vivo/CSI roll-ups before trusting it.
    """
    out = {"precision": None, "recall": None, "f1": None,
           "tp": 0, "fp": 0, "fn": 0, "n_truth_npis": 0}
    if crosswalk is None or len(crosswalk) == 0 or not truth_clusters:
        return out
    key_col = "parent_key" if "parent_key" in crosswalk.columns else (
        "parent_operator" if "parent_operator" in crosswalk.columns else None)
    if key_col is None:
        return out
    assign = dict(zip(crosswalk["legacy_npi"].astype(str), crosswalk[key_col].astype(str)))

    truth_npis = sorted({str(n) for cl_ in truth_clusters for n in cl_ if str(n) in assign})
    out["n_truth_npis"] = len(truth_npis)
    if len(truth_npis) < 2:
        return out

    truth_same = set()
    for cl_ in truth_clusters:
        members = [str(n) for n in cl_ if str(n) in assign]
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                truth_same.add(frozenset((members[i], members[j])))

    tp = fp = fn = 0
    for i in range(len(truth_npis)):
        for j in range(i + 1, len(truth_npis)):
            a, b = truth_npis[i], truth_npis[j]
            pred_same = assign.get(a) == assign.get(b)
            is_same = frozenset((a, b)) in truth_same
            if pred_same and is_same:
                tp += 1
            elif pred_same and not is_same:
                fp += 1
            elif (not pred_same) and is_same:
                fn += 1
    prec = tp / (tp + fp) if (tp + fp) else None
    rec = tp / (tp + fn) if (tp + fn) else None
    f1 = (2 * prec * rec / (prec + rec)) if (prec and rec) else None
    out.update(precision=prec, recall=rec, f1=f1, tp=tp, fp=fp, fn=fn)
    return out
