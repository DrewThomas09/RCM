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

A rejected approach, recorded so it doesn't get re-proposed: matching
against a CCN's **historical** names from earlier cost reports. It
sounds like free coverage — HCRIS carries every filing year's name — but
measuring it found only 7 candidates, and inspecting them showed the
mechanism points the wrong way. A facility that renamed *away* from a
system brand has usually been divested: Mercy Hospital and Medical
Center (Chicago) is now Insights Hospital and Medical Center because
Insight bought it, so matching it to CommonSpirit on the old name would
assert an ownership that ended. Latest name only.

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

from .cms_facility_names import load_cms_facilities
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
# Post-acute and outpatient focuses. These operators hold thousands of
# CCNs between them and not one acute hospital, so a registry that stops
# at FOCUS_ACUTE cannot see them at all.
FOCUS_DIALYSIS = "Dialysis"
FOCUS_HOME_HEALTH = "Home Health"
FOCUS_HOSPICE = "Hospice"
FOCUS_SNF = "Skilled Nursing"
# Ambulance and air-medical operators hold NPIs, not CCNs. They are
# reachable only through the NPI registry, and the footprint guard has
# to know not to demand a CCN footprint of them.
FOCUS_EMS = "Emergency Medical"

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
#
# This first tuple is the acute estate: brands that appear in HCRIS.
# ``POST_ACUTE_REGISTRY`` below covers operators that live almost
# entirely outside it, and the two are concatenated into
# :data:`SYSTEM_REGISTRY`.

ACUTE_REGISTRY: Tuple[SystemDef, ...] = (
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
            "CO:^MEDICAL CENTER OF AURORA", "NC:^MISSION HOSPITAL",
        ),
        note="Largest US for-profit operator; many facilities rebranded "
             "to the HCA / Medical City / TriStar house brands.",
    ),
    SystemDef(
        "tenet", "Tenet Healthcare", KIND_FOR_PROFIT, FOCUS_ACUTE, "TX",
        patterns=("^HOSPITALS OF PROVIDENCE",
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
        patterns=("^HOUSTON METHODIST", "TX:^METHODIST SUGAR LAND",
                  "TX:^METHODIST WILLOWBROOK", "TX:^METHODIST WEST HOUSTON",
                  "TX:^SAN JACINTO METHODIST", "TX:^METHODIST BAYTOWN"),
    ),
    SystemDef(
        "methodist_dallas", "Methodist Health System (Dallas)", KIND_NONPROFIT, FOCUS_ACUTE, "TX",
        patterns=("TX:^METHODIST DALLAS", "TX:^METHODIST CHARLTON",
                  "TX:^METHODIST RICHARDSON", "TX:^METHODIST MANSFIELD",
                  "TX:^METHODIST MIDLOTHIAN", "TX:^METHODIST SOUTHLAKE",
                  "TX:^METHODIST MCKINNEY", "TX:^METHODIST HOSPITAL FOR SURGERY",
                  "TX:^METHODIST REHABILITATION HOSPITAL"),
        note="A bare '^METHODIST' scoped to Texas was swallowing three "
             "unrelated Methodist organizations — Dallas, Houston and San "
             "Antonio each run facilities named METHODIST <something>. Each "
             "now claims only its own.",
    ),
    SystemDef(
        "methodist_san_antonio", "Methodist Healthcare (San Antonio)",
        KIND_FOR_PROFIT, FOCUS_ACUTE, "TX",
        patterns=("TX:^METHODIST HOSPITAL SOUTH", "TX:^METHODIST STONE OAK",
                  "TX:^METHODIST AMBULATORY", "TX:^METHODIST TEXSAN",
                  "TX:^METHODIST SPECIALTY"),
        note="HCA joint venture with Methodist Healthcare Ministries — a "
             "different organization from both Dallas and Houston Methodist.",
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
        patterns=("^NOVANT", "NC:^PRESBYTERIAN HOSPITAL", "NC:^FORSYTH MEMORIAL"),
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
                  "NY:^NEW YORK GRACIE SQUARE"),
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
        patterns=("^CLEVELAND CLINIC", "^CCF ", "^FAIRVIEW HOSPITAL",
                  "^HILLCREST HOSPITAL", "^MARYMOUNT HOSPITAL",
                  "^LUTHERAN HOSPITAL"),
        states=("OH", "FL"),
    ),
    SystemDef(
        "uh_ohio", "University Hospitals (Ohio)", KIND_ACADEMIC, FOCUS_ACUTE, "OH",
        # Scoped to Ohio: University Hospital in Newark NJ files as
        # "UH - UNIVERSITY HOSPITAL" and is a different organization.
        patterns=("^UH ", "^UNIVERSITY HOSPITALS"),
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
        patterns=("^MUSC", "^MEDICAL UNIVERSITY OF SOUTH CAROLINA"),
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
        patterns=("^UT ", "TX:^UNIVERSITY OF TEXAS"),
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
        patterns=("^QUEENS MEDICAL", "^QUEENS HEALTH"),
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
        patterns=("KY:^MEDICAL CENTER",),
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
                  "UT:^DAVIS HOSPITAL", "UT:^MOUNTAIN POINT MEDICAL",
                  "FL:^NORTH SHORE MEDICAL CENTER"),
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
        "parkland", "Parkland Health", KIND_GOVERNMENT, FOCUS_ACUTE, "TX",
        patterns=("TX:^PARKLAND", "TX:^DALLAS CO"),
        note="Files as the hospital district, not the hospital name.",
    ),
    SystemDef(
        "urmc", "University of Rochester Medical Center",
        KIND_ACADEMIC, FOCUS_ACUTE, "NY",
        patterns=("NY:^STRONG MEMORIAL", "NY:^HIGHLAND HOSPITAL",
                  "NY:^THOMPSON HEALTH"),
    ),
    SystemDef(
        "lakeland_regional", "Lakeland Regional Health", KIND_NONPROFIT, FOCUS_ACUTE, "FL",
        patterns=("FL:^LAKELAND REGIONAL",),
    ),
    SystemDef(
        "community_fresno", "Community Health System (Fresno)",
        KIND_NONPROFIT, FOCUS_ACUTE, "CA",
        patterns=("CA:^COMMUNITY REGIONAL", "CA:^CLOVIS COMMUNITY",
                  "CA:^COMMUNITY BEHAVIORAL HEALTH CENTER"),
    ),
    SystemDef(
        "michigan_medicine", "Michigan Medicine", KIND_ACADEMIC, FOCUS_ACUTE, "MI",
        patterns=("^UNIVERSITY OF MICHIGAN", "^MICHIGAN MEDICINE", "MI:^UNIV OF MI"),
    ),
    SystemDef(
        "huntsville", "Huntsville Hospital Health System",
        KIND_GOVERNMENT, FOCUS_ACUTE, "AL",
        patterns=("AL:^HUNTSVILLE HOSPITAL", "AL:^MADISON HOSPITAL",
                  "AL:^HELEN KELLER"),
    ),
    SystemDef(
        "texas_childrens", "Texas Children's Hospital",
        KIND_NONPROFIT, FOCUS_CHILDRENS, "TX",
        patterns=("TX:^TEXAS CHILDRENS",),
    ),
    SystemDef(
        "camc", "CAMC Health System", KIND_NONPROFIT, FOCUS_ACUTE, "WV",
        patterns=("WV:^CHARLESTON AREA MEDICAL",),
    ),
    SystemDef(
        "ou_health", "OU Health", KIND_ACADEMIC, FOCUS_ACUTE, "OK",
        patterns=("OK:^OU MEDICAL", "OK:^OU HEALTH", "OK:^OKLAHOMA CHILDRENS"),
    ),
    SystemDef(
        "santa_clara_county", "Santa Clara Valley Healthcare",
        KIND_GOVERNMENT, FOCUS_ACUTE, "CA",
        patterns=("CA:^SANTA CLARA VALLEY", "CA:^OCONNOR HOSPITAL",
                  "CA:^SAINT LOUISE REGIONAL"),
    ),
    SystemDef(
        "osu_wexner", "Ohio State Wexner Medical Center", KIND_ACADEMIC, FOCUS_ACUTE, "OH",
        patterns=("^OHIO STATE UNIVERSITY", "OH:^JAMES CANCER"),
    ),
    SystemDef(
        "uk_healthcare", "UK HealthCare", KIND_ACADEMIC, FOCUS_ACUTE, "KY",
        patterns=("^UNIVERSITY OF KENTUCKY", "KY:^UNIVERSITY HOSPITAL"),
    ),
    SystemDef(
        "kaleida", "Kaleida Health", KIND_NONPROFIT, FOCUS_ACUTE, "NY",
        patterns=("^KALEIDA", "NY:^BUFFALO GENERAL", "NY:^MILLARD FILLMORE"),
    ),
    SystemDef(
        "ca_state_hospitals", "California Dept of State Hospitals",
        KIND_GOVERNMENT, FOCUS_BEHAVIORAL, "CA",
        patterns=("CA:^METROPOLITAN STATE HOSPITAL", "CA:^NAPA STATE HOSPITAL",
                  "CA:^PATTON STATE HOSPITAL", "CA:^ATASCADERO STATE",
                  "CA:^COALINGA STATE HOSPITAL"),
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

    # ── From the candidate-cluster backlog ─────────────────────────
    #
    # Multi-hospital name families the scan surfaced that resolve to one
    # operator. What the scan leaves behind at this depth — MEMORIAL
    # HOSPITAL, COMMUNITY HOSPITAL, SAINT MARY, GOOD SAMARITAN, DOCTORS
    # HOSPITAL — are shared names whose members have different owners,
    # and no amount of further passes will change that.
    SystemDef(
        "penn_highlands", "Penn Highlands Healthcare", KIND_NONPROFIT,
        FOCUS_ACUTE, "PA",
        patterns=("PA:^PENN HIGHLANDS",),
    ),
    SystemDef(
        "mcleod", "McLeod Health", KIND_NONPROFIT, FOCUS_ACUTE, "SC",
        patterns=("SC:^MCLEOD",),
    ),
    SystemDef(
        "west_tennessee", "West Tennessee Healthcare", KIND_GOVERNMENT,
        FOCUS_ACUTE, "TN",
        patterns=("TN:^WEST TENNESSEE HEALTHCARE",),
    ),
    SystemDef(
        "st_margarets_il", "St. Margaret's Health", KIND_NONPROFIT,
        FOCUS_ACUTE, "IL",
        patterns=("IL:^SAINT MARGARETS",),
    ),
    SystemDef(
        "whittier_ma", "Whittier Health Network", KIND_FOR_PROFIT,
        FOCUS_LTACH, "MA",
        # Massachusetts only: Whittier Hospital Medical Center in
        # Whittier CA is an unrelated acute hospital.
        patterns=("MA:^WHITTIER",),
    ),
    SystemDef(
        "kpc_promise", "KPC Promise Healthcare", KIND_FOR_PROFIT,
        FOCUS_LTACH, "CA",
        patterns=("^KPC PROMISE",),
    ),
    SystemDef(
        "sage_la", "Sage Rehabilitation", KIND_FOR_PROFIT, FOCUS_REHAB, "LA",
        # Louisiana only: Sage Memorial (AZ) and Sage West (WY) are
        # unrelated hospitals that happen to start with the word.
        patterns=("LA:^SAGE SPECIALTY", "LA:^SAGE REHAB"),
    ),
    SystemDef(
        "wellbridge", "Wellbridge Healthcare", KIND_FOR_PROFIT,
        FOCUS_BEHAVIORAL, "TX",
        patterns=("^WELLBRIDGE",),
    ),
    SystemDef(
        "vista_health_ar", "Vista Health", KIND_FOR_PROFIT, FOCUS_BEHAVIORAL, "AR",
        patterns=("AR:^VISTA HEALTH",),
    ),
)


