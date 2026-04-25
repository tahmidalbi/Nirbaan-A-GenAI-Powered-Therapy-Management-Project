# Nirbaan Backend

> **FastAPI** application powering the Nirbaan therapy management platform. Handles authentication, all clinical data, AI/LangGraph agents, WebSocket signaling, live transcription, and background Celery tasks.

---

## Table of Contents

- [Overview](#overview)
- [Module Structure](#module-structure)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Running the Server](#running-the-server)
- [Database](#database)
- [Background Tasks (Celery)](#background-tasks-celery)
- [API Reference](#api-reference)
- [AI Modules](#ai-modules)
- [Environment Variables](#environment-variables)
- [Docker](#docker)
- [Utility Scripts](#utility-scripts)

---

## Overview

The backend is a modular FastAPI application. Each clinical domain lives in its own Python package under `app/` with the same internal layout:

```
app/<module>/
  models.py    — SQLAlchemy ORM models
  schemas.py   — Pydantic request/response schemas
  router.py    — FastAPI APIRouter with all endpoints
  service.py   — Business logic (optional, for complex modules)
```

AI subsystems follow a LangGraph-first pattern:  
`graph.py → nodes/ → state.py → llm/client.py`

---

## Module Structure

```
backend/
├── app/
│   ├── main.py                    # FastAPI app factory, router registration, lifespan
│   ├── auth/                      # JWT auth — therapist & patient registration/login
│   ├── patients/                  # Patient CRUD and therapist–patient relationships
│   ├── therapists/                # Therapist profile management
│   ├── users/                     # Shared user lookup utilities
│   │
│   ├── erp/                       # ERP (Exposure & Response Prevention) module
│   │   ├── ERPCoach/              # LangGraph ERP Coach agent
│   │   │   ├── graph.py           #   LangGraph compiled graph
│   │   │   ├── state.py           #   TypedDict state definition
│   │   │   ├── nodes/             #   Individual graph node functions
│   │   │   ├── prompts/           #   System prompts
│   │   │   ├── llm/               #   LLM client (client.py, retry.py, structured.py)
│   │   │   └── tasks/             #   Celery task wrappers
│   │   └── voice/                 # Realtime voice transcription endpoint
│   │
│   ├── fear_ladder/               # Fear ladder hierarchy CRUD
│   │
│   ├── education/                 # Psychoeducation modules
│   │   ├── erp/                   #   ERP education content
│   │   ├── fear_ladder/           #   Fear ladder education
│   │   ├── ocd_core/              #   OCD core education
│   │   └── relapse_prevention/    #   Relapse prevention education
│   │
│   ├── NirbaanAIPatient/          # Patient-facing AI chatbot (LangGraph)
│   │   ├── CentralAgent/          #   Router agent
│   │   ├── GeneralSupportChatbot/ #   Empathic support sub-agent
│   │   ├── PsychoeducationChatbot/#   OCD psychoeducation sub-agent
│   │   └── HumanEscalationAgent/  #   Risk detection & escalation
│   │
│   ├── NirbaanAITherapist/        # Therapist-facing AI assistant
│   │
│   ├── ERPScriptGenerator/        # Imaginal script LangGraph pipeline
│   │
│   ├── ai_ladder_review/          # V1 AI fear ladder review
│   ├── ai_ladder_review_v2/       # V2 RAG-enhanced fear ladder review
│   │   └── rag/                   #   pgvector retrieval, taxonomy seeding
│   │
│   ├── chat/                      # Messaging
│   │   ├── router.py              #   Therapist↔Patient chat
│   │   ├── ep_router.py           #   EP↔Patient chat
│   │   ├── ep_group_router.py     #   EP group broadcast
│   │   └── ep_patient_router.py   #   EP↔Patient direct messages
│   │
│   ├── therapy_sessions/          # Video session records
│   ├── live_sessions/             # WebSocket signaling + live transcription
│   │   ├── router.py              #   REST session management
│   │   ├── websocket.py           #   WebRTC signaling WebSocket
│   │   └── streaming_transcription.py # Real-time Whisper transcription
│   │
│   ├── self_monitoring/           # Patient self-monitoring logs
│   ├── progress/                  # Weekly progress aggregation
│   ├── patient_homework/          # Homework assignment & submission
│   ├── resources/                 # Clinical file resource library
│   ├── intakes/                   # Patient intake forms
│   ├── emergency_personnel/       # Emergency personnel (EP) accounts
│   │
│   ├── core/                      # Cross-cutting concerns
│   │   ├── celery_app.py          #   Celery application instance
│   │   └── config.py              #   Settings (pydantic-settings)
│   │
│   └── database/
│       ├── session.py             # AsyncSession factory
│       └── base.py                # SQLAlchemy declarative base
│
├── create_all_tables.py           # One-shot table creation (run on first deploy)
├── requirements.txt
├── Dockerfile
├── start.sh                       # Docker entrypoint
├── celery_worker.bat              # Windows Celery worker launcher
└── celery_beat.bat                # Windows Celery beat launcher
```

---

## Prerequisites

- Python 3.11+
- PostgreSQL 16 with the **pgvector** extension enabled
- Redis 7+
- `pip` or `uv`

---

## Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux / macOS

# Install dependencies
pip install -r requirements.txt

# Copy environment file and fill in your values
copy .env.example .env       # or manually create backend/.env
```

---

## Running the Server

```bash
# Start API (hot-reload for development)
uvicorn app.main:app --reload --port 8000
```

Interactive API docs: [http://localhost:8000/docs](http://localhost:8000/docs)  
ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## Database

### First-time setup

```bash
# Creates all tables in the target PostgreSQL database
python create_all_tables.py
```

The script creates every table and runs any necessary migrations (additive only). Safe to re-run — uses `IF NOT EXISTS` internally.

### pgvector

The RAG module (`ai_ladder_review_v2`) requires the `pgvector` extension:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

This is handled automatically when using the `pgvector/pgvector:pg16` Docker image.

### Individual table scripts

For targeted table creation during development:

```bash
python create_erp_tables.py
python create_fear_ladder_tables.py
python create_rag_tables.py
# … see all create_*.py scripts in backend/
```

---

## Background Tasks (Celery)

### Worker

```bash
# Windows (convenience script)
celery_worker.bat

# Manual
celery -A app.core.celery_app worker --loglevel=info --pool=solo --concurrency=4
```

### Beat scheduler

```bash
# Windows
celery_beat.bat

# Manual
celery -A app.core.celery_app beat --loglevel=info
```

### Registered tasks

| Task name | Trigger | Purpose |
|---|---|---|
| `run_ai_ladder_review` | On demand | LLM analysis of a patient fear ladder |
| `generate_imaginal_script` | On demand | LangGraph imaginal script generation |
| `analyse_session_transcript` | Post-session | Transcript summarisation + SUDS extraction |
| `send_homework_reminder` | Scheduled (beat) | Patient homework reminders |

---

## API Reference

All routes are prefixed with `/api`. Key route groups:

| Prefix | Tags | Notes |
|---|---|---|
| `/api/auth` | auth | `POST /register/therapist`, `POST /register/patient`, `POST /login` |
| `/api/patients` | patients | Therapist-scoped CRUD |
| `/api/erp` | erp | Session management, obsession hierarchies |
| `/api/erp/coach` | erp-coach | LangGraph chat endpoint `POST /chat` |
| `/api/erp/voice` | voice | `POST /transcribe-and-respond` |
| `/api/fear-ladder` | fear-ladder | Ladder and step CRUD |
| `/api/education/fear-ladder` | education | Fear ladder module |
| `/api/education/ocd-core` | education | OCD core module |
| `/api/education/erp` | education | ERP module |
| `/api/nirbaan-ai` | nirbaan-ai | Patient chatbot |
| `/api/nirbaan-ai-therapist` | nirbaan-ai | Therapist assistant |
| `/api/imaginal` | imaginal | Script generator |
| `/api/ai-ladder-review` | ai-review | Fear ladder AI review |
| `/api/chat` | chat | Therapist↔Patient messages |
| `/api/therapy-sessions` | sessions | Video session CRUD + WS signaling |
| `/api/resources` | resources | File upload / list / download |
| `/api/self-monitoring` | monitoring | Patient log CRUD |
| `/api/progress` | progress | Weekly aggregated progress |
| `/api/intakes` | intakes | Intake form CRUD |
| `/api/homework` | homework | Assignment + submission |
| `/api/ep` | emergency-personnel | EP management |

---

## AI Modules

### ERP Coach (`app/erp/ERPCoach/`)

LangGraph agent with persistent state per ERP session. The graph:

```
[entry] → check_in_node → coach_node → [end]
                            ↕
                     (tool calls if needed)
```

- **LLM**: configured via `LLM_MODEL` + `OPENAI_API_KEY` environment variables
- **Structured outputs**: uses `build_structured_runnable` with Pydantic schemas
- **Retry logic**: `invoke_with_retries` with exponential backoff + JSON repair pass

### Nirbaan AI Patient (`app/NirbaanAIPatient/`)

Central router agent dispatches to one of three sub-agents based on intent classification. Supports session-level memory via LangGraph's `MemorySaver`.

### Imaginal Script Generator (`app/ERPScriptGenerator/`)

Multi-step LangGraph pipeline:
1. Gather patient obsession and compulsion details
2. Draft imaginal script sections
3. Validate clinical appropriateness
4. Return structured script for therapist review

### AI Ladder Review V2 (`app/ai_ladder_review_v2/`)

RAG-augmented review that:
1. Retrieves relevant clinical guidelines from pgvector store
2. Evaluates SUDS spread and step gradation
3. Returns per-step feedback and an overall ladder score

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | ✅ | `postgresql+asyncpg://user:pass@host/db` |
| `REDIS_URL` | ✅ | `redis://host:6379/0` |
| `SECRET_KEY` | ✅ | JWT signing secret (generate with `openssl rand -hex 32`) |
| `ALGORITHM` | ✅ | JWT algorithm — use `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | ✅ | Token lifetime in minutes |
| `OPENAI_API_KEY` | ✅ | API key for the LLM provider |
| `LLM_MODEL` | ✅ | Model name e.g. `gpt-4o`, `llama-3.1-70b-versatile` |
| `EMBEDDING_MODEL` | ✅ | Embedding model name for RAG |
| `LANGCHAIN_API_KEY` | optional | LangSmith tracing |
| `LANGCHAIN_TRACING_V2` | optional | `true` to enable tracing |
| `LANGCHAIN_PROJECT` | optional | LangSmith project name |
| `R2_ACCOUNT_ID` | optional | Cloudflare R2 file storage |
| `R2_ACCESS_KEY_ID` | optional | Cloudflare R2 |
| `R2_SECRET_ACCESS_KEY` | optional | Cloudflare R2 |
| `R2_BUCKET_NAME` | optional | Cloudflare R2 bucket |
| `R2_PUBLIC_URL` | optional | Public CDN base URL |

---

## Docker

The `Dockerfile` uses a slim Python 3.11 image. The startup command:

```bash
python create_all_tables.py \
  && python -m app.ai_ladder_review_v2.rag.taxonomy_seed \
  && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

See the root [`docker-compose.yml`](../docker-compose.yml) for the full service definition including PostgreSQL, Redis, Celery worker, and Celery beat.

---

## Utility Scripts

| Script | Purpose |
|---|---|
| `create_all_tables.py` | Create / migrate all DB tables |
| `add_ai_summary_columns.py` | Migration: add AI summary columns |
| `add_e2ee_public_key_columns.py` | Migration: add E2EE public key columns |
| `add_source_url_column.py` | Migration: add source URL to resources |
| `add_spike_column.py` | Migration: add spike data to ERP |
| `rename_tables.py` | One-time table rename migration |
| `debug_checkin.py` | Debug ERP check-in flow |
| `test_patient_login.py` | Quick login smoke test |
| `test_therapist_login.py` | Quick therapist login smoke test |
| `reset_patient_password.py` | Admin password reset utility |
