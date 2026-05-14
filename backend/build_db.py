"""
Build the SQLite database from county appraisal CSV exports.

Usage:
    python build_db.py BEXAR.csv OUTPUT.db
    python build_db.py BEXAR.csv ARAPAHOE.csv OUTPUT.db

The output file is still named bcad.db in deploys for compatibility with the
existing Dockerfile, but the schema is county-aware.
"""

import os
import re
import sqlite3
import sys
import time
from bisect import bisect_left, bisect_right

import pandas as pd


COMMON_COLUMNS = [
    "County",
    "PropertyId",
    "GeoId",
    "ZipCode",
    "DistanceFromAnchor",
    "OwnerFullName",
    "NormOwner",
    "SitusAddress",
    "NormAddr",
    "LegalDescription",
    "NeighborhoodCode",
    "Neighborhood",
    "PropertyUse",
    "PropertyUseGroup",
    "MarketValue",
    "AppraisedValue",
    "AssessedValue",
    "LandValue",
    "ImprovementValue",
    "Year",
    "GroupCodes",
    "CB",
    "BLK",
    "HasHomestead",
    "CoordinateX",
    "CoordinateY",
    "SaleDate",
    "SalePrice",
]


ARAPAHOE_ALLOWED_USES = {
    "Single Family",
    "1213 Deed Restricted Single Family Parcels",
    "Residential Condos",
    "Duplex/Triplex",
    "Manufactured Housing",
    "Farm/Ranch Residence",
    "Residential",
}


def parse_legal(ld):
    """Extract (CB, BLK) from BCAD legal description."""
    if pd.isna(ld):
        return (None, None)
    s = str(ld).upper()
    cb = re.search(r"\bN?CB\s+(\d+)", s) or re.search(r"\bNB\s+(\d+)", s)
    blk = re.search(r"\bBLK\s+(\w+)", s)
    return (cb.group(1) if cb else None, blk.group(1) if blk else None)


def norm_addr(value):
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value).upper()).strip()


def clean_text(value):
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def clean_zip(value):
    if pd.isna(value):
        return None
    match = re.search(r"\d{5}", str(value))
    return int(match.group(0)) if match else None


