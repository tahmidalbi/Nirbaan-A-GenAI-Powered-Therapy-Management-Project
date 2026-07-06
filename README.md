# Nirbaan

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21220833.svg)](https://doi.org/10.5281/zenodo.21220833)

Nirbaan is an open-source GenAI-powered therapy management platform
designed to support therapist-supervised Exposure and Response
Prevention (ERP) and digital mental healthcare. The platform integrates
multi-role clinical workflows with LangGraph-based agentic AI,
therapist-scoped retrieval-augmented generation (RAG), human-in-the-loop
safety mechanisms, and real-time communication to bridge the gap between
therapy sessions. Developed alongside a SoftwareX publication, Nirbaan
provides a reproducible research framework for AI-assisted digital
mental health systems. A live demonstration is available at
**https://nirbaan-frontend-6vu7.onrender.com/**.

## Key Features

-   Multi-role platform for therapists, patients, and emergency
    personnel
-   LangGraph-based agentic AI workflows
-   Therapist-scoped retrieval-augmented generation (RAG)
-   AI-assisted ERP coaching and imaginal exposure generation
-   Hidden symptom detection for therapist decision support
-   Human-in-the-loop approval for AI-generated clinical content
-   Real-time messaging and WebRTC video therapy sessions
-   Docker Compose deployment with GitHub Actions continuous integration
-   Open-source under the MIT License

## System Requirements

-   Python 3.11+
-   Node.js 20+
-   PostgreSQL 16+ with pgvector
-   Redis 7+
-   Docker Desktop (recommended)
-   Ollama (optional)

## Installation

``` bash
git clone https://github.com/tahmidalbi/Nirbaan-A-GenAI-Powered-Therapy-Management-Project.git
cd Nirbaan-A-GenAI-Powered-Therapy-Management-Project
cp .env.docker .env
docker compose up --build
```

Services: - Frontend: http://localhost:5174 - Backend:
http://localhost:8000 - Swagger: http://localhost:8000/docs

## Local Development

``` bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

``` bash
cd frontend
npm install
npm run dev
```

## API Documentation

-   Swagger UI: http://localhost:8000/docs
-   ReDoc: http://localhost:8000/redoc

## Project Structure

``` text
Nirbaan/
├── backend/
├── frontend/
├── FTSLM/
├── Paper_Materials/
├── demo/
├── docker-compose.yml
├── CITATION.cff
├── LICENSE
└── README.md
```

## User Roles

**Therapists** -- Manage patients, ERP sessions, AI review, and clinical
resources.

**Patients** -- Complete ERP exercises, self-monitor symptoms, receive
therapist-grounded AI support, and communicate with therapists.

**Emergency Personnel** -- Respond to AI-triggered escalations and
communicate with assigned patients.

## AI Components

  -----------------------------------------------------------------------
  Component                           Purpose
  ----------------------------------- -----------------------------------
  NirbaanAI Patient                   Therapist-grounded patient support

  ERP Coach                           AI-guided ERP sessions

  Hidden Symptom Detector             Fear ladder review using
                                      therapist-scoped RAG

  Imaginal Script Generator           Therapist-approved imaginal
                                      exposure generation

  Therapist Assistant                 Clinical decision support

  Education Agents                    Personalized psychoeducation
  -----------------------------------------------------------------------

## Tech Stack

**Backend:** Python, FastAPI, PostgreSQL, pgvector, Redis, Celery,
LangGraph, LangChain, Docker

**Frontend:** React, Vite, Zustand, Axios, WebRTC

## Reproducibility

Nirbaan can be deployed using Docker Compose, which orchestrates the
React frontend, FastAPI backend, PostgreSQL with pgvector, Redis, Celery
Worker, and Celery Beat services. The repository includes GitHub Actions
workflows for continuous integration, while the archived software
release is available through Zenodo.

## License

Released under the MIT License.

## Citation

If you use Nirbaan in your research, please cite:

> Islam, M. T., Abdullah, A. N., & Das, A. M. (2026). **Nirbaan: A
> GenAI-Powered Therapy Management Platform** (Version 1.0). Zenodo.
> https://doi.org/10.5281/zenodo.21220833

GitHub also provides a **Cite this repository** option through the
included `CITATION.cff` file.

## Contact

**das2107118@stud.kuet.ac.bd**
