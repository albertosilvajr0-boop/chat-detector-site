# How to give this to Codex

This is a step-by-step for **Alberto**, not for Codex itself. Codex's brief is
in `AGENTS.md`.

## Option A — Codex Web (codex.openai.com)

Codex Web runs in a sandboxed container against your GitHub repo and opens a PR.
This is the most hands-off path.

### 1. Push these files to the repo first

You can't ask Codex to "create these files for me" — you give it files via a
commit. So:

```bash
# Clone your repo
git clone https://github.com/albertosilvajr0-boop/chat-detector-site.git
cd chat-detector-site

# Wipe the old chat-detector code (Codex will verify this in AGENTS.md Task 1)
git rm app.py Procfile vercel.json runtime.txt vendors.json requirements.txt .gitignore

# Unpack the package I gave you into the repo root.
# (Drag-and-drop in Finder, or rsync, or whatever you prefer.)

# Commit and push to a feature branch
git checkout -b sprint/protest-helper
git add .
git commit -m "Scaffold protest-helper monorepo"
git push -u origin sprint/protest-helper
```

### 2. Open Codex and point it at the branch

Go to [codex.openai.com](https://codex.openai.com), select the
`chat-detector-site` repo, and pick the `sprint/protest-helper` branch.

### 3. Give Codex this exact prompt

> Read AGENTS.md and follow Tasks 1 through 5 in order. After Task 4 (frontend
> dev server running), stop and open a PR with a summary of what you did and
> any deviations. Do not run `gcloud`, `firebase deploy`, or any task marked
> manual in README.md.

Codex will:
- Read AGENTS.md
- Confirm legacy files were already removed (Task 1)
- Verify file tree (Task 2)
- Run `npm install` and `npm run build` (Task 3)
- Run `npm run dev` and verify it loads (Task 4)
- Open a PR back to your branch

### 4. Review and merge

The PR should be small (maybe just a `package-lock.json` and possibly some
lockfile cleanup). Review and merge to main.

---

## Option B — Codex CLI (local)

If you'd rather run Codex on your own machine:

```bash
# Install (if you haven't)
npm install -g @openai/codex

# Clone and set up the branch like in Option A above

# From repo root:
cd chat-detector-site
codex
```

In the Codex session, give it the same prompt as Option A step 3.

---

## What you do in parallel (Wednesday morning)

While Codex is working on the frontend, you can run these in parallel:

### Track 1: Domain
- Register a domain (suggestions: `bexarprotest.com`, `sahomeowner.com`,
  `protestbexar.com`). Namecheap or Cloudflare Registrar.

### Track 2: Firebase project
- Either reuse an existing project or create a new one.
- Add a Web app, enable Firestore in production mode, copy the config into
  `frontend/.env.local`.

### Track 3: Build the SQLite locally
This is the one task Codex can't help with — it requires the 700K-row CSV.

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python build_db.py ~/path/to/bexar_county_all_properties.csv ./bcad.db
```

Takes ~30 seconds. Produces a `bcad.db` next to the Dockerfile.

### Track 4: Deploy backend to Cloud Run

```bash
cd backend
gcloud run deploy protest-helper --source . --region us-central1 \
    --allow-unauthenticated --memory 1Gi --cpu 1
```

First deploy takes ~5 minutes (Cloud Build packages the image). Grab the URL
it prints — you need it for `frontend/.env.local`.

---

## When everything is ready (Wednesday night / Thursday morning)

```bash
cd frontend
# Make sure .env.local has both VITE_API_BASE_URL and the 6 VITE_FIREBASE_* values
npm run build

cd ..
firebase deploy --only hosting
```

The site is live at `https://YOUR-PROJECT.web.app`. Test the full flow on your
own house first. Once it works, add the custom domain in the Firebase Console.

---

## If Codex gets stuck

Codex sometimes:
- Tries to "improve" code outside the AGENTS.md scope → reject those changes
  in the PR.
- Adds new dependencies → check that `package.json` versions match what shipped.
- Misreads the file tree → re-prompt with "Re-read AGENTS.md Task 2 and tell me
  what's missing."

The acceptance criteria are explicit in AGENTS.md. Hold Codex to them.
