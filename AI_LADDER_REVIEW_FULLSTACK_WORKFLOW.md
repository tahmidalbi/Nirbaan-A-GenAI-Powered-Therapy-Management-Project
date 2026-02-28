# AI Ladder Review — Full Stack Workflow
## From Patient Submitting to Therapist Seeing Results

---

## Birds-Eye View

```
[Patient Browser]  →  PatientFearLadderPage.jsx
      │ POST /fear-ladders/{id}/submit-for-review
      ▼
[FastAPI]  fear_ladder/router.py  →  creates AILadderReview row (status=queued)
      │ .delay(review.id)
      ▼
[Celery Worker]  ai_ladder_review_v2/tasks.py
      │ run_ladder_review_agent(...)
      ▼
[LangGraph Agent]  8 nodes, multiple LLM + RAG calls
      │ writes AILadderSuggestion + AILadderEvidence rows (status=completed)
      ▼
[Therapist Browser]  →  TherapistFearLadderPatientView.jsx
      │ GET /fear-ladders/{id}/ai-review
      ▼
[AILadderReview.jsx]  renders suggestions with expandable evidence cards
```

---

## Step 1 — Patient Side (Frontend)

**File:** `frontend/src/pages/PatientFearLadderPage.jsx`

When the patient clicks "Request AI Analysis":

```jsx
// PatientFearLadderPage.jsx  line 46
const handleSubmitForAIReview = async () => {
  if (!existingLadder?.id) { /* guard */  return; }
  setAiReviewSubmitting(true);
  await submitLadderForAIReview(existingLadder.id);   // ← API call
  setSubmitMessage('✨ AI analysis requested! Your therapist will see results once complete.');
};
```

**File:** `frontend/src/api/fear-ladder.api.js`

```js
// fear-ladder.api.js  line 69
export const submitLadderForAIReview = async (ladderId) => {
  const response = await axiosInstance.post(`/fear-ladders/${ladderId}/submit-for-review`);
  return { data: response.data };
};
```

The call goes to `POST /fear-ladders/{ladder_id}/submit-for-review`.
The patient's JWT is automatically attached by `axiosInstance` (interceptor in `api/axios.js`).

---

## Step 2 — FastAPI Endpoint (Backend)

**File:** `backend/app/fear_ladder/router.py`  line ~323

```python
@router.post("/{ladder_id}/submit-for-review", status_code=202)
async def submit_ladder_for_ai_review(
    ladder_id: int,
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient)   # JWT decoded here
):
```

What happens inside, line by line:

| Line | Action |
|---|---|
| ~330 | Verifies `FearLadder.patient_id == current_patient.id` — 404 if mismatch |
| ~340 | Looks up `patient.therapist_id` — 400 if no therapist assigned |
| ~350 | Checks for `status IN (queued, running)` — returns early if already running |
| ~362 | Creates `AILadderReview(status=queued, ladder_id, patient_id, therapist_id)` |
| ~367 | `db.add(review); db.commit(); db.refresh(review)` |
| ~370 | `run_ladder_review_agent_v2_task.delay(review.id)` — submits to Celery broker |
| ~372 | Returns `{review_id, status: "queued"}` to browser immediately (202 Accepted) |

The response is **202 Accepted** — the patient gets immediate confirmation, the heavy work happens async.

---

## Step 3 — Celery Task

**File:** `backend/app/ai_ladder_review_v2/tasks.py`

```python
@celery_app.task(bind=True, name="run_ladder_review_agent_v2_task")
def run_ladder_review_agent_v2_task(self, review_id, *, requested_by_therapist_id=None, ...):
    db = SessionLocal()
    # 1. Fetch review row
    review = db.get(AILadderReview, review_id)
    # 2. Validate therapist ownership (if provided)
    # 3. Idempotency: skip if already completed + has suggestions
    if review.status == completed and review.suggestions:
        return {"skipped": True}
    # 4. Mark running, commit
    review.status = AILadderReviewStatus.running
    db.commit(); db.close()
    # 5. Run the LangGraph agent
    from app.ai_ladder_review_v2.ladder_review_agent.graph import run_ladder_review_agent
    result = run_ladder_review_agent(db_session_factory=SessionLocal, review_id=review_id, ...)
    return result
    # On exception → fresh session → mark review.status = failed, set error_message
```

The Celery task is registered via `celery_app.py`:
```python
# app/core/celery_app.py  line 19-20
include=[
    'app.ai_ladder_review.tasks',
    'app.ai_ladder_review_v2.tasks',   # ← this one
]
```

The task runs on the Celery worker process (started via `start_celery.py` / `celery_worker.bat`),
completely separate from FastAPI's process.

---

## Step 4 — LangGraph Agent Runs

**File:** `backend/app/ai_ladder_review_v2/ladder_review_agent/graph.py`

```python
def run_ladder_review_agent(*, db_session_factory, review_id, ...):
    db = db_session_factory()                          # one DB session for the whole run
    app = build_ladder_review_graph(db=db, ...)        # build + compile LangGraph
    final_state = app.invoke({"review_id": str(review_id)})   # run all nodes
    return final_state.get("result_payload", {})
```

The agent goes through 8 nodes (detailed in the second doc).
At the end, the `finalizer` node writes:

