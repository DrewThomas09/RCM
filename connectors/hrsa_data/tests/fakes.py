"""In-memory fake HRSA download server for tests — no socket, deterministic.

A :class:`FakeHrsa` is an :data:`Opener` (``(url, headers, timeout) ->
RawResponse``) that serves canned CSV text per download path. It also
models 429 + ``Retry-After`` and 5xx via a scripted ``transients`` map so
the transport's retry path is exercised without a network.

Fixture fidelity: the header lists below are the **real, complete
header rows** of the live files (sampled 2026-07-06), and the emitted
CSV mirrors the live quirks — a dangling trailing comma on the header
*and* every data row, prose headers with ``%``/``/``/``-``, values with
stray padding (``" 6"``), quoted values containing commas, and a
byte-identical duplicate line in the HPSA fixture (the live files
contain a handful). Row values are hand-written but shaped from real
records so normalize/table tests assert against realistic data.
"""
from __future__ import annotations

import csv
import io
from typing import Dict, List, Optional, Tuple

from ..transport import RawResponse

# ── real live header rows (empty trailing cell added by _to_csv) ──────
HPSA_PC_HEADERS: Tuple[str, ...] = (
    "HPSA Name", "HPSA ID", "Designation Type", "HPSA Discipline Class",
    "HPSA Score", "PC MCTA Score", "Primary State Abbreviation",
    "HPSA Status", "HPSA Designation Date",
    "HPSA Designation Last Update Date", "Metropolitan Indicator",
    "HPSA Geography Identification Number", "HPSA Degree of Shortage",
    "Withdrawn Date", "HPSA FTE", "HPSA Designation Population",
    "% of Population Below 100% Poverty", "HPSA Formal Ratio",
    "HPSA Population Type", "Rural Status", "Longitude", "Latitude",
    "BHCMIS Organization Identification Number", "Break in Designation",
    "Common County Name", "Common Postal Code", "Common Region Name",
    "Common State Abbreviation", "Common State County FIPS Code",
    "Common State FIPS Code", "Common State Name", "County Equivalent Name",
    "County or County Equivalent Federal Information Processing Standard Code",
    "Discipline Class Number", "HPSA Address", "HPSA City",
    "HPSA Component Name", "HPSA Component Source Identification Number",
    "HPSA Component State Abbreviation", "HPSA Component Type Code",
    "HPSA Component Type Description",
    "HPSA Designation Population Type Description",
    "HPSA Estimated Served Population",
    "HPSA Estimated Underserved Population",
    "HPSA Metropolitan Indicator Code", "HPSA Population Type Code",
    "HPSA Postal Code", "HPSA Provider Ratio Goal",
    "HPSA Resident Civilian Population", "HPSA Shortage", "HPSA Status Code",
    "HPSA Type Code", "HPSA Withdrawn Date String",
    "Primary State FIPS Code", "Primary State Name", "Provider Type",
    "Rural Status Code", "State Abbreviation",
    "State and County Federal Information Processing Standard Code",
    "State FIPS Code", "State Name",
    "U.S. - Mexico Border 100 Kilometer Indicator",
    "U.S. - Mexico Border County Indicator",
    "Data Warehouse Record Create Date",
    "Data Warehouse Record Create Date Text",
)

# The dental / mental-health files publish the same columns minus
# "PC MCTA Score" (verified live).
HPSA_DH_HEADERS: Tuple[str, ...] = tuple(
    h for h in HPSA_PC_HEADERS if h != "PC MCTA Score")