# ── The post-acute and outpatient registry ─────────────────────────
#
# A hospital-only registry undercounts a health system twice over.
# It misses the 42,387 dialysis stations, nursing homes, home-health
# agencies and hospices that hold their own CCNs, and it misses the
# operators whose entire estate is those CCNs — DaVita has no hospital,
# and neither does Amedisys or Life Care Centers of America.
#
# Every entry below was derived by clustering the unmapped names in the
# six CMS Compare files and keeping the clusters that name an operator
# rather than a service line. "HOSPICE OF …" (208 facilities, 40
# states) is a description, not a company, and is deliberately absent;
# "^CENTERWELL" (226 agencies) is a company.
#
# Three brands that read as national operators are also deliberately
# absent, because the pattern that would catch them catches an
# unrelated hospital: ^GENESIS HEALTHCARE hits Genesis Healthcare
# System in Zanesville OH, ^BROOKDALE hits Brookdale Hospital Medical
# Center in Brooklyn, and ^ARBOR hits Arbor Health Morton Hospital in
# Washington. Precision beats reach — a wrong parent is worse than no
# parent, because nobody audits a mapping that looks complete.
#
# Encompass Health, Kindred, Select Medical and Ernest Health are NOT
# repeated here. They already sit in the acute registry and their
# patterns reach their post-acute CCNs unchanged.

