<div align="center">

# Nirbaan
### A Multi-Agent Platform for Therapist-Supervised OCD Therapy

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21220833.svg)](https://doi.org/10.5281/zenodo.21220833)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agentic_AI-FF6B35)](https://langchain-ai.github.io/langgraph/)

**Bridging the gap between therapy sessions with a supervised, multi-agent AI system.**

[Live Demo](https://nirbaan-frontend-6vu7.onrender.com) · [Report Bug](../../issues) · [Request Feature](../../issues)

</div>

---

## About

ERP (Exposure and Response Prevention) is the gold-standard treatment for OCD, but patients typically get less than an hour of clinical contact per week. Between sessions — when compulsive urges often peak — most digital tools fall short: logging apps don't offer real interaction, and general chatbots have no clinical state model, so they can't tell a genuine SUDS spike from a reassurance-seeking request, or know when a situation needs a human.

Nirbaan takes a different approach. Instead of one general-purpose chatbot, it runs a set of specialised LangGraph agents: a stateful ERP coach for live sessions, a RAG-powered detector that flags symptom patterns a therapist might miss, and a human-in-the-loop gate that requires therapist approval before any AI-generated clinical content — like an imaginal exposure script — ever reaches a patient.

---

## Repository Structure

```
Nirbaan-A-GenAI-Powered-Therapy-Management-Project/
│
├── backend/
│   ├── app/
│   │   ├── auth/                    # JWT auth: register/login for all 3 roles
│   │   ├── patients/                # Patient CRUD (therapist-scoped)
│   │   ├── therapists/              # Therapist CRUD
│   │   ├── emergency_personnel/     # EP accounts, group management
│   │   ├── erp/                     # ERP session lifecycle
│   │   │   └── ERPCoach/            # LangGraph ERP Coach (21 nodes, 7 live handlers)
│   │   │       ├── graph.py         # StateGraph definition + invoke_erp_coach()
│   │   │       ├── nodes/           # All LangGraph nodes
│   │   │       ├── prompts/         # Prompt builders per node
│   │   │       ├── llm/             # LLMClient with structured output + retry
│   │   │       ├── tasks/           # Celery: check-ins + end-session reports
│   │   │       └── services/        # CoachStorage DB helper
│   │   ├── fear_ladder/             # Fear ladder CRUD + ERP pairing
│   │   ├── ai_ladder_review_v2/     # RAG-enhanced hidden symptom detector
│   │   │   ├── ladder_review_agent/ # LangGraph agent
│   │   │   └── rag/                 # pgvector taxonomy retrieval
│   │   ├── NirbaanAIPatient/        # Patient chatbot + escalation pipeline
│   │   │   ├── CentralAgent/        # Top-level routing graph
│   │   │   └── HumanEscalationAgent/# Escalation sub-graph + EP group dispatch
│   │   ├── NirbaanAITherapist/      # Therapist RAG assistant
│   │   ├── ERPScriptGenerator/      # Imaginal script LangGraph + human-in-the-loop
│   │   │   ├── graph.py             # LangGraph with therapist-review interrupt
│   │   │   ├── ollama_client.py     # Fine-tuned SLM via Ollama
│   │   │   ├── piper_tts.py         # Text-to-speech synthesis
│   │   │   └── r2_storage.py        # Cloudflare R2 upload
│   │   ├── education/               # Personalised education agents
│   │   ├── chat/                    # All chat WebSocket endpoints + managers
│   │   ├── therapy_sessions/        # Video session records + Whisper transcription
│   │   ├── live_sessions/           # WebRTC WebSocket signaling
│   │   ├── self_monitoring/         # Daily OCD logs
│   │   ├── progress/                # Progress tracking + charts data
│   │   ├── patient_homework/        # Homework assignment + submission
│   │   ├── resources/               # Resource upload → R2 → Celery ingestion
│   │   ├── intakes/                 # Digital intake forms
│   │   ├── core/                    # Celery app, config, shared deps
│   │   └── database/                # SQLAlchemy session + base
│   ├── create_all_tables.py         # One-shot DB migration script
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── pages/                   # Full-page views (one per feature)
│   │   ├── components/              # Reusable UI (VideoCall, AudioRecorder, etc.)
│   │   ├── dashboards/              # TherapistDashboard, PatientDashboard
│   │   ├── api/                     # Axios API layer (one file per module)
│   │   ├── store/                   # Zustand global state
│   │   ├── auth/                    # Auth context, Login, Signup, guards
│   │   └── routes/                  # React Router v7 route definitions
│   ├── package.json
│   └── Dockerfile
│
├── FTSLM/                           # Federated QLoRA fine-tuning artifacts
│   ├── federated_QLoRA.ipynb        # Google Colab training notebook
│   └── Modelfile                    # Ollama model definition
│
├── mindfulness/                     # Mindfulness audio assets
├── docker-compose.yml               # Full stack orchestration
└── .env.docker                      # Docker environment template
```

---

## Core AI Agents

| Agent | Role |
|---|---|
| **Patient Chatbot** | Routes each message to psychoeducation, general support, or human escalation, grounded only in the treating therapist's uploaded resources |
| **ERP Coach** | A 21-node LangGraph state graph spanning live-session, debrief, and report-generation paths. Seven dedicated handlers manage scenarios like reassurance blocking, compulsion urges, avoidance, and SUDS spikes, and auto-generate a post-session clinical report |
| **Imaginal Script Generator** | Drafts exposure scripts with a fine-tuned local model, then pauses on a PostgreSQL-checkpointed LangGraph interrupt for mandatory therapist approval before anything reaches the patient |
| **Hidden Symptom Detector** | Cross-references self-monitoring logs against a pgvector-indexed OCD taxonomy to flag obsession–compulsion patterns missing from the fear ladder |
| **Education Agents** | Generate personalised OCD, fear-ladder, and relapse-prevention content, grounded in the therapist's knowledge base with a web-search fallback |
| **Proactive Check-in Agent** | Celery Beat task that checks active sessions and inactive patients on a schedule, without clinician action |

---

## Features

- Full ERP session lifecycle: creation, live AI-coached session, SUDS tracking, debrief, clinical report
- Fear ladder builder, daily self-monitoring logs, homework assignment/submission, weekly progress tracking
- WebRTC video sessions with live transcription and post-session AI analysis
- Role-based access (Therapist / Patient / Emergency Personnel) with JWT auth and bcrypt hashing
- Emergency personnel accounts can only be created by the supervising therapist, so every escalation alert goes to a clinician-vetted responder
- Therapist-scoped resource library (PDF/text → chunking → embeddings → pgvector) powering all RAG agents
- Experimental federated QLoRA pipeline: fine-tunes Meta-Llama-3.1-8B-Instruct across simulated clinics via Flower, without centralising raw patient data, exported to Ollama for local inference

---

## Tech Stack

| Layer | Technologies |
|---|---|
| Backend | FastAPI, SQLAlchemy 2.x, PostgreSQL 16 + pgvector, LangGraph, LangChain, Celery + Redis, Piper TTS, Cloudflare R2 |
| AI/ML | OpenAI-compatible LLM API, `text-embedding-3-large`, Ollama (local fine-tuned SLM), Flower, PEFT/QLoRA, TRL |
| Frontend | React 19, Vite, React Router, Zustand, Axios, Recharts |
| Infra | Docker, Docker Compose, WebSockets, WebRTC |

---

## Prerequisites

| Dependency | Minimum version |
|---|---|
| Python | 3.10+ |
| Node.js | 18+ |
| PostgreSQL (with pgvector) | 16 |
| Redis | 7 |
| Ollama | 0.3+ |
| Docker + Docker Compose (optional, for containerised setup) | 24+ / v2+ |
| OpenAI API key | — |

---

## Installation — Docker (recommended)

```bash
git clone https://github.com/tahmidalbi/Nirbaan-A-GenAI-Powered-Therapy-Management-Project
cd Nirbaan-A-GenAI-Powered-Therapy-Management-Project

# 1. Configure your API keys and DB credentials in .env.docker

# 2. Register the fine-tuned local model
ollama create nirbaan-erp-federated -f FTSLM/Modelfile

# 3. Build and start the full stack
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:5174 |
| Backend API | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |

---

## Installation — Local Development

Use this if you want to run each service directly on your machine instead of in containers.

### 1. Backend

```bash
cd backend

# Create and activate a virtual environment
python -m venv venv
.\venv\Scripts\activate          # Windows PowerShell
# source venv/bin/activate       # macOS / Linux

# Install dependencies
pip install -r requirements.txt

# Set up PostgreSQL
psql -U postgres -c "CREATE DATABASE nirbaan_db;"
psql -U postgres -d nirbaan_db -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Configure environment variables
copy .env.example .env    # then fill in DATABASE_URL, REDIS_URL, SECRET_KEY, OPENAI_API_KEY, etc.

# Run database migrations
python create_all_tables.py

# Seed the OCD taxonomy used by the Hidden Symptom Detector
python -m app.ai_ladder_review_v2.rag.taxonomy_seed

# Start the API server
uvicorn app.main:app --reload --port 8000
```

### 2. Celery worker (background AI tasks — open a second terminal)

```bash
cd backend
.\venv\Scripts\activate
celery -A app.core.celery_app worker --loglevel=info --pool=solo --concurrency=4
```

### 3. Celery Beat (scheduled proactive check-ins — open a third terminal)

```bash
cd backend
.\venv\Scripts\activate
celery -A app.core.celery_app beat --loglevel=info
```

### 4. Ollama (local model for the Imaginal Script Generator)

```bash
# Install from https://ollama.com if not already installed
ollama create nirbaan-erp-federated -f FTSLM/Modelfile
ollama list   # should show nirbaan-erp-federated
```

Then set in `backend/.env`:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=nirbaan-erp-federated
```

If you'd rather skip local model hosting, set `OLLAMA_BASE_URL=http://disabled` — every other feature still works; only imaginal script generation will be unavailable.

### 5. Frontend

```bash
cd frontend
npm install
npm run dev
# Runs on http://localhost:5174, proxies /api/* to http://localhost:8000
```

Make sure the backend is running first.

### 6. Create your first account

Open http://localhost:5174, click **Sign Up**, and register as a therapist. You'll be redirected straight to the Therapist Dashboard.

---

## Citation

If you use this software in your research, please cite:

> Das AM, Islam MT, Abdullah AN, Shuvo MB. *tahmidalbi/Nirbaan-A-GenAI-Powered-Therapy-Management-Project: Nirbaan v1.0*. Zenodo; 2026. doi:10.5281/zenodo.21220833

A citation to the accompanying SoftwareX article will be added here upon publication.

---

## License

MIT — see [LICENSE](LICENSE) for details.

## Support & Contributing

Questions, bugs, or feature requests: open an [issue](../../issues) or email das2107118@stud.kuet.ac.bd.

---

<div align="center">

Built to ensure no patient faces their anxiety alone.

</div>
