"""Configuration: canonical schema, column-name synonyms, CMS dataset titles,
NOC codes, and imputation tier definitions. Single source of truth for the pipeline."""

from pathlib import Path
import os
import re as _re

PKG_DIR = Path(__file__).resolve().parent
REF_DIR = PKG_DIR / "reference"


def npi_is_valid(npi):
    """True iff npi is a 10-digit National Provider Identifier that passes the
    Luhn check digit with the NPPES '80840' prefix. A plain 10-digit number that
    fails this is a typo/garbage, not a real NPI — checking it lets the pipeline
    avoid wasted lookups on it and avoid treating it as a verified provider."""
    if npi is None:
        return False
    try:
        s = _re.sub(r"\D", "", str(npi))
    except Exception:
        return False
    if len(s) != 10:
        return False
    payload = "80840" + s[:9]
    total, alt = 0, True
    for ch in reversed(payload):
        d = int(ch)
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        alt = not alt
    check = (10 - (total % 10)) % 10
    return check == int(s[9])

# Cache schema tag. Bump ONLY when the shape/content of a cached record changes,
# so a new version cleanly ignores incompatible old entries instead of serving
# stale data. (All current record shapes — NPPES with full taxonomy set, RxNorm
# with the DailyMed class fallback, multi-dataset CCN resolution — are "v2".)
CACHE_SCHEMA = "v2"


def _default_cache_dir():
    """A STABLE, user-level cache location so the expensive live lookups are
    reused across runs AND across version upgrades — you pay the first-run cost
    once, not every time you drop in a new build. Override with NPI_CACHE_DIR
    (e.g. a shared team folder)."""
    override = os.environ.get("NPI_CACHE_DIR")
    base = Path(override) if override else (Path.home() / ".npi_recovery_cache")
    return base / CACHE_SCHEMA


# Persistent cache (was previously per-folder, which made every upgrade cold).
DEFAULT_CACHE_DIR = _default_cache_dir()

# ---------------------------------------------------------------------------
# Canonical claim fields the pipeline reasons over. The input file can call
# them anything; schema.detect_columns() maps real headers onto these keys.
# ---------------------------------------------------------------------------
CANON = {
    "billing_npi":   "Billing / rendering provider NPI (the field with the gaps)",
    "referring_npi": "Referring provider NPI (survives on ~97% of blank rows)",
    "hcpcs":         "HCPCS / J-code (the drug or service)",
    "pos":           "Place of service / site of care (office, home, facility)",
    "zip":           "Patient or service ZIP (5-digit; ZIP3 is derived from it)",
    "state":         "Service / provider state abbreviation",
    "allowed_amt":   "Allowed / paid / billed dollar amount",
    "units":         "Units / services / quantity",
    "drug_name":     "Drug or product name (helps resolve NOC codes)",
    "payer":         "Payer / plan name",
    "claim_id":      "Claim or line identifier",
    "patient_id":    "De-identified patient / member ID (enables visit-continuity inference)",
    "ndc":           "National Drug Code (11-digit billed product; disambiguates NOC codes)",
    "date":          "Service / paid date",
}

# Headers that should always be read as strings (never coerced to float -> NPIs
# lose leading digits and ZIPs lose leading zeros otherwise).
STRING_FIELDS = {"billing_npi", "referring_npi", "hcpcs", "zip", "state",
                 "pos", "claim_id", "payer", "patient_id", "ndc",
                 "billing_name", "referring_name", "referring_specialty",
                 "billing_specialty", "entity_type", "billing_affiliation",
                 "referring_affiliation"}

# Values that MEAN "missing" but aren't an empty cell. Real data teams write all
# of these; if we don't treat them as blank, a cell that says "NULL" looks
# present (so it never gets filled) and a "N/A" NPI looks like a real identifier.
# Compared case-insensitively against the stripped cell text.
BLANK_TOKENS = {
    "", "nan", "none", "null", "nul", "n/a", "na", "n.a.", "n/a.", "#n/a",
    "#n/a n/a", "<na>", "<null>", "-", "--", "---", "—", "–", ".", "..", "...",
    "?", "??", "(blank)", "blank", "(empty)", "empty", "unknown", "unk", "none.",
    "nil", "#ref!", "#value!", "#name?", "#div/0!", "#null!", "#num!",
    "not available", "not mapped", "(not mapped)", "not applicable", "missing",
    "tbd", "none provided", "no data", "\\n", "none.",
}