POST_ACUTE_REGISTRY: Tuple[SystemDef, ...] = (
    # ── Dialysis ───────────────────────────────────────────────────
    #
    # The dialysis file is the only Compare file that publishes a
    # parent chain, so these entries are reached two ways: by name, and
    # by CHAIN_ALIASES below. Fresenius is the reason both are needed —
    # it operates under five distinct banners (FMC, Fresenius Kidney
    # Care, Bio-Medical Applications, Liberty Dialysis, Renal Care
    # Group), all of which CMS files under one chain string.
    SystemDef(
        "fresenius", "Fresenius Medical Care", KIND_FOR_PROFIT, FOCUS_DIALYSIS, "MA",
        patterns=("^FRESENIUS", "^FMC ", "^BIO MEDICAL APPLICATIONS",
                  "^BMA OF", "^LIBERTY DIALYSIS", "^RENAL CARE GROUP"),
    ),
    SystemDef(
        "davita", "DaVita Kidney Care", KIND_FOR_PROFIT, FOCUS_DIALYSIS, "CO",
        patterns=("^DAVITA",),
    ),
    SystemDef(
        "us_renal_care", "U.S. Renal Care", KIND_FOR_PROFIT, FOCUS_DIALYSIS, "TX",
        patterns=("^US RENAL CARE", "^USRC "),
    ),
    SystemDef(
        "dci", "Dialysis Clinic, Inc.", KIND_NONPROFIT, FOCUS_DIALYSIS, "TN",
        patterns=("^DIALYSIS CLINIC INC", "^DCI "),
    ),
    SystemDef(
        "american_renal", "Innovative Renal Care (American Renal)",
        KIND_FOR_PROFIT, FOCUS_DIALYSIS, "MA",
        patterns=("^AMERICAN RENAL", "^INNOVATIVE RENAL"),
        note="The American Renal name is gone from the current snapshot "
             "and carried anyway — the rebrand to Innovative Renal Care "
             "is recent enough that an older extract still uses it.",
    ),
    SystemDef(
        "satellite_healthcare", "Satellite Healthcare", KIND_NONPROFIT,
        FOCUS_DIALYSIS, "CA",
        patterns=("^SATELLITE DIALYSIS", "^SATELLITE HEALTHCARE"),
        note="Both banners are in use; the chain column reaches the rest.",
    ),
    SystemDef(
        "northwest_kidney", "Northwest Kidney Centers", KIND_NONPROFIT,
        FOCUS_DIALYSIS, "WA",
        patterns=("WA:^NORTHWEST KIDNEY",),
        note="Reached mainly through the published chain column — the "
             "facility names are place names, not the brand.",
    ),
    SystemDef(
        "cdc_cleveland", "Centers for Dialysis Care", KIND_NONPROFIT,
        FOCUS_DIALYSIS, "OH",
        patterns=("OH:^CENTERS FOR DIALYSIS CARE",),
        note="Chain-column only in the current snapshot.",
    ),
    SystemDef(
        "puget_sound_kidney", "Puget Sound Kidney Centers", KIND_NONPROFIT,
        FOCUS_DIALYSIS, "WA",
        patterns=("WA:^PUGET SOUND KIDNEY",),
    ),

    # ── Home health and hospice ────────────────────────────────────
    SystemDef(
        "centerwell", "CenterWell Home Health (Humana)", KIND_FOR_PROFIT,
        FOCUS_HOME_HEALTH, "KY",
        patterns=("^CENTERWELL",),
    ),
    SystemDef(
        "enhabit", "Enhabit Home Health & Hospice", KIND_FOR_PROFIT,
        FOCUS_HOME_HEALTH, "TX",
        patterns=("^ENHABIT",),
    ),
    SystemDef(
        "amedisys", "Amedisys", KIND_FOR_PROFIT, FOCUS_HOME_HEALTH, "LA",
        patterns=("^AMEDISYS", "^COMPASSIONATE CARE HOSPICE",
                  # Acquired brands kept in the market.
                  "^BEACON HOSPICE", "^ASERACARE"),
    ),
    SystemDef(
        "gentiva", "Gentiva", KIND_FOR_PROFIT, FOCUS_HOSPICE, "GA",
        patterns=("^GENTIVA",),
    ),
    SystemDef(
        "bayada", "BAYADA Home Health Care", KIND_NONPROFIT,
        FOCUS_HOME_HEALTH, "NJ",
        patterns=("^BAYADA",),
    ),
    SystemDef(
        "elara_caring", "Elara Caring", KIND_FOR_PROFIT, FOCUS_HOME_HEALTH, "TX",
        patterns=("^ELARA CARING",),
    ),
    SystemDef(
        "aveanna", "Aveanna Healthcare", KIND_FOR_PROFIT, FOCUS_HOME_HEALTH, "GA",
        patterns=("^AVEANNA",),
    ),
    SystemDef(
        "interim_healthcare", "Interim HealthCare", KIND_FOR_PROFIT,
        FOCUS_HOME_HEALTH, "FL",
        patterns=("^INTERIM HEALTHCARE",),
    ),
    SystemDef(
        "accentcare", "AccentCare", KIND_FOR_PROFIT, FOCUS_HOME_HEALTH, "TX",
        patterns=("^ACCENTCARE",),
    ),
    SystemDef(
        "adoration_health", "Adoration Home Health & Hospice", KIND_FOR_PROFIT,
        FOCUS_HOME_HEALTH, "TN",
        patterns=("^ADORATION",),
    ),
    SystemDef(
        "maxim_healthcare", "Maxim Healthcare Services", KIND_FOR_PROFIT,
        FOCUS_HOME_HEALTH, "MD",
        patterns=("^MAXIM HEALTHCARE",),
    ),
    SystemDef(
        "angels_care", "Angels Care Home Health", KIND_FOR_PROFIT,
        FOCUS_HOME_HEALTH, "TX",
        patterns=("^ANGELS CARE HOME",),
    ),
    SystemDef(
        "vitalcaring", "VitalCaring Group", KIND_FOR_PROFIT, FOCUS_HOME_HEALTH, "TX",
        patterns=("^VITALCARING",),
    ),
    SystemDef(
        "suncrest", "Suncrest Home Health & Hospice", KIND_FOR_PROFIT,
        FOCUS_HOME_HEALTH, "TN",
        # NOT bare ^SUNCREST: "SUNCREST HEALTHCARE CENTER" is an
        # unrelated nursing home.
        patterns=("^SUNCREST HOME", "^SUNCREST HOSPICE"),
    ),
    SystemDef(
        "traditions_health", "Traditions Health", KIND_FOR_PROFIT, FOCUS_HOSPICE, "TX",
        patterns=("^TRADITIONS HEALTH",),
    ),
    SystemDef(
        "vitas", "VITAS Healthcare (Chemed)", KIND_FOR_PROFIT, FOCUS_HOSPICE, "OH",
        patterns=("^VITAS",),
    ),
    SystemDef(
        "compassus", "Compassus", KIND_FOR_PROFIT, FOCUS_HOSPICE, "TN",
        patterns=("^COMPASSUS", "^HOSPICE COMPASSUS"),
    ),
    SystemDef(
        "bristol_hospice", "Bristol Hospice", KIND_FOR_PROFIT, FOCUS_HOSPICE, "UT",
        patterns=("^BRISTOL HOSPICE",),
    ),
    SystemDef(
        "st_croix_hospice", "St. Croix Hospice", KIND_FOR_PROFIT, FOCUS_HOSPICE, "MN",
        patterns=("^SAINT CROIX HOSPICE",),
    ),
    SystemDef(
        "heart_to_heart_hospice", "Heart to Heart Hospice", KIND_FOR_PROFIT,
        FOCUS_HOSPICE, "TX",
        patterns=("^HEART TO HEART HOSPICE",),
    ),
    SystemDef(
        "heartland_care", "Heartland Home Health & Hospice", KIND_FOR_PROFIT,
        FOCUS_HOSPICE, "OH",
        patterns=("^HEARTLAND HOSPICE", "^HEARTLAND HOME"),
    ),
    SystemDef(
        "harbor_hospice", "Harbor Hospice", KIND_FOR_PROFIT, FOCUS_HOSPICE, "TX",
        # Scoped: a separate, unrelated Harbor Hospice operates in
        # Muskegon MI.
        patterns=("^HARBOR HOSPICE",),
        states=("TX", "LA", "OK", "MO", "KS"),
    ),

    # ── Skilled nursing ────────────────────────────────────────────
    SystemDef(
        "life_care_centers", "Life Care Centers of America", KIND_FOR_PROFIT,
        FOCUS_SNF, "TN",
        patterns=("^LIFE CARE CENTER",),
    ),
    SystemDef(
        "good_samaritan_society", "Good Samaritan Society (Sanford Health)",
        KIND_NONPROFIT, FOCUS_SNF, "SD",
        # NOT bare ^GOOD SAMARITAN: a dozen unrelated Good Samaritan
        # hospitals carry that name. "SOCIETY" is the discriminator.
        patterns=("^GOOD SAMARITAN SOCIETY",),
    ),
    SystemDef(
        "pruitthealth", "PruittHealth", KIND_FOR_PROFIT, FOCUS_SNF, "GA",
        patterns=("^PRUITTHEALTH",),
    ),
    SystemDef(
        "complete_care", "Complete Care", KIND_FOR_PROFIT, FOCUS_SNF, "NJ",
        patterns=("^COMPLETE CARE AT",),
    ),
    SystemDef(
        "avir_healthcare", "Avir Healthcare", KIND_FOR_PROFIT, FOCUS_SNF, "TX",
        patterns=("TX:^AVIR AT",),
    ),
    SystemDef(
        "aviata_health", "Aviata Health", KIND_FOR_PROFIT, FOCUS_SNF, "FL",
        patterns=("FL:^AVIATA AT",),
    ),
    SystemDef(
        "autumn_lake", "Autumn Lake Healthcare", KIND_FOR_PROFIT, FOCUS_SNF, "MD",
        patterns=("^AUTUMN LAKE",),
    ),
    SystemDef(
        "national_healthcare", "National HealthCare Corporation (NHC)",
        KIND_FOR_PROFIT, FOCUS_SNF, "TN",
        patterns=("^NHC HEALTHCARE", "^NHC HOMECARE"),
    ),
    SystemDef(
        "signature_snf", "Signature HealthCARE", KIND_FOR_PROFIT, FOCUS_SNF, "KY",
        # NOT bare ^SIGNATURE HEALTHCARE: Signature Healthcare Brockton
        # Hospital in Massachusetts is an unrelated acute system.
        patterns=("^SIGNATURE HEALTHCARE OF", "^SIGNATURE HEALTHCARE AT"),
    ),
    SystemDef(
        "medilodge", "MediLodge", KIND_FOR_PROFIT, FOCUS_SNF, "MI",
        patterns=("MI:^MEDILODGE",),
    ),
    SystemDef(
        "laurel_health_care", "Laurel Health Care", KIND_FOR_PROFIT, FOCUS_SNF, "OH",
        patterns=("^LAURELS OF",),
    ),
    SystemDef(
        "waters_senior_living", "The Waters", KIND_FOR_PROFIT, FOCUS_SNF, "IN",
        patterns=("^WATERS OF",),
        states=("IN", "TN"),
    ),
    SystemDef(
        "diversicare", "Diversicare Healthcare Services", KIND_FOR_PROFIT,
        FOCUS_SNF, "TN",
        patterns=("^DIVERSICARE",),
    ),
    SystemDef(
        "majestic_care", "Majestic Care", KIND_FOR_PROFIT, FOCUS_SNF, "IN",
        patterns=("^MAJESTIC CARE",),
    ),
    SystemDef(
        "accura_healthcare", "Accura Healthcare", KIND_FOR_PROFIT, FOCUS_SNF, "IA",
        patterns=("^ACCURA HEALTHCARE",),
    ),
    SystemDef(
        "ignite_medical", "Ignite Medical Resorts", KIND_FOR_PROFIT, FOCUS_SNF, "IL",
        patterns=("^IGNITE MEDICAL",),
    ),
    SystemDef(
        "focused_care", "Focused Care", KIND_FOR_PROFIT, FOCUS_SNF, "TX",
        patterns=("TX:^FOCUSED CARE",),
    ),
    SystemDef(
        "optalis_health", "Optalis Health & Rehabilitation", KIND_FOR_PROFIT,
        FOCUS_SNF, "MI",
        patterns=("MI:^OPTALIS",),
    ),
    SystemDef(
        "autumn_corp", "Autumn Corporation", KIND_FOR_PROFIT, FOCUS_SNF, "NC",
        patterns=("^AUTUMN CARE OF",),
        states=("NC", "VA"),
    ),

    # ── Second pass ────────────────────────────────────────────────
    #
    # A re-clustering of what the first pass left unmapped, down to a
    # 12-facility floor. The same rule applies: a cluster earns an entry
    # only when it names an operator. "HOSPICE OF" (206 facilities, 40
    # states), "HOME HEALTH", "COMMUNITY HOME HEALTH", "MOUNTAIN VIEW"
    # and "VALLEY VIEW" are all larger than anything below and all
    # absent, because they are descriptions and place names shared by
    # organizations with nothing to do with each other.
    #
    # Several of these are acquisitions that kept the acquired brand,
    # and they are folded into the acquirer rather than given their own
    # row: Beacon Hospice and AseraCare are Amedisys, Hospice Compassus
    # is Compassus, NHC Homecare is National HealthCare. A rollup that
    # lists an acquirer's brands as separate operators is not a rollup.
    SystemDef(
        "brighton_hospice", "Brighton Hospice", KIND_FOR_PROFIT, FOCUS_HOSPICE, "MN",
        patterns=("^BRIGHTON HOSPICE",),
    ),
    SystemDef(
        "three_oaks_hospice", "Three Oaks Hospice", KIND_FOR_PROFIT,
        FOCUS_HOSPICE, "TX",
        patterns=("^THREE OAKS HOSPICE",),
    ),
    SystemDef(
        "agape_care", "Agape Care Group", KIND_FOR_PROFIT, FOCUS_HOSPICE, "SC",
        patterns=("^ACG HOSPICE",),
    ),
    SystemDef(
        "legacy_hospice", "Legacy Hospice", KIND_FOR_PROFIT, FOCUS_HOSPICE, "OK",
        patterns=("^LEGACY HOSPICE",),
    ),
    SystemDef(
        "moments_hospice", "Moments Hospice", KIND_FOR_PROFIT, FOCUS_HOSPICE, "MN",
        patterns=("^MOMENTS HOSPICE",),
    ),
    SystemDef(
        "serenity_hospice", "Serenity Hospice", KIND_FOR_PROFIT, FOCUS_HOSPICE, "MO",
        patterns=("^SERENITY HOSPICE",),
    ),
    SystemDef(
        "eden_hospice", "Eden Hospice", KIND_FOR_PROFIT, FOCUS_HOSPICE, "MO",
        patterns=("^EDEN HOSPICE",),
    ),
    SystemDef(
        "affinity_care", "Affinity Care", KIND_FOR_PROFIT, FOCUS_HOSPICE, "AL",
        patterns=("^AFFINITY CARE OF", "^AFFINITY HOSPICE"),
    ),
    SystemDef(
        "st_joseph_hospice", "St. Joseph Hospice", KIND_FOR_PROFIT,
        FOCUS_HOSPICE, "LA",
        patterns=("^SAINT JOSEPH HOSPICE",),
    ),
    SystemDef(
        "elite_home_health", "Elite Home Health & Hospice", KIND_FOR_PROFIT,
        FOCUS_HOME_HEALTH, "TX",
        patterns=("^ELITE HOME HEALTH", "^ELITE HOSPICE"),
    ),
    SystemDef(
        "concierge_home_care", "Concierge Home Care", KIND_FOR_PROFIT,
        FOCUS_HOME_HEALTH, "FL",
        patterns=("^CONCIERGE HOME CARE",),
    ),
    SystemDef(
        "mederi_caretenders", "Mederi Caretenders", KIND_FOR_PROFIT,
        FOCUS_HOME_HEALTH, "FL",
        patterns=("^MEDERI CARETENDERS",),
    ),
    SystemDef(
        "pinnacle_home_care", "Pinnacle Home Care", KIND_FOR_PROFIT,
        FOCUS_HOME_HEALTH, "FL",
        patterns=("FL:^PINNACLE HOME CARE",),
    ),
    SystemDef(
        "assured_home_health", "Assured Home Health", KIND_FOR_PROFIT,
        FOCUS_HOME_HEALTH, "WA",
        patterns=("^ASSURED HOME HEALTH",),
    ),
    SystemDef(
        "aperion_care", "Aperion Care", KIND_FOR_PROFIT, FOCUS_SNF, "IL",
        patterns=("^APERION CARE",),
    ),
    SystemDef(
        "brickyard_healthcare", "Brickyard Healthcare", KIND_FOR_PROFIT,
        FOCUS_SNF, "IN",
        patterns=("IN:^BRICKYARD",),
    ),
    SystemDef(
        "solaris_healthcare", "Solaris Healthcare", KIND_FOR_PROFIT, FOCUS_SNF, "FL",
        patterns=("FL:^SOLARIS HEALTHCARE",),
    ),
    SystemDef(
        "careone", "CareOne", KIND_FOR_PROFIT, FOCUS_SNF, "NJ",
        patterns=("^CAREONE AT",),
    ),
    SystemDef(
        "mission_point_snf", "Mission Point Healthcare Services",
        KIND_FOR_PROFIT, FOCUS_SNF, "MI",
        patterns=("MI:^MISSION POINT",),
    ),
    SystemDef(
        "apple_rehab", "Apple Rehab", KIND_FOR_PROFIT, FOCUS_SNF, "CT",
        patterns=("^APPLE REHAB",),
        states=("CT", "RI"),
    ),
    SystemDef(
        "heritage_hall", "Heritage Hall", KIND_FOR_PROFIT, FOCUS_SNF, "VA",
        patterns=("^HERITAGE HALL",),
        states=("VA", "WV"),
    ),
    SystemDef(
        "advanced_health_care", "Advanced Health Care", KIND_FOR_PROFIT,
        FOCUS_SNF, "UT",
        patterns=("^ADVANCED HEALTH CARE OF",),
    ),
    SystemDef(
        "aspire_senior_living", "Aspire Senior Living", KIND_FOR_PROFIT,
        FOCUS_SNF, "MO",
        patterns=("MO:^ASPIRE SENIOR LIVING",),
    ),
    SystemDef(
        "dialyze_direct", "Dialyze Direct", KIND_FOR_PROFIT, FOCUS_DIALYSIS, "NJ",
        patterns=("^DIALYZE DIRECT",),
    ),
    SystemDef(
        "dialysis_care_center", "Dialysis Care Center", KIND_FOR_PROFIT,
        FOCUS_DIALYSIS, "IL",
        patterns=("^DIALYSIS CARE CENTER",),
    ),
    # Reached through the published chain column rather than a name.
    SystemDef(
        "atlantis_healthcare", "Atlantis Healthcare Group", KIND_FOR_PROFIT,
        FOCUS_DIALYSIS, "PR",
        patterns=("PR:^ATLANTIS",),
    ),
    SystemDef(
        "greenfield_health", "Greenfield Health Systems", KIND_NONPROFIT,
        FOCUS_DIALYSIS, "MI",
        patterns=("^GREENFIELD HEALTH",),
    ),
    SystemDef(
        "atlantic_dms", "Atlantic Dialysis Management Services",
        KIND_FOR_PROFIT, FOCUS_DIALYSIS, "NY",
        patterns=("NY:^ATLANTIC DMS",),
    ),
    SystemDef(
        "dsi_renal", "Diversified Specialty Institutes (DSI)", KIND_FOR_PROFIT,
        FOCUS_DIALYSIS, "TN",
        patterns=("^DSI RENAL",),
        note="Chain-column only — the facilities file under local names.",
    ),
    SystemDef(
        "central_florida_kidney", "Central Florida Kidney Centers",
        KIND_FOR_PROFIT, FOCUS_DIALYSIS, "FL",
        patterns=("FL:^CENTRAL FLORIDA KIDNEY",),
    ),
)


