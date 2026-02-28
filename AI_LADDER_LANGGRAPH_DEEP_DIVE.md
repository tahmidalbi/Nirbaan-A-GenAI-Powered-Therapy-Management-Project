# AI Ladder Review v2 — LangGraph Agent Deep Dive
## Every Node, Every File, Every Line of Logic

---

## What the Agent Does

Given a patient's fear ladder and their recent self-monitoring logs, the agent finds
**obsession-compulsion pairs that exist in the patient's behaviour but are absent from their declared ladder**.
It uses a combination of RAG (OCD taxonomy retrieval) and multiple LLM calls inside a stateful
LangGraph loop.

---

## File Map

```
ai_ladder_review_v2/
  tasks.py                              ← Celery entrypoint
  ladder_review_agent/
    graph.py                            ← builds + wires the LangGraph
    state.py                            ← shared state dataclass
    schemas.py                          ← Pydantic schemas for LLM responses
    nodes/
      load_context.py                   ← DB reads (no LLM)
      ladder_extractor.py               ← LLM: normalise ladder
      create_batches.py                 ← chunk log entries (no LLM)
      taxonomy_retriever_node.py        ← RAG: retrieve OCD taxonomy
      symtom_finder.py                  ← LLM: extract O-C candidates
      checker.py                        ← LLM: should we recheck?
      hidden_matcher.py                 ← LLM: which candidates are missing?
      finalizer.py                      ← DB writes (no LLM)
    prompts/
      ladder_extractor_prompt.py
      symtom_finder_prompt.py
      checker_prompt.py
      hidden_matcher_prompt.py
  rag/
    taxonomy_retriever.py               ← pgvector similarity search
    taxonomy_model.py                   ← DB model for taxonomy chunks
    embedding_client.py                 ← OpenAI embeddings
    taxonomy_seed.py                    ← seeds OCD taxonomy into DB
    constants.py                        ← TAXONOMY_VERSION = "1.1"
```

---

## State — `state.py`

Every node receives and returns a single `LadderReviewState` dataclass.

```python
@dataclass
class LadderReviewState:
    # identity
    review_id: str = ""
    patient_id: str = ""
    therapist_id: str = ""

    # loaded by load_context
    intake_text: str = ""
    ladder_raw_text: str = ""
    logs_raw: List[Dict] = field(default_factory=list)

    # set by ladder_extractor
    ladder_items: List[Dict] = field(default_factory=list)
    ladder_text: str = ""

    # set by create_batches
    batches: List[Dict] = field(default_factory=list)
    batch_index: int = 0
    batch_retry_count: int = 0
    max_batch_retries: int = 2

    # per-batch working set (taxonomy_retriever → symptom_finder → checker)
    taxonomy_context_text: str = ""
    retrieved_taxonomy_titles: List[str] = field(default_factory=list)
    batch_candidates: List[Dict] = field(default_factory=list)
    recheck: bool = False
    recheck_reason: str = ""
    recheck_query: str = ""

    # accumulated across all batches
    candidates_all: List[Dict] = field(default_factory=list)

    # set by hidden_matcher
    missing_ids: List[str] = field(default_factory=list)

    # set by finalizer
    result_payload: Dict = field(default_factory=dict)

    errors: List[str] = field(default_factory=list)
    trace: List[Dict] = field(default_factory=list)
```

LangGraph requires a plain `dict` as state.  
`graph.py` converts back and forth using two helpers:

```python
def _to_state(d: dict) -> LadderReviewState:
    return LadderReviewState(**d)

def _to_dict(s: LadderReviewState) -> dict:
    return asdict(s)
```

Every node is wrapped so LangGraph sees `dict → dict`, but the node code works with the dataclass:

```python
def _wrap_no_db(fn):
    def _inner(d):
        st = _to_state(d)
        st = fn(st)          # node modifies state
        return _to_dict(st)
    return _inner

def _wrap_with_db(fn, db):
    def _inner(d):
        st = _to_state(d)
        st = fn(db, st)      # node gets DB session too
        return _to_dict(st)
    return _inner
```

---

## Graph Construction — `graph.py`