- `AILadderSuggestion` rows — each has `obsession_label`, `compulsion_summary`, `rationale`
- `AILadderEvidence` rows — each has `source_type`, `source_id`, `quote_text`, `source_date`
- Sets `AILadderReview.status = completed`

---

## Database Models Involved

**File:** `backend/app/fear_ladder/models.py`

```
AILadderReview (ai_ladder_reviews)
  id, ladder_id, patient_id, therapist_id
  status: queued→running→completed|failed
  error_message, model_name, created_at
  → suggestions: [AILadderSuggestion]

AILadderSuggestion (ai_ladder_suggestions)
  id, review_id
  obsession_label   — "Fear of contamination"
  compulsion_summary — "Hand washing; avoidance of door handles"
  rationale          — "Detected in logs + intake evidence"
  → evidence: [AILadderEvidence]

AILadderEvidence (ai_ladder_evidence)
  id, suggestion_id
  source_type   — "daily_log" | "intake"
  source_id     — entry ID (matches [E123] tag from log lines)
  source_date   — date of the log entry
  field_name    — e.g. "ritual", "event"
  quote_text    — exact quote from the log/intake
```

---

## Step 5 — Therapist Reads Results (Frontend)

**File:** `frontend/src/pages/TherapistFearLadderPatientView.jsx`

When the therapist opens a patient's ladder view, the page auto-fetches the AI review:

```jsx
// TherapistFearLadderPatientView.jsx  line 35
useEffect(() => {
  if (patientId) { fetchPatientLadder(); }
}, [patientId]);

const fetchPatientLadder = async () => {
  const response = await getPatientFearLadder(patientId);   // fetches FearLadder
  setLadder(response.data);
  if (response.data?.id) {
    fetchAIReview(response.data.id);    // ← triggers AI review fetch
  }
};

// line 47
const fetchAIReview = async (ladderId) => {
  const response = await getLadderAIReview(ladderId);   // GET /fear-ladders/{id}/ai-review
  setAiReview(response.data);
};
```

**File:** `frontend/src/api/fear-ladder.api.js`  line 78

```js
export const getLadderAIReview = async (ladderId) => {
  const response = await axiosInstance.get(`/fear-ladders/${ladderId}/ai-review`);
  return { data: response.data };
};
```

---

## Step 6 — FastAPI Returns Review to Therapist

**File:** `backend/app/fear_ladder/router.py`  line ~390

```python
@router.get("/{ladder_id}/ai-review", response_model=AILadderReviewSummary)
async def get_ladder_ai_review(
    ladder_id: int,
    db: Session = Depends(get_db),
    current_therapist: Therapist = Depends(get_current_therapist)   # therapist JWT only
):
    # Verifies FearLadder belongs to therapist's patient (security check)
    ladder = db.query(FearLadder).join(Patient).filter(
        FearLadder.id == ladder_id,
        Patient.therapist_id == current_therapist.id    # ← ownership enforced
    ).first()

    # Gets most recent review ordered by created_at desc
    review = db.query(AILadderReview).filter(
        AILadderReview.ladder_id == ladder_id
    ).order_by(AILadderReview.created_at.desc()).first()

    return AILadderReviewSummary(
        status=review.status.value,
        suggestions=[s for s in review.suggestions] if review.status == completed else [],
        error_message=review.error_message
    )
```

A second endpoint exists for full metadata (with trace/evidences):
`GET /fear-ladders/{ladder_id}/ai-review/full` → `AILadderReviewResponse`

---

## Step 7 — Therapist Sees Results (UI)

The `aiReview` state flows into the layout:

```jsx
// TherapistFearLadderPatientView.jsx  line 191
<div className="ai-details-section">
  <h3>AI Analysis</h3>
  <AILadderReview reviewData={aiReview} />
</div>
```

**File:** `frontend/src/components/AILadderReview.jsx`

The component handles all 4 status states:

| `reviewData` state | What the therapist sees |
|---|---|
| `null` | "Patient needs to submit ladder for analysis" |
| `status: queued/running` | Spinner — "AI Analysis in Progress" |
| `status: failed` | Error box with `error_message` |
| `status: completed, suggestions=[]` | "No additional patterns detected" |
| `status: completed, suggestions=[...]` | Expandable suggestion cards with evidence |

Each suggestion card (on expand) shows:
- **AI Rationale**: the `rationale` text
- **Evidence quotes**: source badge (Intake / Daily Log), date, field name, and the exact `quote_text`

---

## Status Flow Summary

```
Patient clicks "Request AI Analysis"
  → POST /submit-for-review → 202 Accepted
    → AILadderReview.status = queued

Celery picks up the task
  → AILadderReview.status = running

LangGraph agent finishes → finalizer writes suggestions
  → AILadderReview.status = completed
  → AILadderSuggestion + AILadderEvidence rows created

Therapist opens patient ladder view
  → GET /ai-review → returns suggestions
  → AILadderReview.jsx renders expandable suggestion cards
```

---

## Security Boundaries

| Check | Where enforced |
|---|---|
| Patient can only submit their own ladder | `FearLadder.patient_id == current_patient.id` |
| No double-queue | Status guard: returns early if `queued` or `running` already exists |
| Therapist can only read their assigned patients | `Patient.therapist_id == current_therapist.id` join |
| Celery task validates ownership | `review.therapist_id != requested_by_therapist_id` check |
| Idempotency | Task exits if `status==completed` and suggestions exist |
