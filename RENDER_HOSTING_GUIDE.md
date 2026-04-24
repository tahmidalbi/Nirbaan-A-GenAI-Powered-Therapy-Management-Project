# Nirbaan — Complete Render Hosting Guide

## What is already done (no action needed)

| Item | Status |
|---|---|
| `frontend/src/api/axios.js` — hardcoded URL replaced with `VITE_API_URL` env var | ✅ Done |
| `frontend/src/components/VideoCall.jsx` — WebSocket URL replaced with `VITE_API_URL` | ✅ Done |
| `.github/workflows/ci.yml` — CI build check + Render deploy hooks on push | ✅ Done |
| HuggingFace model `tahmidalbi/nirbaan-erp-federated` uploaded | ✅ Done |
| You are on the `hosting` git branch | ✅ Done |

---

## Architecture on Render

```
GitHub (hosting branch)
    │
    └─► GitHub Actions CI/CD (.github/workflows/ci.yml)
            │  builds Docker images to verify
            │  then on success, triggers 4 deploy hooks:
            ▼
    ┌────────────────────────────────────────────────────┐
    │                    Render                           │
    │                                                     │
    │  [Web Service]      nirbaan-backend   port 8000    │
    │  [Background]       celery-worker                  │
    │  [Background]       celery-beat                    │
    │  [Web Service]      nirbaan-frontend  port 80      │
    │  [Redis]            nirbaan-redis                  │
    └────────────────────────────────────────────────────┘
            │
            └─► Supabase (PostgreSQL + pgvector)
```

> **Note:** Ollama is NOT hosted. ERP imaginal script generation will not work in the hosted version. Everything else works.

---

## Step 1 — Push current code to GitHub

Run these commands in your terminal from the project root:

```powershell
git add .
git commit -m "hosting: env-based API URL, CI/CD workflow"
git push origin hosting
```

If you haven't set up the GitHub remote yet:
```powershell
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git push -u origin hosting
```

---

## Step 2 — Create Supabase database

Render's managed PostgreSQL does **not** include the `pgvector` extension. Supabase has it pre-installed.