MUA_HEADERS: Tuple[str, ...] = (
    "MUA/P ID", "MUA/P Area Code", "MUA/P Service Area Name",
    "Designation Type Code", "Designation Type", "MUA/P Status Code",
    "MUA/P Status Description", "Designation Date",
    "MUA/P Designation Date String", "MUA/P Update Date",
    "MUA/P Update Date String",
    "Medically Underserved Area/Population (MUA/P) Withdrawal Date",
    "Medically Underserved Area/Population (MUA/P) Withdrawal Date in Text Format",
    "Break in Designation", "IMU Score", "MUA/P Population Type Code",
    "Population Type",
    "Medically Underserved Area/Population (MUA/P) Metropolitan Indicator",
    "Medically Underserved Area/Population (MUA/P) Metropolitan Description",
    "Medically Underserved Area/Population (MUA/P) Component Geographic Name",
    "Medically Underserved Area/Population (MUA/P) Component Geographic Type Code",
    "Medically Underserved Area/Population (MUA/P) Component Geographic Type Description",
    "HHS Region Code", "HHS Region Name", "State FIPS Code", "State Name",
    "State Abbreviation",
    "State and County Federal Information Processing Standard Code",
    "County or County Equivalent Federal Information Processing Standard Code",
    "Complete County Name", "County Equivalent Name", "County Description",
    "County Subdivision Name", "County Subdivision FIPS Code",
    "Census Tract", "Rural Status Code", "Rural Status Description",
    "U.S. - Mexico Border 100 Kilometer Indicator",
    "U.S. - Mexico Border County Indicator",
    "Percent of Population with Incomes at or Below 100 Percent of the U.S. Federal Poverty Level",
    "Percent of Population with Incomes at or Below 100 Percent of the U.S. Federal Poverty Level Index of Medical Underservice Score",
    "Percentage of Population Age 65 and Over",
    "Percentage of Population Age 65 and Over IMU Score",
    "Infant Mortality Rate", "Infant Mortality Rate IMU Score",
    "Designation Population in a Medically Underserved Area/Population (MUA/P)",
    "Medically Underserved Area/Population (MUA/P) Total Resident Civilian Population",
    "Providers per 1000 Population",
    "Ratio of Providers per 1000 Population",
    "Ratio of Providers per 1000 Population IMU Score",
    "Primary HHS Region Code", "Primary HHS Region Name",
    "Primary State FIPS Code", "Primary State Abbreviation",
    "Primary State Name", "Common Region Code", "Common Region Name",
    "Common State Name", "Common State Abbreviation",
    "Common State FIPS Code", "Common State County FIPS Code",
    "Common County Name", "Data Warehouse Record Create Date",
    "Data Warehouse Record Create Date Text",
)

SITES_HEADERS: Tuple[str, ...] = (
    "Health Center Type", "Health Center Number",
    "BHCMIS Organization Identification Number", "BPHC Assigned Number",
    "Site Name", "Site Address", "Site City", "Site State Abbreviation",
    "Site Postal Code", "Site Telephone Number", "Site Web Address",
    "Operating Hours per Week",
    "Health Center Location Setting Identification Number",
    "Health Center Service Delivery Site Location Setting Description",
    "Health Center Status Identification Number", "Site Status Description",
    "FQHC Site Medicare Billing Number", "FQHC Site NPI Number",
    "Health Center Location Identification Number",
    "Health Center Location Type Description",
    "Health Center Type Identification Number",
    "Health Center Type Description",
    "Health Center Operator Identification Number",
    "Health Center Operator Description",
    "Health Center Operating Schedule Identification Number",
    "Health Center Operational Schedule Description",
    "Health Center Operating Calendar Surrogate Key",
    "Health Center Operating Calendar", "Site Added to Scope this Date",
    "Health Center Name", "Health Center Organization Street Address",
    "Health Center Organization City", "Health Center Organization State",
    "Health Center Organization ZIP Code",
    "Grantee Organization Type Description",
    "Geocoding Artifact Address Primary X Coordinate",
    "Geocoding Artifact Address Primary Y Coordinate",
    "U.S. - Mexico Border 100 Kilometer Indicator",
    "U.S. - Mexico Border County Indicator",
    "State and County Federal Information Processing Standard Code",
    "Complete County Name", "County Equivalent Name", "County Description",
    "HHS Region Code", "HHS Region Name", "State FIPS Code", "State Name",
    "State FIPS and Congressional District Number Code",
    "Congressional District Number", "Congressional District Name",
    "Congressional District Code", "U.S. Congressional Representative Name",
    "Name of U.S. Senator Number One", "Name of U.S. Senator Number Two",
    "Data Warehouse Record Create Date",
)


