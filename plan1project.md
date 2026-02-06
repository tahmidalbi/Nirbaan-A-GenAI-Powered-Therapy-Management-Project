I'll help you create a comprehensive plan for this therapy management platform. Let me first explore the existing codebase to understand what's already in place. 

Explore codebase structure

Read [](file:///c%3A/Users/albit/OneDrive/Desktop/Nirbaan-%20A%20Therapy%20Management%20Project/Backend)

Read [](file:///c%3A/Users/albit/OneDrive/Desktop/Nirbaan-%20A%20Therapy%20Management%20Project/Frontend)

Read [](file:///c%3A/Users/albit/OneDrive/Desktop/Nirbaan-%20A%20Therapy%20Management%20Project)

Searched for files matching `**/*`, no matches

Searched for regex `.*`, no results

Thanks for the detailed requirements! This is a greenfield project with no existing code. Before I create a comprehensive plan, I need to clarify several critical aspects that will significantly impact the architecture: 

Asked 4 questions (Scope, Services, AI Priority, Banglish)

Perfect, that helps clarify the scope. Now let me create a comprehensive plan for the complete system.

## Plan: Nirbaan Multi-Tenant Therapy Management Platform

**TL;DR:** Build a full-featured therapy management platform from scratch supporting multiple therapists, patients, and emergency handlers. Core systems include multi-role authentication, video therapy sessions with transcription, therapist knowledge base with RAG-powered AI assistance (LangGraph), condition-specific tools (ADHD games, OCD exposure therapy), risk detection with automatic escalation, uncertainty scoring, federated learning for personalization, and Banglish chat support. Tech stack: React frontend, FastAPI backend, Postgres database, with managed services for video (Twilio/Agora), AI (OpenAI/Anthropic), and speech-to-text (Whisper API).

---

### **Architecture Overview**

**1. Multi-Tenant Database Schema (Postgres)**
- Design schema supporting multiple therapists with their own patient rosters
- Core entities: Users (multi-role auth), Therapists, Patients, EmergencyHandlers, TherapistPatientRelationships
- Session management: VideoSessions, SessionTranscripts, Groups, GroupMembers
- Knowledge system: KnowledgeBase (file storage + embeddings), SystemPrompts (per therapist-patient pair)
- AI interaction: ChatMessages, UncertaintyScores, RiskAlerts
- Patient tools: Homework, ProgressTracking, TherapyNotebook, PatientNotes, TherapistNotes
- ADHD features: ADHDTasks, DistractedThoughts, ADHDGameSessions
- OCD features: FearLadders, Compulsions, ExposureExercises, DistressRatings, ExposureVideos
- ML: FederatedModelWeights, PersonalizationMetadata
- Implement row-level security ensuring therapists only access their patients

**2. Authentication & Authorization System**
- JWT-based auth with refresh tokens
- Three role types: THERAPIST, PATIENT, EMERGENCY_HANDLER
- Therapists create login credentials for patients and emergency handlers
- Patients cannot self-register (therapist-generated ID/password only)
- Role-based access control (RBAC) middleware in FastAPI
- Session management with secure token storage

**3. Backend Structure (FastAPI)**

Create modular API structure:
- Backend/main.py - FastAPI app initialization, CORS, middleware
- Backend/config.py - Environment config (DB, API keys, services)
- Backend/database.py - SQLAlchemy setup, connection pooling
- Backend/models/ - SQLAlchemy ORM models for all entities
- Backend/schemas/ - Pydantic schemas for request/response validation
- Backend/routers/ - API route modules:
  - `auth.py` - Login, token refresh, password management
  - `therapist.py` - Patient CRUD, group management, knowledge base upload, system prompt configuration
  - `patient.py` - Homework view, progress tracking, notes, ADHD/OCD tools
  - `chat.py` - AI chat endpoints (therapist + patient), streaming responses
  - `video.py` - Session creation, Twilio/Agora token generation, transcript storage
  - `emergency.py` - Emergency handler endpoints, risk alert handling
  - `rag.py` - RAG pipeline interactions, LangGraph trajectory selection
  - `adhd.py` - Game APIs, distraction capture, task breakdown, lecture processing
  - `ocd.py` - Fear ladder CRUD, exposure exercise tracking, video generation
  - `federated.py` - Model weight sync, personalization endpoints
  - `mindfulness.py` - Guided session retrieval (Bangla audio)
- Backend/services/ - Business logic layer:
  - `knowledge_base_service.py` - File processing, chunking, embedding generation (pgvector or Pinecone)
  - `rag_service.py` - LangGraph pipeline, retrieval, prompt construction
  - `uncertainty_service.py` - Separate uncertainty scoring model integration
  - `risk_detection_service.py` - Analyze patient messages for self-harm/suicide indicators, trigger alerts
  - `video_service.py` - Twilio/Agora SDK integration, token generation, webhook handling
  - `transcript_service.py` - Whisper API integration, process audio to text, store with timestamps
  - `ai_video_service.py` - Generate OCD exposure videos (via AI video gen APIs)
  - `federated_learning_service.py` - Coordinate patient model training, aggregate weights
  - `lecture_processing_service.py` - Convert lecture transcripts to structured notes
- Backend/middleware/ - Auth middleware, error handling, logging
- Backend/utils/ - Helper functions, constants

**4. AI/ML Infrastructure**

**RAG Pipeline (LangGraph):**
- Design multi-trajectory LangGraph workflow:
  - Trajectory 1: Patient progress analysis (read progress tracking + previous sessions + treatment protocol) → generate insights
  - Trajectory 2: Therapist inquiry (query knowledge base + patient context)
  - Trajectory 3: Homework management (read/write homework assignments)
  - Trajectory 4: Notebook update (read/write therapy notebook)
- Implement automatic trajectory selection based on query intent
- Integrate patient name auto-completion triggering context retrieval
- Use therapist's system prompt to ground all responses
- Support Banglish input/output (OpenAI GPT-4 handles well)

**Uncertainty Scoring:**
- Separate model endpoint evaluating response confidence
- If uncertainty score < threshold → respond "I don't know" instead of hallucinating
- Log all scores for therapist review

**Risk Detection:**
- Real-time analysis of patient chat messages
- Detect keywords/patterns for self-harm or suicide ideation
- Automatically create RiskAlert and notify emergency handler
- Provide emergency handler contact option to patient immediately

**Federated Learning:**
- Patient-side: Train local personalization model on device/browser data (encrypted)
- Aggregate model weights server-side without exposing raw patient data
- Update global model periodically
- Privacy-preserving architecture (differential privacy considerations)

**Vector Database:**
- Use pgvector extension in Postgres (simplest), or external Pinecone/Weaviate
- Store knowledge base document embeddings (OpenAI text-embedding-3)
- Semantic search for RAG retrieval

**5. Frontend Structure (React)**

Initialize with Vite/Create-React-App:
- Frontend/src/main.jsx - Entry point
- Frontend/src/App.jsx - Root component, routing
- Frontend/src/contexts/ - React Context for auth, user state
- Frontend/src/services/ - API client (axios), service functions
- Frontend/src/hooks/ - Custom hooks (useAuth, useChat, useVideo)
- Frontend/src/components/ - Shared components (buttons, forms, modals)
- Frontend/src/pages/ - Page components:
  - `Login.jsx` - Role-based login
  - **Therapist pages:**
    - `TherapistDashboard.jsx` - Overview, patient list, quick actions
    - `PatientManagement.jsx` - Add/edit patients, diagnosis, system prompt per patient
    - `GroupManagement.jsx` - Create groups, schedule group video sessions
    - `KnowledgeBase.jsx` - Upload scripts, blogs, books, PDFs
    - `VideoSession.jsx` - Video call interface (Twilio/Agora integration)
    - `AIChat.jsx` - Chat with RAG agent, select LangGraph trajectories, automatic AI actions (homework/notebook updates)
    - `TherapistNotes.jsx` - Private notes section
  - **Patient pages:**
    - `PatientDashboard.jsx` - Overview, homework due, progress summary
    - `PatientChat.jsx` - AI assistance (homework help), uncertainty-aware responses
    - `Homework.jsx` - List of assignments, mark complete
    - `ProgressTracking.jsx` - Manual progress entry forms
    - `TherapyNotebook.jsx` - Personal journal/notes
    - `ADHDTools.jsx` - Hub for ADHD features
      - `GoNoGoGame.jsx`, `DualNBackGame.jsx`, `InterferenceGame.jsx`
      - `TaskBreakdown.jsx` - Enter overwhelming task, AI breaks into steps with rewards
      - `DistractionCapture.jsx` - Log distracting thought, structured list, reminder to return
      - `LectureRecorder.jsx` - Record audio, transcribe, AI formats as class notes
      - `FocusReminder.jsx` - Vibration/notification every 5-10 minutes
      - `CognitiveWorksheet.jsx` - CBT worksheets for ADHD
    - `OCDTools.jsx` - Hub for OCD features
      - `FearLadder.jsx` - View/edit fear hierarchy, click item to see compulsions
      - `ExposurePractice.jsx` - ERP exercises, button for urge tracking, distress rating
      - `ImaginalExposure.jsx` - AI-generated scenarios (therapist-guided)
      - `ExposureVideos.jsx` - View AI-generated exposure videos
    - `Mindfulness.jsx` - Guided meditation sessions in Bangla
    - `PatientNotes.jsx` - Personal note section
  - **Emergency Handler pages:**
    - `EmergencyDashboard.jsx` - Active risk alerts, contact patient via chat/call
    - `RiskAlertDetail.jsx` - View patient context, conversation history, therapist contact
- Frontend/src/games/ - Game logic for ADHD tools (canvas-based or library)
- Frontend/src/styles/ - CSS/Tailwind configuration

**State Management:**
- Use React Context + Hooks for auth and global state
- Consider Zustand or Redux Toolkit if state becomes complex
- Real-time updates: WebSocket or Server-Sent Events for chat, risk alerts

**Video Integration:**
- Integrate Twilio Video or Agora SDK in React
- Participant views, screen sharing, recording controls
- Automatic transcript generation post-session (send audio to backend → Whisper API)

**6. Specialized Feature Implementations**

**ADHD Games:**
- Go/No-Go: Visual stimuli, respond to target, inhibit to non-target (reaction time tracking)
- Dual N-Back: Memory game, track N-back levels, performance over time
- Interference processing: Stroop-like tasks
- Store game session results in database for progress tracking

**OCD Exposure:**
- Fear Ladder UI: Drag-and-drop hierarchy editor
- ERP Practice: Timer, urge button (logs timestamp), distress slider (0-10), completion tracking
- AI Imaginal Exposure: Therapist provides guidance → AI generates narrative scenario
- AI Video Exposure: Therapist describes scenario → use AI video generation API (Runway, Synthesia, or custom) → store video, patient views repeatedly
- **No reassurance logic:** AI explicitly avoids reassuring language, prompts patient to tolerate uncertainty

**Lecture Processing:**
- Patient records lecture audio via browser
- Upload to backend → Whisper API transcription
- AI analyzes transcript, identifies key concepts, formats as structured class notes
- Explains important concepts in simple terms

**Distraction Management:**
- Patient clicks "I'm distracted" → input distraction thought
- System adds to structured list (visible in separate tab)
- Reassures patient, prompts to return to current task
- Review list later

**Mindfulness Sessions:**
- Pre-recorded or synthesized Bangla audio files
- Guided breathing, body scan, meditation
- Playback controls, session completion tracking

**Therapist AI Actions:**
- When therapist instructs AI: "Update homework for [patient] to include [task]"
- AI parses intent → calls backend API to create homework entry automatically
- Confirm action to therapist

**7. Federated Learning Pipeline**

**Patient-side:**
- Train lightweight personalization model in browser (TensorFlow.js or federated learning library)
- Use patient interaction data (encrypted, local-only)
- Send only model weight updates to server, never raw data

**Server-side:**
- Aggregate weight updates from multiple patients using Federated Averaging (FedAvg)
- Update global model
- Distribute updated model back to patients
- Apply differential privacy techniques to protect individual patient data

**Therapist-side:**
- Similar pipeline for therapist-side personalization
- Aggregate across therapists (optional, consider privacy)

**8. Video Session & Transcription Flow**

1. Therapist schedules session (individual or group) via TherapistDashboard.jsx
2. Frontend requests video token from Backend/routers/video.py
3. Backend generates Twilio/Agora access token, creates VideoSession record
4. Video call interface loads, participants join
5. Enable recording (Twilio Recordings or local capture)
6. Post-session: Backend retrieves recording audio
7. Backend/services/transcript_service.py sends audio to Whisper API
8. Store transcript in SessionTranscripts table with timestamps
9. Transcript available for RAG retrieval in future AI interactions

**9. Knowledge Base Processing**

1. Therapist uploads files (PDFs, DOCX, links) via KnowledgeBase.jsx
2. Backend knowledge_base_service.py:
   - Extracts text (PyPDF2, python-docx, BeautifulSoup for web)
   - Chunks documents (LangChain text splitters, ~500 tokens)
   - Generates embeddings (OpenAI text-embedding-3-large)
   - Stores in vector database (pgvector or Pinecone)
3. Associate knowledge base with therapist ID
4. RAG queries retrieve relevant chunks based on semantic similarity

**10. System Prompt Configuration**

- Therapist creates system prompt per patient (or default for all patients)
- System prompt includes:
  - Patient diagnosis context
  - Therapeutic approach (CBT, DBT, etc.)
  - Dos/Don'ts for AI (never provide reassurance for OCD, focus on homework not therapy)
- AI prepends system prompt to every LangGraph interaction
- Therapist can update prompts, version history tracked

**11. Risk Detection & Emergency Routing**

1. Patient sends chat message in PatientChat.jsx
2. Backend risk_detection_service.py analyzes message
3. If risk detected (self-harm keywords, suicide ideation patterns):
   - Create RiskAlert record (severity, patient ID, message excerpt, timestamp)
   - Notify emergency handler (push notification, email, SMS via Twilio)
   - Display emergency contact option to patient immediately
4. Emergency handler sees alert in EmergencyDashboard.jsx
5. Emergency handler can initiate chat or call with patient
6. Therapist notified of escalation

**12. Banglish Support**

- Backend AI endpoints accept Banglish text input
- OpenAI GPT-4 handles mixed Bengali-English well
- Prompt engineering: "Respond in Banglish if user writes in Banglish"
- Frontend uses English UI labels (buttons, menus)
- Chat interface displays Banglish naturally

**13. Multi-Therapist Isolation**

- All database queries filter by therapist ID (row-level security or ORM filters)
- Therapists cannot see other therapists' patients, knowledge bases, or sessions
- Shared resources (ADHD games, mindfulness sessions) available to all
- Emergency handlers can access patients across therapists when risk alert triggered

---

### **Implementation Steps**

**Phase 1: Foundation (Database + Auth)**
1. Set up Postgres database in Backend/database.py with SQLAlchemy
2. Define all ORM models in Backend/models/ (User, Therapist, Patient, EmergencyHandler, etc.)
3. Create database migrations (Alembic)
4. Implement JWT authentication in Backend/routers/auth.py and Backend/middleware/auth.py
5. Build role-based access control decorators (`@require_role("THERAPIST")`)
6. Create seed script for initial therapist account

**Phase 2: Core Backend APIs**
7. Implement therapist endpoints in Backend/routers/therapist.py: patient CRUD, credential generation
8. Implement group management endpoints
9. Build patient endpoints in Backend/routers/patient.py: profile view, homework list, progress tracking
10. Create notes endpoints (therapist and patient note CRUD)
11. Set up file upload handling (S3 or local storage) for knowledge base
12. Implement basic error handling and logging

**Phase 3: Frontend Shell**
13. Initialize React app in Frontend (Vite recommended)
14. Set up React Router for multi-page navigation
15. Create authentication context in Frontend/src/contexts/AuthContext.jsx
16. Build login page Login.jsx with role detection
17. Create dashboard shells for therapist, patient, emergency handler
18. Build patient management UI in PatientManagement.jsx
19. Implement API client service in Frontend/src/services/api.js with axios, JWT token handling

**Phase 4: Video Sessions**
20. Set up Twilio or Agora account, obtain API credentials
21. Implement video token generation in Backend/services/video_service.py
22. Create video session endpoints: create session, join session, end session
23. Build video call UI in VideoSession.jsx with Twilio Video SDK
24. Implement group video call support (multiple participants)
25. Set up video recording via Twilio Recordings
26. Create webhook endpoint for recording completion

**Phase 5: Transcription**
27. Integrate Whisper API in Backend/services/transcript_service.py
28. Implement audio file handling (download from Twilio, convert format if needed)
29. Process transcription: send audio to Whisper, receive text with timestamps
30. Store transcript in SessionTranscripts table with session ID reference
31. Create endpoint for therapist to view session transcripts

**Phase 6: Knowledge Base & Vector Database**
32. Choose vector database (pgvector extension for Postgres recommended for simplicity)
33. Set up pgvector in Backend/database.py, create embeddings table
34. Implement file processing in knowledge_base_service.py: PDF extraction, DOCX parsing, web scraping
35. Chunk documents using LangChain RecursiveCharacterTextSplitter
36. Generate embeddings using OpenAI text-embedding-3-large API
37. Store embeddings with metadata (therapist ID, document name, chunk index)
38. Create knowledge base upload endpoint, frontend UI in KnowledgeBase.jsx
39. Implement semantic search function (cosine similarity query on pgvector)

**Phase 7: RAG Pipeline (LangGraph)**
40. Design LangGraph workflow with multiple trajectories:
    - State: `{patient_id, query, trajectory, context, messages}`
    - Node 1: Classify intent → select trajectory
    - Node 2a (progress analysis): Retrieve progress data + sessions + protocol → generate insights
    - Node 2b (inquiry): Retrieve knowledge base chunks + patient context → answer query
    - Node 2c (homework): Parse action (read/write) → call DB function → confirm
    - Node 2d (notebook): Parse action → update notebook → confirm
    - Node 3: Assemble response with system prompt
    - Node 4: Generate response with OpenAI/Anthropic
41. Implement trajectory-specific retrievers in Backend/services/rag_service.py
42. Build prompt templates for each trajectory, include therapist's custom system prompt
43. Create chat endpoint in Backend/routers/chat.py with streaming support
44. Implement patient name auto-completion trigger (when therapist types patient name, preload context)
45. Build therapist chat UI in AIChat.jsx with trajectory selector dropdown
46. Support Banglish in prompts (add instruction: "User may write in Banglish, respond accordingly")

**Phase 8: Uncertainty Scoring**
47. Set up separate uncertainty scoring model (fine-tuned classifier or use LLM-based scoring)
48. Implement Backend/services/uncertainty_service.py: send response candidate → receive confidence score
49. Define threshold (e.g., 0.7) - if score < threshold, replace response with "I don't know, let me check with your therapist"
50. Log all uncertainty scores in UncertaintyScores table for analysis
51. Apply uncertainty check to patient-side AI chat only (not therapist-side)

**Phase 9: Risk Detection & Emergency Routing**
52. Implement risk detection in Backend/services/risk_detection_service.py:
    - Keyword matching (self-harm, suicide ideation phrases)
    - Sentiment analysis (very negative sentiment)
    - LLM-based classification (fine-tuned or few-shot prompt)
53. Create RiskAlert model and endpoints in Backend/routers/emergency.py
54. Trigger alert creation when risk detected in patient chat
55. Implement notification system (Twilio SMS, email, push notification) to emergency handler
56. Build emergency dashboard in EmergencyDashboard.jsx: list alerts, patient context, chat interface
57. Create emergency chat/call UI for patient-emergency handler communication
58. Notify therapist of escalation

**Phase 10: Patient Chat Interface**
59. Build patient chat UI in PatientChat.jsx
60. Connect to chat endpoint with streaming responses (Server-Sent Events or WebSockets)
61. Display AI responses grounded in therapist knowledge base
62. Implement uncertainty-aware responses (show "I don't know" when score low)
63. Apply risk detection on every patient message (frontend shows emergency contact if risk detected)
64. Support Banglish input/output

**Phase 11: Homework & Progress Tracking**
65. Implement homework CRUD endpoints in Backend/routers/patient.py
66. Build homework UI in Homework.jsx: list assignments, mark complete, view details
67. Implement progress tracking endpoints: manual entry by patient
68. Build progress tracking UI in ProgressTracking.jsx: forms for mood, symptoms, goals
69. Store progress data in ProgressTracking table with timestamps
70. Make progress data available to RAG pipeline (therapist can query patient progress)

**Phase 12: System Prompt Configuration**
71. Create system prompt CRUD endpoints in Backend/routers/therapist.py
72. Build system prompt editor UI in PatientManagement.jsx (per patient)
73. Store prompts in SystemPrompts table (therapist_id, patient_id, prompt_text, version)
74. Prepend system prompt to all RAG interactions for that therapist-patient pair
75. Support default system prompt for therapist (applies to all patients unless overridden)

**Phase 13: ADHD Features**
76. Implement ADHD API endpoints in Backend/routers/adhd.py:
    - Game session logging
    - Task breakdown (AI-powered)
    - Distraction capture
    - Lecture audio upload & processing
77. Build ADHD tools hub in ADHDTools.jsx
78. Create Go/No-Go game in GoNoGoGame.jsx: canvas-based, reaction time tracking
79. Create Dual N-Back game in DualNBackGame.jsx: memory grid, N-back levels
80. Create interference game (Stroop-like) 
81. Build task breakdown UI in TaskBreakdown.jsx: input task → AI breaks into steps with rewards
82. Build distraction capture in DistractionCapture.jsx: quick input, structured list view, "return to task" prompt
83. Implement lecture recorder in LectureRecorder.jsx: record audio via browser API → upload → Whisper transcription → AI formats as notes
84. Build focus reminder component FocusReminder.jsx: vibration/notification every 5-10 minutes (configurable)
85. Create cognitive therapy worksheet UI CognitiveWorksheet.jsx: fillable CBT forms

**Phase 14: OCD Features**
86. Implement OCD API endpoints in Backend/routers/ocd.py:
    - Fear ladder CRUD
    - Exposure exercise tracking
    - Imaginal exposure generation (AI)
    - Exposure video generation (AI)
87. Build OCD tools hub in OCDTools.jsx
88. Create fear ladder UI in FearLadder.jsx: drag-and-drop hierarchy, attach compulsions to each level
89. Build exposure practice UI in ExposurePractice.jsx:
    - Select exposure from fear ladder
    - Timer display
    - "I feel urge to do compulsion" button (logs timestamp)
    - Distress rating slider (0-10)
    - Complete/Withdraw buttons (track completion rate)
90. Implement imaginal exposure generator: therapist provides guidance → AI creates narrative → patient reads/listens repeatedly
91. Integrate AI video generation API (Runway, Synthesia) in Backend/services/ai_video_service.py
92. Build exposure video generator: therapist describes scenario → AI generates video → store in ExposureVideos table
93. Create exposure video player in ExposureVideos.jsx: view videos, repeat exposure
94. **Implement no-reassurance logic:** System prompt instructs AI to never provide reassurance for OCD, prompts patient to tolerate uncertainty

**Phase 15: Mindfulness Sessions**
95. Prepare Bangla mindfulness audio files (guided meditation, breathing, body scan)
96. Store audio files in cloud storage (S3) or serve from backend
97. Create mindfulness endpoints: list sessions, track completion
98. Build mindfulness UI in Mindfulness.jsx: audio player, session selection, progress tracking

**Phase 16: Federated Learning Pipeline**
99. Research federated learning library (TensorFlow Federated, PySyft, Flower)
100. Design personalization model architecture (lightweight, trains on user interaction data)
101. Implement patient-side training in Frontend/src/services/federatedLearning.js:
     - Collect interaction data (encrypted, local storage)
     - Train model locally (TensorFlow.js)
     - Send weight updates to server (not raw data)
102. Implement server-side aggregation in Backend/services/federated_learning_service.py:
     - Receive weight updates from patients
     - Apply Federated Averaging (FedAvg) algorithm
     - Update global model
     - Distribute updated model to patients
103. Apply differential privacy (add noise to weight updates)
104. Create federated learning endpoints in Backend/routers/federated.py
105. Implement therapist-side federated learning (similar pipeline)
106. Store model weights in FederatedModelWeights table

**Phase 17: Lecture Processing (ADHD)**
107. Implement lecture processing in Backend/services/lecture_processing_service.py:
     - Receive lecture transcript (from Whisper)
     - Use AI (OpenAI) to identify key concepts, structure as class notes
     - Extract main topics, definitions, examples
     - Generate simplified explanations
108. Return formatted notes to patient
109. Display formatted notes in LectureRecorder.jsx

**Phase 18: Therapist AI Action Automation**
110. Enhance RAG pipeline in rag_service.py to parse therapist action commands:
     - "Update homework for [patient] to [task]" → create homework entry
     - "Add note to [patient] therapy notebook: [content]" → update notebook
111. Implement function calling (OpenAI function calling or LangChain tools)
112. Define tools: `create_homework`, `update_notebook`, `update_progress`
113. When AI detects action command → execute tool → confirm to therapist
114. Display confirmation in therapist chat UI

**Phase 19: Notes Sections**
115. Implement therapist notes endpoints (private, patient cannot see)
116. Implement patient notes endpoints (private, therapist can optionally view)
117. Build therapist notes UI in TherapistNotes.jsx: rich text editor, per-patient notes
118. Build patient notes UI in PatientNotes.jsx: journal-style entries

**Phase 20: Testing & Refinement**
119. Write unit tests for critical backend services (auth, RAG, risk detection, federated learning)
120. Write integration tests for API endpoints
121. Test multi-therapist isolation (ensure data leakage prevention)
122. Test role-based access control (patients cannot access therapist endpoints, etc.)
123. Test video session flow end-to-end (create → join → record → transcribe)
124. Test RAG pipeline with sample knowledge base and queries
125. Test risk detection with sample messages (should trigger alerts)
126. Test uncertainty scoring (low-confidence responses handled correctly)
127. Test ADHD games (performance tracking, data storage)
128. Test OCD exposure flow (fear ladder → ERP → distress tracking)
129. Test federated learning (weight aggregation, privacy preservation)
130. Perform security audit (SQL injection, XSS, CSRF protection)
131. Load testing for concurrent users (multiple therapists, patients)

**Phase 21: Deployment Preparation**
132. Create deployment configuration files:
     - Backend/Dockerfile for FastAPI container
     - Frontend/Dockerfile for React build
     - docker-compose.yml for local multi-container setup
133. Set up environment variable management (.env files, secrets management)
134. Configure production database (managed Postgres on AWS RDS, Azure, or similar)
135. Set up cloud storage (S3 or Azure Blob) for knowledge base files, videos, audio
136. Configure CDN for static assets (frontend build, audio files)
137. Set up API keys for Twilio, OpenAI, Whisper API securely
138. Implement database backup strategy
139. Set up logging and monitoring (Sentry for errors, CloudWatch/Datadog for metrics)
140. Configure HTTPS/SSL certificates
141. Set up CI/CD pipeline (GitHub Actions, GitLab CI)

**Phase 22: Documentation**
142. Write API documentation (OpenAPI/Swagger via FastAPI auto-docs)
143. Create developer setup guide (README.md in Backend and Frontend)
144. Document database schema (ER diagram, table descriptions)
145. Write user guides for therapists, patients, emergency handlers
146. Document AI system prompts and configuration options
147. Create troubleshooting guide for common issues

---

### **Verification**

**Manual Testing:**
1. Create therapist account via seed script
2. Therapist logs in, uploads knowledge base documents (PDFs, web links)
3. Therapist adds patients with diagnosis details and custom system prompts
4. Therapist creates patient login credentials, provides to test patient
5. Patient logs in, views homework assignments (initially empty)
6. Therapist creates homework via AI chat: "Add homework for [patient]: practice CBT worksheet"
7. Verify homework appears in patient's Homework.jsx
8. Patient chats with AI asking homework help, verify responses grounded in knowledge base
9. Patient enters message with self-harm keywords ("I want to hurt myself")
10. Verify risk alert created, emergency handler notified, patient sees emergency contact option
11. Emergency handler logs in, views alert, initiates chat with patient
12. Therapist schedules video session, patient joins, session records
13. Post-session, verify transcript generated and stored
14. Patient plays ADHD game (Go/No-Go), verify performance tracked
15. Patient creates fear ladder in OCD tools, practices exposure, logs distress
16. Verify federated learning weight updates sent from patient browser to server
17. Therapist queries patient progress via AI chat, verify RAG retrieves progress data

**Automated Tests:**
- Run unit tests: `pytest Backend/tests/`
- Run integration tests for all API endpoints
- Run frontend tests: `npm test` in Frontend/
- Check test coverage (aim for >80% on critical paths)

**Security Checks:**
- Confirm JWT tokens expire and refresh properly
- Verify role-based access: patient cannot access therapist endpoints (returns 403)
- Test SQL injection attempts (should be blocked by SQLAlchemy parameterization)
- Verify CORS configuration (only allow frontend domain)
- Check file upload validation (reject malicious files)

**Performance Tests:**
- Simulate 100 concurrent users, measure response times
- Test RAG pipeline with large knowledge base (1000+ documents)
- Verify vector search performance (<100ms for semantic search)
- Test video session with 10+ participants (group call)

**Banglish Tests:**
- Patient sends Banglish message: "Ami amar homework korte parchi na"
- Verify AI responds in Banglish appropriately

---

### **Technology Stack Summary**

**Frontend:**
- React (Vite)
- React Router (routing)
- Axios (API client)
- Twilio Video SDK or Agora SDK (video calls)
- TensorFlow.js (federated learning client-side)
- Tailwind CSS or Material-UI (styling)

**Backend:**
- FastAPI (API framework)
- SQLAlchemy (ORM)
- Alembic (database migrations)
- PostgreSQL with pgvector (database + vector search)
- Pydantic (validation)
- LangChain + LangGraph (RAG pipeline)
- OpenAI API (LLM, embeddings)
- Whisper API (speech-to-text)
- Twilio or Agora (video SDK + SMS notifications)
- JWT (authentication)
- Python libraries: PyPDF2, python-docx, BeautifulSoup (document processing)

**AI/ML:**
- OpenAI GPT-4 or Anthropic Claude (LLM)
- OpenAI text-embedding-3-large (embeddings)
- Whisper API (transcription)
- Custom uncertainty scoring model (fine-tuned classifier or LLM-based)
- Federated learning framework (TensorFlow Federated, Flower, or PySyft)
- AI video generation API (Runway, Synthesia, or similar)

**Infrastructure:**
- Postgres (managed: AWS RDS, Azure Database, or Supabase)
- S3 or Azure Blob Storage (file storage)
- Docker (containerization)
- CI/CD (GitHub Actions or GitLab CI)
- Sentry (error tracking)
- CloudWatch/Datadog (monitoring)

---

### **Key Decisions**

1. **Managed Services Approach:** Using Twilio/Agora for video, OpenAI for AI, Whisper API for transcription reduces infrastructure complexity and speeds development (vs. self-hosting open-source alternatives)

2. **pgvector for Vector Database:** Simplifies architecture by keeping vectors in Postgres (vs. external Pinecone/Weaviate), suitable for moderate scale, easier to manage multi-tenant isolation

3. **LangGraph for RAG:** Multi-trajectory design allows flexible AI behavior (progress analysis, inquiry, homework management) controlled by therapist, more sophisticated than simple retrieval

4. **Separate Uncertainty Model:** Dedicated uncertainty scoring prevents AI hallucination in patient-facing chat, critical for safety in therapy context

5. **Federated Learning Complexity:** Privacy-preserving but adds significant development overhead; consider deferring if timeline is tight, or use simpler personalization (user preferences)

6. **AI Video Generation:** Cutting-edge feature for OCD exposure therapy, may have high API costs; confirm budget and explore alternatives (static images, text-based exposure) if needed

7. **Banglish via Prompt Engineering:** GPT-4 handles Banglish well without fine-tuning, simpler than maintaining separate Bangla model

8. **Multi-Tenant at DB Level:** Row-level security or ORM filters ensure therapist data isolation, critical for privacy and compliance

---

This plan covers the complete system architecture and implementation path. The project is large and will require significant development time (estimated 6-12 months with a team of 3-5 developers). Prioritization within phases can be adjusted based on delivery timeline needs.