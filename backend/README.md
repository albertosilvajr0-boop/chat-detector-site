# Backend - Property Protest Helper API

FastAPI service exposing search, analysis, and PDF generation over normalized
Bexar County and Arapahoe County appraisal rolls. Stateless; the only state is a
read-only SQLite database bundled into the Docker image.

## Files

- `api.py` - FastAPI app with county-aware endpoints
- `comp_engine.py` - County-aware comparable-value logic
- `pdf_packet.py` - ReportLab evidence packet generator
- `build_db.py` - Builds `bcad.db` from county CSVs
- `Dockerfile` - Cloud Run image
- `requirements.txt` - Python dependencies

## Build the database

```bash
cd backend
pip install -r requirements.txt

# Bexar only
python build_db.py /path/to/bexar.csv ./bcad.db

# Bexar + Arapahoe
python build_db.py /path/to/bexar.csv /path/to/arapahoe.csv ./bcad.db
```

Re-run when either county republishes the roll. Do not commit `bcad.db`.

## Local dev

```bash
DB_PATH=./bcad.db uvicorn api:app --reload --port 8080
```

## Deploy to Cloud Run

```bash
gcloud run deploy protest-helper \
    --source . \
    --region us-central1 \
    --allow-unauthenticated \
    --memory 1Gi --cpu 1 \
    --max-instances 10 \
    --set-env-vars PRODUCT_NAME="Bexar + Arapahoe Protest Helper",CORS_ORIGINS="*"
```

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| GET | `/healthz` | Health plus total/county parcel counts |
| GET | `/counties` | Supported county metadata |
| GET | `/search?county=bexar&q=text&limit=10` | List matching parcels by address or owner name |
| GET | `/analyze/{county}/{property_id}` | Full analysis JSON |
| GET | `/packet/{county}/{property_id}` | PDF download when comps support a reduction |

Legacy Bexar routes `/analyze/{property_id}` and `/packet/{property_id}` remain available.
