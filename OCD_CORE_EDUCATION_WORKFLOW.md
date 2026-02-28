# OCD Core Education — LangGraph Agent Workflow

Complete walkthrough of every file, every node, and every line involved from a patient clicking "Generate" to a completed education page appearing in their browser.

---

## Module Location

```
backend/app/education/ocd_core/
├── config.py      ← env-driven constants
├── state.py       ← TypedDict that flows through the graph
├── schemas.py     ← Pydantic output shapes (LLM + API)
├── prompts.py     ← System prompts for both LLM calls
├── kb.py          ← RAG retrieval + formatting
├── llm.py         ← ChatOpenAI factory
├── web.py         ← Tavily fallback
├── graph.py       ← LangGraph StateGraph (4 nodes)
├── models.py      ← SQLAlchemy DB table
├── tasks.py       ← Celery task (entry point)
├── service.py     ← DEFAULT_TOPIC constant
└── router.py      ← FastAPI endpoints (3 routes)
```

---

## High-Level Data Flow

```
[Patient browser]
      │
      │  POST /education/ocd-core/patient/generate
      ▼
[router.py]  ── creates DB row (status=queued) ──► [PostgreSQL: ocd_core_education_cache]
      │
      │  .delay() ──────────────────────────────► [Redis broker]
      ▼                                                  │
[tasks.py]  ◄──────────────────────────────────────────┘
      │
      │  build_graph().invoke(...)
      ▼
[graph.py: LangGraph StateGraph]
  kb_retrieve ──► kb_judge ──► (route) ──► [web?] ──► generate
      │                                                    │
      │  retrieve_kb()                           structured_output
      ▼                                                    │
  [kb.py → rag_service]                         output_json in state
                                                           │
[tasks.py]  ◄──────────────────────────────────────────────
      │
      │  writes sections_json, sources_json to DB (status=completed)
      ▼
[PostgreSQL]
      ▲
      │  GET /education/ocd-core/patient/my-education (polled every 4s)
[Patient browser]
```

---

## Step 1 — Patient Triggers Generation

**File: `router.py` — `POST /education/ocd-core/patient/generate`** (line 80–152)

```python
@router.post("/patient/generate", response_model=TriggerResponse, status_code=202)
async def trigger_ocd_education_generation(
    regenerate: bool = False,
    current_patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
):
```

The route is guarded by `get_current_patient` — only a logged-in patient can call it.

**Guard logic (lines 103–120):**

| Condition | Behaviour |
|-----------|-----------|
| `regenerate=False` + status=`completed` | Return 202 immediately, no new task |
| `regenerate=False` + status=`queued/running` | Return 202, task already in-flight |
| Any other case | Proceed to queue |

**Before queuing, therapist check (lines 122–127):**
```python
patient = db.query(Patient).filter(Patient.id == current_patient.id).first()
if not patient or not patient.therapist_id:
    raise HTTPException(status_code=400, detail="No therapist assigned ...")
```
Without a `therapist_id` the KB retrieval has no anchor — prevented here.

**Create/reset DB row (lines 130–138):**
```python
if record:
    record.status = OCDCoreEducationStatus.queued
    record.error_message = None
else:
    record = OCDCoreEducationCache(patient_id=current_patient.id, status=OCDCoreEducationStatus.queued)
    db.add(record)
db.commit()
```
The row is immediately persisted as `queued` so subsequent GET polls return a meaningful status while Celery starts up.

**Fire Celery task (lines 141–145):**
```python
generate_ocd_core_education_task.delay(
    patient_id=current_patient.id,
    therapist_id=patient.therapist_id,
    topic=DEFAULT_TOPIC,
)
```
`.delay()` serialises the three integers/strings, pushes them onto the Redis queue, and returns instantly. The HTTP response (202) is returned before the task starts.

`DEFAULT_TOPIC` (from `service.py`):
```
"Core OCD concepts: nature, obsessions, compulsions, the OCD cycle,
 ERP model, cognitive distortions, OCD subtypes"
```

---

## Step 2 — Celery Worker Picks Up the Task

**File: `tasks.py` — `generate_ocd_core_education_task`**

Registered in `celery_app.py`:
```python
include=[ ..., 'app.education.ocd_core.tasks' ]
```
and in `_register_tasks()`:
```python
import app.education.ocd_core.tasks
```

The task signature:
```python
@celery_app.task(bind=True, name="generate_ocd_core_education_task")
def generate_ocd_core_education_task(self, patient_id, therapist_id, topic):
```
`bind=True` gives the task access to `self` (Celery task instance) for retries if needed.

