"""
County-aware comparable appraisal engine.

Bexar uses the tightest BCAD geography available: same City Block + Block, then
same City Block. Arapahoe uses same Neighborhood Code + same residential property
type. Both counties also apply value bands so the comp pool stays reasonably
similar to the subject.
"""

import re
import sqlite3
from dataclasses import asdict, dataclass
from statistics import median
from typing import Optional


MIN_COMPS = 5
DISPLAY_COMPS = 10

VAL_BAND_LO_BEXAR_CBBLK = 0.65
VAL_BAND_HI_BEXAR_CBBLK = 1.55
VAL_BAND_LO_BEXAR_CB = 0.75
VAL_BAND_HI_BEXAR_CB = 1.35

VAL_BAND_LO_ARAPAHOE = 0.70
VAL_BAND_HI_ARAPAHOE = 1.45
ARAPAHOE_MAX_NEAREST_COMPS = 80

MAX_CLAIMABLE_PCT = 25.0
BEXAR_EFFECTIVE_TAX_RATE = 0.0203


COUNTY_INFO = {
    "bexar": {
        "id": "bexar",
        "label": "Bexar County",
        "short_label": "Bexar",
        "assessor_label": "Bexar Central Appraisal District",
        "assessor_short": "BCAD",
        "property_id_label": "BCAD Property ID",
        "appraisal_label": "BCAD Appraised",
        "appeal_label": "protest",
        "deadline": "May 15, 2026",
        "evidence_basis": "Texas Tax Code Section 41.43(b)(3) unequal appraisal",
        "data_source": "2026 BCAD certified appraisal roll",
        "filing_url": "https://bcad.org",
    },
    "arapahoe": {
        "id": "arapahoe",
        "label": "Arapahoe County",
        "short_label": "Arapahoe",
        "assessor_label": "Arapahoe County Assessor",
        "assessor_short": "Arapahoe Assessor",
        "property_id_label": "Arapahoe Parcel ID",
        "appraisal_label": "Assessor Value",
        "appeal_label": "appeal",
        "deadline": "June 8, 2026",
        "evidence_basis": "Colorado real property valuation appeal evidence",
        "data_source": "Arapahoe County appraisal roll",
        "filing_url": "https://www.arapahoeco.gov/assessor",
    },
}


@dataclass
class Parcel:
    County: str
    PropertyId: str
    GeoId: str
    ZipCode: int
    DistanceFromAnchor: Optional[float]
    OwnerFullName: str
    SitusAddress: str
    NormAddr: str
    LegalDescription: str
    NeighborhoodCode: Optional[str]
    Neighborhood: Optional[str]
    PropertyUse: Optional[str]
    PropertyUseGroup: Optional[str]
    MarketValue: Optional[float]
    AppraisedValue: float
    AssessedValue: Optional[float]
    LandValue: Optional[float]
    ImprovementValue: Optional[float]
    Year: int
    GroupCodes: Optional[str]
    CB: Optional[str]
    BLK: Optional[str]
    HasHomestead: bool
    CoordinateX: Optional[float]
    CoordinateY: Optional[float]
    SaleDate: Optional[str]
    SalePrice: Optional[float]


@dataclass
class CompAnalysis:
    county: dict
    subject: dict
    comps: list
    comp_count_total: int
    geography_tier_used: str
    median_appraised: Optional[float]
    median_market: Optional[float]
    target_value: Optional[float]
    estimated_reduction: Optional[float]
    estimated_pct_reduction: Optional[float]
    estimated_annual_tax_savings: Optional[float]
    is_protestable: bool
    reason: str


def valid_county(county: str) -> str:
    key = (county or "bexar").lower()
    if key not in COUNTY_INFO:
        raise ValueError(f"unsupported county: {county}")
    return key


def county_options() -> list[dict]:
    return list(COUNTY_INFO.values())


def find_parcel_by_id(con: sqlite3.Connection, county: str, property_id: str) -> Optional[Parcel]:
    county = valid_county(county)
    cur = con.cursor()
    cur.execute(
        """
        SELECT County, PropertyId, GeoId, ZipCode, DistanceFromAnchor,
               OwnerFullName, SitusAddress, NormAddr, LegalDescription,
               NeighborhoodCode, Neighborhood, PropertyUse, PropertyUseGroup,
               MarketValue, AppraisedValue, AssessedValue, LandValue,
               ImprovementValue, Year, GroupCodes, CB, BLK, HasHomestead,
               CoordinateX, CoordinateY, SaleDate, SalePrice
        FROM parcels
        WHERE County = ? AND PropertyId = ?
        LIMIT 1
        """,
        (county, str(property_id)),
    )
    row = cur.fetchone()
    if not row:
        return None
    data = dict(row)
    data["HasHomestead"] = bool(data.get("HasHomestead"))
    return Parcel(**data)