```python
def build_ladder_review_graph(*, db, taxonomy_version, taxonomy_top_k, max_entries_per_batch):
    graph = StateGraph(StateDict)   # LangGraph graph over plain dict

    # Register all nodes
    graph.add_node("mark_review_running", mark_review_running_node)
    graph.add_node("load_context",        _wrap_with_db(load_context_node, db))
    graph.add_node("ladder_extractor",    _wrap_no_db(ladder_extractor_node))
    graph.add_node("create_batches",      create_batches_configured)
    graph.add_node("taxonomy_retriever",  taxonomy_retriever_configured)
    graph.add_node("symptom_finder",      _wrap_no_db(symptom_finder_node))
    graph.add_node("checker",             _wrap_no_db(checker_node))
    graph.add_node("recheck_same_batch",  recheck_same_batch_node)
    graph.add_node("advance_batch",       advance_batch_node)
    graph.add_node("hidden_matcher",      _wrap_no_db(hidden_matcher_node))
    graph.add_node("finalizer",           finalizer_configured)

    # Wire edges (see section below)
    ...
    return graph.compile()
```

---

## Node 1 — `mark_review_running` (inline in `graph.py`)

```python
def mark_review_running_node(d):
    st = _to_state(d)
    review = db.get(AILadderReview, int(st.review_id))
    review.status = AILadderReviewStatus.running
    review.error_message = None
    db.commit()
    st.log_trace("mark_review_running", {"review_id": st.review_id})
    return _to_dict(st)
```

**Purpose:** Sets the DB row to `running` before any expensive work, so the frontend
can show a spinner immediately.

---

## Node 2 — `load_context` (`nodes/load_context.py`)

**No LLM. Pure DB reads.**

```python
def load_context_node(db, state, *, days_back=14):
    review = db.get(AILadderReview, int(state.review_id))
    state.patient_id = str(review.patient_id)
    state.therapist_id = str(review.therapist_id)
```

### Ladder items
```python
    ladder = db.get(FearLadder, int(review.ladder_id))
    ladder_items = db.execute(
        select(FearLadderItem).where(FearLadderItem.fear_ladder_id == ladder.id)
    ).scalars().all()
    state.ladder_raw_text = _ladder_items_to_raw_text(ladder_items)
    # produces:  "- (60/100) Touching door handles\n- (40/100) Checking the stove"
```

### Intake
```python
    intake = db.execute(
        select(PatientIntake).where(PatientIntake.patient_id == ...)
    ).scalar_one_or_none()
    state.intake_text = _intake_to_text(intake)
    # joins: your_story, when_started, medication, affected_life_areas, issues list
```

### Self-monitoring logs
```python
    cutoff = datetime.utcnow() - timedelta(days=days_back)
    days = db.execute(
        select(SelfMonitoringDay)
        .where(SelfMonitoringDay.patient_id == patient_id, SelfMonitoringDay.date >= cutoff)
    ).scalars().all()
    # Flattens nested SelfMonitoringEntry rows into state.logs_raw
    # Each dict: {entry_id, date, time, event, ritual, time_spent, anxiety_level}
```

---

## Node 3 — `ladder_extractor` (`nodes/ladder_extractor.py`)

**LLM Call #1.**

```python
def ladder_extractor_node(state):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    model = os.getenv("LLM_MODEL", "gpt-5.2")

    prompt = build_ladder_extractor_prompt(state.ladder_raw_text)
    resp = client.responses.create(model=model, input=prompt)
    parsed = LadderExtractionResponse.model_validate_json(resp.output_text)

    state.ladder_items = [x.model_dump() for x in parsed.ladder_items]
    # Each item: {id, obsession, compulsions: [...]}

    # compact text for hidden_matcher later:
    # "- Fear of contamination || hand washing; avoidance"
    state.ladder_text = "\n".join(compact)
```

**Why?** The raw ladder is SUDS-ordered plain text like `"(60/100) Door handles"`.
The LLM normalises it into structured obsession + compulsion objects that can be
compared programmatically later.

**Pydantic schema (`schemas.py`):**
```python
class LadderItem(BaseModel):
    id: str
    obsession: str
    compulsions: List[str]

class LadderExtractionResponse(BaseModel):
    ladder_items: List[LadderItem]
```

---

## Node 4 — `create_batches` (`nodes/create_batches.py`)

**No LLM. Pure Python.**

