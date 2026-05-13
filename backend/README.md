# Backend — BCAD Protest Helper API

FastAPI service exposing search, analysis, and PDF generation over the
2026 BCAD certified appraisal roll. Stateless; the only state is a
read-only ~210 MB SQLite database bundled into the Docker image.

## Files

- `api.py` — FastAPI app with 4 endpoints
- `comp_engine.py` — Tex. Tax Code §41.43(b)(3) unequal-appraisal logic
- `pdf_packet.py` — 4-page ReportLab evidence packet generator
- `build_db.py` — Builds `bcad.db` from the BCAD CSV (run locally, then bundle)
- `Dockerfile` — Cloud Run image
- `requirements.txt` — Python deps

## Build the database (one-time, local)

```bash
cd backend
pip install -r requirements.txt
python build_db.py /path/to/bexar_county_all_properties_sorted_by_proximity_to_78233.csv ./bcad.db
```

Produces `./bcad.db` (~210 MB). Re-run when BCAD republishes the roll.

## Local dev

```bash
DB_PATH=./bcad.db uvicorn api:app --reload --port 8080
# Visit http://localhost:8080/healthz
```

## Deploy to Cloud Run

```bash
# bcad.db must be in the build context — Dockerfile COPYs it into the image
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

gcloud run deploy protest-helper \
    --source . \
    --region us-central1 \
    --allow-unauthenticated \
    --memory 1Gi --cpu 1 \
    --max-instances 10 \
    --set-env-vars PRODUCT_NAME="Bexar Protest Helper",CORS_ORIGINS="https://YOUR-DOMAIN.com,https://YOUR-PROJECT.web.app"
```

Cold start ~3-4s; subsequent requests sub-100ms. Image will be ~250 MB.

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| GET | `/healthz` | `{ok: true, parcels: 699751}` |
| GET | `/search?q=text&limit=10` | List matching parcels by address |
| GET | `/analyze/{property_id}` | Full CompAnalysis JSON |
| GET | `/packet/{property_id}` | PDF download (400 if not protestable) |