# ── Ambulance and air-medical operators ────────────────────────────
#
# These hold NPIs and no CCNs, so they are invisible to every facility
# file and reachable only through the NPI registry. They earn a place
# for the same reason DaVita does: a national operator running the same
# service under one owner in thirty states is exactly what a rollup is
# supposed to see.
#
# The consolidation is severe and the brands do not advertise it, which
# is why these are worth writing down. Global Medical Response operates
# as AMR on the ground and as Air Evac, Med-Trans, Guardian Flight,
# REACH and EagleMed in the air; Air Methods files as Rocky Mountain
# Holdings, LifeNet and Mercy Air Service. The CMS PECOS Associate
# Control ID is what makes this checkable rather than asserted — those
# NPIs share an enrolment.
#
# Deliberately absent: Lifeguard Ambulance Service (30 NPIs, 12 states).
# It is plainly one operator, but this data does not say which, and
# naming the wrong parent is the failure mode that matters.

EMS_REGISTRY: Tuple[SystemDef, ...] = (
    SystemDef(
        "global_medical_response", "Global Medical Response",
        KIND_FOR_PROFIT, FOCUS_EMS, "CO",
        patterns=("^AMERICAN MEDICAL RESPONSE", "^AMR ", "^RURAL METRO",
                  "^AIR EVAC", "^MED TRANS", "^GUARDIAN FLIGHT",
                  "^REACH AIR MEDICAL", "^EAGLEMED"),
    ),
    SystemDef(
        "air_methods", "Air Methods", KIND_FOR_PROFIT, FOCUS_EMS, "CO",
        patterns=("^ROCKY MOUNTAIN HOLDINGS", "^AIR METHODS",
                  "^LIFENET INC", "^MERCY AIR SERVICE"),
    ),
    SystemDef(
        "phi_health", "PHI Health", KIND_FOR_PROFIT, FOCUS_EMS, "LA",
        patterns=("^PHI HEALTH", "^PHI AIR MEDICAL"),
    ),
    SystemDef(
        "falck", "Falck", KIND_FOR_PROFIT, FOCUS_EMS, "CA",
        patterns=("^FALCK",),
    ),
)