# Normalised synonym -> canonical key. Matching is done on a normalised header
# (lowercased, non-alphanumerics stripped). Order matters only within a list.
COLUMN_SYNONYMS = {
    "billing_npi": [
        "billingnpi", "billingprovidernpi", "renderingnpi", "renderingprovidernpi",
        "rndrngnpi", "servicingnpi", "servicingprovidernpi", "billprovnpi",
        "providernpi", "npibilling", "billnpi", "rendnpi", "performingnpi",
        "billingprovider", "renderingprovider", "supplierprovidernpi", "supplier",
        "npi", "prvdrnpi", "provnpi", "billgprovnpi", "attendingnpi", "atndngnpi",
        "renderingproviderid", "nationalproviderid", "natlprovid", "billernpi",
        "servicingprovider", "performingprovidernpi", "billingnationalproviderid",
        "pharmacynpi", "dispensingnpi", "dispensingprovidernpi", "dispensingpharmacynpi",
        "servicingpharmacynpi", "pharmacyprovidernpi", "pharmacynpinumber", "rxprovidernpi",
    ],
    "referring_npi": [
        "referringnpi", "referringprovidernpi", "refnpi", "referrernpi",
        "orderingnpi", "orderingprovidernpi", "orderingreferringnpi",
        "prescribernpi", "prescribingnpi", "referringprovider", "refprovnpi",
        "ordprvdrnpi", "ordprovnpi", "refrngnpi", "ordrngnpi", "referprovnpi",
        "primarycarenpi", "pcpnpi", "orderingreferringprovidernpi",
    ],
    "hcpcs": [
        "hcpcs", "hcpcscd", "hcpcscode", "jcode", "procedurecode", "proccode",
        "cpt", "cpthcpcs", "hcpcsj", "drugcode", "servicecode", "proccd",
        "prccd", "prcdrcd", "hcpc", "hcpcslevelii", "hcpcsii", "cptcode",
        "linehcpcs", "jcd",
    ],
    "pos": [
        "pos", "placeofservice", "placeofsvc", "siteofcare", "siteofservice",
        "soc", "poscode", "servicelocation", "placeofserv",
    ],
    "zip": [
        "zip", "zipcode", "zip5", "patientzip", "memberzip", "servicezip",
        "providerzip", "rndrngprvdrzip5", "postalcode", "zipcd",
    ],
    "state": [
        "state", "stateabbr", "stateabbrv", "statecode", "patientstate",
        "providerstate", "servicestate", "rndrngprvdrstateabrvtn", "st", "prvdrstate",
    ],
    "allowed_amt": [
        "allowedamount", "allowedamt", "allowed", "paidamount", "paidamt", "paid",
        "billedamount", "billedamt", "charge", "chargeamount", "totalallowed",
        "allowamt", "reimbursement", "reimbamt", "netpaid", "linepaid", "amount",
    ],
    "units": [
        "units", "unit", "quantity", "qty", "totalunits", "billedunits",
        "servicecount", "totsrvcs", "totalservices", "svccount", "daysor units",
        "numberofservices", "linequantity",
        "quantitydispensed", "metricquantity", "dispensedqty", "qtydispensed",
        "metricdecimalquantity", "billedquantity", "dispensedquantity",
    ],
    "drug_name": [
        "drugname", "productname", "drug", "product", "ndcdescription",
        "labelname", "brandname", "genericname", "drugdescription", "hcpcsdesc",
        "description", "medication",
    ],
    "payer": [
        "payer", "payername", "plan", "planname", "insurer", "carrier",
        "payor", "payorname", "insurancename", "healthplan",
        "primarypayer", "primaryinsurer", "primaryinsurance", "insurancecarrier",
        "plansponsor", "lineofbusiness", "lob", "payergroup", "payorgroup",
        "insurance", "payerplanname", "financialclass",
    ],
    # v42 coding-edit fields. Defined before claim_id / patient_id / date so a
    # column like "Claim Status" or "Patient Age" is claimed by the specific
    # field, not the generic substring match ("claim", "patient", "date").
    "diagnosis": [
        "diagnosis", "diagnosiscode", "primarydiagnosis", "dx", "dx1",
        "icd10", "icd10cm", "icd10code", "icddiagnosis", "principaldiagnosis",
        "diagcode", "diagnosiscd", "primarydx", "admittingdiagnosis", "icddx",
        "diagnosis1", "primarydiagnosiscode",
    ],
    "patient_age": [
        "patientage", "age", "patage", "memberage", "ageatservice", "ageyears",
        "beneage", "ptage",
    ],
    "patient_sex": [
        "patientsex", "sex", "gender", "patientgender", "patsex", "membergender",
        "membersex", "ptsex", "ptgender", "benesex", "genderdesc",
    ],
    "modifiers": [
        "modifier", "modifiers", "modifier1", "mod1", "hcpcsmodifier",
        "proceduremodifier", "mods", "modifiercode", "linemodifier",
    ],
    "claim_status": [
        "claimstatus", "claimtype", "adjudicationstatus", "adjudstatus",
        "claimstage", "openclosed", "openclosedflag", "claimsource", "sourcetype",
        "adjudication", "claimdisposition", "dispositionstatus",
    ],
    "date_of_service": [
        # intentionally narrow: the generic "date" field (defined below) still
        # catches dateofservice/dos/servicedate for v40 analytics. The coding-edit
        # screens resolve date_of_service, then fall back to date, so both work.
        "servicedatefrom", "dtofservice", "dosdate",
    ],
    "claim_id": [
        "claimid", "claimnumber", "claimno", "claim", "claimlineid", "lineid",
        "claimkey", "encounterid", "icn", "id", "rowid", "linenumber",
    ],
    "patient_id": [
        "patientid", "memberid", "member", "patient", "beneficiaryid", "beneid",
        "beneficiary", "deidentifiedpatientid", "deidpatientid", "patientkey",
        "memberkey", "enrolleeid", "subscriberid", "personid", "uniquepatientid",
        "patienttoken", "membertoken", "mrn",
    ],
    "ndc": [
        "ndc", "ndccode", "ndc11", "ndcnumber", "nationaldrugcode", "drugndc",
        "ndccd", "ndc11code", "billedndc",
    ],
    "days_supply": [
        "dayssupply", "dayssupplied", "supplydays", "dossupply", "dayofsupply",
        "daysofsupply", "dys", "dayssup",
    ],
    "ingredient_cost": [
        "ingredientcost", "ingredientcostpaid", "drugcost", "drugingredientcost",
        "ingcost", "ingredientcostsubmitted", "ingredientcostdue",
    ],
    "dispensing_fee": [
        "dispensingfee", "dispensefee", "dispfee", "dispensingfeepaid",
        "professionalfee", "dispensingfeedue",
    ],
    # v45 consistency-screen fields
    "billed_amt": [
        "billedamt", "billedamount", "chargeamt", "chargeamount", "charges",
        "submittedamt", "submittedamount", "submittedcharge", "totalcharge",
        "billedcharges", "grosscharge",
    ],
    "paid_amt": [
        "paidamt", "paidamount", "paymentamt", "paymentamount", "planpaid",
        "planpaidamt", "amountpaid", "netpaid", "paidtotal",
    ],
    "paid_date": [
        "paiddate", "paymentdate", "adjudicationdate", "adjudateddate",
        "remitdate", "checkdate", "processeddate",
    ],
    "rendering_npi": [
        "renderingnpi", "renderingprovidernpi", "renderingprovider",
        "performingnpi", "servicingnpi", "attendingnpi",
    ],
    "date": [
        "date", "servicedate", "dos", "dateofservice", "paiddate", "claimdate",
        "fromdate", "svcdate", "filldate", "datefilled",
    ],
    "billing_name": [
        "billingprovidername", "billingname", "billprovname", "providername",
        "renderingprovidername", "performingprovidername", "suppliername",
        "billingprovidernm", "rndrngprvdrname", "servicingprovidername",
        "billerprovidername", "organizationname", "orgname", "legalbusinessname",
        "supplierorganizationname", "renderingname", "provname", "facilityname",
    ],
    "referring_name": [
        "referringprovidername", "referringname", "refname", "referrername",
        "orderingprovidername", "prescribername", "refprovname",
        "referringprovidernm", "orderingreferringname", "ordprovname",
        "orderingname", "referringorgname", "refprvdrname",
    ],
    "referring_specialty": [
        "referringproviderspecialty", "referringspecialty", "refspecialty",
        "referringprovidertaxonomy", "orderingproviderspecialty",
        "referringtaxonomy", "refprovspecialty", "referringproviderspecialtydesc",
        "prescriberspecialty", "refspec", "referringspec", "ordprovspecialty",
        "ordprovtaxonomy", "referringprovspecialty", "refprovtaxonomy",
    ],
    "billing_specialty": [
        "billingproviderspecialty", "billingspecialty", "billprovspecialty",
        "renderingproviderspecialty", "billingprovidertaxonomy",
        "providertaxonomy", "performingproviderspecialty", "provspecialty",
        "providerspecialty", "specialty", "taxonomy", "taxonomydescription",
    ],
    "entity_type": [
        "entitytype", "providerentitytype", "entitytypecode", "enttype",
        "npitype", "entitytypedesc", "proventitytype", "billingentitytype",
        "providerentitytypecode", "nppestype", "individualororganization",
        "entitytypeindividualorganization", "providertype",
    ],
    "billing_affiliation": [
        "billingprovideraffiliation", "billingaffiliation", "billingorganization",
        "billingorg", "billinggroup", "billinghealthsystem", "billingsystem",
        "billingparent", "billingprovideraffil", "affiliation",
        "groupaffiliation", "groupname", "practicename", "parentorganization",
    ],
    "referring_affiliation": [
        "referringprovideraffiliation", "referringaffiliation",
        "referringorganization", "referringorg", "referringgroup",
        "referringhealthsystem", "referringsystem", "referringparent",
        "referringgroupname", "referringpracticename",
    ],
}

