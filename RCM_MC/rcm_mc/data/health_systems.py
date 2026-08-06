"""Health-system master mapping — which system each hospital belongs to.

Why this module exists
----------------------
HCRIS gives us 6,123 facilities keyed by CCN (``data/hcris.py``) with
beds, payer mix and financials — and **no parent-system column**. CMS
does not publish one. Every hospital surface in the app therefore reads
the universe as 6,123 unrelated rows, which is not how a partner thinks
about it: they think "how many hospitals does Ascension run, how many of
them are behavioral, and which states". Answering that question meant
hand-counting off a screener export every time.

This module is the single place that answers it. It carries a curated
registry of US health systems, matches HCRIS facility names to that
registry, and rolls the result up to one row per system with hospital
counts, bed counts, state footprint and a facility-type mix (acute /
critical access / **behavioral** / rehab / LTACH / children's).

How the match works — and what it is not
----------------------------------------
Assignment is **name-based**, because the name is the only ownership
signal HCRIS carries. Each :class:`SystemDef` lists the brand strings
that appear in HCRIS names (including the abbreviations HCRIS itself
uses — ``SSH -`` for Select Specialty, ``KFH -`` for Kaiser Foundation
Hospitals, ``UH `` for University Hospitals). Where a brand is ambiguous
across unrelated systems — MERCY, BAPTIST, METHODIST, SAINT LUKE'S,
AURORA all name two or more unrelated organizations — the entry is
scoped with ``states`` so the match cannot leak across the country.

Consequences a reader must hold onto:

  - A hospital owned by a system but carrying a purely local name (much
    of Community Health Systems, Tenet and Steward) lands in
    **Independent / Unmapped**. Unmapped is "the name doesn't say", not
    "independent" — the page labels it that way.
  - Match precision is protected by ``states`` scoping and the
    longest-pattern-wins rule, so a wrong system is much less likely
    than a missing one. The mapping under-claims by design.
  - Every assigned row carries ``system_match`` (the pattern that fired)
    so any count on the page can be traced back to why a facility was
    pulled into a system.

Facility type comes from ``hcris._classify_series`` (CCN range first,
name keywords as fallback) — the same classifier the screeners use, so
"behavioral" means the same thing here as everywhere else. Behavioral
additionally catches name signals (BEHAVIORAL / PSYCH / BH / MENTAL
HEALTH) on facilities whose CCN range says otherwise, because a
psychiatric unit filed under a general CCN still reads as behavioral to
a partner screening the space.

Public API::

    assign_systems(df=None)   -> DataFrame (universe + system columns)
    build_system_map(df=None) -> HealthSystemMap (rollup, cached)
    system_hospitals(system_id, df=None) -> DataFrame
    candidate_clusters(df=None) -> list[CandidateCluster]
    registry_size() -> int
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from .hcris import _classify_series, _get_latest_per_ccn

# ── Vocabulary ─────────────────────────────────────────────────────
#
# ``kind`` is the ownership model a partner underwrites against (a
# for-profit chain and a Catholic non-profit price and behave
# differently). ``focus`` is what the system actually operates — the
# facet that answers "show me the behavioral platforms".

KIND_FOR_PROFIT = "For-Profit"
KIND_NONPROFIT = "Non-Profit"
KIND_CATHOLIC = "Catholic Non-Profit"
KIND_ACADEMIC = "Academic"
KIND_GOVERNMENT = "Government"

FOCUS_ACUTE = "Acute"
FOCUS_BEHAVIORAL = "Behavioral"
FOCUS_REHAB = "Rehab"
FOCUS_LTACH = "LTACH"
FOCUS_CHILDRENS = "Children's"
FOCUS_MIXED = "Mixed"

# Facility-type labels as emitted by ``hcris._classify_series``.
TYPE_LABELS: Tuple[str, ...] = (
    "general", "critical_access", "psychiatric", "rehab",
    "ltach", "children", "other",
)

# Partner-facing names for those labels — the table headers.
TYPE_DISPLAY: Dict[str, str] = {
    "general": "Acute",
    "critical_access": "Critical Access",
    "psychiatric": "Behavioral",
    "rehab": "Rehab",
    "ltach": "LTACH",
    "children": "Children's",
    "other": "Other",
}


@dataclass(frozen=True)
class SystemDef:
    """One health system in the registry.

    ``patterns`` are normalized name fragments (see :func:`normalize_name`
    — upper-cased, punctuation stripped, ``ST``/``ST.`` expanded to
    ``SAINT``, ``&`` to ``AND``). A leading ``^`` anchors the pattern to
    the start of the facility name, which is how brands that are common
    words elsewhere (MERCY, TRINITY, MEMORIAL) stay precise.

    ``states`` restricts a pattern to a footprint. Required for every
    brand that names more than one unrelated organization; without it a
    Kentucky Baptist hospital gets counted into Baptist Health South
    Florida and the hospital count silently lies.
    """

    system_id: str
    name: str
    kind: str
    focus: str
    hq_state: str
    patterns: Tuple[str, ...]
    states: Tuple[str, ...] = ()
    exclude: Tuple[str, ...] = ()
    note: str = ""


# ── The registry ───────────────────────────────────────────────────
#
# Ordered roughly by hospital count. Entries earn their place by having
# a brand that actually appears in HCRIS facility names; a system whose
# hospitals all carry local names (much of CHS / Tenet / Steward) cannot
# be mapped from this data source and is deliberately absent rather than
# guessed at. Adding one is a one-line append — the rollup, the page and
# the coverage numbers all derive from this tuple.

SYSTEM_REGISTRY: Tuple[SystemDef, ...] = (
    # ── National for-profit acute chains ───────────────────────────
    SystemDef(
        "hca", "HCA Healthcare", KIND_FOR_PROFIT, FOCUS_ACUTE, "TN",
        patterns=(
            "^HCA", "^TRISTAR", "^MEDICAL CITY", "^SAINT DAVIDS",
            "^PARKRIDGE", "^RESEARCH MEDICAL CENTER", "^MENORAH MEDICAL",
            "^OVERLAND PARK REGIONAL", "^WESLEY MEDICAL CENTER",
            "^SUNRISE HOSPITAL", "^MOUNTAINVIEW HOSPITAL",
            "^SOUTHERN HILLS HOSPITAL",
            # MountainStar (Utah division) — local brands, state-scoped.
            "UT:^OGDEN REGIONAL", "UT:^SAINT MARKS HOSPITAL",
            "UT:^LONE PEAK HOSPITAL", "UT:^TIMPANOGOS REGIONAL",
            "UT:^BRIGHAM CITY COMMUNITY", "UT:^MOUNTAIN VIEW HOSPITAL",
            "UT:^CACHE VALLEY", "UT:^LAKEVIEW HOSPITAL",
            # Divisions that never carry the HCA name.
            "VA:^LEWISGALE", "TX:^CORPUS CHRISTI MEDICAL", "TX:^RIO GRANDE REGIONAL",
            "TX:^ROUND ROCK MEDICAL", "CO:^THE MEDICAL CENTER OF AURORA",
            "CO:^MEDICAL CENTER OF AURORA",
        ),
        note="Largest US for-profit operator; many facilities rebranded "
             "to the HCA / Medical City / TriStar house brands.",
    ),
    SystemDef(
        "tenet", "Tenet Healthcare", KIND_FOR_PROFIT, FOCUS_ACUTE, "TX",
        patterns=("^THE HOSPITALS OF PROVIDENCE", "^HOSPITALS OF PROVIDENCE",
                  "MI:^DETROIT RECEIVING", "MI:^HARPER UNIVERSITY",
                  "MI:^SINAI GRACE", "MI:^DETROIT MEDICAL CENTER",
                  "AZ:^CARONDELET", "TX:^VALLEY BAPTIST", "TN:^SAINT FRANCIS"),
        note="Tenet keeps acquired local names almost everywhere; only the "
             "explicitly branded facilities are reachable from HCRIS names.",
    ),
    SystemDef(
        "ardent", "Ardent Health Services", KIND_FOR_PROFIT, FOCUS_ACUTE, "TN",
        patterns=("OK:^HILLCREST HOSPITAL", "OK:^HILLCREST MEDICAL",
                  "NM:^LOVELACE", "^BSA HOSPITAL"),
    ),
    SystemDef(
        "prime", "Prime Healthcare", KIND_FOR_PROFIT, FOCUS_ACUTE, "CA",
        patterns=("^PRIME HEALTHCARE", "CA:^GARDEN GROVE HOSPITAL",
                  "CA:^SHASTA REGIONAL", "CA:^WEST ANAHEIM", "CA:^LA PALMA",
                  "CA:^HUNTINGTON BEACH HOSPITAL", "CA:^CENTINELA",
                  "CA:^CHINO VALLEY MEDICAL", "CA:^MONTCLAIR HOSPITAL",
                  "CA:^SHERMAN OAKS HOSPITAL", "CA:^SAN DIMAS COMMUNITY"),
    ),
    SystemDef(
        "uhs", "Universal Health Services", KIND_FOR_PROFIT, FOCUS_BEHAVIORAL, "PA",
        patterns=("^UHS ", "^UBH ", "UNIVERSAL HEALTH SERVICES",
                  "TX:^SOUTH TEXAS HEALTH", "TX:^DOCTORS HOSPITAL OF LAREDO",
                  "NV:^NORTHERN NEVADA MEDICAL", "NV:^NORTHERN NEVADA SIERRA"),
        note="UHS runs the largest US behavioral estate; HCRIS carries "
             "several of them under the UHS / UBH abbreviations.",
    ),

    # ── Post-acute / specialty platforms ───────────────────────────
    SystemDef(
        "encompass", "Encompass Health", KIND_FOR_PROFIT, FOCUS_REHAB, "AL",
        patterns=("^ENCOMPASS",),
        note="Largest US inpatient-rehab operator — the single biggest "
             "name-matched system in the HCRIS universe.",
    ),
    SystemDef(
        "select_medical", "Select Medical", KIND_FOR_PROFIT, FOCUS_LTACH, "PA",
        patterns=("^SSH ", "^SELECT SPECIALTY", "^SELECT REHAB", "^REGENCY HOSPITAL"),
        note="HCRIS abbreviates Select Specialty Hospital to 'SSH - <city>'.",
    ),
    SystemDef(
        "kindred", "ScionHealth / Kindred", KIND_FOR_PROFIT, FOCUS_LTACH, "KY",
        patterns=("^KINDRED", "^SCIONHEALTH"),
    ),
    SystemDef(
        "pam", "PAM Health", KIND_FOR_PROFIT, FOCUS_LTACH, "TX",
        patterns=("^PAM ", "TX:^POST ACUTE MEDICAL", "TX:^WARM SPRINGS"),
    ),
    SystemDef(
        "vibra", "Vibra Healthcare", KIND_FOR_PROFIT, FOCUS_LTACH, "PA",
        patterns=("^VIBRA",),
    ),
    SystemDef(
        "cornerstone", "Cornerstone Healthcare Group", KIND_FOR_PROFIT, FOCUS_LTACH, "TX",
        patterns=("^CORNERSTONE SPECIALTY", "^CORNERSTONE BH", "^CORNERSTONE HOSPITAL"),
    ),
    SystemDef(
        "ernest", "Ernest Health", KIND_FOR_PROFIT, FOCUS_REHAB, "NM",
        patterns=("^REHABILITATION HOSPITAL OF",),
        note="Ernest operates under 'Rehabilitation Hospital of <place>' "
             "naming; the pattern is anchored so it cannot swallow the "
             "generic rehab long tail.",
    ),
    SystemDef(
        "shriners", "Shriners Children's", KIND_NONPROFIT, FOCUS_CHILDRENS, "FL",
        patterns=("^SHRINERS",),
    ),

    # ── Behavioral platforms ───────────────────────────────────────
    SystemDef(
        "acadia", "Acadia Healthcare", KIND_FOR_PROFIT, FOCUS_BEHAVIORAL, "TN",
        patterns=("^ACADIA",),
    ),
    SystemDef(
        "oceans", "Oceans Healthcare", KIND_FOR_PROFIT, FOCUS_BEHAVIORAL, "LA",
        patterns=("^OCEANS",),
    ),
    SystemDef(
        "haven_bh", "Haven Behavioral Healthcare", KIND_FOR_PROFIT, FOCUS_BEHAVIORAL, "TN",
        patterns=("^HAVEN BEHAVIORAL",),
    ),
    SystemDef(
        "signature_bh", "Signature Healthcare Services", KIND_FOR_PROFIT, FOCUS_BEHAVIORAL, "CA",
        patterns=("^AURORA BEHAVIORAL", "^AURORA SAN DIEGO", "^AURORA CHARTER OAK"),
        note="Trades as Aurora Behavioral Health — state-scoped away "
             "from Advocate Aurora in Wisconsin by the pattern itself.",
    ),
    SystemDef(
        "rogers_bh", "Rogers Behavioral Health", KIND_NONPROFIT, FOCUS_BEHAVIORAL, "WI",
        patterns=("^ROGERS MEMORIAL", "^ROGERS BEHAVIORAL"),
    ),
    SystemDef(
        "sheppard_pratt", "Sheppard Pratt", KIND_NONPROFIT, FOCUS_BEHAVIORAL, "MD",
        patterns=("^SHEPPARD PRATT", "^SHEPPARD AND ENOCH"),
    ),
    SystemDef(
        "brattleboro", "Brattleboro Retreat", KIND_NONPROFIT, FOCUS_BEHAVIORAL, "VT",
        patterns=("^BRATTLEBORO RETREAT",),
    ),

    # ── National Catholic / faith-based systems ────────────────────
    SystemDef(
        "ascension", "Ascension", KIND_CATHOLIC, FOCUS_ACUTE, "MO",
        patterns=("^ASCENSION", "TN:^SAINT THOMAS", "IL:^PRESENCE",
                  "AL:^SAINT VINCENTS", "KS:^VIA CHRISTI", "OK:^SAINT JOHN",
                  "MI:^SAINT JOHN HOSPITAL", "IL:^ALEXIAN BROTHERS"),
        note="Many Ascension facilities still file under the legacy "
             "Saint Thomas / Presence / Via Christi brands.",
    ),
    SystemDef(
        "commonspirit", "CommonSpirit Health", KIND_CATHOLIC, FOCUS_ACUTE, "IL",
        patterns=(
            "^CHI ", "^CHI-", "^CATHOLIC HEALTH INITIATIVES", "^COMMONSPIRIT",
            "^CENTURA", "^DIGNITY HEALTH", "^MERCY HOSPITAL AND MEDICAL CENTER",
            "KY:^SAINT JOSEPH", "KY:^FLAGET MEMORIAL", "AR:^SAINT VINCENT",
            "TX:^SAINT LUKES", "NV:^SAINT ROSE DOMINICAN", "CA:^MERCY MEDICAL CENTER",
            "CA:^SAINT FRANCIS MEMORIAL", "CA:^METHODIST HOSPITAL OF SACRAMENTO",
        ),
        note="CHI + Dignity + Centura merged into CommonSpirit; HCRIS "
             "names still carry all three legacy brands.",
    ),
    SystemDef(
        "trinity", "Trinity Health", KIND_CATHOLIC, FOCUS_ACUTE, "MI",
        patterns=(
            "^TRINITY HEALTH", "^MERCYONE", "^SAINT JOSEPH MERCY",
            "^SAINT MARY MERCY", "^LOYOLA", "^GOTTLIEB", "^SAINT ALPHONSUS",
            "^MERCY HEALTH MUSKEGON", "OH:^MOUNT CARMEL",
            "IN:^SAINT JOSEPHS REG", "GA:^SAINT MARYS",
            "NY:^SAINT JOSEPHS HOSPITAL HEALTH", "MD:^HOLY CROSS",
            "IA:^MERCY MEDICAL CENTER DES", "IA:^MERCY MEDICAL CENTER NEW HAM",
        ),
        note="Bare '^TRINITY' is NOT a pattern here — Trinity Rock Island / "
             "Muscatine / Bettendorf are UnityPoint, and Trinity Hospital "
             "(CA) and Trinity Hospitals (ND) are unrelated again.",
    ),
    SystemDef(
        "chr_christus", "CHRISTUS Health", KIND_CATHOLIC, FOCUS_ACUTE, "TX",
        patterns=("^CHRISTUS",),
    ),
    SystemDef(
        "ssm", "SSM Health", KIND_CATHOLIC, FOCUS_ACUTE, "MO",
        patterns=("^SSM ", "^SSM-", "OK:^SAINT ANTHONY"),
    ),
    SystemDef(
        "mercy_mo", "Mercy (Chesterfield)", KIND_CATHOLIC, FOCUS_ACUTE, "MO",
        patterns=("^MERCY",),
        states=("MO", "AR", "OK", "KS"),
        note="Four-state Mercy footprint. MERCY is the single most "
             "over-loaded brand in HCRIS (77 facilities across at least "
             "six unrelated owners) — hence the hard state scope.",
    ),
    SystemDef(
        "bon_secours", "Bon Secours Mercy Health", KIND_CATHOLIC, FOCUS_ACUTE, "OH",
        patterns=("^BON SECOURS", "^MERCY HEALTH", "^MERCY ",
                  "OH:^SAINT ELIZABETH", "OH:^SAINT VINCENT MEDICAL"),
        states=("OH", "KY", "VA", "SC"),
    ),
    SystemDef(
        "providence", "Providence", KIND_CATHOLIC, FOCUS_ACUTE, "WA",
        patterns=("^PROVIDENCE", "^SWEDISH MEDICAL", "^KADLEC", "^COVENANT HEALTH"),
        states=("WA", "OR", "CA", "AK", "MT", "TX", "NM"),
    ),
    SystemDef(
        "franciscan", "Franciscan Health", KIND_CATHOLIC, FOCUS_ACUTE, "IN",
        patterns=("^FRANCISCAN",),
        states=("IN", "IL"),
    ),
    SystemDef(
        "hshs", "Hospital Sisters Health System", KIND_CATHOLIC, FOCUS_ACUTE, "IL",
        patterns=("^HSHS",),
    ),
    SystemDef(
        "avera", "Avera Health", KIND_CATHOLIC, FOCUS_ACUTE, "SD",
        patterns=("^AVERA",),
    ),
    SystemDef(
        "adventhealth", "AdventHealth", KIND_NONPROFIT, FOCUS_ACUTE, "FL",
        patterns=("^ADVENTHEALTH", "^ADVENTIST HEALTH SYSTEM"),
    ),
    SystemDef(
        "adventist_health", "Adventist Health", KIND_NONPROFIT, FOCUS_ACUTE, "CA",
        patterns=("^ADVENTIST HEALTH",),
        states=("CA", "OR", "WA", "HI"),
    ),
    SystemDef(
        "adventist_md", "Adventist HealthCare", KIND_NONPROFIT, FOCUS_ACUTE, "MD",
        patterns=("^ADVENTIST", "^AHC "),
        states=("MD",),
    ),

    # ── Large non-profit / regional systems ────────────────────────
    SystemDef(
        "kaiser", "Kaiser Permanente", KIND_NONPROFIT, FOCUS_ACUTE, "CA",
        patterns=("^KFH ", "^KFH-", "^KAISER"),
        note="HCRIS files Kaiser Foundation Hospitals as 'KFH - <city>'.",
    ),
    SystemDef(
        "sanford", "Sanford Health", KIND_NONPROFIT, FOCUS_ACUTE, "SD",
        patterns=("^SANFORD",),
    ),
    SystemDef(
        "banner", "Banner Health", KIND_NONPROFIT, FOCUS_ACUTE, "AZ",
        patterns=("^BANNER",),
    ),
    SystemDef(
        "advocate", "Advocate Health", KIND_NONPROFIT, FOCUS_ACUTE, "NC",
        patterns=("^ADVOCATE", "^AURORA", "^ATRIUM", "NC:^NORTH CAROLINA BAPTIST",
                  "NC:^WAKE FOREST"),
        states=("IL", "WI", "NC", "SC", "GA", "AL"),
        note="Advocate Aurora + Atrium Health combination.",
    ),
    SystemDef(
        "baylor", "Baylor Scott & White Health", KIND_NONPROFIT, FOCUS_ACUTE, "TX",
        patterns=("^BAYLOR SCOTT", "^BAYLOR", "^SCOTT AND WHITE"),
        states=("TX",),
        exclude=("BAYLOR COLLEGE",),
    ),
    SystemDef(
        "texas_health", "Texas Health Resources", KIND_NONPROFIT, FOCUS_ACUTE, "TX",
        patterns=("^TEXAS HEALTH", "^TX HLTH"),
        states=("TX",),
    ),
    SystemDef(
        "memorial_hermann", "Memorial Hermann Health System", KIND_NONPROFIT, FOCUS_ACUTE, "TX",
        patterns=("^MEMORIAL HERMANN",),
    ),
    SystemDef(
        "houston_methodist", "Houston Methodist", KIND_NONPROFIT, FOCUS_ACUTE, "TX",
        patterns=("^HOUSTON METHODIST",),
    ),
    SystemDef(
        "methodist_dallas", "Methodist Health System (Dallas)", KIND_NONPROFIT, FOCUS_ACUTE, "TX",
        patterns=("^METHODIST ",),
        states=("TX",),
        exclude=("HOUSTON METHODIST",),
    ),
    SystemDef(
        "methodist_lebonheur", "Methodist Le Bonheur Healthcare", KIND_NONPROFIT, FOCUS_ACUTE, "TN",
        patterns=("^METHODIST", "^LE BONHEUR"),
        states=("TN",),
    ),
    SystemDef(
        "nebraska_methodist", "Methodist Health System (Nebraska)", KIND_NONPROFIT, FOCUS_ACUTE, "NE",
        patterns=("^METHODIST", "^NEBRASKA METHODIST"),
        states=("NE",),
    ),
    SystemDef(
        "indiana_methodist", "Indiana University Health", KIND_ACADEMIC, FOCUS_ACUTE, "IN",
        patterns=("^INDIANA UNIVERSITY HEALTH", "^IU HEALTH"),
    ),
    SystemDef(
        "sutter", "Sutter Health", KIND_NONPROFIT, FOCUS_ACUTE, "CA",
        patterns=("^SUTTER", "^CALIFORNIA PACIFIC MEDICAL", "^ALTA BATES"),
        states=("CA",),
    ),
    SystemDef(
        "scripps", "Scripps Health", KIND_NONPROFIT, FOCUS_ACUTE, "CA",
        patterns=("^SCRIPPS",),
    ),
    SystemDef(
        "sharp", "Sharp HealthCare", KIND_NONPROFIT, FOCUS_ACUTE, "CA",
        patterns=("^SHARP",),
        states=("CA",),
    ),
    SystemDef(
        "cedars", "Cedars-Sinai", KIND_NONPROFIT, FOCUS_ACUTE, "CA",
        patterns=("^CEDARS",),
    ),
    SystemDef(
        "memorialcare", "MemorialCare", KIND_NONPROFIT, FOCUS_ACUTE, "CA",
        patterns=("^MEMORIALCARE",),
    ),
    SystemDef(
        "intermountain", "Intermountain Health", KIND_NONPROFIT, FOCUS_ACUTE, "UT",
        patterns=(
            "^INTERMOUNTAIN", "^SAINT VINCENT HEALTHCARE",
            "^GOOD SAMARITAN MEDICAL CENTER",
            # Utah roster — Intermountain names its hospitals for the
            # valley they sit in, so the brand never appears in HCRIS.
            "UT:^UTAH VALLEY HOSPITAL", "UT:^MCKAY DEE", "UT:^LDS HOSPITAL",
            "UT:^CEDAR CITY HOSPITAL", "UT:^LOGAN REGIONAL",
            "UT:^AMERICAN FORK HOSPITAL", "UT:^ALTA VIEW", "UT:^RIVERTON HOSPITAL",
            "UT:^PARK CITY HOSPITAL", "UT:^LAYTON HOSPITAL",
            "UT:^SPANISH FORK HOSPITAL", "UT:^OREM COMMUNITY",
            "UT:^DELTA COMMUNITY", "UT:^FILLMORE COMMUNITY",
            "UT:^SANPETE VALLEY", "UT:^SEVIER VALLEY", "UT:^GARFIELD MEMORIAL",
            "UT:^HEBER VALLEY", "UT:^BEAR RIVER VALLEY",
            "UT:^SAINT GEORGE REGIONAL", "UT:^PRIMARY CHILDRENS",
            "ID:^CASSIA REGIONAL",
        ),
        states=("UT", "ID", "NV", "CO", "MT", "WY", "KS"),
    ),
    SystemDef(
        "ochsner", "Ochsner Health", KIND_NONPROFIT, FOCUS_ACUTE, "LA",
        patterns=("^OCHSNER",),
    ),
    SystemDef(
        "piedmont", "Piedmont Healthcare", KIND_NONPROFIT, FOCUS_ACUTE, "GA",
        patterns=("^PIEDMONT",),
        states=("GA",),
    ),
    SystemDef(
        "wellstar", "Wellstar Health System", KIND_NONPROFIT, FOCUS_ACUTE, "GA",
        patterns=("^WELLSTAR", "GA:^KENNESTONE", "GA:^COBB HOSPITAL",
                  "GA:^SPALDING REGIONAL", "GA:^SYLVAN GROVE"),
    ),
    SystemDef(
        "northside", "Northside Hospital", KIND_NONPROFIT, FOCUS_ACUTE, "GA",
        patterns=("^NORTHSIDE HOSPITAL",),
        states=("GA",),
    ),
    SystemDef(
        "prisma", "Prisma Health", KIND_NONPROFIT, FOCUS_ACUTE, "SC",
        patterns=("^PRISMA", "SC:^PH "),
    ),
    SystemDef(
        "novant", "Novant Health", KIND_NONPROFIT, FOCUS_ACUTE, "NC",
        patterns=("^NOVANT", "NC:^PRESBYTERIAN HOSPITAL", "NC:^FORSYTH MEDICAL"),
    ),
    SystemDef(
        "unc", "UNC Health", KIND_ACADEMIC, FOCUS_ACUTE, "NC",
        patterns=("^UNC ", "^UNIVERSITY OF NORTH CAROLINA"),
    ),
    SystemDef(
        "duke", "Duke Health", KIND_ACADEMIC, FOCUS_ACUTE, "NC",
        patterns=("^DUKE",),
    ),
    SystemDef(
        "cone", "Cone Health", KIND_NONPROFIT, FOCUS_ACUTE, "NC",
        patterns=("^CONE HEALTH", "MOSES H CONE", "NC:^ALAMANCE REGIONAL"),
    ),
    SystemDef(
        "sentara", "Sentara Health", KIND_NONPROFIT, FOCUS_ACUTE, "VA",
        patterns=("^SENTARA",),
    ),
    SystemDef(
        "inova", "Inova Health System", KIND_NONPROFIT, FOCUS_ACUTE, "VA",
        patterns=("^INOVA",),
    ),
    SystemDef(
        "vcu", "VCU Health", KIND_ACADEMIC, FOCUS_ACUTE, "VA",
        patterns=("^VCU ", "^VIRGINIA COMMONWEALTH"),
    ),
    SystemDef(
        "medstar", "MedStar Health", KIND_NONPROFIT, FOCUS_ACUTE, "MD",
        patterns=("^MEDSTAR",),
    ),
    SystemDef(
        "hopkins", "Johns Hopkins Medicine", KIND_ACADEMIC, FOCUS_ACUTE, "MD",
        patterns=("^JOHNS HOPKINS", "^SUBURBAN HOSPITAL", "^SIBLEY MEMORIAL"),
    ),
    SystemDef(
        "lifebridge", "LifeBridge Health", KIND_NONPROFIT, FOCUS_ACUTE, "MD",
        patterns=("^LIFEBRIDGE", "^SINAI HOSPITAL OF BALTIMORE"),
    ),
    SystemDef(
        "umms", "University of Maryland Medical System", KIND_ACADEMIC, FOCUS_ACUTE, "MD",
        patterns=("^UNIVERSITY OF MARYLAND", "^UM ", "^UMMS"),
        states=("MD",),
    ),
    SystemDef(
        "christiana", "ChristianaCare", KIND_NONPROFIT, FOCUS_ACUTE, "DE",
        patterns=("^CHRISTIANA",),
    ),
    SystemDef(
        "nemours", "Nemours Children's Health", KIND_NONPROFIT, FOCUS_CHILDRENS, "FL",
        patterns=("^NEMOURS",),
    ),

    # ── Northeast ──────────────────────────────────────────────────
    SystemDef(
        "northwell", "Northwell Health", KIND_NONPROFIT, FOCUS_ACUTE, "NY",
        patterns=("^NORTHWELL", "^LONG ISLAND JEWISH", "^NORTH SHORE UNIVERSITY HOSPITAL",
                  "^LENOX HILL", "^STATEN ISLAND UNIVERSITY"),
        states=("NY",),
    ),
    SystemDef(
        "nyp", "NewYork-Presbyterian", KIND_ACADEMIC, FOCUS_ACUTE, "NY",
        patterns=("^NEW YORK PRESBYTERIAN", "^NEWYORK PRESBYTERIAN", "^NY PRESBYTERIAN"),
    ),
    SystemDef(
        "mount_sinai", "Mount Sinai Health System", KIND_ACADEMIC, FOCUS_ACUTE, "NY",
        patterns=("^MOUNT SINAI", "NY:^NEW YORK EYE AND EAR",
                  "NY:^THE NEW YORK GRACIE SQUARE", "NY:^NEW YORK GRACIE SQUARE"),
        states=("NY",),
    ),
    SystemDef(
        "nyu", "NYU Langone Health", KIND_ACADEMIC, FOCUS_ACUTE, "NY",
        patterns=("^NYU",),
    ),
    SystemDef(
        "montefiore", "Montefiore Health System", KIND_ACADEMIC, FOCUS_ACUTE, "NY",
        patterns=("^MONTEFIORE",),
    ),
    SystemDef(
        "nyc_h_h", "NYC Health + Hospitals", KIND_GOVERNMENT, FOCUS_ACUTE, "NY",
        patterns=("^NYC HEALTH", "^NEW YORK CITY HEALTH AND HOSPITALS"),
    ),
    SystemDef(
        "rochester_regional", "Rochester Regional Health", KIND_NONPROFIT, FOCUS_ACUTE, "NY",
        patterns=("^ROCHESTER GENERAL", "^ROCHESTER REGIONAL", "^UNITED MEMORIAL MEDICAL"),
        states=("NY",),
    ),
    SystemDef(
        "bassett", "Bassett Healthcare Network", KIND_NONPROFIT, FOCUS_ACUTE, "NY",
        patterns=("^BASSETT",),
    ),
    SystemDef(
        "mass_general_brigham", "Mass General Brigham", KIND_ACADEMIC, FOCUS_ACUTE, "MA",
        patterns=("^MASSACHUSETTS GENERAL", "^BRIGHAM AND WOMEN", "^NEWTON WELLESLEY",
                  "^SALEM HOSPITAL", "^COOLEY DICKINSON", "^MASS GENERAL"),
        states=("MA", "NH"),
    ),
    SystemDef(
        "beth_israel_lahey", "Beth Israel Lahey Health", KIND_ACADEMIC, FOCUS_ACUTE, "MA",
        patterns=("^BETH ISRAEL", "^LAHEY", "^MOUNT AUBURN", "^WINCHESTER HOSPITAL",
                  "MA:^NEW ENGLAND BAPTIST"),
        states=("MA",),
    ),
    SystemDef(
        "umass", "UMass Memorial Health", KIND_ACADEMIC, FOCUS_ACUTE, "MA",
        patterns=("^UMASS", "^UMASS MEMORIAL"),
    ),
    SystemDef(
        "baystate", "Baystate Health", KIND_NONPROFIT, FOCUS_ACUTE, "MA",
        patterns=("^BAYSTATE",),
    ),
    SystemDef(
        "yale", "Yale New Haven Health", KIND_ACADEMIC, FOCUS_ACUTE, "CT",
        patterns=("^YALE", "^BRIDGEPORT HOSPITAL", "^GREENWICH HOSPITAL", "^LAWRENCE AND MEMORIAL"),
        states=("CT", "RI"),
    ),
    SystemDef(
        "hartford", "Hartford HealthCare", KIND_NONPROFIT, FOCUS_ACUTE, "CT",
        patterns=("^HARTFORD HOSPITAL", "^HARTFORD HEALTHCARE", "^BACKUS", "^WINDHAM"),
        states=("CT",),
    ),
    SystemDef(
        "dartmouth", "Dartmouth Health", KIND_ACADEMIC, FOCUS_ACUTE, "NH",
        patterns=("^DARTMOUTH", "^MARY HITCHCOCK"),
    ),
    SystemDef(
        "maine_health", "MaineHealth", KIND_NONPROFIT, FOCUS_ACUTE, "ME",
        patterns=("^MAINE MEDICAL", "^MAINEHEALTH", "^MAINEGENERAL"),
        states=("ME",),
    ),
    SystemDef(
        "hackensack", "Hackensack Meridian Health", KIND_NONPROFIT, FOCUS_ACUTE, "NJ",
        patterns=("^HACKENSACK", "^JERSEY SHORE UNIVERSITY", "^OCEAN UNIVERSITY MEDICAL"),
        states=("NJ",),
    ),
    SystemDef(
        "rwjbarnabas", "RWJBarnabas Health", KIND_NONPROFIT, FOCUS_ACUTE, "NJ",
        patterns=("^ROBERT WOOD JOHNSON", "^RWJ", "^BARNABAS", "^NEWARK BETH ISRAEL",
                  "^COMMUNITY MEDICAL CENTER", "NJ:^MONMOUTH MEDICAL"),
        states=("NJ",),
    ),
    SystemDef(
        "atlantic_health", "Atlantic Health System", KIND_NONPROFIT, FOCUS_ACUTE, "NJ",
        patterns=("^MORRISTOWN MEDICAL", "^OVERLOOK MEDICAL", "^ATLANTIC HEALTH"),
        states=("NJ",),
    ),
    SystemDef(
        "virtua", "Virtua Health", KIND_NONPROFIT, FOCUS_ACUTE, "NJ",
        patterns=("^VIRTUA",),
    ),
    SystemDef(
        "upmc", "UPMC", KIND_ACADEMIC, FOCUS_ACUTE, "PA",
        patterns=("^UPMC",),
    ),
    SystemDef(
        "penn_medicine", "Penn Medicine", KIND_ACADEMIC, FOCUS_ACUTE, "PA",
        patterns=("^HOSPITAL OF THE UNIVERSITY OF PENNSYLVANIA", "^PENN PRESBYTERIAN",
                  "^PENNSYLVANIA HOSPITAL", "^LANCASTER GENERAL", "^CHESTER COUNTY HOSPITAL"),
        states=("PA", "NJ"),
    ),
    SystemDef(
        "jefferson", "Jefferson Health", KIND_ACADEMIC, FOCUS_ACUTE, "PA",
        patterns=("^JEFFERSON", "^THOMAS JEFFERSON", "^ABINGTON"),
        states=("PA", "NJ"),
    ),
    SystemDef(
        "temple", "Temple Health", KIND_ACADEMIC, FOCUS_ACUTE, "PA",
        patterns=("^TEMPLE",),
        states=("PA",),
    ),
    SystemDef(
        "geisinger", "Geisinger", KIND_NONPROFIT, FOCUS_ACUTE, "PA",
        patterns=("^GEISINGER",),
    ),
    SystemDef(
        "lehigh", "Lehigh Valley Health Network", KIND_NONPROFIT, FOCUS_ACUTE, "PA",
        patterns=("^LEHIGH VALLEY", "PA:^POCONO MEDICAL"),
    ),
    SystemDef(
        "st_lukes_pa", "St. Luke's University Health Network", KIND_NONPROFIT, FOCUS_ACUTE, "PA",
        patterns=("^SAINT LUKES",),
        states=("PA",),
    ),
    SystemDef(
        "wellspan", "WellSpan Health", KIND_NONPROFIT, FOCUS_ACUTE, "PA",
        patterns=("^WELLSPAN",),
    ),
    SystemDef(
        "ahn", "Allegheny Health Network", KIND_NONPROFIT, FOCUS_ACUTE, "PA",
        patterns=("^ALLEGHENY GENERAL", "^ALLEGHENY VALLEY", "^AHN ", "^FORBES HOSPITAL",
                  "^WEST PENN"),
        states=("PA",),
    ),
    SystemDef(
        "tower_health", "Tower Health", KIND_NONPROFIT, FOCUS_ACUTE, "PA",
        patterns=("^TOWER HEALTH", "^READING HOSPITAL", "^POTTSTOWN HOSPITAL"),
        states=("PA",),
    ),

    # ── Midwest ────────────────────────────────────────────────────
    SystemDef(
        "cleveland_clinic", "Cleveland Clinic", KIND_ACADEMIC, FOCUS_ACUTE, "OH",
        patterns=("^CLEVELAND CLINIC", "^FAIRVIEW HOSPITAL", "^HILLCREST HOSPITAL",
                  "^MARYMOUNT HOSPITAL", "^LUTHERAN HOSPITAL"),
        states=("OH", "FL"),
    ),
    SystemDef(
        "uh_ohio", "University Hospitals (Ohio)", KIND_ACADEMIC, FOCUS_ACUTE, "OH",
        patterns=("^UH ",),
        states=("OH",),
    ),
    SystemDef(
        "ohiohealth", "OhioHealth", KIND_NONPROFIT, FOCUS_ACUTE, "OH",
        patterns=("^OHIOHEALTH", "^RIVERSIDE METHODIST", "^GRANT MEDICAL CENTER"),
        states=("OH",),
    ),
    SystemDef(
        "promedica", "ProMedica", KIND_NONPROFIT, FOCUS_ACUTE, "OH",
        patterns=("^PROMEDICA",),
    ),
    SystemDef(
        "trihealth", "TriHealth", KIND_NONPROFIT, FOCUS_ACUTE, "OH",
        patterns=("^TRIHEALTH", "^BETHESDA NORTH", "^GOOD SAMARITAN HOSPITAL OF CINCINNATI"),
        states=("OH",),
    ),
    SystemDef(
        "premier_health", "Premier Health", KIND_NONPROFIT, FOCUS_ACUTE, "OH",
        patterns=("^MIAMI VALLEY", "^PREMIER HEALTH"),
        states=("OH",),
    ),
    SystemDef(
        "corewell", "Corewell Health", KIND_NONPROFIT, FOCUS_ACUTE, "MI",
        patterns=("^COREWELL", "^BEAUMONT", "^SPECTRUM HEALTH", "MI:^WILLIAM BEAUMONT"),
        states=("MI",),
    ),
    SystemDef(
        "henry_ford", "Henry Ford Health", KIND_NONPROFIT, FOCUS_ACUTE, "MI",
        patterns=("^HENRY FORD",),
    ),
    SystemDef(
        "mclaren", "McLaren Health Care", KIND_NONPROFIT, FOCUS_ACUTE, "MI",
        patterns=("^MCLAREN",),
    ),
    SystemDef(
        "munson", "Munson Healthcare", KIND_NONPROFIT, FOCUS_ACUTE, "MI",
        patterns=("^MUNSON",),
    ),
    SystemDef(
        "mymichigan", "MyMichigan Health", KIND_NONPROFIT, FOCUS_ACUTE, "MI",
        patterns=("^MYMICHIGAN",),
    ),
    SystemDef(
        "northwestern", "Northwestern Medicine", KIND_ACADEMIC, FOCUS_ACUTE, "IL",
        patterns=("^NORTHWESTERN", "^CENTRAL DUPAGE", "^DELNOR"),
        states=("IL",),
    ),
    SystemDef(
        "endeavor", "Endeavor Health", KIND_NONPROFIT, FOCUS_ACUTE, "IL",
        patterns=("^ENDEAVOR", "^NORTHSHORE UNIVERSITY", "^EDWARD HOSPITAL", "^ELMHURST HOSPITAL"),
        states=("IL",),
    ),
    SystemDef(
        "rush", "Rush University System for Health", KIND_ACADEMIC, FOCUS_ACUTE, "IL",
        patterns=("^RUSH",),
        states=("IL",),
    ),
    SystemDef(
        "osf", "OSF HealthCare", KIND_CATHOLIC, FOCUS_ACUTE, "IL",
        patterns=("^OSF",),
    ),
    SystemDef(
        "carle", "Carle Health", KIND_NONPROFIT, FOCUS_ACUTE, "IL",
        patterns=("^CARLE",),
    ),
    SystemDef(
        "unitypoint", "UnityPoint Health", KIND_NONPROFIT, FOCUS_ACUTE, "IA",
        patterns=("^UNITYPOINT", "IA,IL:^TRINITY", "IA:^ALLEN HOSPITAL",
                  "IA:^ILES", "IA:^METHODIST WEST", "IA:^SAINT LUKES"),
        note="Quad-Cities and Fort Dodge facilities still file as TRINITY — "
             "the reason Trinity Health cannot claim a bare '^TRINITY'.",
    ),
    SystemDef(
        "univ_iowa", "University of Iowa Health Care", KIND_ACADEMIC, FOCUS_ACUTE, "IA",
        patterns=("^UNIVERSITY OF IOWA", "^UI HEALTH CARE"),
    ),
    SystemDef(
        "genesis_ia", "Genesis Health System", KIND_NONPROFIT, FOCUS_ACUTE, "IA",
        patterns=("^GENESIS MEDICAL",),
        states=("IA", "IL"),
    ),
    SystemDef(
        "allina", "Allina Health", KIND_NONPROFIT, FOCUS_ACUTE, "MN",
        patterns=("^ALLINA", "^ABBOTT NORTHWESTERN", "^UNITED HOSPITAL", "^MERCY HOSPITAL MN"),
        states=("MN", "WI"),
    ),
    SystemDef(
        "fairview", "M Health Fairview", KIND_ACADEMIC, FOCUS_ACUTE, "MN",
        patterns=("^FAIRVIEW", "^M HEALTH", "MN:^HEALTHEAST"),
        states=("MN",),
    ),
    SystemDef(
        "healthpartners", "HealthPartners", KIND_NONPROFIT, FOCUS_ACUTE, "MN",
        patterns=("^HEALTHPARTNERS", "^REGIONS HOSPITAL", "^PARK NICOLLET"),
        states=("MN", "WI"),
    ),
    SystemDef(
        "essentia", "Essentia Health", KIND_NONPROFIT, FOCUS_ACUTE, "MN",
        patterns=("^ESSENTIA", "MN:^SAINT MARYS MEDICAL CENTER"),
    ),
    SystemDef(
        "cuyuna", "CentraCare", KIND_NONPROFIT, FOCUS_ACUTE, "MN",
        patterns=("^CENTRACARE", "^SAINT CLOUD HOSPITAL"),
        states=("MN",),
    ),
    SystemDef(
        "mayo", "Mayo Clinic", KIND_ACADEMIC, FOCUS_ACUTE, "MN",
        patterns=("^MAYO",),
    ),
    SystemDef(
        "aspirus", "Aspirus Health", KIND_NONPROFIT, FOCUS_ACUTE, "WI",
        patterns=("^ASPIRUS",),
    ),
    SystemDef(
        "froedtert", "Froedtert ThedaCare Health", KIND_ACADEMIC, FOCUS_ACUTE, "WI",
        patterns=("^FROEDTERT", "^THEDACARE"),
    ),
    SystemDef(
        "marshfield", "Marshfield Clinic Health System", KIND_NONPROFIT, FOCUS_ACUTE, "WI",
        patterns=("^MARSHFIELD",),
    ),
    SystemDef(
        "gundersen", "Emplify Health (Gundersen · Bellin)", KIND_NONPROFIT, FOCUS_ACUTE, "WI",
        patterns=("^GUNDERSEN", "^BELLIN"),
    ),
    SystemDef(
        "nebraska_medicine", "Nebraska Medicine", KIND_ACADEMIC, FOCUS_ACUTE, "NE",
        patterns=("NE:NEBRASKA MEDICAL CENTER", "^NEBRASKA MEDICINE"),
    ),
    SystemDef(
        "bryan", "Bryan Health", KIND_NONPROFIT, FOCUS_ACUTE, "NE",
        patterns=("^BRYAN",),
        states=("NE",),
    ),
    SystemDef(
        "ku_health", "University of Kansas Health System", KIND_ACADEMIC, FOCUS_ACUTE, "KS",
        patterns=("^UNIVERSITY OF KANSAS",),
    ),
    SystemDef(
        "st_lukes_kc", "Saint Luke's Health System (Kansas City)", KIND_NONPROFIT, FOCUS_ACUTE, "MO",
        patterns=("^SAINT LUKES",),
        states=("MO", "KS"),
    ),
    SystemDef(
        "bjc", "BJC HealthCare", KIND_ACADEMIC, FOCUS_ACUTE, "MO",
        patterns=("^BARNES JEWISH", "^BJC", "^MISSOURI BAPTIST", "^CHRISTIAN HOSPITAL",
                  "MO:^SAINT LOUIS CHILDRENS"),
        states=("MO", "IL"),
    ),
    SystemDef(
        "cox", "CoxHealth", KIND_NONPROFIT, FOCUS_ACUTE, "MO",
        patterns=("^COX ", "^COXHEALTH"),
        states=("MO",),
    ),

    # ── South / Southeast ──────────────────────────────────────────
    SystemDef(
        "uab", "UAB Health System", KIND_ACADEMIC, FOCUS_ACUTE, "AL",
        patterns=("^UAB", "AL:^BAPTIST MEDICAL CENTER"),
        note="Baptist Health (Montgomery) came into UAB Health System — "
             "its facilities still file under the Baptist name.",
    ),
    SystemDef(
        "infirmary", "Infirmary Health", KIND_NONPROFIT, FOCUS_ACUTE, "AL",
        patterns=("^MOBILE INFIRMARY", "^INFIRMARY"),
        states=("AL",),
    ),
    SystemDef(
        "baptist_fl", "Baptist Health South Florida", KIND_NONPROFIT, FOCUS_ACUTE, "FL",
        patterns=("^BAPTIST",),
        states=("FL",),
    ),
    SystemDef(
        "baptist_ky", "Baptist Health (Kentucky)", KIND_NONPROFIT, FOCUS_ACUTE, "KY",
        patterns=("^BAPTIST",),
        states=("KY",),
    ),
    SystemDef(
        "baptist_memphis", "Baptist Memorial Health Care", KIND_NONPROFIT, FOCUS_ACUTE, "TN",
        patterns=("^BAPTIST MEMORIAL", "^BAPTIST MEM", "MS:^BAPTIST MEDICAL CENTER"),
        states=("TN", "MS", "AR"),
    ),
    SystemDef(
        "baptist_ar", "Baptist Health (Arkansas)", KIND_NONPROFIT, FOCUS_ACUTE, "AR",
        patterns=("^BAPTIST",),
        states=("AR",),
    ),
    SystemDef(
        "orlando_health", "Orlando Health", KIND_NONPROFIT, FOCUS_ACUTE, "FL",
        patterns=("^ORLANDO HEALTH",),
    ),
    SystemDef(
        "tampa_general", "Tampa General Hospital", KIND_ACADEMIC, FOCUS_ACUTE, "FL",
        patterns=("^TAMPA GENERAL",),
    ),
    SystemDef(
        "jackson_health", "Jackson Health System", KIND_GOVERNMENT, FOCUS_ACUTE, "FL",
        patterns=("^JACKSON MEMORIAL", "^JACKSON NORTH", "^JACKSON SOUTH", "^JACKSON WEST"),
        states=("FL",),
    ),
    SystemDef(
        "lee_health", "Lee Health", KIND_GOVERNMENT, FOCUS_ACUTE, "FL",
        patterns=("^LEE MEMORIAL", "^LEE HEALTH", "^GULF COAST MEDICAL CENTER"),
        states=("FL",),
    ),
    SystemDef(
        "uf_health", "UF Health", KIND_ACADEMIC, FOCUS_ACUTE, "FL",
        patterns=("^UF HEALTH", "^SHANDS"),
    ),
    SystemDef(
        "vanderbilt", "Vanderbilt Health", KIND_ACADEMIC, FOCUS_ACUTE, "TN",
        patterns=("^VANDERBILT",),
    ),
    SystemDef(
        "ballad", "Ballad Health", KIND_NONPROFIT, FOCUS_ACUTE, "TN",
        patterns=("^BALLAD", "TN:^HOLSTON VALLEY", "TN:^JOHNSON CITY MEDICAL",
                  "TN:^BRISTOL REGIONAL", "TN:^INDIAN PATH", "VA:^NORTON COMMUNITY",
                  "VA:^LONESOME PINE", "VA:^JOHNSTON MEMORIAL"),
    ),
    SystemDef(
        "norton", "Norton Healthcare", KIND_NONPROFIT, FOCUS_ACUTE, "KY",
        patterns=("^NORTON",),
        states=("KY", "IN"),
    ),
    SystemDef(
        "uofl", "UofL Health", KIND_ACADEMIC, FOCUS_ACUTE, "KY",
        patterns=("^UOFL", "^UNIVERSITY OF LOUISVILLE"),
    ),
    SystemDef(
        "lcmc", "LCMC Health", KIND_NONPROFIT, FOCUS_ACUTE, "LA",
        patterns=("^LCMC", "^TOURO INFIRMARY", "^EAST JEFFERSON GENERAL"),
        states=("LA",),
    ),
    SystemDef(
        "franciscan_missionaries", "Franciscan Missionaries of Our Lady", KIND_CATHOLIC, FOCUS_ACUTE, "LA",
        patterns=("^OUR LADY OF THE LAKE", "^OUR LADY OF LOURDES", "^SAINT FRANCIS MEDICAL CENTER"),
        states=("LA",),
    ),
    SystemDef(
        "ummc_ms", "University of Mississippi Medical Center", KIND_ACADEMIC, FOCUS_ACUTE, "MS",
        patterns=("^UNIVERSITY OF MISSISSIPPI",),
    ),
    SystemDef(
        "musc", "MUSC Health", KIND_ACADEMIC, FOCUS_ACUTE, "SC",
        patterns=("^MUSC",),
    ),
    SystemDef(
        "unm", "UNM Health", KIND_ACADEMIC, FOCUS_ACUTE, "NM",
        patterns=("^UNIVERSITY OF NEW MEXICO", "^UNM "),
    ),
    SystemDef(
        "presbyterian_nm", "Presbyterian Healthcare Services", KIND_NONPROFIT, FOCUS_ACUTE, "NM",
        patterns=("^PRESBYTERIAN",),
        states=("NM",),
    ),
    SystemDef(
        "ut_system", "UT Health (Texas)", KIND_ACADEMIC, FOCUS_ACUTE, "TX",
        patterns=("^UT ",),
        states=("TX",),
    ),
    SystemDef(
        "cook_childrens", "Cook Children's Health Care System", KIND_NONPROFIT, FOCUS_CHILDRENS, "TX",
        patterns=("^COOK CHILDRENS",),
    ),
    SystemDef(
        "harris_health", "Harris Health System", KIND_GOVERNMENT, FOCUS_ACUTE, "TX",
        patterns=("^HARRIS HEALTH", "^BEN TAUB", "^LYNDON B JOHNSON"),
        states=("TX",),
    ),

    # ── West / Mountain ────────────────────────────────────────────
    SystemDef(
        "honorhealth", "HonorHealth", KIND_NONPROFIT, FOCUS_ACUTE, "AZ",
        patterns=("^HONORHEALTH",),
    ),
    SystemDef(
        "uchealth", "UCHealth", KIND_ACADEMIC, FOCUS_ACUTE, "CO",
        patterns=("^UCHEALTH", "^UNIVERSITY OF COLORADO"),
    ),
    SystemDef(
        "sclhealth", "Intermountain (SCL Health legacy)", KIND_CATHOLIC, FOCUS_ACUTE, "CO",
        patterns=("^SCL ", "^LUTHERAN MEDICAL CENTER", "^SAINT JOSEPH HOSPITAL DENVER"),
        states=("CO", "MT"),
    ),
    SystemDef(
        "billings", "Billings Clinic", KIND_NONPROFIT, FOCUS_ACUTE, "MT",
        patterns=("^BILLINGS CLINIC",),
    ),
    SystemDef(
        "st_lukes_id", "St. Luke's Health System (Idaho)", KIND_NONPROFIT, FOCUS_ACUTE, "ID",
        patterns=("^SAINT LUKES",),
        states=("ID",),
    ),
    SystemDef(
        "multicare", "MultiCare Health System", KIND_NONPROFIT, FOCUS_ACUTE, "WA",
        patterns=("^MULTICARE", "^TACOMA GENERAL", "^GOOD SAMARITAN HOSPITAL PUYALLUP"),
        states=("WA",),
    ),
    SystemDef(
        "uw_medicine", "UW Medicine", KIND_ACADEMIC, FOCUS_ACUTE, "WA",
        patterns=("^UNIVERSITY OF WASHINGTON", "^UW MEDICINE", "^HARBORVIEW"),
    ),
    SystemDef(
        "peacehealth", "PeaceHealth", KIND_CATHOLIC, FOCUS_ACUTE, "WA",
        patterns=("^PEACEHEALTH",),
    ),
    SystemDef(
        "confluence", "Confluence Health", KIND_NONPROFIT, FOCUS_ACUTE, "WA",
        patterns=("^CONFLUENCE", "WA:^CENTRAL WASHINGTON HOSPITAL"),
    ),
    SystemDef(
        "legacy", "Legacy Health", KIND_NONPROFIT, FOCUS_ACUTE, "OR",
        patterns=("^LEGACY",),
        states=("OR", "WA"),
    ),
    SystemDef(
        "ohsu", "OHSU Health", KIND_ACADEMIC, FOCUS_ACUTE, "OR",
        patterns=("^OHSU", "^OREGON HEALTH AND SCIENCE"),
    ),
    SystemDef(
        "samaritan_or", "Samaritan Health Services", KIND_NONPROFIT, FOCUS_ACUTE, "OR",
        patterns=("^SAMARITAN",),
        states=("OR",),
    ),
    SystemDef(
        "renown", "Renown Health", KIND_NONPROFIT, FOCUS_ACUTE, "NV",
        patterns=("^RENOWN",),
    ),
    SystemDef(
        "queens", "The Queen's Health System", KIND_NONPROFIT, FOCUS_ACUTE, "HI",
        patterns=("^QUEENS MEDICAL", "^THE QUEENS"),
        states=("HI",),
    ),
    SystemDef(
        "hawaii_pacific", "Hawai'i Pacific Health", KIND_NONPROFIT, FOCUS_ACUTE, "HI",
        patterns=("^STRAUB", "^KAPIOLANI", "^PALI MOMI", "^WILCOX"),
        states=("HI",),
    ),
    SystemDef(
        "alaska_native", "Alaska Native Tribal Health Consortium", KIND_GOVERNMENT, FOCUS_ACUTE, "AK",
        patterns=("^ALASKA NATIVE",),
    ),

    # ── University of California ───────────────────────────────────
    SystemDef(
        "uc_health", "University of California Health", KIND_ACADEMIC, FOCUS_ACUTE, "CA",
        patterns=("^UCSF", "^UCLA", "^UC SAN DIEGO", "^UC DAVIS", "^UC IRVINE",
                  "^UNIVERSITY OF CALIFORNIA", "^RONALD REAGAN"),
        states=("CA",),
    ),
    SystemDef(
        "stanford", "Stanford Health Care", KIND_ACADEMIC, FOCUS_ACUTE, "CA",
        patterns=("^STANFORD", "^LUCILE PACKARD"),
    ),
    SystemDef(
        "dignity_ca", "Dignity Health (CommonSpirit CA)", KIND_CATHOLIC, FOCUS_ACUTE, "CA",
        patterns=("^DIGNITY", "^MERCY GENERAL", "^MERCY SAN JUAN", "^SAINT JOSEPHS MEDICAL CENTER"),
        states=("CA", "NV"),
    ),
    SystemDef(
        "cedars_marina", "Providence Southern California", KIND_CATHOLIC, FOCUS_ACUTE, "CA",
        patterns=("^SAINT JOSEPH HOSPITAL ORANGE", "^HOAG", "^MISSION HOSPITAL"),
        states=("CA",),
    ),
    SystemDef(
        "pih", "PIH Health", KIND_NONPROFIT, FOCUS_ACUTE, "CA",
        patterns=("^PIH HEALTH",),
    ),
    SystemDef(
        "john_muir", "John Muir Health", KIND_NONPROFIT, FOCUS_ACUTE, "CA",
        patterns=("^JOHN MUIR",),
    ),

    # ── Regional systems surfaced by the unmapped long tail ────────
    #
    # Every entry below was added because the candidate-cluster scan
    # (see :func:`candidate_clusters`) showed two or more unmapped
    # facilities sharing a brand in one state. That scan is the intended
    # maintenance loop for this registry.
    SystemDef(
        "logan_health", "Logan Health", KIND_NONPROFIT, FOCUS_ACUTE, "MT",
        patterns=("^LOGAN HEALTH",),
    ),
    SystemDef(
        "monument", "Monument Health", KIND_NONPROFIT, FOCUS_ACUTE, "SD",
        patterns=("^MONUMENT HEALTH",),
    ),
    SystemDef(
        "broward", "Broward Health", KIND_GOVERNMENT, FOCUS_ACUTE, "FL",
        patterns=("^BROWARD HEALTH",),
    ),
    SystemDef(
        "memorial_fl", "Memorial Healthcare System (South Broward)",
        KIND_GOVERNMENT, FOCUS_ACUTE, "FL",
        patterns=("FL:^MEMORIAL REGIONAL", "FL:^MEMORIAL HOSPITAL WEST",
                  "FL:^MEMORIAL HOSPITAL MIRAMAR", "FL:^MEMORIAL HOSPITAL PEMBROKE",
                  "FL:^JOE DIMAGGIO"),
    ),
    SystemDef(
        "kettering", "Kettering Health", KIND_NONPROFIT, FOCUS_ACUTE, "OH",
        patterns=("^KETTERING HEALTH", "OH:^SOIN MEDICAL"),
    ),
    SystemDef(
        "summa", "Summa Health", KIND_NONPROFIT, FOCUS_ACUTE, "OH",
        patterns=("^SUMMA",),
    ),
    SystemDef(
        "st_elizabeth_ky", "St. Elizabeth Healthcare", KIND_CATHOLIC, FOCUS_ACUTE, "KY",
        patterns=("^SAINT ELIZABETH",),
        states=("KY",),
    ),
    SystemDef(
        "arh", "Appalachian Regional Healthcare", KIND_NONPROFIT, FOCUS_ACUTE, "KY",
        patterns=("ARH",),
        states=("KY", "WV"),
        note="Files as '<TOWN> ARH' — an unanchored pattern, safe only "
             "because of the word boundary and the two-state scope.",
    ),
    SystemDef(
        "owensboro", "Owensboro Health", KIND_NONPROFIT, FOCUS_ACUTE, "KY",
        patterns=("^OWENSBORO HEALTH",),
    ),
    SystemDef(
        "med_center_health", "Med Center Health", KIND_NONPROFIT, FOCUS_ACUTE, "KY",
        patterns=("KY:^THE MEDICAL CENTER",),
    ),
    SystemDef(
        "saint_francis_ok", "Saint Francis Health System", KIND_CATHOLIC, FOCUS_ACUTE, "OK",
        patterns=("^SAINT FRANCIS",),
        states=("OK",),
    ),
    SystemDef(
        "st_charles_or", "St. Charles Health System", KIND_NONPROFIT, FOCUS_ACUTE, "OR",
        patterns=("^SAINT CHARLES",),
        states=("OR",),
    ),
    SystemDef(
        "noland", "Noland Health Services", KIND_NONPROFIT, FOCUS_LTACH, "AL",
        patterns=("^NOLAND",),
    ),
    SystemDef(
        "community_health_in", "Community Health Network", KIND_NONPROFIT, FOCUS_ACUTE, "IN",
        patterns=("IN:^COMMUNITY HOSPITAL", "IN:^COMMUNITY HEALTH NETWORK",
                  "IN:^COMMUNITY HEART AND VASCULAR", "IN:^COMMUNITY HOWARD"),
    ),
    SystemDef(
        "parkview", "Parkview Health", KIND_NONPROFIT, FOCUS_ACUTE, "IN",
        patterns=("^PARKVIEW",),
        states=("IN", "OH"),
    ),
    SystemDef(
        "beacon_in", "Beacon Health System", KIND_NONPROFIT, FOCUS_ACUTE, "IN",
        patterns=("IN:^MEMORIAL HOSPITAL OF SOUTH BEND", "IN:^ELKHART GENERAL",
                  "IN:^BEACON "),
    ),
    SystemDef(
        "deaconess", "Deaconess Health System", KIND_NONPROFIT, FOCUS_ACUTE, "IN",
        patterns=("^DEACONESS",),
        states=("IN", "KY", "IL"),
    ),
    SystemDef(
        "north_mississippi", "North Mississippi Health Services",
        KIND_NONPROFIT, FOCUS_ACUTE, "MS",
        patterns=("^NORTH MISSISSIPPI",),
    ),
    SystemDef(
        "great_plains_ks", "Great Plains Health Alliance", KIND_NONPROFIT, FOCUS_ACUTE, "KS",
        patterns=("^GREAT PLAINS",),
        states=("KS",),
    ),
    SystemDef(
        "wvu", "WVU Medicine", KIND_ACADEMIC, FOCUS_ACUTE, "WV",
        patterns=("^WVU", "^WEST VIRGINIA UNIVERSITY"),
    ),
    SystemDef(
        "ecu_health", "ECU Health", KIND_ACADEMIC, FOCUS_ACUTE, "NC",
        patterns=("^ECU HEALTH", "^VIDANT"),
    ),
    SystemDef(
        "nuvance", "Nuvance Health", KIND_NONPROFIT, FOCUS_ACUTE, "CT",
        patterns=("^DANBURY HOSPITAL", "^NORWALK HOSPITAL", "^VASSAR BROTHERS",
                  "^SHARON HOSPITAL", "^NORTHERN DUTCHESS"),
        states=("CT", "NY"),
    ),
    SystemDef(
        "catholic_health_buffalo", "Catholic Health (Buffalo)", KIND_CATHOLIC, FOCUS_ACUTE, "NY",
        patterns=("NY:^MERCY HOSPITAL OF BUFFALO", "NY:^SISTERS OF CHARITY",
                  "NY:^KENMORE MERCY", "NY:^MOUNT SAINT MARYS"),
    ),
    SystemDef(
        "guthrie", "The Guthrie Clinic", KIND_NONPROFIT, FOCUS_ACUTE, "PA",
        patterns=("^GUTHRIE",),
    ),
    SystemDef(
        "carilion", "Carilion Clinic", KIND_NONPROFIT, FOCUS_ACUTE, "VA",
        patterns=("^CARILION",),
    ),
    SystemDef(
        "riverside_va", "Riverside Health", KIND_NONPROFIT, FOCUS_ACUTE, "VA",
        patterns=("^RIVERSIDE",),
        states=("VA",),
    ),
    SystemDef(
        "valley_health_va", "Valley Health System", KIND_NONPROFIT, FOCUS_ACUTE, "VA",
        patterns=("VA,WV:^WINCHESTER MEDICAL", "VA,WV:^SHENANDOAH MEMORIAL",
                  "VA,WV:^WARREN MEMORIAL", "VA,WV:^PAGE MEMORIAL"),
    ),
    SystemDef(
        "erlanger", "Erlanger Health", KIND_NONPROFIT, FOCUS_ACUTE, "TN",
        patterns=("^ERLANGER",),
    ),
    SystemDef(
        "covenant_tn", "Covenant Health (Tennessee)", KIND_NONPROFIT, FOCUS_ACUTE, "TN",
        patterns=("TN:^FORT SANDERS", "TN:^PARKWEST", "TN:^METHODIST MEDICAL CENTER OF OAK",
                  "TN:^LECONTE", "TN:^MORRISTOWN HAMBLEN", "TN:^ROANE MEDICAL"),
    ),
    SystemDef(
        "northeast_georgia", "Northeast Georgia Health System", KIND_NONPROFIT, FOCUS_ACUTE, "GA",
        patterns=("^NORTHEAST GEORGIA",),
    ),
    SystemDef(
        "tanner", "Tanner Health System", KIND_NONPROFIT, FOCUS_ACUTE, "GA",
        patterns=("^TANNER",),
    ),
    SystemDef(
        "emory", "Emory Healthcare", KIND_ACADEMIC, FOCUS_ACUTE, "GA",
        patterns=("^EMORY", "GA:^SAINT JOSEPHS OF ATLANTA"),
    ),
    SystemDef(
        "grady", "Grady Health System", KIND_GOVERNMENT, FOCUS_ACUTE, "GA",
        patterns=("^GRADY",),
        states=("GA",),
    ),
    SystemDef(
        "menonita", "Menonita Healthcare System", KIND_NONPROFIT, FOCUS_ACUTE, "PR",
        patterns=("^HOSPITAL MENONITA",),
    ),
    SystemDef(
        "hima", "HIMA San Pablo", KIND_FOR_PROFIT, FOCUS_ACUTE, "PR",
        patterns=("^HOSPITAL HIMA", "^HIMA SAN PABLO"),
    ),
    SystemDef(
        "san_pablo_pr", "San Pablo Health System", KIND_FOR_PROFIT, FOCUS_ACUTE, "PR",
        patterns=("^HOSPITAL SAN PABLO",),
    ),

    # ── Round 2: the next pass over the candidate-cluster backlog ──
    #
    # Same discipline as the block above — each entry answers a cluster
    # the scan surfaced. Several are national operators reachable only
    # through their regional brands (Steward, CHS, Tenet), which is why
    # the for-profit chains keep showing up in more than one place.
    SystemDef(
        "steward", "Steward Health Care", KIND_FOR_PROFIT, FOCUS_ACUTE, "MA",
        patterns=("^STEWARD", "UT:^SALT LAKE REGIONAL", "UT:^JORDAN VALLEY MEDICAL",
                  "UT:^DAVIS HOSPITAL", "UT:^MOUNTAIN POINT MEDICAL"),
    ),
    SystemDef(
        "chs", "Community Health Systems", KIND_FOR_PROFIT, FOCUS_ACUTE, "TN",
        patterns=("^TENNOVA", "MS:^MERIT HEALTH", "AZ:^NORTHWEST MEDICAL CENTER",
                  "FL:^BAYFRONT HEALTH PUNTA", "FL:^BAYFRONT HEALTH PORT"),
        note="CHS keeps acquired local names almost everywhere; only the "
             "regional house brands (Tennova, Merit Health) are reachable.",
    ),
    SystemDef(
        "baycare", "BayCare Health System", KIND_NONPROFIT, FOCUS_ACUTE, "FL",
        patterns=("FL:^MEASE", "FL:^MORTON PLANT", "FL:^SOUTH FLORIDA BAPTIST"),
    ),
    SystemDef(
        "mainline", "Main Line Health", KIND_NONPROFIT, FOCUS_ACUTE, "PA",
        patterns=("PA:^BRYN MAWR", "PA:^LANKENAU", "PA:^PAOLI HOSPITAL", "PA:^RIDDLE"),
    ),
    SystemDef(
        "garnet", "Garnet Health", KIND_NONPROFIT, FOCUS_ACUTE, "NY",
        patterns=("^GARNET HEALTH",),
    ),
    SystemDef(
        "concord_nh", "Concord Hospital Health System", KIND_NONPROFIT, FOCUS_ACUTE, "NH",
        patterns=("^CONCORD HOSPITAL",),
        states=("NH",),
    ),
    SystemDef(
        "heritage_valley", "Heritage Valley Health System", KIND_NONPROFIT, FOCUS_ACUTE, "PA",
        patterns=("^HERITAGE VALLEY",),
    ),
    SystemDef(
        "delta_health_ms", "Delta Health System", KIND_NONPROFIT, FOCUS_ACUTE, "MS",
        patterns=("^DELTA HEALTH",),
        states=("MS",),
    ),
    SystemDef(
        "singing_river", "Singing River Health System", KIND_GOVERNMENT, FOCUS_ACUTE, "MS",
        patterns=("^SINGING RIVER",),
    ),
    SystemDef(
        "loma_linda", "Loma Linda University Health", KIND_ACADEMIC, FOCUS_ACUTE, "CA",
        patterns=("^LOMA LINDA",),
    ),
    SystemDef(
        "nationwide_childrens", "Nationwide Children's Hospital",
        KIND_NONPROFIT, FOCUS_CHILDRENS, "OH",
        patterns=("^NATIONWIDE CHILDRENS",),
    ),
    SystemDef(
        "sarasota", "Sarasota Memorial Health Care System",
        KIND_GOVERNMENT, FOCUS_ACUTE, "FL",
        patterns=("^SARASOTA MEMORIAL",),
    ),
    SystemDef(
        "cape_fear", "Cape Fear Valley Health", KIND_NONPROFIT, FOCUS_ACUTE, "NC",
        patterns=("^CAPE FEAR VALLEY",),
    ),
    SystemDef(
        "hendrick", "Hendrick Health", KIND_NONPROFIT, FOCUS_ACUTE, "TX",
        patterns=("^HENDRICK",),
    ),
    SystemDef(
        "emanate", "Emanate Health", KIND_NONPROFIT, FOCUS_ACUTE, "CA",
        patterns=("^EMANATE",),
    ),
    SystemDef(
        "inspira", "Inspira Health", KIND_NONPROFIT, FOCUS_ACUTE, "NJ",
        patterns=("^INSPIRA",),
    ),
    SystemDef(
        "bayhealth", "Bayhealth", KIND_NONPROFIT, FOCUS_ACUTE, "DE",
        patterns=("^BAYHEALTH",),
    ),
    SystemDef(
        "palomar", "Palomar Health", KIND_GOVERNMENT, FOCUS_ACUTE, "CA",
        patterns=("^PALOMAR",),
    ),
    SystemDef(
        "cottage", "Cottage Health", KIND_NONPROFIT, FOCUS_ACUTE, "CA",
        patterns=("CA:^SANTA BARBARA COTTAGE", "CA:^GOLETA VALLEY COTTAGE",
                  "CA:^SANTA YNEZ VALLEY COTTAGE"),
    ),
    SystemDef(
        "university_health_kc", "University Health (Kansas City)",
        KIND_GOVERNMENT, FOCUS_ACUTE, "MO",
        patterns=("MO:^UNIVERSITY HEALTH",),
    ),
    SystemDef(
        "regional_one", "Regional One Health", KIND_GOVERNMENT, FOCUS_ACUTE, "TN",
        patterns=("^REGIONAL ONE",),
    ),
    SystemDef(
        "anmed", "AnMed Health", KIND_NONPROFIT, FOCUS_ACUTE, "SC",
        patterns=("^ANMED",),
    ),
    SystemDef(
        "roper", "Roper St. Francis Healthcare", KIND_NONPROFIT, FOCUS_ACUTE, "SC",
        patterns=("^ROPER",),
    ),
    SystemDef(
        "union_health_in", "Union Health", KIND_NONPROFIT, FOCUS_ACUTE, "IN",
        patterns=("IN:^UNION HOSPITAL",),
    ),
    SystemDef(
        "carson_tahoe", "Carson Tahoe Health", KIND_NONPROFIT, FOCUS_ACUTE, "NV",
        patterns=("^CARSON TAHOE",),
    ),
    SystemDef(
        "conway", "Conway Regional Health System", KIND_NONPROFIT, FOCUS_ACUTE, "AR",
        patterns=("^CONWAY REGIONAL",),
    ),
    SystemDef(
        "oklahoma_heart", "Oklahoma Heart Hospital", KIND_FOR_PROFIT, FOCUS_ACUTE, "OK",
        patterns=("^OKLAHOMA HEART",),
    ),
    SystemDef(
        "regional_west", "Regional West Health Services", KIND_NONPROFIT, FOCUS_ACUTE, "NE",
        patterns=("^REGIONAL WEST",),
    ),
    SystemDef(
        "general_health_la", "General Health System (Baton Rouge)",
        KIND_NONPROFIT, FOCUS_ACUTE, "LA",
        patterns=("LA:^BATON ROUGE GENERAL",),
    ),
    SystemDef(
        "cape_cod", "Cape Cod Healthcare", KIND_NONPROFIT, FOCUS_ACUTE, "MA",
        patterns=("MA:^CAPE COD",),
    ),
    SystemDef(
        "uva", "UVA Health", KIND_ACADEMIC, FOCUS_ACUTE, "VA",
        patterns=("^UVA ", "VA:^UNIVERSITY OF VIRGINIA"),
    ),

    # Post-acute / rehab platforms.
    SystemDef(
        "madonna", "Madonna Rehabilitation Hospitals", KIND_NONPROFIT, FOCUS_REHAB, "NE",
        patterns=("^MADONNA",),
    ),
    SystemDef(
        "sheltering_arms", "Sheltering Arms Institute", KIND_NONPROFIT, FOCUS_REHAB, "VA",
        patterns=("^SHELTERING ARMS",),
    ),
    SystemDef(
        "good_shepherd_pa", "Good Shepherd Rehabilitation Network",
        KIND_NONPROFIT, FOCUS_REHAB, "PA",
        patterns=("PA:^GOOD SHEPHERD",),
    ),
    SystemDef(
        "landmark", "Landmark Hospitals", KIND_FOR_PROFIT, FOCUS_LTACH, "MO",
        patterns=("^LANDMARK HOSPITAL",),
    ),
    SystemDef(
        "solara", "Solara Hospitals", KIND_FOR_PROFIT, FOCUS_LTACH, "TX",
        patterns=("^SOLARA",),
    ),
    SystemDef(
        "larkin", "Larkin Health System", KIND_FOR_PROFIT, FOCUS_ACUTE, "FL",
        patterns=("^LARKIN",),
    ),

    # Behavioral operators — the facet this mapping exists to answer.
    SystemDef(
        "assurance_health", "Assurance Health System", KIND_FOR_PROFIT, FOCUS_BEHAVIORAL, "OH",
        patterns=("^ASSURANCE HEALTH",),
    ),
    SystemDef(
        "compass_bh", "Compass Behavioral Health", KIND_FOR_PROFIT, FOCUS_BEHAVIORAL, "LA",
        patterns=("^COMPASS BEHAVIORAL",),
    ),
    SystemDef(
        "beacon_bh", "Beacon Behavioral Health", KIND_FOR_PROFIT, FOCUS_BEHAVIORAL, "LA",
        patterns=("^BEACON BEHAVIORAL",),
    ),
    SystemDef(
        "centerpointe", "CenterPointe Behavioral Health",
        KIND_FOR_PROFIT, FOCUS_BEHAVIORAL, "MO",
        patterns=("^CENTERPOINTE",),
    ),
    SystemDef(
        "four_winds", "Four Winds Hospitals", KIND_FOR_PROFIT, FOCUS_BEHAVIORAL, "NY",
        patterns=("^FOUR WINDS",),
    ),
    SystemDef(
        "college_health", "College Health Enterprises",
        KIND_FOR_PROFIT, FOCUS_BEHAVIORAL, "CA",
        patterns=("^COLLEGE HOSPITAL",),
    ),
    SystemDef(
        "ridgeview_ga", "Ridgeview Institute", KIND_NONPROFIT, FOCUS_BEHAVIORAL, "GA",
        patterns=("^RIDGEVIEW INSTITUTE",),
    ),
    SystemDef(
        "spring_mountain", "Spring Mountain Treatment Centers",
        KIND_FOR_PROFIT, FOCUS_BEHAVIORAL, "NV",
        patterns=("^SPRING MOUNTAIN",),
    ),

    # Children's systems.
    SystemDef(
        "arkansas_childrens", "Arkansas Children's", KIND_NONPROFIT, FOCUS_CHILDRENS, "AR",
        patterns=("^ARKANSAS CHILDRENS",),
    ),
    SystemDef(
        "childrens_wi", "Children's Wisconsin", KIND_NONPROFIT, FOCUS_CHILDRENS, "WI",
        patterns=("WI:^CHILDRENS HOSPITAL",),
    ),
    SystemDef(
        "childrens_health_tx", "Children's Health (Dallas)",
        KIND_NONPROFIT, FOCUS_CHILDRENS, "TX",
        patterns=("TX:^CHILDRENS MEDICAL CENTER",),
    ),

    # Puerto Rico.
    SystemDef(
        "doctors_center_pr", "Doctors' Center Hospital", KIND_FOR_PROFIT, FOCUS_ACUTE, "PR",
        patterns=("^DOCTORS CENTER",),
    ),
    SystemDef(
        "metro_pavia", "Metro Pavia Health System", KIND_FOR_PROFIT, FOCUS_ACUTE, "PR",
        patterns=("^HOSPITAL METROPOLITANO",),
    ),
    SystemDef(
        "sih", "Southern Illinois Healthcare", KIND_NONPROFIT, FOCUS_ACUTE, "IL",
        patterns=("IL:^MEMORIAL HOSPITAL OF CARBONDALE", "IL:^HERRIN HOSPITAL",
                  "IL:^SAINT JOSEPH MEMORIAL"),
    ),
    SystemDef(
        "la_county_dhs", "LA County Health Services", KIND_GOVERNMENT, FOCUS_ACUTE, "CA",
        patterns=("CA:^LOS ANGELES GENERAL", "CA:^HARBOR UCLA", "CA:^OLIVE VIEW",
                  "CA:^RANCHO LOS AMIGOS"),
    ),
    SystemDef(
        "suny", "SUNY Health", KIND_ACADEMIC, FOCUS_ACUTE, "NY",
        patterns=("NY:^UNIVERSITY HOSPITAL", "NY:^STONY BROOK"),
    ),
    SystemDef(
        "la_extended", "LA Extended Care Hospitals", KIND_FOR_PROFIT, FOCUS_LTACH, "LA",
        patterns=("LA:^LA EXTENDED CARE",),
    ),
)


# ── Name normalization + matching ──────────────────────────────────

_PUNCT_RE = re.compile(r"[^A-Z0-9]+")
_SAINT_RE = re.compile(r"\bST\b\.?")
_SPACE_RE = re.compile(r"\s+")


def normalize_name(raw: Any) -> str:
    """Upper-case, punctuation-stripped facility name used for matching.

    HCRIS names are truncated at ~36 characters and inconsistent about
    punctuation ("ST. MARY'S" / "ST MARYS" / "SAINT MARYS" all occur for
    the same brand), so matching on the raw string loses whole systems.
    Normalizing folds all three into ``SAINT MARYS``.
    """
    s = str(raw or "").upper().replace("&", " AND ")
    # Apostrophes are dropped, not spaced: "ST. MARY'S" has to fold onto
    # "ST MARYS", which is how HCRIS files the same hospital elsewhere.
    s = s.replace("'", "").replace("\u2019", "")
    s = _PUNCT_RE.sub(" ", s)
    s = _SAINT_RE.sub("SAINT", s)
    s = _SPACE_RE.sub(" ", s).strip()
    return s


def _compile_pattern(pattern: str) -> "re.Pattern[str]":
    """Compile one registry pattern into a word-bounded regex.

    ``^`` anchors to the start of the name. **Both ends of every pattern
    are word-bounded.** The first cut of this matcher compared with
    ``str.startswith`` and pulled CHINLE, CHINESE HOSPITAL, CHINO VALLEY
    and five children's hospitals into CommonSpirit off the ``CHI``
    brand — short brand abbreviations (CHI, UH, UT, UM, PAM, SSH) are
    only safe with a trailing boundary.
    """
    body = pattern.lstrip("^").strip()
    if not body:
        # Never-matching pattern — cheaper than special-casing at call sites.
        return re.compile(r"(?!)")
    prefix = "^" if pattern.startswith("^") else r"(?<![A-Z0-9])"
    return re.compile(prefix + re.escape(body) + r"(?![A-Z0-9])")


def _pattern_hits(norm: str, pattern: str) -> bool:
    """True if ``pattern`` matches ``norm``. Kept for direct/test use —
    the hot path goes through the precompiled index below."""
    return bool(_compile_pattern(pattern).search(norm))


# A pattern may carry its own state scope as a ``TX:`` / ``UT,ID:``
# prefix. This exists so a national system whose local brands are
# state-specific (HCA's MountainStar names in Utah, CommonSpirit's
# legacy Saint Joseph names in Kentucky) stays ONE row in the master
# mapping. Splitting them into per-state pseudo-systems would answer
# the "how many hospitals does this system run" question wrongly.
_PATTERN_SCOPE_RE = re.compile(r"^([A-Z]{2}(?:,[A-Z]{2})*):")


def _split_pattern(pattern: str) -> Tuple[Tuple[str, ...], str]:
    """Split ``"UT,ID:^ALTA VIEW"`` into ``(("UT", "ID"), "^ALTA VIEW")``."""
    m = _PATTERN_SCOPE_RE.match(pattern)
    if not m:
        return (), pattern
    return tuple(m.group(1).split(",")), pattern[m.end():]


@dataclass(frozen=True)
class _Compiled:
    """One registry pattern, ready to run against a normalized name."""

    sysdef: SystemDef
    raw: str
    regex: Any
    scope: Tuple[str, ...]
    specificity: int


def _build_index() -> Tuple[Tuple[_Compiled, ...], Dict[str, Tuple[_Compiled, ...]]]:
    """Precompile every pattern once, bucketed by state.

    Matching is O(rows x patterns) — 6,123 facilities against ~600
    patterns. Compiling inside the loop leaned on ``re``'s 512-entry
    cache, which thrashes at this pattern count and cost ~8s per cold
    page render; precompiling and pre-bucketing by state brings it under
    a second.
    """
    unscoped: List[_Compiled] = []
    by_state: Dict[str, List[_Compiled]] = {}
    for sysdef in SYSTEM_REGISTRY:
        for pattern in sysdef.patterns:
            scope, body = _split_pattern(pattern)
            entry = _Compiled(
                sysdef=sysdef,
                raw=pattern,
                regex=_compile_pattern(body),
                scope=scope or sysdef.states,
                specificity=len(body.lstrip("^")),
            )
            if entry.scope:
                for st in entry.scope:
                    by_state.setdefault(st, []).append(entry)
            else:
                unscoped.append(entry)
    return tuple(unscoped), {k: tuple(v) for k, v in by_state.items()}


_UNSCOPED_PATTERNS, _STATE_PATTERNS = _build_index()

_EXCLUDE_INDEX: Dict[str, Tuple[Any, ...]] = {
    s.system_id: tuple(_compile_pattern(x) for x in s.exclude)
    for s in SYSTEM_REGISTRY if s.exclude
}


def match_system(name: Any, state: Any = None) -> Tuple[Optional[SystemDef], str]:
    """Resolve one facility to a :class:`SystemDef`.

    Returns ``(system_def, matched_pattern)``, or ``(None, "")`` when the
    name carries no system brand. Longest matched pattern wins, so a
    facility matching both ``^MERCY`` (Mercy MO) and
    ``^MERCY HEALTH MUSKEGON`` (Trinity) resolves to Trinity — the more
    specific claim is the more trustworthy one. State-scoped entries win
    ties against unscoped ones for the same reason.
    """
    norm = normalize_name(name)
    if not norm:
        return None, ""
    st = str(state or "").upper().strip()
    best: Optional[SystemDef] = None
    best_pattern = ""
    best_key: Tuple[int, int] = (-1, -1)
    for entry in _STATE_PATTERNS.get(st, ()) + _UNSCOPED_PATTERNS:
        key = (entry.specificity, 1 if entry.scope else 0)
        if key <= best_key:
            continue
        if not entry.regex.search(norm):
            continue
        excludes = _EXCLUDE_INDEX.get(entry.sysdef.system_id)
        if excludes and any(x.search(norm) for x in excludes):
            continue
        best, best_pattern, best_key = entry.sysdef, entry.raw, key
    return best, best_pattern


# ── Behavioral detection ───────────────────────────────────────────

# Name signals that read as behavioral to a partner screening the space
# even when the CCN range says otherwise (a psych hospital filed under a
# general CCN, or a rehab CCN carrying a BH brand). "BH " is included
# because HCRIS abbreviates it that way ("CORNERSTONE BH EL DORADO").
_BEHAVIORAL_NAME_RE = re.compile(
    r"(?<![A-Z0-9])(?:BEHAVIORAL|PSYCHIATRIC|PSYCH|MENTAL HEALTH|BH)(?![A-Z0-9])"
)


def _behavioral_series(names: pd.Series, types: pd.Series) -> pd.Series:
    """True where a facility is behavioral by CCN range **or** by name."""
    by_ccn = types.eq("psychiatric")
    by_name = names.map(normalize_name).str.contains(_BEHAVIORAL_NAME_RE, na=False)
    return (by_ccn | by_name).fillna(False)


# ── Facility status — is this hospital still open? ─────────────────
#
# HCRIS has no "closed" flag: a hospital leaves the data by simply not
# filing another cost report. That silence is the only closure signal
# the source carries, and it is a good one — 98% of the universe filed
# for the corpus's latest year, and the facilities two years behind are
# recognisable closures (Pickens County, Coalinga Regional, East Valley
# Glendora, Mee Memorial). Counting them as operating hospitals
# overstates a system's estate, which is the number this page exists to
# get right.
#
# Three statuses, on filing recency alone:
#
#   Active         — filed for the corpus's latest year. The operating
#                    estate. A current cost report is the evidence the
#                    CCN is live.
#   Dormant        — last filed one year behind. A late filer and a
#                    mid-year closure are indistinguishable here, so the
#                    status claims neither; both are held out of the
#                    operating counts and listed by name.
#   Stopped filing — last filed two or more years behind. Closed, merged
#                    into another CCN, or converted (a Rural Emergency
#                    Hospital conversion looks identical from here). Not
#                    operating under this CCN either way.
#
# Reported activity is deliberately NOT part of this ladder. An earlier
# cut treated "filed with zero beds, zero patient days and zero net
# patient revenue" as closed, which dropped Mary Bridge Children's,
# Shriners and Texas Scottish Rite — all open hospitals that simply do
# not report those fields the way a general acute hospital does. Those
# facilities now carry a ``reports_no_activity`` flag instead: they stay
# in the hospital counts (they are open) while contributing nothing to
# beds or revenue, and the flag says why a system's bed count can look
# light against its hospital count.
#
# What this is NOT: proof of closure. A CCN can go quiet because the
# facility was absorbed into a parent's cost report. The page labels the
# status rather than asserting "closed", and lists every held-out
# facility by name so the call is auditable rather than buried.

STATUS_ACTIVE = "Active"
STATUS_DORMANT = "Dormant — last filed prior year"
STATUS_STOPPED = "Stopped filing — closed, merged or converted"

#: Statuses that count toward a system's operating hospital estate.
OPERATING_STATUSES: Tuple[str, ...] = (STATUS_ACTIVE,)

#: Every status, in the order the page should list them.
STATUS_ORDER: Tuple[str, ...] = (STATUS_ACTIVE, STATUS_DORMANT, STATUS_STOPPED)


def _numeric(df: pd.DataFrame, col: str) -> pd.Series:
    if col not in df.columns:
        return pd.Series(0.0, index=df.index)
    return pd.to_numeric(df[col], errors="coerce").fillna(0.0)


@lru_cache(maxsize=1)
def _last_active_year_by_ccn() -> "pd.Series":
    """Per CCN, the last fiscal year that reported any activity.

    Read off the FULL cost-report history rather than the latest filing
    per CCN, because that is the only way to separate the two very
    different facilities inside "no reported activity": one that ran
    until 2021 and went dark (a closure), and one that has never
    reported beds, days or revenue in the corpus at all (a shell CCN or
    a chronic non-reporter). The status label can't tell them apart —
    this column can, and the closed list shows it.
    """
    from .hcris import _get_hcris_cached

    hist = _get_hcris_cached()
    if hist is None or hist.empty or "ccn" not in hist.columns:
        return pd.Series(dtype="Int64")
    active = hist[
        (_numeric(hist, "beds") > 0)
        | (_numeric(hist, "total_patient_days") > 0)
        | (_numeric(hist, "net_patient_revenue") > 0)
    ]
    if active.empty:
        return pd.Series(dtype="Int64")
    years = pd.to_numeric(active["fiscal_year"], errors="coerce")
    return (active.assign(_fy=years).groupby("ccn")["_fy"].max().astype("Int64"))


def _status_series(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
    """Classify each facility on filing recency. Returns (status, last_fy).

    The corpus's own latest fiscal year is the reference point rather
    than the wall clock, so the classification stays correct across
    HCRIS refreshes instead of silently declaring the whole universe
    closed once the extract ages.
    """
    if "fiscal_year" not in df.columns:
        # A caller-supplied frame without the column can't be aged; treat
        # every row as operating rather than declaring the frame closed.
        return (pd.Series(STATUS_ACTIVE, index=df.index),
                pd.Series(pd.NA, index=df.index, dtype="Int64"))
    years = pd.to_numeric(df["fiscal_year"], errors="coerce")
    if years.dropna().empty:
        return (pd.Series(STATUS_ACTIVE, index=df.index),
                pd.Series(pd.NA, index=df.index, dtype="Int64"))
    gap = int(years.max()) - years

    status = pd.Series(STATUS_ACTIVE, index=df.index, dtype=object)
    status = status.mask(gap == 1, STATUS_DORMANT)
    status = status.mask(gap >= 2, STATUS_STOPPED)
    return status, years.astype("Int64")


def _no_activity_series(df: pd.DataFrame) -> pd.Series:
    """True where a filing reports zero beds, zero days and zero revenue.

    A flag, not a closure signal — see the note above. It exists so a
    system whose bed count reads light against its hospital count has a
    visible reason.
    """
    return ~(
        (_numeric(df, "beds") > 0)
        | (_numeric(df, "total_patient_days") > 0)
        | (_numeric(df, "net_patient_revenue") > 0)
    )


# ── Assignment over the universe ───────────────────────────────────

_SYSTEM_BY_ID: Dict[str, SystemDef] = {s.system_id: s for s in SYSTEM_REGISTRY}

UNMAPPED_ID = "_unmapped"
UNMAPPED_NAME = "Independent / Unmapped"


def registry_size() -> int:
    """Number of systems currently in the registry."""
    return len(SYSTEM_REGISTRY)


def get_system(system_id: str) -> Optional[SystemDef]:
    return _SYSTEM_BY_ID.get(str(system_id or ""))


def assign_systems(df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Return the hospital universe with system + type columns attached.

    Added columns: ``system_id``, ``system_name``, ``system_kind``,
    ``system_focus``, ``system_match`` (the pattern that fired — the
    audit trail for every count on the page), ``facility_type``,
    ``facility_type_label``, ``is_behavioral``.

    Passing ``df=None`` reads the bundled universe through the process
    cache; the returned frame is always a copy, so callers may mutate.
    """
    if df is None:
        return _assigned_cached().copy()
    return _assign_universe(df)