```python
def create_batches_node(state, *, max_entries_per_batch=40):
    entries = state.logs_raw
    lines = [_entry_to_line(e) for e in entries]
    # Each line:
    # "[E42] DATE:2026-02-25 TIME:09:00 | EVENT:touched door | RITUAL:hand wash | TIME_SPENT_MIN:15 | ANXIETY:7/10"
    #  ^^^^ The [E<id>] prefix makes evidence traceable back to DB rows

    for i in range(0, len(lines), max_entries_per_batch):
        chunk = lines[i:i+max_entries_per_batch]
        batches.append({
            "batch_id": f"B{batch_id}",
            "text": "\n".join(f"- {ln}" for ln in chunk),
            "meta": {
                "entry_count": len(chunk),
                "entry_ids": [...],
                "date_from": ...,   "date_to": ...
            }
        })
    state.batches = batches
    state.batch_index = 0
```

**Why batch?** LLM context windows are limited.
40 entries ≈ ~2k tokens, safe for a single call even with taxonomy context injected.

**Router after create_batches:**
```python
def after_create_batches_router(d):
    st = _to_state(d)
    return "taxonomy_retriever" if st.batches else "hidden_matcher"
    # If no logs at all → skip straight to hidden_matcher
```

---

## Node 5 — `taxonomy_retriever` (`nodes/taxonomy_retriever_node.py`)

**RAG — pgvector similarity search. No LLM for the retrieval itself.**

```python
def taxonomy_retriever_node(db, state, *, top_k=6, taxonomy_version="1.1"):
    batch = state.current_batch()
    query_for_retrieval = batch["text"]

    # On recheck, the checker LLM provided a focused query
    if state.batch_retry_count > 0 and state.recheck_query.strip():
        query_for_retrieval = f"{batch_text}\n\nFOCUS:\n{state.recheck_query.strip()}"

    retriever = TaxonomyRetriever()
    chunks = retriever.retrieve(
        db,
        query=query_for_retrieval,
        version=taxonomy_version,
        k=top_k,
        ensure_core=True,    # always include the core OCD definition chunk
    )

    state.retrieved_taxonomy_titles = [c.title for c in chunks]
    state.taxonomy_context_text = "\n\n".join(
        f"### {c.title}\n{c.content}" for c in chunks
    )
```

**How retrieval works (`rag/taxonomy_retriever.py`):**
1. `embedding_client.py` calls `OpenAI embeddings` on `query_for_retrieval`.
2. pgvector cosine similarity search over `taxonomy_chunks` table (versioned).
3. Returns top-K chunks (e.g., "OCD: Contamination", "OCD: Checking", "OCD: Symmetry").
4. `ensure_core=True` forces inclusion of the foundational OCD boundary chunk.

The taxonomy was seeded via `rag/taxonomy_seed.py` once during setup.

---

## Node 6 — `symptom_finder` (`nodes/symtom_finder.py`)

**LLM Call #2 (per batch).**

```python
def symptom_finder_node(state):
    batch = state.current_batch()
    intake_text = state.intake_text if state.batch_index == 0 else ""
    # Only inject intake on batch 0 to save tokens on subsequent batches

    prompt = build_symptom_finder_prompt(
        taxonomy_context_text=state.taxonomy_context_text,  # RAG-retrieved OCD knowledge
        intake_text=intake_text,                            # patient's story
        batch_text=batch["text"],                           # log entries with [E<id>] tags
        recheck_mode=(state.batch_retry_count > 0),
    )
    resp = client.responses.create(model=model, input=prompt)
    parsed = SymptomFinderResponse.model_validate_json(resp.output_text)
    # parsed.candidates: [{id, obsession, compulsions, evidence: [{source_type, source_id, quote_text, ...}]}]

    # Deduplicate against candidates_all using normalised key: "obsession||first_compulsion"
    existing = {_candidate_key(c): c for c in state.candidates_all}
    for c in batch_candidates:
        k = _candidate_key(c)
        if k not in existing:
            existing[k] = c

    state.batch_candidates = batch_candidates
    state.candidates_all = list(existing.values())
```

The prompt gives the LLM:
- OCD taxonomy context (what OCD subtypes look like)
- Intake text (what the patient said about themselves)
- Raw log entries (what the patient actually did)

The LLM identifies obsession-compulsion patterns and extracts direct quotes as evidence,
quoting the `[E<id>]` entry IDs so they can be stored in `AILadderEvidence.source_id`.

---

## Node 7 — `checker` (`nodes/checker.py`)

**LLM Call #3 (per batch). Quality gate.**

