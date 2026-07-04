"""ZIP3 -> US state crosswalk, built from the standard USPS ZIP-prefix ranges.
Used only as a *proxy* to fill a missing state when a ZIP is present; a handful
of split prefixes are approximate and that is fine for imputation/QA purposes.
"""

# (lo, hi, state) inclusive ranges over the first three ZIP digits.
_RANGES = [
    (("005", "005"), "NY"), (("004", "004"), "NY"),
    (("006", "009"), "PR"),
    (("010", "027"), "MA"), (("055", "055"), "MA"),
    (("028", "029"), "RI"),
    (("030", "038"), "NH"),
    (("039", "049"), "ME"),
    (("050", "059"), "VT"),
    (("060", "069"), "CT"),
    (("070", "089"), "NJ"),
    (("090", "098"), "AE"),                       # military Europe
    (("100", "149"), "NY"),
    (("150", "196"), "PA"),
    (("197", "199"), "DE"),
    (("200", "200"), "DC"), (("202", "205"), "DC"), (("569", "569"), "DC"),
    (("201", "201"), "VA"), (("220", "246"), "VA"),
    (("206", "219"), "MD"),
    (("247", "268"), "WV"),
    (("270", "289"), "NC"),
    (("290", "299"), "SC"),
    (("300", "319"), "GA"), (("398", "399"), "GA"),
    (("320", "349"), "FL"),
    (("340", "340"), "AA"),                       # military Americas
    (("350", "369"), "AL"),
    (("370", "385"), "TN"),
    (("386", "397"), "MS"),
    (("400", "427"), "KY"),
    (("430", "459"), "OH"),
    (("460", "479"), "IN"),
    (("480", "499"), "MI"),
    (("500", "528"), "IA"),
    (("530", "549"), "WI"),
    (("550", "567"), "MN"),
    (("570", "577"), "SD"),
    (("580", "588"), "ND"),
    (("590", "599"), "MT"),
    (("600", "629"), "IL"),
    (("630", "658"), "MO"),
    (("660", "679"), "KS"),
    (("680", "693"), "NE"),
    (("700", "714"), "LA"),
    (("716", "729"), "AR"),
    (("730", "749"), "OK"),
    (("750", "799"), "TX"), (("885", "885"), "TX"),
    (("800", "816"), "CO"),
    (("820", "831"), "WY"),
    (("832", "838"), "ID"),
    (("840", "847"), "UT"),
    (("850", "865"), "AZ"),
    (("870", "884"), "NM"),
    (("889", "898"), "NV"),
    (("900", "961"), "CA"),
    (("962", "966"), "AP"),                       # military Pacific
    (("967", "968"), "HI"),
    (("970", "979"), "OR"),
    (("980", "994"), "WA"),
    (("995", "999"), "AK"),
]

US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "HI", "ID",
    "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO",
    "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA",
    "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "PR", "VI", "AE", "AA", "AP",
}


def _build():
    m = {}
    for (lo, hi), st in _RANGES:
        for n in range(int(lo), int(hi) + 1):
            m[f"{n:03d}"] = st
    return m


ZIP3_TO_STATE = _build()


def state_from_zip(zip_value):
    """Return a 2-letter state for any ZIP/ZIP3-ish value, or '' if unknown."""
    import re
    try:
        import pandas as _pd
        if zip_value is None or _pd.isna(zip_value):
            return ""
    except Exception:
        if zip_value is None:
            return ""
    digits = re.sub(r"\D", "", str(zip_value))
    if len(digits) < 3:
        return ""
    return ZIP3_TO_STATE.get(digits[:3], "")