# ---------------------------------------------------------------------------
# CMS dataset titles (exact 'title' strings in data.cms.gov/data.json).
# UUIDs are NOT hardcoded; clients.CMSClient resolves the 'latest' vintage.
# ---------------------------------------------------------------------------
DATASET_TITLES = {
    "physician_provider": "Medicare Physician & Other Practitioners - by Provider and Service",
    "physician_geo":      "Medicare Physician & Other Practitioners - by Geography and Service",
    "dme_supplier":       "Medicare Durable Medical Equipment, Devices & Supplies - by Supplier and Service",
    "dme_referring":      "Medicare Durable Medical Equipment, Devices & Supplies - by Referring Provider and Service",
    "partd_provider":     "Medicare Part D Prescribers - by Provider and Drug",
    "psps":               "Physician/Supplier Procedure Summary",
    "market_saturation":  "Market Saturation & Utilization State-County",
    "provider_enrollment": "Medicare Fee-For-Service  Public Provider Enrollment",
    "order_referring":    "Order and Referring",
    "opt_out":            "Opt Out Affidavits",
}

# Column names in each CMS file (verified against live API June 2026).
PHYS_COLS = {
    "npi": "Rndrng_NPI", "name": "Rndrng_Prvdr_Last_Org_Name",
    "first": "Rndrng_Prvdr_First_Name", "ent": "Rndrng_Prvdr_Ent_Cd",
    "state": "Rndrng_Prvdr_State_Abrvtn", "zip": "Rndrng_Prvdr_Zip5",
    "city": "Rndrng_Prvdr_City", "type": "Rndrng_Prvdr_Type",
    "hcpcs": "HCPCS_Cd", "desc": "HCPCS_Desc", "drugind": "HCPCS_Drug_Ind",
    "place": "Place_Of_Srvc", "benes": "Tot_Benes", "srvcs": "Tot_Srvcs",
    "allowed": "Avg_Mdcr_Alowd_Amt", "paid": "Avg_Mdcr_Pymt_Amt",
}
DME_COLS = {
    "npi": "Rfrg_NPI", "name": "Rfrg_Prvdr_Last_Name_Org",
    "supplier_npi": "Suplr_NPI", "supplier_name": "Suplr_Prvdr_Last_Name_Org",
    "state": "Suplr_Prvdr_State_Abrvtn", "hcpcs": "HCPCS_Cd",
    "srvcs": "Tot_Suplr_Srvcs", "allowed": "Avg_Suplr_Mdcr_Alowd_Amt",
}

