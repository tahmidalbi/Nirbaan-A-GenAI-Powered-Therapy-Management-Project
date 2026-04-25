# Nirbaan — AI-Powered Therapy Management Platform


**Live Demo:** [https://nirbaan-frontend-6vu7.onrender.com](https://nirbaan-frontend-6vu7.onrender.com)

> **Nirbaan** is a full-stack, AI-first therapy management platform built for OCD and anxiety treatment. It combines evidence-based clinical workflows (ERP, Fear Ladders, Imaginal Scripting) with cutting-edge AI tooling — LangGraph agents, RAG knowledge retrieval, real-time video sessions, and a fine-tuned local LLM — all orchestrated inside a HIPAA-conscious architecture.

---

## Table of Contents

- [Features](#features)
- [Architecture Overview](#architecture-overview)
- [Folder Structure](#folder-structure)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Quick Start (Docker)](#quick-start-docker)
- [Local Development](#local-development)
- [Environment Variables](#environment-variables)
- [Key API Modules](#key-api-modules)
- [AI & LLM Subsystems](#ai--llm-subsystems)
- [WebRTC Video Calls](#webrtc-video-calls)
- [Background Jobs (Celery)](#background-jobs-celery)
- [Federated QLoRA Fine-Tuning](#federated-qlora-fine-tuning)
- [Contributing](#contributing)

---

## Features

### Clinical Workflows
| Feature | Description |
|---|---|
| **ERP Sessions** | Full Exposure & Response Prevention session lifecycle with AI Coach |
| **Fear Ladder** | Build, manage and track hierarchical fear ladders |
| **Imaginal Scripts** | AI-generated imaginal exposure scripts with therapist review |
| **Self-Monitoring** | Patient daily OCD/anxiety self-monitoring logs |
| **Patient Intakes** | Structured digital intake forms |
| **Patient Homework** | Therapist-assigned homework with submission tracking |
| **Weekly Progress** | Visual progress charts and trend analysis |
| **Relapse Prevention** | Structured relapse prevention education modules |

### AI Capabilities
| Feature | Description |
|---|---|
| **ERP Coach (LangGraph)** | Stateful multi-node LangGraph agent guiding ERP exercises |
| **Nirbaan AI Patient Chat** | LangGraph-powered patient-facing chatbot with psychoeducation, general support, and human escalation |
| **Nirbaan AI Therapist** | Therapist-side AI assistant with RAG over clinical knowledge base |
| **AI Ladder Review** | Automated LLM analysis of fear ladder quality and clinical appropriateness |
| **Imaginal Script Generator** | LangGraph pipeline that drafts imaginal scripts from patient obsession data |
| **RAG Knowledge Base** | pgvector-backed retrieval-augmented generation over uploaded clinical resources |
| **Session Analysis** | Automatic post-session transcript analysis and SUDS scoring |

### Platform
| Feature | Description |
|---|---|
| **Video Calls** | WebRTC peer-to-peer video therapy sessions |
| **Live Transcription** | Real-time session audio transcription via Whisper |
| **Incoming Call Notifications** | WebSocket-based ring notification with Web Audio API ringtone |
| **Multi-role Auth** | JWT-based auth for Therapists, Patients, and Emergency Personnel |
| **Emergency Personnel** | Dedicated EP module with group chat and patient escalation |
| **Resource Library** | File-based clinical resource management (Cloudflare R2 / local) |
| **Mindfulness Player** | Built-in audio mindfulness session player |
| **E2EE Key Exchange** | Public-key infrastructure groundwork for end-to-end encrypted sessions |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Browser / Patient / Therapist        │
│                     React 19 + Vite + Zustand           │
└──────────────────────────┬──────────────────────────────┘
                           │ HTTPS / WSS
┌──────────────────────────▼──────────────────────────────┐
│              FastAPI (Python 3.11)                      │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│   │ Auth     │ │ ERP      │ │ NirbaanAI│ │ Sessions │  │
│   │ module   │ │ module   │ │ module   │ │ module   │  │
│   └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│   │ Fear     │ │ Chat     │ │ RAG      │ │ Celery   │  │
│   │ Ladder   │ │ module   │ │ pipeline │ │ Tasks    │  │
│   └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
└────────────┬──────────────────┬──────────────────────── ┘
             │                  │
   ┌──────────▼────────┐ ┌──────▼────────────┐
   │  PostgreSQL 16    │ │   Redis 7          │
   │  + pgvector       │ │   (Celery broker)  │
   └───────────────────┘ └────────────────────┘
```

---

## Folder Structure

```
Nirbaan- A Therapy Management Project/
│
├── backend/                   # FastAPI application
│   ├── app/
│   │   ├── auth/              # JWT authentication (therapist + patient)
│   │   ├── patients/          # Patient CRUD
│   │   ├── therapists/        # Therapist CRUD
│   │   ├── erp/               # ERP sessions, ERP Coach LangGraph agent
│   │   │   ├── ERPCoach/      # LangGraph agent (graph, nodes, state, LLM client)
│   │   │   └── voice/         # Voice transcription endpoint
│   │   ├── fear_ladder/       # Fear ladder CRUD
│   │   ├── education/         # Education modules (ERP, OCD, Fear Ladder, Relapse)
│   │   ├── NirbaanAIPatient/  # Patient AI chatbot (LangGraph)
│   │   ├── NirbaanAITherapist/# Therapist AI assistant
│   │   ├── ERPScriptGenerator/# Imaginal script LangGraph pipeline
│   │   ├── ai_ladder_review/  # AI fear ladder review pipeline
│   │   ├── ai_ladder_review_v2/ # RAG-enhanced ladder review
│   │   ├── chat/              # Therapist↔Patient, EP, EP Group chats
│   │   ├── therapy_sessions/  # Video session records
│   │   ├── live_sessions/     # WebSocket signaling + live transcription
│   │   ├── self_monitoring/   # Self-monitoring logs
│   │   ├── progress/          # Progress tracking
│   │   ├── patient_homework/  # Homework assignment + submission
│   │   ├── resources/         # Clinical resource file library
│   │   ├── intakes/           # Patient intake forms
│   │   ├── emergency_personnel/ # EP accounts and access
│   │   ├── users/             # Shared user utilities
│   │   ├── core/              # Celery app, config, shared utilities
│   │   ├── database/          # SQLAlchemy session and base
│   │   └── schemas/           # Shared Pydantic schemas
│   ├── requirements.txt
│   ├── Dockerfile
│   └── create_all_tables.py   # One-shot DB table creation script
│
├── frontend/                  # React 19 + Vite application
│   ├── src/
│   │   ├── pages/             # Full-page views (ERP, Fear Ladder, Chat, Video…)
│   │   ├── components/        # Reusable UI components
│   │   ├── dashboards/        # Therapist & Patient dashboards
│   │   ├── api/               # Axios API layer (per-module files)
│   │   ├── hooks/             # Custom React hooks
│   │   ├── store/             # Zustand global state
│   │   ├── auth/              # Auth context & guards
│   │   ├── routes/            # React Router v7 route definitions
│   │   └── utils/             # Shared utilities
│   ├── package.json
│   ├── Dockerfile
│   └── vite.config.js
│
├── mindfulness/               # Mindfulness audio assets
├── understanding/             # Auth workflow documentation
├── docker-compose.yml         # Full stack orchestration
└── .env.docker                # Docker environment template
```

---

## Tech Stack

### Backend
| Layer | Technology |
|---|---|
| Framework | FastAPI 0.110+ |
| ORM | SQLAlchemy 2 (async) |
| Database | PostgreSQL 16 + pgvector |
| Auth | JWT (python-jose) |
| AI Orchestration | LangGraph 0.2+, LangChain |
| LLM | OpenAI-compatible (configurable via `LLM_MODEL`) |
| Embeddings | OpenAI `text-embedding-3-small` |
| Task Queue | Celery 5 + Redis 7 |
| Audio | OpenAI Whisper API |
| File Storage | Cloudflare R2 / local filesystem |
| WebSockets | FastAPI native WebSocket |
| Containerisation | Docker + Docker Compose |

### Frontend
| Layer | Technology |
|---|---|
| Framework | React 19 |
| Build tool | Vite 7 |
| Routing | React Router v7 |
| State | Zustand 5 |
| HTTP | Axios |
| Charts | Recharts |
| Markdown | react-markdown |
| Styling | Plain CSS modules (per-component) |

---

## Prerequisites

- **Docker Desktop** 24+ (recommended for full stack)
- **Node.js** 20+ (local frontend dev)
- **Python** 3.11+ (local backend dev)
- **PostgreSQL** 16 with pgvector extension (local backend dev)
- **Redis** 7 (local Celery dev)
- An **OpenAI-compatible API key** (OpenAI, Groq, etc.) set as `OPENAI_API_KEY` / `LLM_MODEL`

---

## Quick Start (Docker)

```bash
# 1. Clone the repository
git clone <repo-url>
cd "Nirbaan- A Therapy Management Project"

# 2. Copy and fill the Docker environment file
copy .env.docker .env.docker   # already present — edit it with your keys

# 3. Build and start all services
docker compose up --build

# Services started:
#   http://localhost:8000  — FastAPI backend + Swagger UI (/docs)
#   http://localhost:5174  — React frontend (Nginx in Docker)
#   PostgreSQL on 5432 (internal)
#   Redis on 6379 (internal)
```

> **First run**: The backend startup command automatically runs `create_all_tables.py` and seeds the RAG taxonomy before accepting requests.

---

## Local Development

### Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/macOS

pip install -r requirements.txt

# Create the database tables
python create_all_tables.py

# Start the API server
uvicorn app.main:app --reload --port 8000
```

**Celery worker** (separate terminal):
```bash
celery -A app.core.celery_app worker --loglevel=info --pool=solo
```

**Celery beat** (separate terminal):
```bash
celery -A app.core.celery_app beat --loglevel=info
```

Or use the convenience scripts:
```bash
celery_worker.bat
celery_beat.bat
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Runs on http://localhost:5174
```

---

## Environment Variables

Create `backend/.env` (and `.env.docker` for Docker). Key variables:

```env
# ── Database ──────────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/nirbaan_db

# ── Redis ─────────────────────────────────────────────────
REDIS_URL=redis://localhost:6379/0

# ── Auth ──────────────────────────────────────────────────
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# ── LLM (primary — used by all AI modules) ────────────────
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4o                 # or any OpenAI-compatible model name

# ── Embeddings ────────────────────────────────────────────
EMBEDDING_MODEL=text-embedding-3-small

# ── LangSmith (optional tracing) ─────────────────────────
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__...
LANGCHAIN_PROJECT=nirbaan

# ── File Storage ──────────────────────────────────────────
# Cloudflare R2 (or leave blank for local storage)
R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME=
R2_PUBLIC_URL=

# ── Frontend (Vite) ───────────────────────────────────────
VITE_API_URL=http://localhost:8000
```

---

## Key API Modules

| Prefix | Module | Description |
|---|---|---|
| `/api/auth` | auth | Register, login, token refresh |
| `/api/patients` | patients | Patient CRUD |
| `/api/erp` | erp | ERP sessions, hierarchies, SUDS |
| `/api/erp/coach` | ERPCoach | LangGraph ERP Coach chat |
| `/api/erp/voice` | voice | Voice transcription → ERP response |
| `/api/fear-ladder` | fear_ladder | Fear ladder CRUD |
| `/api/education` | education | ERP, OCD, Fear Ladder, Relapse Prevention modules |
| `/api/nirbaan-ai` | NirbaanAIPatient | Patient AI chat (LangGraph) |
| `/api/nirbaan-ai-therapist` | NirbaanAITherapist | Therapist AI assistant |
| `/api/imaginal` | ERPScriptGenerator | Imaginal script generation |
| `/api/ai-ladder-review` | ai_ladder_review_v2 | AI fear ladder review |
| `/api/chat` | chat | Therapist↔Patient messaging |
| `/api/ep` | emergency_personnel | EP accounts and patient access |
| `/api/therapy-sessions` | therapy_sessions | Video session records + WebSocket signaling |
| `/api/resources` | resources | Clinical resource library |
| `/api/self-monitoring` | self_monitoring | Patient logs |
| `/api/progress` | progress | Weekly progress data |
| `/api/intakes` | intakes | Intake forms |
| `/api/homework` | patient_homework | Homework assignment + tracking |


---

## AI & LLM Subsystems

### ERP Coach (`backend/app/erp/ERPCoach/`)
A stateful LangGraph agent that guides patients through Exposure & Response Prevention exercises. Maintains session context, tracks SUDS levels, and provides Socratic coaching prompts.

### Nirbaan AI Patient (`backend/app/NirbaanAIPatient/`)
Multi-agent LangGraph pipeline with three specialised sub-agents:
- **GeneralSupportChatbot** — empathic general support
- **PsychoeducationChatbot** — OCD and anxiety psychoeducation
- **HumanEscalationAgent** — detects risk signals and escalates to therapist

### Imaginal Script Generator (`backend/app/ERPScriptGenerator/`)
LangGraph pipeline that receives a patient's obsession details and generates a clinically appropriate imaginal exposure script for therapist review.

### AI Ladder Review (`backend/app/ai_ladder_review_v2/`)
RAG-enhanced pipeline that evaluates a patient's fear ladder against clinical best practices, checking step gradation, SUDS spread, and clinical rationale.

### RAG Knowledge Base
pgvector is used to store and retrieve embeddings from the clinical resource library. Therapists can upload PDFs/text; the retriever augments AI responses with relevant passages.

---

## WebRTC Video Calls

- **Signaling**: FastAPI WebSocket at `/api/therapy-sessions/ws/signal/{session_id}`
- **Call notification**: Therapist triggers `incoming_call` WebSocket event to patient dashboard
- **Ringtone**: Web Audio API dual-tone ring (480 Hz + 620 Hz) — no audio file required
- **Transcription**: Live audio chunks sent to Whisper during session
- See [WEBRTC_COMPLETE_INTEGRATION.md](WEBRTC_COMPLETE_INTEGRATION.md) for full implementation notes

---

## Background Jobs (Celery)

Celery workers handle all long-running AI tasks to keep API responses fast:

| Task | Description |
|---|---|
| `run_ai_ladder_review` | Asynchronously runs AI analysis on a completed fear ladder |
| `generate_imaginal_script` | Background LangGraph script generation |
| `analyse_session_transcript` | Post-session transcript summarisation and SUDS extraction |
| `send_homework_reminder` | Scheduled homework reminder notifications |

---

## Federated QLoRA Fine-Tuning

Nirbaan includes a privacy-preserving fine-tuning pipeline that adapts **Meta-Llama-3.1-8B-Instruct** to the therapy domain using **QLoRA** (4-bit NF4 quantisation) inside a simulated federated learning setup.

---

## Contributing

1. Create a feature branch from `main`
2. Follow the existing module pattern: `models.py → schemas.py → router.py → service.py`
3. Add a corresponding frontend API file in `frontend/src/api/`
4. Ensure Docker build passes before opening a PR
