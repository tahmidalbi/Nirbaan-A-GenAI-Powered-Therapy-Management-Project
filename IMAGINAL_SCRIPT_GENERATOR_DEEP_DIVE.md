# Imaginal Script Generator Agent — Complete Deep Dive

> **Module path:** `backend/app/ERPScriptGenerator/`
> **Feature scope:** AI-assisted imaginal exposure script generation for OCD therapy, with therapist review loop, text-to-speech synthesis, and cloud audio storage.

---

## Table of Contents

1. [What Is This Feature?](#1-what-is-this-feature)
2. [Full File Map](#2-full-file-map)
3. [Architecture Overview](#3-architecture-overview)
4. [Database Layer — `models.py`](#4-database-layer--modelspy)
5. [LangGraph State — `state.py`](#5-langgraph-state--statepy)
6. [Configuration — `config.py`](#6-configuration--configpy)
7. [Prompt Engineering — `prompts.py`](#7-prompt-engineering--promptspy)
8. [GPT Prompt Builder — `gemini_builder.py`](#8-gpt-prompt-builder--gemini_builderpy)
9. [Local SLM Client — `ollama_client.py`](#9-local-slm-client--ollama_clientpy)
10. [LangGraph Agent — `graph.py`](#10-langgraph-agent--graphpy)
11. [Repository Layer — `repository.py`](#11-repository-layer--repositorypy)
12. [Service Layer — `service.py`](#12-service-layer--servicepy)
13. [API Schemas — `schemas.py`](#13-api-schemas--schemaspy)
14. [FastAPI Router — `router.py`](#14-fastapi-router--routerpy)
15. [Text-To-Speech — `piper_tts.py`](#15-text-to-speech--piper_ttspy)
16. [Cloud Storage — `r2_storage.py`](#16-cloud-storage--r2_storagepy)
17. [App Initialization — `main.py`](#17-app-initialization--mainpy)
18. [Frontend API Client — `imaginal-generator.api.js`](#18-frontend-api-client--imaginal-generatorapijs)
19. [Therapist UI — `TherapistImaginalScriptPage.jsx`](#19-therapist-ui--therapistimaginalscriptpagejsx)
20. [Patient UI — `PatientImaginalScripts.jsx`](#20-patient-ui--patientimaginalscriptsjsx)
21. [Route Definitions — `AppRoutes.jsx`](#21-route-definitions--approutesjsx)
22. [Complete End-to-End Workflow Trace](#22-complete-end-to-end-workflow-trace)
23. [LangGraph Node Execution Flow](#23-langgraph-node-execution-flow)
24. [Revision Loop Deep Dive](#24-revision-loop-deep-dive)
25. [Database Tables & Relationships](#25-database-tables--relationships)
26. [Status State Machine](#26-status-state-machine)
27. [Audio Pipeline Detail](#27-audio-pipeline-detail)

---

## 1. What Is This Feature?

**Imaginal Exposure** is a core technique in ERP (Exposure and Response Prevention) therapy for OCD. A therapist narrates a vivid story placing the patient in their feared scenario — for instance, contaminating their family — to deliberately trigger anxiety without performing the compulsion, allowing habituation.

This feature **automates the script writing** using a two-model AI pipeline:

```
GPT-5.2 (prompt engineer)  →  fine-tuned SLM via Ollama (script writer)  →  Therapist review  →  Piper TTS  →  R2 audio
```

The therapist can reject a script with written feedback, which loops back through the prompt engineer to regenerate. Once approved, the script is synthesized to audio and stored for the patient to play as a therapeutic exercise.

---

## 2. Full File Map

```
backend/app/ERPScriptGenerator/
├── __init__.py
├── config.py              ← Pydantic settings (env vars, paths, R2, Ollama)
├── state.py               ← LangGraph TypedDict state
├── prompts.py             ← System prompt strings for GPT
├── gemini_builder.py      ← GPT-5.2 prompt normalizer
├── ollama_client.py       ← HTTP client for local Ollama SLM
├── graph.py               ← LangGraph 6-node agent definition
├── repository.py          ← SQLAlchemy DB operations
├── models.py              ← ORM table definitions
├── schemas.py             ← Pydantic request/response schemas
├── service.py             ← Graph invocation helpers
├── router.py              ← FastAPI route handlers
├── piper_tts.py           ← Piper CLI TTS synthesis
├── r2_storage.py          ← Cloudflare R2 (S3-compatible) uploads
└── voices/
    └── en_US-lessac-medium.onnx   ← Piper voice model (git-ignored)

backend/
└── create_erp_script_generator_tables.py  ← One-time DB migration script

frontend/src/
├── api/
│   └── imaginal-generator.api.js          ← Axios REST client
└── pages/
    ├── TherapistImaginalScriptPage.jsx     ← Therapist generate/review UI
    ├── TherapistImaginalScriptPage.css
    ├── TherapistImaginalObsessionList.jsx  ← Pick an obsession to work on
    ├── TherapistImaginalPatientList.jsx    ← Pick a patient
    ├── PatientImaginalScripts.jsx          ← Patient views approved scripts
    └── PatientImaginalScripts.css
```

---

## 3. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React)                        │
│                                                                 │
│  TherapistImaginalPatientList  ──→  TherapistImaginalObsessionList  │
│           ↓ navigate with state                                 │
│  TherapistImaginalScriptPage                                    │
│    [Form: feared_consequence, intensity, subtype]               │
│    handleGenerate() → POST /imaginal-generator/start            │
│    [Show script] → handleApprove() or handleReject(feedback)    │
│    → POST /imaginal-generator/review                            │
│    [Done] → <audio src="/imaginal-generator/audio/{id}" />      │
│                                                                 │
│  PatientImaginalScripts                                         │
│    → GET /imaginal-generator/patient/{id}/approved              │
│    → <audio src="/imaginal-generator/audio/{id}" />             │
└─────────────────────────────────────────────────────────────────┘
             │ HTTP (Axios)
             ↓
┌─────────────────────────────────────────────────────────────────┐
│                     FASTAPI BACKEND                             │
│                                                                 │
│  router.py  →  service.py  →  graph.invoke()                    │
│                                                                 │
│  ┌──────────────── LangGraph Agent (graph.py) ─────────────┐   │
│  │                                                           │   │
│  │  START → load_case_context                               │   │
│  │              ↓                                           │   │
│  │          build_prompt_node  ←──────────────────┐        │   │
│  │              ↓                                  │        │   │
│  │          generate_script_node                   │        │   │
│  │              ↓                                  │        │   │
│  │          therapist_review_node [INTERRUPT]       │        │   │
│  │           ↙ approved              ↘ rejected    │        │   │
│  │  finalize_approved_node    prepare_revision_node┘        │   │
│  │              ↓                                           │   │
│  │             END                                          │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                                 │
│  GPT-5.2 (gemini_builder.py)  →  Ollama SLM (ollama_client.py) │
│  PostgreSQL checkpointer       Piper TTS  →  Cloudflare R2     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Database Layer — `models.py`

**File:** `backend/app/ERPScriptGenerator/models.py`

Three ORM tables store the entire lifecycle of a script generation session.

### `ImaginalScriptRun` — lines 19–58

```python
class ImaginalScriptRun(Base):
    __tablename__ = "imaginal_script_runs"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String(128), unique=True, nullable=False, index=True)   # LangGraph session key

    patient_id  = Column(Integer, ForeignKey("patients.id"),   nullable=False, index=True)
    therapist_id= Column(Integer, ForeignKey("therapists.id"), nullable=False, index=True)
    erp_item_id = Column(Integer, ForeignKey("erp_items.id"),  nullable=False, index=True)

    # Case formulation (never changes after creation)
    obsession          = Column(Text, nullable=False)
    compulsion         = Column(Text, nullable=False)
    feared_consequence = Column(Text, nullable=False)
    script_intensity   = Column(String(20), nullable=False)
    exposure_type      = Column(String(20), nullable=False, default="imaginal")
    subtype            = Column(String(100), nullable=True)

    # Lifecycle tracking
    status         = Column(String(30), nullable=False, default="pending_review")
    revision_count = Column(Integer,   nullable=False, default=1)
    latest_prompt_text = Column(Text, nullable=True)   # current active prompt
    latest_script_text = Column(Text, nullable=True)   # current generated script

    # Populated on approval
    approved_script_text = Column(Text, nullable=True)
    approved_audio_path  = Column(Text, nullable=True)  # R2 URL or local path
    approved_audio_key   = Column(Text, nullable=True)  # R2 object key
    approved_script_id   = Column(Integer, ForeignKey("approved_imaginal_scripts.id",
                                   use_alter=True,
                                   name="fk_run_approved_script_id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    versions = relationship("ImaginalScriptVersion", back_populates="run",
                            cascade="all, delete-orphan",
                            order_by="ImaginalScriptVersion.version_no")
```

**Purpose**: The single "session" record. One record per `thread_id`. Updates in-place as the run progresses.

---

### `ImaginalScriptVersion` — lines 61–81

```python
class ImaginalScriptVersion(Base):
    __tablename__ = "imaginal_script_versions"

    id          = Column(Integer, primary_key=True, index=True)
    run_id      = Column(Integer, ForeignKey("imaginal_script_runs.id"), nullable=False, index=True)
    version_no  = Column(Integer, nullable=False)          # 1, 2, 3… per revision
    prompt_text      = Column(Text, nullable=False)        # prompt sent to SLM
    generated_script = Column(Text, nullable=False)        # what SLM returned
    therapist_feedback = Column(Text, nullable=True)       # rejection reason (null on first version)
    approved    = Column(Boolean, nullable=True)           # True when this version approved
    created_at  = Column(DateTime, default=datetime.utcnow, nullable=False)

    run = relationship("ImaginalScriptRun", back_populates="versions")
```

**Purpose**: Immutable audit trail. Every generation attempt (every version) is recorded. Never updated — only inserted.

---

### `ApprovedImaginalScript` — lines 84–96

```python
class ApprovedImaginalScript(Base):
    __tablename__ = "approved_imaginal_scripts"

    id           = Column(Integer, primary_key=True, index=True)
    patient_id   = Column(Integer, ForeignKey("patients.id"),   nullable=False, index=True)
    therapist_id = Column(Integer, ForeignKey("therapists.id"), nullable=False, index=True)
    erp_item_id  = Column(Integer, ForeignKey("erp_items.id"),  nullable=False, index=True)
    run_id       = Column(Integer, ForeignKey("imaginal_script_runs.id"), nullable=False, index=True)

    subtype          = Column(String(100), nullable=True)
    approved_script  = Column(Text, nullable=False)
    audio_path       = Column(Text, nullable=True)   # final audio URL (R2 or local)
    audio_key        = Column(Text, nullable=True)   # R2 object key for presigned URL logic
    metadata_json    = Column(JSON, nullable=True)   # obsession/compulsion/intensity snapshot
```

**Purpose**: The final product. What the patient sees and plays. `metadata_json` snapshots the full case formulation for display without joining multiple tables.

---

## 5. LangGraph State — `state.py`

**File:** `backend/app/ERPScriptGenerator/state.py` (lines 1–29)

```python
class ImaginalGraphState(TypedDict, total=False):
    # ── Identifiers (set at graph entry) ──
    thread_id:    str       # "imaginal-{pid}-{iid}-{tid}-{hex8}" — LangGraph session key
    run_id:       int       # DB primary key from imaginal_script_runs
    patient_id:   int
    therapist_id: int
    erp_item_id:  int

    # ── Case formulation (loaded from ERPItem in Node 1) ──
    obsession:         str
    compulsion:        str          # stringified compulsions list
    feared_consequence:str          # supplied by therapist on form
    script_intensity:  str          # e.g. "7/10"
    exposure_type:     str          # always "imaginal"
    subtype:           str | None   # e.g. "contamination", "checking"

    # ── Pipeline working data ──
    prompt_text:      str           # output of GPT prompt builder
    generated_script: str           # output of Ollama SLM
    version_no:       int           # revision counter

    # ── Human-in-the-loop fields ──
    therapist_feedback: str | None  # rejection reason from therapist
    approved:           bool | None # decision from therapist

    # ── Final outputs ──
    audio_path:        str | None   # cloud URL or local path
    approved_script_id:int | None   # FK to approved_imaginal_scripts

    # ── Lifecycle ──
    status: str   # see status machine section
```

> **`total=False`** means every field is optional. This is required by LangGraph because nodes return partial dicts that merge into the running state — not every node sets every field.

---

## 6. Configuration — `config.py`

**File:** `backend/app/ERPScriptGenerator/config.py` (lines 1–48)

```python
class ERPScriptGeneratorSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",          # ignore unknown env vars — safe for shared .env
    )

    DATABASE_URL:    str             # e.g. postgresql://user:pass@localhost/nirbaan
    OPENAI_API_KEY:  str | None = None

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL:    str = "nirbaan-erp-federated"    # fine-tuned Federated QLoRA model

    PIPER_MODEL_PATH: str = "backend/app/ERPScriptGenerator/voices/en_US-lessac-medium.onnx"
    PIPER_OUTPUT_DIR: str = "backend/media/imaginal_audio"

    LANGGRAPH_CHECKPOINT_DB_URL: str | None = None   # separate DB for checkpoints, or reuse DATABASE_URL

    R2_ACCOUNT_ID:          str | None = None
    R2_ACCESS_KEY_ID:       str | None = None
    R2_SECRET_ACCESS_KEY:   str | None = None
    R2_BUCKET_NAME:         str | None = None
    R2_ENDPOINT_URL:        str | None = None
    R2_PRESIGNED_URL_EXPIRY:int = 3600    # 1 hour TTL for presigned download URLs

    @property
    def checkpoint_db_url(self) -> str:
        # Falls back to DATABASE_URL if separate checkpoint DB not configured
        return self.LANGGRAPH_CHECKPOINT_DB_URL or self.DATABASE_URL

    @property
    def has_r2_config(self) -> bool:
        # Returns True only if ALL four R2 fields are present
        return all([
            self.R2_ACCESS_KEY_ID,
            self.R2_SECRET_ACCESS_KEY,
            self.R2_BUCKET_NAME,
            self.R2_ENDPOINT_URL,
        ])

settings = ERPScriptGeneratorSettings()   # singleton — imported everywhere
```

**Key design decisions:**
- `has_r2_config` is a computed property so the audio pipeline can conditionally upload vs. serve locally — no code change needed to switch modes.
- `checkpoint_db_url` defaults to the app DB, but you can point it at a separate DB to isolate LangGraph's checkpoint tables.

---

## 7. Prompt Engineering — `prompts.py`

**File:** `backend/app/ERPScriptGenerator/prompts.py` (lines 1–48)

This file defines the three prompt components used to drive the GPT prompt-builder.

```python
# ── Layer 1: Fixed instruction (becomes "Instruction:" in the SLM prompt) ──
BASE_INSTRUCTION = (
    "Act as an ERP therapist. Generate an imaginal exposure script based on the "
    "following OCD obsession, compulsion, and feared consequence."
)
```

```python
# ── Layer 2: System message for building a FIRST-TIME prompt ──
PROMPT_BUILDER_SYSTEM = """You are a prompt normalization assistant for an OCD imaginal exposure generator.

Your task is NOT to write the final script.
Your task is to produce the exact prompt text that will be sent to a fine-tuned small model.

Rules:
1. Preserve these fields as the source of truth unless therapist feedback explicitly asks to change them:
   - obsession
   - compulsion
   - feared_consequence
   - subtype
2. exposure_type must remain "imaginal".
3. Keep the final prompt in this exact structure:

Instruction: <fixed instruction>
Input:
Obsession: ...
Compulsion: ...
Feared consequence: ...
Script intensity: ...
Exposure type: imaginal
Type: ...

4. If therapist feedback is present, use it only to refine how the prompt should steer the generator.
5. Do not output JSON. Output only the final prompt text.
"""
```

```python
# ── Layer 3: System message for REVISING a rejected prompt ──
REVISION_INTERPRETER_SYSTEM = """You are helping revise an imaginal exposure prompt.

The therapist rejected the generated script and provided feedback.
Do not overwrite the core case formulation unless the therapist clearly asks for it.

Your task:
- preserve obsession, compulsion, feared consequence, exposure type, subtype by default
- adjust prompt wording only enough to reflect therapist feedback
- keep the final result in the same prompt schema
- output only the revised final prompt text
"""
```

**Why three layers?**
The SLM (`nirbaan-erp-federated`) was fine-tuned on a specific prompt template. The GPT model acts as a "prompt normalizer" — it converts raw therapist input into the exact schema the SLM understands. This decouples the UX (flexible natural language input) from the SLM (strict template-based input).

---

## 8. GPT Prompt Builder — `gemini_builder.py`

**File:** `backend/app/ERPScriptGenerator/gemini_builder.py` (lines 1–108)

Despite the file name (`gemini_builder.py`), this module uses **GPT-5.2 via LangChain OpenAI** — the name is a legacy artifact.

```python
def get_llm():
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is missing")
    return ChatOpenAI(
        model="gpt-5.2",
        api_key=settings.OPENAI_API_KEY,
        temperature=0.1,     # near-deterministic; prompt structure must be consistent
    )
```

### `build_initial_prompt()` — lines 19–54

Called by `build_prompt_node` on **first generation** (no prior feedback).

```python
def build_initial_prompt(
    *,
    obsession: str,
    compulsion: str,
    feared_consequence: str,
    script_intensity: str,
    subtype: str | None,
) -> str:
    llm = get_llm()

    user = f"""Create the exact final prompt text for the generator model.

Fixed instruction:
{BASE_INSTRUCTION}

Locked fields:
Obsession: {obsession}
Compulsion: {compulsion}
Feared consequence: {feared_consequence}
Script intensity: {script_intensity}
Exposure type: imaginal
Type: {subtype or ""}

Return only the final prompt text.
"""

    msg = llm.invoke([
        SystemMessage(content=PROMPT_BUILDER_SYSTEM),
        HumanMessage(content=user),
    ])
    return msg.content.strip()
```

**What GPT does here**: Takes the raw fields and assembles them into the exact `Instruction: ... Input: ...` template the SLM expects, resolving phrasing ambiguities without changing the clinical content.

---

### `build_revised_prompt()` — lines 57–108

Called by `build_prompt_node` on every **revision** (when `therapist_feedback` is present in state).

```python
def build_revised_prompt(
    *,
    obsession: str, compulsion: str, feared_consequence: str,
    script_intensity: str, subtype: str | None,
    therapist_feedback: str,
    previous_prompt: str,
    previous_script: str,
) -> str:
    llm = get_llm()

    user = f"""Revise the final generator prompt based on therapist feedback.

Locked fields:
Obsession: {obsession}
Compulsion: {compulsion}
Feared consequence: {feared_consequence}
Script intensity: {script_intensity}
Exposure type: imaginal
Type: {subtype or ""}

Previous prompt:
{previous_prompt}

Previous generated script:
{previous_script}

Therapist feedback:
{therapist_feedback}

Return only the revised final prompt text.
"""

    msg = llm.invoke([
        SystemMessage(content=REVISION_INTERPRETER_SYSTEM),
        HumanMessage(content=user),
    ])
    return msg.content.strip()
```

**What GPT does here**: It sees the rejected script AND the therapist's written feedback, then rewrites only the prompt directives (e.g., "focus more on contamination fear") without altering the clinical case formulation (obsession, compulsion, etc.).

---

## 9. Local SLM Client — `ollama_client.py`

**File:** `backend/app/ERPScriptGenerator/ollama_client.py` (lines 1–31)

```python
def generate_script_with_ollama(prompt_text: str) -> str:
    """Send the finalized prompt to the fine-tuned local SLM via Ollama and
    return the generated imaginal exposure script text."""
    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate"
    payload = {
        "model": settings.OLLAMA_MODEL,   # "nirbaan-erp-federated"
        "prompt": prompt_text,
        "stream": False,                   # wait for complete response
    }
    try:
        response = requests.post(url, json=payload, timeout=120)   # 2-minute timeout
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(
            f"Ollama request failed ({settings.OLLAMA_BASE_URL}): {exc}"
        ) from exc

    data = response.json()
    script = data.get("response", "").strip()
    if not script:
        raise RuntimeError(
            f"Ollama returned an empty response for model '{settings.OLLAMA_MODEL}'"
        )
    return script
```

**Key points:**
- `stream: False` means the function blocks until the full script is generated (synchronous).
- The model `nirbaan-erp-federated` is a custom fine-tuned model — trained via Federated QLoRA on ERP therapy data (see `FTSLM/` folder).
- Timeout is 120 seconds to accommodate slower inference on low-end hardware.
- Both network error and empty response are converted to `RuntimeError` so the LangGraph node can handle them consistently.

---

## 10. LangGraph Agent — `graph.py`

**File:** `backend/app/ERPScriptGenerator/graph.py` (lines 1–287)

This is the core of the system — a **6-node stateful agent** with a human-in-the-loop interrupt.

### Node 1: `load_case_context` — lines 28–62

```python
def load_case_context(state: ImaginalGraphState) -> ImaginalGraphState:
    db = SessionLocal()
    try:
        erp_item = get_erp_item_or_raise(db, state["erp_item_id"])
        obsession  = erp_item.obsession
        compulsion = stringify_compulsions(erp_item.compulsions)   # JSON list → "comp1; comp2; comp3"

        thread_id = state["thread_id"]
        run = get_run_by_thread_id(db, thread_id)
        if not run:
            run = create_run(
                db,
                thread_id=thread_id,
                patient_id=state["patient_id"],
                therapist_id=state["therapist_id"],
                erp_item_id=state["erp_item_id"],
                obsession=obsession,
                compulsion=compulsion,
                feared_consequence=state["feared_consequence"],
                script_intensity=state["script_intensity"],
                subtype=state.get("subtype"),
            )

        return {
            "run_id":        run.id,
            "obsession":     obsession,
            "compulsion":    compulsion,
            "exposure_type": "imaginal",
            "status":        "building_prompt",
            "version_no":    run.revision_count,
        }
    finally:
        db.close()
```

**What it does:**
1. Fetches the `ERPItem` from the database to get the patient's obsession and compulsions (which are stored in the ERP module, not entered here).
2. Creates a new `ImaginalScriptRun` record **only if this is a fresh start** (idempotent: the `if not run` guard).
3. Returns the case context into state so subsequent nodes can use it without more DB hits.

---

### Node 2: `build_prompt_node` — lines 65–87

```python
def build_prompt_node(state: ImaginalGraphState) -> ImaginalGraphState:
    if state.get("therapist_feedback"):
        # REVISION PATH: use feedback to steer the revised prompt
        prompt_text = build_revised_prompt(
            obsession=state["obsession"],
            compulsion=state["compulsion"],
            feared_consequence=state["feared_consequence"],
            script_intensity=state["script_intensity"],
            subtype=state.get("subtype"),
            therapist_feedback=state["therapist_feedback"],
            previous_prompt=state.get("prompt_text", ""),
            previous_script=state.get("generated_script", ""),
        )
    else:
        # INITIAL PATH: build from scratch
        prompt_text = build_initial_prompt(
            obsession=state["obsession"],
            compulsion=state["compulsion"],
            feared_consequence=state["feared_consequence"],
            script_intensity=state["script_intensity"],
            subtype=state.get("subtype"),
        )

    return {
        "prompt_text": prompt_text,
        "status": "generating",
    }
```

**What it does:**
- Checks `therapist_feedback` in state to decide which prompt-building function to call.
- Calls GPT-5.2 (via `gemini_builder.py`) to build or revise the normalized SLM prompt.
- Returns the finalized prompt text into state.

---

### Node 3: `generate_script_node` — lines 89–128

```python
def generate_script_node(state: ImaginalGraphState) -> ImaginalGraphState:
    script = generate_script_with_ollama(state["prompt_text"])    # call local SLM

    db = SessionLocal()
    try:
        run = get_run_by_thread_id(db, state["thread_id"])
        version_no = run.revision_count if run else state.get("version_no", 1)
        save_version(
            db,
            run_id=run.id,
            version_no=version_no,
            prompt_text=state["prompt_text"],
            generated_script=script,
            therapist_feedback=state.get("therapist_feedback"),
            approved=None,                # null until therapist decides
        )
        update_run_latest(
            db,
            run=run,
            latest_prompt_text=state["prompt_text"],
            latest_script_text=script,
            revision_count=version_no,
            status="pending_review",
        )
    finally:
        db.close()

    return {
        "generated_script": script,
        "status": "pending_review",
    }
```

**What it does:**
1. Calls the local Ollama SLM with the normalized prompt text.
2. Saves an immutable `ImaginalScriptVersion` record (audit log entry).
3. Updates the `ImaginalScriptRun` with the latest prompt + script + status.
4. Returns the script into state.

---

### Node 4: `therapist_review_node` — lines 130–167

This is the **human-in-the-loop node** — the graph pauses execution here.

```python
def therapist_review_node(
    state: ImaginalGraphState,
) -> Command[Literal["finalize_approved_node", "prepare_revision_node"]]:
    decision = interrupt({
        "action": "review_script",
        "thread_id": state["thread_id"],
        "run_id": state["run_id"],
        "version_no": state["version_no"],
        "obsession": state["obsession"],
        "compulsion": state["compulsion"],
        "feared_consequence": state["feared_consequence"],
        "script_intensity": state["script_intensity"],
        "exposure_type": state["exposure_type"],
        "subtype": state.get("subtype"),
        "generated_script": state["generated_script"],
        "message": "Therapist must approve or reject this imaginal exposure script.",
    })

    approved = bool(decision.get("approved", False))
    feedback = decision.get("feedback")

    if approved:
        return Command(
            update={"approved": True, "therapist_feedback": None, "status": "approved_pending_audio"},
            goto="finalize_approved_node",
        )

    return Command(
        update={"approved": False, "therapist_feedback": feedback or "", "status": "revising"},
        goto="prepare_revision_node",
    )
```

**What it does:**
- Calls LangGraph's `interrupt()` — this **serializes the entire state to the PostgreSQL checkpoint** and raises a special exception that pauses execution.
- The `interrupt()` payload is the data that will be visible when the graph is inspected (not directly returned to the API right now).
- The graph remains in this paused state indefinitely until `graph.invoke(Command(resume=...))` is called.
- Upon resume, `decision` is populated with `{approved: bool, feedback: str | None}`.
- Uses `Command(update=..., goto=...)` — a LangGraph primitive that simultaneously: (a) updates the state dict and (b) directs which node to go to next (bypassing the normal edge graph).

---

### Node 5: `prepare_revision_node` — lines 169–188

```python
def prepare_revision_node(state: ImaginalGraphState) -> ImaginalGraphState:
    db = SessionLocal()
    try:
        run = get_run_by_thread_id(db, state["thread_id"])
        next_version = (run.revision_count + 1) if run else (state.get("version_no", 1) + 1)
        if run:
            run.revision_count = next_version
            run.status = "revising"
            db.commit()
    finally:
        db.close()

    return {
        "version_no": next_version,
        "status": "building_prompt",
    }
```

**What it does:**
- Increments `revision_count` in both DB and state.
- Returns updated state, then the graph follows the `prepare_revision_node → build_prompt_node` edge back to Node 2 — back into the loop with `therapist_feedback` now set.

---

### Node 6: `finalize_approved_node` — lines 191–240

```python
def finalize_approved_node(state: ImaginalGraphState) -> ImaginalGraphState:
    local_audio_path = synthesize_with_piper(state["generated_script"])   # TTS → WAV

    audio_url = local_audio_path   # default: serve local WAV
    audio_key = None

    if settings.has_r2_config:
        object_key = build_audio_object_key(
            patient_id=state["patient_id"],
            run_id=state["run_id"],
            extension=".wav",
        )
        uploaded = upload_file_to_r2(
            local_path=local_audio_path,
            object_key=object_key,
            content_type="audio/wav",
        )
        audio_url = uploaded["url"]      # public R2 URL
        audio_key = uploaded["object_key"]

        try:
            if os.path.exists(local_audio_path):
                os.remove(local_audio_path)    # clean up local file after upload
        except Exception:
            pass

    db = SessionLocal()
    try:
        run = get_run_by_thread_id(db, state["thread_id"])
        approved = approve_run(
            db,
            run=run,
            approved_script=state["generated_script"],
            audio_url=audio_url,
            audio_key=audio_key,
        )
        latest_version = run.versions[-1]
        latest_version.approved = True    # mark this version as the approved one
        db.commit()
        approved_script_id = approved.id   # must read while session is open (avoid DetachedInstanceError)
    finally:
        db.close()

    return {
        "audio_path":         audio_url,
        "approved_script_id": approved_script_id,
        "status":             "done",
    }
```

**What it does:**
1. Runs Piper TTS to synthesize a WAV from the approved script text.
2. If R2 is configured: uploads the WAV to Cloudflare R2 bucket, gets a public URL, deletes the local file.
3. Calls `approve_run()` — creates `ApprovedImaginalScript` record + updates the run to status `"approved"`.
4. Marks the `ImaginalScriptVersion.approved = True` for the accepted version.
5. Returns final outputs into state.

---

### Graph Assembly — lines 242–287

```python
def build_graph():
    builder = StateGraph(ImaginalGraphState)

    # Add all 6 nodes
    builder.add_node("load_case_context",     load_case_context)
    builder.add_node("build_prompt_node",     build_prompt_node)
    builder.add_node("generate_script_node",  generate_script_node)
    builder.add_node("therapist_review_node", therapist_review_node)
    builder.add_node("prepare_revision_node", prepare_revision_node)
    builder.add_node("finalize_approved_node",finalize_approved_node)

    # Define edges (static routing)
    builder.add_edge(START,                    "load_case_context")
    builder.add_edge("load_case_context",      "build_prompt_node")
    builder.add_edge("build_prompt_node",      "generate_script_node")
    builder.add_edge("generate_script_node",   "therapist_review_node")
    builder.add_edge("prepare_revision_node",  "build_prompt_node")    # ← the loop-back edge
    builder.add_edge("finalize_approved_node", END)

    return builder


def compile_graph():
    # Opens a persistent connection to PostgreSQL for checkpoint storage
    checkpointer_cm = PostgresSaver.from_conn_string(settings.checkpoint_db_url)
    checkpointer = checkpointer_cm.__enter__()
    checkpointer.setup()   # creates LangGraph checkpoint tables if they don't exist
    graph = build_graph().compile(checkpointer=checkpointer)
    return graph, checkpointer_cm
```

> **`therapist_review_node`'s dynamic routing** uses `Command(goto=...)`, not `add_conditional_edges()`. This is why there are no conditional edges in `build_graph()` — the routing is handled inside the node itself via the `Command` return type.

---

## 11. Repository Layer — `repository.py`

**File:** `backend/app/ERPScriptGenerator/repository.py` (lines 1–160)

All database operations are isolated here. Nodes don't write SQL directly.

### Key Functions

| Function | Lines | Purpose |
|---|---|---|
| `get_erp_item_or_raise(db, id)` | 13–17 | Fetch `ERPItem` from erp module; raises `ValueError` if missing |
| `stringify_compulsions(compulsions)` | 20–23 | Converts JSON array `["wash hands", "check door"]` → `"wash hands; check door"` |
| `create_run(db, ...)` | 26–58 | INSERT new `ImaginalScriptRun`; initial status = `"pending_review"`, revision_count = 1 |
| `get_run_by_thread_id(db, thread_id)` | 61–63 | SELECT by thread; returns `None` if not found |
| `save_version(db, ...)` | 66–85 | INSERT immutable `ImaginalScriptVersion` |
| `update_run_latest(db, ...)` | 88–104 | UPDATE run's prompt/script/revision/status |
| `approve_run(db, ...)` | 107–144 | INSERT `ApprovedImaginalScript` + UPDATE `ImaginalScriptRun` approved fields |
| `list_approved_for_patient(db, id)` | 147–154 | SELECT all approved scripts for a patient (desc by date) |
| `get_approved_by_id(db, id)` | 157–158 | SELECT single by PK |
| `list_approved_for_erp_item(db, id)` | 160+  | SELECT by erp_item_id |

### `approve_run()` in detail — lines 107–144

```python
def approve_run(db, *, run, approved_script, audio_url, audio_key) -> ApprovedImaginalScript:
    approved = ApprovedImaginalScript(
        patient_id=run.patient_id,
        therapist_id=run.therapist_id,
        erp_item_id=run.erp_item_id,
        run_id=run.id,
        subtype=run.subtype,
        approved_script=approved_script,
        audio_path=audio_url,
        audio_key=audio_key,
        metadata_json={           # ← snapshot for denormalized read access
            "obsession":          run.obsession,
            "compulsion":         run.compulsion,
            "feared_consequence": run.feared_consequence,
            "script_intensity":   run.script_intensity,
            "exposure_type":      run.exposure_type,
            "subtype":            run.subtype,
        },
    )
    db.add(approved)
    db.commit()
    db.refresh(approved)

    # Mirror key fields back onto the run for fast lookup
    run.approved_script_text = approved_script
    run.approved_audio_path  = audio_url
    run.approved_audio_key   = audio_key
    run.approved_script_id   = approved.id
    run.status               = "approved"
    db.commit()
    db.refresh(run)
    return approved
```

---

## 12. Service Layer — `service.py`

**File:** `backend/app/ERPScriptGenerator/service.py` (lines 1–35)

Thin wrappers that bridge the router (HTTP layer) and the graph (LangGraph layer).

```python
def start_run(graph, payload: StartImaginalRunRequest) -> dict:
    # Generate a collision-resistant thread_id: "imaginal-{pid}-{iid}-{tid}-{8hex}"
    thread_id = f"imaginal-{payload.patient_id}-{payload.erp_item_id}-{payload.therapist_id}-{uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}}

    graph.invoke(
        {
            "thread_id":         thread_id,
            "patient_id":        payload.patient_id,
            "therapist_id":      payload.therapist_id,
            "erp_item_id":       payload.erp_item_id,
            "feared_consequence":payload.feared_consequence,
            "script_intensity":  payload.script_intensity,
            "subtype":           payload.subtype,
        },
        config=config,
    )
    return config    # ← caller uses thread_id from this to query the DB
```

```python
def resume_run(graph, payload: ReviewImaginalRunRequest) -> dict:
    config = {"configurable": {"thread_id": payload.thread_id}}
    decision = {
        "approved": payload.approved,
        "feedback": payload.feedback,
    }
    # Command(resume=...) is LangGraph's way of resuming from an interrupt
    graph.invoke(Command(resume=decision), config=config)
    return config
```

> `graph.invoke()` with a `Command(resume=...)` resumes execution from the exact point of the last `interrupt()` call.  The `decision` dict is returned as the value of `interrupt(...)` in `therapist_review_node`.

---

## 13. API Schemas — `schemas.py`

**File:** `backend/app/ERPScriptGenerator/schemas.py` (lines 1–49)

```python
class StartImaginalRunRequest(BaseModel):
    patient_id:    int
    therapist_id:  int
    erp_item_id:   int
    feared_consequence: str = Field(min_length=3)          # validated at API boundary
    script_intensity:   str = Field(description="Examples: 4/10, 7/10, 10/10")
    subtype: str | None = None
```

```python
class ReviewImaginalRunRequest(BaseModel):
    thread_id: str
    approved:  bool
    feedback:  str | None = None    # required only on rejection
```

```python
class ImaginalRunResponse(BaseModel):
    thread_id:          str
    run_id:             int
    status:             str
    version_no:         int
    script_text:        str
    interrupt_required: bool = True    # always True after /start
```

```python
class ResumeResult(BaseModel):
    thread_id:          str
    run_id:             int
    status:             str
    version_no:         int
    script_text:        str | None = None
    interrupt_required: bool
    audio_path:         str | None = None    # populated on approval
    approved_script_id: int | None = None    # populated on approval
```

```python
class ApprovedImaginalScriptItem(BaseModel):
    id:              int
    run_id:          int
    patient_id:      int
    erp_item_id:     int
    approved_script: str
    audio_path:      str | None
    subtype:         str | None
    created_at:      datetime
```

---

## 14. FastAPI Router — `router.py`

**File:** `backend/app/ERPScriptGenerator/router.py` (lines 1–166)

```python
router = APIRouter(prefix="/imaginal-generator", tags=["Imaginal Exposure Generator"])
```

### `POST /imaginal-generator/start` — lines 35–56

```python
@router.post("/start", response_model=ImaginalRunResponse)
def start_imaginal_generation(payload: StartImaginalRunRequest, request: Request, db: Session = Depends(get_db)):
    graph = get_graph(request)           # pulls graph from app.state (set at startup)
    config = start_run(graph, payload)   # invokes graph → pauses at interrupt

    thread_id = config["configurable"]["thread_id"]
    run = get_run_by_thread_id(db, thread_id)
    if not run:
        raise HTTPException(status_code=500, detail="Run was not created")

    return ImaginalRunResponse(
        thread_id=thread_id,
        run_id=run.id,
        status=run.status,
        version_no=run.revision_count,
        script_text=run.latest_script_text or "",
        interrupt_required=True,    # always True — graph paused at review node
    )
```

> The response is built by **reading from the DB** (not from graph state). This is intentional: the graph runs in the same synchronous call and commits to DB before returning. The DB is the source of truth for the HTTP response.

---

### `POST /imaginal-generator/review` — lines 58–102

```python
@router.post("/review", response_model=ResumeResult)
def review_imaginal_generation(payload: ReviewImaginalRunRequest, request: Request, db: Session = Depends(get_db)):
    graph = get_graph(request)

    run = get_run_by_thread_id(db, payload.thread_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    resume_run(graph, payload)    # resumes graph from interrupt — runs to next pause or END

    # CRITICAL: expire the SQLAlchemy identity-map cache
    # The graph nodes use separate DB sessions and committed changes externally.
    # Without expire_all(), this session returns stale cached data.
    db.expire_all()
    refreshed = get_run_by_thread_id(db, payload.thread_id)

    if refreshed.status == "approved":
        return ResumeResult(
            thread_id=payload.thread_id,
            run_id=refreshed.id,
            status=refreshed.status,
            version_no=refreshed.revision_count,
            script_text=refreshed.approved_script_text,
            interrupt_required=False,            # graph is done
            audio_path=refreshed.approved_audio_path,
            approved_script_id=refreshed.approved_script_id,
        )

    # Rejected → new version generated → waiting for next review
    return ResumeResult(
        thread_id=payload.thread_id,
        run_id=refreshed.id,
        status=refreshed.status,
        version_no=refreshed.revision_count,
        script_text=refreshed.latest_script_text,
        interrupt_required=True,                 # still paused at review node
    )
```

> **`db.expire_all()`** is a subtle but critical line. The graph nodes each create their own `SessionLocal()`, commit changes, and close. The router's `db` session has identity-map cached objects that don't see these external commits. `expire_all()` marks all cached objects as expired, forcing them to reload from the DB on next access.

---

### `GET /imaginal-generator/audio/{script_id}` — lines 141–166

```python
@router.get("/audio/{script_id}")
def stream_audio(script_id: int, db: Session = Depends(get_db)):
    script = get_approved_by_id(db, script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    # R2 path: generate time-limited presigned URL and redirect
    if script.audio_key:
        if settings.has_r2_config:
            url = generate_presigned_download_url(script.audio_key)
            return RedirectResponse(url=url, status_code=307)  # 307 = Temporary Redirect

    # Local file fallback
    if script.audio_path and os.path.isfile(script.audio_path):
        return FileResponse(
            script.audio_path,
            media_type="audio/wav",
            filename=os.path.basename(script.audio_path),
        )

    raise HTTPException(status_code=404, detail="Audio file not available")
```

**Why `307` redirect instead of streaming?**  
Presigned R2 URLs are direct CDN links. Redirecting lets the browser download directly from R2's edge network instead of proxying through the Python server — much more efficient for audio files.

---

## 15. Text-To-Speech — `piper_tts.py`

**File:** `backend/app/ERPScriptGenerator/piper_tts.py` (lines 1–80)

```python
# Resolve voice model path regardless of working directory
_VOICES_DIR = Path(__file__).parent / "voices"
_DEFAULT_VOICE = _VOICES_DIR / "en_US-lessac-medium.onnx"
RESOLVED_MODEL_PATH = str(_DEFAULT_VOICE if _DEFAULT_VOICE.exists() else _MODEL_PATH)
```

```python
def prepare_text_for_audio(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = text.replace("\n", "\n\n")    # double newlines → pauses in speech
    return text.strip()
```

```python
def synthesize_with_piper(text: str) -> str:
    output_dir  = ensure_output_dir()
    output_name = f"{uuid4().hex}.wav"      # random UUID filename prevents collisions
    output_path = os.path.join(output_dir, output_name)

    prepared = prepare_text_for_audio(text)

    cmd = [
        "piper",
        "--model",       RESOLVED_MODEL_PATH,
        "--output_file", output_path,
        "--length_scale","1.08",     # 8% slower than normal — more therapeutic pacing
    ]

    proc = subprocess.run(
        cmd,
        input=prepared.encode("utf-8"),    # text piped to stdin
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    if proc.returncode != 0:
        raise RuntimeError(
            f"Piper failed with code {proc.returncode}: {proc.stderr.decode('utf-8', errors='ignore')}"
        )

    return output_path    # local WAV file path
```

**Design notes:**
- `length_scale=1.08` makes speech 8% slower, which is more comfortable for therapeutic listening.
- `uuid4().hex` for filename prevents race conditions if two scripts are synthesized simultaneously.
- `input=prepared.encode("utf-8")` sends the text via stdin (not a temp file) — cleaner subprocess usage.
- The model `en_US-lessac-medium.onnx` is a high-quality American English neural TTS voice.

---

## 16. Cloud Storage — `r2_storage.py`

**File:** `backend/app/ERPScriptGenerator/r2_storage.py` (lines 1–80)

```python
def _get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.R2_ENDPOINT_URL,         # e.g. https://{account_id}.r2.cloudflarestorage.com
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),        # R2 requires v4 signatures
        region_name="auto",                             # R2 doesn't use regions — "auto" is required
    )
```

```python
def build_audio_object_key(*, patient_id, run_id, extension=".wav") -> str:
    # Format: imaginal_audio/patient_42/run_99/a1b2c3d4e5f6.wav
    return f"imaginal_audio/patient_{patient_id}/run_{run_id}/{uuid4().hex}{extension}"
```

```python
def upload_file_to_r2(*, local_path, object_key, content_type=None) -> dict:
    client = _get_s3_client()
    guessed_type, _ = mimetypes.guess_type(local_path)
    content_type = content_type or guessed_type or "application/octet-stream"

    with open(local_path, "rb") as f:
        client.upload_fileobj(
            Fileobj=f,
            Bucket=settings.R2_BUCKET_NAME,
            Key=object_key,
            ExtraArgs={"ContentType": content_type},
        )
    return {"object_key": object_key, "url": build_r2_public_url(object_key)}
```

```python
def generate_presigned_download_url(object_key: str) -> str:
    client = _get_s3_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.R2_BUCKET_NAME, "Key": object_key},
        ExpiresIn=settings.R2_PRESIGNED_URL_EXPIRY,    # default: 3600 seconds
    )
```

**Security note:** Presigned URLs are time-limited — they expire after 1 hour by default. This prevents permanent public exposure of patient audio files. When a patient plays a script, the browser is redirected to a fresh presigned URL each time.

---

## 17. App Initialization — `main.py`

**File:** `backend/app/main.py` — relevant sections for the script generator

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── STARTUP ──
    graph, checkpointer_cm = compile_graph()   # from ERPScriptGenerator.graph
    app.state.imaginal_graph       = graph
    app.state.imaginal_checkpointer_cm = checkpointer_cm
    print("✅ Imaginal Script Generator graph initialized.")

    yield  # app runs here

    # ── SHUTDOWN ──
    checkpointer_cm.__exit__(None, None, None)   # close PostgreSQL checkpointer connection
```

**Why store in `app.state`?**  
The compiled LangGraph object holds the PostgreSQL checkpointer connection pool. Creating it once at startup (and storing globally on `app.state`) means every request shares the same compiled graph and connection pool — no overhead per-request.

The router retrieves it via:
```python
def get_graph(request: Request):
    graph = getattr(request.app.state, "imaginal_graph", None)
    if graph is None:
        raise HTTPException(status_code=500, detail="Imaginal graph is not initialized")
    return graph
```

---

## 18. Frontend API Client — `imaginal-generator.api.js`

**File:** `frontend/src/api/imaginal-generator.api.js` (lines 1–45)

```javascript
import axiosInstance from './axios';

const API_BASE = 'http://127.0.0.1:8000';

// Returns the backend URL for audio streaming/redirect
export const getAudioUrl = (scriptId) =>
  `${API_BASE}/imaginal-generator/audio/${scriptId}`;

// POST /imaginal-generator/start
export const startImaginalRun = async (payload) => {
  try {
    const response = await axiosInstance.post('/imaginal-generator/start', payload);
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to start imaginal script generation';
  }
};

// POST /imaginal-generator/review
export const reviewImaginalRun = async (payload) => {
  try {
    const response = await axiosInstance.post('/imaginal-generator/review', payload);
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to submit review';
  }
};

// GET /imaginal-generator/patient/{patientId}/approved
export const listPatientApprovedScripts = async (patientId) => {
  try {
    const response = await axiosInstance.get(`/imaginal-generator/patient/${patientId}/approved`);
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to fetch approved scripts';
  }
};

// GET /imaginal-generator/erp-item/{erpItemId}/approved
export const listApprovedByItem = async (erpItemId) => {
  try {
    const response = await axiosInstance.get(`/imaginal-generator/erp-item/${erpItemId}/approved`);
    return { data: response.data };
  } catch (error) {
    throw error.response?.data?.detail || 'Failed to fetch scripts for this item';
  }
};
```

---

## 19. Therapist UI — `TherapistImaginalScriptPage.jsx`

**File:** `frontend/src/pages/TherapistImaginalScriptPage.jsx` (lines 1–369)

### State variables (lines 22–37)

```javascript
const { patientId, itemId } = useParams();        // from URL: /imaginal/patient/:patientId/item/:itemId
const location = useLocation();

// Context data passed via React Router state (from ObsessionList page)
const obsession  = location.state?.obsession  || '';
const compulsions= location.state?.compulsions|| [];

// Form fields
const [sgFeared,   setSgFeared]   = useState('');    // feared_consequence
const [sgIntensity,setSgIntensity]= useState('');    // script_intensity (e.g. "7/10")
const [sgSubtype,  setSgSubtype]  = useState('');    // subtype (optional)

// Run state
const [sgRun,     setSgRun]     = useState(null);    // ImaginalRunResponse or ResumeResult
const [sgLoading, setSgLoading] = useState(false);
const [sgError,   setSgError]   = useState('');

// Reject feedback
const [sgFeedback,        setSgFeedback]        = useState('');
const [sgFeedbackVisible, setSgFeedbackVisible] = useState(false);

// Tabs
const [activeTab, setActiveTab] = useState('generator');

// Past scripts tab
const [pastScripts, setPastScripts] = useState([]);
const [expandedScript, setExpandedScript] = useState(null);
```

### `handleGenerate()` — lines 65–81

```javascript
const handleGenerate = async () => {
  setSgError('');
  setSgLoading(true);
  try {
    const { data } = await startImaginalRun({
      patient_id:        Number(patientId),
      therapist_id:      Number(user?.id),
      erp_item_id:       Number(itemId),
      feared_consequence:sgFeared.trim(),
      script_intensity:  sgIntensity.trim(),
      subtype:           sgSubtype.trim() || null,
    });
    setSgRun(data);    // data = ImaginalRunResponse (interrupt_required: true)
  } catch (err) {
    setSgError(typeof err === 'string' ? err : 'Failed to start generation.');
  } finally {
    setSgLoading(false);
  }
};
```

### `handleApprove()` — lines 83–96

```javascript
const handleApprove = async () => {
  setSgLoading(true);
  try {
    const { data } = await reviewImaginalRun({
      thread_id: sgRun.thread_id,
      approved: true,
    });
    setSgRun(data);    // data = ResumeResult (interrupt_required: false, audio_path set)
  } catch (err) {
    setSgError(typeof err === 'string' ? err : 'Failed to approve script.');
  } finally {
    setSgLoading(false);
  }
};
```

### `handleReject()` — lines 98–115

```javascript
const handleReject = async () => {
  setSgLoading(true);
  setSgFeedbackVisible(false);
  try {
    const { data } = await reviewImaginalRun({
      thread_id: sgRun.thread_id,
      approved:  false,
      feedback:  sgFeedback.trim(),
    });
    setSgRun(data);    // data = ResumeResult (interrupt_required: true, version_no incremented)
    setSgFeedback('');
  } catch (err) {
    setSgError(typeof err === 'string' ? err : 'Failed to submit feedback.');
  } finally {
    setSgLoading(false);
  }
};
```

### UI Rendering logic (lines 230–310)

The UI has **4 conditional states** based on `sgRun` and `sgLoading`:

| Condition | UI Shown |
|---|---|
| `!sgRun && !sgLoading` | **Form**: feared_consequence textarea, intensity input, subtype input, Generate button |
| `sgLoading` | **Spinner**: "Running LangGraph agent… this may take a moment." |
| `sgRun && sgRun.interrupt_required` | **Review**: script text in `<pre>`, Approve + Reject buttons |
| `sgRun && !sgRun.interrupt_required` | **Done**: success message + `<audio>` player + Generate Another button |

```jsx
{/* Done state — lines 280–310 */}
{sgRun && !sgLoading && !sgRun.interrupt_required && (
  <div className="tisp-done">
    <div className="tisp-done-icon">✓</div>
    <h3>Script Approved</h3>
    <p>The script has been saved and audio generated for the patient.</p>
    {sgRun.approved_script_id && (
      <div className="tisp-audio-box">
        <span className="tisp-label">Preview Audio</span>
        <audio
          controls
          src={getAudioUrl(sgRun.approved_script_id)}
          className="tisp-audio-player"
        />
      </div>
    )}
    <button onClick={resetGenerator}>Generate Another Script</button>
  </div>
)}
```

---

## 20. Patient UI — `PatientImaginalScripts.jsx`

**File:** `frontend/src/pages/PatientImaginalScripts.jsx`

- Calls `listPatientApprovedScripts(user.id)` on mount.
- Groups scripts by `erp_item_id` to show scripts organized under each obsession.
- Each script card is expandable — shows script text + audio player.
- Audio source: `getAudioUrl(script.id)` → backend redirects to R2 presigned URL.

---

## 21. Route Definitions — `AppRoutes.jsx`

**File:** `frontend/src/routes/AppRoutes.jsx` — lines 270–315

```
/therapist/dashboard/imaginal
  → <TherapistImaginalPatientList />         ← step 1: pick a patient

/therapist/dashboard/imaginal/patient/:patientId
  → <TherapistImaginalObsessionList />       ← step 2: pick an obsession

/therapist/dashboard/imaginal/patient/:patientId/item/:itemId
  → <TherapistImaginalScriptPage />          ← step 3: generate script

/patient/dashboard/imaginal-scripts
  → <PatientImaginalScripts />               ← patient views approved scripts
```

All therapist routes are guarded (therapist role only). Patient route is guarded (patient role only).

---

## 22. Complete End-to-End Workflow Trace

```
THERAPIST navigates:
  /therapist/dashboard/imaginal
    → selects patient → navigate with {patientName, patientEmail}

  /therapist/dashboard/imaginal/patient/42
    → selects obsession (ERP item 12) → navigate with {obsession, compulsions}

  /therapist/dashboard/imaginal/patient/42/item/12
    → sees obsession + compulsions displayed
    → fills form: feared_consequence="I'll contaminate my family",
                  script_intensity="7/10",
                  subtype="contamination"
    → clicks "Generate Script"

─────────────────────────────────────────────────────────
FRONTEND (TherapistImaginalScriptPage.jsx #handleGenerate):
  POST /imaginal-generator/start
  Body: {patient_id:42, therapist_id:5, erp_item_id:12,
         feared_consequence:"I'll contaminate...",
         script_intensity:"7/10", subtype:"contamination"}

─────────────────────────────────────────────────────────
ROUTER (router.py #start_imaginal_generation):
  → calls service.start_run(graph, payload)

SERVICE (service.py #start_run):
  → thread_id = "imaginal-42-12-5-a3f8c21b"
  → config    = {configurable: {thread_id: "imaginal-42-12-5-a3f8c21b"}}
  → graph.invoke({thread_id, patient_id:42, ...}, config)

─────────────────────────────────────────────────────────
GRAPH executes synchronously:

  NODE 1: load_case_context
    DB: SELECT erp_items WHERE id=12
      → obsession="Fear of contaminating family"
      → compulsions=["wash hands 50x", "avoid touching doorknobs"]
    DB: INSERT imaginal_script_runs → run.id=99
    Returns: {run_id:99, obsession:"...", compulsion:"wash hands 50x; avoid...",
              exposure_type:"imaginal", status:"building_prompt", version_no:1}

  NODE 2: build_prompt_node
    No therapist_feedback → calls build_initial_prompt()
    GPT-5.2 call:
      System: PROMPT_BUILDER_SYSTEM
      User: "Create exact prompt... Obsession: Fear of contaminating... Intensity: 7/10..."
      GPT response:
      "Instruction: Act as an ERP therapist. Generate an imaginal exposure script...
       Input:
       Obsession: Fear of contaminating family
       Compulsion: wash hands 50x; avoid touching doorknobs
       Feared consequence: I'll contaminate my family...
       Script intensity: 7/10
       Exposure type: imaginal
       Type: contamination"
    Returns: {prompt_text: "[above]", status:"generating"}

  NODE 3: generate_script_node
    POST http://localhost:11434/api/generate
      {model:"nirbaan-erp-federated", prompt:"[above]", stream:false}
    SLM returns: "You reach for the door handle..."  (full imaginal script)
    DB: INSERT imaginal_script_versions (run_id=99, version_no=1, prompt="...", script="...")
    DB: UPDATE imaginal_script_runs SET latest_script_text="...", status="pending_review"
    Returns: {generated_script:"You reach for the door handle...", status:"pending_review"}

  NODE 4: therapist_review_node
    interrupt({action:"review_script", generated_script:"...", ...})
    *** GRAPH PAUSES HERE — state serialized to PostgreSQL ***
    graph.invoke() returns to service.py

─────────────────────────────────────────────────────────
SERVICE returns config to ROUTER
ROUTER queries DB: get_run_by_thread_id("imaginal-42-12-5-a3f8c21b")
ROUTER returns HTTP 200:
  {thread_id:"imaginal-42-12-5-a3f8c21b", run_id:99, status:"pending_review",
   version_no:1, script_text:"You reach for the door handle...", interrupt_required:true}

FRONTEND: setSgRun(data) → shows script in <pre> + Approve/Reject buttons

─────────────────────────────────────────────────────────
SCENARIO A: THERAPIST APPROVES

FRONTEND (handleApprove):
  POST /imaginal-generator/review
  Body: {thread_id:"imaginal-42-12-5-a3f8c21b", approved:true}

ROUTER: calls resume_run(graph, payload)
SERVICE:  graph.invoke(Command(resume={approved:true, feedback:null}), config)

GRAPH resumes in therapist_review_node:
  decision = {approved:true, feedback:null}
  Returns Command(update={approved:True, status:"approved_pending_audio"},
                  goto="finalize_approved_node")

  NODE 6: finalize_approved_node
    piper synthesize_with_piper("You reach for the door handle...")
      → subprocess: piper --model en_US-lessac-medium.onnx --output_file /media/imaginal_audio/{uuid}.wav
      → returns: "/path/to/{uuid}.wav"
    R2 upload:
      object_key = "imaginal_audio/patient_42/run_99/{uuid}.wav"
      uploads WAV → Cloudflare R2
      audio_url = "https://{account}.r2.cloudflarestorage.com/{bucket}/imaginal_audio/..."
      deletes local file
    DB: INSERT approved_imaginal_scripts (id=145, patient_id=42, ...)
    DB: UPDATE imaginal_script_runs SET status="approved", approved_script_id=145
    DB: UPDATE imaginal_script_versions SET approved=True
    Returns: {audio_path:"https://...", approved_script_id:145, status:"done"}

  GRAPH reaches END

ROUTER: db.expire_all(); refreshed = get_run_by_thread_id(...)
  refreshed.status == "approved" → returns ResumeResult:
  {thread_id:"...", run_id:99, status:"approved", version_no:1,
   script_text:"You reach for the door handle...",
   interrupt_required:false,
   audio_path:"https://r2.../imaginal_audio/...",
   approved_script_id:145}

FRONTEND: setSgRun(data)
  → sgRun.interrupt_required = false → shows "Script Approved" + audio player

─────────────────────────────────────────────────────────
SCENARIO B: THERAPIST REJECTS

FRONTEND (handleReject):
  POST /imaginal-generator/review
  Body: {thread_id:"...", approved:false, feedback:"Too graphic, focus more on contamination"}

GRAPH resumes in therapist_review_node:
  Returns Command(update={approved:False, therapist_feedback:"Too graphic...", status:"revising"},
                  goto="prepare_revision_node")

  NODE 5: prepare_revision_node
    DB: UPDATE imaginal_script_runs SET revision_count=2, status="revising"
    Returns: {version_no:2, status:"building_prompt"}

  NODE 2: build_prompt_node  ← loops back
    therapist_feedback is set → calls build_revised_prompt()
    GPT-5.2 call with REVISION_INTERPRETER_SYSTEM:
      includes previous_prompt, previous_script, therapist_feedback
      returns revised prompt (less graphic, more focus on contamination)

  NODE 3: generate_script_node
    POST to Ollama with revised prompt
    SLM returns: "You're washing your hands again..." (revised script)
    DB: INSERT imaginal_script_versions (version_no=2, ...)
    DB: UPDATE imaginal_script_runs (latest_script_text="...", revision_count=2)

  NODE 4: therapist_review_node
    interrupt({...new script...})
    *** PAUSES AGAIN ***

ROUTER returns:
  {interrupt_required:true, version_no:2, script_text:"You're washing your hands again..."}

FRONTEND: setSgRun(data) → shows new script at "Version 2" + Approve/Reject
```

---

## 23. LangGraph Node Execution Flow

```
START
  │
  ▼
load_case_context ──── DB: get ERPItem, create ImaginalScriptRun
  │                     State: +run_id, +obsession, +compulsion, version_no=1
  ▼
build_prompt_node ──── GPT-5.2: normalize prompt
  │  ▲                  State: +prompt_text
  │  │ (loop on reject)
  ▼  │
generate_script_node ─ Ollama SLM: generate script
  │                     DB: save ImaginalScriptVersion, update run
  │                     State: +generated_script
  ▼
therapist_review_node ─ interrupt() → PAUSE → wait for Command(resume=...)
  │                     On resume: reads {approved, feedback}
  ├── approved=True  ──→ Command(goto="finalize_approved_node")
  │                     State: +approved=True
  └── approved=False ──→ Command(goto="prepare_revision_node")
                         State: +therapist_feedback, +status="revising"
                         │
                         ▼
                    prepare_revision_node ─ DB: increment revision_count
                         │                  State: version_no += 1
                         └──────────────────► build_prompt_node (loop)

finalize_approved_node ─ Piper TTS → WAV
  │                       R2 upload → delete local
  │                       DB: create ApprovedImaginalScript, update run
  │                       State: +audio_path, +approved_script_id, status="done"
  ▼
END
```

---

## 24. Revision Loop Deep Dive

Each revision cycle:

1. `therapist_review_node` receives `Command(resume={approved:false, feedback:"..."})`.
2. `Command(update={therapist_feedback:...}, goto="prepare_revision_node")` fires.
3. `prepare_revision_node` increments `revision_count` in DB and state.
4. Edge `prepare_revision_node → build_prompt_node` fires.
5. `build_prompt_node` detects `state["therapist_feedback"]` is set → calls `build_revised_prompt()`.
6. GPT-5.2 receives: the locked case formulation + previous prompt + previous script + feedback.
7. GPT outputs a revised prompt that steers the SLM differently.
8. `generate_script_node` runs the revised prompt through Ollama.
9. New `ImaginalScriptVersion` inserted with `version_no=2` (or 3, 4…).
10. `run.revision_count` updated in DB.
11. `therapist_review_node` fires again — new interrupt → another pause.

**There is no hard limit on revisions** — the loop continues until the therapist approves.

State after N revisions:

| Field | After revision N |
|---|---|
| `version_no` | N |
| `prompt_text` | Latest GPT-built prompt (for revision N) |
| `generated_script` | Latest SLM output |
| `therapist_feedback` | Latest rejection reason |
| `revision_count` (DB) | N |
| `imaginal_script_versions` rows | N rows total |

---

## 25. Database Tables & Relationships

```
patients ──────────────────────────────────────────────────┐
therapists ────────────────────────────────────────────────┤
erp_items ─────────────────────────────────────────────────┤
                                                           │
              imaginal_script_runs                         │
              ───────────────────                          │
              id (PK)                                      │
              thread_id (UNIQUE)  ← LangGraph session key  │
              patient_id ─────────────────────────────────►│ FK→patients
              therapist_id ───────────────────────────────►│ FK→therapists
              erp_item_id ────────────────────────────────►│ FK→erp_items
              obsession, compulsion (snapshot)             │
              feared_consequence, script_intensity         │
              subtype, exposure_type                       │
              status, revision_count                       │
              latest_prompt_text, latest_script_text       │
              approved_script_text                         │
              approved_audio_path, approved_audio_key      │
              approved_script_id ─────────────────────────►│ FK→approved_imaginal_scripts
              created_at, updated_at                       │
                    │                                      │
                    │ 1:N                                  │
                    ▼                                      │
              imaginal_script_versions                     │
              ────────────────────────                     │
              id (PK)                                      │
              run_id ─────────────────────────────────────►│ FK→imaginal_script_runs
              version_no                                   │
              prompt_text (what was sent to SLM)           │
              generated_script (what SLM returned)         │
              therapist_feedback (rejection reason)        │
              approved (True only for accepted version)    │
              created_at                                   │
                                                           │
              approved_imaginal_scripts                    │
              ────────────────────────                     │
              id (PK)                                      │
              patient_id ─────────────────────────────────►│ FK→patients
              therapist_id ───────────────────────────────►│ FK→therapists
              erp_item_id ────────────────────────────────►│ FK→erp_items
              run_id ─────────────────────────────────────►│ FK→imaginal_script_runs
              subtype                                      │
              approved_script (final text)                 │
              audio_path (R2 URL or local path)            │
              audio_key (R2 object key)                    │
              metadata_json (case formulation snapshot)    │
              created_at                                   │
```

---

## 26. Status State Machine

The `ImaginalScriptRun.status` field transitions:

```
"pending_review"   ← initial status when run is created (in load_case_context node)
       │
       │ (after generate_script_node saves version)
       ▼
"pending_review"   ← run awaiting therapist review (script ready)
       │
       ├── therapist approves ──────────────────────────────────────┐
       │                                                             │
       └── therapist rejects                                         │
             │                                                       │
             ▼                                                       │
          "revising"    ← prepare_revision_node sets this            │
             │                                                       │
             │ (after revised script generated)                      │
             ▼                                                       │
          "pending_review"  ← back to awaiting review                │
                                                                     │
         "approved_pending_audio"  ← Command(update=...) in         ◄┘
                   review node after approval
                          │
                          │ (after finalize_approved_node)
                          ▼
                       "approved"    ← terminal state
                       "done"        ← state field in LangGraph state
```

---

## 27. Audio Pipeline Detail

```
approved script text
        │
        ▼
prepare_text_for_audio()
  - normalize line endings (\r\n → \n)
  - double newlines (\n → \n\n) for speech pauses
        │
        ▼
piper subprocess
  stdin: prepared text (UTF-8 encoded)
  args: --model en_US-lessac-medium.onnx
        --output_file /backend/media/imaginal_audio/{uuid}.wav
        --length_scale 1.08   ← 8% slower for therapeutic pacing
        │
        ▼
  /backend/media/imaginal_audio/{uuid}.wav  (local WAV file)
        │
        │  if R2 configured
        ▼
boto3 upload_fileobj()
  Bucket: settings.R2_BUCKET_NAME
  Key:    "imaginal_audio/patient_{id}/run_{id}/{uuid}.wav"
  ContentType: "audio/wav"
        │
        ▼
  R2 public URL: "https://{endpoint}/{bucket}/imaginal_audio/..."
  → stored in approved_imaginal_scripts.audio_path
  → local file DELETED

        │  if R2 NOT configured
        ▼
  local path stored in audio_path
  served via FileResponse from /imaginal-generator/audio/{id}

        │  when patient plays audio
        ▼
GET /imaginal-generator/audio/{script_id}
  if audio_key present → generate_presigned_download_url(audio_key)
                       → RedirectResponse(url, status_code=307)
                       → browser downloads directly from R2 CDN
  else                 → FileResponse(audio_path)
                       → streamed through Python server
```

---

*Document generated: March 24, 2026*
*Covers: `backend/app/ERPScriptGenerator/` — all 14 Python files, 3 DB tables, 5 API endpoints, 4 React components, 1 JS API client*
