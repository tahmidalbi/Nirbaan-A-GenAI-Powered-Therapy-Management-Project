# ERP LangGraph Agent — Complete Workflow Deep Dive

## Table of Contents
1. [Overview](#overview)
2. [File Map](#file-map)
3. [The Four Event Types](#the-four-event-types)
4. [Entry Point: `invoke_erp_coach()`](#entry-point-invoke_erp_coach)
5. [The Graph Structure](#the-graph-structure)
6. [Node-by-Node Walkthrough](#node-by-node-walkthrough)
   - [load_context](#1-load_context)
   - [compute_metrics](#2-compute_metrics)
   - [mode_router](#3-mode_router-conditional-edge)
   - [LIVE path: log_user → live_intent_router](#4-live-path-log_user--live_intent_router)
   - [LIVE handlers](#5-live-handlers)
   - [finalize_coach_live → log_coach → END](#6-finalize_coach_live--log_coach--end)
   - [DEBRIEF path](#7-debrief-path)
   - [REPORT path](#8-report-path)
7. [LLM Layer](#llm-layer)
8. [Celery: Scheduled Check-ins](#celery-scheduled-check-ins)
9. [Frontend ↔ Backend Flow](#frontend--backend-flow)
10. [State Object Reference](#state-object-reference)
11. [Complete Call Sequence Diagrams](#complete-call-sequence-diagrams)

---

## Overview

The ERP Coach is a **LangGraph StateGraph** agent that handles all AI-driven interactions in a live Exposure & Response Prevention session. It is invoked in four different scenarios (events), runs a chain of deterministic and LLM nodes, and always writes its results back to PostgreSQL.

The entire agent lives in:
```
backend/app/erp/ERPCoach/
```

---

## File Map

```
backend/app/erp/ERPCoach/
│
├── events.py                  # EventType literals + normalize_event_type()
├── state.py                   # CoachState TypedDict (shared dict flowing through all nodes)
├── graph.py                   # Graph builder + invoke_erp_coach() entry point
│
├── nodes/
│   ├── load_context.py        # Node 1: DB query → populate state
│   ├── compute_metrics.py     # Node 2: compute flags (rate_reminder, spike, cooldown)
│   ├── mode_router.py         # Conditional router: LIVE / DEBRIEF_PROMPT / REPORT
│   ├── live_intent_router.py  # Conditional router: which LIVE handler to call
│   ├── live_handlers.py       # 7 LIVE handler nodes (general, reassurance, etc.)
│   ├── debrief_prompt.py      # DEBRIEF_PROMPT handler
│   ├── report_bundle.py       # REPORT: assemble inputs
│   ├── report_generate.py     # REPORT: 3 LLM nodes (facts, therapist, patient)
│   ├── finalize_json.py       # Validate / normalize coach_response_json
│   └── persist.py             # Write results to DB (chat messages, reports)
│
├── prompts/
│   ├── live_handlers.py       # Prompt builders for all 7 live handlers
│   ├── router_prompt.py       # Prompt builder for intent router LLM call
│   ├── debrief_prompt.py      # Prompt builder for debrief coach message
│   └── report_prompts.py      # Prompt builders for 3-step report generation
│
├── llm/
│   ├── client.py              # LLMClient: structured_call() + text_call()
│   ├── structured.py          # build_structured_runnable() wraps ChatOpenAI
│   └── retry.py               # invoke_with_retries() + repair_to_schema()
│
├── utils/
│   ├── transcript.py          # format_transcript_block() → "PATIENT: ...\nCOACH: ..."
│   ├── summarization.py       # compute_suds_stats(), compact_prior_session_summaries()
│   └── time.py                # compute_elapsed_seconds(), seconds_since(), now_utc()
│
├── tasks/
│   ├── erp_checkins.py        # Celery tasks: dispatch_due_checkins + run_checkin
│   └── erp_reports.py         # Celery task: run_end_session_report
│
└── services/
    └── coach_storage.py       # All DB read/write helpers (CoachStorage class)
```

---

## The Four Event Types

Every graph invocation carries exactly one `event_type`. Defined in `events.py`:

```python
EventType = Literal[
    "USER_MESSAGE",              # patient sent a chat message
    "CHECK_IN",                  # Celery timed check-in (every 5 min)
    "END_SESSION_DEBRIEF_PROMPT",# patient clicked "End Session"
    "END_SESSION_REPORT",        # patient submitted debrief text
]
```

`normalize_event_type()` in `events.py` maps any casing/variant to the canonical form. Unknown values default to `"USER_MESSAGE"`.

---

## Entry Point: `invoke_erp_coach()`

**File:** `graph.py` lines 230–255

```python
def invoke_erp_coach(payload: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(payload)
    payload["event_type"] = normalize_event_type(payload.get("event_type"))

    db = SessionLocal()          # 1. Open ONE DB connection for this entire run
    try:
        payload["db"] = db
        payload["storage"] = CoachStorage(db)   # 2. Inject storage helper
        payload["llm_client"] = LLMClient()     # 3. Inject LLM client

        graph = get_erp_coach_graph()           # 4. Get compiled graph (cached via lru_cache)
        return graph.invoke(payload)            # 5. Run the graph

    except Exception:
        try: db.rollback()
        except: pass
        raise
    finally:
        db.close()               # 6. Always close DB
```

Key design decisions:
- **One DB connection per invocation** — opened before the graph starts, closed in `finally`. No node opens its own connection.
- **`@lru_cache(maxsize=1)` on `get_erp_coach_graph()`** — the graph is compiled once and reused forever. LangGraph compilation is expensive; this avoids repeating it per request.
- **Dependency injection via state** — `db`, `storage`, and `llm_client` are put directly into the state dict so every node can access them without global singletons.

---

## The Graph Structure

**File:** `graph.py`, lines 130–220

The graph is built with `StateGraph(CoachState)`. Here is the complete wiring:

```
START
  │
  ▼
load_context          (always runs — DB query)
  │
  ▼
compute_metrics       (always runs — deterministic flag computation)
  │
  ▼ [mode_router conditional edge]
  ├──► LIVE ──────────► log_user
  │                        │
  │                        ▼ [live_intent_router conditional edge]
  │                        ├──► live_general
  │                        ├──► live_reassurance
  │                        ├──► live_urge
  │                        ├──► live_quit
  │                        ├──► live_rate_reminder
  │                        ├──► live_spike
  │                        └──► live_no_message
  │                        │    (all 7 converge here)
  │                        ▼
  │                     finalize_coach_live
  │                        │
  │                        ▼
  │                     log_coach
  │                        │
  │                        ▼
  │                       END
  │
  ├──► DEBRIEF_PROMPT ─► debrief_prompt
  │                        │
  │                        ▼
  │                     finalize_coach_debrief
  │                        │
  │                        ▼
  │                     log_debrief_prompt
  │                        │
  │                        ▼
  │                       END
  │
  └──► REPORT ──────────► report_bundle
                             │
                             ▼
                          report_facts        (LLM: plain text compression)
                             │
                             ▼
                          report_therapist    (LLM: TherapistReportJSON)
                             │
                             ▼
                          report_patient      (LLM: PatientFeedbackJSON)
                             │
                             ▼
                          finalize_reports    (Pydantic validation)
                             │
                             ▼
                          save_reports        (DB write)
                             │
                             ▼
                            END
```

---

## Node-by-Node Walkthrough

### 1. `load_context`

**File:** `nodes/load_context.py`

Called on every single graph run regardless of event type.

```python
bundle = storage.get_session_bundle(
    session_id,
    message_limit=20,    # last 20 chat messages
    suds_limit=12,       # last 12 SUDS readings
    prior_sessions_limit=3,
    include_transcript=True,
)
```

`CoachStorage.get_session_bundle()` runs multiple DB queries in one call:
- Fetches `ERPLiveSession` by `session_id`
- Fetches `ERPItem` (obsession + compulsions)
- Fetches last exercise note for this item
- Fetches last 20 `ERPChatMessage` rows (ordered by `created_at`)
- Fetches last 12 `ERPSUDSReading` rows
- Fetches peak SUDS for the session
- Fetches last 3 ended sessions for continuity summaries

Then it:
```python
transcript_block = format_transcript_block(bundle.messages, max_messages=20)
# → "PATIENT: i feel anxious\nCOACH: That's the exposure working..."
```

`format_transcript_block()` in `utils/transcript.py` takes ORM objects, normalizes roles (`"user"` → `"PATIENT"`, `"assistant"` → `"COACH"`), truncates messages >1200 chars, and joins with newlines.

Everything is written into `state`:
```python
state.update({
    "session": bundle.session,          # ORM object
    "obsession": bundle.obsession,      # str
    "compulsions": bundle.compulsions,  # List[str]
    "transcript_block": transcript_block,
    "suds_recent": bundle.suds_recent,
    "suds_peak": bundle.suds_peak,
    "prior_summaries": prior_summaries,
    "elapsed_seconds": compute_elapsed_seconds(...),
    ...
})
```

`elapsed_seconds` is computed via `utils/time.py`:
- If session is `running`: `accumulated_seconds + (now - resumed_at)`
- Otherwise: just `accumulated_seconds`

---

### 2. `compute_metrics`

**File:** `nodes/compute_metrics.py`

Runs deterministic math on the loaded context to produce routing flags for the `live_intent_router`.

```python
reminder_seconds = 300   # 5 minutes
cooldown_seconds = 120   # 2 minutes
spike_delta_threshold = 15   # SUDS jump ≥ 15
spike_slope_threshold = 8.0  # SUDS rising ≥ 8 points/min
```

**`rate_reminder_flag`:**
```python
if since_last_suds is None:
    # Never rated — remind after elapsed >= reminder_seconds
    rate_reminder_flag = elapsed_seconds >= reminder_seconds
else:
    rate_reminder_flag = since_last_suds >= reminder_seconds
```
→ `True` if the patient has not submitted a SUDS rating in the last 5 minutes.

**`spike_flag`:**
```python
if suds_delta >= 15:      spike_flag = True
if slope_per_min >= 8.0:  spike_flag = True
```
→ `True` if SUDS jumped by 15+ points, or is rising at 8+ points per minute.

**`cooldown_ok`:**
```python
if since_last_agent < 120:
    cooldown_ok = False
```
→ `False` if the agent spoke less than 2 minutes ago (prevents spam).

**`suds_trend_hint`:**
Produces a string like `"rising (delta=20)"` or `"stable (delta=3)"` for the LLM prompts.

All flags written into state: `rate_reminder_flag`, `spike_flag`, `cooldown_ok`, `since_last_suds_seconds`, `suds_trend_hint`, etc.

---

### 3. `mode_router` (conditional edge)

**File:** `nodes/mode_router.py`

Pure Python function, no LLM call:

```python
def mode_router(state) -> Literal["LIVE", "DEBRIEF_PROMPT", "REPORT"]:
    event_type = state.get("event_type").upper()

    if event_type == "END_SESSION_DEBRIEF_PROMPT":
        return "DEBRIEF_PROMPT"
    if event_type == "END_SESSION_REPORT":
        return "REPORT"
    return "LIVE"   # USER_MESSAGE and CHECK_IN both go LIVE
```

LangGraph uses this return value to decide which node to call next.

---

### 4. LIVE Path: `log_user` → `live_intent_router`

**`log_user` — File:** `nodes/persist.py`

First thing in the LIVE path: save the patient's message to DB.

```python
storage.save_chat_message(
    session_id=session.id,
    erp_item_id=session.erp_item_id,
    patient_id=session.patient_id,
    role="patient",
    content=msg,
    intent="USER_MESSAGE",
    tags=[],
    commit=True,     # ← commits immediately
)
```

For `CHECK_IN` events, `user_message` is `""` so nothing is written.

**`live_intent_router` — File:** `nodes/live_intent_router.py`

This is another conditional edge function. It runs **after** `log_user`.

**For CHECK_IN events — purely deterministic, no LLM:**
```python
if event_type == "CHECK_IN":
    if not cooldown_ok:    return "NO_MESSAGE"
    if spike_flag:         return "SUDS_SPIKE"
    if rate_reminder_flag: return "RATE_REMINDER"
    return "GENERAL"
```
Priority: cooldown → spike → rate reminder → general check-in.

**For USER_MESSAGE events — one cheap LLM call:**
```python
prompt = build_live_intent_router_prompt(
    obsession=obsession,
    compulsions=compulsions,
    user_message=user_message,
    transcript_tail=transcript_block[-1500:],
)
out = llm.structured_call(
    schema=LiveIntentOut,   # Pydantic: intent: Literal["REASSURANCE","COMPULSION_URGE","AVOIDANCE_QUIT","GENERAL"]
    prompt=prompt,
    attempts=2,
    repair_attempts=0,      # cheap fast call, no repair
)
```

The router prompt (`prompts/router_prompt.py`) tells the LLM to classify the patient's message into one of 4 intents. The LLM returns a single-field JSON like `{"intent": "REASSURANCE"}`.

Mapping to graph routes:
```python
"REASSURANCE"    → "REASSURANCE_BLOCK"
"COMPULSION_URGE"→ "COMPULSION_URGE"
"AVOIDANCE_QUIT" → "AVOIDANCE_QUIT"
"GENERAL"        → "GENERAL"
# Any exception  → "GENERAL" (safe fallback)
```

---

### 5. LIVE Handlers

**File:** `nodes/live_handlers.py` (nodes) + `prompts/live_handlers.py` (prompt text)

All 7 handlers follow the same pattern. Example — `handle_general`:

```python
def handle_general(state, *, llm: LLMClient):
    ctx = _ctx(state)   # extracts the 10 common context fields
    event_type = state.get("event_type", "").upper()

    if event_type == "CHECK_IN":
        prompt = prompt_checkin_general(**ctx)
    else:
        prompt = prompt_general_coaching(**ctx, user_message=user_message)

    resp = llm.structured_call(schema=CoachResponse, prompt=prompt)
    state["coach_response"] = resp
    state["coach_response_json"] = resp.model_dump()
    return state
```

The 10 context fields passed to every prompt:
```python
{
    "obsession": ...,
    "compulsions": [...],
    "exercise_text": ...,
    "elapsed_seconds": ...,
    "suds_latest": ...,
    "suds_peak": ...,
    "suds_trend_hint": ...,
    "prior_summaries": [...],
    "transcript_block": "PATIENT: ...\nCOACH: ...",
}
```

**Every prompt ends with** the full conversation transcript in this format:
```
Recent chat transcript (most recent at bottom):
PATIENT: i feel so anxious
COACH: That's exactly what exposure looks like. Stay with it.
PATIENT: should I stop?
```
This gives the model full conversation memory for up to 20 turns.

**The 7 handler routes and what triggers them:**

| Route | Trigger | Prompt focus |
|---|---|---|
| `live_general` | Default USER_MESSAGE or general CHECK_IN | General ERP coaching |
| `live_reassurance` | Patient seeking certainty ("will I be ok?") | Block reassurance, redirect to exposure |
| `live_urge` | Patient reporting compulsion urge | Delay compulsion, stay in exposure |
| `live_quit` | Patient wanting to stop/avoid | Encourage staying in exposure |
| `live_rate_reminder` | No SUDS rating for 5 min | Direct ask: "rate 0–100 right now" |
| `live_spike` | SUDS jumped ≥15 or rising fast | Stabilize + normalize high anxiety |
| `live_no_message` | Cooldown active | Static `NO_MESSAGE` — no LLM call |

**`handle_no_message`** is the only handler with no LLM call — it returns a hard-coded static response:
```python
static_json = {
    "type": "NO_MESSAGE",
    "source": "CHECK_IN",
    "coach_message": None,
    "next_action": {"type": "NONE", "payload": {}},
    "tags": ["cooldown_no_message"],
}
```

**The `CoachResponse` Pydantic schema** (what every handler produces):
```python
class CoachResponse(BaseModel):
    type: Literal["COACH_MESSAGE", "NO_MESSAGE"]
    source: Literal["USER_MESSAGE", "CHECK_IN", "SYSTEM"]
    coach_message: Optional[str]
    next_action: NextAction   # type + payload dict
    tags: List[str]

class NextAction(BaseModel):
    type: Literal["NONE","RATE_SUDS_NOW","CONTINUE","DELAY_COMPULSION","END_SESSION_CONFIRM"]
    payload: Dict[str, Any]
```

---

### 6. `finalize_coach_live` → `log_coach` → END

**`finalize_coach_live` — File:** `nodes/finalize_json.py`

Validates that `coach_response_json` is a valid `CoachResponse`. If something went wrong upstream, falls back to a safe `NO_MESSAGE`:
```python
try:
    CoachResponse.model_validate(state["coach_response_json"])
    return state  # valid, pass through
except ValidationError:
    pass
# fallback
state["coach_response_json"] = {
    "type": "NO_MESSAGE", "source": "SYSTEM",
    "coach_message": None, ...
}
```

**`log_coach` — File:** `nodes/persist.py`

Writes the coach message to `erp_chat_messages`:
```python
if resp.get("type") == "NO_MESSAGE":
    return state   # nothing to write
storage.save_chat_message(
    role="coach",
    content=resp["coach_message"],
    intent=resp.get("source"),    # "USER_MESSAGE" or "CHECK_IN"
    tags=resp.get("tags") or [],
    commit=True,
)
```

Also calls `storage.update_last_agent_run_at()` to track cooldown timing.

After `log_coach`, the graph hits `END`. LangGraph returns the final state dict to `invoke_erp_coach()`, which returns it to the caller (API router or Celery task).

---

### 7. DEBRIEF Path

Triggered by `event_type = "END_SESSION_DEBRIEF_PROMPT"` (patient clicks "End Session").

**`debrief_prompt` — File:** `nodes/debrief_prompt.py`

```python
prompt = build_debrief_prompt(
    obsession=state.get("obsession"),
    compulsions=state.get("compulsions"),
    elapsed_seconds=float(state.get("elapsed_seconds", 0.0)),
    suds_peak=state.get("suds_peak"),
    suds_latest=state.get("suds_latest"),
)
resp = llm.structured_call(schema=CoachResponse, prompt=prompt)
```

The debrief prompt (`prompts/debrief_prompt.py`) asks the LLM to generate a warm, structured prompt asking the patient to reflect on their session: what they did, what urges showed up, what they resisted, what they learned.

The response has `next_action.type = "SHOW_DEBRIEF_FORM"` — the frontend sees this and displays the reflection text box.

After: `finalize_coach_debrief` → `log_debrief_prompt` → `END`. Same validation/persist pattern as LIVE.

---

### 8. REPORT Path

Triggered by `event_type = "END_SESSION_REPORT"` (patient submits debrief text). This runs via **Celery** (background task), not inline with the API response.

**Step A — `report_bundle` — File:** `nodes/report_bundle.py`

Prepares a compact `report_inputs` dict from everything in state:
```python
# Converts SUDS readings to timestamped text lines:
suds_points_block = "0s -> 65\n180s -> 72\n360s -> 58\n..."

report_inputs = {
    "obsession": ...,
    "compulsions": [...],
    "transcript_block": "PATIENT: ...\nCOACH: ...",
    "suds_points_block": suds_points_block,
    "patient_debrief_text": "I did the exposure for 10 mins...",
    "prior_summaries": [...],
    "elapsed_seconds": 720.0,
    "suds_peak": 85,
    "suds_latest": 45,
}
```

**Step B — `report_facts` — File:** `nodes/report_generate.py`

First LLM call: plain text compression.

```python
session_facts_text = llm.text_call(prompt=build_session_facts_prompt(...))
```

The facts prompt asks the LLM to extract objective bullets from the transcript + debrief + SUDS data: what happened, what compulsions occurred, what was resisted. This intermediate text is **not JSON** — it's cheaper and cleaner to compress first, then generate structured JSON from clean bullets rather than directly from noisy raw transcript.

**Step C — `report_therapist` — File:** `nodes/report_generate.py`

Second LLM call: structured `TherapistReportJSON`.

```python
report = llm.structured_call(
    schema=TherapistReportJSON,
    prompt=build_therapist_report_prompt(session_facts=facts, ...),
    attempts=3,
    repair_attempts=1,
    repair_context=facts,    # passed to repair_to_schema if needed
)
```

`TherapistReportJSON` fields: `session_overview`, `suds_curve_summary`, `what_happened`, `compulsions_urges`, `response_prevention_successes`, `avoidance_or_safety_behaviors`, `key_learning`, `recommend_next_step`, `risk_flags`.

**Step D — `report_patient` — File:** `nodes/report_generate.py`

Third LLM call: structured `PatientFeedbackJSON`.

```python
feedback = llm.structured_call(schema=PatientFeedbackJSON, prompt=...)
```

`PatientFeedbackJSON` fields: `reflection`, `wins`, `skill_to_practice`, `one_micro_goal_next_time`, `reminder`.

**Step E — `finalize_reports` — File:** `nodes/finalize_json.py`

Validates both Pydantic models:
```python
TherapistReportJSON.model_validate(state["therapist_report_json"])
PatientFeedbackJSON.model_validate(state["patient_feedback_json"])
```
Raises `ValidationError` immediately if invalid — catches LLM hallucinations early.

**Step F — `save_reports` — File:** `nodes/persist.py`

```python
storage.save_end_session_reports(
    session_id=session_id,
    patient_debrief_text=patient_debrief_text,
    therapist_report_json=therapist_report_json,
    patient_feedback_json=patient_feedback_json,
    commit=True,
)
storage.set_item_latest_session(erp_item_id, session_id, commit=True)
```

Writes both JSON blobs to `erp_live_sessions.therapist_report_json` and `erp_live_sessions.patient_feedback_json`.

---

## LLM Layer

### `LLMClient` — `llm/client.py`

```python
class LLMClient:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-5.2", temperature=0.4, ...)

    def structured_call(self, *, schema, prompt, method="function_calling", ...):
        runnable = build_structured_runnable(self.llm, schema, ...)
        result = invoke_with_retries(runnable, prompt, attempts=3, ...)
        return result   # instance of schema (Pydantic model)

    def text_call(self, *, prompt, attempts=3):
        result = invoke_with_retries(self.llm, prompt, ...)
        return result.content   # str
```

### `build_structured_runnable()` — `llm/structured.py`

```python
return llm.with_structured_output(schema, method="function_calling")
```

Uses LangChain's `.with_structured_output()` with `method="function_calling"`. This is used instead of `json_schema` because some schemas (`CoachResponse`, `TherapistReportJSON`) contain `Dict[str, Any]` fields which OpenAI's strict `json_schema` mode cannot handle (requires `additionalProperties: false` on every object).

### `invoke_with_retries()` — `llm/retry.py`

```python
for i in range(attempts):
    try:
        return runnable.invoke(payload)    # payload is a plain string
    except Exception as e:
        last_exc = e
        if i < attempts - 1:
            time.sleep(backoff * 2**i + jitter)
raise LLMRetryError(...)
```

Passes the prompt string directly to `runnable.invoke()`. LangChain auto-converts a bare string to a `HumanMessage`.

### `repair_to_schema()` — `llm/retry.py`

If `structured_call` fails all retries, it calls `repair_to_schema()` as a last chance:
```python
prompt = "You are a strict JSON formatter. Return ONLY a valid JSON...\nBad output:\n{bad_text}"
result = invoke_with_retries(runnable, prompt, attempts=2)
```
This sends the failed output back to the model and asks it to fix the JSON.

---

## Celery: Scheduled Check-ins

### Beat schedule — `app/core/celery_app.py`

```python
celery_app.conf.beat_schedule = {
    "erp-checkin-dispatch-every-minute": {
        "task": "app.erp.ERPCoach.tasks.erp_checkins.dispatch_due_checkins",
        "schedule": crontab(minute="*"),   # every minute
    },
}
```

### `dispatch_due_checkins` — `tasks/erp_checkins.py`

Runs every minute. Queries for sessions that are due:
```python
cutoff = datetime.utcnow() - timedelta(seconds=CHECKIN_SECONDS)  # 300s = 5 min
sessions = db.query(ERPLiveSession.id).filter(
    ERPLiveSession.status == "running",
    (ERPLiveSession.last_checkin_at.is_(None)) |
    (ERPLiveSession.last_checkin_at <= cutoff),
).all()

for session_id in session_ids:
    run_checkin.delay(session_id)   # enqueue per session
```

### `run_checkin` — `tasks/erp_checkins.py`

For each session:
1. Verify it's still `running`
2. Mark `last_checkin_at = now()` immediately (prevents duplicate concurrent tasks)
3. Call `invoke_erp_coach({"session_id": ..., "event_type": "CHECK_IN", "user_message": ""})`
4. If response is `NO_MESSAGE` → skip writing to DB
5. If response has `coach_message` → `storage.save_chat_message(role="coach", ...)`

The `invoke_erp_coach` call goes through the full graph: load_context → compute_metrics → mode_router (→ LIVE) → log_user (writes nothing, message is "") → live_intent_router (deterministic for CHECK_IN) → one of the LIVE handlers → finalize → log_coach → END.

### `run_end_session_report` — `tasks/erp_reports.py`

Triggered asynchronously when the patient submits their debrief text. Called from the API router as `.delay(session_id, debrief_text)`:
```python
result = invoke_erp_coach({
    "session_id": session_id,
    "event_type": "END_SESSION_REPORT",
    "patient_debrief_text": patient_debrief_text,
})
```
The graph runs the full REPORT path (bundle → facts → therapist → patient → finalize → save).

---

## Frontend ↔ Backend Flow

### Patient sends a message

```
[ERPSessionPage.jsx]
  coachSendMessage(sessionId, text)
  → POST /erp/sessions/{id}/coach/message  { message: "i feel anxious" }

[router.py]
  → invoke_erp_coach({ session_id, event_type: "USER_MESSAGE", user_message: text })
  → graph runs → coach_response_json returned
  → returns { coach_message: "...", next_action: {...}, ... }

[frontend]
  → appends coach message to chatMessages state
```

### 15-second polling for Celery messages

```
[ERPSessionPage.jsx — useEffect poll]
  every 15s while session.status === "running":
    getSessionTranscript(sessionId)
    → GET /erp/sessions/{id}/transcript
    → setChatMessages(data.messages)   ← picks up Celery check-in messages
```

### Patient clicks "End Session"

```
[ERPSessionPage.jsx]
  coachEndClick(sessionId)
  → POST /erp/sessions/{id}/end-clicked

[router.py]
  1. session.status = "ending", session.ended_at = now()
  2. invoke_erp_coach({ event_type: "END_SESSION_DEBRIEF_PROMPT" })
  3. returns coach_message + next_action: SHOW_DEBRIEF_FORM

[frontend]
  → shows debrief textarea
```

### Patient submits debrief

```
[ERPSessionPage.jsx]
  coachDebriefSubmit(sessionId, debriefText)
  → POST /erp/sessions/{id}/debrief

[router.py]
  1. Saves patient_debrief_text to session
  2. run_end_session_report.delay(session_id, debrief_text)   ← Celery async
  3. Returns immediately (patient sees "generating..." state)

[Celery worker]
  → invoke_erp_coach({ event_type: "END_SESSION_REPORT", ... })
  → REPORT path → saves therapist_report_json + patient_feedback_json

[frontend polls]
  → eventually GET /erp/sessions/{id}/detail
  → sees patient_feedback_json populated → shows session summary card
```

---

## State Object Reference

The `CoachState` TypedDict (`state.py`) is the single dict that flows through every node. Key fields:

| Field | Set by | Used by |
|---|---|---|
| `session_id` | Caller | load_context |
| `event_type` | Caller (normalized) | mode_router, live_intent_router |
| `user_message` | Caller | log_user, live_intent_router, handlers |
| `patient_debrief_text` | Caller | report_bundle |
| `session` | load_context | all nodes (ORM object) |
| `obsession` | load_context | all prompts |
| `compulsions` | load_context | all prompts |
| `transcript_block` | load_context | all prompts |
| `suds_recent` | load_context | report_bundle |
| `elapsed_seconds` | load_context | all prompts |
| `rate_reminder_flag` | compute_metrics | live_intent_router |
| `spike_flag` | compute_metrics | live_intent_router |
| `cooldown_ok` | compute_metrics | live_intent_router |
| `suds_trend_hint` | compute_metrics | all LIVE prompts |
| `coach_response` | LIVE/DEBRIEF handlers | finalize_json |
| `coach_response_json` | handlers + finalize | log_coach, API return |
| `report_inputs` | report_bundle | report_generate nodes |
| `session_facts_text` | report_facts | report_therapist, report_patient |
| `therapist_report_json` | report_therapist | finalize_reports, save_reports |
| `patient_feedback_json` | report_patient | finalize_reports, save_reports |
| `db` | invoke_erp_coach | CoachStorage |
| `storage` | invoke_erp_coach | all persist nodes |
| `llm_client` | invoke_erp_coach | handlers, router, report nodes |

---

## Complete Call Sequence Diagrams

### USER_MESSAGE

```
Patient types "i feel so anxious"
  │
  ▼
POST /erp/sessions/6/coach/message
  │
  ▼
router.py: invoke_erp_coach({session_id:6, event_type:"USER_MESSAGE", user_message:"i feel..."})
  │
  ├─ db = SessionLocal()
  ├─ storage = CoachStorage(db)
  └─ llm_client = LLMClient()
  │
  ▼ graph.invoke(payload)
  │
  ├─ [load_context]          ← 7 DB queries, builds transcript_block
  ├─ [compute_metrics]       ← rate_reminder_flag=False, cooldown_ok=True, etc.
  ├─ [mode_router]           → "LIVE"
  ├─ [log_user]              ← INSERT erp_chat_messages (role=patient)
  ├─ [live_intent_router]    ← LLM call → {"intent":"GENERAL"} → "GENERAL"
  ├─ [live_general]          ← LLM call → CoachResponse(coach_message="...", next_action=CONTINUE)
  ├─ [finalize_coach_live]   ← validate CoachResponse
  ├─ [log_coach]             ← INSERT erp_chat_messages (role=coach)
  └─ END
  │
  ▼
returns { coach_response_json: { coach_message: "Stay with it...", ... } }
  │
  ▼
API returns { coach_message: "Stay with it...", ... }
  │
  ▼
Frontend appends bubble to chat
```

### CHECK_IN (Celery)

```
celery beat: every 1 min fires dispatch_due_checkins
  │
  ▼
dispatch_due_checkins():
  SELECT id FROM erp_live_sessions
  WHERE status='running' AND last_checkin_at <= (now - 5min)
  → [session_id=6]
  │
  ▼
run_checkin.delay(6)     ← enqueued to Redis
  │
  ▼ (worker picks up)
run_checkin(6):
  │
  ├─ verify session.status == "running"
  ├─ UPDATE last_checkin_at = now   ← prevent duplicate
  │
  ▼ invoke_erp_coach({session_id:6, event_type:"CHECK_IN", user_message:""})
  │
  ├─ [load_context]
  ├─ [compute_metrics]       ← rate_reminder_flag=True (no SUDS for >5min)
  ├─ [mode_router]           → "LIVE"
  ├─ [log_user]              ← writes nothing (message is "")
  ├─ [live_intent_router]    ← deterministic: rate_reminder_flag=True → "RATE_REMINDER"
  ├─ [live_rate_reminder]    ← LLM call: "I haven't heard your anxiety level in 5.2 min..."
  ├─ [finalize_coach_live]
  ├─ [log_coach]             ← INSERT erp_chat_messages (role=coach, intent=CHECK_IN)
  └─ END
  │
  ▼
Frontend polls every 15s → picks up new message → append to chat
```

### END SESSION (full sequence)

```
Patient clicks "End Session"
  │
  ▼
POST /erp/sessions/6/end-clicked
  │
  ├─ session.status = "ending"
  └─ invoke_erp_coach({event_type:"END_SESSION_DEBRIEF_PROMPT"})
     │
     ├─ [load_context]
     ├─ [compute_metrics]
     ├─ [mode_router]             → "DEBRIEF_PROMPT"
     ├─ [debrief_prompt]          ← LLM: generates reflection questions
     ├─ [finalize_coach_debrief]
     ├─ [log_debrief_prompt]      ← INSERT chat message (role=coach)
     └─ END → coach_message + next_action:SHOW_DEBRIEF_FORM

Frontend shows debrief textarea with coach's reflection prompt
  │
  ▼
Patient writes and submits reflection
  │
  ▼
POST /erp/sessions/6/debrief  { patient_debrief_text: "I did the exposure for 10 min..." }
  │
  ├─ session.patient_debrief_text = text
  └─ run_end_session_report.delay(6, text)   ← async Celery

  [Celery worker — REPORT path]
  ├─ invoke_erp_coach({event_type:"END_SESSION_REPORT", patient_debrief_text:"..."})
  │  ├─ [load_context]
  │  ├─ [compute_metrics]
  │  ├─ [mode_router]           → "REPORT"
  │  ├─ [report_bundle]         ← assemble suds_points_block, report_inputs
  │  ├─ [report_facts]          ← LLM text call → session_facts_text (bullets)
  │  ├─ [report_therapist]      ← LLM structured → TherapistReportJSON
  │  ├─ [report_patient]        ← LLM structured → PatientFeedbackJSON
  │  ├─ [finalize_reports]      ← Pydantic validation
  │  ├─ [save_reports]          ← UPDATE erp_live_sessions SET therapist_report_json=..., patient_feedback_json=...
  │  └─ END

Frontend polls GET /erp/sessions/6/detail
  └─ sees patient_feedback_json → shows session summary card
```
