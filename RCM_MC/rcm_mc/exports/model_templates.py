"""Downloadable Excel model templates — the deal team's starter kit.

Partners kept rebuilding the same workbooks (quick LBO, QoE databook,
NWC peg, 13-week cash, market model, payer-mix sensitivity) from
scratch in every CDD sprint because nothing on the desk shipped a
ready-to-edit model. This module is the template library behind
``/excel-templates``: every workbook downloads with **live formulas**
and the banker blue-input convention (blue cells = assumptions you
edit, black cells = formulas that recompute), so the file is a working
model the moment it opens — not a static data dump.

Built on the stdlib ``xlsx_writer`` (no openpyxl requirement, "no new
runtime dependencies"). Formulas use the explicit ``F(...)`` wrapper —
never inferred from strings — so templates stay immune to the Excel
formula-injection class the CSV exporters already defend against.

Public API:
    TEMPLATES                      — ordered registry of TemplateSpec
    get_template(slug)             — TemplateSpec or None
    build_template_xlsx(slug)      — workbook bytes for a registry slug
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from .xlsx_writer import F, Sheet, write_xlsx

# Shared first rows for every sheet that carries inputs: the convention
# line is the difference between a template a VP trusts and one they
# re-audit cell by cell.
_CONVENTION = "Blue cells = inputs (edit these). Black cells = live formulas."


@dataclass(frozen=True)
class TemplateSpec:
    slug: str
    title: str
    category: str          # "Deal Math" | "QoE & Accounting" | "CDD & Market"
    description: str       # one-line partner-facing description
    sheets: List[str]      # sheet names, for the library page listing
    builder: Callable[[], List[Sheet]]


# ---------------------------------------------------------------- helpers

def _years_header(label: str, n: int, start: int = 0) -> list:
    row = [(label, "header")]
    for i in range(start, start + n):
        row.append((f"Yr {i}", "header"))
    return row


def _blank(n: int = 1) -> List[list]:
    return [[""] for _ in range(n)]


# ---------------------------------------------------------------- 1) LBO

def _lbo_model() -> List[Sheet]:
    """Quick LBO: sources & uses, 5-year debt sweep, MOIC/IRR.

    Single-sheet by design — the point is a screen-stage answer in
    under a minute, not a 14-tab artifact. Yr 0..5 live in B..G.
    """
    r: List[list] = []
    r.append([("QUICK LBO MODEL", "header"), ("", "header"), ("", "header"),
              ("", "header"), ("", "header"), ("", "header"), ("", "header")])
    r.append([_CONVENTION])
    r.append([""])
    # -- Transaction assumptions (rows 4-12)
    r.append([("TRANSACTION ASSUMPTIONS", "label")])
    r.append(["Entry EBITDA ($M)", (25.00, "input_num")])                  # B5
    r.append(["Entry multiple", (9.50, "input_num")])                      # B6
    r.append(["Entry TEV ($M)", (F("B5*B6"), "num2")])                     # B7
    r.append(["Leverage (Debt / EBITDA)", (5.00, "input_num")])            # B8
    r.append(["Debt raised ($M)", (F("B5*B8"), "num2")])                   # B9
    r.append(["Transaction fees (% of TEV)", (0.02, "input_pct")])         # B10
    r.append(["Sponsor equity ($M)", (F("B7-B9+B7*B10"), "num2")])         # B11
    r.append([""])
    # -- Operating case (rows 13-22); Yr0 in B, Yr1-5 in C..G
    r.append(_years_header("OPERATING CASE", 6))                           # row 13
    r.append(["Revenue ($M)", (120.00, "input_num"),                       # row 14
              (F("B14*(1+C15)"), "num2"), (F("C14*(1+D15)"), "num2"),
              (F("D14*(1+E15)"), "num2"), (F("E14*(1+F15)"), "num2"),
              (F("F14*(1+G15)"), "num2")])
    r.append(["Revenue growth %", "",                                      # row 15
              (0.08, "input_pct"), (0.08, "input_pct"), (0.07, "input_pct"),
              (0.06, "input_pct"), (0.06, "input_pct")])
    r.append(["EBITDA margin %", (F("B5/B14"), "pct"),                     # row 16
              (0.215, "input_pct"), (0.225, "input_pct"), (0.235, "input_pct"),
              (0.24, "input_pct"), (0.245, "input_pct")])
    r.append(["EBITDA ($M)", (F("B5"), "num2"),                            # row 17
              (F("C14*C16"), "num2"), (F("D14*D16"), "num2"),
              (F("E14*E16"), "num2"), (F("F14*F16"), "num2"),
              (F("G14*G16"), "num2")])
    r.append(["Capex % of revenue", "",                                    # row 18
              (0.03, "input_pct"), (0.03, "input_pct"), (0.03, "input_pct"),
              (0.03, "input_pct"), (0.03, "input_pct")])
    r.append(["Cash taxes % of EBITDA", "",                                # row 19
              (0.18, "input_pct"), (0.18, "input_pct"), (0.18, "input_pct"),
              (0.18, "input_pct"), (0.18, "input_pct")])
    r.append(["Free cash flow pre-debt ($M)", "",                          # row 20
              (F("C17-C14*C18-C17*C19"), "num2"),
              (F("D17-D14*D18-D17*D19"), "num2"),
              (F("E17-E14*E18-E17*E19"), "num2"),
              (F("F17-F14*F18-F17*F19"), "num2"),
              (F("G17-G14*G18-G17*G19"), "num2")])
    r.append([""])
    # -- Debt schedule (rows 22-26); Yr1-5 stay in C..G to align with
    # the operating case, so B gets a blank header cell.
    r.append([("DEBT SCHEDULE", "header"), ("", "header"),
              ("Yr 1", "header"), ("Yr 2", "header"), ("Yr 3", "header"),
              ("Yr 4", "header"), ("Yr 5", "header")])                     # row 22
    r.append(["Debt, beginning ($M)", "",                                  # row 23
              (F("B9"), "num2"), (F("C26"), "num2"), (F("D26"), "num2"),
              (F("E26"), "num2"), (F("F26"), "num2")])
    r.append(["Cash interest % (all-in)", "",                              # row 24
              (0.09, "input_pct"), (0.09, "input_pct"), (0.09, "input_pct"),
              (0.09, "input_pct"), (0.09, "input_pct")])
    r.append(["Interest expense ($M)", "",                                 # row 25
              (F("C23*C24"), "num2"), (F("D23*D24"), "num2"),
              (F("E23*E24"), "num2"), (F("F23*F24"), "num2"),
              (F("G23*G24"), "num2")])
    r.append(["Debt, ending (100% sweep) ($M)", "",                        # row 26
              (F("MAX(C23-MAX(C20-C25,0),0)"), "num2"),
              (F("MAX(D23-MAX(D20-D25,0),0)"), "num2"),
              (F("MAX(E23-MAX(E20-E25,0),0)"), "num2"),
              (F("MAX(F23-MAX(F20-F25,0),0)"), "num2"),
              (F("MAX(G23-MAX(G20-G25,0),0)"), "num2")])
    r.append([""])
    # -- Exit & returns (rows 28-33)
    r.append([("EXIT & RETURNS", "label")])                                # row 28
    r.append(["Exit multiple (Yr 5 EBITDA)", (9.50, "input_num")])         # B29
    r.append(["Exit TEV ($M)", (F("G17*B29"), "num2")])                    # B30
    r.append(["Exit equity ($M)", (F("B30-G26"), "num2")])                 # B31
    r.append(["MOIC", (F("B31/B11"), "mult")])                             # B32
    r.append(["IRR (5-yr hold)", (F("(B31/B11)^(1/5)-1"), "pct")])         # B33
    return [Sheet("Quick LBO", r,
                  col_widths=[34, 13, 13, 13, 13, 13, 13])]


# ----------------------------------------------------- 2) QoE databook

def _qoe_databook() -> List[Sheet]:
    """Reported-to-Adjusted EBITDA walk plus a TTM revenue cadence tab."""
    walk: List[list] = []
    walk.append([("QoE ADJUSTED EBITDA WALK", "header"), ("", "header"),
                 ("", "header"), ("", "header")])
    walk.append([_CONVENTION])
    walk.append([""])
    walk.append([("Adjustment", "header"), ("FY-1 ($)", "header"),
                 ("TTM ($)", "header"), ("Notes / evidence", "header")])
    walk.append(["Reported EBITDA",
                 (18_400_000, "input_money"), (19_700_000, "input_money"),
                 "Per management P&L"])
    adjustments = [
        ("Owner compensation normalization", 450_000, 450_000),
        ("One-time legal settlement", 300_000, 0),
        ("Out-of-period revenue (cutoff)", -220_000, -180_000),
        ("Deferred revenue haircut", -150_000, -150_000),
        ("Run-rate impact of signed contracts", 0, 600_000),
        ("Above/below-market related-party rent", 120_000, 120_000),
        ("Non-recurring recruiting / severance", 200_000, 90_000),
    ]
    for name, fy1, ttm in adjustments:
        walk.append([name, (fy1, "input_money"), (ttm, "input_money"),
                     ("Describe support here", "input")])
    first, last = 6, 5 + len(adjustments)
    walk.append([("Total adjustments", "label"),
                 (F(f"SUM(B{first}:B{last})"), "money2"),
                 (F(f"SUM(C{first}:C{last})"), "money2"), ""])
    walk.append([("Adjusted EBITDA", "label"),
                 (F(f"B5+B{last + 1}"), "money2"),
                 (F(f"C5+C{last + 1}"), "money2"), ""])
    walk.append(["Adjustments as % of reported",
                 (F(f"B{last + 1}/B5"), "pct"),
                 (F(f"C{last + 1}/C5"), "pct"), ""])

    cadence: List[list] = []
    cadence.append([("TTM REVENUE CADENCE", "header"), ("", "header"),
                    ("", "header"), ("", "header")])
    cadence.append([_CONVENTION])
    cadence.append([""])
    cadence.append([("Month", "header"), ("Gross revenue ($)", "header"),
                    ("Contractual adj. ($)", "header"),
                    ("Net revenue ($)", "header")])
    base = 2_400_000
    for i in range(12):
        row_n = 5 + i
        cadence.append([f"M-{12 - i}",
                        (base + i * 35_000, "input_money"),
                        (-(int((base + i * 35_000) * 0.42)), "input_money"),
                        (F(f"B{row_n}+C{row_n}"), "money2")])
    cadence.append([("TTM total", "label"),
                    (F("SUM(B5:B16)"), "money2"),
                    (F("SUM(C5:C16)"), "money2"),
                    (F("SUM(D5:D16)"), "money2")])
    cadence.append(["Net realization %", "", "", (F("D17/B17"), "pct")])
    return [
        Sheet("EBITDA Walk", walk, col_widths=[40, 16, 16, 40]),
        Sheet("Revenue Cadence", cadence, col_widths=[12, 20, 22, 18]),
    ]


# ------------------------------------------------- 3) NWC peg analysis

def _working_capital() -> List[Sheet]:
    """Monthly NWC build with a trailing-average peg and DSO/DPO reads."""
    r: List[list] = []
    r.append([("NET WORKING CAPITAL PEG", "header")] + [("", "header")] * 7)
    r.append([_CONVENTION])
    r.append([""])
    r.append([("Month", "header"), ("AR ($)", "header"),
              ("Prepaids ($)", "header"), ("Other CA ($)", "header"),
              ("AP ($)", "header"), ("Accrued ($)", "header"),
              ("NWC ($)", "header"), ("Net revenue ($)", "header")])
    seeds = [
        (5_100_000, 320_000, 140_000, 1_650_000, 980_000, 2_350_000),
        (5_240_000, 310_000, 150_000, 1_700_000, 1_010_000, 2_380_000),
        (5_060_000, 330_000, 140_000, 1_620_000, 960_000, 2_410_000),
        (5_320_000, 325_000, 145_000, 1_690_000, 990_000, 2_440_000),
        (5_450_000, 318_000, 150_000, 1_740_000, 1_020_000, 2_460_000),
        (5_380_000, 335_000, 148_000, 1_710_000, 1_005_000, 2_480_000),
        (5_510_000, 322_000, 152_000, 1_760_000, 1_030_000, 2_500_000),
        (5_620_000, 328_000, 155_000, 1_790_000, 1_045_000, 2_530_000),
        (5_540_000, 340_000, 150_000, 1_770_000, 1_025_000, 2_550_000),
        (5_700_000, 332_000, 158_000, 1_820_000, 1_060_000, 2_580_000),
        (5_810_000, 338_000, 160_000, 1_850_000, 1_075_000, 2_600_000),
        (5_760_000, 345_000, 162_000, 1_830_000, 1_065_000, 2_620_000),
    ]
    for i, (ar, pre, oca, ap, acc, rev) in enumerate(seeds):
        n = 5 + i
        r.append([f"M-{12 - i}", (ar, "input_money"), (pre, "input_money"),
                  (oca, "input_money"), (ap, "input_money"),
                  (acc, "input_money"),
                  (F(f"B{n}+C{n}+D{n}-E{n}-F{n}"), "money2"),
                  (rev, "input_money")])
    r.append([""])
    r.append([("PEG & DIAGNOSTICS", "label")])                              # row 18
    r.append(["TTM average NWC (the peg)", (F("AVERAGE(G5:G16)"), "money2")])
    r.append(["6-month average NWC", (F("AVERAGE(G11:G16)"), "money2")])
    r.append(["3-month average NWC", (F("AVERAGE(G14:G16)"), "money2")])
    r.append(["Latest month vs peg (excess / deficit)",
              (F("G16-B19"), "money2")])
    r.append(["Implied DSO (latest month, 30-day)",
              (F("B16/H16*30"), "num2")])
    r.append(["Implied DPO (latest month, 30-day)",
              (F("E16/H16*30"), "num2")])
    r.append(["NWC as % of TTM revenue",
              (F("B19/SUM(H5:H16)"), "pct")])
    return [Sheet("NWC Peg", r,
                  col_widths=[36, 14, 13, 13, 13, 13, 14, 16])]


# --------------------------------------------- 4) 13-week cash flow

def _thirteen_week_cash() -> List[Sheet]:
    """Direct-method weekly cash forecast — the lender-ask workbook."""
    ncols = 14  # label + 13 weeks
    r: List[list] = []
    r.append([("13-WEEK CASH FLOW FORECAST", "header")]
             + [("", "header")] * (ncols - 1))
    r.append([_CONVENTION])
    r.append([""])
    header = [("Line item", "header")]
    for w in range(1, 14):
        header.append((f"Wk {w}", "header"))
    r.append(header)                                                        # row 4

    def _input_row(label: str, base: int, step: int) -> list:
        return [label] + [(base + i * step, "input_money") for i in range(13)]

    r.append([("RECEIPTS", "label")])                                       # row 5
    r.append(_input_row("Patient / customer collections", 410_000, 2_500))  # row 6
    r.append(_input_row("Payer remittances", 760_000, 4_000))               # row 7
    r.append(_input_row("Other receipts", 25_000, 0))                       # row 8
    total_receipts = ["Total receipts"]
    for c in range(13):
        col = chr(ord("B") + c)
        total_receipts.append((F(f"SUM({col}6:{col}8)"), "money2"))
    r.append(total_receipts)                                                # row 9
    r.append([("DISBURSEMENTS", "label")])                                  # row 10
    r.append(_input_row("Payroll & benefits", 520_000, 0))                  # row 11
    r.append(_input_row("Supplies / medical costs", 240_000, 1_500))        # row 12
    r.append(_input_row("Rent & occupancy", 85_000, 0))                     # row 13
    r.append(_input_row("Debt service", 110_000, 0))                        # row 14
    r.append(_input_row("Other operating", 95_000, 500))                    # row 15
    total_disb = ["Total disbursements"]
    for c in range(13):
        col = chr(ord("B") + c)
        total_disb.append((F(f"SUM({col}11:{col}15)"), "money2"))
    r.append(total_disb)                                                    # row 16
    r.append([""])
    net = ["Net cash flow"]
    for c in range(13):
        col = chr(ord("B") + c)
        net.append((F(f"{col}9-{col}16"), "money2"))
    r.append(net)                                                           # row 18
    begin = ["Cash, beginning", (1_500_000, "input_money")]
    for c in range(1, 13):
        col = chr(ord("B") + c - 1)
        begin.append((F(f"{col}20"), "money2"))
    r.append(begin)                                                         # row 19
    end = ["Cash, ending"]
    for c in range(13):
        col = chr(ord("B") + c)
        end.append((F(f"{col}18+{col}19"), "money2"))
    r.append(end)                                                           # row 20
    r.append([""])
    r.append(["Minimum liquidity covenant", (750_000, "input_money")])      # row 22
    headroom = ["Headroom vs covenant"]
    for c in range(13):
        col = chr(ord("B") + c)
        headroom.append((F(f"{col}20-$B$22"), "money2"))
    r.append(headroom)                                                      # row 23
    return [Sheet("13-Week Cash", r,
                  col_widths=[30] + [12.5] * 13)]


# ------------------------------------------- 5) CDD market model

def _cdd_market_model() -> List[Sheet]:
    """TAM→SAM→SOM build plus a competitor share grid — the two
    exhibits every commercial-diligence readout opens with."""
    size: List[list] = []
    size.append([("MARKET SIZING — TAM / SAM / SOM", "header"),
                 ("", "header"), ("", "header"), ("", "header")])
    size.append([_CONVENTION])
    size.append([""])
    size.append([("Driver", "header"), ("Value", "header"),
                 ("Unit", "header"), ("Source", "header")])
    size.append(["Addressable population / accounts",
                 (1_200_000, "input_num"), "units",
                 ("Cite source", "input")])
    size.append(["Annual utilization per unit",
                 (2.40, "input_num"), "events / unit / yr",
                 ("Cite source", "input")])
    size.append(["Average realized price per event",
                 (310.00, "input_money"), "$ / event",
                 ("Cite source", "input")])
    size.append([("TAM ($/yr)", "label"), (F("B5*B6*B7"), "money2")])       # row 8
    size.append(["Serviceable filter (geography / payer / acuity)",
                 (0.45, "input_pct")])                                      # row 9
    size.append([("SAM ($/yr)", "label"), (F("B8*B9"), "money2")])          # row 10
    size.append(["Realistic obtainable share at maturity",
                 (0.12, "input_pct")])                                      # row 11
    size.append([("SOM ($/yr)", "label"), (F("B10*B11"), "money2")])        # row 12
    size.append([""])
    size.append([("5-YEAR MARKET PROJECTION", "label")])                    # row 14
    size.append([("Year", "header"), ("TAM ($)", "header"),
                 ("Market growth %", "header"), ("Target share %", "header"),
                 ("Target revenue ($)", "header")])                         # row 15
    for i in range(5):
        n = 16 + i
        tam = F("B8") if i == 0 else F(f"B{n - 1}*(1+C{n})")
        size.append([f"Yr {i + 1}", (tam, "money2"),
                     (0.05, "input_pct"),
                     (round(0.02 + 0.02 * i, 2), "input_pct"),
                     (F(f"B{n}*$B$9*D{n}"), "money2")])

    comp: List[list] = []
    comp.append([("COMPETITOR SHARE GRID", "header"), ("", "header"),
                 ("", "header"), ("", "header"), ("", "header"),
                 ("", "header")])
    comp.append([_CONVENTION])
    comp.append([""])
    comp.append([("Competitor", "header"), ("Est. revenue ($)", "header"),
                 ("Share of SAM %", "header"), ("3-yr growth %", "header"),
                 ("Relative price (1.00 = market)", "header"),
                 ("Right to win / notes", "header")])
    players = [
        ("Target company", 38_000_000, 0.09),
        ("Competitor A (national)", 95_000_000, 0.21),
        ("Competitor B (regional)", 52_000_000, 0.12),
        ("Competitor C (regional)", 31_000_000, 0.06),
        ("Long tail / independents", 0, 0.0),
    ]
    for i, (name, rev, growth) in enumerate(players):
        n = 5 + i
        if name.startswith("Long tail"):
            comp.append([name,
                         (F("'Market Sizing'!B10-SUM(B5:B8)"), "money2"),
                         (F(f"B{n}/'Market Sizing'!B10"), "pct"),
                         (0.02, "input_pct"), (0.90, "input_num"),
                         ("Fragmented remainder", "input")])
        else:
            comp.append([name, (rev, "input_money"),
                         (F(f"B{n}/'Market Sizing'!B10"), "pct"),
                         (growth, "input_pct"), (1.00, "input_num"),
                         ("Notes", "input")])
    comp.append([("Total (should ≈ SAM)", "label"),
                 (F("SUM(B5:B9)"), "money2"),
                 (F("SUM(C5:C9)"), "pct")])
    return [
        Sheet("Market Sizing", size, col_widths=[44, 16, 18, 30]),
        Sheet("Competitors", comp, col_widths=[30, 18, 16, 14, 24, 36]),
    ]


# ------------------------------- 6) Payer-mix rate sensitivity

def _payer_mix_sensitivity() -> List[Sheet]:
    """Revenue/EBITDA torque from payer-mix shift and rate changes —
    the healthcare-services question every IC asks first."""
    r: List[list] = []
    r.append([("PAYER MIX × RATE SENSITIVITY", "header"), ("", "header"),
              ("", "header"), ("", "header"), ("", "header")])
    r.append([_CONVENTION])
    r.append([""])
    r.append([("Payer", "header"), ("Volume mix %", "header"),
              ("Net rate per unit ($)", "header"),
              ("Rate change %", "header"),
              ("Revenue per 1,000 units ($)", "header")])                   # row 4
    payers = [
        ("Commercial", 0.38, 245.00, 0.03),
        ("Medicare", 0.31, 168.00, 0.012),
        ("Medicare Advantage", 0.14, 159.00, 0.01),
        ("Medicaid / managed Medicaid", 0.12, 118.00, 0.0),
        ("Self-pay / other", 0.05, 62.00, 0.0),
    ]
    for i, (name, mix, rate, chg) in enumerate(payers):
        n = 5 + i
        r.append([name, (mix, "input_pct"), (rate, "input_money"),
                  (chg, "input_pct"),
                  (F(f"B{n}*1000*C{n}*(1+D{n})"), "money2")])
    r.append([("Blended (per 1,000 units)", "label"),
              (F("SUM(B5:B9)"), "pct"), (F("E10/1000/B10"), "money2"),
              "", (F("SUM(E5:E9)"), "money2")])                             # row 10
    r.append([""])
    r.append([("VOLUME & FLOW-THROUGH", "label")])                          # row 12
    r.append(["Annual volume (units)", (185_000, "input_num")])             # B13
    r.append(["Baseline net revenue ($)",
              (F("SUMPRODUCT(B5:B9,C5:C9)*B13"), "money2")])                # B14
    r.append(["Scenario net revenue ($)", (F("E10/1000*B13"), "money2")])   # B15
    r.append(["Revenue delta ($)", (F("B15-B14"), "money2")])               # B16
    r.append(["Variable-cost flow-through %", (0.85, "input_pct")])         # B17
    r.append(["EBITDA impact ($)", (F("B16*B17"), "money2")])               # B18
    r.append(["Baseline EBITDA ($)", (4_800_000, "input_money")])           # B19
    r.append(["EBITDA impact %", (F("B18/B19"), "pct")])                    # B20
    r.append([""])
    r.append([("MIX-SHIFT STRESS (commercial → MA migration)", "label")])   # row 22
    r.append(["Commercial points migrating to MA", (0.03, "input_pct")])    # B23
    r.append(["Revenue impact of migration ($)",
              (F("B23*B13*1000/1000*(C7-C5)"), "money2")])                  # B24
    r.append(["EBITDA impact of migration ($)",
              (F("B24*B17"), "money2")])                                    # B25
    return [Sheet("Payer Sensitivity", r,
                  col_widths=[40, 16, 20, 14, 24])]


# ------------------------------------------- 7) Cohort retention / NRR

def _cohort_retention() -> List[Sheet]:
    """Revenue cohort triangle with GRR/NRR — the recurring-revenue
    quality exhibit for HCIT / services CDD."""
    r: List[list] = []
    r.append([("REVENUE COHORT RETENTION", "header"), ("", "header"),
              ("", "header"), ("", "header"), ("", "header"), ("", "header")])
    r.append([_CONVENTION])
    r.append([""])
    r.append([("Cohort (start yr)", "header"), ("Yr 1 rev ($)", "header"),
              ("Yr 2 rev ($)", "header"), ("Yr 3 rev ($)", "header"),
              ("Yr 4 rev ($)", "header"), ("Yr 5 rev ($)", "header")])      # row 4
    cohorts = [
        ("2021 cohort", [4_200_000, 4_350_000, 4_280_000, 4_400_000, 4_510_000]),
        ("2022 cohort", [3_600_000, 3_720_000, 3_810_000, 3_940_000, None]),
        ("2023 cohort", [5_100_000, 5_240_000, 5_390_000, None, None]),
        ("2024 cohort", [4_800_000, 4_980_000, None, None, None]),
        ("2025 cohort", [6_200_000, None, None, None, None]),
    ]
    for name, vals in cohorts:
        row: list = [name]
        for v in vals:
            row.append((v, "input_money") if v is not None else "")
        r.append(row)
    r.append([""])
    r.append([("RETENTION READS", "label")])                                # row 11
    r.append(["2021 cohort NRR (Yr1→Yr5 CAGR)",
              (F("(F5/B5)^(1/4)-1"), "pct")])
    r.append(["Yr1→Yr2 NRR, all cohorts with data",
              (F("(C5+C6+C7+C8)/(B5+B6+B7+B8)"), "pct")])
    r.append(["Latest-year revenue, retained cohorts ($)",
              (F("F5+E6+D7+C8+B9"), "money2")])
    r.append(["Total Yr-1 revenue, all cohorts ($)",
              (F("SUM(B5:B9)"), "money2")])
    r.append([""])
    r.append([("Gross churn assumption for case-building", "label")])
    r.append(["Annual gross revenue churn %", (0.07, "input_pct")])         # B18
    r.append(["Expansion % of retained base", (0.10, "input_pct")])         # B19
    r.append(["Implied NRR", (F("(1-B18)*(1+B19)"), "pct")])                # B20
    return [Sheet("Cohort Triangle", r,
                  col_widths=[34, 15, 15, 15, 15, 15])]


# ------------------------------------------- 8) Win/Loss tracker

def _win_loss_log() -> List[Sheet]:
    """Editable opportunity log + a summary tab that recomputes win
    rates and loss-reason mix via COUNTIFS as rows are added — the
    workbook version of /win-loss, pointed at the target's own CRM
    export instead of the curated demo log."""
    log: List[list] = []
    log.append([("WIN/LOSS OPPORTUNITY LOG", "header")] + [("", "header")] * 5)
    log.append([_CONVENTION + " Add rows; the Summary tab recomputes."])
    log.append([""])
    log.append([("Date", "header"), ("Segment", "header"),
                ("Competitor", "header"), ("Outcome (WON/LOST)", "header"),
                ("Deal value ($)", "header"), ("Loss reason", "header")])
    seed = [
        ("2026-01-12", "Payer contracts", "Competitor A", "WON", 420_000, ""),
        ("2026-01-28", "Employer direct", "Competitor B", "LOST", 350_000,
         "PRICE"),
        ("2026-02-09", "Referral flow", "Competitor A", "WON", 180_000, ""),
        ("2026-02-21", "Payer contracts", "Competitor C", "LOST", 510_000,
         "RELATIONSHIP"),
        ("2026-03-05", "Employer direct", "Competitor A", "LOST", 270_000,
         "PRICE"),
        ("2026-03-18", "Referral flow", "Competitor B", "WON", 220_000, ""),
        ("2026-04-02", "Payer contracts", "Competitor A", "WON", 640_000, ""),
        ("2026-04-19", "Employer direct", "Competitor C", "WON", 310_000, ""),
        ("2026-05-06", "Referral flow", "Competitor B", "LOST", 150_000,
         "CAPABILITY"),
        ("2026-05-22", "Payer contracts", "Competitor B", "WON", 480_000, ""),
    ]
    for d, seg, comp, outcome, value, reason in seed:
        log.append([(d, "input"), (seg, "input"), (comp, "input"),
                    (outcome, "input"), (value, "input_money"),
                    (reason, "input")])
    # Spare blank input rows so adding opportunity #11 needs no
    # formula edits — the summary ranges already cover to row 60.
    for _ in range(10):
        log.append([("", "input"), ("", "input"), ("", "input"),
                    ("", "input"), ("", "input_money"), ("", "input")])

    rng = "'Opportunity Log'!$C$5:$C$60"
    out = "'Opportunity Log'!$D$5:$D$60"
    why = "'Opportunity Log'!$F$5:$F$60"
    summ: List[list] = []
    summ.append([("WIN/LOSS SUMMARY (live — recomputes from the log)",
                  "header")] + [("", "header")] * 3)
    summ.append([""])
    summ.append([("Competitor", "header"), ("Contested", "header"),
                 ("Wins", "header"), ("Win rate", "header")])
    for i, comp in enumerate(("Competitor A", "Competitor B",
                              "Competitor C")):
        n = 4 + i
        summ.append([(comp, "input"),
                     (F(f"COUNTIF({rng},A{n})"), "num"),
                     (F(f'COUNTIFS({rng},A{n},{out},"WON")'), "num"),
                     (F(f"IF(B{n}=0,0,C{n}/B{n})"), "pct")])
    summ.append([("Overall", "label"),
                 (F('COUNTIF(\'Opportunity Log\'!$D$5:$D$60,"WON")'
                    '+COUNTIF(\'Opportunity Log\'!$D$5:$D$60,"LOST")'),
                  "num"),
                 (F('COUNTIF(\'Opportunity Log\'!$D$5:$D$60,"WON")'), "num"),
                 (F("IF(B7=0,0,C7/B7)"), "pct")])
    summ.append([""])
    summ.append([("LOSS-REASON MIX", "label")])                       # row 9
    summ.append([("Reason", "header"), ("Losses", "header"),
                 ("Share of losses", "header")])                      # row 10
    for i, reason in enumerate(("PRICE", "CAPABILITY", "RELATIONSHIP",
                                "GEOGRAPHY", "TIMING")):
        n = 11 + i
        summ.append([reason,
                     (F(f'COUNTIFS({why},A{n},{out},"LOST")'), "num"),
                     (F(f"IF(SUM(B$11:B$15)=0,0,B{n}/SUM(B$11:B$15))"),
                      "pct")])
    return [
        Sheet("Opportunity Log", log,
              col_widths=[12, 20, 16, 18, 14, 16]),
        Sheet("Summary", summ, col_widths=[24, 12, 10, 12]),
    ]


# ------------------------------------------- 9) KPC survey scorer

def _kpc_survey() -> List[Sheet]:
    """Key-purchase-criteria gap matrix with live classification and a
    weighted competitive-position score — the workbook a VoC vendor
    panel drops into (the /voc-survey math, editable)."""
    r: List[list] = []
    r.append([("KPC SURVEY SCORER", "header")] + [("", "header")] * 6)
    r.append([_CONVENTION])
    r.append(["Differentiator: importance ≥ 3.5 AND gap ≥ +0.3. "
              "Vulnerability: importance ≥ 3.5 AND gap ≤ -0.3."])
    r.append([""])
    r.append([("Purchase criterion", "header"), ("Importance /5", "header"),
              ("Target /10", "header"), ("Best comp /10", "header"),
              ("Gap", "header"), ("Weighted gap", "header"),
              ("Classification", "header")])                          # row 5
    seed = [
        ("Access / responsiveness", 4.6, 8.2, 7.0),
        ("Clinical quality reputation", 4.8, 8.0, 8.1),
        ("Price / rates", 3.9, 6.3, 7.2),
        ("Coverage / footprint", 3.6, 7.1, 7.9),
        ("Digital experience", 3.2, 6.9, 6.4),
        ("Reporting & transparency", 4.0, 6.8, 6.2),
    ]
    first = 6
    for i, (crit, imp, tgt, comp) in enumerate(seed):
        n = first + i
        r.append([(crit, "input"), (imp, "input_num"), (tgt, "input_num"),
                  (comp, "input_num"),
                  (F(f"C{n}-D{n}"), "num2"),
                  (F(f"B{n}*E{n}"), "num2"),
                  (F(f'IF(AND(B{n}>=3.5,E{n}>=0.3),"DIFFERENTIATOR",'
                     f'IF(AND(B{n}>=3.5,E{n}<=-0.3),"VULNERABILITY",'
                     f'"TABLE STAKES"))'), "text")])
    last = first + len(seed) - 1
    r.append([""])
    r.append([("Weighted position score (gap pts, importance-weighted)",
               "label"),
              (F(f"SUMPRODUCT(B{first}:B{last},E{first}:E{last})"
                 f"/SUM(B{first}:B{last})"), "num2")])
    r.append([("Differentiators", "label"),
              (F(f'COUNTIF(G{first}:G{last},"DIFFERENTIATOR")'), "num")])
    r.append([("Vulnerabilities", "label"),
              (F(f'COUNTIF(G{first}:G{last},"VULNERABILITY")'), "num")])
    return [Sheet("KPC Matrix", r,
                  col_widths=[34, 13, 11, 13, 9, 13, 17])]


TEMPLATES: List[TemplateSpec] = [
    TemplateSpec(
        slug="quick-lbo",
        title="Quick LBO Model",
        category="Deal Math",
        description=("Screen-stage LBO: entry, 5-year operating case, "
                     "100% cash-sweep debt schedule, MOIC / IRR — one tab, "
                     "answers in under a minute."),
        sheets=["Quick LBO"],
        builder=_lbo_model,
    ),
    TemplateSpec(
        slug="qoe-databook",
        title="QoE Adjusted-EBITDA Databook",
        category="QoE & Accounting",
        description=("Reported→Adjusted EBITDA walk with addback lines and "
                     "evidence column, plus a TTM revenue-cadence tab with "
                     "net-realization read."),
        sheets=["EBITDA Walk", "Revenue Cadence"],
        builder=_qoe_databook,
    ),
    TemplateSpec(
        slug="nwc-peg",
        title="Working-Capital Peg Analysis",
        category="QoE & Accounting",
        description=("12-month NWC build (AR / prepaids / AP / accrued) "
                     "with TTM / 6-mo / 3-mo peg candidates, DSO / DPO, "
                     "and latest-month excess-or-deficit vs peg."),
        sheets=["NWC Peg"],
        builder=_working_capital,
    ),
    TemplateSpec(
        slug="13-week-cash",
        title="13-Week Cash Flow Forecast",
        category="Deal Math",
        description=("Direct-method weekly receipts / disbursements grid "
                     "with rolling cash balance and covenant-headroom row — "
                     "the lender ask, ready to populate."),
        sheets=["13-Week Cash"],
        builder=_thirteen_week_cash,
    ),
    TemplateSpec(
        slug="cdd-market-model",
        title="CDD Market Model (TAM / SAM / SOM)",
        category="CDD & Market",
        description=("Driver-tree market sizing with sourced inputs, 5-year "
                     "projection, and a competitor share grid that "
                     "reconciles back to SAM."),
        sheets=["Market Sizing", "Competitors"],
        builder=_cdd_market_model,
    ),
    TemplateSpec(
        slug="payer-sensitivity",
        title="Payer-Mix × Rate Sensitivity",
        category="CDD & Market",
        description=("Blended-rate build across commercial / Medicare / MA / "
                     "Medicaid with rate-change and mix-migration stress "
                     "flowing through to EBITDA."),
        sheets=["Payer Sensitivity"],
        builder=_payer_mix_sensitivity,
    ),
    TemplateSpec(
        slug="cohort-retention",
        title="Revenue Cohort & NRR Triangle",
        category="CDD & Market",
        description=("Cohort revenue triangle with GRR / NRR reads and a "
                     "churn-expansion bridge — the recurring-revenue quality "
                     "exhibit for HCIT and services deals."),
        sheets=["Cohort Triangle"],
        builder=_cohort_retention,
    ),
    TemplateSpec(
        slug="win-loss-log",
        title="Win/Loss Opportunity Tracker",
        category="CDD & Market",
        description=("Editable opportunity log with a live summary tab — "
                     "win rate by competitor and loss-reason mix recompute "
                     "via COUNTIFS as rows are added."),
        sheets=["Opportunity Log", "Summary"],
        builder=_win_loss_log,
    ),
    TemplateSpec(
        slug="kpc-survey",
        title="KPC Survey Scorer",
        category="CDD & Market",
        description=("Key-purchase-criteria matrix with live gap, "
                     "importance-weighted position score, and automatic "
                     "differentiator / vulnerability classification."),
        sheets=["KPC Matrix"],
        builder=_kpc_survey,
    ),
]

_BY_SLUG: Dict[str, TemplateSpec] = {t.slug: t for t in TEMPLATES}


def get_template(slug: str) -> Optional[TemplateSpec]:
    return _BY_SLUG.get(slug)


def build_template_xlsx(slug: str) -> Optional[bytes]:
    """Workbook bytes for a registry slug, or None for unknown slugs.

    Builders run per-request (no caching): each is pure construction of
    a few hundred cells, well under a millisecond, and per-request build
    keeps the download trivially consistent with the registry.
    """
    spec = _BY_SLUG.get(slug)
    if spec is None:
        return None
    return write_xlsx(spec.builder())
