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

from dataclasses import dataclass
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
    Rule("state-from-zip", "repair", "info", "Geography",
         "Blank state filled from ZIP",
         "A blank state cell next to a resolvable ZIP is filled from the "
         "ZIP3→state map — the same deterministic truth the "
         "zip-state-mismatch flag trusts (military/territory prefixes "
         "excluded). Fully audited in the change log.",
         "Capture state at intake; the fill closes the gap downstream.",
         "completeness"),
    Rule("name-from-nppes", "repair", "info", "Provider",
         "Blank provider name filled from NPPES",
         "A blank provider-name cell next to a verified (active) billing "
         "NPI is filled with that NPI's canonical NPPES record name. "
         "Online enrich mode only; blanks-only, never overwrites.",
         "The registry is the source of truth for provider names.",
         "completeness"),
    Rule("state-from-nppes", "repair", "info", "Provider",
         "Blank state filled from NPPES",
         "A blank state cell next to a verified (active) billing NPI is "
         "filled from that NPI's NPPES practice-location state. Online "
         "enrich mode only; blanks-only.",
         "Capture practice state at intake.", "completeness"),
    Rule("taxonomy-from-nppes", "repair", "info", "Provider",
         "Blank taxonomy filled from NPPES",
         "A blank taxonomy cell next to a verified (active) billing NPI "
         "is filled with that NPI's primary NPPES taxonomy. Online enrich "
         "mode only; blanks-only.",
         "Taxonomy drives the specialty mix — filling it improves it.",
         "completeness"),
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
    Rule("provider-name-format", "repair", "info", "Identifiers",
         "Provider name re-cased",
         "An all-caps or all-lowercase PERSON name in a provider-name "
         "column was converted to standard casing (SMITH, JOHN A, MD → "
         "Smith, John A, MD). Mc/O'/hyphenated surnames keep their inner "
         "capitals, credential tokens (MD, DO, NP …) stay uppercase, and "
         "organization names (LLC, CLINIC, HOSPITAL …) are never touched.",
         "None needed — cosmetic normalization; the change log holds every "
         "original value.", "conformity"),

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
    Rule("icd10-unknown-code", "flag", "warning", "Coding",
         "Diagnosis code not in ICD-10-CM",
         "A diagnosis that is shaped correctly but does not exist in the "
         "ICD-10-CM code set. Runs only when the icd10cm reference pack "
         "is installed (pull it under Reference data packs).",
         "Usually a keyed digit or a retired code — verify against the "
         "current code set.", "validity"),
    Rule("hcpcs-unknown-code", "flag", "warning", "Coding",
         "HCPCS Level II code not in the set",
         "A letter-led procedure code (A–V + 4 digits) that does not "
         "exist in the CMS HCPCS Level II file. Runs only when the hcpcs "
         "pack is installed. Numeric CPT-4 codes are AMA-licensed and are "
         "shape-checked only.",
         "Verify against the current quarterly HCPCS release.",
         "validity"),
    Rule("leie-excluded-npi", "flag", "critical", "Compliance",
         "Billing NPI on the OIG exclusion list",
         "The billing provider appears on the OIG List of Excluded "
         "Individuals/Entities — claims involving excluded providers are "
         "direct fraud exposure. Runs automatically and offline on every "
         "run once the leie pack is installed (refresh monthly).",
         "Stop billing immediately and escalate to compliance counsel; "
         "verify the match on the OIG site (NPI-level match).",
         "validity"),

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
    Rule("possible-duplicate-service", "flag", "warning", "Duplicates",
         "Possible duplicate service",
         "The same patient, provider, and procedure code appears again "
         "within the duplicate window (default 3 days, profile-tunable) on "
         "a DIFFERENT date. Same-date repeats are covered by the "
         "duplicate-claim rules; this catches the re-bill-two-days-later "
         "pattern payers deny as duplicate.",
         "Check whether the second line is a corrected re-bill (needs the "
         "right frequency code) or a true duplicate.", "uniqueness"),
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
    Rule("mbi-malformed", "flag", "critical", "Identifiers",
         "Malformed Medicare MBI",
         "The member ID on a Medicare line isn't a valid Medicare "
         "Beneficiary Identifier (11 chars, strict position classes, no "
         "S/L/O/I/B/Z letters).",
         "Re-verify eligibility — a bad MBI is a guaranteed rejection.",
         "validity"),
    Rule("condition-code-malformed", "flag", "warning", "Coding",
         "Malformed condition code",
         "A UB-04 condition code isn't 2 alphanumeric characters.",
         "Fix keying at source; check for column shift.", "validity"),
    Rule("occurrence-code-malformed", "flag", "warning", "Coding",
         "Malformed occurrence code",
         "A UB-04 occurrence code isn't 2 alphanumeric characters.",
         "Fix keying at source.", "validity"),
    Rule("value-code-malformed", "flag", "warning", "Coding",
         "Malformed value code",
         "A UB-04 value code isn't 2 alphanumeric characters.",
         "Fix keying at source.", "validity"),
    Rule("near-duplicate-row", "flag", "warning", "Duplicates",
         "Near-duplicate row",
         "Rows identical after case-folding and whitespace collapse — "
         "exact dedupe correctly keeps them, a human would merge them.",
         "Standardize casing at the source and re-extract.", "uniqueness"),
    Rule("timely-filing-risk", "flag", "warning", "Dates",
         "Timely-filing risk",
         "Days between service and submission/received dates exceed the "
         "filing limit. When the row names a payer with a published limit "
         "(Medicare 365, most commercial 90-180) that limit applies; "
         "unknown payers use the profile threshold (default 365).",
         "Check the payer contract's limit; write off or appeal as "
         "applicable.", "consistency"),
    Rule("drg-pad", "repair", "warning", "Coding",
         "DRG zeros restored",
         "Numeric MS-DRGs shorter than 3 digits zero-padded (87 → 087) — "
         "Excel strips the leading zero.",
         "Format DRG columns as text before Excel.", "validity"),
    Rule("drg-malformed", "flag", "critical", "Coding",
         "Malformed DRG",
         "MS-DRG isn't a 3-digit code 001-999. Institutional claims price "
         "off the DRG — a bad one misprices or denies the whole stay.",
         "Correct the DRG at the source; check for truncation or a grouper "
         "export issue.", "validity"),
    Rule("revenue-tob-mismatch", "flag", "warning", "Coding",
         "Room & board revenue on an outpatient bill",
         "An accommodation revenue code (0100-0219 — room & board, ICU, "
         "CCU) appears on an outpatient type of bill (hospital outpatient "
         "013x/014x, clinic 07xx, ASC 083x). Inpatient room charges can't "
         "ride an outpatient claim.",
         "Check whether the claim should be inpatient (wrong TOB) or the "
         "revenue code is a keying error.", "consistency"),
    Rule("anesthesia-units-implausible", "flag", "warning", "Coding",
         "Implausible anesthesia units",
         "An anesthesia line (CPT 00100-01999) bills more than 24 hours' "
         "worth of time units (1,440). That's a keying error or a column "
         "shift, not a marathon case.",
         "Verify the units against the anesthesia record; check for an "
         "extra digit or minutes-vs-units confusion.", "consistency"),
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