**Status: queued → running (lines 34–46):**
```python
record = db.query(OCDCoreEducationCache).filter(
    OCDCoreEducationCache.patient_id == patient_id
).first()

if not record:
    record = OCDCoreEducationCache(patient_id=patient_id, status=OCDCoreEducationStatus.running)
    db.add(record)
else:
    record.status = OCDCoreEducationStatus.running
    record.error_message = None
db.commit()
```
The row transitions to `running` so the frontend spinner can distinguish "waiting in queue" from "actively generating."

**Run the graph (lines 49–53):**
```python
graph = build_graph(SessionLocal)
final_state = graph.invoke({
    "therapist_id": therapist_id,
    "topic": topic,
})
```
`SessionLocal` (the SQLAlchemy factory) is passed into `build_graph` so each graph node can open its own DB connection without sharing the task's connection.

**Persist results (lines 55–66):**
```python
record.status = OCDCoreEducationStatus.completed
record.topic = output.get("topic", topic)
record.reading_level = output.get("reading_level", "simple")
record.sections_json = output.get("sections", [])
record.sources_json = output.get("sources", [])
record.disclaimer = output.get("disclaimer", "")
db.commit()
```

**Error path (lines 69–87):**
If any exception bubbles up, a *separate* DB session is opened (the original `db` might be broken) and the record is marked `failed` with `error_message = str(exc)[:1000]`. The exception is then re-raised so Celery logs it correctly.

---

## Step 3 — LangGraph Pipeline

**File: `graph.py` — `build_graph(db_factory)`**

`db_factory` is `SessionLocal` — a callable that returns a new SQLAlchemy session.

The graph is built using LangGraph's `StateGraph`:
```python
g = StateGraph(OCDEducationState)
```

### State Object

**File: `state.py`**

```python
class OCDEducationState(TypedDict, total=False):
    therapist_id: int        # passed in at invoke time
    topic: str               # the full topic string
    kb_chunks: List[KBChunk] # populated by kb_retrieve_node
    kb_sufficient: bool      # populated by kb_judge_node
    kb_reason: str           # LLM explanation of the judgment
    web_results: List[dict]  # populated by web_node (optional)
    output_json: dict        # final structured output from generate_node
```

`total=False` means all keys are optional — LangGraph merges partial dicts returned by each node into a single accumulated state.

### Node 1 — `kb_retrieve_node` (graph.py lines 22–28)

```python
def kb_retrieve_node(state: OCDEducationState) -> OCDEducationState:
    db = db_factory()
    try:
        chunks = retrieve_kb(db, state["therapist_id"], state["topic"])
        return {**state, "kb_chunks": chunks}
    finally:
        db.close()
```

Calls `retrieve_kb` from `kb.py`:
```python
def retrieve_kb(db, therapist_id, query) -> List[KBChunk]:
    return rag_service.retrieve_chunks(
        db=db, therapist_id=therapist_id,
        query=query, top_k=KB_TOP_K  # default: 8 chunks
    )
```

`rag_service.retrieve_chunks` runs a **pgvector cosine similarity search** restricted to documents uploaded by this therapist. Each returned `KBChunk` has:
- `chunk_text` — the actual KB paragraph
- `resource_title` — name of the uploaded resource
- `resource_id` — FK to the resource table
- `similarity_score` — cosine similarity (0–1)

Returns a partial state: `{ ...state, kb_chunks: [...] }`.

### Node 2 — `kb_judge_node` (graph.py lines 30–43)

```python
def kb_judge_node(state: OCDEducationState) -> OCDEducationState:
    ctx = kb_context(state.get("kb_chunks", []))
    judge_llm = llm.with_structured_output(KBJudge, method="json_schema")
    result: KBJudge = judge_llm.invoke([
        {"role": "system", "content": KB_JUDGE_SYSTEM},
        {"role": "user", "content": f"TOPIC: {state['topic']}\n\nKB EXCERPTS:\n{ctx or '(none)'}"},
    ])
    return { ...state, "kb_sufficient": bool(result.kb_sufficient), "kb_reason": result.reason }
```

**`kb_context()` in kb.py (lines 20–33):**
Formats chunks into numbered blocks capped at 7000 chars:
```
[KB 1: DSM-5 OCD Chapter | sim=0.892 | resource_id=14]
OCD is characterized by...
---
[KB 2: ERP Workbook | sim=0.874 | resource_id=7]
Exposure and Response Prevention involves...
```