```python
def checker_node(state):
    prompt = build_checker_prompt(
        batch_text=batch["text"],
        extracted_candidates_json=json.dumps({"candidates": state.batch_candidates}),
    )
    resp = client.responses.create(model=model, input=prompt)
    parsed = CheckerResponse.model_validate_json(resp.output_text)

    state.recheck = bool(parsed.recheck)
    state.recheck_reason = parsed.reason
    state.recheck_query = parsed.recheck_query or ""
```

The checker asks: *"Does the extracted list look complete and plausible given the log entries?"*
If not, it returns `recheck=True` plus a focused `recheck_query` like `"aggressive obsessions"` 
to bias the next retrieval pass toward different taxonomy chunks.

**Pydantic schema:**
```python
class CheckerResponse(BaseModel):
    recheck: bool
    reason: str
    recheck_query: str = ""
```

---

## Routing After Checker — The Batch Loop

```python
def advance_or_recheck_router(d):
    st = _to_state(d)
    if not st.current_batch():
        return "hidden_matcher"
    if st.recheck and st.batch_retry_count < st.max_batch_retries:
        return "recheck_same_batch"     # same batch, biased retrieval
    return "advance_batch"              # move to next batch

def recheck_same_batch_node(d):
    st = _to_state(d)
    st.batch_retry_count += 1          # increment, keep batch_index
    return _to_dict(st)
    # → goes back to taxonomy_retriever with recheck_query in state

def advance_batch_node(d):
    st = _to_state(d)
    st.batch_index += 1
    st.batch_retry_count = 0
    st.recheck = False;  st.recheck_reason = "";  st.recheck_query = ""
    st.batch_candidates = [];  st.taxonomy_context_text = ""
    return _to_dict(st)

def after_advance_router(d):
    st = _to_state(d)
    return "hidden_matcher" if st.is_done() else "taxonomy_retriever"
```

**Per-batch recheck flow:**
```
taxonomy_retriever → symptom_finder → checker
    checker says recheck=True, retry_count < 2
       → recheck_same_batch (retry_count++) → taxonomy_retriever (with biased query)
       → symptom_finder → checker again
    checker satisfied OR retry_count == 2
       → advance_batch → next batch OR hidden_matcher
```

Maximum LLM calls per batch: `(retriever + symptom_finder + checker) × (1 + max_retries)` = 9 LLM calls per batch worst case.

---

## Node 8 — `hidden_matcher` (`nodes/hidden_matcher.py`)

**LLM Call — once, after all batches.**

```python
def hidden_matcher_node(state):
    ladder_items_json = json.dumps({"ladder_items": state.ladder_items})
    # What patient declared on their ladder (normalised by ladder_extractor)

    candidates_all_json = json.dumps({"candidates": state.candidates_all})
    # What the agent found across ALL batches (deduped)

    prompt = build_hidden_matcher_prompt(ladder_items_json, candidates_all_json)
    resp = client.responses.create(model=model, input=prompt)
    parsed = HiddenMatcherResponse.model_validate_json(resp.output_text)

    state.missing_ids = parsed.missing_ids
    # IDs of candidates not already covered by any ladder item
```

The LLM compares the two lists and returns IDs of candidates that are genuinely new —
not already described by an existing ladder item, even if phrased differently.

---

## Node 9 — `finalizer` (`nodes/finalizer.py`)

**No LLM. DB writes only.**

```python
def finalizer_node(db, state):
    review = db.get(AILadderReview, int(state.review_id))
    missing_set = set(state.missing_ids)
    missing_candidates = [c for c in state.candidates_all if c.get("id") in missing_set]

    # Delete old suggestions (idempotent reruns)
    for s in list(review.suggestions): db.delete(s)
    db.flush()

    for cand in missing_candidates:
        sug = AILadderSuggestion(
            review_id=review.id,
            obsession_label=cand["obsession"],
            compulsion_summary="; ".join(cand.get("compulsions", [])),
            rationale=cand.get("label", "") + (" (Potential pattern)" if cand.get("potential_pattern") else ""),
        )
        db.add(sug);  db.flush()   # flush to get sug.id

        # Evidence rows — each [E42] tag becomes source_id=42 in DB
        for ev in cand.get("evidence", []):
            source_id = int(str(ev["source_id"]).replace("E", ""))
            db.add(AILadderEvidence(
                suggestion_id=sug.id,
                source_type=ev.get("source_type", "daily_log"),
                source_id=source_id,
                source_date=datetime.fromisoformat(ev["source_date"]) if ev.get("source_date") else None,
                field_name=ev.get("field_name"),
                quote_text=ev["quote_text"],
            ))

    review.status = AILadderReviewStatus.completed
    review.model_name = "gpt-5.2"
    db.commit()

    state.result_payload = {"review_id": review.id, "status": "completed", "missing_count": len(missing_candidates)}
```