def _assign_universe(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if out.empty:
        for col in ("system_id", "system_name", "system_kind", "system_focus",
                    "system_match", "facility_type", "facility_type_label"):
            out[col] = pd.Series(dtype=object)
        out["is_behavioral"] = pd.Series(dtype=bool)
        return out

    names = out["name"] if "name" in out.columns else pd.Series([""] * len(out), index=out.index)
    states = out["state"] if "state" in out.columns else pd.Series([""] * len(out), index=out.index)
    ccns = out["ccn"] if "ccn" in out.columns else pd.Series([""] * len(out), index=out.index)

    matches = [match_system(n, s) for n, s in zip(names, states, strict=True)]
    out["system_id"] = [m[0].system_id if m[0] else UNMAPPED_ID for m in matches]
    out["system_name"] = [m[0].name if m[0] else UNMAPPED_NAME for m in matches]
    out["system_kind"] = [m[0].kind if m[0] else "" for m in matches]
    out["system_focus"] = [m[0].focus if m[0] else "" for m in matches]
    out["system_match"] = [m[1] for m in matches]

    types = _classify_series(ccns, names)
    out["facility_type"] = types
    out["facility_type_label"] = types.map(lambda t: TYPE_DISPLAY.get(t, "Other"))
    out["is_behavioral"] = _behavioral_series(names, types)

    status, last_fy = _status_series(out)
    out["facility_status"] = status
    out["last_fiscal_year"] = last_fy
    out["is_operating"] = status.isin(OPERATING_STATUSES)
    out["reports_no_activity"] = _no_activity_series(out)
    try:
        last_active = _last_active_year_by_ccn()
        out["last_active_fiscal_year"] = ccns.astype(str).map(last_active).astype("Int64")
    except Exception:  # history unavailable (synthetic frame) — leave blank
        out["last_active_fiscal_year"] = pd.Series(pd.NA, index=out.index, dtype="Int64")
    return out


@lru_cache(maxsize=1)
def _assigned_cached() -> pd.DataFrame:
    """Assignment over the bundled universe, computed once per process.

    The page hits this on every render (master table, roster drill-down,
    candidate clusters); the bundled HCRIS extract only changes on a data
    refresh, so recomputing per request was pure waste.
    """
    return _assign_universe(_get_latest_per_ccn())


# ── Rollup ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SystemRollup:
    """One row of the master mapping — a system and what it operates."""

    system_id: str
    system_name: str
    kind: str
    focus: str
    hq_state: str
    hospitals: int          # operating estate — closed / dormant excluded
    beds: float             # operating facilities only
    net_patient_revenue: float
    states: Tuple[str, ...]
    type_counts: Dict[str, int]
    behavioral_hospitals: int
    inactive_hospitals: int = 0
    zero_activity_hospitals: int = 0
    status_counts: Dict[str, int] = field(default_factory=dict)
    note: str = ""

    @property
    def total_facilities(self) -> int:
        """Every CCN mapped to the system, operating or not."""
        return self.hospitals + self.inactive_hospitals

    @property
    def state_count(self) -> int:
        return len(self.states)

    @property
    def behavioral_share(self) -> float:
        """Share of the system's OPERATING facilities that are behavioral (0-1)."""
        return (self.behavioral_hospitals / self.hospitals) if self.hospitals else 0.0

    @property
    def avg_beds(self) -> float:
        return (self.beds / self.hospitals) if self.hospitals else 0.0

    def type_count(self, label: str) -> int:
        return int(self.type_counts.get(label, 0))

    def status_count(self, status: str) -> int:
        return int(self.status_counts.get(status, 0))


@dataclass(frozen=True)
class CandidateCluster:
    """An unmapped name family that looks like a system we don't carry.

    Surfaced so the registry has a visible backlog instead of an
    invisible one: two or more unmapped facilities sharing a two-word
    name stem in the same state is usually a real local system.
    """

    stem: str
    state: str
    hospitals: int
    beds: float
    examples: Tuple[str, ...]


@dataclass(frozen=True)
class HealthSystemMap:
    """The whole master mapping — systems, coverage, and the long tail."""

    systems: Tuple[SystemRollup, ...]
    unmapped: SystemRollup
    total_hospitals: int        # operating facilities in the universe
    total_beds: float
    mapped_hospitals: int       # operating facilities inside a named system
    total_behavioral: int
    states_covered: int
    type_totals: Dict[str, int]
    candidates: Tuple[CandidateCluster, ...] = ()
    inactive_hospitals: int = 0
    zero_activity_hospitals: int = 0
    status_totals: Dict[str, int] = field(default_factory=dict)

    @property
    def universe_facilities(self) -> int:
        """Every CCN in the extract, operating or not."""
        return self.total_hospitals + self.inactive_hospitals

    @property
    def system_count(self) -> int:
        return len(self.systems)

    @property
    def coverage_pct(self) -> float:
        """Share of the OPERATING universe assigned to a named system (0-100)."""
        if not self.total_hospitals:
            return 0.0
        return self.mapped_hospitals / self.total_hospitals * 100.0

    def status_total(self, status: str) -> int:
        return int(self.status_totals.get(status, 0))

    @property
    def multi_state_systems(self) -> int:
        return sum(1 for s in self.systems if s.state_count > 1)

    @property
    def behavioral_systems(self) -> int:
        """Systems that operate at least one behavioral facility."""
        return sum(1 for s in self.systems if s.behavioral_hospitals > 0)


def _rollup_group(
    system_id: str,
    system_name: str,
    kind: str,
    focus: str,
    hq_state: str,
    note: str,
    group: pd.DataFrame,
) -> SystemRollup:
    """Roll one system's facilities up.

    Every operating figure — hospital count, beds, revenue, type mix,
    behavioral count, state footprint — is computed over the OPERATING
    subset. A closed hospital must not inflate the estate a partner
    underwrites, and a closed hospital's last-reported beds are the
    least real number in the frame.
    """
    operating = (group[group["is_operating"]] if "is_operating" in group.columns
                 else group)
    inactive = int(len(group) - len(operating))
    beds = float(pd.to_numeric(operating.get("beds"), errors="coerce").fillna(0).sum())
    npr = float(pd.to_numeric(
        operating.get("net_patient_revenue"), errors="coerce").fillna(0).sum())
    states = tuple(sorted({str(s).upper() for s in operating.get("state", [])
                           if str(s).strip()}))
    counts = (operating["facility_type"].value_counts().to_dict()
              if "facility_type" in operating else {})
    type_counts = {label: int(counts.get(label, 0)) for label in TYPE_LABELS}
    behavioral = int(operating["is_behavioral"].sum()) if "is_behavioral" in operating else 0
    s_counts = (group["facility_status"].value_counts().to_dict()
                if "facility_status" in group else {})
    zero_activity = (int(operating["reports_no_activity"].sum())
                     if "reports_no_activity" in operating else 0)
    return SystemRollup(
        system_id=system_id,
        system_name=system_name,
        kind=kind,
        focus=focus,
        hq_state=hq_state,
        hospitals=int(len(operating)),
        beds=beds,
        net_patient_revenue=npr,
        states=states,
        type_counts=type_counts,
        behavioral_hospitals=behavioral,
        inactive_hospitals=inactive,
        zero_activity_hospitals=zero_activity,
        status_counts={k: int(v) for k, v in s_counts.items()},
        note=note,
    )


_STOP_STEM_WORDS = frozenset({
    "THE", "OF", "AND", "AT", "FOR", "A", "AN",
})


def candidate_clusters(
    df: Optional[pd.DataFrame] = None,
    *,
    min_hospitals: int = 2,
    limit: int = 40,
) -> List[CandidateCluster]:
    """Unmapped name families that look like systems the registry misses.

    Groups unmapped facilities by (first two meaningful name tokens,
    state). This is the maintenance queue for :data:`SYSTEM_REGISTRY` —
    it is deliberately *not* used to assign systems, because a shared
    name stem is evidence of a candidate, not proof of ownership.
    """
    assigned = assign_systems(df)
    rest = assigned[(assigned["system_id"] == UNMAPPED_ID) & assigned["is_operating"]]
    if rest.empty:
        return []
    stems: List[str] = []
    for raw in rest["name"]:
        toks = [t for t in normalize_name(raw).split() if t not in _STOP_STEM_WORDS]
        stems.append(" ".join(toks[:2]) if len(toks) >= 2 else (toks[0] if toks else ""))
    rest = rest.assign(_stem=stems)
    rest = rest[rest["_stem"].astype(bool)]
    out: List[CandidateCluster] = []
    for (stem, state), group in rest.groupby(["_stem", "state"], sort=False):
        if len(group) < min_hospitals:
            continue
        out.append(CandidateCluster(
            stem=str(stem),
            state=str(state),
            hospitals=len(group),
            beds=float(pd.to_numeric(group["beds"], errors="coerce").fillna(0).sum()),
            examples=tuple(str(x) for x in group["name"].head(3)),
        ))
    out.sort(key=lambda c: (-c.hospitals, -c.beds, c.stem))
    return out[:limit]


def _empty_rollup() -> SystemRollup:
    """Zero-row stand-in so an empty universe still returns a whole map."""
    return SystemRollup(
        UNMAPPED_ID, UNMAPPED_NAME, "", "", "", 0, 0.0, 0.0, (),
        {label: 0 for label in TYPE_LABELS}, 0,
    )


def build_system_map(df: Optional[pd.DataFrame] = None) -> HealthSystemMap:
    """Roll the assigned universe up to one row per health system."""
    assigned = assign_systems(df)
    if assigned.empty:
        empty = _empty_rollup()
        return HealthSystemMap((), empty, 0, 0.0, 0, 0, 0,
                               {label: 0 for label in TYPE_LABELS})

    rollups: List[SystemRollup] = []
    unmapped: Optional[SystemRollup] = None
    for system_id, group in assigned.groupby("system_id", sort=False):
        sysdef = _SYSTEM_BY_ID.get(str(system_id))
        if sysdef is None:
            unmapped = _rollup_group(UNMAPPED_ID, UNMAPPED_NAME, "", "", "",
                                     "", group)
            continue
        rollups.append(_rollup_group(
            sysdef.system_id, sysdef.name, sysdef.kind, sysdef.focus,
            sysdef.hq_state, sysdef.note, group,
        ))
    rollups.sort(key=lambda s: (-s.hospitals, -s.beds, s.system_name))

    if unmapped is None:
        unmapped = _empty_rollup()

    # Universe totals are computed over OPERATING facilities for the same
    # reason the per-system ones are: a coverage percentage whose
    # denominator includes closed hospitals answers a question nobody
    # asked. The inactive count and the per-status breakdown ride
    # alongside so the two always reconcile on the page.
    operating = assigned[assigned["is_operating"]]
    counts = operating["facility_type"].value_counts().to_dict()
    type_totals = {label: int(counts.get(label, 0)) for label in TYPE_LABELS}
    states_covered = len({str(x).upper() for x in operating["state"] if str(x).strip()})
    status_totals = {k: int(v) for k, v
                     in assigned["facility_status"].value_counts().to_dict().items()}

    return HealthSystemMap(
        systems=tuple(rollups),
        unmapped=unmapped,
        total_hospitals=int(len(operating)),
        total_beds=float(pd.to_numeric(operating["beds"], errors="coerce").fillna(0).sum()),
        mapped_hospitals=int(len(operating) - unmapped.hospitals),
        total_behavioral=int(operating["is_behavioral"].sum()),
        states_covered=states_covered,
        type_totals=type_totals,
        candidates=tuple(candidate_clusters(df)),
        inactive_hospitals=int(len(assigned) - len(operating)),
        zero_activity_hospitals=int(operating["reports_no_activity"].sum()),
        status_totals=status_totals,
    )


@lru_cache(maxsize=1)
def _cached_map() -> HealthSystemMap:
    """Cached rollup over the bundled universe.

    The rollup walks 6,123 rows × ~180 registry entries; at ~0.5s that is
    too slow to redo on every page render, and the underlying HCRIS
    extract only changes on a data refresh.
    """
    return build_system_map(None)


def get_system_map(df: Optional[pd.DataFrame] = None) -> HealthSystemMap:
    """Rollup for the page. Uses the cache when reading the bundled universe."""
    if df is None:
        return _cached_map()
    return build_system_map(df)


def system_hospitals(
    system_id: str,
    df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Facility roster for one system, largest first."""
    assigned = assign_systems(df)
    rows = assigned[assigned["system_id"] == str(system_id)]
    if rows.empty:
        return rows
    beds = pd.to_numeric(rows["beds"], errors="coerce").fillna(0)
    return rows.assign(_beds=beds).sort_values("_beds", ascending=False).drop(columns="_beds")


def inactive_facilities(
    df: Optional[pd.DataFrame] = None,
    *,
    status: str = "",
) -> pd.DataFrame:
    """Every facility that is NOT counted in a system's operating estate.

    This is the audit list behind the exclusion: a hospital dropped from
    a system's count has to be nameable, or the count is just a smaller
    number with no explanation. Ordered by how strong the closure signal
    is (stopped filing first), then by state and name.
    """
    assigned = assign_systems(df)
    if assigned.empty:
        return assigned
    rows = assigned[~assigned["is_operating"]]
    if status:
        rows = rows[rows["facility_status"] == status]
    if rows.empty:
        return rows
    rank = {STATUS_STOPPED: 0, STATUS_DORMANT: 1}
    ordered = rows.assign(_r=rows["facility_status"].map(lambda v: rank.get(v, 3)))
    ordered = ordered.sort_values(
        ["_r", "last_fiscal_year", "state", "name"],
        ascending=[True, True, True, True])
    return ordered.drop(columns="_r")


def find_hospitals(
    query: str,
    df: Optional[pd.DataFrame] = None,
    *,
    limit: int = 60,
) -> pd.DataFrame:
    """Reverse lookup — hospital name or CCN in, system out.

    The other half of a lookup: a partner reading a CIM sees a facility
    name, not a system, and needs to know who owns it. Matches a CCN
    exactly (with or without the leading zero HCRIS pads onto it) or a
    normalized substring of the facility name, then sorts exact-CCN and
    name-prefix hits above mid-string hits so "MERCY" opens on the
    hospitals actually called Mercy.
    """
    assigned = assign_systems(df)
    q = str(query or "").strip()
    if not q or assigned.empty:
        return assigned.iloc[0:0]

    ccn_col = assigned["ccn"].astype(str)
    by_ccn = ccn_col.str.lstrip("0").eq(q.lstrip("0")) if q.isdigit() else None
    if by_ccn is not None and by_ccn.any():
        return assigned[by_ccn]

    needle = normalize_name(q)
    if not needle:
        return assigned.iloc[0:0]
    names = assigned["name"].map(normalize_name)
    hits = assigned[names.str.contains(re.escape(needle), na=False)].copy()
    if hits.empty:
        return hits
    hit_names = hits["name"].map(normalize_name)
    hits["_rank"] = (~hit_names.str.startswith(needle)).astype(int)
    hits["_beds"] = pd.to_numeric(hits["beds"], errors="coerce").fillna(0)
    hits = hits.sort_values(["_rank", "_beds"], ascending=[True, False])
    return hits.drop(columns=["_rank", "_beds"]).head(max(1, int(limit)))


def mapping_rows(df: Optional[pd.DataFrame] = None) -> List[Dict[str, Any]]:
    """Flat one-row-per-hospital view of the mapping — for CSV export.

    Deliberately hospital-grained rather than system-grained: the export
    exists so the mapping can be joined against a target list or a deal
    model in Excel, and CCN is the only key that joins cleanly.
    """
    assigned = assign_systems(df)
    cols = ["ccn", "name", "city", "state", "system_id", "system_name",
            "system_kind", "system_focus", "system_match",
            "facility_type_label", "is_behavioral", "facility_status",
            "reports_no_activity", "last_fiscal_year",
            "last_active_fiscal_year", "beds", "net_patient_revenue"]
    present = [c for c in cols if c in assigned.columns]
    out: List[Dict[str, Any]] = []
    for row in assigned[present].to_dict("records"):
        row["is_behavioral"] = "Y" if row.get("is_behavioral") else "N"
        row["reports_no_activity"] = "Y" if row.get("reports_no_activity") else "N"
        if row.get("system_id") == UNMAPPED_ID:
            row["system_id"] = ""
        out.append(row)
    out.sort(key=lambda r: (r.get("system_name") or "", str(r.get("state") or ""),
                            str(r.get("name") or "")))
    return out


def export_mapping(
    *,
    state: str = "",
    kind: str = "",
    focus: str = "",
    ftype: str = "",
    system_id: str = "",
    query: str = "",
    status: str = "",
    df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Filter-aware export frame — one row per hospital.

    Filters are hospital-grained, not system-grained: ``state`` is the
    facility's state and ``ftype`` the facility's own type, so a
    "behavioral in TX" export returns the behavioral facilities in Texas
    rather than every facility of every system that has one.

    ``status`` accepts ``operating`` / ``inactive`` or any single status
    label. The export ships EVERY facility by default, closed ones
    included, because the row carries ``facility_status`` — an export
    that silently dropped them would be harder to reconcile against the
    page, not easier.
    """
    rows = pd.DataFrame(mapping_rows(df))
    if rows.empty:
        return rows
    if state:
        rows = rows[rows["state"].astype(str).str.upper() == state.upper()]
    if kind:
        rows = rows[rows["system_kind"] == kind]
    if focus:
        rows = rows[rows["system_focus"] == focus]
    if system_id:
        rows = rows[rows["system_id"] == system_id]
    if ftype == "behavioral":
        rows = rows[rows["is_behavioral"] == "Y"]
    elif ftype:
        label = TYPE_DISPLAY.get(ftype, ftype)
        rows = rows[rows["facility_type_label"] == label]
    if status == "operating":
        rows = rows[rows["facility_status"].isin(OPERATING_STATUSES)]
    elif status == "inactive":
        rows = rows[~rows["facility_status"].isin(OPERATING_STATUSES)]
    elif status:
        rows = rows[rows["facility_status"] == status]
    if query:
        q = query.strip().lower()
        rows = rows[rows["system_name"].str.lower().str.contains(re.escape(q), na=False)
                    | rows["name"].str.lower().str.contains(re.escape(q), na=False)]
    return rows


def _clear_cache() -> None:
    """Test hook — drop the memoized assignment + rollup."""
    _assigned_cached.cache_clear()
    _cached_map.cache_clear()
    _last_active_year_by_ccn.cache_clear()
