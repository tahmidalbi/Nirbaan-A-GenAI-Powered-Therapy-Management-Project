<div align="center">

# Nirbaan — AI-Powered Therapy Management Platform

[![Live Demo](https://img.shields.io/badge/Live%20Demo-nirbaan--frontend-4CAF50?style=for-the-badge&logo=render&logoColor=white)](https://nirbaan-frontend-6vu7.onrender.com)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agentic_AI-FF6B35?style=for-the-badge)](https://langchain-ai.github.io/langgraph/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+pgvector-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

**Bridging the gap between therapy sessions with production-grade Agentic AI.**

[Live Demo](https://nirbaan-frontend-6vu7.onrender.com) · [Report Bug](../../issues) · [Request Feature](../../issues)

</div>

---

## The Problem We Are Solving

Mental health therapy — particularly for OCD and anxiety — requires consistent support. But **between weekly sessions, patients are on their own**. A spike in anxiety, an intrusive thought, a moment of crisis: the therapist is unreachable and the patient has nowhere to turn.

Nirbaan solves this by deploying a network of **specialised AI agents** that remain active 24/7 between sessions:

- Patients get **therapist-grounded AI support** at any hour, through a chatbot that only knows what their own therapist has uploaded — not the open internet.
- If the situation escalates, the AI **autonomously hands off to a human emergency helper** in real time.
- On the therapist's side, every AI interaction feeds into a **Clinical Decision Support System** that surfaces hidden symptom patterns the therapist might otherwise miss.
- During homework (ERP exercises), a dedicated **AI coach** guides the patient step-by-step and automatically submits a **clinical report** to the therapist when the session ends.
- A scheduled background agent **proactively checks on inactive patients** — no patient goes silent without the system noticing.

---

## Table of Contents

- [The Problem We Are Solving](#the-problem-we-are-solving)
- [Core Architecture](#core-architecture)
- [Feature Overview](#feature-overview)
  - [Agentic AI Subsystems](#-agentic-ai-subsystems)
  - [Clinical Workflows](#-clinical-workflows)
  - [Real-Time Communication](#-real-time-communication)
  - [Security & Authentication](#-security--authentication)
  - [Background Intelligence](#-background-intelligence)
  - [Federated QLoRA Fine-Tuning](#-federated-qlora-fine-tuning)
- [Deep-Dive: AI Agent Architectures](#deep-dive-ai-agent-architectures)
  - [Patient AI Agent — NirbaanAIPatient](#1-patient-ai-agent--nirbaanaipatient)
  - [ERP Coach Agent](#2-erp-coach-agent)
  - [Imaginal Script Generator](#3-imaginal-script-generator-with-human-in-the-loop)
  - [Hidden Symptom Detector — AI Ladder Review](#4-hidden-symptom-detector--ai-ladder-review-v2)
  - [RAG Knowledge Base](#5-rag-knowledge-base-pgvector)
  - [Education Agents](#6-education-agents)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Quick Start — Docker (Recommended)](#quick-start--docker-recommended)
- [Local Development](#local-development)
- [Ollama Local Model Setup](#ollama-local-model-setup)
- [Environment Variables Reference](#environment-variables-reference)
- [API Reference](#api-reference)
- [Federated QLoRA — Research Background](#federated-qlora--research-background)
- [Contributing](#contributing)

---

## Core Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        Browser  (React 19 + Vite)                        │
│          Therapist Dashboard  │  Patient Dashboard  │  EP Dashboard       │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │  HTTPS / WSS
┌───────────────────────────────▼──────────────────────────────────────────┐
│                           FastAPI  (Python 3.11)                          │
│                                                                            │
│  ┌────────────┐  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │   Auth     │  │  ERP /      │  │  NirbaanAI   │  │  Therapy        │  │
│  │   JWT      │  │  Sessions   │  │  Patient +   │  │  Sessions +     │  │
│  │            │  │             │  │  Therapist   │  │  WebRTC Signal  │  │
│  └────────────┘  └─────────────┘  └──────────────┘  └─────────────────┘  │
│  ┌────────────┐  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │   Fear     │  │  Imaginal   │  │  AI Ladder   │  │  Education      │  │
│  │   Ladder   │  │  Script Gen │  │  Review v2   │  │  Agents (RAG)   │  │
│  └────────────┘  └─────────────┘  └──────────────┘  └─────────────────┘  │
│  ┌────────────┐  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │  Resource  │  │  Chat       │  │  Emergency   │  │  Celery Tasks   │  │
│  │  Library   │  │  WebSockets │  │  Personnel   │  │  (Beat + Worker)│  │
│  └────────────┘  └─────────────┘  └──────────────┘  └─────────────────┘  │
└───────────────────┬─────────────────────┬────────────────────────────────┘
                    │                     │
         ┌──────────▼──────┐    ┌─────────▼───────────┐
         │  PostgreSQL 16  │    │      Redis 7         │
         │  + pgvector     │    │  Celery broker +     │
         │  (embeddings)   │    │  result backend      │
         └─────────────────┘    └─────────────────────┘
                    │
         ┌──────────▼──────────────┐
         │  Ollama (host machine)  │
         │  nirbaan-erp-federated  │
         │  (QLoRA fine-tuned LLM) │
         └─────────────────────────┘
```

---

## Feature Overview

### 🤖 Agentic AI Subsystems

| Agent | Role | Tech |
|---|---|---|
| **NirbaanAI Patient Chatbot** | 24/7 patient support grounded on therapist-uploaded resources; autonomously escalates to human helpers when needed | LangGraph multi-agent, RAG, OpenAI |
| **ERP Coach Agent** | Guides patients through live ERP homework sessions; handles reassurance blocks, compulsion urges, SUDS spikes, and avoidance; generates clinical post-session reports | LangGraph StateGraph, 7 specialised nodes |
| **Imaginal Script Generator** | Generates personalised imaginal exposure scripts using a fine-tuned local SLM, with a human-in-the-loop therapist review gate | LangGraph + PostgreSQL checkpointer + Ollama |
| **Hidden Symptom Detector** | RAG-powered clinical analysis of the patient's fear ladder vs. self-monitoring logs to surface obsession-compulsion pairs the therapist may have missed | LangGraph, pgvector RAG, OCD taxonomy |
| **OCD Core Education Agent** | Generates personalised OCD psychoeducation content for patients, grounded in the therapist's knowledge base with Tavily web fallback | LangGraph, RAG, Tavily |
| **Fear Ladder Education Agent** | Generates personalised fear ladder explanation and theory pages for patients | LangGraph, RAG |
| **NirbaanAI Therapist Assistant** | Clinical decision support: answers therapist questions about patients using RAG over clinical notes and knowledge base | LangChain RAG, pgvector |
| **Proactive Check-in Agent** | Celery Beat fires this agent every 5 minutes during active ERP sessions to check patient engagement, detect SUDS spikes, and send targeted prompts without human intervention | Celery Beat + LangGraph |

---

### 🏥 Clinical Workflows

| Feature | Description |
|---|---|
| **ERP Session Lifecycle** | Full Exposure & Response Prevention sessions: create exposure item, run live session with AI coach, submit SUDS ratings, receive debrief, generate clinical report |
| **Fear Ladder Management** | Build, edit, and track hierarchical fear ladders with SUDS scores, linked obsessions/compulsions, and step-by-step progression |
| **Imaginal Exposure Scripts** | AI drafts vivid imaginal scripts from patient case data; therapist approves or rejects with feedback (revision loop); approved scripts synthesised to audio via Piper TTS and stored in Cloudflare R2 |
| **Self-Monitoring Logs** | Daily patient OCD/anxiety tracking with timestamped obsession, compulsion, and SUDS entries |
| **Patient Intake Forms** | Structured digital intake capturing diagnosis, history, and presenting concerns |
| **Patient Homework** | Therapist assigns homework tasks; patients complete and submit; AI coach assists during execution |
| **Progress Tracking** | Visual weekly progress charts with trend analysis across SUDS, session frequency, and homework completion |
| **Relapse Prevention** | AI-generated psychoeducation modules for relapse prevention, tailored per patient |
| **Clinical Resource Library** | Therapists upload PDFs, articles, and clinical guides; system ingests, chunks, embeds, and indexes them for RAG retrieval |
| **Mindfulness Player** | Built-in audio mindfulness sessions for patient self-care between appointments |

---

### 📡 Real-Time Communication

| Feature | Description |
|---|---|
| **WebRTC Video Calls** | Peer-to-peer video therapy sessions over WebRTC, mediated by a FastAPI WebSocket signaling server |
| **Incoming Call Notifications** | WebSocket push notification with a Web Audio API dual-tone ringtone (480 Hz + 620 Hz) when a therapist initiates a session |
| **Live Whisper Transcription** | Session audio is chunked and sent to OpenAI Whisper in real time; transcripts are stored and used for post-session AI analysis |
| **Therapist ↔ Patient Chat** | Real-time WebSocket-based direct messaging between therapist and patient |
| **EP ↔ Patient Direct Chat** | Emergency personnel can open a direct chat session with any assigned patient in real time |
| **EP Group Chat** | All emergency personnel in a therapist's team share a live group channel; the AI agent broadcasts escalation alerts directly into this channel |
| **Human Escalation via AI** | When a patient's message triggers the escalation path, the Patient AI agent writes a structured alert into the EP group chat via WebSocket broadcast — all helpers are notified within milliseconds |

---

### 🔐 Security & Authentication

| Feature | Description |
|---|---|
| **JWT Authentication** | Access tokens for all three roles (Therapist, Patient, Emergency Personnel); tokens carry role claims and are validated on every protected route |
| **Role-Based Access Control** | Therapists register and manage their own patients; patients cannot self-register; each role has strictly scoped API access |
| **Password Hashing** | All passwords hashed with bcrypt (cost factor 12) via passlib; plaintext is never stored |
| **Multi-tenant Isolation** | All database queries are scoped by `therapist_id`; a therapist can never access another therapist's patient data |
| **E2EE Public Key Infrastructure** | Database columns for public-key exchange are in place as groundwork for end-to-end encrypted messaging |
| **WebSocket Auth** | Every WebSocket connection validates the JWT token before accepting; invalid or mismatched tokens are rejected with a 4003/4004 close code |

---

### ⚙️ Background Intelligence

| Celery Task | Trigger | Description |
|---|---|---|
| `dispatch_due_checkins` | Every 60 s (Beat) | Scans all running ERP sessions; dispatches `run_checkin` for any session idle longer than 5 minutes |
| `run_checkin` | Dispatched by above | Invokes the ERP Coach LangGraph agent with `event_type=CHECK_IN`; sends SUDS reminder, spike alert, or stays silent based on computed metrics |
| `run_end_session_report` | Patient ends session | Runs the report path of the ERP Coach graph; produces a structured therapist report + patient feedback JSON and saves to DB |
| `generate_ocd_core_education_task` | Patient requests education | Runs the OCD Core Education LangGraph agent in a Celery worker; updates DB status from `queued → running → completed` |
| `generate_fear_ladder_education_task` | Patient requests education | Fear Ladder education generation pipeline |
| `ingest_resource_task` | Therapist uploads resource | Downloads file from R2, chunks text, generates OpenAI embeddings, stores in pgvector |

---

### 🔬 Federated QLoRA Fine-Tuning

Nirbaan includes a research-grade federated learning pipeline that fine-tunes **Meta-Llama-3.1-8B-Instruct** on OCD imaginal exposure therapy data using **QLoRA** (4-bit quantisation) inside a privacy-preserving **Flower federated simulation**. The resulting model powers the Imaginal Script Generator via Ollama. See the [full research background](#federated-qlora--research-background) section for details.

---

## Deep-Dive: AI Agent Architectures

### 1. Patient AI Agent — NirbaanAIPatient

The patient-facing chatbot is not a single model call. It is a **multi-agent LangGraph pipeline** with a central routing brain.

```
Patient message
      │
      ▼
[CentralAgent Router]  ←── cheap LLM (gpt-4o-mini) classifies intent
      │
      ├─ "psychoeducation"  ──►  PsychoeducationChatbot (RAG over therapist KB)
      │
      ├─ "support"          ──►  GeneralSupportChatbot  (empathic counselling)
      │
      └─ "human_escalation" ──►  HumanEscalationAgent
                                         │
                                    [load_context]  ← patient profile, ERP history
                                         │
                                    [LLM verifier]  ← "does this REALLY need a human?"
                                         │
                                    YES  │  NO
                                         │
                               [generate_helper_message]
                                         │
                               [send_to_ep_group]  ← WebSocket broadcast to all EPs
```

**Key properties:**
- The chatbot only knows what the therapist has uploaded to the knowledge base. It cannot access the open internet.
- The `HumanEscalationAgent` has a second LLM "verifier" node that prevents false escalations. Only genuine distress triggers the alert.
- The EP group alert is a structured clinical message that includes patient context, current concern, and suggested action — not a raw chat message.
- The `is_escalation` flag is returned to the frontend so the patient UI can show a confirmation that help is on the way.

---

### 2. ERP Coach Agent

The ERP Coach is a **9-node LangGraph StateGraph** that manages the entire lifecycle of a live ERP session.

```
START → load_context → compute_metrics → [mode_router]
                                               │
               ┌───────────────┬───────────────┘
               │               │               │
           LIVE path      DEBRIEF path    REPORT path
               │               │               │
           log_user      debrief_prompt    report_bundle
               │               │               │
    [live_intent_router]  finalize      report_facts (LLM)
               │               │               │
    ┌──────────┴──────┐   log_debrief   report_therapist (LLM)
    │                 │                        │
7 handler nodes    END                 report_patient (LLM)
(LLM-powered)                                  │
    │                                    finalize_reports
    ▼                                          │
finalize_coach_live → log_coach → END      save_reports → END
```

**The 7 LIVE handler nodes** each specialise in a different therapeutic scenario:

| Handler | Triggers on |
|---|---|
| `live_general` | Normal patient message |
| `live_reassurance` | Patient seeking reassurance (intentionally blocked in ERP) |
| `live_urge` | Patient reports compulsion urge |
| `live_quit` | Patient wants to stop the exposure |
| `live_rate_reminder` | Patient hasn't submitted SUDS in 5 minutes |
| `live_spike` | SUDS jumped ≥15 points or slope ≥8 pts/min |
| `live_no_message` | Celery check-in during active/engaged session — stay silent |

**After every session**, the REPORT path fires automatically via Celery. Three sequential LLM calls produce:
1. A factual compression of the session transcript
2. A structured `TherapistReportJSON` (clinical summary, SUDS trend, recommendations)
3. A `PatientFeedbackJSON` (motivational debrief sent to the patient)

---

### 3. Imaginal Script Generator with Human-in-the-Loop

This agent demonstrates production-grade **LangGraph Human-in-the-Loop** via PostgreSQL checkpointing.

```
POST /imaginal-generator/start
        │
   [load_case_context]  ← patient obsession, compulsion, feared consequence
        │
   [build_prompt_node]  ← GPT-5.2 prompt engineer (normalises + enriches)
        │
   [generate_script_node] ← fine-tuned Ollama SLM (nirbaan-erp-federated)
        │
   [therapist_review_node] ← ─────── INTERRUPT ────────────────────────────┐
        │                                                                    │
   Graph state FROZEN in PostgreSQL.                                         │
   HTTP response returned with script_text.                                 │
   Therapist reads it...                                                     │
                                                                            │
POST /imaginal-generator/review  {approved: true / false, feedback: "..."}  │
        │                                                                    │
   Graph RESUMES from frozen checkpoint ◄───────────────────────────────────┘
        │
   ┌────┴─────────────────────────────────────────────────────┐
   │ APPROVED                                                 │ REJECTED
   ▼                                                          ▼
[finalize_approved_node]                          [prepare_revision_node]
        │                                                     │
   Piper TTS synthesis                              version++ │
        │                                                     ▼
   Upload audio to Cloudflare R2                    back to [build_prompt_node]
        │                                           (therapist_feedback in state)
   Patient can play audio
```

**Why this matters:** The server can restart between the two HTTP requests and the graph resumes correctly, because its entire state is persisted to PostgreSQL. This is not simulation — it is production-ready stateful AI.

---

### 4. Hidden Symptom Detector — AI Ladder Review v2

This is the therapist's clinical decision support eye. It runs automatically after each self-monitoring batch and answers:

> *"Is there an obsession-compulsion pattern in this patient's behaviour that is NOT listed on their current fear ladder?"*

```
[load_context]         ← patient intake, ladder items, 14-day log entries
      │
[ladder_extractor]     ← LLM normalises ladder into structured items
      │
[create_batches]       ← splits log entries into manageable chunks
      │
[taxonomy_retriever]   ← pgvector RAG over OCD taxonomy (150+ subtypes)
      │
[symptom_finder]       ← LLM extracts obsession-compulsion candidates from log batch
      │
[checker]              ← LLM: "was this analysis complete? should we re-examine?"
      │ ← recheck loop if needed
[hidden_matcher]       ← LLM: "which candidates are genuinely MISSING from the ladder?"
      │
[finalizer]            ← writes result to DB, marks review complete
```

The therapist sees a structured list of **hidden symptom flags** with clinical descriptions and the source log entries that triggered each flag. This operates entirely without therapist input — it runs as a background clinical audit.

---

### 5. RAG Knowledge Base (pgvector)

The knowledge base is the foundation of all patient-facing and therapist-facing AI. Without it, no AI agent has access to clinical context.

**Ingestion pipeline:**

```
Therapist uploads PDF/TXT
        │
FastAPI receives file → saves to Cloudflare R2
        │
Celery task: ingest_resource_task
        │
   [Download from R2]
        │
   [PyPDF / text load]
        │
   [RecursiveCharacterTextSplitter → 800-char chunks with 100-char overlap]
        │
   [OpenAI text-embedding-3-large → 1536-dim vectors]
        │
   [Batch insert into PostgreSQL pgvector table]
        │
Resource status → "completed" — ready for RAG retrieval
```

**Retrieval at query time:**

All RAG-powered agents (NirbaanAI Patient, Therapist Assistant, Education Agents) embed the user query, run a cosine similarity search against the therapist's knowledge base (filtered by `therapist_id`), and inject the top-k chunks into the LLM prompt with source citations.

---

### 6. Education Agents

Three separate LangGraph agents generate **personalised educational content** for patients:

| Agent | Content | Fallback |
|---|---|---|
| **OCD Core Education** | Nature of OCD, obsessions, compulsions, the OCD cycle, ERP model, cognitive distortions, subtypes | KB retrieval → KB quality judge → Tavily web search if KB insufficient |
| **Fear Ladder Education** | What a fear ladder is, how exposure hierarchies work, SUDS, step structure | KB retrieval → web fallback |
| **Relapse Prevention** | Warning signs, coping strategies, maintenance ERP | KB retrieval |

Content is **cached per patient** in the database after first generation. Patients can regenerate with a single button click.

---

## Project Structure

```
Nirbaan- A Therapy Management Project/
│
├── backend/
│   ├── app/
│   │   ├── auth/                    # JWT auth: register/login for all 3 roles
│   │   ├── patients/                # Patient CRUD (therapist-scoped)
│   │   ├── therapists/              # Therapist CRUD
│   │   ├── emergency_personnel/     # EP accounts, group management
│   │   ├── erp/                     # ERP session lifecycle
│   │   │   ├── ERPCoach/            # LangGraph ERP Coach (9 nodes, 7 handlers)
│   │   │   │   ├── graph.py         # StateGraph definition + invoke_erp_coach()
│   │   │   │   ├── nodes/           # All LangGraph nodes
│   │   │   │   ├── prompts/         # Prompt builders per node
│   │   │   │   ├── llm/             # LLMClient with structured output + retry
│   │   │   │   ├── tasks/           # Celery: check-ins + end-session reports
│   │   │   │   └── services/        # CoachStorage DB helper
│   │   ├── fear_ladder/             # Fear ladder CRUD + ERP pairing
│   │   ├── ai_ladder_review/        # v1 ladder review
│   │   ├── ai_ladder_review_v2/     # v2: RAG-enhanced hidden symptom detector
│   │   │   ├── ladder_review_agent/ # LangGraph agent (8 nodes)
│   │   │   └── rag/                 # pgvector taxonomy retrieval
│   │   ├── NirbaanAIPatient/        # Patient chatbot + escalation pipeline
│   │   │   ├── CentralAgent/        # Top-level routing graph
│   │   │   ├── HumanEscalationAgent/# Escalation sub-graph + EP group dispatch
│   │   │   └── chat_service.py      # Chat entry point
│   │   ├── NirbaanAITherapist/      # Therapist RAG assistant
│   │   ├── ERPScriptGenerator/      # Imaginal script LangGraph + HiTL
│   │   │   ├── graph.py             # 6-node LangGraph with interrupt
│   │   │   ├── ollama_client.py     # Fine-tuned SLM via Ollama
│   │   │   ├── gemini_builder.py    # GPT prompt normaliser
│   │   │   ├── piper_tts.py         # Text-to-speech synthesis
│   │   │   └── r2_storage.py        # Cloudflare R2 upload
│   │   ├── education/               # Personalised education agents
│   │   │   ├── ocd_core/            # OCD core education LangGraph
│   │   │   ├── fear_ladder/         # Fear ladder education LangGraph
│   │   │   └── relapse_prevention/  # Relapse prevention agent
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
│   ├── vite.config.js
│   └── Dockerfile
│
├── FTSLM/                           # Federated QLoRA fine-tuning artifacts
│   ├── federated_QLoRA.ipynb        # Google Colab training notebook
│   └── Modelfile                    # Ollama model definition
│
├── mindfulness/                     # Mindfulness audio assets
├── docker-compose.yml               # Full stack orchestration
├── .env.docker                      # Docker environment template
└── start_backend.bat / start_frontend.bat
```

---

## Tech Stack

### Backend

| Category | Technology | Version |
|---|---|---|
| API Framework | FastAPI | 0.110+ |
| ORM | SQLAlchemy | 2.x |
| Database | PostgreSQL + pgvector | 16 |
| Auth | python-jose (JWT) + passlib (bcrypt) | — |
| AI Orchestration | LangGraph | 0.2+ |
| LLM Abstraction | LangChain + LangChain-OpenAI | 1.2+ |
| LLM Inference | OpenAI-compatible API | configurable |
| Local SLM | Ollama (`nirbaan-erp-federated`) | 0.3+ |
| Embeddings | OpenAI `text-embedding-3-large` | — |
| Task Queue | Celery + Redis | 5.x / 7 |
| Audio Transcription | OpenAI Whisper API | — |
| Text-to-Speech | Piper TTS | — |
| File Storage | Cloudflare R2 (S3-compatible) | — |
| WebSockets | FastAPI native | — |
| Containerisation | Docker + Docker Compose | — |

### Frontend

| Category | Technology | Version |
|---|---|---|
| Framework | React | 19 |
| Build Tool | Vite | 7 |
| Routing | React Router | v7 |
| State Management | Zustand | 5 |
| HTTP Client | Axios | — |
| Charts | Recharts | — |
| Markdown Rendering | react-markdown | — |
| Video/Audio | WebRTC (browser native) + MediaRecorder API | — |
| Styling | CSS Modules (per-component) | — |

---

## Prerequisites

| Dependency | Minimum Version | Purpose |
|---|---|---|
| Docker Desktop | 24+ | Full stack Docker run |
| Docker Compose | v2+ | Bundled with Docker Desktop |
| Node.js | 20+ | Local frontend development |
| Python | 3.11+ | Local backend development |
| PostgreSQL | 16 (with pgvector) | Local backend development |
| Redis | 7 | Local Celery broker |
| Ollama | 0.3+ | Local SLM for Imaginal Script Generator |
| OpenAI API key | — | LLM inference + embeddings |

---

## Quick Start — Docker (Recommended)

> **All services — backend, frontend, PostgreSQL, Redis, Celery worker, Celery beat — start with a single command.**

### Step 1 — Clone & configure

```bash
git clone <repo-url>
cd "Nirbaan- A Therapy Management Project"
```

Edit `.env.docker` with your API keys (see the [Environment Variables Reference](#environment-variables-reference) section below for the full list). The file is already present in the repository with placeholder values.

### Step 2 — Start Ollama on the host (for Imaginal Script Generator)

```bash
# Install Ollama from https://ollama.com if not already installed

# Register the fine-tuned model
ollama create nirbaan-erp-federated -f FTSLM/Modelfile

# Verify
ollama list
# Should show: nirbaan-erp-federated
```

> On Windows and macOS, Docker containers reach the host machine at `host.docker.internal`. The `docker-compose.yml` already configures this. Set `OLLAMA_BASE_URL=http://host.docker.internal:11434` in `.env.docker`.

### Step 3 — Build and run

```bash
docker compose up --build
```

On first run the backend container will:
1. Run `create_all_tables.py` — creates all PostgreSQL tables
2. Run `taxonomy_seed` — seeds the OCD taxonomy into pgvector for the Hidden Symptom Detector
3. Start the FastAPI server on port 8000

| Service | URL |
|---|---|
| Frontend (React via Nginx) | http://localhost:5174 |
| Backend API | http://localhost:8000 |
| Swagger / OpenAPI docs | http://localhost:8000/docs |

### Step 4 — Create your first therapist account

1. Open http://localhost:5174
2. Click **Sign Up** on the landing page
3. Fill in name, email, password, license number, and specialty
4. You are automatically logged in and redirected to the Therapist Dashboard

---

## Local Development

### Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate          # Windows PowerShell
# source venv/bin/activate        # macOS / Linux

# Install dependencies
pip install -r requirements.txt

# Set up PostgreSQL
# 1. Make sure PostgreSQL 16 is running
# 2. Create the database:
#    psql -U postgres -c "CREATE DATABASE nirbaan_db;"
# 3. Enable pgvector:
#    psql -U postgres -d nirbaan_db -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Copy and edit the environment file
copy .env.example .env    # then fill in your values

# Run database migrations
python create_all_tables.py

# Seed the OCD taxonomy for the RAG-based Hidden Symptom Detector
python -m app.ai_ladder_review_v2.rag.taxonomy_seed

# Start the API server
uvicorn app.main:app --reload --port 8000
```

**Celery Worker** (open a second terminal — required for background AI tasks):

```bash
cd backend
.\venv\Scripts\activate
celery -A app.core.celery_app worker --loglevel=info --pool=solo --concurrency=4
# Or use the convenience script:
celery_worker.bat
```

**Celery Beat Scheduler** (open a third terminal — required for proactive patient check-ins):

```bash
cd backend
.\venv\Scripts\activate
celery -A app.core.celery_app beat --loglevel=info
# Or:
celery_beat.bat
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Runs on http://localhost:5174
```

> The frontend proxies `/api/*` requests to `http://localhost:8000`. Ensure the backend is running first.

---

## Ollama Local Model Setup

The **Imaginal Script Generator** uses a locally fine-tuned LLM served by Ollama. This is separate from the cloud LLM used by all other agents.

### Install Ollama

Download from [https://ollama.com](https://ollama.com) and install for your OS. Ollama starts automatically as a background service on most systems.

### Register the fine-tuned model

```bash
# From the project root
ollama create nirbaan-erp-federated -f FTSLM/Modelfile

# Verify registration
ollama list
# Expected output includes: nirbaan-erp-federated
```

### Test the model

```bash
ollama run nirbaan-erp-federated "Write a brief imaginal exposure script for contamination OCD."
```

### Configure the backend to use it

Add these to your `backend/.env` (or `.env.docker`):

```env
OLLAMA_BASE_URL=http://localhost:11434          # local development
# OLLAMA_BASE_URL=http://host.docker.internal:11434  # when running inside Docker
OLLAMA_MODEL=nirbaan-erp-federated
```

> **If you do not want to run Ollama**, set `OLLAMA_BASE_URL=http://disabled`. All other platform features will work normally; only imaginal script generation will be unavailable.

---

## Environment Variables Reference

Create `backend/.env` for local development. Use `.env.docker` for Docker Compose. All required variables are listed below.

```env
# ── Database ───────────────────────────────────────────────────────────────────
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/nirbaan_db
# Docker:
# DATABASE_URL=postgresql://postgres:2021@db:5432/nirbaan_db

# ── Redis ─────────────────────────────────────────────────────────────────────
REDIS_URL=redis://localhost:6379/0
# Docker:
# REDIS_URL=redis://redis:6379/0

# ── Authentication ─────────────────────────────────────────────────────────────
SECRET_KEY=your-very-long-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# ── Primary LLM (used by ALL AI agents) ──────────────────────────────────────
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4o                     # any OpenAI-compatible model name
EMBEDDING_MODEL=text-embedding-3-large

# ── Local SLM (Imaginal Script Generator only) ────────────────────────────────
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=nirbaan-erp-federated

# ── Web Search Fallback for Education Agents (optional) ───────────────────────
TAVILY_API_KEY=tvly-...

# ── Cloudflare R2 File Storage ────────────────────────────────────────────────
# Leave blank to use local filesystem storage instead
R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME=nirbaan-resources
R2_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
R2_PUBLIC_URL=

# ── LangSmith Tracing (optional, recommended for development) ────────────────
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__...
LANGCHAIN_PROJECT=nirbaan

# ── Frontend (Vite build arg — not used at runtime) ──────────────────────────
VITE_API_URL=http://localhost:8000
```

---

## API Reference

All routes are prefixed with `/api/`. Interactive documentation is available at `http://localhost:8000/docs` (Swagger UI) and `http://localhost:8000/redoc`.

| Route Prefix | Module | Description |
|---|---|---|
| `/auth` | auth | Register (therapist), login (all roles), token operations |
| `/patients` | patients | Patient CRUD — therapist-scoped |
| `/therapists` | therapists | Therapist profile |
| `/emergency-personnel` | emergency_personnel | EP accounts, group management |
| `/erp` | erp | ERP session lifecycle, SUDS ratings, exposure hierarchies |
| `/erp/coach` | ERPCoach | LangGraph ERP Coach WebSocket + REST |
| `/fear-ladder` | fear_ladder | Fear ladder CRUD + OCD pairing |
| `/ai-ladder-review` | ai_ladder_review_v2 | Trigger and retrieve hidden symptom analysis |
| `/nirbaan-ai/patient` | NirbaanAIPatient | Patient AI chatbot (LangGraph) |
| `/nirbaan-ai/therapist` | NirbaanAITherapist | Therapist RAG assistant |
| `/imaginal-generator` | ERPScriptGenerator | Start / review / audio for imaginal scripts |
| `/education/ocd-core` | education/ocd_core | OCD core education (patient + therapist preview) |
| `/education/fear-ladder` | education/fear_ladder | Fear ladder education |
| `/education/relapse` | education/relapse_prevention | Relapse prevention education |
| `/chat` | chat | Therapist↔Patient, EP↔Patient, EP group WebSocket |
| `/therapy-sessions` | therapy_sessions | Video session records + Whisper transcription |
| `/sessions/ws` | live_sessions | WebRTC WebSocket signaling |
| `/resources` | resources | Upload, ingest, and retrieve clinical resources |
| `/self-monitoring` | self_monitoring | Patient daily OCD/anxiety logs |
| `/progress` | progress | Weekly progress chart data |
| `/intakes` | intakes | Digital intake forms |
| `/homework` | patient_homework | Homework assignment + submission tracking |

---

## Federated QLoRA — Research Background

The `FTSLM/federated_QLoRA.ipynb` notebook (designed for Google Colab) implements a complete **privacy-preserving federated fine-tuning pipeline** for the imaginal exposure script domain.

### Why Federated Learning?

Therapy data is among the most sensitive personal data in existence. In a real multi-clinic deployment, each clinic would have its own patient population. Centralising that data raises serious privacy and ethical concerns. Federated learning allows each clinic to train a local copy of the model on their own data, then share only the learned weight updates — never the raw therapy transcripts.

### The Pipeline

```
Google Colab (single GPU)
        │
        ├─ Base model: meta-llama/Meta-Llama-3.1-8B-Instruct (via Unsloth, 4-bit NF4)
        │
        ├─ Dataset: train.jsonl / dev.jsonl / test.jsonl
        │   Each record: instruction + patient case → imaginal script
        │
        ├─ Non-IID split across 4 simulated clients:
        │   Client 0 → 80% Harm OCD data
        │   Client 1 → 80% Contamination OCD data
        │   Client 2 → 80% Checking/Hit-and-Run OCD data
        │   Client 3 → mixed remainder
        │
        ├─ Federated rounds: 5
        │   Per round: each client trains for 1 local epoch (SFTTrainer/TRL)
        │              uploads LoRA adapter weights (not data)
        │              server averages weights (FedAvg via Flower)
        │
        ├─ Best adapter checkpoint saved after each round (BLEU/ROUGE eval on dev set)
        │
        └─ Final export: GGUF format → imported into Ollama as nirbaan-erp-federated
```

### Key Libraries

| Library | Role |
|---|---|
| **Flower (`flwr`)** | Federated orchestration (clients, server, FedAvg strategy) |
| **Unsloth** | Memory-efficient 4-bit LLaMA loading (fits in a single T4 GPU) |
| **PEFT** | LoRA adapter training (rank 16, all attention + MLP layers) |
| **TRL / SFTTrainer** | Supervised fine-tuning loop |

### Human-in-the-Loop on Top of the Fine-Tuned Model

Once the model is deployed via Ollama, it does not run autonomously. The LangGraph `therapist_review_node` gate (using PostgreSQL checkpointing) ensures that every generated script pauses for therapist approval before it ever reaches the patient. This is the deliberate safety architecture: the AI produces, the human approves, the patient receives.

---

## Contributing

1. Fork the repository and create a feature branch from `main`.
2. Follow the existing module pattern: `models.py → schemas.py → router.py → service.py → (graph.py for AI modules)`.
3. Add a corresponding API file in `frontend/src/api/` for any new backend module.
4. Ensure `docker compose up --build` completes without errors before submitting a PR.
5. Document any new AI agent or LangGraph graph by adding a `DEEP_DIVE` markdown file at the project root, following the existing convention.

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

Built to ensure no patient faces their anxiety alone.

[![Live Demo](https://img.shields.io/badge/Try%20the%20Live%20Demo-4CAF50?style=for-the-badge&logo=render&logoColor=white)](https://nirbaan-frontend-6vu7.onrender.com)

</div>
