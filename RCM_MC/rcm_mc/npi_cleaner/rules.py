"""Declarative rule registry — every check the cleaner runs, as data.

Enterprise DQ platforms (Great Expectations, Informatica, Ataccama) treat
rules as first-class objects with identity, severity, category, and
remediation guidance, so the SAME rule definition powers the UI, the
executive report, the API, and the worklist exports. This module is that
registry for the claims cleaner: the engine still executes the checks
inline for speed, but everything that *describes* a rule comes from here.

Two rule kinds:
  * ``repair``  — deterministic normalizations the cleaner APPLIES
                  (safe, reversible via the change log).
  * ``flag``    — report-only findings the cleaner NEVER auto-fixes
                  (verify at the source system).

Severity semantics:
  * ``critical`` — will deny / corrupt money math (bad codes, impossible
                   chronology, unparseable amounts).
  * ``warning``  — likely defect worth a look (outliers, staleness,
                   suspicious duplicates).
  * ``info``     — hygiene/formatting signal.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class Rule:
    id: str                    # stable key, matches engine repair/sanity keys
    kind: str                  # "repair" | "flag"
    severity: str              # "critical" | "warning" | "info"
    category: str              # grouping for UI / report sections
    title: str                 # short human name
    description: str           # what the rule means
    remediation: str = ""      # what a team should do about it
    dimension: str = ""        # DQ dimension it feeds (validity/consistency/…)


_RULES: List[Rule] = [
    # ------------------------------------------------------------- repairs --
    Rule("whitespace-chars", "repair", "info", "Formatting",
         "Whitespace normalization",
         "Non-breaking and zero-width spaces replaced with plain spaces.",
         "None needed — cosmetic fix applied in place.", "conformity"),
    Rule("collapse-space", "repair", "info", "Formatting",
         "Internal whitespace collapsed",
         "Runs of spaces inside a value collapsed to one.",
         "None needed.", "conformity"),
    Rule("mojibake", "repair", "info", "Formatting",
         "Mojibake repaired",
         "UTF-8 text mis-decoded as Latin-1/CP-1252 (â€™ …) restored.",
         "Fix the export encoding at the source (use UTF-8).", "conformity"),
    Rule("leading-apostrophe", "repair", "info", "Formatting",
         "Excel text-marker stripped",
         "Leading apostrophes Excel uses to force text were removed.",
         "Export as CSV directly rather than via Excel copy/paste.",
         "conformity"),
    Rule("null-token", "repair", "info", "Completeness",
         "Null tokens unified",
         "NA / N/A / NULL / -- and similar tokens normalized to blank.",
         "Prefer truly empty cells for missing data at the source.",
         "completeness"),
    Rule("npi-excel-float", "repair", "warning", "Identifiers",
         "NPI float damage repaired",
         "NPIs mangled to floats by Excel (1234567893.0) restored.",
         "Format NPI columns as text before opening extracts in Excel.",
         "validity"),
    Rule("npi-strip-nondigits", "repair", "info", "Identifiers",
         "NPI punctuation stripped",
         "Hyphens/spaces inside NPIs removed to the bare 10 digits.",
         "None needed.", "conformity"),
    Rule("money-normalize", "repair", "info", "Amounts",
         "Money normalized",
         "$ signs, thousands separators, and accounting-style (negatives) "
         "unified to plain decimals.",
         "None needed.", "conformity"),
    Rule("date-excel-serial", "repair", "warning", "Dates",
         "Excel serial dates converted",
         "Raw Excel day-numbers (45300) converted to ISO dates.",
         "Format date columns as dates before export.", "validity"),
    Rule("date-us-to-iso", "repair", "info", "Dates",
         "US dates converted to ISO",
         "MM/DD/YYYY converted to YYYY-MM-DD.",
         "Standardize source extracts on ISO-8601.", "conformity"),
    Rule("date-iso-trim", "repair", "info", "Dates",
         "Datetimes trimmed to dates",
         "ISO datetimes trimmed to the date part.",
         "None needed.", "conformity"),
    Rule("state-name-to-code", "repair", "info", "Geography",
         "State names mapped to codes",
         "Full state names (Texas) mapped to USPS codes (TX).",
         "None needed.", "conformity"),
    Rule("state-upper", "repair", "info", "Geography",
         "State codes upper-cased", "tx → TX.", "None needed.", "conformity"),
    Rule("zip-pad", "repair", "warning", "Geography",
         "ZIP leading zeros restored",
         "Excel strips leading zeros; 1234 restored to 01234.",
         "Format ZIP columns as text before opening extracts in Excel.",
         "validity"),
    Rule("zip5+4", "repair", "info", "Geography",
         "ZIP+4 formatted", "9-digit ZIPs formatted 12345-6789.",
         "None needed.", "conformity"),
    Rule("zip-clean", "repair", "info", "Geography",
         "ZIP formatting cleaned", "Stray characters removed from ZIPs.",
         "None needed.", "conformity"),
    Rule("hcpcs-upper", "repair", "info", "Coding",
         "HCPCS/CPT upper-cased", "g0008 → G0008.", "None needed.",
         "conformity"),
    Rule("sex-normalize", "repair", "info", "Demographics",
         "Sex/gender normalized", "Male / 1 / f → M / F / U.",
         "None needed.", "conformity"),
    Rule("dx-upper", "repair", "info", "Coding",
         "ICD-10 upper-cased", "e11.65 → E11.65.", "None needed.",
         "conformity"),
    Rule("dx-decimal", "repair", "info", "Coding",
         "ICD-10 decimal inserted", "E1165 → E11.65.",
         "Source system should store dotted ICD-10-CM.", "conformity"),
    Rule("modifier-normalize", "repair", "info", "Coding",
         "Modifiers normalized",
         "Modifier lists split, upper-cased, and de-duplicated.",
         "None needed.", "conformity"),
    Rule("phone-format", "repair", "info", "Contact",
         "Phones formatted", "10/11-digit numbers formatted (555) 123-4567.",
         "None needed.", "conformity"),
    Rule("taxonomy-upper", "repair", "info", "Identifiers",
         "Taxonomy upper-cased", "207q00000x → 207Q00000X.", "None needed.",
         "conformity"),
    Rule("ndc-pad-11", "repair", "warning", "Drugs",
         "NDC padded to 11 digits",
         "Hyphenated 10-digit NDCs zero-padded segment-aware to the "
         "5-4-2 billing format.",
         "Bill NDCs in the 11-digit format.", "validity"),
    Rule("ndc-normalize-11", "repair", "info", "Drugs",
         "NDC normalized", "Hyphens removed from 11-digit NDCs.",
         "None needed.", "conformity"),
    Rule("revcode-pad", "repair", "warning", "Coding",
         "Revenue-code zeros restored",
         "3-digit revenue codes zero-padded to the 4-digit UB-04 form "
         "(450 → 0450).",
         "Format revenue-code columns as text before Excel.", "validity"),
    Rule("pos-pad", "repair", "info", "Coding",
         "POS zero-padded", "1-digit Place of Service padded (1 → 01).",
         "None needed.", "conformity"),

    # ------------------------------------------------------ flags: validity --
    Rule("hcpcs-malformed", "flag", "critical", "Coding",
         "Malformed HCPCS/CPT",
         "Procedure code isn't a valid shape (5 digits, letter+4 digits, "
         "or 4 digits+letter). These lines will deny on submission.",
         "Correct the code at the source; check for truncation or "
         "column-shift in the extract.", "validity"),
    Rule("icd10-malformed", "flag", "critical", "Coding",
         "Malformed ICD-10 diagnosis",
         "Diagnosis code isn't a valid ICD-10-CM shape.",
         "Correct at source; verify the extract isn't mixing ICD-9.",
         "validity"),
    Rule("money-unparseable", "flag", "critical", "Amounts",
         "Non-numeric amount",
         "A value in an amount column can't be read as money "
         "(text, letter O for zero, stray symbols).",
         "Fix the cell at the source; sums over this column are wrong "
         "until then.", "validity"),
    Rule("sex-invalid", "flag", "warning", "Demographics",
         "Invalid sex/gender value",
         "Value didn't resolve to M/F/U.",
         "Map the source system's local codes.", "validity"),
    Rule("taxonomy-malformed", "flag", "warning", "Identifiers",
         "Malformed taxonomy code",
         "Provider taxonomy isn't 10 alphanumeric characters (NUCC).",
         "Re-pull from NPPES; check for truncation.", "validity"),
    Rule("pos-invalid", "flag", "critical", "Coding",
         "Invalid Place of Service",
         "POS code isn't in the official CMS code set.",
         "Correct at source — an invalid POS is an instant denial.",
         "validity"),
    Rule("revenue-code-malformed", "flag", "critical", "Coding",
         "Malformed revenue code",
         "UB-04 revenue code isn't 4 digits.",
         "Correct at source; check for column shift.", "validity"),
    Rule("carc-invalid", "flag", "warning", "Denials",
         "Invalid denial reason code",
         "Denial/adjustment cell isn't a valid CARC shape "
         "(1-3 digits or letter+digits).",
         "Check the remit parser — free text is leaking into the "
         "reason-code field.", "validity"),
    Rule("tob-malformed", "flag", "critical", "Coding",
         "Invalid Type of Bill",
         "TOB isn't a valid NUBC shape (facility type + classification + "
         "frequency).",
         "Correct at source — an invalid TOB rejects at the clearinghouse.",
         "validity"),
    Rule("discharge-status-invalid", "flag", "warning", "Coding",
         "Invalid discharge status",
         "Patient discharge status isn't an NUBC code.",
         "Map the source system's local status codes.", "validity"),
    Rule("admission-type-invalid", "flag", "warning", "Coding",
         "Invalid admission type",
         "Admission type isn't in the UB-04 FL14 domain (1-5, 9).",
         "Map the source system's local codes.", "validity"),
    Rule("modifier-unknown", "flag", "info", "Coding",
         "Unknown modifier",
         "A well-formed 2-character modifier that isn't in the standard "
         "catalog — often a typo (Q6 vs 06), sometimes payer-proprietary.",
         "Verify against the payer companion guide.", "validity"),

    # --------------------------------------------------- flags: consistency --
    Rule("allowed-exceeds-billed", "flag", "critical", "Amounts",
         "Allowed exceeds billed",
         "The allowed amount is greater than the billed charge.",
         "Almost always a column swap or keying error.", "consistency"),
    Rule("paid-exceeds-allowed", "flag", "critical", "Amounts",
         "Paid exceeds allowed",
         "The paid amount is greater than the allowed amount.",
         "Check for interest payments keyed into the paid field, or a "
         "column swap.", "consistency"),
    Rule("paid-exceeds-billed", "flag", "critical", "Amounts",
         "Paid exceeds billed",
         "The paid amount is greater than the billed charge.",
         "Check for column swap; legitimate only with interest/incentives.",
         "consistency"),
    Rule("negative-allowed", "flag", "warning", "Amounts",
         "Negative allowed amount",
         "Allowed is negative — a reversal leaking into a snapshot extract.",
         "Confirm reversal handling in the extract logic.", "consistency"),
    Rule("negative-paid", "flag", "warning", "Amounts",
         "Negative paid amount",
         "Paid is negative — recoupment/reversal row.",
         "Confirm reversal handling; consider netting logic.", "consistency"),
    Rule("nonpositive-units", "flag", "warning", "Units",
         "Units ≤ 0",
         "Zero or negative service units on a claim line.",
         "Check reversal rows and unit-capture at source.", "consistency"),
    Rule("fractional-units", "flag", "info", "Units",
         "Fractional units",
         "Non-integer units — legitimate for anesthesia time/drugs, a "
         "defect for most E/M and procedure lines.",
         "Verify by code family.", "consistency"),
    Rule("date-in-future", "flag", "critical", "Dates",
         "Impossible future date",
         "A service/birth/paid date after today.",
         "Century keying error (2035 for 1935) — fix at source.",
         "consistency"),
    Rule("date-stale", "flag", "warning", "Dates",
         "Stale service date",
         "Service date more than 10 years old in a working extract.",
         "Verify century keying and the extract's date filter.",
         "consistency"),
    Rule("zip-state-mismatch", "flag", "warning", "Geography",
         "ZIP/state disagreement",
         "The ZIP's USPS prefix resolves to a different state than the "
         "state cell (same entity).",
         "Verify the provider/patient address at source.", "consistency"),
    Rule("service-before-birth", "flag", "critical", "Dates",
         "Service before birth",
         "Date of service precedes the patient's date of birth.",
         "DOB keying error or patient-identity mismatch — fix before any "
         "age-based analytics.", "consistency"),
    Rule("discharge-before-admit", "flag", "critical", "Dates",
         "Discharge before admission",
         "Discharge date precedes the admission date.",
         "Date swap at source; length-of-stay math is wrong until fixed.",
         "consistency"),
    Rule("ndc-ambiguous-10digit", "flag", "warning", "Drugs",
         "Ambiguous 10-digit NDC",
         "Unhyphenated 10-digit NDC — the segment layout is unknowable, "
         "so it cannot be safely padded to the billing format.",
         "Re-pull with hyphens or in the 11-digit format.", "consistency"),
    Rule("suspected-duplicate-claim", "flag", "warning", "Duplicates",
         "Suspected duplicate claim",
         "Distinct rows sharing provider · patient · date · code · amount.",
         "Review for double billing; confirm before deleting anything.",
         "uniqueness"),
    Rule("conflicting-amount-claim", "flag", "warning", "Duplicates",
         "Conflicting amounts on same claim key",
         "The same provider · patient · date · code appears with different "
         "amounts — re-bills/corrections living alongside originals.",
         "Keep only the final adjudication for spend analytics.",
         "consistency"),
    Rule("charge-outlier", "flag", "warning", "Amounts",
         "Statistical charge outlier",
         "Charge beyond 3×IQR fences within its HCPCS code.",
         "Review the top offenders — data error or a story either way.",
         "consistency"),
    Rule("jw-zero-units", "flag", "warning", "Coding",
         "JW modifier with no units",
         "A JW (discarded drug) line bills the wasted units — units must "
         "be positive.",
         "Correct units or drop the JW modifier.", "consistency"),
    Rule("bilateral-units", "flag", "warning", "Coding",
         "Bilateral 50 with >1 unit",
         "A bilateral procedure bills 1 unit with modifier 50 per CMS MUE "
         "guidance.",
         "Rebill as 1 unit with 50, or 2 lines LT/RT per payer rules.",
         "consistency"),
    Rule("timely-filing-risk", "flag", "warning", "Dates",
         "Timely-filing risk",
         "More than 365 days between service and submission/received "
         "dates — most payers' filing limit.",
         "Check payer-specific limits; write off or appeal as applicable.",
         "consistency"),
]

_BY_ID: Dict[str, Rule] = {r.id: r for r in _RULES}


def get(rule_id: str) -> Optional[Rule]:
    return _BY_ID.get(rule_id)


def all_rules() -> List[Rule]:
    return list(_RULES)


def catalog() -> List[Dict[str, str]]:
    """JSON-safe rule catalog for the API / UI."""
    return [{"id": r.id, "kind": r.kind, "severity": r.severity,
             "category": r.category, "title": r.title,
             "description": r.description, "remediation": r.remediation,
             "dimension": r.dimension} for r in _RULES]


def describe(rule_id: str) -> Dict[str, str]:
    """Description block for one rule, with a graceful unknown fallback so a
    new engine rule never breaks a renderer that hasn't caught up."""
    r = _BY_ID.get(rule_id)
    if r is None:
        return {"id": rule_id, "kind": "flag", "severity": "info",
                "category": "Other", "title": rule_id,
                "description": "", "remediation": "", "dimension": ""}
    return {"id": r.id, "kind": r.kind, "severity": r.severity,
            "category": r.category, "title": r.title,
            "description": r.description, "remediation": r.remediation,
            "dimension": r.dimension}
