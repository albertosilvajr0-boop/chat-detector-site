"""
BCAD Unequal-Appraisal Comp Engine
===================================
Legal basis: Texas Tax Code §41.43(b)(3) — appraised value of subject property
must be equal to or less than the median appraised value of a reasonable number
of comparable properties, appropriately adjusted.

Geography tiers (tightest -> loosest):
  1. Same CB (City Block) + Same BLK         -- sub-street-block
  2. Same CB                                 -- neighborhood
  3. Same ZIP                                -- fallback only

Value-band filter excludes wildly different property types from comp pool:
  Comps must be within [0.40x, 2.50x] of subject's appraised value.

Returns target value = median(comps), reduction = subject - target.
"""

import sqlite3
from dataclasses import dataclass, asdict
from statistics import median
from typing import Optional

MIN_COMPS = 5
DISPLAY_COMPS = 10  # how many to show in the evidence packet

# Two-tier value bands. CB+BLK gets a slightly wider band since geography is tight;
# CB-level uses a narrow band to avoid pulling in apples-to-oranges from large CBs.
VAL_BAND_LO_CBBLK = 0.65
VAL_BAND_HI_CBBLK = 1.55
VAL_BAND_LO_CB    = 0.75
VAL_BAND_HI_CB    = 1.35

# Cap the reduction we'll publicly claim. If the math says more than this, the
# property likely needs a human (different sqft, condition, etc.) — don't oversell.
MAX_CLAIMABLE_PCT = 25.0


@dataclass
class Parcel:
    PropertyId: int
    GeoId: str
    SitusAddress: str
    OwnerFullName: str
    ZipCode: int
    CB: Optional[str]
    BLK: Optional[str]
    MarketValue: float
    AppraisedValue: float
    AssessedValue: float
    LegalDescription: str
    HasHomestead: bool


@dataclass
class CompAnalysis:
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


# Effective property-tax rate in Bexar County is ~2.03% per recent KENS/BCAD data.
# Used to translate value reduction into annual savings.
BEXAR_EFFECTIVE_TAX_RATE = 0.0203


def find_parcel_by_id(con: sqlite3.Connection, property_id: int) -> Optional[Parcel]:
    cur = con.cursor()
    cur.execute("""
        SELECT PropertyId, GeoId, SitusAddress, OwnerFullName, ZipCode, CB, BLK,
               MarketValue, AppraisedValue, AssessedValue, LegalDescription, HasHomestead
        FROM parcels WHERE PropertyId = ?
    """, (property_id,))
    r = cur.fetchone()
    if not r: return None
    return Parcel(*r)


def search_parcels_by_address(con: sqlite3.Connection, query: str, limit: int = 10) -> list:
    """Address-search using FTS5. Returns list of dicts."""
    import re
    # Build a forgiving FTS query: tokens AND'd, prefix-matched.
    tokens = [t for t in re.split(r'\W+', query.upper()) if t]
    if not tokens: return []
    fts_q = ' '.join(f'{t}*' for t in tokens)
    cur = con.cursor()
    try:
        cur.execute("""
            SELECT p.PropertyId, p.SitusAddress, p.OwnerFullName, p.AppraisedValue, p.ZipCode
            FROM addr_fts f
            JOIN parcels p ON p.rowid = f.rowid
            WHERE addr_fts MATCH ?
            ORDER BY bm25(addr_fts) LIMIT ?
        """, (fts_q, limit))
    except sqlite3.OperationalError:
        return []
    return [
        dict(property_id=r[0], situs_address=r[1], owner=r[2],
             appraised_value=r[3], zip_code=r[4])
        for r in cur.fetchall()
    ]