# "Not Otherwise Classified" codes: the drug is identified by NDC/free text,
# NOT by the code, so a biller cannot be inferred from the code alone.
NOC_CODES = {"J3490", "J3590", "C9399", "J9999", "J7799", "J8499", "J7999"}

# ---------------------------------------------------------------------------
# Dual-channel molecules. The same drug bills under a Part B IV J-code AND a
# self-administered (SAD) subcutaneous code/brand. Routing MUST key on the
# specific HCPCS, never the molecule name — otherwise an IV claim whose drug
# name happens to contain the brand (e.g. "Entyvio", "Stelara") gets wrongly
# grossed up (a legitimate biller thrown away), and an SC claim under the
# molecule name gets a biller invented. These IV codes force Part B and
# override any SAD brand-name match. The SC siblings stay SAD via the seed /
# NOC + brand path. (Verified against CMS HCPCS, Jun 2026.)
PARTB_IV_OVERRIDE_CODES = {
    "J3380",  # vedolizumab IV (Entyvio) — SC sibling bills C9399 / by brand
    "J3358",  # ustekinumab IV (Stelara) — SC sibling is J3357 (SAD)
    "J1602",  # golimumab IV (Simponi Aria) — SC sibling (Simponi) bills C9399
}

# Documentation map (routing uses the code set above; this is for reference).
DUAL_CHANNEL_MOLECULES = {
    "vedolizumab": {"partb_iv": "J3380", "sad_sc": "C9399 (Entyvio SC)"},
    "ustekinumab": {"partb_iv": "J3358", "sad_sc": "J3357"},
    "golimumab":   {"partb_iv": "J1602", "sad_sc": "C9399 (Simponi SC)"},
}

