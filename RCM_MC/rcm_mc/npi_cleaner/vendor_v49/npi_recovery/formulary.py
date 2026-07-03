"""formulary (v31): the "exclude by inclusion" gate on the common-name grouper.

Why this exists — how Curtis and Nick framed the cleanup on the sync:
    Curtis: "use the common name we have now and ensure it matches everything in
             their formulary. Then do the same for any drugs OUTSIDE the formulary
             that we care about, and keep any of those where the names match."
    Nick:   "so basically an exclude-by-inclusion — look for the non-matching, keep
             the ones we actually care about, and exclude everything else."
plus the spot-check Evan wanted:
    "look at the top therapeutic-area drugs and manually check if there are any
     Keytrudas that we need to remove."

The gate tags every row against the client formulary using the resolved common
name (so all of a molecule's J-codes and NDCs share one disposition), keeps the
formulary drugs plus an explicit keep-list of off-formulary drugs the team cares
about, and surfaces everything else for a decision. It NEVER drops silently — it
returns a disposition and a mask; the pipeline applies the filter only on an
explicit opt-in, and always emits the review list first (Evan's "let's talk about
it" bucket, top dollars first, so a Keytruda jumps straight out).

Statuses:
  IN_FORMULARY        common name is in the client formulary                keep
  KEEP_OFF_FORMULARY  off formulary but on the explicit keep-list           keep
  EXCLUDE_CONFIRMED   matched an explicit exclude term (oncology/chemo)      drop candidate
  EXCLUDE_REVIEW      off formulary, not kept, not an explicit exclude       review
  UNRESOLVED_REVIEW   drug not identified to a common name yet               review

Seed lives in reference/formulary_seed.csv. Drop the client's real formulary at
reference/*formulary*user*.csv (user rows extend/override). No LLM.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

from . import config
from . import rx_bridge as _rxb

KEEP_STATUSES = {"IN_FORMULARY", "KEEP_OFF_FORMULARY"}


def load_formulary(ref_dir=None):
    """Return {formulary:set, keep_off:set, exclude_tokens:list[(tok,note)],
    notes:dict}. Ingredient keys are normalized to the crosswalk convention.

    ref_dir may be a directory (the shipped seed plus any *formulary*user*.csv
    override in it are read) or an explicit CSV file (loaded as the override on
    top of the shipped seed)."""
    p = Path(ref_dir) if ref_dir else Path(config.REF_DIR)
    frames = []
    seed = Path(config.REF_DIR) / "formulary_seed.csv"
    if seed.exists():
        frames.append(pd.read_csv(seed, dtype=str).assign(_prio=0))
    if p.is_file():
        try:
            frames.append(pd.read_csv(p, dtype=str).assign(_prio=1))
        except Exception:
            pass
    elif p.is_dir():
        # an in-place seed in a custom dir takes base priority
        local_seed = p / "formulary_seed.csv"
        if local_seed.exists() and local_seed != seed:
            frames.append(pd.read_csv(local_seed, dtype=str).assign(_prio=0))
        for extra in sorted(p.glob("*formulary*user*.csv")):
            try:
                frames.append(pd.read_csv(extra, dtype=str).assign(_prio=1))
            except Exception:
                pass
    formulary, keep_off, exclude = set(), set(), []
    notes = {}
    if not frames:
        return {"formulary": formulary, "keep_off": keep_off,
                "exclude_tokens": exclude, "notes": notes}
    df = pd.concat(frames, ignore_index=True).fillna("").sort_values("_prio")
    for _, r in df.iterrows():
        key = _rxb._norm(r.get("key", ""))
        kind = str(r.get("kind", "ingredient")).strip().lower()
        disp = str(r.get("disposition", "")).strip().lower()
        note = str(r.get("note", ""))
        if not key:
            continue
        if disp == "in_formulary":
            formulary.add(key)
            notes.setdefault(key, note)
        elif disp == "keep_off_formulary":
            keep_off.add(key)
            notes.setdefault(key, note)
        elif disp == "exclude":
            if kind == "token":
                exclude.append((key, note))
            else:
                exclude.append((key, note))
    return {"formulary": formulary, "keep_off": keep_off,
            "exclude_tokens": exclude, "notes": notes}


def _name_matches_exclude(name_norm, key_norm, exclude_tokens):
    for tok, note in exclude_tokens:
        if not tok:
            continue
        if tok == key_norm:
            return note or tok
        if re.search(r"\b" + re.escape(tok) + r"\b", name_norm):
            return note or tok
    return ""


def _name_matches_set(name_norm, key_norm, token_set):
    """True if the resolved key is in the set, or any set token appears as a
    whole word in the free-text name. Lets OPAT antibiotics and other drugs that
    fall back to a name:: key still match the keep-list / formulary by token."""
    if key_norm and key_norm in token_set:
        return True
    for tok in token_set:
        if tok and re.search(r"\b" + re.escape(tok) + r"\b", name_norm):
            return True
    return False


def assign_formulary_disposition(std_named: pd.DataFrame, formulary=None,
                                 ref_dir=None) -> pd.DataFrame:
    """Add `formulary_status` and `_formulary_reason` using the resolved common
    key (falling back to a drug-name token scan for unresolved rows). Additive
    only — no rows dropped here."""
    F = formulary or load_formulary(ref_dir)
    out = std_named.copy()
    n = len(out)
    key = (out["drug_common_key"].astype("string").fillna("")
           if "drug_common_key" in out.columns else pd.Series([""] * n))
    name = (out["drug_common_name"].astype("string").fillna("")
            if "drug_common_name" in out.columns else pd.Series([""] * n))
    dn = (out["drug_name"].astype("string").fillna("")
          if "drug_name" in out.columns else pd.Series([""] * n))

    status = np.array(["EXCLUDE_REVIEW"] * n, dtype=object)
    reason = np.array([""] * n, dtype=object)
    for i in range(n):
        ky = str(key.iat[i]).strip()
        nm_norm = _rxb._norm(str(name.iat[i]) + " " + str(dn.iat[i]))
        # explicit exclude first (a Keytruda is a Keytruda even if 'in formulary'
        # somewhere by accident)
        exnote = _name_matches_exclude(nm_norm, ky, F["exclude_tokens"])
        if exnote:
            status[i] = "EXCLUDE_CONFIRMED"
            reason[i] = f"explicit exclude: {exnote}"
            continue
        if _name_matches_set(nm_norm, ky, F["formulary"]):
            status[i] = "IN_FORMULARY"
            reason[i] = F["notes"].get(ky, "in client formulary")
            continue
        if _name_matches_set(nm_norm, ky, F["keep_off"]):
            status[i] = "KEEP_OFF_FORMULARY"
            reason[i] = F["notes"].get(ky, "off formulary; on keep-list")
            continue
        # unresolved drug (no common key) -> review, distinct from a resolved
        # off-formulary drug so the two are triaged differently
        if not ky or ky.startswith("name::") or ky.startswith("hcpcs::"):
            status[i] = "UNRESOLVED_REVIEW"
            reason[i] = "drug not identified to a common name — resolve then re-gate"
        else:
            status[i] = "EXCLUDE_REVIEW"
            reason[i] = "off formulary and not on the keep-list"
    out["formulary_status"] = status
    out["_formulary_reason"] = reason
    return out


def formulary_gate_summary(std_tagged: pd.DataFrame, allowed: pd.Series | None = None) -> pd.DataFrame:
    """Disposition table: per common name x status, rows and dollars, so the team
    sees exactly what stays vs what is up for exclusion. Keep vs drop is totalled."""
    if "formulary_status" not in std_tagged.columns:
        return pd.DataFrame({"note": ["run assign_formulary_disposition first"]})
    a = (pd.to_numeric(allowed, errors="coerce").fillna(0.0) if allowed is not None
         else pd.to_numeric(std_tagged.get("allowed_amt"), errors="coerce").fillna(0.0))
    name = (std_tagged["drug_common_name"].astype("string").fillna("(unresolved)")
            if "drug_common_name" in std_tagged.columns else pd.Series("(unresolved)", index=std_tagged.index))
    df = pd.DataFrame({"name": name.values, "status": std_tagged["formulary_status"].values, "a": a.values})
    g = (df.groupby(["status", "name"]).agg(rows=("a", "size"), allowed=("a", "sum"))
         .reset_index().sort_values(["status", "allowed"], ascending=[True, False]))
    g["allowed"] = g["allowed"].round(2)
    keep = df[df["status"].isin(KEEP_STATUSES)]["a"].sum()
    drop = df[df["status"] == "EXCLUDE_CONFIRMED"]["a"].sum()
    review = df[df["status"].isin({"EXCLUDE_REVIEW", "UNRESOLVED_REVIEW"})]["a"].sum()
    tot = pd.DataFrame([
        {"status": "== KEEP (formulary + keep-list)", "name": "", "rows": int((df["status"].isin(KEEP_STATUSES)).sum()), "allowed": round(float(keep), 2)},
        {"status": "== EXCLUDE (confirmed)", "name": "", "rows": int((df["status"] == "EXCLUDE_CONFIRMED").sum()), "allowed": round(float(drop), 2)},
        {"status": "== REVIEW (decide)", "name": "", "rows": int((df["status"].isin({"EXCLUDE_REVIEW", "UNRESOLVED_REVIEW"})).sum()), "allowed": round(float(review), 2)},
    ])
    out = pd.concat([g, tot], ignore_index=True)
    out.attrs["note"] = ("Exclude-by-inclusion. KEEP = client formulary + explicit keep-list; "
                         "EXCLUDE_CONFIRMED = matched an exclude term (oncology/chemo); REVIEW = off "
                         "formulary and not kept, or not yet resolved to a drug. Nothing is dropped "
                         "unless the gate is applied on purpose.")
    return out


def formulary_exclusions_review(std_tagged: pd.DataFrame, allowed: pd.Series | None = None,
                                top_n: int = 100) -> pd.DataFrame:
    """The 'let's talk about it' list: every drug that would be excluded or needs
    review, ranked by dollars, so a large out-of-scope drug (a Keytruda) is the
    first thing on the page."""
    if "formulary_status" not in std_tagged.columns:
        return pd.DataFrame({"note": ["run assign_formulary_disposition first"]})
    a = (pd.to_numeric(allowed, errors="coerce").fillna(0.0) if allowed is not None
         else pd.to_numeric(std_tagged.get("allowed_amt"), errors="coerce").fillna(0.0))
    df = std_tagged.assign(_a=a.values)
    flagged = df[df["formulary_status"].isin({"EXCLUDE_CONFIRMED", "EXCLUDE_REVIEW", "UNRESOLVED_REVIEW"})]
    if flagged.empty:
        return pd.DataFrame({"note": ["nothing flagged for exclusion or review — everything maps to the formulary or keep-list"]})
    nm = (flagged["drug_common_name"].astype("string").fillna("")
          if "drug_common_name" in flagged.columns else pd.Series("", index=flagged.index))
    dn = (flagged["drug_name"].astype("string").fillna("")
          if "drug_name" in flagged.columns else pd.Series("", index=flagged.index))
    hc = (flagged["hcpcs"].astype("string").fillna("")
          if "hcpcs" in flagged.columns else pd.Series("", index=flagged.index))
    label = nm.where(nm.ne("") & nm.ne("(unresolved drug)"), dn)
    g = (flagged.assign(_label=label.values, _hc=hc.values)
         .groupby(["formulary_status", "_label", "_formulary_reason"])
         .agg(rows=("_a", "size"), allowed=("_a", "sum"),
              example_codes=("_hc", lambda s: ", ".join(sorted({x for x in s if x})[:6])))
         .reset_index().sort_values("allowed", ascending=False)
         .rename(columns={"_label": "drug", "_formulary_reason": "reason"}))
    g["allowed"] = g["allowed"].round(2)
    if top_n and len(g) > top_n:
        g = g.head(top_n)
    g.attrs["note"] = ("Top-dollar first. EXCLUDE_CONFIRMED can be dropped; EXCLUDE_REVIEW and "
                       "UNRESOLVED_REVIEW are judgement calls — confirm before removing. This is the "
                       "sheet to scan for a stray oncology drug in an infusion book.")
    return g


def apply_gate(std_tagged: pd.DataFrame, *, keep_statuses=None, drop_confirmed_only=True):
    """Return (kept_frame, dropped_audit). ONLY call on an explicit opt-in.

    drop_confirmed_only=True (default) drops just EXCLUDE_CONFIRMED and keeps
    everything else (the conservative default: never lose a row that a human has
    not signed off). Set False and pass keep_statuses to enforce a stricter gate.
    """
    if "formulary_status" not in std_tagged.columns:
        return std_tagged, pd.DataFrame({"note": ["run assign_formulary_disposition first"]})
    st = std_tagged["formulary_status"].astype("string")
    if drop_confirmed_only:
        drop_mask = st == "EXCLUDE_CONFIRMED"
    else:
        keep = keep_statuses or KEEP_STATUSES
        drop_mask = ~st.isin(set(keep))
    dropped = std_tagged[drop_mask]
    kept = std_tagged[~drop_mask]
    return kept, dropped