SYSTEM_REGISTRY: Tuple[SystemDef, ...] = (
    ACUTE_REGISTRY + POST_ACUTE_REGISTRY + EMS_REGISTRY)


# ── Published parent chains ────────────────────────────────────────
#
# CMS's dialysis file names a parent for 6,699 of 7,557 facilities.
# That column outranks anything the matcher can infer from a facility
# name, because it is the operator's own answer rather than our reading
# of their signage — and it reaches facilities whose names never carry
# the brand at all (Northwest Kidney Centers files eleven facilities as
# place names).
#
# Keys are matched after :func:`normalize_name`. A chain string with no
# entry here is still carried on the row as ``chain_name``: knowing a
# facility belongs to "Atlantis Healthcare Group" is worth more than
# calling it independent, even when no registry entry exists yet.

CHAIN_ALIASES: Dict[str, str] = {
    "DAVITA": "davita",
    "FRESENIUS MEDICAL CARE": "fresenius",
    "US RENAL CARE INC": "us_renal_care",
    "DIALYSIS CLINIC INC": "dci",
    "AMERICAN RENAL ASSOCIATES": "american_renal",
    "SATELLITE HEALTHCARE": "satellite_healthcare",
    "SATELLITE DIALYSIS": "satellite_healthcare",
    "NORTHWEST KIDNEY CENTERS": "northwest_kidney",
    "CENTERS FOR DIALYSIS CARE": "cdc_cleveland",
    "PUGET SOUND KIDNEY CENTERS": "puget_sound_kidney",
    "ATLANTIS HEALTHCARE GROUP": "atlantis_healthcare",
    "GREENFIELD HEALTH SYSTEMS": "greenfield_health",
    "ATLANTIC DIALYSIS MANAGEMENT SERVICES": "atlantic_dms",
    "DIVERSIFIED SPECIALTY INSTITUTES DSI": "dsi_renal",
    "CENTRAL FLORIDA KIDNEY CENTERS": "central_florida_kidney",
    # Health systems that run their own dialysis under the parent brand.
    # The chain column reaches these without a single extra pattern.
    "KAISER PERMANENTE": "kaiser",
    "SANFORD HEALTH": "sanford",
    "INTERMOUNTAIN HEALTHCARE": "intermountain",
    "MAYO CLINIC DIALYSIS": "mayo",
    "GUNDERSEN LUTHERAN": "gundersen",
    "UPMC HEALTH SYSTEM": "upmc",
    "MEMORIAL HERMANN HEALTHCARE SYSTEM": "memorial_hermann",
    "SCOTT AND WHITE MEMORIAL HOSPITAL": "baylor",
}


# ── CCN overrides ──────────────────────────────────────────────────
#
# The escape hatch for facilities a name can never resolve. Two cases
# recur, and both are visible in the Texas Methodist estate:
#
#   1. Two unrelated organizations file identical names. Houston
#      Methodist's flagship is "THE METHODIST HOSPITAL" and Methodist
#      Healthcare San Antonio's is "METHODIST HOSPITAL" — the same
#      string once normalized, in the same state, 200 miles apart.
#   2. HCRIS truncates at ~36 characters and abbreviates, so
#      "Hospital of the University of Pennsylvania" files as
#      "HOSPITAL OF THE UNIV OF PENNA" and no pattern written from the
#      real name can reach it.
#
# Every entry is one named facility, verified individually, and shows
# on the page as its own match basis — a reader can see the assignment
# was asserted rather than derived. Reach for a pattern first; an
# override is for when the name genuinely cannot carry the answer.