# Human-readable per-row channel label for the FILLED file's _Benefit_Channel
# column, so every value (and every N/A) carries a reason.
BENEFIT_CHANNEL_LABELS = {
    ("sad", "physician"):    "Part D — self-administered (gross-up; no biller)",
    ("sad", "dme"):          "Part D — self-administered (gross-up; no biller)",
    ("noc", "physician"):    "Unclassified code — drug not identifiable (gross-up)",
    ("noc", "dme"):          "Unclassified code — drug not identifiable (gross-up)",
    ("part_b", "dme"):       "Part B — DME / home-infusion supplier",
    ("part_b", "physician"): "Part B — medical biller",
}


def benefit_channel_label(benefit, channel):
    """Map a (benefit, channel) pair to a readable label; default Part B biller."""
    return BENEFIT_CHANNEL_LABELS.get(
        (str(benefit), str(channel)), "Part B — medical biller")

# Backoff tiers for referral-anchored imputation, strongest -> weakest.
# weight feeds the confidence score; 'keys' are canonical fields.
IMPUTE_TIERS = [
    {"name": "T1_full_key",     "keys": ["referring_npi", "hcpcs", "pos", "zip3"], "weight": 1.00, "source": "in_panel"},
    {"name": "T2_ref_zip",      "keys": ["referring_npi", "hcpcs", "zip3"],         "weight": 0.90, "source": "in_panel"},
    {"name": "T3_ref_drug",     "keys": ["referring_npi", "hcpcs"],                 "weight": 0.78, "source": "in_panel"},
    {"name": "T3p_payer_zip",   "keys": ["payer", "hcpcs", "zip3"],                 "weight": 0.66, "source": "in_panel"},
    {"name": "T3s_refspec_zip", "keys": ["referring_specialty", "hcpcs", "zip3"],   "weight": 0.62, "source": "in_panel"},
    {"name": "T4_drug_zip",     "keys": ["hcpcs", "zip3"],                          "weight": 0.55, "source": "in_panel"},
    {"name": "T4p_payer_state", "keys": ["payer", "hcpcs", "state"],               "weight": 0.52, "source": "in_panel"},
    {"name": "T4s_refspec_st",  "keys": ["referring_specialty", "hcpcs", "state"],  "weight": 0.50, "source": "in_panel"},
    {"name": "T5_drug_state",   "keys": ["hcpcs", "state"],                         "weight": 0.40, "source": "in_panel"},
    {"name": "T5b_drug_book",   "keys": ["hcpcs"],                                  "weight": 0.34, "source": "in_panel"},
    {"name": "T6_cms_pool",     "keys": ["hcpcs", "state"],                         "weight": 0.25, "source": "cms_pool"},
]
# Tiers at/above this index are treated as point attribution; below = distributional.
POINT_ATTRIBUTION_MAX_TIER = "T3_ref_drug"