**`KBJudge` schema (schemas.py):**
```python
class KBJudge(BaseModel):
    kb_sufficient: bool
    reason: str
```

**`KB_JUDGE_SYSTEM` prompt (prompts.py lines 4–12):**
Tells the LLM to check if the KB excerpts cover: what OCD is, the obsession/compulsion distinction, the OCD cycle (trigger→obsession→anxiety→compulsion→relief→loop), ERP model basics, cognitive distortions, and common subtypes.

The LLM replies with a structured JSON — `.with_structured_output(KBJudge, method="json_schema")` enforces the Pydantic schema via OpenAI's JSON schema mode, so hallucinated field names are impossible.

### Conditional Edge — `route_after_judge` (graph.py lines 45–50)

```python
def route_after_judge(state: OCDEducationState) -> str:
    if state.get("kb_sufficient", False):
        return "generate"
    if not USE_WEB_FALLBACK:
        return "generate"      # skip web even if KB is thin
    return "web"
```

Two config switches control this:
- `kb_sufficient` — LLM decision from previous node
- `USE_WEB_FALLBACK` — env var `OCD_EDU_USE_WEB_FALLBACK` (default `true`)

If KB is sufficient **or** web fallback is disabled → go straight to `generate`.  
If KB is insufficient **and** web fallback is enabled → go to `web`.

### Node 3 — `web_node` (graph.py lines 52–55) — optional

```python
def web_node(state: OCDEducationState) -> OCDEducationState:
    q = "OCD obsessions compulsions ERP exposure response prevention core concepts patient education"
    results = tavily_search(q, k=5)
    return {**state, "web_results": results}
```

**`tavily_search()` in web.py:**
- Returns `[]` immediately if `TAVILY_API_KEY` is not set (safe default)
- Uses `TavilySearchResults` from `langchain_community` with `include_raw_content=True`
- Restricted to trusted domains via `ALLOWED_DOMAINS` in `config.py`:
  `iocdf.org, nimh.nih.gov, nhs.uk, mayoclinic.org, clevelandclinic.org, apa.org`

### Node 4 — `generate_node` (graph.py lines 57–88)

This is the main generation call. It assembles the full prompt context and calls the LLM with the final output schema.

**Context assembly:**

1. **KB context** (always): `kb_context(state["kb_chunks"])` → formatted numbered blocks
2. **Web context** (only if web_results populated):
   ```python
   for i, r in enumerate(web_results, 1):
       "[WEB 1: Title | url]\n content[:2000]\n"
   ```
   Each web result is capped at 2000 chars.

**LLM call:**
```python
edu_llm = llm.with_structured_output(OCDCoreEducation, method="json_schema")
payload: OCDCoreEducation = edu_llm.invoke([
    {"role": "system", "content": EDU_SYSTEM},
    {"role": "user", "content": (
        f"TOPIC: {state['topic']}\n\n"
        f"KB EXCERPTS (primary):\n{kb_ctx}\n\n"
        f"WEB EXCERPTS (only if KB insufficient):\n{web_ctx}\n\n"
        "Return JSON now."
    )},
])
return {**state, "output_json": payload.model_dump()}
```

**`EDU_SYSTEM` prompt (prompts.py lines 15–28):**
Instructions include:
- Use KB as primary, web only as fallback
- Simple, compassionate language
- Required sections: what OCD is, the OCD cycle, obsessions, compulsions, why compulsions worsen OCD, ERP overview, common subtypes, coping note
- 3–5 key_points per section

**`OCDCoreEducation` schema (schemas.py):**
```python
class OCDCoreEducation(BaseModel):
    module: Literal["ocd_core_education"]
    topic: str
    reading_level: Literal["simple", "standard"]
    sections: List[Section]          # ordered list of content sections
    sources: List[Source]            # KB or web citations
    disclaimer: str
```

```python
class Section(BaseModel):
    id: str                          # e.g. "what_is_ocd"
    title: str                       # display name
    content_markdown: str            # full paragraph(s) in Markdown
    key_points: List[str]            # 3-5 bullet takeaways
```

```python
class Source(BaseModel):
    type: Literal["kb", "web"]
    title: str
    resource_id: Optional[int]       # set for kb sources
    url: Optional[str]               # set for web sources
```

`payload.model_dump()` converts the validated Pydantic object to a plain dict stored as `output_json` in the state.

### Graph Wiring (graph.py lines 90–102)

```python
g.set_entry_point("kb_retrieve")
g.add_edge("kb_retrieve", "kb_judge")
g.add_conditional_edges("kb_judge", route_after_judge, {
    "web": "web",
    "generate": "generate",
})
g.add_edge("web", "generate")
g.add_edge("generate", END)
return g.compile()
```

