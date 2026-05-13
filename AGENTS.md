# AGENTS.md

> This file is the source of truth for any AI coding agent (Codex, Cursor, Claude
> Code, etc.) working on this repo. Read it end-to-end before making changes.

## What this project is

**Bexar Protest Helper** — a free public web tool. A Bexar County homeowner enters
their address, sees an unequal-appraisal comp analysis from the 2026 BCAD
appraisal roll, and downloads a PDF evidence packet they file themselves on
BCAD E-File before the **May 15, 2026** deadline.

Two halves:

1. `backend/` — Python FastAPI service. Read-only SQLite (~210 MB) bundled into a
   Docker image. Deploys to **Google Cloud Run**.
2. `frontend/` — React + Vite + TypeScript + Tailwind. Deploys to **Firebase
   Hosting**. Lead capture writes directly to Firestore via the Firebase web SDK
   (no backend hop).

## Important: legacy code in this repo

This repository was previously used for an unrelated experiment ("chat detector,"
a Python/Vercel app). **All pre-existing files must be deleted** (`app.py`,
`Procfile`, `vercel.json`, `runtime.txt`, `vendors.json`, the old
`requirements.txt`, the old `.gitignore`). The replacement files in this PR
supersede them.

## What you (the agent) should do

Work through these tasks **in order**. Do not skip ahead — later tasks assume
the earlier ones are complete.

### Task 1 — Wipe legacy files

Delete these files from the repo root if they exist:
- `app.py`
- `Procfile`
- `vercel.json`
- `runtime.txt`
- `vendors.json`
- The old root-level `requirements.txt` (note: a new one lives at `backend/requirements.txt`)
- The old root-level `.gitignore` (a new one is at the repo root in this PR)

### Task 2 — Verify the new file tree

After this PR is applied, the repo should look like this:

```
.
├── AGENTS.md                      # this file
├── README.md
├── .gitignore
├── .firebaserc                    # placeholder project ID
├── firebase.json                  # Firebase Hosting + Firestore config
├── firestore.rules                # Firestore security rules
├── backend/
│   ├── README.md
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── api.py                     # FastAPI app
│   ├── comp_engine.py             # comp algorithm
│   ├── pdf_packet.py              # ReportLab PDF generator
│   └── build_db.py                # CSV → SQLite (run locally)
└── frontend/
    ├── .env.example
    ├── index.html
    ├── package.json
    ├── postcss.config.js
    ├── tailwind.config.js
    ├── tsconfig.json
    ├── tsconfig.node.json
    ├── vite.config.ts
    └── src/
        ├── App.tsx
        ├── main.tsx
        ├── index.css
        ├── lib/
        │   ├── api.ts            # API client + types
        │   └── firebase.ts       # Firebase init + lead capture
        └── pages/
            ├── Home.tsx
            ├── Property.tsx
            └── Thanks.tsx
```

If any file is missing, stop and report it. Do not fabricate replacements.

### Task 3 — Verify the frontend builds

```bash
cd frontend
cp .env.example .env.local
npm install
npm run build
```

The TypeScript compile (`tsc -b`) and Vite build must both succeed with **zero
errors and zero warnings**. If TypeScript complains:

- Do **not** weaken `strict` mode in `tsconfig.json`.
- Do **not** add `// @ts-ignore` or `any` to silence errors.
- Fix the underlying type issue, or if the issue is a genuine missing dependency
  type, add `@types/...` as a devDependency.

### Task 4 — Verify the frontend runs in dev mode

```bash
cd frontend
npm run dev
```

The dev server should start on `http://localhost:5173`. Visiting it should show
the Home page hero ("Are you overpaying property taxes on your Bexar County
home?") with a working address-input field. The search will fail with a network
error (no backend running yet) — that's expected.

### Task 5 — Stop here for human handoff

Do **not** attempt:
- Building or running the backend (requires the 700K-row CSV that's not in the repo)
- Running `gcloud` or `firebase deploy` (requires the user's credentials)
- Editing `.firebaserc` or `.env.example` to put real credentials in

These are documented in `README.md` as manual steps for the repo owner.

## How the pieces fit together

```
┌─────────────────┐         GET /search?q=...
│  React frontend │ ──────────────────────────┐
│  (Firebase      │  GET /analyze/{id}        │
│   Hosting)      │  GET /packet/{id}         ▼
│                 │                  ┌──────────────────┐
│                 │                  │  FastAPI         │
│   addDoc()      │                  │  (Cloud Run)     │
│      │          │                  │                  │
│      ▼          │                  │  SQLite (210 MB) │
│  Firestore      │                  │  bundled in image│
│  /leads         │                  └──────────────────┘
└─────────────────┘
```

The backend is **completely stateless** and has **no Firebase dependencies**.
The frontend handles all lead capture by writing directly to Firestore using
the Firebase web SDK. This keeps the backend simple and means the Cloud Run
service doesn't need any service account secrets.

## Coding conventions

- TypeScript strict mode is on. No `any`, no `@ts-ignore`.
- React function components with hooks. No class components.
- Tailwind utility classes for styling. Brand colors live in
  `tailwind.config.js` under the `bcad` namespace (don't use raw hex codes in
  components).
- Python: type hints encouraged; no formatter-specific config (don't add
  black/ruff configs without asking).
- Keep `frontend/package.json` versions pinned exactly as shipped — they're
  chosen for compatibility, not to be auto-upgraded.

## Constraints on agent behavior

- **Do not** add analytics, tracking pixels, or third-party scripts. The site
  is meant to be a public utility; user trust matters.
- **Do not** add a payments integration in this PR (Stripe, etc.). The 2026
  season is free; payments come in a follow-up.
- **Do not** add a service worker or PWA manifest. Adds complexity for no MVP
  benefit.
- **Do not** modify the comp algorithm constants in `backend/comp_engine.py`
  (`MIN_COMPS`, `VAL_BAND_*`, `MAX_CLAIMABLE_PCT`). They were tuned against
  1,000 random parcels; changes affect the credibility of the protest packets.
- **Do not** change the BCAD blue palette without asking. It matches the PDF.

## If you find a bug

Open a question in the PR rather than guessing at intent. The acceptance
criteria above are what matters; don't add scope.