# A point tier alone is not enough to call a recovery high-confidence. Even on a
# strong key (T1-T3) the candidate billers can be split — e.g. a referrer that
# sends to two infusion centers roughly 50/50. Writing that into the verified
# billing column would be a coin flip dressed up as a fact, so a point recovery
# is DEMOTED to a best-guess (distributional) unless BOTH hold on the
# dollar-weighted candidate mass within the matched key:
#   • the top biller clears the runner-up by at least POINT_MARGIN_MIN, and
#   • the top biller holds at least POINT_PURITY_MIN of the mass.
# This is the "not 50/50" gate: a near-tie never lands in the billing column.
POINT_MARGIN_MIN = 0.20   # top1 - top2 share gap, dollar-weighted
POINT_PURITY_MIN = 0.50   # top1 share of the key's dollar mass

# Purity and margin alone can be fooled by a single anecdote: a key seen once
# resolves to one biller at 100% with no runner-up, so it sails through the
# margin gate even though it rests on n=1. So a point recovery also needs a
# minimum number of TRAINING OBSERVATIONS behind the winning biller. The
# threshold is tier-aware: a highly specific key (exact referrer+drug+site+ZIP)
# is credible at n=1 because the specificity itself is the evidence, while a
# coarse key (referrer+drug only) needs corroboration. Below the bar, the
# recovery is demoted to a best-guess rather than written to the billing column.
POINT_MIN_OBS = {
    "T1_full_key": 1,   # referrer + hcpcs + pos + zip3  — specific, credible at 1
    "T2_ref_zip":  1,   # referrer + hcpcs + zip3        — specific, credible at 1
    "T3_ref_drug": 2,   # referrer + hcpcs               — coarse, needs >= 2
}

# --- two-hop / group-inference layer (infer.py) -------------------------------
# These fill attributable blanks the point imputer didn't confidently resolve,
# by borrowing from sibling rows in the SAME claim cluster. They are tiered
# "inferred" — they land in the billing column (so the blank rate can fall to a
# few percent) but are labelled distinctly from a verified/point recovery, never
# presented as a direct lookup. Two guards keep them honest:
#   • Cluster dominance runs on entity-ROLLED billers, and the high threshold
#     means a genuine change-of-ownership splits the cluster and fails CLOSED
#     (no inference) rather than inferring the wrong operator.
#   • Continuity inheritance never bridges a > CONTINUITY_MAX_GAP_DAYS break or a
#     site (place-of-service) change.
CLUSTER_KEYS = ("referring_npi", "hcpcs", "zip3")  # payer appended when present
CLUSTER_DOMINANCE_MIN = 0.85   # one operator must own >= this share of the cluster's populated rows
CLUSTER_MIN_SUPPORT = 3        # cluster needs >= this many populated rows to infer from
CLUSTER_USE_PAYER = True       # append payer to the cluster key when the column exists
CONTINUITY_MAX_GAP_DAYS = 90   # never inherit a biller across a longer visit gap
INFER_ROLLUP_CAP = 6000        # max populated billers to entity-roll for cluster dominance

# --- backtest-grounded calibration (pipeline Step 6.5) ------------------------
# "High confidence" should be a measured hit-rate, not an assertion. The masking
# backtest measures each tier's dollar-weighted top-1 accuracy on held-out rows;
# if a tier the imputer treats as POINT actually underperforms on that holdout,
# its recoveries are demoted to best-guess. The tier ranking is a prior; the
# holdout is evidence, and the evidence wins. A tier is only calibrated when it
# has enough holdout support, so a noisy estimate never demotes a good tier.
POINT_MIN_MEASURED_ACC = 0.70  # a point tier below this measured top-1 acc is demoted
CALIBRATION_MIN_HOLDOUT = 20   # min held-out rows before a tier's measured acc is trusted
HIGH_CONF_ACC = 0.85           # measured top-1 at/above this reads "high"; bar..this reads "medium"
BACKTEST_FOLDS = 5             # k-fold splits for the masking backtest (every known row tested once)

# Candidate scoring weights billers by allowed dollars, not row count: one
# $9,000 IVIG claim should outweigh a $20 saline push when deciding who bills a
# referrer's volume. Set to None to fall back to row-count (legacy) behavior.
ATTRIBUTION_WEIGHT_COL = "allowed_amt"


