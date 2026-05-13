# Bexar Protest Helper

A free web tool that helps Bexar County, Texas homeowners protest their property
tax appraisal before the **May 15, 2026** deadline.

- Frontend (React + Vite + Tailwind) → Firebase Hosting
- Backend (FastAPI + SQLite) → Cloud Run
- Lead capture → Firestore (directly from the frontend)

For agents working on this code, see [`AGENTS.md`](./AGENTS.md).

---

## One-time setup (do this Tuesday night)

### 1. Local prerequisites

```bash
# Node 20+ and Python 3.12 should already be installed.
# Install Firebase CLI globally:
npm install -g firebase-tools

# Install Google Cloud SDK if not already:
# https://cloud.google.com/sdk/docs/install
gcloud --version
```

### 2. Create the Firebase project (or reuse an existing one)

```bash
firebase login
firebase projects:list
```

Either pick an existing project ID or create one in the
[Firebase Console](https://console.firebase.google.com/).

Then edit `.firebaserc` and replace `REPLACE_WITH_YOUR_FIREBASE_PROJECT_ID`
with your actual project ID.

### 3. Add a Firebase **web app** to the project

In the Firebase Console: **Project settings → Your apps → Add app → Web**.
Copy the config values into `frontend/.env.local`:

```bash
cd frontend
cp .env.example .env.local
# Open .env.local and paste the 6 VITE_FIREBASE_* values from the console
```

### 4. Enable Firestore in **production mode**

Firebase Console → Build → Firestore Database → Create database → production mode.
Pick a region close to San Antonio (`us-central1` is fine).

Then deploy the security rules:

```bash
# From repo root
firebase deploy --only firestore:rules
```

### 5. Build the SQLite database from the BCAD CSV

The BCAD CSV (`bexar_county_all_properties_sorted_by_proximity_to_78233.csv`)
is too large to commit to git. Build the database locally:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python build_db.py /path/to/bexar_county_all_properties.csv ./bcad.db
```

The resulting `bcad.db` is ~210 MB. It stays local; the Docker build will
COPY it into the image.

---

## Deploying

### Backend → Cloud Run

```bash
cd backend
gcloud auth login
gcloud config set project YOUR_FIREBASE_PROJECT_ID

# The first deploy enables the necessary APIs and creates the service.
gcloud run deploy protest-helper \
    --source . \
    --region us-central1 \
    --allow-unauthenticated \
    --memory 1Gi --cpu 1 \
    --max-instances 10 \
    --set-env-vars PRODUCT_NAME="Bexar Protest Helper",CORS_ORIGINS="https://YOUR-DOMAIN.com,https://YOUR-PROJECT.web.app"
```

After deploy, grab the service URL (e.g. `https://protest-helper-xxxxx.run.app`)
and put it in `frontend/.env.local`:

```
VITE_API_BASE_URL=https://protest-helper-xxxxx.run.app
```

Smoke test it:

```bash
curl https://protest-helper-xxxxx.run.app/healthz
# Expected: {"ok": true, "parcels": 699751}
```

### Frontend → Firebase Hosting

```bash
cd frontend
npm install
npm run build           # produces frontend/dist/

cd ..
firebase deploy --only hosting
```

Visit the URL Firebase prints (`https://YOUR-PROJECT.web.app`). Test the full
flow: search for `554 W BROADVIEW DR` (a known-protestable address),
click into the property page, enter your email, download the packet.

---

## Custom domain

Once it's working at `YOUR-PROJECT.web.app`:

1. Register the domain (e.g. via Namecheap).
2. Firebase Console → Hosting → Add custom domain → follow the DNS verification
   steps. Adds an A record at the apex pointing to Firebase's load balancer.
3. Update the backend CORS to include the new domain:

```bash
gcloud run services update protest-helper \
    --region us-central1 \
    --update-env-vars CORS_ORIGINS="https://YOUR-DOMAIN.com,https://YOUR-PROJECT.web.app"
```

---

## Monitoring during launch week

```bash
# Live tail Cloud Run logs
gcloud run services logs tail protest-helper --region us-central1

# See captured leads in Firestore
firebase firestore:get leads --limit 50
```

Or open the Firebase Console → Firestore → `leads` collection for a UI view.

---

## Repository layout

```
backend/        Python FastAPI service (deploys to Cloud Run)
frontend/       React + Vite app (deploys to Firebase Hosting)
firebase.json   Firebase Hosting + Firestore config
firestore.rules Firestore security rules (allow-create-only on /leads)
AGENTS.md       Brief for AI coding agents
```

For backend-specific notes (endpoints, schema), see [`backend/README.md`](./backend/README.md).