def search_parcels_by_address(
    con: sqlite3.Connection,
    query: str,
    county: str = "bexar",
    limit: int = 10,
) -> list:
    """Address search using FTS5. Returns list of dicts."""
    county = valid_county(county)
    tokens = [t for t in re.split(r"\W+", query.upper()) if t]
    if not tokens:
        return []
    fts_q = " ".join(f"{t}*" for t in tokens)
    cur = con.cursor()
    try:
        cur.execute(
            """
            SELECT p.PropertyId, p.County, p.SitusAddress, p.OwnerFullName,
                   p.AppraisedValue, p.ZipCode
            FROM addr_fts f
            JOIN parcels p ON p.rowid = f.rowid
            WHERE addr_fts MATCH ? AND p.County = ?
            ORDER BY bm25(addr_fts)
            LIMIT ?
            """,
            (fts_q, county, limit),
        )
    except sqlite3.OperationalError:
        return []

    info = COUNTY_INFO[county]
    return [
        {
            "property_id": r[0],
            "county": r[1],
            "county_label": info["label"],
            "situs_address": r[2],
            "owner": r[3],
            "appraised_value": r[4],
            "zip_code": r[5],
            "assessor_label": info["assessor_short"],
        }
        for r in cur.fetchall()
    ]


def _comp_rows_to_dicts(rows, county: str) -> list[dict]:
    return [
        {
            "property_id": r["PropertyId"],
            "county": county,
            "situs_address": r["SitusAddress"],
            "appraised_value": r["AppraisedValue"],
            "market_value": r["MarketValue"],
            "assessed_value": r["AssessedValue"],
            "legal_description": r["LegalDescription"] or "",
            "neighborhood": r["Neighborhood"] or "",
            "property_use": r["PropertyUse"] or "",
            "has_homestead": bool(r["HasHomestead"]),
        }
        for r in rows
    ]


def _select_comp_rows(con, where_sql: str, params: tuple) -> list:
    cur = con.cursor()
    cur.execute(
        f"""
        SELECT PropertyId, SitusAddress, AppraisedValue, MarketValue,
               AssessedValue, LegalDescription, Neighborhood, PropertyUse,
               HasHomestead
        FROM parcels
        WHERE {where_sql}
        """,
        params,
    )
    return cur.fetchall()


def _fetch_bexar_comps(con: sqlite3.Connection, subject: Parcel) -> tuple[list, str]:
    if subject.CB and subject.BLK:
        lo = subject.AppraisedValue * VAL_BAND_LO_BEXAR_CBBLK
        hi = subject.AppraisedValue * VAL_BAND_HI_BEXAR_CBBLK
        rows = _select_comp_rows(
            con,
            """
            County = 'bexar' AND CB = ? AND BLK = ? AND PropertyId != ?
            AND AppraisedValue BETWEEN ? AND ?
            """,
            (subject.CB, subject.BLK, subject.PropertyId, lo, hi),
        )
        if len(rows) >= MIN_COMPS:
            return rows, "same city block + block"

    if subject.CB:
        lo = subject.AppraisedValue * VAL_BAND_LO_BEXAR_CB
        hi = subject.AppraisedValue * VAL_BAND_HI_BEXAR_CB
        rows = _select_comp_rows(
            con,
            """
            County = 'bexar' AND CB = ? AND PropertyId != ?
            AND AppraisedValue BETWEEN ? AND ?
            """,
            (subject.CB, subject.PropertyId, lo, hi),
        )
        if len(rows) >= MIN_COMPS:
            return rows, "same city block"

    return [], "none"