def clean_code(value):
    if pd.isna(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        as_float = float(text)
        if as_float.is_integer():
            return str(int(as_float))
    except ValueError:
        pass
    return text


def has_excl(gc):
    """Codes excluded from the Bexar residential set."""
    if pd.isna(gc):
        return False
    toks = set(t.strip() for t in str(gc).split(","))
    return bool(toks & {"EXPUB", "EXCH", "EXUR", "EX-XV", "EX-XR"})


def has_hs(gc):
    """Detect Bexar homestead-related codes."""
    if pd.isna(gc):
        return False
    toks = set(t.strip() for t in str(gc).split(","))
    if {"HS-AUDIT-OK", "HS", "HS65", "DV100%"} & toks:
        return True
    return any("EXUP" in t for t in toks)


def arapahoe_use_group(puc):
    text = clean_text(puc)
    upper = text.upper()
    if "CONDO" in upper:
        return "Condo"
    if "DUPLEX" in upper or "TRIPLEX" in upper:
        return "Duplex/Triplex"
    if "MANUFACTURED" in upper:
        return "Manufactured Housing"
    if "FARM/RANCH RESIDENCE" in upper:
        return "Farm/Ranch Residence"
    if "SINGLE FAMILY" in upper:
        return "Single Family"
    return text or "Residential"


def build_bexar(csv_path):
    print(f"[Bexar 1/3] Reading {csv_path}...")
    df = pd.read_csv(csv_path, low_memory=False)
    print(f"      {len(df):,} rows loaded")

    print("[Bexar 2/3] Filtering residential parcels...")
    res = df[
        (df["PropertyTypeCode"] == "R (Real)")
        & (df["AppraisedValue"].notna())
        & (df["AppraisedValue"] > 1000)
        & (df["SitusAddress"].notna())
    ].copy()
    res = res[~res["GroupCodes"].apply(has_excl)].copy()
    print(f"      {len(res):,} residential parcels")

    print("[Bexar 3/3] Normalizing columns...")
    parsed = res["LegalDescription"].apply(parse_legal)
    out = pd.DataFrame(index=res.index)
    out["County"] = "bexar"
    out["PropertyId"] = res["PropertyId"].astype("Int64").astype(str)
    out["GeoId"] = res["GeoId"].fillna("").astype(str)
    out["ZipCode"] = pd.to_numeric(res["ZipCode"], errors="coerce").astype("Int64")
    out["DistanceFromAnchor"] = pd.to_numeric(res["DistanceFrom78233"], errors="coerce")
    out["OwnerFullName"] = res["OwnerFullName"].apply(clean_text)
    out["NormOwner"] = res["OwnerFullName"].apply(norm_addr)
    out["SitusAddress"] = res["SitusAddress"].apply(clean_text)
    out["NormAddr"] = res["SitusAddress"].apply(norm_addr)
    out["LegalDescription"] = res["LegalDescription"].apply(clean_text)
    out["NeighborhoodCode"] = None
    out["Neighborhood"] = None
    out["PropertyUse"] = "Residential"
    out["PropertyUseGroup"] = "Residential"
    out["MarketValue"] = pd.to_numeric(res["MarketValue"], errors="coerce")
    out["AppraisedValue"] = pd.to_numeric(res["AppraisedValue"], errors="coerce")
    out["AssessedValue"] = pd.to_numeric(res["AssessedValue"], errors="coerce")
    out["LandValue"] = None
    out["ImprovementValue"] = None
    out["Year"] = pd.to_numeric(res["Year"], errors="coerce").fillna(2026).astype("Int64")
    out["GroupCodes"] = res["GroupCodes"].apply(clean_text)
    out["CB"] = parsed.apply(lambda x: x[0])
    out["BLK"] = parsed.apply(lambda x: x[1])
    out["HasHomestead"] = res["GroupCodes"].apply(has_hs).astype(int)
    out["CoordinateX"] = None
    out["CoordinateY"] = None
    out["SaleDate"] = None
    out["SalePrice"] = None
    return out[COMMON_COLUMNS]


def build_arapahoe(csv_path):
    print(f"[Arapahoe 1/3] Reading {csv_path}...")
    df = pd.read_csv(csv_path, low_memory=False)
    print(f"      {len(df):,} rows loaded")

    print("[Arapahoe 2/3] Filtering residential homeowner parcels...")
    puc = df["PUC"].fillna("").map(clean_text)
    taxable = pd.to_numeric(df["Taxable"], errors="coerce")
    appraised = pd.to_numeric(df["Appr_Value"], errors="coerce")
    res = df[
        puc.isin(ARAPAHOE_ALLOWED_USES)
        & taxable.notna()
        & (taxable > 0)
        & appraised.notna()
        & (appraised > 1000)
        & df["Situs_Address"].notna()
    ].copy()
    res["PUC_Clean"] = puc.loc[res.index]
    print(f"      {len(res):,} residential parcels")

    print("[Arapahoe 3/3] Normalizing columns...")
    city_state_zip = res["Situs_City_State_Zip"].apply(clean_text)
    street = res["Situs_Address"].apply(clean_text)
    display_addr = street.where(city_state_zip.eq(""), street + ", " + city_state_zip)
    norm_search = (street + " " + city_state_zip).apply(norm_addr)

    out = pd.DataFrame(index=res.index)
    out["County"] = "arapahoe"
    out["PropertyId"] = res["PARCEL_ID"].fillna(res["PIN"]).astype(str).map(clean_text)
    out["GeoId"] = res["PIN"].fillna(res["Folio"]).astype(str).map(clean_text)
    out["ZipCode"] = res["Zip"].apply(clean_zip).astype("Int64")
    out["DistanceFromAnchor"] = pd.to_numeric(res["DistanceFrom80112"], errors="coerce")
    out["OwnerFullName"] = res["Owner"].apply(clean_text)
    out["NormOwner"] = res["Owner"].apply(norm_addr)
    out["SitusAddress"] = display_addr
    out["NormAddr"] = norm_search
    out["LegalDescription"] = res["Neighborhood"].apply(clean_text)
    out["NeighborhoodCode"] = res["Neighborhood_Code"].apply(clean_code)
    out["Neighborhood"] = res["Neighborhood"].apply(clean_text)
    out["PropertyUse"] = res["PUC_Clean"]
    out["PropertyUseGroup"] = res["PUC_Clean"].apply(arapahoe_use_group)
    out["MarketValue"] = pd.to_numeric(res["Appr_Value"], errors="coerce")
    out["AppraisedValue"] = pd.to_numeric(res["Appr_Value"], errors="coerce")
    out["AssessedValue"] = pd.to_numeric(res["Assd_Value"], errors="coerce")
    out["LandValue"] = pd.to_numeric(res["Land_Value"], errors="coerce")
    out["ImprovementValue"] = pd.to_numeric(res["Imp_Value"], errors="coerce")
    out["Year"] = 2026
    out["GroupCodes"] = res["PUC_Code"].apply(clean_text)
    out["CB"] = None
    out["BLK"] = None
    out["HasHomestead"] = 0
    out["CoordinateX"] = pd.to_numeric(res["Coordinate_X"], errors="coerce")
    out["CoordinateY"] = pd.to_numeric(res["Coordinate_Y"], errors="coerce")
    out["SaleDate"] = res["Sale_Date"].apply(clean_text)
    out["SalePrice"] = pd.to_numeric(res["Price"], errors="coerce")
    return out[COMMON_COLUMNS]


def write_sqlite(frames, db_path):
    print(f"[DB 1/4] Writing SQLite to {db_path}...")
    if os.path.exists(db_path):
        os.remove(db_path)

    parcels = pd.concat(frames, ignore_index=True)
    parcels = parcels[parcels["PropertyId"].notna() & (parcels["PropertyId"] != "")].copy()
    con = sqlite3.connect(db_path)
    parcels.to_sql("parcels", con, index=False, if_exists="replace")

    cur = con.cursor()
    print("[DB 2/4] Building indexes...")
    cur.execute("CREATE INDEX idx_county_propid ON parcels(County, PropertyId)")
    cur.execute("CREATE INDEX idx_county_zip ON parcels(County, ZipCode)")
    cur.execute("CREATE INDEX idx_county_cb ON parcels(County, CB)")
    cur.execute("CREATE INDEX idx_county_cb_blk ON parcels(County, CB, BLK)")
    cur.execute("CREATE INDEX idx_county_cb_value ON parcels(County, CB, AppraisedValue)")
    cur.execute(
        "CREATE INDEX idx_county_cb_blk_value "
        "ON parcels(County, CB, BLK, AppraisedValue)"
    )
    cur.execute("CREATE INDEX idx_county_value ON parcels(County, AppraisedValue)")
    cur.execute(
        "CREATE INDEX idx_county_neighborhood_use_value "
        "ON parcels(County, NeighborhoodCode, PropertyUseGroup, AppraisedValue)"
    )

    print("[DB 3/4] Building FTS5 address + owner search...")
    cur.execute(
        "CREATE VIRTUAL TABLE parcel_fts USING fts5("
        "NormAddr, NormOwner, content='parcels', content_rowid='rowid'"
        ")"
    )
    cur.execute(
        "INSERT INTO parcel_fts(rowid, NormAddr, NormOwner) "
        "SELECT rowid, NormAddr, NormOwner FROM parcels"
    )
    con.commit()

    print("[DB 4/4] Precomputing protest candidate exports...")
    build_protest_candidates(con, parcels)

    counts = con.execute(
        "SELECT County, COUNT(*) FROM parcels GROUP BY County ORDER BY County"
    ).fetchall()
    candidate_counts = con.execute(
        "SELECT County, COUNT(*) FROM protest_candidates GROUP BY County ORDER BY County"
    ).fetchall()
    con.close()

    size_mb = os.path.getsize(db_path) / 1024 / 1024
    print("\nDone.")
    for county, count in counts:
        print(f"  {county}: {count:,} parcels")
    for county, count in candidate_counts:
        print(f"  {county}: {count:,} protest candidates")
    print(f"  {db_path}: {size_mb:.0f} MB")


def build_protest_candidates(con, parcels):
    """Materialize all parcels where the same comp logic supports a filing."""
    from comp_engine import analyze

    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("DROP TABLE IF EXISTS protest_candidates")
    cur.execute(
        """
        CREATE TABLE protest_candidates (
            County TEXT NOT NULL,
            PropertyId TEXT NOT NULL,
            SitusAddress TEXT NOT NULL,
            OwnerFullName TEXT NOT NULL,
            ZipCode INTEGER,
            AppraisedValue REAL,
            RecommendedValue REAL,
            EstimatedReduction REAL,
            EstimatedPctReduction REAL,
            EstimatedAnnualTaxSavings REAL,
            EstimatedSavingsNote TEXT,
            CompCount INTEGER,
            GeographyTierUsed TEXT,
            Reason TEXT,
            PRIMARY KEY (County, PropertyId)
        )
        """
    )

    insert_sql = """
        INSERT OR IGNORE INTO protest_candidates (
            County, PropertyId, SitusAddress, OwnerFullName, ZipCode,
            AppraisedValue, RecommendedValue, EstimatedReduction,
            EstimatedPctReduction, EstimatedAnnualTaxSavings, EstimatedSavingsNote,
            CompCount, GeographyTierUsed, Reason
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    bexar_rows = build_bexar_candidate_rows(parcels)
    cur.executemany(insert_sql, bexar_rows)
    con.commit()
    total_candidates = len(bexar_rows)
    print(f"      bexar: {len(bexar_rows):,} protest candidates")

    for county in ("arapahoe",):
        ids = [
            r["PropertyId"]
            for r in con.execute(
                """
                SELECT PropertyId FROM parcels
                WHERE County = ?
                GROUP BY PropertyId
                ORDER BY MIN(rowid)
                """,
                (county,),
            )
        ]
        started = time.time()
        batch = []
        for i, property_id in enumerate(ids, start=1):
            result = analyze(con, county, property_id)
            if result.is_protestable:
                subject = result.subject
                savings_note = (
                    "Varies by tax district"
                    if result.estimated_annual_tax_savings is None
                    else ""
                )
                batch.append(
                    (
                        county,
                        subject["PropertyId"],
                        subject["SitusAddress"],
                        subject["OwnerFullName"],
                        subject["ZipCode"],
                        subject["AppraisedValue"],
                        result.target_value,
                        result.estimated_reduction,
                        result.estimated_pct_reduction,
                        result.estimated_annual_tax_savings,
                        savings_note,
                        result.comp_count_total,
                        result.geography_tier_used,
                        result.reason,
                    )
                )

            if len(batch) >= 5000:
                cur.executemany(insert_sql, batch)
                total_candidates += len(batch)
                batch.clear()

            if i % 50000 == 0:
                elapsed = time.time() - started
                print(f"      {county}: checked {i:,}/{len(ids):,} parcels in {elapsed:.0f}s")

        if batch:
            cur.executemany(insert_sql, batch)
            total_candidates += len(batch)

        con.commit()
        print(f"      {county}: candidate scan complete")

    cur.execute("CREATE INDEX idx_candidates_county ON protest_candidates(County)")
    con.commit()
    print(f"      {total_candidates:,} total protest candidates")


def build_bexar_candidate_rows(parcels):
    """Compute Bexar candidates in batches using the same value-band tiers."""
    from comp_engine import (
        BEXAR_EFFECTIVE_TAX_RATE,
        MAX_CLAIMABLE_PCT,
        MIN_COMPS,
        VAL_BAND_HI_BEXAR_CB,
        VAL_BAND_HI_BEXAR_CBBLK,
        VAL_BAND_LO_BEXAR_CB,
        VAL_BAND_LO_BEXAR_CBBLK,
    )

    bexar = parcels[parcels["County"] == "bexar"].drop_duplicates(
        subset=["County", "PropertyId"],
        keep="first",
    ).copy()
    bexar["ExportKey"] = range(len(bexar))
    tier_results = {}

    block_rows = bexar[bexar["CB"].notna() & bexar["BLK"].notna()]
    for _, group in block_rows.groupby(["CB", "BLK"], sort=False):
        add_band_results(
            tier_results,
            group,
            VAL_BAND_LO_BEXAR_CBBLK,
            VAL_BAND_HI_BEXAR_CBBLK,
            "same city block + block",
            MIN_COMPS,
        )

    remaining = bexar[
        bexar["CB"].notna() & ~bexar["ExportKey"].isin(tier_results.keys())
    ]
    for _, group in remaining.groupby("CB", sort=False):
        add_band_results(
            tier_results,
            group,
            VAL_BAND_LO_BEXAR_CB,
            VAL_BAND_HI_BEXAR_CB,
            "same city block",
            MIN_COMPS,
        )

    rows = []
    for row in bexar.itertuples(index=False):
        result = tier_results.get(row.ExportKey)
        if not result:
            continue
        median_appraised, comp_count, tier = result
        reduction = float(row.AppraisedValue) - median_appraised
        pct = reduction / float(row.AppraisedValue) * 100 if row.AppraisedValue else 0
        if reduction <= 0 or pct < 2.0 or pct > MAX_CLAIMABLE_PCT:
            continue
        rows.append(
            (
                "bexar",
                row.PropertyId,
                row.SitusAddress,
                row.OwnerFullName,
                sqlite_value(row.ZipCode),
                sqlite_value(row.AppraisedValue),
                median_appraised,
                reduction,
                pct,
                reduction * BEXAR_EFFECTIVE_TAX_RATE,
                "",
                comp_count,
                tier,
                "overassessed_vs_comps",
            )
        )
    return rows


def sqlite_value(value):
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def add_band_results(results, group, lo_factor, hi_factor, tier, min_comps):
    if len(group) <= min_comps:
        return

    sorted_group = group.sort_values(["AppraisedValue", "PropertyId"], kind="mergesort")
    values = [float(v) for v in sorted_group["AppraisedValue"].tolist()]
    keys = sorted_group["ExportKey"].tolist()

    for pos, value in enumerate(values):
        left = bisect_left(values, value * lo_factor)
        right = bisect_right(values, value * hi_factor)
        comp_count = right - left - 1
        if comp_count < min_comps:
            continue
        results.setdefault(
            keys[pos],
            (median_excluding_self(values, left, right, pos), comp_count, tier),
        )


def median_excluding_self(values, left, right, self_pos):
    count = right - left - 1

    def pick(offset):
        index = left + offset
        if index >= self_pos:
            index += 1
        return values[index]

    mid = count // 2
    if count % 2:
        return pick(mid)
    return (pick(mid - 1) + pick(mid)) / 2


def main(argv):
    if len(argv) == 3:
        bexar_csv, db_path = argv[1], argv[2]
        frames = [build_bexar(bexar_csv)]
    elif len(argv) == 4:
        bexar_csv, arapahoe_csv, db_path = argv[1], argv[2], argv[3]
        frames = [build_bexar(bexar_csv), build_arapahoe(arapahoe_csv)]
    else:
        print("Usage: python build_db.py BEXAR.csv [ARAPAHOE.csv] OUTPUT.db")
        return 1

    write_sqlite(frames, db_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
