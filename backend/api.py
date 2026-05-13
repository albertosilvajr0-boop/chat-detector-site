"""
BCAD Protest Helper — Cloud Run API service.

Endpoints:
  GET  /healthz                     -> liveness check + parcel count
  GET  /search?q={text}&limit=10    -> matching parcels (FTS5)
  GET  /analyze/{property_id}       -> CompAnalysis as JSON
  GET  /packet/{property_id}        -> PDF download

Lead capture is handled on the frontend by writing directly to Firestore
(see frontend/src/lib/firebase.ts) — keeps this service stateless and
free of any Firebase credentials.

Local dev:
    DB_PATH=./bcad.db uvicorn api:app --reload --port 8080

Deploy to Cloud Run:
    gcloud run deploy protest-helper --source . --region us-central1 \\
        --allow-unauthenticated --memory 1Gi --cpu 1
"""

import os, sqlite3, io, tempfile
from dataclasses import asdict
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from comp_engine import analyze, search_parcels_by_address
from pdf_packet import build_packet

DB_PATH      = os.environ.get('DB_PATH', '/app/bcad.db')
PRODUCT_NAME = os.environ.get('PRODUCT_NAME', 'Bexar Protest Helper')
# Comma-separated list of allowed origins. Tighten before launch.
CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')

app = FastAPI(title="BCAD Protest Helper")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _con():
    """Read-only SQLite connection, one per request."""
    con = sqlite3.connect(f'file:{DB_PATH}?mode=ro', uri=True)
    con.row_factory = sqlite3.Row
    return con


@app.get("/healthz")
def healthz():
    try:
        con = _con()
        n = con.execute("SELECT COUNT(*) FROM parcels").fetchone()[0]
        con.close()
        return {"ok": True, "parcels": n}
    except Exception as e:
        raise HTTPException(500, f"db error: {e}")


@app.get("/search")
def search(q: str, limit: int = 10):
    if not q or len(q.strip()) < 3:
        return {"results": []}
    con = _con()
    try:
        results = search_parcels_by_address(con, q, limit=min(limit, 20))
    finally:
        con.close()
    return {"results": results}


@app.get("/analyze/{property_id}")
def analyze_endpoint(property_id: int):
    con = _con()
    try:
        result = analyze(con, property_id)
    finally:
        con.close()
    if not result.subject:
        raise HTTPException(404, "parcel not found")
    return asdict(result)


@app.get("/packet/{property_id}")
def packet(property_id: int):
    con = _con()
    try:
        result = analyze(con, property_id)
    finally:
        con.close()
    if not result.subject:
        raise HTTPException(404, "parcel not found")
    if not result.is_protestable:
        raise HTTPException(400, f"not protestable: {result.reason}")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        tmp_path = f.name
    build_packet(result, tmp_path, product_name=PRODUCT_NAME)
    with open(tmp_path, 'rb') as f:
        data = f.read()
    os.unlink(tmp_path)

    addr = result.subject['SitusAddress'].replace(' ', '_').replace('/', '-')[:50]
    filename = f"protest_evidence_{addr}.pdf"
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