Compiled execution path:

```
kb_retrieve → kb_judge → (if sufficient)  → generate → END
                        → (if insufficient & web on) → web → generate → END
```

---

## Step 4 — Frontend Polling

**File: `frontend/src/pages/PatientOCDEducation.jsx`**

On mount and after triggering generation, the component polls every 4 seconds:

```js
intervalRef.current = setInterval(() => {
  fetchStatus();
}, 4000);
```

`fetchStatus()` calls `GET /education/ocd-core/patient/my-education`:

```python
@router.get("/patient/my-education", response_model=OCDEducationStatusResponse)
async def get_patient_ocd_education(current_patient, db):
    record = db.query(OCDCoreEducationCache).filter(
        OCDCoreEducationCache.patient_id == current_patient.id
    ).first()
    if not record:
        raise HTTPException(404, ...)
    return _cache_to_response(record)
```

`_cache_to_response` returns:
```json
{
  "status": "queued|running|completed|failed",
  "error_message": null,
  "education": { ... }   // only present when status=completed
}
```

The frontend clears the polling interval the moment `status` transitions to `completed` or `failed`.

Render states the component handles:
| `status` | What player sees |
|----------|-----------------|
| `null` (404) | Empty state + "Generate" button |
| `queued` | Spinner + "Queued…" |
| `running` | Spinner + "Generating…" |
| `completed` | Expandable section cards + sources + disclaimer |
| `failed` | Error banner + `error_message` + "Try Again" button |

---

## Step 5 — DB Model

**File: `models.py` — `OCDCoreEducationCache`**

```
Table: ocd_core_education_cache
┌──────────────┬──────────────┬──────────────────────────────────────┐
│ Column       │ Type         │ Notes                                │
├──────────────┼──────────────┼──────────────────────────────────────┤
│ id           │ Integer PK   │ auto-increment                       │
│ patient_id   │ Integer FK   │ UNIQUE — one row per patient         │
│ status       │ String(20)   │ queued/running/completed/failed      │
│ error_message│ Text         │ null unless failed                   │
│ topic        │ String       │ written after completion             │
│ reading_level│ String       │ "simple" or "standard"               │
│ sections_json│ JSON         │ List[Section] as plain dicts         │
│ sources_json │ JSON         │ List[Source] as plain dicts          │
│ disclaimer   │ Text         │ written after completion             │
│ created_at   │ DateTime     │ server_default=now()                 │
│ updated_at   │ DateTime     │ onupdate=now()                       │
└──────────────┴──────────────┴──────────────────────────────────────┘
```

`UNIQUE` on `patient_id` ensures there is always exactly one cache row per patient — generation overwrites without creating duplicates.

---

## Config Reference

**File: `config.py`**

| Variable | Env Key | Default |
|----------|---------|---------|
| `LLM_MODEL` | `LLM_MODEL` | `gpt-5.2` |
| `KB_TOP_K` | `OCD_EDU_KB_TOP_K` | `8` |
| `USE_WEB_FALLBACK` | `OCD_EDU_USE_WEB_FALLBACK` | `true` |
| `TAVILY_API_KEY` | `TAVILY_API_KEY` | `""` (web disabled) |

---

## Sequence Summary

```
[Patient]  POST /generate
               │
[Router]   creates DB row (queued) → returns 202
               │
[Redis]    task pushed to queue
               │
[Celery]   picks task up → DB row (running)
               │
[graph.invoke]
  1. kb_retrieve  → pgvector similarity search (top 8 chunks, therapist-scoped)
  2. kb_judge     → LLM decides: is KB sufficient? (KBJudge schema)
  3. web (maybe)  → Tavily search on trusted OCD domains
  4. generate     → LLM writes full education (OCDCoreEducation schema)
               │
[Celery]   writes sections_json, sources_json → DB row (completed)
               │
[Patient]  GET /my-education (polled every 4s) → receives completed education
               │
[Browser]  renders expandable section cards
```

---

## Key Difference from Fear Ladder Education

| Aspect | Fear Ladder Education | OCD Core Education |
|--------|----------------------|--------------------|
| Execution | Synchronous — blocks HTTP request | Async — Celery task |
| HTTP response | 200 + content | 202 Accepted immediately |
| DB status field | None | `queued/running/completed/failed` |
| Frontend strategy | Single fetch | Polling every 4 s |
| Error recovery | Exception propagates to user | Stored in `error_message`, surfaced in UI |