1. Go to [https://supabase.com](https://supabase.com) → **New project**
2. Choose a region close to your Render region (e.g. both `US East`)
3. Set a strong database password (save it — you'll need it)
4. Wait ~2 minutes for provisioning
5. Go to: **Project Settings → Database → Connection string → URI**
6. Copy the connection string — it looks like:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.xxxxxxxxxxxx.supabase.co:5432/postgres
   ```
7. Also note the **Project URL** from **Settings → API** (needed if you use Supabase auth features later)

> You will need this connection string in Step 4 as `DATABASE_URL`.

---

## Step 3 — Create Render Redis

1. Go to [https://render.com](https://render.com) → **New → Redis**
2. Name: `nirbaan-redis`
3. Plan: **Free**
4. Click **Create Redis**
5. Once created, go to the Redis dashboard and copy the **Internal Redis URL**
   - Looks like: `redis://red-xxxxxxxxxxxxxxxxx:6379`

> You will need this URL in Step 4 as `REDIS_URL`, `CELERY_BROKER_URL`, and `CELERY_RESULT_BACKEND`.

---

## Step 4 — Create 4 Render Services

### Notes before you start:
- All backend services use the same Docker image (built from `backend/Dockerfile`)
- Set **Auto-Deploy** to **No** on all services — GitHub Actions controls deploys
- Use branch `hosting`

---

### Service 1: Backend (Web Service)

| Setting | Value |
|---|---|
| Type | Web Service |
| Source | GitHub repo, branch `hosting` |
| Root Directory | `backend` |
| Runtime | Docker |
| Dockerfile Path | `./Dockerfile` |
| Port | `8000` |
| Start Command | `bash -c "python create_all_tables.py && python -m app.ai_ladder_review_v2.rag.taxonomy_seed && uvicorn app.main:app --host 0.0.0.0 --port 8000"` |
| Auto-Deploy | No |

**Environment Variables** (add all of these):

```
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.xxxxxxxxxxxx.supabase.co:5432/postgres
PGVECTOR_CONNECTION=postgresql+psycopg://postgres:[YOUR-PASSWORD]@db.xxxxxxxxxxxx.supabase.co:5432/postgres
LANGGRAPH_CHECKPOINT_DB_URL=postgresql://postgres:[YOUR-PASSWORD]@db.xxxxxxxxxxxx.supabase.co:5432/postgres

SECRET_KEY=YyJ8cH9Kk3sP0qR5mN7vT2xL9aB1dE4fG6hU8jI0oP2wS5zX

REDIS_URL=redis://red-xxxxxxxxxxxxxxxxx:6379
CELERY_BROKER_URL=redis://red-xxxxxxxxxxxxxxxxx:6379
CELERY_RESULT_BACKEND=redis://red-xxxxxxxxxxxxxxxxx:6379

PIPER_MODEL_PATH=/app/app/ERPScriptGenerator/voices/en_US-lessac-medium.onnx
PIPER_OUTPUT_DIR=/app/media/imaginal_audio

OLLAMA_BASE_URL=http://disabled
OLLAMA_MODEL=nirbaan-erp-federated

OPENAI_API_KEY=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
EMBEDDING_DIMENSION=3072
LLM_MODEL=gpt-4o

MAX_CHUNK_SIZE=40
CHUNK_OVERLAP=80

R2_ACCOUNT_ID=88d1dc2f3bce02c46cf91bcd4afbdc79
R2_ACCESS_KEY_ID=543e5c6eb7f94d5ab62b6a2e0380ece9
R2_SECRET_ACCESS_KEY=3ef80083b492eb326e8364dccae027d31fbf6af9880cab4cdd73c09d0128d6b8
R2_BUCKET_NAME=nirbaan-knowledge-base
R2_ENDPOINT_URL=https://88d1dc2f3bce02c46cf91bcd4afbdc79.r2.cloudflarestorage.com
R2_PRESIGNED_URL_EXPIRY=3600

LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY=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
LANGCHAIN_PROJECT=NIRBAAN
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=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
LANGSMITH_PROJECT=NIRBAAN

GOOGLE_API_KEY=AIzaSyDAFr5IM8b9DDANYeAzdIsIjQToMP2S0GM
TAVILY_API_KEY=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

INDEX_NAME=medium-blogs-embeddings-index
PINECONE_API_KEY=your_pinecone_api_key_here
```

> After creation, copy the **Deploy Hook URL** from Settings → Deploy Hook. You need it for Step 5.
> Also copy the **service URL** (e.g. `https://nirbaan-backend.onrender.com`) — needed for the frontend.

---

### Service 2: Celery Worker (Background Worker)

| Setting | Value |
|---|---|
| Type | Background Worker |
| Source | GitHub repo, branch `hosting` |
| Root Directory | `backend` |
| Runtime | Docker |
| Dockerfile Path | `./Dockerfile` |
| Start Command | `celery -A app.core.celery_app worker --loglevel=info --pool=solo --concurrency=2` |
| Auto-Deploy | No |

**Environment Variables:** Same as Service 1 (copy all the same variables).

> Copy the **Deploy Hook URL** from Settings → Deploy Hook.

---

### Service 3: Celery Beat (Background Worker)

| Setting | Value |
|---|---|
| Type | Background Worker |
| Source | GitHub repo, branch `hosting` |
| Root Directory | `backend` |
| Runtime | Docker |
| Dockerfile Path | `./Dockerfile` |
| Start Command | `celery -A app.core.celery_app beat --loglevel=info` |
| Auto-Deploy | No |

**Environment Variables:** Same as Service 1 (copy all the same variables).

> Copy the **Deploy Hook URL** from Settings → Deploy Hook.

---

### Service 4: Frontend (Web Service)

| Setting | Value |
|---|---|
| Type | Web Service |
| Source | GitHub repo, branch `hosting` |
| Root Directory | `frontend` |
| Runtime | Docker |
| Dockerfile Path | `./Dockerfile` |
| Port | `80` |
| Auto-Deploy | No |

**Environment Variables:**

```
VITE_API_URL=https://nirbaan-backend.onrender.com
```

> Replace `nirbaan-backend` with the actual name you gave your backend service.
> Copy the **Deploy Hook URL** from Settings → Deploy Hook.

---

## Step 5 — Set GitHub Actions Secrets

Go to your GitHub repo → **Settings → Secrets and variables → Actions → New repository secret**

Add these 4 secrets, using the deploy hook URLs from Step 4:

| Secret Name | Value |
|---|---|
| `RENDER_BACKEND_DEPLOY_HOOK` | Deploy hook URL from Service 1 |
| `RENDER_CELERY_WORKER_DEPLOY_HOOK` | Deploy hook URL from Service 2 |
| `RENDER_CELERY_BEAT_DEPLOY_HOOK` | Deploy hook URL from Service 3 |
| `RENDER_FRONTEND_DEPLOY_HOOK` | Deploy hook URL from Service 4 |

Deploy hook URLs look like:
```
https://api.render.com/deploy/srv-xxxxxxxxxxxxxxxxx?key=xxxxxxxxx
```

---

## Step 6 — Trigger first deploy

Push an empty commit to trigger the CI/CD pipeline:

```powershell
git commit --allow-empty -m "trigger: first hosted deploy"
git push origin hosting
```

Then go to your GitHub repo → **Actions** tab to watch the workflow run.

The workflow does:
1. Builds backend Docker image (CI check)
2. Builds frontend (CI check)  
3. If both pass → fires all 4 Render deploy hooks

First deploy will take **10–15 minutes** because Docker images are built from scratch on Render.

---

## Step 7 — Verify deployment

Once Render shows all services as **Live**:

1. **Backend health check**: Open `https://your-backend.onrender.com/docs` — FastAPI Swagger UI should load
2. **Frontend**: Open `https://your-frontend.onrender.com` — login page should appear
3. **Database**: Try registering a new account — if it succeeds, pgvector + migrations worked
4. **Celery**: Check Render logs for celery_worker — should show `celery@xxx ready`

---

## Environment Variables Reference

Quick reference for what goes where:

| Variable | Backend | Celery Worker | Celery Beat | Frontend |
|---|:---:|:---:|:---:|:---:|
| `DATABASE_URL` | ✅ | ✅ | ✅ | — |
| `PGVECTOR_CONNECTION` | ✅ | ✅ | ✅ | — |
| `LANGGRAPH_CHECKPOINT_DB_URL` | ✅ | ✅ | — | — |
| `REDIS_URL` | ✅ | ✅ | ✅ | — |
| `CELERY_BROKER_URL` | ✅ | ✅ | ✅ | — |
| `CELERY_RESULT_BACKEND` | ✅ | ✅ | ✅ | — |
| `SECRET_KEY` | ✅ | ✅ | — | — |
| `OPENAI_API_KEY` | ✅ | ✅ | — | — |
| `R2_*` | ✅ | ✅ | — | — |
| `VITE_API_URL` | — | — | — | ✅ |
| `OLLAMA_BASE_URL` | ✅ | ✅ | — | — |

---

## What works hosted vs local

| Feature | Hosted (Render) | Local (Docker) |
|---|:---:|:---:|
| Auth (login, register, JWT) | ✅ | ✅ |
| Patient & therapist management | ✅ | ✅ |
| Chat (patient ↔ therapist) | ✅ | ✅ |
| ERP session tracking | ✅ | ✅ |
| Fear ladder (create, steps, review) | ✅ | ✅ |
| OCD Core Education | ✅ | ✅ |
| AI Ladder Review (RAG) | ✅ | ✅ |
| Video calls (WebRTC signaling) | ✅ | ✅ |
| Celery background tasks | ✅ | ✅ |
| Piper TTS audio generation | ✅ | ✅ |
| ERP imaginal script generation | ❌ (no Ollama) | ✅ |
| Emergency Personnel features | ✅ | ✅ |

---

## Troubleshooting

### Backend crashes on startup
- Check Render logs — most likely a missing environment variable
- Make sure `DATABASE_URL` points to Supabase, not the old `db:5432` Docker internal address

### `pgvector extension not found`
- Supabase has pgvector but you may need to enable it manually:
  - Go to Supabase → **SQL Editor** → run: `CREATE EXTENSION IF NOT EXISTS vector;`

### Frontend shows blank page or network errors
- Check that `VITE_API_URL` is set to the exact backend service URL (no trailing slash)
- Make sure backend is deployed and healthy before checking frontend

### Celery worker not processing tasks
- Confirm `CELERY_BROKER_URL` uses the Render **internal** Redis URL (not external)
- Check Render logs for the celery_worker service

### GitHub Actions fails on build step
- Check Actions tab for error details
- Backend Docker build failures are usually a missing system package in `requirements.txt`
- Frontend build failures are usually a missing `npm` package

### First deploy is stuck / very slow
- Normal — first Docker build on Render takes 10–15 minutes
- Subsequent deploys are faster due to layer caching

---

## Local development (unchanged)

Local Docker setup is not affected by any of these changes:

```powershell
docker-compose up --build
```

Frontend at `http://localhost:5173`, backend at `http://localhost:8000`.

The `.env.docker` file is still used for local Docker. The Render env vars are configured separately in the Render dashboard.
