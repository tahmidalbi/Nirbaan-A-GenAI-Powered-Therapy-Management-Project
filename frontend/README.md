# Nirbaan Frontend

> **React 19 + Vite** single-page application for the Nirbaan therapy management platform. Provides separate, role-scoped dashboards and workflows for Therapists, Patients, and Emergency Personnel.

**Live Demo:** [https://nirbaan-frontend-6vu7.onrender.com](https://nirbaan-frontend-6vu7.onrender.com)

---

## Table of Contents

- [Tech Stack](#tech-stack)
- [Folder Structure](#folder-structure)
- [Pages](#pages)
- [Key Components](#key-components)
- [State Management](#state-management)
- [API Layer](#api-layer)
- [Routing & Auth Guards](#routing--auth-guards)
- [Custom Hooks](#custom-hooks)
- [Setup & Development](#setup--development)
- [Build & Preview](#build--preview)
- [Environment Variables](#environment-variables)
- [Docker](#docker)

---

## Tech Stack

| Library | Version | Purpose |
|---|---|---|
| React | 19 | UI framework |
| Vite | 7 | Build tool & dev server |
| React Router | v7 | Client-side routing |
| Zustand | 5 | Global state |
| Axios | 1.13 | HTTP API client |
| Recharts | 3 | Progress & SUDS charts |
| react-markdown | 10 | Render AI markdown responses |
| prop-types | 15 | Runtime prop validation |
| jwt-decode | 4 | Decode JWT claims client-side |

---

## Folder Structure

```
frontend/src/
│
├── main.jsx                  # App entry point
├── App.jsx                   # Root component with router
├── App.css / index.css       # Global base styles
│
├── auth/                     # Auth context provider & route guards
│   ├── AuthContext.jsx
│   └── PrivateRoute.jsx
│
├── store/                    # Zustand stores
│   └── authStore.js          # User, token, role state
│
├── routes/                   # React Router v7 route tree
│   └── AppRoutes.jsx
│
├── api/                      # Axios API layer (one file per domain)
│   ├── auth.api.js
│   ├── erp.api.js
│   ├── fearLadder.api.js
│   ├── chat.api.js
│   ├── nirbaan.api.js
│   ├── progress.api.js
│   ├── resources.api.js
│   ├── sessions.api.js
│   └── ...
│
├── hooks/                    # Custom React hooks
│   └── useRealtimeVoice.js   # ERP voice mode hook
│
├── utils/                    # Shared utility functions
│
├── assets/                   # Static images, icons
│
├── dashboards/               # Role-level dashboard shells
│   ├── TherapistDashboard.jsx
│   └── PatientDashboard.jsx  # Includes WebSocket incoming-call listener
│
├── components/               # Reusable UI components
│   ├── Navbar.jsx
│   ├── Sidebar.jsx
│   ├── IncomingCallModal.jsx  # Call ring + Web Audio API ringtone
│   ├── VideoCall.jsx          # WebRTC peer connection
│   ├── AILadderReview.jsx
│   ├── AudioRecorder.jsx
│   ├── FearLadderBuilder.jsx
│   ├── Intake.jsx
│   ├── MindfulnessPlayer.jsx
│   ├── PatientChat.jsx
│   ├── PatientHistory.jsx
│   ├── PatientHomework.jsx
│   ├── PatientResourceLibrary.jsx
│   ├── PatientSelfMonitoring.jsx
│   ├── RAGChat.jsx
│   ├── ResourceManager.jsx
│   ├── TherapistChat.jsx
│   ├── TherapistSelfMonitoringView.jsx
│   ├── TranscriptDisplay.jsx
│   └── ActiveSessions.jsx
│
└── pages/                    # Full-page views (one per major workflow)
    ├── LandingPage.jsx
    ├── RoleSelection.jsx
    ├── ERPWorkspace.jsx / ERPDiveIn.jsx / ERPSessionPage.jsx
    ├── PatientFearLadder*.jsx / TherapistFearLadder*.jsx
    ├── NirbaanAIChat.jsx / TherapistNirbaanAIPage.jsx
    ├── PatientImaginalScripts.jsx / TherapistImaginalScriptPage.jsx
    ├── PatientOCDEducation.jsx / PatientERPEducation.jsx
    ├── PatientChatPage.jsx / TherapistChatPage.jsx / EPChatPage.jsx
    ├── VideoSession.jsx / VideoSessionWithTranscript.jsx
    └── PatientWeeklyProgress.jsx
```

---

## Pages

### Therapist Workflows
| Page | Description |
|---|---|
| `TherapistDashboard` | Overview: patient list, active sessions, quick actions |
| `PatientDetail` | Full patient profile: history, ERP, fear ladder, notes |
| `ERPWorkspace` | Manage a patient's ERP obsession hierarchy |
| `ERPDiveIn` | Obsession detail with exposure steps |
| `ERPAIReport` | AI-generated ERP session report |
| `TherapistFearLadderHub` | Fear ladder management hub |
| `TherapistImaginalScriptPage` | Review and approve generated imaginal scripts |
| `TherapistNirbaanAIPage` | RAG-powered therapist AI assistant |
| `TherapistChatPage` | Direct messaging with patient |

### Patient Workflows
| Page | Description |
|---|---|
| `PatientDashboard` | Overview + incoming call WebSocket listener |
| `ERPSessionPage` | Live ERP session with AI Coach chat |
| `PatientFearLadderHub` | Fear ladder overview and SUDS tracking |
| `NirbaanAIChat` | AI chatbot (support + psychoeducation) |
| `PatientImaginalScripts` | View assigned imaginal scripts |
| `PatientOCDEducation` | OCD core education module |
| `PatientERPEducation` | ERP education module |
| `PatientWeeklyProgress` | Charts of SUDS and homework progress |
| `VideoSession` | WebRTC video therapy session |

---

## Key Components

### `IncomingCallModal`
Displays when a therapist initiates a call to a patient. Features:
- 45-second auto-decline timer with countdown
- Animated pulse ring
- **Web Audio API ringtone** — dual-tone ring (480 Hz + 620 Hz), loops every 3 seconds, no audio file required
- Audio context closed automatically on accept / decline / timeout

### `VideoCall`
Full WebRTC peer connection component with ICE candidate exchange via WebSocket signaling, mic mute toggle, and live transcription chunk forwarding.

### `PatientDashboard`
Maintains a persistent WebSocket connection to `/api/therapy-sessions/ws/call/:userId`. Mounts `IncomingCallModal` on `incoming_call` events.

### `RAGChat`
Chat interface for the therapist AI assistant. Renders markdown responses with source citations from the clinical knowledge base.

---

## State Management

Zustand store (`src/store/authStore.js`) holds `user`, `token`, and `role`. Token is persisted to `localStorage` and rehydrated on app load.

---

## API Layer

All files in `src/api/` use a shared Axios instance with the base URL from `VITE_API_URL`. A request interceptor attaches the JWT from Zustand on every request.

---

## Routing & Auth Guards

`src/routes/AppRoutes.jsx` defines the full route tree.  
`src/auth/PrivateRoute.jsx` redirects to `/role` if no token is present. Routes under `/therapist/*` enforce `role === 'therapist'`; `/patient/*` enforce `role === 'patient'`.

---

## Custom Hooks

### `useRealtimeVoice(sessionId, onCoachText, onUserText)`
Manages ERP session voice mode: records microphone chunks via `MediaRecorder`, POSTs each chunk to `/api/erp/voice/transcribe-and-respond`, and delivers transcription + AI response via callbacks.

---

## Setup & Development

```bash
cd frontend
npm install
npm run dev      # http://localhost:5174
```

---

## Build & Preview

```bash
npm run build    # outputs to dist/
npm run preview  # serve production build locally
```

---

## Environment Variables

```env
VITE_API_URL=http://localhost:8000
```

---

## Docker

Two-stage build: Node 20 builder (`npm ci && npm run build`) → Nginx Alpine runtime serving `dist/`. The root `docker-compose.yml` handles the full stack automatically.