CCN_OVERRIDES: Dict[str, str] = {
    # Identical names, different organizations (see case 1).
    "450358": "houston_methodist",       # THE METHODIST HOSPITAL, Houston
    "450388": "methodist_san_antonio",   # METHODIST HOSPITAL, San Antonio
    # Truncated / abbreviated beyond pattern reach (see case 2).
    "390111": "penn_medicine",           # HOSPITAL OF THE UNIV OF PENNA
    "010033": "uab",                     # UNIVERSITY OF ALABAMA HOSPITAL
    "340113": "advocate",                # CAROLINAS MEDICAL CENTER (Atrium)
    "340040": "ecu_health",              # PITT COUNTY MEMORIAL (Vidant flagship)
    "100075": "baycare",                 # SAINT JOSEPHS HOSPITAL, Tampa
    "450058": "tenet",                   # BAPTIST HEALTH SYSTEM, San Antonio
}


# ── Name normalization + matching ──────────────────────────────────

_PUNCT_RE = re.compile(r"[^A-Z0-9]+")
_SAINT_RE = re.compile(r"\bST\b\.?")
_SPACE_RE = re.compile(r"\s+")

# HCRIS sometimes files an amended cost report under a name carrying the
# amendment marker — "AMEND #1 LAKEVIEW HOSPITAL", "AMEND 1 CENTERPOINT
# MEDICAL CENTER", "LOUISIANA BEHAVIORAL HEALTH AMEND #1". The marker is
# filing metadata, not part of the hospital's name, and it silently
# defeats every anchored pattern: HCA's Lakeview and Centerpoint were
# both unmapped purely because of the prefix.
_AMEND_RE = re.compile(r"(?:^|\s)AMEND(?:MENT)?\s*#?\s*\d*(?=\s|$)")

# A leading "THE" is noise for matching: HCRIS carries both "THE JOHNS
# HOPKINS HOSPITAL" and "JOHNS HOPKINS BAYVIEW", and an anchored pattern
# can only catch one of them. Dropping it cost nothing and recovered
# Hopkins' flagship, Ohio State's and Houston Methodist's.
_LEADING_THE_RE = re.compile(r"^THE\s+")


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
    s = _AMEND_RE.sub(" ", s)
    s = _PUNCT_RE.sub(" ", s)
    s = _LEADING_THE_RE.sub("", s.strip())
    s = _SAINT_RE.sub("SAINT", s)
    s = _SPACE_RE.sub(" ", s).strip()
    return s


#: Pattern length at or above which the trailing word boundary is
#: dropped. Short abbreviations (CHI, UH, UT, UM, PAM, SSH) are only
#: safe bounded — unbounded, "CHI" swallowed CHINLE, CHINESE HOSPITAL,
#: CHINO VALLEY and five children's hospitals. But the same boundary
#: silently killed "^BRIGHAM AND WOMEN", because the real facility is
#: BRIGHAM AND WOMENS and the S is a word character: Mass General
#: Brigham's second-largest hospital sat unmapped over an apostrophe.
#: A brand string this long is distinctive enough to match as a prefix.
_UNBOUNDED_PATTERN_LEN = 10


def _compile_pattern(pattern: str) -> "re.Pattern[str]":
    """Compile one registry pattern into a regex.

    ``^`` anchors to the start of the name. Short patterns are bounded
    at both ends; long ones match as prefixes — see
    :data:`_UNBOUNDED_PATTERN_LEN` for why the rule is length-dependent.
    """
    body = pattern.lstrip("^").strip()
    if not body:
        # Never-matching pattern — cheaper than special-casing at call sites.
        return re.compile(r"(?!)")
    prefix = "^" if pattern.startswith("^") else r"(?<![A-Z0-9])"
    suffix = "" if len(body) >= _UNBOUNDED_PATTERN_LEN else r"(?![A-Z0-9])"
    return re.compile(prefix + re.escape(body) + suffix)


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
    #: Whether the pattern is ``^``-anchored, and its literal body — the
    #: two facts the prefix index needs.
    anchored: bool = False
    body: str = ""


#: How many leading characters of an anchored pattern are indexed.
#: Two is enough to cut the candidate set by ~50x and short enough that
#: the buckets stay well populated.
_PREFIX_LEN = 2


@dataclass(frozen=True)
class _Bucket:
    """Patterns for one scope, split so a lookup skips the impossible ones.

    A ``^``-anchored pattern compiles to ``^`` + an escaped literal, so
    it can only match a name that starts with that literal. Indexing
    those by their first two characters means a name beginning "SA"
    never tests the 300-odd patterns that begin with anything else.
    Unanchored patterns match mid-string and have to be tried every
    time; there are only a handful.
    """

    by_prefix: Dict[str, Tuple[_Compiled, ...]]
    floating: Tuple[_Compiled, ...]

    def candidates(self, norm: str) -> Tuple[_Compiled, ...]:
        return self.by_prefix.get(norm[:_PREFIX_LEN], ()) + self.floating


_EMPTY_BUCKET = _Bucket({}, ())


def _to_bucket(entries: List[_Compiled]) -> _Bucket:
    by_prefix: Dict[str, List[_Compiled]] = {}
    floating: List[_Compiled] = []
    for entry in entries:
        body = entry.body
        if entry.anchored and len(body) >= _PREFIX_LEN:
            by_prefix.setdefault(body[:_PREFIX_LEN], []).append(entry)
        else:
            floating.append(entry)
    return _Bucket({k: tuple(v) for k, v in by_prefix.items()}, tuple(floating))


