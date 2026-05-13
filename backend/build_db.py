"""
Build the SQLite database from the BCAD CSV export.

Run locally on your machine to produce bcad.db, then bundle it into the
Docker image at /app/bcad.db (see Dockerfile). For a fresh appraisal roll
(BCAD republishes throughout the year), re-run this and redeploy.

Usage:
    python build_db.py path/to/bexar_all_properties.csv path/to/output/bcad.db
"""

import sys, re, os, sqlite3
import pandas as pd


def parse_legal(ld):
    """Extract (CB, BLK) from BCAD legal description."""
    if pd.isna(ld): return (None, None)
    s = str(ld).upper()
    cb  = re.search(r'\bN?CB\s+(\d+)', s) or re.search(r'\bNB\s+(\d+)', s)
    blk = re.search(r'\bBLK\s+(\w+)', s)
    return (cb.group(1) if cb else None, blk.group(1) if blk else None)


def norm_addr(s):
    if pd.isna(s): return ''
    return re.sub(r'\s+', ' ', str(s).upper()).strip()


def has_excl(gc):
    """Codes we exclude from the residential set (public-owned, churches, etc.)."""
    if pd.isna(gc): return False
    toks = set(t.strip() for t in str(gc).split(','))
    return bool(toks & {'EXPUB','EXCH','EXUR','EX-XV','EX-XR'})


def has_hs(gc):
    """Detect homestead-related codes (proxy for owner-occupied)."""
    if pd.isna(gc): return False
    toks = set(t.strip() for t in str(gc).split(','))
    if {'HS-AUDIT-OK','HS','HS65','DV100%'} & toks: return True
    return any('EXUP' in t for t in toks)


def main(csv_path: str, db_path: str):
    print(f"[1/5] Reading {csv_path}...")
    df = pd.read_csv(csv_path, low_memory=False)
    print(f"      {len(df):,} rows loaded")

    print("[2/5] Filtering to residential parcels...")
    res = df[
        (df['PropertyTypeCode'] == 'R (Real)') &
        (df['AppraisedValue'].notna()) &
        (df['AppraisedValue'] > 1000) &
        (df['SitusAddress'].notna())
    ].copy()
    res = res[~res['GroupCodes'].apply(has_excl)]
    print(f"      {len(res):,} residential parcels")

    print("[3/5] Parsing legal descriptions...")
    parsed = res['LegalDescription'].apply(parse_legal)
    res['CB']  = parsed.apply(lambda x: x[0])
    res['BLK'] = parsed.apply(lambda x: x[1])
    res['NormAddr'] = res['SitusAddress'].apply(norm_addr)
    res['HasHomestead'] = res['GroupCodes'].apply(has_hs)

    print(f"[4/5] Writing SQLite to {db_path}...")
    if os.path.exists(db_path):
        os.remove(db_path)
    con = sqlite3.connect(db_path)
    cols = ['PropertyId','GeoId','ZipCode','DistanceFrom78233',
            'OwnerFullName','SitusAddress','NormAddr','LegalDescription',
            'MarketValue','AppraisedValue','AssessedValue','Year',
            'GroupCodes','CB','BLK','HasHomestead']
    res[cols].to_sql('parcels', con, index=False, if_exists='replace')

    cur = con.cursor()
    print("[5/5] Building indexes + FTS5 address search...")
    cur.execute("CREATE INDEX idx_propid  ON parcels(PropertyId)")
    cur.execute("CREATE INDEX idx_cb      ON parcels(CB)")
    cur.execute("CREATE INDEX idx_cb_blk  ON parcels(CB, BLK)")
    cur.execute("CREATE INDEX idx_zip     ON parcels(ZipCode)")
    cur.execute("CREATE INDEX idx_value   ON parcels(AppraisedValue)")
    cur.execute("""CREATE VIRTUAL TABLE addr_fts USING fts5(
        NormAddr, PropertyId UNINDEXED, content='parcels', content_rowid='rowid'
    )""")
    cur.execute("INSERT INTO addr_fts(rowid, NormAddr, PropertyId) "
                "SELECT rowid, NormAddr, PropertyId FROM parcels")
    con.commit()
    con.close()

    size_mb = os.path.getsize(db_path) / 1024 / 1024
    print(f"\nDone. {db_path}  ({size_mb:.0f} MB)")


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python build_db.py INPUT.csv OUTPUT.db")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
