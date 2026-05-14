"""
County-aware property protest helper API.

Endpoints:
  GET /healthz
  GET /counties
  GET /search?county={bexar|arapahoe}&q={text}&limit=10
  GET /analyze/{county}/{property_id}
  GET /packet/{county}/{property_id}

Legacy Bexar routes are retained:
  GET /analyze/{property_id}
  GET /packet/{property_id}
"""

import io
import os
import sqlite3
import tempfile
from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from comp_engine import analyze, county_options, search_parcels_by_address, valid_county
from pdf_packet import build_packet


DB_PATH = os.environ.get("DB_PATH", "/app/bcad.db")
PRODUCT_NAME = os.environ.get("PRODUCT_NAME", "Bexar + Arapahoe Protest Helper")
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")

app = FastAPI(title="Property Protest Helper")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _con():
    """Read-only SQLite connection, one per request."""
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


@app.get("/healthz")
def healthz():
    try:
        con = _con()
        rows = con.execute(
            "SELECT County, COUNT(*) AS n FROM parcels GROUP BY County ORDER BY County"
        ).fetchall()
        con.close()
        counts = {r["County"]: r["n"] for r in rows}
        return {"ok": True, "parcels": sum(counts.values()), "counties": counts}
    except Exception as e:
        raise HTTPException(500, f"db error: {e}")


@app.get("/health")
def health():
    return healthz()


@app.get("/counties")
def counties():
    return {"counties": county_options()}


@app.get("/search")
def search(q: str, county: str = "bexar", limit: int = 10):
    try:
        county = valid_county(county)
    except ValueError as e:
        raise HTTPException(400, str(e))

    if not q or len(q.strip()) < 3:
        return {"results": []}

    con = _con()
    try:
        results = search_parcels_by_address(con, q, county=county, limit=min(limit, 20))
    finally:
        con.close()
    return {"results": results}


@app.get("/analyze/{county}/{property_id}")
def analyze_county_endpoint(county: str, property_id: str):
    try:
        county = valid_county(county)
    except ValueError as e:
        raise HTTPException(400, str(e))

    con = _con()
    try:
        result = analyze(con, county, property_id)
    finally:
        con.close()
    if not result.subject:
        raise HTTPException(404, "parcel not found")
    return asdict(result)


@app.get("/analyze/{property_id}")
def analyze_legacy_endpoint(property_id: str):
    return analyze_county_endpoint("bexar", property_id)


@app.get("/packet/{county}/{property_id}")
def packet_county_endpoint(county: str, property_id: str):
    try:
        county = valid_county(county)
    except ValueError as e:
        raise HTTPException(400, str(e))

    con = _con()
    try:
        result = analyze(con, county, property_id)
    finally:
        con.close()
    if not result.subject:
        raise HTTPException(404, "parcel not found")
    if not result.is_protestable:
        raise HTTPException(400, f"not protestable: {result.reason}")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        tmp_path = f.name
    build_packet(result, tmp_path, product_name=PRODUCT_NAME)
    with open(tmp_path, "rb") as f:
        data = f.read()
    os.unlink(tmp_path)

    addr = result.subject["SitusAddress"].replace(" ", "_").replace("/", "-")[:50]
    filename = f"protest_evidence_{county}_{addr}.pdf"
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/packet/{property_id}")
def packet_legacy_endpoint(property_id: str):
    return packet_county_endpoint("bexar", property_id)