def _build_index() -> Tuple[_Bucket, Dict[str, _Bucket]]:
    """Precompile every pattern once, bucketed by state then by prefix.

    Matching is O(rows x patterns), and the row count is no longer
    6,123: the post-acute universe puts 42,387 more names through the
    same loop. Compiling inside the loop leaned on ``re``'s 512-entry
    cache, which thrashes at this pattern count and cost ~8s per cold
    page render. Precompiling fixed that; the prefix index is what keeps
    it flat as the universe grows, taking the full-universe assignment
    from 8.4s to well under a second.
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
                anchored=body.startswith("^"),
                body=body.lstrip("^").strip(),
            )
            if entry.scope:
                for st in entry.scope:
                    by_state.setdefault(st, []).append(entry)
            else:
                unscoped.append(entry)
    return (_to_bucket(unscoped),
            {k: _to_bucket(v) for k, v in by_state.items()})


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
    scoped = _STATE_PATTERNS.get(st, _EMPTY_BUCKET)
    for entry in scoped.candidates(norm) + _UNSCOPED_PATTERNS.candidates(norm):
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

# Post-acute providers carry no cost report and so no filing recency.
# The Compare files publish a certification date and no termination
# date, which supports exactly one honest statement: CMS still lists
# it. Reusing STATUS_ACTIVE would claim a recency check that never ran.
STATUS_CERTIFIED = "Certified — CMS listing, no filing history"

#: Statuses that count toward a system's operating estate.
OPERATING_STATUSES: Tuple[str, ...] = (STATUS_ACTIVE, STATUS_CERTIFIED)

#: Every status, in the order the page should list them.
STATUS_ORDER: Tuple[str, ...] = (STATUS_ACTIVE, STATUS_CERTIFIED,
                                 STATUS_DORMANT, STATUS_STOPPED)


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
    # Second name, second chance. HCRIS truncates at ~36 characters and
    # abbreviates — "BHMC-CONWAY" is Baptist Health Medical Center
    # Conway, and no pattern written from the brand can reach it. CMS
    # Care Compare carries the untruncated name for the same CCN, and
    # trying it recovers ~380 facilities the cost report spelled too
    # short to see.
    care_compare = load_cms_facilities()

    # A CCN override wins over both name matches — it exists precisely
    # because the name is wrong or unusable for this facility.
    resolved, bases = [], []
    for ccn, state, (sysdef, pattern) in zip(
            ccns.astype(str), states, matches, strict=True):
        override = CCN_OVERRIDES.get(ccn)
        if override and override in _SYSTEM_BY_ID:
            resolved.append(_SYSTEM_BY_ID[override])
            bases.append(f"ccn override {ccn}")
            continue
        if sysdef is None:
            alt = care_compare.get(ccn)
            if alt is not None and alt.name:
                alt_def, alt_pattern = match_system(alt.name, state)
                if alt_def is not None:
                    resolved.append(alt_def)
                    bases.append(f"cms name: {alt_pattern}")
                    continue
        resolved.append(sysdef)
        bases.append(pattern)
    out["system_id"] = [d.system_id if d else UNMAPPED_ID for d in resolved]
    out["system_name"] = [d.name if d else UNMAPPED_NAME for d in resolved]
    out["system_kind"] = [d.kind if d else "" for d in resolved]
    out["system_focus"] = [d.focus if d else "" for d in resolved]
    out["system_match"] = bases

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


# ── Post-acute assignment ──────────────────────────────────────────
#
# Same registry, different ordering. On a hospital the name is all we
# have, so the matcher runs first. On a dialysis facility CMS publishes
# the parent chain outright, and an operator's own answer outranks our
# reading of their signage — so the chain column runs first there.
#
# The tier that fired is recorded in ``system_match`` either way
# ("chain: DaVita" vs "^DAVITA"), because a mapping nobody can audit is
# a mapping nobody should trust.

#: Provider classes, in the order the page should list them.
PROVIDER_CLASS_HOSPITAL = "hospital"


def _post_acute_frame() -> pd.DataFrame:
    """The six Compare files, minus CCNs the hospital universe already has."""
    from .provider_universe import load_post_acute_universe

    hospital_ccns = frozenset(_assigned_cached()["ccn"].astype(str))
    return load_post_acute_universe(hospital_ccns)


def assign_post_acute(df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Attach system columns to the post-acute / outpatient universe.

    Accepts (and returns) the shape produced by
    :func:`provider_universe.load_post_acute_universe`. Passing
    ``df=None`` reads the bundled files through the process cache.
    """
    out = (_post_acute_assigned_cached().copy() if df is None
           else _assign_post_acute_universe(df))
    return out