# --------------------------------------------------------------------------- #
# v31 — NDC -> best-J-code disambiguation, payer-type channel, control totals
# --------------------------------------------------------------------------- #

# Not-otherwise-classified / unclassified catch-all HCPCS. Assigning one of these
# to an NDC is never a real drug identification, so the NDC->J-code resolver
# refuses to *force* a row onto a catch-all (it stays an NDC, flagged) and the
# common-name grouper never folds a catch-all into a J-code-keyed cut on its own.
# (Verified against CMS HCPCS descriptors, Jun 2026.)
NOC_CATCHALL_CODES = {
    "J3490",  # Unclassified drugs
    "J3590",  # Unclassified biologics
    "J9999",  # Not otherwise classified, antineoplastic
    "J8499",  # Prescription drug, oral, non-chemo, NOS
    "J8999",  # Prescription drug, oral, chemo, NOS
    "J7599",  # Immunosuppressive drug, NOC
    "J7699",  # Inhalation solution, compounded, NOC
    "J7799",  # NOC drugs, other than inhalation
    "J7999",  # Compounded drug, NOC
    "C9399",  # Unclassified drugs or biologicals
    "Q0181",  # Unspecified oral dosage form
}

# Non-specific "NOS" codes that live INSIDE a real drug class (a valid class code,
# but not brand-specific). Preferred over a catch-all, dispreferred vs a brand
# code. Extend as needed; the resolver also treats any descriptor containing
# "NOS" / "not otherwise specified" as non-specific.
NOS_CODES = {
    "J1599",  # Injection, immune globulin, NOS
    "J7599",  # (also NOC above; harmless overlap)
    "J1566",  # IG, powder, NOS-ish lyophilized (kept mild)
}


def is_catchall_code(code) -> bool:
    return str(code).strip().upper() in NOC_CATCHALL_CODES


# Payer-type classifier. Government claims for a specialty pharmacy are billed
# through separate pharmacy NPIs (the exact issue raised on the sync: "government
# claims are built through their own pharmacies, unique NPIs"). To tell those
# NPIs apart we first need a payer-type per row. Rules are ordered; first match
# wins. Matched case-insensitively against the payer / plan text.
PAYER_TYPE_RULES = [
    ("military_va", ["tricare", "champva", "va ", "veterans", "humana military",
                     "health net federal", "triwest", "us family health", "department of defense",
                     "dod ", "military"]),
    ("medicaid",    ["medicaid", "medi-cal", "medical assistance", "chip", "husky",
                     "soonercare", "tenncare", "denali", "apple health", "masshealth",
                     "managed medicaid", "star kids", "star plus", "star+plus", "star medicaid"]),
    ("medicare",    ["medicare", "mapd", "ma-pd", " ma plan", "medicare advantage",
                     "part b", "part d", "dsnp", "d-snp", "csnp", "railroad medicare",
                     "ghi medicare", "aarp medicare"]),
    ("commercial",  ["blue cross", "bcbs", "bluecross", "anthem", "aetna", "cigna",
                     "unitedhealth", "united health", "uhc", "humana", "centene",
                     "ambetter", "molina", "kaiser", "oscar", "community health choice",
                     "commercial", "ppo", "hmo", "epo", "employer", "exchange", "marketplace",
                     "self-funded", "self funded", "erisa", "wellcare", "elevance"]),
]


def classify_payer_type(payer_text) -> str:
    """One of: medicare | medicaid | military_va | commercial | unknown.
    Government = {medicare, medicaid, military_va}. Ordered so a 'Medicaid'
    that also contains 'managed' resolves to medicaid, and a Medicare Advantage
    plan named 'UnitedHealthcare Medicare' resolves to medicare, not commercial.
    """
    s = str(payer_text or "").lower()
    if not s.strip():
        return "unknown"
    # military/VA and medicaid checked before medicare so 'VA medicaid' etc. land
    # correctly; then medicare (catches 'medicare advantage'); commercial last.
    for label, toks in PAYER_TYPE_RULES:
        for t in toks:
            if t in s:
                return label
    return "unknown"


GOVERNMENT_PAYER_TYPES = {"medicare", "medicaid", "military_va"}