---

## Complete Edge Map

```python
graph.set_entry_point("mark_review_running")

graph.add_edge("mark_review_running",  "load_context")
graph.add_edge("load_context",         "ladder_extractor")
graph.add_edge("ladder_extractor",     "create_batches")

graph.add_conditional_edges("create_batches", after_create_batches_router, {
    "taxonomy_retriever": "taxonomy_retriever",
    "hidden_matcher":     "hidden_matcher",
})

graph.add_edge("taxonomy_retriever",   "symptom_finder")
graph.add_edge("symptom_finder",       "checker")

graph.add_conditional_edges("checker", advance_or_recheck_router, {
    "recheck_same_batch": "recheck_same_batch",
    "advance_batch":      "advance_batch",
    "hidden_matcher":     "hidden_matcher",
})

graph.add_edge("recheck_same_batch",   "taxonomy_retriever")   # re-enter batch loop

graph.add_conditional_edges("advance_batch", after_advance_router, {
    "taxonomy_retriever": "taxonomy_retriever",   # next batch
    "hidden_matcher":     "hidden_matcher",       # all batches done
})

graph.add_edge("hidden_matcher",       "finalizer")
graph.add_edge("finalizer",            END)
```

---

## Visual Graph

```
START
  └─► mark_review_running
        └─► load_context        (DB: ladder + intake + logs)
              └─► ladder_extractor   (LLM #1: normalise ladder)
                    └─► create_batches    (chunk logs into B1, B2, ...)
                          │
                    [has batches?]
                    yes ──►  ┌─────────────────────────────┐
                             │   taxonomy_retriever (RAG)  │◄──── recheck_same_batch ◄──┐
                             │         │                   │                             │
                             │   symptom_finder (LLM #2)  │                             │
                             │         │                   │     [recheck + retries left]│
                             │   checker (LLM #3) ─────────►────────────────────────────┘
                             └─────────┼───────────────────┘
                                       │ [advance OR done]
                                  advance_batch
                                       │
                              [more batches?] ──yes──► loop back
                              [done]
                    no ──────────────────────────────────────────►
                                                                  hidden_matcher (LLM #4)
                                                                        │
                                                                   finalizer (DB writes)
                                                                        │
                                                                       END
```

---

## LLM Call Summary

| Call # | Node | Model Env Var | Input | Output |
|---|---|---|---|---|
| 1 | `ladder_extractor` | `LLM_MODEL` (gpt-5.2) | Raw SUDS ladder text | `LadderExtractionResponse` |
| 2/batch | `symptom_finder` | `LLM_MODEL` | taxonomy + intake + log batch | `SymptomFinderResponse` |
| 3/batch | `checker` | `LLM_MODEL` | batch text + candidates JSON | `CheckerResponse` |
| Final | `hidden_matcher` | `LLM_MODEL` | ladder_items JSON + candidates_all JSON | `HiddenMatcherResponse` |

Plus one embedding call per batch for RAG retrieval (`OpenAI text-embedding-*` via `embedding_client.py`).

---

## Key Design Patterns

### `[E<id>]` evidence tags
Every log line is formatted as `[E42] DATE:... RITUAL:...`.
When the LLM quotes evidence, it copies these tags.
`finalizer.py` strips `"E"` and parses the integer as `AILadderEvidence.source_id`,
giving a direct DB FK to the original `SelfMonitoringEntry`.

### Deduplication in `symptom_finder`
Candidates across batches are deduped using a normalised string key:
```python
def _candidate_key(c):
    obs = c["obsession"].lower().strip()
    first = (c["compulsions"][0] if c["compulsions"] else "").lower().strip()
    return f"{obs}||{first}"
```
Same pattern found in batch B1 and B3 → stored once.

### Bounded retries
`max_batch_retries = 2` means each batch gets at most 3 total passes (1 original + 2 rechecks).
This bounds LLM spend while still allowing self-correction.

### One DB session for the whole graph
`run_ladder_review_agent()` opens one `SessionLocal()` and passes it into `build_ladder_review_graph(db=db)`.
Every node that needs DB access closes over this session via `_wrap_with_db`.
Session is closed in the `finally` block after `app.invoke()` returns.