def _to_csv(headers: Tuple[str, ...], rows: List[Dict[str, str]]) -> str:
    """Emit CSV the way HRSA publishes it: header + every data row carry
    a dangling trailing comma (an empty last cell)."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(list(headers) + [""])
    for row in rows:
        writer.writerow([row.get(h, "") for h in headers] + [""])
    return buf.getvalue()


# ── ready-made fixture rows (realistic values, small counts) ──────────
def hpsa_pc_rows() -> List[Dict[str, str]]:
    base = {
        "Designation Type": "Geographic HPSA",
        "HPSA Discipline Class": "Primary Care",
        "HPSA Status": "Designated",
        "HPSA Designation Date": "06/01/2012",
        "HPSA Designation Last Update Date": "12/31/2020",
        "Rural Status": "Rural",
        "HPSA Degree of Shortage": "Not applicable",
        "Provider Type": "Not Applicable",
        "Data Warehouse Record Create Date": "07/03/2026",
        "Data Warehouse Record Create Date Text": "2026/07/03",
    }
    r1 = dict(base, **{
        "HPSA Name": "Lubbock County", "HPSA ID": "1481234567",
        "HPSA Score": "18", "PC MCTA Score": " 6",     # live padding quirk
        "Primary State Abbreviation": "TX",
        "HPSA Geography Identification Number": "48303",
        "Common County Name": "Lubbock, TX", "Common State Abbreviation": "TX",
        "Common State County FIPS Code": "48303",
        "HPSA Estimated Underserved Population": "35000",
        "HPSA Formal Ratio": "3800:1",
        "State Abbreviation": "TX", "State Name": "Texas",
    })
    r2 = dict(base, **{
        "HPSA Name": "Deaf Smith County", "HPSA ID": "1481234568",
        "HPSA Score": "21", "PC MCTA Score": "9",
        "Primary State Abbreviation": "TX",
        "HPSA Geography Identification Number": "48117",
        "Common County Name": "Deaf Smith, TX",
        "Common State Abbreviation": "TX",
        "Common State County FIPS Code": "48117",
        "HPSA Estimated Underserved Population": "12000",
        # Live files quote values containing commas.
        "HPSA Component Name": "Hereford, city of",
        "State Abbreviation": "TX", "State Name": "Texas",
    })
    r3 = dict(base, **{
        "HPSA Name": "Aur", "HPSA ID": "1688361205",
        "Designation Type": "High Needs Geographic HPSA",
        "HPSA Score": "25", "PC MCTA Score": " 6",
        "Primary State Abbreviation": "MH",
        "HPSA Geography Identification Number": "68050",
        "Common County Name": "Aur, MH", "Common State Abbreviation": "MH",
        "Common State County FIPS Code": "68050",
        "State Abbreviation": "MH", "State Name": "Marshall Islands",
    })
    return [r1, r2, r3]


def hpsa_pc_csv(duplicate_last_row: bool = False) -> str:
    rows = hpsa_pc_rows()
    if duplicate_last_row:
        rows = rows + [dict(rows[-1])]  # byte-identical duplicate line
    return _to_csv(HPSA_PC_HEADERS, rows)


def hpsa_dh_csv() -> str:
    row = {
        "HPSA Name": "Marshall Islands", "HPSA ID": "6689996801",
        "Designation Type": "Geographic HPSA",
        "HPSA Discipline Class": "Dental Health", "HPSA Score": "0",
        "Primary State Abbreviation": "MH", "HPSA Status": "Withdrawn",
        "HPSA Geography Identification Number": "68160",
        "Common State Abbreviation": "MH",
        "Common State County FIPS Code": "68160",
        "HPSA Formal Ratio": "15019:1",
        "State Abbreviation": "MH", "State Name": "Marshall Islands",
        "Data Warehouse Record Create Date": "07/03/2026",
        "Data Warehouse Record Create Date Text": "2026/07/03",
    }
    return _to_csv(HPSA_DH_HEADERS, [row])


def mua_rows() -> List[Dict[str, str]]:
    r1 = {
        "MUA/P ID": "1512420473", "MUA/P Area Code": "51015",
        "MUA/P Service Area Name": "Augusta-Staunton-Waynesboro MUP",
        "Designation Type Code": "MUP",
        "Designation Type": "Medically Underserved Population",
        "MUA/P Status Code": "D", "MUA/P Status Description": "Designated",
        "Designation Date": "03/23/2022",
        "MUA/P Designation Date String": "2022/03/23",
        "MUA/P Update Date String": "2022/03/23",
        "IMU Score": "60.00", "Population Type": "MUP Low Income",
        "State FIPS Code": "51", "State Name": "Virginia",
        "State Abbreviation": "VA",
        "State and County Federal Information Processing Standard Code": "51015",
        "County Subdivision FIPS Code": "",
        "Census Tract": "Not Applicable",
        "Medically Underserved Area/Population (MUA/P) Component Geographic Name": "Augusta",
        # Live padding quirk: fixed-width residue in County Description.
        "County Description": "County            ",
        "Data Warehouse Record Create Date": "07/03/2026",
        "Data Warehouse Record Create Date Text": "2026/07/03",
    }
    # MUA/P id re-use, the reason the service-area name is in the key: a
    # Designated and a Withdrawn designation sharing id AND geography.
    r2 = {
        "MUA/P ID": "01458", "MUA/P Area Code": "23021",
        "MUA/P Service Area Name": "Greenville PCAA",
        "Designation Type Code": "MUA",
        "Designation Type": "Medically Underserved Area",
        "MUA/P Status Code": "D", "MUA/P Status Description": "Designated",
        "MUA/P Update Date String": "2012/08/30",
        "IMU Score": "51.30",
        "State Abbreviation": "ME", "State Name": "Maine",
        "State and County Federal Information Processing Standard Code": "23021",
        "County Subdivision FIPS Code": "2302105560",
        "Census Tract": "Not Applicable",
        "Medically Underserved Area/Population (MUA/P) Component Geographic Name": "Blanchard",
    }
    r3 = dict(r2, **{
        "MUA/P Service Area Name": "Piscataquis Service Area",
        "MUA/P Status Code": "W", "MUA/P Status Description": "Withdrawn",
        "MUA/P Update Date String": "2010/11/08",
        "IMU Score": "51.76",
    })
    return [r1, r2, r3]


def mua_csv() -> str:
    return _to_csv(MUA_HEADERS, mua_rows())


def sites_rows() -> List[Dict[str, str]]:
    r1 = {
        "Health Center Type": "Federally Qualified Health Center (FQHC)",
        "Health Center Number": "H80CS00189",
        "BHCMIS Organization Identification Number": "051570",
        "BPHC Assigned Number": "BPS-H80-041310",
        "Site Name": "YWCA Cincinnati",
        "Site Address": "3565 Van Antwerp Pl", "Site City": "Cincinnati",
        "Site State Abbreviation": "OH", "Site Postal Code": "45229-2631",
        "Site Telephone Number": "513-286-7899",
        "Site Status Description": "Active",
        "FQHC Site NPI Number": "1234567893",
        "Health Center Type Description": "Service Delivery Site",
        "Site Added to Scope this Date": "02/09/2026",
        "Health Center Name": "THE CINCINNATI HEALTH NETWORK, INC.",
        "Health Center Organization State": "OH",
        "Grantee Organization Type Description":
            "Corporate Entity, Federal Tax Exempt",   # embedded comma
        "Geocoding Artifact Address Primary X Coordinate": "-84.49394921",
        "Geocoding Artifact Address Primary Y Coordinate": "39.14710252",
        "State FIPS Code": "39", "State Name": "Ohio",
        "Data Warehouse Record Create Date": "07/03/2026",
    }
    r2 = {
        "Health Center Type": "Federally Qualified Health Center (FQHC)",
        "Health Center Number": "H80CS26599",
        "BPHC Assigned Number": "BPS-H80-556677",
        "Site Name": "South Plains Clinic", "Site City": "Lubbock",
        "Site State Abbreviation": "TX", "Site Postal Code": "79401",
        "Site Status Description": "Active",
        "FQHC Site NPI Number": "1987654325",
        "Health Center Name": "SOUTH PLAINS RURAL HEALTH SERVICES INC",
        "State FIPS Code": "48", "State Name": "Texas",
        "Data Warehouse Record Create Date": "07/03/2026",
    }
    return [r1, r2]


def sites_csv() -> str:
    return _to_csv(SITES_HEADERS, sites_rows())


class FakeHrsa:
    """Serve canned CSV bodies per path; script transient failures."""

    def __init__(self) -> None:
        self.files: Dict[str, str] = {}
        self.calls: List[str] = []
        # Scripted transient responses keyed by call index:
        # {idx: (status, headers)}.
        self.transients: Dict[int, Tuple[int, Optional[Dict[str, str]]]] = {}

    def add(self, path: str, csv_text: str) -> "FakeHrsa":
        self.files[path] = csv_text
        return self

    def __call__(self, url: str, headers: Dict[str, str], timeout: float
                 ) -> RawResponse:
        idx = len(self.calls)
        self.calls.append(url)
        if idx in self.transients:
            status, hdrs = self.transients[idx]
            return RawResponse(status=status, headers=hdrs or {}, body=b"err")
        path = url.split("data.hrsa.gov", 1)[-1].split("?", 1)[0]
        if path not in self.files:
            return RawResponse(status=404, body=b"Not Found")
        return RawResponse(status=200, body=self.files[path].encode("utf-8"))