def _assign_post_acute_universe(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if out.empty:
        for col in ("system_id", "system_name", "system_kind", "system_focus",
                    "system_match", "facility_type", "facility_type_label",
                    "facility_status"):
            out[col] = pd.Series(dtype=object)
        for col in ("is_behavioral", "is_operating"):
            out[col] = pd.Series(dtype=bool)
        return out

    def _col(name: str) -> pd.Series:
        if name in out.columns:
            return out[name].fillna("").astype(str)
        return pd.Series([""] * len(out), index=out.index, dtype=object)

    names, states, chains = _col("name"), _col("state"), _col("chain_name")

    resolved: List[Optional[SystemDef]] = []
    bases: List[str] = []
    for name, state, chain in zip(names, states, chains, strict=True):
        alias = CHAIN_ALIASES.get(normalize_name(chain)) if chain else None
        sysdef = _SYSTEM_BY_ID.get(alias) if alias else None
        if sysdef is not None:
            resolved.append(sysdef)
            bases.append(f"chain: {chain}")
            continue
        sysdef, pattern = match_system(name, state)
        resolved.append(sysdef)
        bases.append(pattern)

    out["system_id"] = [d.system_id if d else UNMAPPED_ID for d in resolved]
    out["system_name"] = [d.name if d else UNMAPPED_NAME for d in resolved]
    out["system_kind"] = [d.kind if d else "" for d in resolved]
    out["system_focus"] = [d.focus if d else "" for d in resolved]
    out["system_match"] = bases

    # The provider class already IS the facility type here — a CCN-range
    # classifier would only re-derive what CMS told us outright.
    out["facility_type"] = _col("provider_class")
    out["facility_type_label"] = _col("provider_class_label")
    out["is_behavioral"] = names.map(normalize_name).str.contains(
        _BEHAVIORAL_NAME_RE, na=False)
    out["facility_status"] = STATUS_CERTIFIED
    out["is_operating"] = True
    return out


@lru_cache(maxsize=1)
def _post_acute_assigned_cached() -> pd.DataFrame:
    return _assign_post_acute_universe(_post_acute_frame())


#: Columns shared by the hospital and post-acute frames — the ones a
#: union can carry without inventing values for either side.
UNION_COLUMNS: Tuple[str, ...] = (
    "ccn", "name", "city", "state", "zip", "county",
    "provider_class", "provider_class_label",
    "system_id", "system_name", "system_kind", "system_focus", "system_match",
    "facility_type", "facility_type_label", "is_behavioral",
    "facility_status", "is_operating", "beds", "chain_name",
)


def assign_all() -> pd.DataFrame:
    """Every Medicare-certified CCN we hold, hospital and post-acute alike.

    ~48,500 rows against the hospital universe's 6,123. Financial
    columns are dropped: only hospitals file a cost report, and carrying
    a revenue column that is null for 87% of the frame invites exactly
    the kind of averaging that produces a wrong number.
    """
    hospitals = assign_systems()
    if not hospitals.empty:
        hospitals = hospitals.assign(
            provider_class=PROVIDER_CLASS_HOSPITAL,
            provider_class_label="Hospital",
            chain_name="",
        )
    post_acute = assign_post_acute()
    frames = []
    for frame in (hospitals, post_acute):
        if frame.empty:
            continue
        missing = [c for c in UNION_COLUMNS if c not in frame.columns]
        for col in missing:
            frame = frame.assign(**{col: ""})
        frames.append(frame[list(UNION_COLUMNS)])
    if not frames:
        return pd.DataFrame(columns=list(UNION_COLUMNS))
    return pd.concat(frames, ignore_index=True)


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


# ── Market concentration ───────────────────────────────────────────
#
# The mapping answers "who owns what". Concentration answers the
# question a deal team asks next: "who controls this market, and is
# there room for another operator". Both come out of the same
# assignment, so they belong in the same module.
#
# Method, stated plainly because the number is only as good as its
# denominator:
#
#   - Share is measured on BEDS, not facility count. A 400-bed
#     flagship and a 15-bed critical-access hospital are not one unit
#     of market power each.
#   - Only OPERATING facilities count. Closed hospitals don't hold
#     share.
#   - Each mapped system is one firm. **Each unmapped facility is its
#     own firm**, which is the conservative reading when ownership is
#     unknown — it can only push the index DOWN. So every HHI here is
#     a FLOOR: real concentration is at least this high, and higher
#     wherever an unmapped facility is quietly part of a system.
#   - HHI is the standard sum of squared percentage shares (0–10,000).
#     The DOJ/FTC merger-guideline bands are 1,500 and 2,500.

HHI_UNCONCENTRATED = 1500.0
HHI_MODERATE = 2500.0


def hhi_band(hhi: float) -> str:
    """DOJ/FTC label for an HHI value."""
    if hhi >= HHI_MODERATE:
        return "Highly concentrated"
    if hhi >= HHI_UNCONCENTRATED:
        return "Moderately concentrated"
    return "Unconcentrated"


@dataclass(frozen=True)
class MarketShare:
    """One firm's position in a state."""

    system_id: str
    system_name: str
    kind: str
    hospitals: int
    beds: float
    bed_share: float            # 0–1 of the state's operating beds
    is_independent: bool = False


@dataclass(frozen=True)
class StateConcentration:
    """Bed-share concentration for one state's operating hospitals."""

    state: str
    hospitals: int
    beds: float
    shares: Tuple[MarketShare, ...]     # every firm, ranked by bed share
    hhi: float
    independent_beds: float
    independent_facilities: int

    @property
    def band(self) -> str:
        return hhi_band(self.hhi)

    @property
    def cr1(self) -> float:
        return self.shares[0].bed_share if self.shares else 0.0

    @property
    def cr3(self) -> float:
        return sum(s.bed_share for s in self.shares[:3])

    @property
    def leader(self) -> Optional[MarketShare]:
        """The largest firm — which in a low-coverage state is often a
        single unmapped hospital, and should read that way."""
        return self.shares[0] if self.shares else None

    @property
    def mapped_shares(self) -> Tuple[MarketShare, ...]:
        return tuple(s for s in self.shares if not s.is_independent)

    @property
    def independent_share(self) -> float:
        return (self.independent_beds / self.beds) if self.beds else 0.0


def state_concentration(
    state: str,
    df: Optional[pd.DataFrame] = None,
) -> Optional[StateConcentration]:
    """Bed-share concentration for one state. ``None`` if the state is empty.

    Facilities that report zero beds are excluded from the share math
    (they cannot hold bed share) but still count in the facility
    totals, so the two figures on the page don't silently disagree.
    """
    st = str(state or "").upper().strip()
    if not st:
        return None
    assigned = assign_systems(df)
    if assigned.empty:
        return None
    rows = assigned[(assigned["state"].astype(str).str.upper() == st)
                    & assigned["is_operating"]]
    if rows.empty:
        return None

    beds = pd.to_numeric(rows["beds"], errors="coerce").fillna(0.0)
    rows = rows.assign(_beds=beds)
    total_beds = float(beds.sum())
    if total_beds <= 0:
        return None

    shares: List[MarketShare] = []
    mapped = rows[rows["system_id"] != UNMAPPED_ID]
    for system_id, group in mapped.groupby("system_id", sort=False):
        sysdef = _SYSTEM_BY_ID.get(str(system_id))
        sys_beds = float(group["_beds"].sum())
        shares.append(MarketShare(
            system_id=str(system_id),
            system_name=sysdef.name if sysdef else str(system_id),
            kind=sysdef.kind if sysdef else "",
            hospitals=int(len(group)),
            beds=sys_beds,
            bed_share=sys_beds / total_beds,
        ))

    # Each unmapped facility enters the ranking as its OWN firm, not as
    # one lumped "independent" block. Lumping would invent a cartel that
    # doesn't exist and put it at the top of every low-coverage state;
    # leaving them out entirely would hand the leader spot to whichever
    # small system happens to be mapped. In Rhode Island — 99% unmapped —
    # only this treatment gives a leader a partner would recognise.
    independents = rows[rows["system_id"] == UNMAPPED_ID]
    independent_beds = float(independents["_beds"].sum())
    for _, solo in independents.iterrows():
        solo_beds = float(solo["_beds"])
        shares.append(MarketShare(
            system_id="",
            system_name=str(solo.get("name", "")),
            kind="Independent / Unmapped",
            hospitals=1,
            beds=solo_beds,
            bed_share=solo_beds / total_beds,
            is_independent=True,
        ))

    hhi = sum((s.bed_share * 100.0) ** 2 for s in shares)
    shares.sort(key=lambda s: (-s.bed_share, -s.hospitals, s.system_name))
    return StateConcentration(
        state=st,
        hospitals=int(len(rows)),
        beds=total_beds,
        shares=tuple(shares),
        hhi=hhi,
        independent_beds=independent_beds,
        independent_facilities=int(len(independents)),
    )


@lru_cache(maxsize=1)
def _all_state_concentration() -> Tuple[StateConcentration, ...]:
    assigned = assign_systems()
    states = sorted({str(x).upper() for x in assigned["state"] if str(x).strip()})
    out = [state_concentration(st) for st in states]
    return tuple(c for c in out if c is not None)


def concentration_ranking(
    df: Optional[pd.DataFrame] = None,
    *,
    min_hospitals: int = 10,
    limit: int = 15,
) -> List[StateConcentration]:
    """States ranked most-concentrated first — a sourcing lens.

    ``min_hospitals`` keeps single-hospital territories out of the top
    of the list: a state with three hospitals is arithmetically
    "highly concentrated" without that meaning anything to a buyer.
    """
    if df is None:
        pool = list(_all_state_concentration())
    else:
        assigned = assign_systems(df)
        states = sorted({str(x).upper() for x in assigned["state"] if str(x).strip()})
        pool = [c for c in (state_concentration(st, df) for st in states) if c]
    pool = [c for c in pool if c.hospitals >= min_hospitals]
    pool.sort(key=lambda c: (-c.hhi, -c.beds))
    return pool[:limit]


@lru_cache(maxsize=1)
def _leader_map() -> Dict[str, Tuple[str, ...]]:
    """system_id -> the states where it is the largest firm by beds.

    "Runs 22 hospitals in Utah" and "is the largest operator in Utah"
    are different claims, and only the second one tells a deal team
    whether they are buying into a market or against its incumbent.
    """
    out: Dict[str, List[str]] = {}
    for c in _all_state_concentration():
        leader = c.leader
        if leader is None or leader.is_independent or not leader.system_id:
            continue
        out.setdefault(leader.system_id, []).append(c.state)
    return {k: tuple(sorted(v)) for k, v in out.items()}


def leading_states(system_id: str) -> Tuple[str, ...]:
    """States where this system holds the largest bed share."""
    return _leader_map().get(str(system_id or ""), ())


@lru_cache(maxsize=1)
def _npi_names() -> Tuple[Tuple[str, str], ...]:
    """(normalized name, state) for every cached organization NPI.

    Both the legal name and every d/b/a, because a pattern that only
    ever matches a d/b/a is alive, not dead.
    """
    from .npi_registry import load_npi_registry

    out: List[Tuple[str, str]] = []
    for rec in load_npi_registry().values():
        state = rec.state.upper()
        for name in (rec.legal_name, *rec.dbas):
            if name:
                out.append((normalize_name(name), state))
    return tuple(out)


def dead_patterns(df: Optional[pd.DataFrame] = None) -> List[Tuple[str, str]]:
    """Registry patterns that match no facility, as ``(system_id, pattern)``.

    A maintenance scan, not an error list. Some dead patterns are
    deliberate — house brands that will appear after a data refresh
    (``^COMMONSPIRIT``, ``^SCIONHEALTH``) are worth carrying early. But
    the scan is how typos surface: it is what caught ``^FORSYTH MEDICAL``
    against a facility actually named FORSYTH MEMORIAL, and
    ``^BRIGHAM AND WOMEN`` failing the trailing boundary against
    BRIGHAM AND WOMENS.

    Scans everything the registry can reach — hospital, post-acute and
    the NPI roster — because the registry now spans all three. Scanning
    hospitals alone would report fifty post-acute operators and four
    ambulance operators as dead and drown the signal the scan exists to
    produce.
    """
    assigned = assign_all() if df is None else assign_systems(df)
    seen = [(normalize_name(n), str(st).upper())
            for n, st in zip(assigned["name"], assigned["state"], strict=True)]
    if df is None:
        seen.extend(_npi_names())
    out: List[Tuple[str, str]] = []
    for sysdef in SYSTEM_REGISTRY:
        for pattern in sysdef.patterns:
            scope, body = _split_pattern(pattern)
            scope = scope or sysdef.states
            regex = _compile_pattern(body)
            if not any(regex.search(nm) and (not scope or st in scope)
                       for nm, st in seen):
                out.append((sysdef.system_id, pattern))
    return out


def _clear_cache() -> None:
    """Test hook — drop the memoized assignment + rollup."""
    _all_state_concentration.cache_clear()
    _leader_map.cache_clear()
    _assigned_cached.cache_clear()
    _post_acute_assigned_cached.cache_clear()
    _npi_names.cache_clear()
    _cached_map.cache_clear()
    _last_active_year_by_ccn.cache_clear()