def _fetch_arapahoe_comps(con: sqlite3.Connection, subject: Parcel) -> tuple[list, str]:
    if not subject.NeighborhoodCode or not subject.PropertyUseGroup:
        return [], "none"

    lo = subject.AppraisedValue * VAL_BAND_LO_ARAPAHOE
    hi = subject.AppraisedValue * VAL_BAND_HI_ARAPAHOE
    cur = con.cursor()
    cur.execute(
        """
        SELECT PropertyId, SitusAddress, AppraisedValue, MarketValue,
               AssessedValue, LegalDescription, Neighborhood, PropertyUse,
               HasHomestead
        FROM parcels
        WHERE County = 'arapahoe'
          AND NeighborhoodCode = ?
          AND PropertyUseGroup = ?
          AND PropertyId != ?
          AND AppraisedValue BETWEEN ? AND ?
        ORDER BY
          ((CoordinateX - ?) * (CoordinateX - ?)) +
          ((CoordinateY - ?) * (CoordinateY - ?))
        LIMIT ?
        """,
        (
            subject.NeighborhoodCode,
            subject.PropertyUseGroup,
            subject.PropertyId,
            lo,
            hi,
            subject.CoordinateX,
            subject.CoordinateX,
            subject.CoordinateY,
            subject.CoordinateY,
            ARAPAHOE_MAX_NEAREST_COMPS,
        ),
    )
    rows = cur.fetchall()
    if len(rows) >= MIN_COMPS:
        return rows, "same neighborhood + property type + nearest parcels"

    return [], "none"


def _fetch_comps_by_tier(con: sqlite3.Connection, subject: Parcel) -> tuple[list, str]:
    if subject.County == "bexar":
        return _fetch_bexar_comps(con, subject)
    if subject.County == "arapahoe":
        return _fetch_arapahoe_comps(con, subject)
    return [], "none"


def _tax_savings(county: str, reduction: float) -> Optional[float]:
    if reduction <= 0:
        return 0
    if county == "bexar":
        return reduction * BEXAR_EFFECTIVE_TAX_RATE
    return None


def _empty_analysis(county: str, reason: str) -> CompAnalysis:
    county = valid_county(county)
    return CompAnalysis(
        county=COUNTY_INFO[county],
        subject={},
        comps=[],
        comp_count_total=0,
        geography_tier_used="",
        median_appraised=None,
        median_market=None,
        target_value=None,
        estimated_reduction=None,
        estimated_pct_reduction=None,
        estimated_annual_tax_savings=None,
        is_protestable=False,
        reason=reason,
    )


def analyze(con: sqlite3.Connection, county: str, property_id: str) -> CompAnalysis:
    county = valid_county(county)
    subject = find_parcel_by_id(con, county, str(property_id))
    if not subject:
        return _empty_analysis(county, "parcel_not_found")

    rows, tier = _fetch_comps_by_tier(con, subject)

    if len(rows) < MIN_COMPS:
        return CompAnalysis(
            county=COUNTY_INFO[county],
            subject=asdict(subject),
            comps=[],
            comp_count_total=len(rows),
            geography_tier_used=tier,
            median_appraised=None,
            median_market=None,
            target_value=None,
            estimated_reduction=None,
            estimated_pct_reduction=None,
            estimated_annual_tax_savings=None,
            is_protestable=False,
            reason=f"insufficient_comps ({len(rows)} found, need {MIN_COMPS})",
        )

    comp_appraised = [r["AppraisedValue"] for r in rows]
    comp_market = [r["MarketValue"] for r in rows if r["MarketValue"] is not None]

    med_app = median(comp_appraised)
    med_mkt = median(comp_market) if comp_market else None

    target = med_app
    reduction = subject.AppraisedValue - target
    pct = reduction / subject.AppraisedValue * 100 if subject.AppraisedValue else 0
    tax_savings = _tax_savings(county, reduction)
    is_protestable = reduction > 0 and pct >= 2.0

    if is_protestable:
        if pct > MAX_CLAIMABLE_PCT:
            reason = "large_reduction_needs_human_review"
            target = subject.AppraisedValue * (1 - MAX_CLAIMABLE_PCT / 100)
            reduction = subject.AppraisedValue - target
            pct = MAX_CLAIMABLE_PCT
            tax_savings = _tax_savings(county, reduction)
            is_protestable = False
        else:
            reason = "overassessed_vs_comps"
    elif reduction <= 0:
        reason = "not_overassessed"
    else:
        reason = "reduction_too_small"

    rows_sorted = sorted(rows, key=lambda r: r["AppraisedValue"])[:DISPLAY_COMPS]
    comps = _comp_rows_to_dicts(rows_sorted, county)

    return CompAnalysis(
        county=COUNTY_INFO[county],
        subject=asdict(subject),
        comps=comps,
        comp_count_total=len(rows),
        geography_tier_used=tier,
        median_appraised=med_app,
        median_market=med_mkt,
        target_value=target,
        estimated_reduction=reduction,
        estimated_pct_reduction=pct,
        estimated_annual_tax_savings=tax_savings,
        is_protestable=is_protestable,
        reason=reason,
    )