def _fetch_comps_by_tier(con, subject: Parcel) -> tuple:
    """Try CB+BLK with a wider band, then CB with a tight band. No ZIP fallback —
    a property without enough sub-neighborhood comps doesn't have a strong unequal-
    appraisal case anyway."""
    cur = con.cursor()

    if subject.CB and subject.BLK:
        lo = subject.AppraisedValue * VAL_BAND_LO_CBBLK
        hi = subject.AppraisedValue * VAL_BAND_HI_CBBLK
        cur.execute("""
            SELECT PropertyId, SitusAddress, AppraisedValue, MarketValue,
                   AssessedValue, LegalDescription, HasHomestead
            FROM parcels
            WHERE CB = ? AND BLK = ? AND PropertyId != ?
              AND AppraisedValue BETWEEN ? AND ?
        """, (subject.CB, subject.BLK, subject.PropertyId, lo, hi))
        rows = cur.fetchall()
        if len(rows) >= MIN_COMPS:
            return rows, 'CB+BLK'

    if subject.CB:
        lo = subject.AppraisedValue * VAL_BAND_LO_CB
        hi = subject.AppraisedValue * VAL_BAND_HI_CB
        cur.execute("""
            SELECT PropertyId, SitusAddress, AppraisedValue, MarketValue,
                   AssessedValue, LegalDescription, HasHomestead
            FROM parcels
            WHERE CB = ? AND PropertyId != ?
              AND AppraisedValue BETWEEN ? AND ?
        """, (subject.CB, subject.PropertyId, lo, hi))
        rows = cur.fetchall()
        if len(rows) >= MIN_COMPS:
            return rows, 'CB'

    return [], 'none'


def analyze(con: sqlite3.Connection, property_id: int) -> CompAnalysis:
    subject = find_parcel_by_id(con, property_id)
    if not subject:
        return CompAnalysis(subject={}, comps=[], comp_count_total=0,
                            geography_tier_used='', median_appraised=None,
                            median_market=None, target_value=None,
                            estimated_reduction=None, estimated_pct_reduction=None,
                            estimated_annual_tax_savings=None,
                            is_protestable=False, reason='parcel_not_found')

    rows, tier = _fetch_comps_by_tier(con, subject)

    if len(rows) < MIN_COMPS:
        return CompAnalysis(
            subject=asdict(subject), comps=[], comp_count_total=len(rows),
            geography_tier_used=tier, median_appraised=None,
            median_market=None, target_value=None,
            estimated_reduction=None, estimated_pct_reduction=None,
            estimated_annual_tax_savings=None,
            is_protestable=False,
            reason=f'insufficient_comps ({len(rows)} found, need {MIN_COMPS})')

    comp_appraised = [r[2] for r in rows]
    comp_market    = [r[3] for r in rows if r[3] is not None]

    med_app = median(comp_appraised)
    med_mkt = median(comp_market) if comp_market else None

    target = med_app
    reduction = subject.AppraisedValue - target
    pct = reduction / subject.AppraisedValue * 100 if subject.AppraisedValue else 0
    tax_savings = reduction * BEXAR_EFFECTIVE_TAX_RATE if reduction > 0 else 0

    # Pick the DISPLAY_COMPS lowest-value comps for the evidence packet —
    # this is what protest firms do; it's not cherry-picking, it's emphasis
    # of the favorable end of the comp distribution.
    rows_sorted = sorted(rows, key=lambda r: r[2])[:DISPLAY_COMPS]
    comps = [dict(
        property_id=r[0], situs_address=r[1], appraised_value=r[2],
        market_value=r[3], assessed_value=r[4],
        legal_description=r[5], has_homestead=bool(r[6]),
    ) for r in rows_sorted]

    is_protestable = reduction > 0 and pct >= 2.0  # require ≥2% to be worth filing

    if is_protestable:
        if pct > MAX_CLAIMABLE_PCT:
            # Walk back the claim. The math says big reduction, but our data is
            # too coarse to credibly assert that — defer to human review.
            reason = 'large_reduction_needs_human_review'
            target = subject.AppraisedValue * (1 - MAX_CLAIMABLE_PCT/100)
            reduction = subject.AppraisedValue - target
            pct = MAX_CLAIMABLE_PCT
            tax_savings = reduction * BEXAR_EFFECTIVE_TAX_RATE
        else:
            reason = 'overassessed_vs_comps'
    elif reduction <= 0:
        reason = 'not_overassessed'
    else:
        reason = 'reduction_too_small'

    return CompAnalysis(
        subject=asdict(subject), comps=comps, comp_count_total=len(rows),
        geography_tier_used=tier, median_appraised=med_app, median_market=med_mkt,
        target_value=target, estimated_reduction=reduction,
        estimated_pct_reduction=pct, estimated_annual_tax_savings=tax_savings,
        is_protestable=is_protestable, reason=reason,
    )
