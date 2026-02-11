# Nirbaan AI — Multi-Agent Treatment Protocol Generator

## Research-Grade System Architecture Document

**Version**: 1.0  
**Date**: February 11, 2026  
**System**: LangGraph-based Multi-Agent Orchestration for Automated Therapy Session Protocol Generation  
**Stack**: LangGraph · OpenAI GPT-4o · pgvector · FastAPI · PostgreSQL · React

---

## Table of Contents

1. [Abstract](#1-abstract)
2. [System Overview](#2-system-overview)
3. [Frontend Architecture — Nirbaan AI Interface](#3-frontend-architecture--nirbaan-ai-interface)
4. [Multi-Agent Orchestration Graph — LangGraph Pipeline](#4-multi-agent-orchestration-graph--langgraph-pipeline)
5. [Shared State Schema](#5-shared-state-schema)
6. [Agent 1 — History Picker Agent](#6-agent-1--history-picker-agent)
7. [Agent 2 — Session Picker Agent](#7-agent-2--session-picker-agent)
8. [Agent 3 — Stage Picker Agent](#8-agent-3--stage-picker-agent)
9. [Agent 4 — Blueprint Generator Agent](#9-agent-4--blueprint-generator-agent)
10. [Agent 5 — Protocol Generator Agent](#10-agent-5--protocol-generator-agent)
11. [Agent 6 — Uncertainty Scorer Agent](#11-agent-6--uncertainty-scorer-agent)
12. [Knowledge Base Integration Layer](#12-knowledge-base-integration-layer)
13. [Memory Architecture — Per-Patient Per-Therapist Isolation](#13-memory-architecture--per-patient-per-therapist-isolation)
14. [Error Propagation & Graceful Degradation](#14-error-propagation--graceful-degradation)
15. [Backend API Design](#15-backend-api-design)
16. [Database Schema Extensions](#16-database-schema-extensions)
17. [Data Flow Diagram — End-to-End](#17-data-flow-diagram--end-to-end)
18. [Security & Access Control](#18-security--access-control)
19. [Future Work](#19-future-work)
20. [References](#20-references)

---

## 1. Abstract

Nirbaan AI Protocol Generator is a multi-agent orchestration system built on **LangGraph** that automates the generation of **60-minute therapy session protocols** grounded entirely in a therapist's uploaded knowledge base (KB). The system employs six specialised agents arranged in a directed acyclic graph (DAG), where each agent has a well-defined responsibility, explicit input/output contracts, and a mandatory knowledge-base grounding constraint. An **Uncertainty Scorer** agent (designed for future publication as a Q1 journal contribution) annotates the final protocol with both global and per-claim epistemic uncertainty scores, giving the therapist transparent confidence metrics before clinical use.

The system enforces **strict multi-tenant isolation**—every datum accessed and every protocol generated is scoped to a `(therapist_id, patient_id)` pair—ensuring that one therapist's patients, knowledge, and session histories are never visible to another.

---

## 2. System Overview

### 2.1 High-Level Pipeline

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                           THERAPIST FRONTEND (React)                             │
│                                                                                  │
│  ┌──────────────┐    ┌───────────────────────────────────────┐                   │
│  │ Patient List  │───▶│  Patient Protocol Workspace           │                   │
│  │   (Sidebar)   │    │  ┌─────────────────────────────────┐  │                   │
│  │               │    │  │ Session Focus Input (textarea)   │  │                   │
│  │  • Patient A  │    │  ├─────────────────────────────────┤  │                   │
│  │  • Patient B  │    │  │ [Generate Protocol] Button       │  │                   │
│  │  • Patient C  │    │  ├─────────────────────────────────┤  │                   │
│  │  • ...        │    │  │ Generated Protocol Display       │  │                   │
│  └──────────────┘    │  │  + Uncertainty Annotations        │  │                   │
│                      │  └─────────────────────────────────┘  │                   │
│                      └───────────────────────────────────────┘                   │
└──────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼  POST /ai/generate-protocol
┌──────────────────────────────────────────────────────────────────────────────────┐
│                            BACKEND (FastAPI)                                     │
│                                                                                  │
│  ┌────────────────────────────────────────────────────────────────────────────┐  │
│  │                    LangGraph Multi-Agent Pipeline                          │  │
│  │                                                                            │  │
│  │  ┌─────────────┐   ┌──────────────┐   ┌──────────────┐                    │  │
│  │  │  History     │──▶│  Session      │──▶│  Stage       │                    │  │
│  │  │  Picker      │   │  Picker       │   │  Picker      │                    │  │
│  │  │  Agent       │   │  Agent        │   │  Agent       │                    │  │
│  │  └─────────────┘   └──────────────┘   └──────┬───────┘                    │  │
│  │                                               │                            │  │
│  │                               ┌───────────────┤                            │  │
│  │                               ▼               ▼                            │  │
│  │                    ┌──────────────┐   ┌──────────────┐                     │  │
│  │                    │  Blueprint    │   │  HALT:       │                     │  │
│  │                    │  Generator    │   │  Insufficient│                     │  │
│  │                    │  Agent        │   │  KB Info     │                     │  │
│  │                    └──────┬───────┘   └──────────────┘                     │  │
│  │                           │                                                │  │
│  │                           ▼                                                │  │
│  │                    ┌──────────────┐                                         │  │
│  │                    │  Protocol     │                                         │  │
│  │                    │  Generator    │                                         │  │
│  │                    │  Agent        │                                         │  │
│  │                    └──────┬───────┘                                         │  │
│  │                           │                                                │  │
│  │                           ▼                                                │  │
│  │                    ┌──────────────┐                                         │  │
│  │                    │  Uncertainty  │                                         │  │
│  │                    │  Scorer       │                                         │  │
│  │                    │  Agent        │                                         │  │
│  │                    └──────────────┘                                         │  │
│  └────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌───────────────┐  ┌────────────────────────────┐  │
│  │PostgreSQL │  │ pgvector │  │ Cloudflare R2 │  │ OpenAI GPT-4o / Embeddings│  │
│  └──────────┘  └──────────┘  └───────────────┘  └────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Design Principles

| Principle | Implementation |
|---|---|
| **Knowledge-Base Grounding** | Every agent that produces clinical content must retrieve from the therapist's KB via pgvector similarity search. No free-form hallucination is permitted. |
| **Fail-Fast on Insufficient Evidence** | Agents 3, 4, and 5 each independently verify that the KB contains sufficient material. If not, the pipeline halts immediately with a structured `INSUFFICIENT_KB_INFO` response rather than generating speculative content. |
| **Multi-Tenant Isolation** | All queries are scoped by `therapist_id`. Patient data is further scoped by `patient_id`. No cross-therapist or cross-patient data leakage is possible at the database query level. |
| **Deterministic Reproducibility** | LLM calls use `temperature=0`. Retrieved chunks are logged. The full state graph is persisted, enabling protocol re-generation audits. |
| **Epistemic Transparency** | The Uncertainty Scorer provides both a global protocol-level confidence score and per-claim inline confidence scores, giving the therapist calibrated trust signals. |
| **Stateful Patient Memory** | The system accumulates and remembers all generated protocols, therapist feedback, and patient trajectory data across sessions, scoped per `(therapist_id, patient_id)` pair. |

---

## 3. Frontend Architecture — Nirbaan AI Interface

### 3.1 Navigation & Layout

The **Nirbaan AI** tab in the Therapist Dashboard renders a two-panel layout:

**Left Panel — Patient Selector**
- Lists all patients assigned to the currently authenticated therapist
- Each card displays: patient name, conditions, current therapy week, last protocol generation date
- Clicking a patient card loads the right panel with that patient's AI workspace

**Right Panel — Patient AI Workspace**
- Header: Patient name, conditions, therapy week indicator
- **Session Focus Input** (`<textarea>`): Free-text field where the therapist can type:
  - The focus of the upcoming session (e.g., *"exposure hierarchy for social anxiety"*)
  - Specific techniques to emphasise
  - Areas of concern or breakthroughs from last session
  - Any overriding instructions for the protocol generator
- **[Generate Protocol]** button: Triggers the multi-agent pipeline
- **Protocol Display Area**: Renders the generated 60-minute protocol with:
  - Structured timeline (minute-by-minute or block-by-block)
  - Inline uncertainty badges on critical claims (e.g., `[Confidence: 0.82]`)
  - Global uncertainty score header
  - Source citations from the KB
  - Expandable sections for each protocol phase

### 3.2 Frontend State

```javascript
// Zustand store (conceptual)
{
  selectedPatientId: number | null,
  sessionFocus: string,               // therapist's free-text input
  isGenerating: boolean,              // loading state during pipeline execution
  generatedProtocol: {
    protocol_id: number,
    patient_id: number,
    stage: string,
    blueprint: object,
    protocol_text: string,            // the full 60-minute protocol
    uncertainty: {
      global_score: number,           // 0.0 – 1.0
      per_claim_scores: [
        { claim: string, score: number, source: string }
      ]
    },
    sources_used: string[],
    created_at: string,
  } | null,
  protocolHistory: [],                // previous protocols for this patient
  error: string | null,               // "INSUFFICIENT_KB_INFO" or other errors
}
```

### 3.3 API Call on Generate

```javascript
// POST /ai/generate-protocol
const response = await axiosInstance.post('/ai/generate-protocol', {
  patient_id: selectedPatientId,
  session_focus: sessionFocus,        // therapist's free-text guidance
});
```

---

## 4. Multi-Agent Orchestration Graph — LangGraph Pipeline

### 4.1 Why LangGraph

LangGraph (built on LangChain) provides:
- **Stateful, cyclic graph execution** — agents can conditionally branch and loop
- **Typed shared state** — enforced via `TypedDict` state schema passed between nodes
- **Checkpointing** — full state snapshots at each node for audit and debugging
- **Conditional edges** — route to `HALT` nodes when KB evidence is insufficient
- **First-class tool integration** — agents can call retrieval tools, database tools, etc.

### 4.2 Graph Topology

```
                    ┌─────────────────┐
                    │    __START__     │
                    │  (therapist_id,  │
                    │   patient_id,    │
                    │   session_focus) │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  history_picker  │  Node 1
                    │     Agent        │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  session_picker  │  Node 2
                    │     Agent        │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  stage_picker    │  Node 3
                    │     Agent        │
                    └────────┬────────┘
                             │
                    ┌────────┴────────┐
                    │ Conditional Edge │
                    │ has_sufficient   │
                    │   _kb_info?      │
                    └────┬───────┬────┘
                    YES  │       │  NO
                         ▼       ▼
              ┌──────────────┐  ┌───────────────┐
              │  blueprint_  │  │  halt_         │
              │  generator   │  │  insufficient  │
              │  Agent       │  │  _info         │
              └──────┬───────┘  └───────────────┘
                     │
            ┌────────┴────────┐
            │ Conditional Edge │
            │ has_sufficient   │
            │   _kb_info?      │
            └────┬───────┬────┘
            YES  │       │  NO
                 ▼       ▼
      ┌──────────────┐  ┌───────────────┐
      │  protocol_   │  │  halt_         │
      │  generator   │  │  insufficient  │
      │  Agent       │  │  _info         │
      └──────┬───────┘  └───────────────┘
             │
    ┌────────┴────────┐
    │ Conditional Edge │
    │ has_sufficient   │
    │   _kb_info?      │
    └────┬───────┬────┘
    YES  │       │  NO
         ▼       ▼
  ┌──────────────┐  ┌───────────────┐
  │  uncertainty_ │  │  halt_         │
  │  scorer       │  │  insufficient  │
  │  Agent        │  │  _info         │
  └──────┬───────┘  └───────────────┘
         │
         ▼
  ┌──────────────┐
  │   __END__    │
  │  (return     │
  │   protocol)  │
  └──────────────┘
```

### 4.3 LangGraph Definition (Pseudocode)

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional, List

class ProtocolState(TypedDict):
    # Input
    therapist_id: int
    patient_id: int
    session_focus: str
    
    # Agent 1 output
    patient_history: dict
    
    # Agent 2 output
    recent_sessions: list
    
    # Agent 3 output
    selected_stage: str
    stage_rationale: str
    stage_kb_sufficient: bool
    
    # Agent 4 output
    session_blueprint: dict
    blueprint_kb_sufficient: bool
    
    # Agent 5 output
    protocol_text: str
    protocol_sections: list
    protocol_kb_sufficient: bool
    
    # Agent 6 output
    uncertainty_global: float
    uncertainty_per_claim: list
    annotated_protocol: str
    
    # Error state
    halt_reason: Optional[str]
    halted_at_agent: Optional[str]
    
    # Metadata
    kb_chunks_retrieved: dict          # {agent_name: [chunks]}
    generation_timestamp: str

# Build the graph
graph = StateGraph(ProtocolState)

graph.add_node("history_picker", history_picker_agent)
graph.add_node("session_picker", session_picker_agent)
graph.add_node("stage_picker", stage_picker_agent)
graph.add_node("blueprint_generator", blueprint_generator_agent)
graph.add_node("protocol_generator", protocol_generator_agent)
graph.add_node("uncertainty_scorer", uncertainty_scorer_agent)
graph.add_node("halt_insufficient_info", halt_node)

# Edges
graph.set_entry_point("history_picker")
graph.add_edge("history_picker", "session_picker")
graph.add_edge("session_picker", "stage_picker")

graph.add_conditional_edges(
    "stage_picker",
    lambda state: "blueprint_generator" if state["stage_kb_sufficient"] else "halt_insufficient_info"
)

graph.add_conditional_edges(
    "blueprint_generator",
    lambda state: "protocol_generator" if state["blueprint_kb_sufficient"] else "halt_insufficient_info"
)

graph.add_conditional_edges(
    "protocol_generator",
    lambda state: "uncertainty_scorer" if state["protocol_kb_sufficient"] else "halt_insufficient_info"
)

graph.add_edge("uncertainty_scorer", END)
graph.add_edge("halt_insufficient_info", END)

protocol_pipeline = graph.compile(checkpointer=PostgresSaver(conn))
```

---

## 5. Shared State Schema

The LangGraph `ProtocolState` is the single source of truth flowing through the pipeline. Each agent reads from and writes to this shared state. Below is the full field specification:

| Field | Type | Written By | Read By | Description |
|---|---|---|---|---|
| `therapist_id` | `int` | Router (input) | All agents | Scopes all DB/KB queries |
| `patient_id` | `int` | Router (input) | All agents | Identifies target patient |
| `session_focus` | `str` | Router (input) | Agents 3, 4, 5 | Therapist's free-text session guidance |
| `patient_history` | `dict` | Agent 1 | Agents 3, 4, 5 | `{initial_condition, weekly_progress, therapist_notes, current_week}` |
| `recent_sessions` | `list[dict]` | Agent 2 | Agents 3, 4, 5 | Last 2 session transcripts with metadata |
| `selected_stage` | `str` | Agent 3 | Agents 4, 5 | E.g. `"assessment"`, `"cbt_skill_building"`, `"exposure_therapy"` |
| `stage_rationale` | `str` | Agent 3 | Agent 6 | KB-grounded reasoning for stage selection |
| `stage_kb_sufficient` | `bool` | Agent 3 | Conditional edge | Whether KB had sufficient stage info |
| `session_blueprint` | `dict` | Agent 4 | Agent 5 | Structured session plan with phases/activities |
| `blueprint_kb_sufficient` | `bool` | Agent 4 | Conditional edge | Whether KB had sufficient blueprint info |
| `protocol_text` | `str` | Agent 5 | Agent 6 | Full 60-minute protocol text |
| `protocol_sections` | `list[dict]` | Agent 5 | Agent 6 | Structured sections: `[{time, activity, instructions, kb_source}]` |
| `protocol_kb_sufficient` | `bool` | Agent 5 | Conditional edge | Whether KB had sufficient protocol info |
| `uncertainty_global` | `float` | Agent 6 | Frontend | Protocol-level confidence (0.0–1.0) |
| `uncertainty_per_claim` | `list[dict]` | Agent 6 | Frontend | `[{claim, score, source, reasoning}]` |
| `annotated_protocol` | `str` | Agent 6 | Frontend | Protocol text with inline confidence markers |
| `halt_reason` | `str \| None` | Any halting agent | Frontend | Human-readable explanation of halt |
| `halted_at_agent` | `str \| None` | Any halting agent | Frontend | Name of agent that triggered halt |
| `kb_chunks_retrieved` | `dict` | Agents 3, 4, 5 | Audit/logging | Map of agent → retrieved chunks for provenance |
| `generation_timestamp` | `str` | Router | All | ISO-8601 timestamp of generation start |

---

## 6. Agent 1 — History Picker Agent

### 6.1 Purpose

Aggregates the complete longitudinal clinical history for the specified patient, producing a structured patient context object that downstream agents use to understand who the patient is, what trajectory they are on, and what the therapist has observed.

### 6.2 Data Sources

This agent performs **database reads only** — no LLM calls, no KB retrieval. It is a deterministic data-fetching node.

| Source | Table | Fields Extracted |
|---|---|---|
| Patient Demographics | `patients` | `name`, `conditions`, `conditions_description`, `address` |
| Initial Condition | `patient_progress` | `initial_condition` |
| Weekly Self-Reports | `patient_progress` | `weekly_progress` (JSON: `{week_1: "...", week_2: "...", ...}`) |
| Current Therapy Week | `patient_progress` | `current_week` |
| Therapist Notes | `therapist_notes` | `week_notes` (JSON: `{initial: "...", week_1: "...", ...}`) |
| AI Protocol Instructions | `therapist_notes` | `ai_protocol_instruction` (therapist's global AI guidance) |

### 6.3 Processing Logic

```python
async def history_picker_agent(state: ProtocolState) -> dict:
    """
    Pure data-fetching agent. No LLM calls.
    Queries: patients, patient_progress, therapist_notes
    Scoped by: therapist_id + patient_id
    """
    db = get_db_session()
    
    # 1. Fetch patient demographics
    patient = db.query(Patient).filter(
        Patient.id == state["patient_id"],
        Patient.therapist_id == state["therapist_id"]  # TENANT ISOLATION
    ).first()
    
    # 2. Fetch progress history
    progress = db.query(PatientProgress).filter(
        PatientProgress.patient_id == state["patient_id"]
    ).first()
    
    # 3. Fetch therapist notes
    notes = db.query(TherapistNote).filter(
        TherapistNote.patient_id == state["patient_id"],
        TherapistNote.therapist_id == state["therapist_id"]  # TENANT ISOLATION
    ).first()
    
    return {
        "patient_history": {
            "patient_name": patient.name,
            "conditions": patient.conditions,
            "conditions_description": patient.conditions_description,
            "initial_condition": progress.initial_condition if progress else None,
            "weekly_progress": progress.weekly_progress if progress else {},
            "current_week": progress.current_week if progress else 0,
            "therapist_week_notes": notes.week_notes if notes else {},
            "ai_protocol_instruction": notes.ai_protocol_instruction if notes else None,
        }
    }
```

### 6.4 Output Schema

```json
{
  "patient_history": {
    "patient_name": "John Doe",
    "conditions": "OCD, Social Anxiety",
    "conditions_description": "Obsessive checking behaviors, avoidance of social situations...",
    "initial_condition": "Patient presents with moderate OCD symptoms...",
    "weekly_progress": {
      "week_1": "Slight improvement in checking frequency...",
      "week_2": "Introduced ERP, patient reports moderate anxiety..."
    },
    "current_week": 3,
    "therapist_week_notes": {
      "initial": "Good rapport. Start with psychoeducation.",
      "week_1": "Responsive to CBT framework. Ready for ERP.",
      "week_2": "Hierarchy established. Begin in-vivo next."
    },
    "ai_protocol_instruction": "Focus on gradual exposure. Patient responds well to Socratic questioning."
  }
}
```

### 6.5 Failure Modes

| Condition | Behaviour |
|---|---|
| Patient not found | Returns empty `patient_history`; downstream agents detect and handle |
| No progress records yet | `initial_condition = null`, `weekly_progress = {}` — pipeline continues with limited context |
| No therapist notes | `therapist_week_notes = {}` — pipeline continues |

---

## 7. Agent 2 — Session Picker Agent

### 7.1 Purpose

Retrieves the **last two session transcripts** for the patient. These transcripts provide the most recent conversational context — what was discussed, what interventions were attempted, how the patient responded — which is critical for the Stage Picker to determine where to go next.

### 7.2 Data Source

| Source | Table | Query |
|---|---|---|
| Session Transcripts | `therapy_sessions` | `WHERE patient_id = :pid AND therapist_id = :tid ORDER BY week_number DESC LIMIT 2` |

### 7.3 Processing Logic

```python
async def session_picker_agent(state: ProtocolState) -> dict:
    """
    Pure data-fetching agent. No LLM calls.
    Queries: therapy_sessions (last 2 by week_number)
    Scoped by: therapist_id + patient_id
    """
    db = get_db_session()
    
    sessions = db.query(TherapySession).filter(
        TherapySession.patient_id == state["patient_id"],
        TherapySession.therapist_id == state["therapist_id"]
    ).order_by(
        TherapySession.week_number.desc()
    ).limit(2).all()
    
    recent_sessions = [
        {
            "week_number": s.week_number,
            "session_date": s.session_date.isoformat(),
            "transcript": s.transcript,
        }
        for s in reversed(sessions)  # chronological order (older first)
    ]
    
    return {"recent_sessions": recent_sessions}
```

### 7.4 Output Schema

```json
{
  "recent_sessions": [
    {
      "week_number": 2,
      "session_date": "2026-01-28T10:00:00",
      "transcript": "Therapist: Let's review the exposure hierarchy we built last week..."
    },
    {
      "week_number": 3,
      "session_date": "2026-02-04T10:00:00",
      "transcript": "Therapist: How did the in-vivo exposure go this week?..."
    }
  ]
}
```

### 7.5 Failure Modes

| Condition | Behaviour |
|---|---|
| No sessions exist | Returns `recent_sessions = []`; pipeline continues — Stage Picker treats this as initial session |
| Only 1 session exists | Returns single-element list; pipeline continues normally |

---

## 8. Agent 3 — Stage Picker Agent

### 8.1 Purpose

This is the first **LLM + RAG agent** in the pipeline. It synthesises the patient's history, recent sessions, and therapist guidance to determine the **current therapeutic stage** for the patient's next session. The stage selection is **grounded entirely in the therapist's knowledge base** — the agent performs vector similarity search against the KB to find stage-relevant material and uses only that material to make its determination.

### 8.2 Inputs Consumed

| Input | Source | Usage |
|---|---|---|
| `patient_history` | Agent 1 | Conditions, progression trajectory, therapist notes |
| `recent_sessions` | Agent 2 | Last 2 transcripts — what happened recently |
| `session_focus` | Therapist input | Therapist's explicit guidance for this session |
| **KB Retrieval** | pgvector | Therapy stage definitions, stage transition criteria, treatment models |

### 8.3 KB Retrieval Strategy

The agent constructs a **composite query** that combines patient context with stage-determination intent:

```python
def _build_stage_query(state: ProtocolState) -> str:
    """
    Construct a KB retrieval query optimized for stage identification.
    Combines condition + trajectory + therapist guidance into a single
    query that will retrieve stage-relevant KB material.
    """
    parts = [
        f"therapy stage selection for {state['patient_history']['conditions']}",
        f"patient in week {state['patient_history']['current_week']}",
    ]
    if state["session_focus"]:
        parts.append(f"therapist wants to focus on: {state['session_focus']}")
    if state["patient_history"].get("ai_protocol_instruction"):
        parts.append(f"therapist AI instruction: {state['patient_history']['ai_protocol_instruction']}")
    
    # Include recent session themes for better retrieval
    for session in state.get("recent_sessions", []):
        parts.append(f"recent session theme: {session['transcript'][:200]}")
    
    return ". ".join(parts)
```

**Retrieval parameters:**
- `top_k = 8` (retrieve 8 most similar chunks)
- Similarity search via pgvector cosine distance
- Scoped to `therapist_id` (multi-tenant isolation)

### 8.4 LLM Prompt Architecture

```
SYSTEM:
You are a therapy stage selection specialist. Your task is to determine the
appropriate therapeutic stage for the patient's next session.

You must ONLY select stages that are described in the provided knowledge base
excerpts. Do NOT invent stages or use knowledge outside the provided sources.

If the knowledge base does not contain sufficient information about therapy
stages, stage progression criteria, or treatment models for the patient's
condition(s), you MUST respond with:
  {"kb_sufficient": false, "reason": "<specific explanation of what is missing>"}

KNOWLEDGE BASE EXCERPTS:
{retrieved_chunks}

PATIENT HISTORY:
- Name: {patient_name}
- Conditions: {conditions}
- Detailed Description: {conditions_description}
- Current Week: {current_week}
- Initial Condition: {initial_condition}
- Weekly Progress: {weekly_progress}
- Therapist Notes: {therapist_week_notes}
- Therapist AI Instruction: {ai_protocol_instruction}

RECENT SESSION TRANSCRIPTS:
{recent_sessions}

THERAPIST SESSION FOCUS:
{session_focus}

INSTRUCTIONS:
1. Analyse the patient's trajectory across weeks
2. Review recent session transcripts for treatment progress signals
3. Consult the knowledge base for stage definitions and transition criteria
4. Consider the therapist's explicit session focus and AI protocol instruction
5. Select the most appropriate stage for the NEXT session

Respond in JSON:
{
  "kb_sufficient": true,
  "selected_stage": "<stage name as described in KB>",
  "stage_rationale": "<KB-grounded reasoning for this stage selection>",
  "kb_sources_used": ["<chunk summaries for citation>"],
  "alternative_stages_considered": ["<other stages considered and why rejected>"]
}
```

### 8.5 Sufficiency Check Logic

```python
async def stage_picker_agent(state: ProtocolState) -> dict:
    # 1. Build query & retrieve from KB
    query = _build_stage_query(state)
    chunks = rag_service.retrieve_chunks(db, state["therapist_id"], query, top_k=8)
    
    # 2. Pre-LLM sufficiency heuristic
    if len(chunks) == 0 or all(c["similarity_score"] < 0.3 for c in chunks):
        return {
            "selected_stage": None,
            "stage_rationale": None,
            "stage_kb_sufficient": False,
            "halt_reason": "No relevant therapy stage information found in the knowledge base. "
                          "Please upload treatment model documents that describe therapy stages "
                          "and stage transition criteria.",
            "halted_at_agent": "stage_picker",
            "kb_chunks_retrieved": {**state.get("kb_chunks_retrieved", {}), "stage_picker": []},
        }
    
    # 3. LLM call with retrieved context
    llm_response = call_llm(stage_picker_prompt, chunks, state)
    parsed = json.loads(llm_response)
    
    # 4. LLM-level sufficiency check
    if not parsed["kb_sufficient"]:
        return {
            "selected_stage": None,
            "stage_rationale": None,
            "stage_kb_sufficient": False,
            "halt_reason": f"Stage Picker: {parsed['reason']}",
            "halted_at_agent": "stage_picker",
            "kb_chunks_retrieved": {**state.get("kb_chunks_retrieved", {}), "stage_picker": chunks},
        }
    
    return {
        "selected_stage": parsed["selected_stage"],
        "stage_rationale": parsed["stage_rationale"],
        "stage_kb_sufficient": True,
        "kb_chunks_retrieved": {**state.get("kb_chunks_retrieved", {}), "stage_picker": chunks},
    }
```

### 8.6 Example Output — Success

```json
{
  "selected_stage": "exposure_response_prevention_phase_2",
  "stage_rationale": "Per the uploaded CBT-OCD treatment manual (Chapter 7), after establishing a fear hierarchy (completed in weeks 1-2) and conducting initial in-session exposures (week 3), the protocol recommends transitioning to Phase 2: graduated in-vivo exposures with response prevention assignments. The patient's weekly progress shows readiness, and the therapist's notes confirm hierarchy completion.",
  "stage_kb_sufficient": true,
  "kb_sources_used": [
    "CBT-OCD Manual Ch.7: 'Phase 2 begins when the patient has demonstrated tolerance to at least 3 items on the lower half of the SUDs hierarchy...'",
    "Treatment Planning Guide: 'Transition criteria: patient reports <50 SUDs on previously triggering stimuli during in-session exposure...'"
  ]
}
```

### 8.7 Example Output — Insufficient KB

```json
{
  "selected_stage": null,
  "stage_rationale": null,
  "stage_kb_sufficient": false,
  "halt_reason": "Stage Picker: The knowledge base does not contain treatment stage definitions or stage transition criteria for OCD. Found general OCD psychoeducation material but no structured treatment model with defined phases. Please upload a treatment manual or protocol that defines therapy stages for OCD.",
  "halted_at_agent": "stage_picker"
}
```

---

## 9. Agent 4 — Blueprint Generator Agent

### 9.1 Purpose

Given the selected therapeutic stage, this agent generates a **structured session blueprint** — a high-level session plan that outlines the phases, activities, and objectives for the 60-minute session. The blueprint acts as the skeleton that the Protocol Generator will later flesh out into a detailed minute-by-minute protocol.

The blueprint is **stage-specific and KB-grounded**. For example:
- An **assessment stage** blueprint might include intake interview structure, standardised assessments, and rapport-building activities
- A **CBT skill-building stage** blueprint might include psychoeducation, thought record exercises, and behavioural experiment planning
- An **exposure therapy stage** blueprint might include SUDS baseline, graduated exposure exercises, and post-exposure processing

### 9.2 Inputs Consumed

| Input | Source | Usage |
|---|---|---|
| `selected_stage` | Agent 3 | The therapy stage to build a blueprint for |
| `stage_rationale` | Agent 3 | Why this stage was selected (context for blueprint alignment) |
| `patient_history` | Agent 1 | Personalise blueprint to patient's condition/trajectory |
| `recent_sessions` | Agent 2 | Continuity — avoid repeating what was already done |
| `session_focus` | Therapist input | Therapist's overriding preferences for this session |
| **KB Retrieval** | pgvector | Session structures, activity templates, technique descriptions for the selected stage |

### 9.3 KB Retrieval Strategy

```python
def _build_blueprint_query(state: ProtocolState) -> str:
    """
    Query optimized for retrieving session structure and activity
    descriptions for the selected therapeutic stage.
    """
    parts = [
        f"session structure for {state['selected_stage']}",
        f"therapy session blueprint activities for {state['patient_history']['conditions']}",
        f"session plan components for stage: {state['selected_stage']}",
    ]
    if state["session_focus"]:
        parts.append(f"session focus: {state['session_focus']}")
    return ". ".join(parts)
```

**Retrieval parameters:**
- `top_k = 10` (broader retrieval — blueprint needs activity/technique details)
- Scoped to `therapist_id`

### 9.4 LLM Prompt Architecture

```
SYSTEM:
You are a therapy session blueprint designer. Given a specific therapeutic stage
and patient context, you design structured session blueprints that outline the
phases, activities, approximate time allocations, and objectives for a 60-minute
therapy session.

You must ONLY use activities, techniques, and session structures described in the
provided knowledge base. Do not invent techniques or reference methods not present
in the KB.

If the knowledge base does not contain sufficient information to construct a
meaningful session blueprint for the given stage, you MUST respond with:
  {"kb_sufficient": false, "reason": "<what is missing>"}

KNOWLEDGE BASE EXCERPTS:
{retrieved_chunks}

SELECTED STAGE: {selected_stage}
STAGE RATIONALE: {stage_rationale}

PATIENT CONTEXT:
{patient_history_summary}

RECENT SESSIONS:
{recent_sessions_summary}

THERAPIST SESSION FOCUS:
{session_focus}

INSTRUCTIONS:
1. Design a 60-minute session blueprint appropriate for the "{selected_stage}" stage
2. Each phase must reference specific KB-described techniques/activities
3. Ensure logical flow: opening → core work → processing → closing
4. Adapt to the patient's specific conditions and progress trajectory
5. Honour the therapist's session focus and AI protocol instructions

Respond in JSON:
{
  "kb_sufficient": true,
  "blueprint": {
    "session_title": "<descriptive title>",
    "session_objective": "<primary objective for this session>",
    "phases": [
      {
        "phase_name": "<e.g., Opening & Check-in>",
        "time_minutes": <int>,
        "activities": ["<activity 1>", "<activity 2>"],
        "objective": "<what this phase achieves>",
        "kb_technique_reference": "<which KB technique/method>"
      }
    ],
    "materials_needed": ["<any worksheets, scales, etc. from KB>"],
    "homework_preview": "<potential homework assignment based on KB>"
  }
}
```

### 9.5 Sufficiency Check

Identical pattern to Agent 3:
1. **Pre-LLM heuristic**: If `len(chunks) == 0` or max similarity < 0.3 → halt immediately
2. **LLM-level check**: If LLM sets `kb_sufficient = false` → halt with explanation

### 9.6 Example Output — Success

```json
{
  "kb_sufficient": true,
  "blueprint": {
    "session_title": "ERP Phase 2 — Graduated In-Vivo Exposure Session",
    "session_objective": "Conduct first in-session in-vivo exposure to Item #4 on the fear hierarchy (touching unwashed surfaces) with response prevention",
    "phases": [
      {
        "phase_name": "Opening & Check-in",
        "time_minutes": 10,
        "activities": [
          "Weekly SUDS rating review",
          "Homework review: between-session exposure log",
          "Brief agenda-setting"
        ],
        "objective": "Assess between-session progress, set collaborative agenda",
        "kb_technique_reference": "CBT-OCD Manual Ch.3: Session Opening Protocol"
      },
      {
        "phase_name": "Psychoeducation Refresher",
        "time_minutes": 5,
        "activities": [
          "Review habituation curve concept",
          "Reinforcement of response prevention rationale"
        ],
        "objective": "Strengthen treatment motivation before exposure",
        "kb_technique_reference": "CBT-OCD Manual Ch.5: Psychoeducation for ERP"
      },
      {
        "phase_name": "In-Vivo Exposure",
        "time_minutes": 25,
        "activities": [
          "SUDS baseline measurement",
          "Guided exposure to hierarchy item #4",
          "SUDS monitoring at 5-minute intervals",
          "Therapist-guided response prevention coaching",
          "Continued exposure until SUDS decrease of ≥50%"
        ],
        "objective": "Achieve within-session habituation to target stimulus",
        "kb_technique_reference": "CBT-OCD Manual Ch.7: In-Vivo Exposure Protocol"
      },
      {
        "phase_name": "Processing & Cognitive Restructuring",
        "time_minutes": 12,
        "activities": [
          "Post-exposure SUDS debrief",
          "Identify cognitive distortions activated during exposure",
          "Guided Socratic questioning",
          "Updated belief rating"
        ],
        "objective": "Consolidate learning, modify dysfunctional beliefs",
        "kb_technique_reference": "CBT-OCD Manual Ch.8: Post-Exposure Processing"
      },
      {
        "phase_name": "Homework Assignment & Closing",
        "time_minutes": 8,
        "activities": [
          "Assign between-session exposure (hierarchy item #4, 3x/week)",
          "Review response prevention instructions",
          "Schedule next session",
          "Positive reinforcement"
        ],
        "objective": "Ensure generalization and between-session practice",
        "kb_technique_reference": "CBT-OCD Manual Ch.9: Homework Protocol"
      }
    ],
    "materials_needed": [
      "SUDS tracking worksheet",
      "Fear hierarchy card",
      "Exposure log template"
    ],
    "homework_preview": "Complete 3 self-guided exposures to hierarchy item #4 with full response prevention. Log SUDS every 5 minutes using exposure log template."
  }
}
```

---

## 10. Agent 5 — Protocol Generator Agent

### 10.1 Purpose

This is the **core generative agent** in the pipeline. It takes the session blueprint and expands it into a **detailed, minute-by-minute 60-minute therapy session protocol** — the exact script a therapist would follow during the session. Every instruction, dialogue prompt, technique cue, and timing note is grounded in the therapist's knowledge base.

### 10.2 Inputs Consumed

| Input | Source | Usage |
|---|---|---|
| `session_blueprint` | Agent 4 | Structural skeleton to expand |
| `selected_stage` | Agent 3 | Stage context for technique selection |
| `patient_history` | Agent 1 | Personalisation of dialogue and examples |
| `recent_sessions` | Agent 2 | Continuity references |
| `session_focus` | Therapist input | Priority areas |
| **KB Retrieval** | pgvector | Detailed technique instructions, scripts, clinical guidelines |

### 10.3 KB Retrieval Strategy

The Protocol Generator performs the **most intensive KB retrieval** in the pipeline. It queries multiple times — once per blueprint phase — to retrieve technique-specific instructions:

```python
def _build_protocol_queries(state: ProtocolState) -> list[str]:
    """
    Generate one KB query per blueprint phase for targeted retrieval.
    """
    queries = []
    for phase in state["session_blueprint"]["phases"]:
        query = (
            f"detailed instructions for {phase['kb_technique_reference']}. "
            f"How to conduct {', '.join(phase['activities'])} "
            f"for {state['patient_history']['conditions']}"
        )
        queries.append(query)
    return queries
```

**Per-phase retrieval**: `top_k = 5` per query, deduplicated across phases  
**Total chunks**: Up to 25 unique chunks for protocol generation

### 10.4 LLM Prompt Architecture

```
SYSTEM:
You are a clinical therapy protocol writer. You expand session blueprints into
detailed, actionable 60-minute therapy session protocols. Your output is used
directly by therapists during sessions.

CRITICAL RULES:
1. EVERY instruction must be grounded in the knowledge base. Cite sources inline.
2. Include specific dialogue prompts the therapist can use verbatim
3. Include SUDS/rating scale prompts where appropriate
4. Include timing cues (e.g., "[Minute 10-15]")
5. Include therapist action notes (e.g., "Observe patient's non-verbal cues")
6. If the KB does not contain enough detail for ANY section, return kb_sufficient=false

KNOWLEDGE BASE EXCERPTS (organized by blueprint phase):
{per_phase_chunks}

SESSION BLUEPRINT:
{session_blueprint_json}

PATIENT CONTEXT:
{patient_context_summary}

Generate a detailed 60-minute protocol in JSON:
{
  "kb_sufficient": true,
  "protocol": {
    "title": "<session title>",
    "total_duration_minutes": 60,
    "sections": [
      {
        "time_range": "0:00 – 10:00",
        "phase": "<phase name>",
        "detailed_instructions": "<step-by-step therapist instructions>",
        "dialogue_prompts": ["<exact phrases therapist can say>"],
        "therapist_notes": "<clinical observations to make>",
        "kb_sources": ["<source references>"]
      }
    ],
    "session_summary_template": "<post-session note template>",
    "risk_flags": ["<things to watch for that may require protocol deviation>"]
  }
}
```

### 10.5 Output Structure

The protocol contains:

1. **Sections** (typically 4–6): Each maps to a blueprint phase with expanded detail
2. **Time ranges**: Minute-by-minute or block-level timing
3. **Detailed instructions**: Step-by-step therapist actions
4. **Dialogue prompts**: Ready-to-use therapeutic language
5. **Therapist notes**: Clinical observation cues, contraindication warnings
6. **KB sources**: Inline citations for every clinical claim
7. **Summary template**: Post-session documentation scaffold
8. **Risk flags**: Conditions that warrant clinical judgement override

### 10.6 Sufficiency Check

Same two-tier pattern:
1. **Pre-LLM**: Check minimum chunk retrieval across phases
2. **LLM-level**: `kb_sufficient` field in response

---

## 11. Agent 6 — Uncertainty Scorer Agent

### 11.1 Purpose

The capstone agent in the pipeline. It evaluates the generated protocol and produces **quantified epistemic uncertainty scores** at two levels of granularity:

1. **Global Protocol Score** (0.0–1.0): Overall confidence in the protocol's KB-groundedness
2. **Per-Claim Scores**: Individual confidence scores attached to critical clinical statements within the protocol

This agent is designed as a **research contribution** target for Q1 journal publication. The initial implementation (v1) uses **prompt engineering** only; future versions (v2+) will incorporate calibrated confidence estimation methods (e.g., verbalized probability calibration, multi-sample consistency scoring, semantic entailment verification).

### 11.2 Research Motivation

In clinical AI systems, uncalibrated confidence is dangerous. A protocol generator that produces plausible-sounding but unsupported claims could lead to harmful clinical decisions. The Uncertainty Scorer addresses this by:

- Making the system's epistemic state **transparent** to the therapist
- Flagging claims that are weakly supported or extrapolated beyond KB material
- Providing a decision-support signal: high-uncertainty protocols should be reviewed more carefully

### 11.3 v1 Architecture (Prompt Engineering)

```
SYSTEM:
You are a clinical AI uncertainty assessor. You evaluate therapy session protocols
for epistemic uncertainty — how well each claim is supported by the knowledge base.

SCORING CRITERIA:
- 0.9–1.0: Claim directly quoted or closely paraphrased from KB
- 0.7–0.89: Claim clearly supported by KB with minor inference
- 0.5–0.69: Claim partially supported; some extrapolation beyond KB
- 0.3–0.49: Claim weakly supported; significant inference or generalization
- 0.0–0.29: Claim not supported by KB; appears to be generated from LLM pretraining

WHAT TO SCORE:
1. Clinical technique instructions
2. Timing and dosage recommendations (e.g., "expose for 25 minutes")
3. Dialogue prompts with clinical significance
4. Homework assignments
5. Stage transition recommendations
6. Risk assessments

DO NOT SCORE:
- Generic session management (e.g., "greet the patient")
- Obvious administrative tasks

INPUT:
Protocol: {protocol_text}
KB Chunks Used Across Pipeline: {all_kb_chunks}
Stage Rationale: {stage_rationale}
Blueprint: {session_blueprint}

OUTPUT JSON:
{
  "global_uncertainty_score": <float 0.0-1.0>,
  "global_rationale": "<why this overall score>",
  "per_claim_assessments": [
    {
      "claim_text": "<exact text from protocol>",
      "uncertainty_score": <float 0.0-1.0>,
      "supporting_kb_evidence": "<relevant KB text or 'none found'>",
      "reasoning": "<why this score>"
    }
  ],
  "high_risk_flags": [
    "<claims with score < 0.5 that have clinical significance>"
  ],
  "annotated_protocol": "<full protocol text with [Confidence: X.XX] inline markers>"
}
```

### 11.4 Scoring Dimensions (v1 — Prompt-Based)

| Dimension | Weight | Description |
|---|---|---|
| **Source Traceability** | 0.35 | Can the claim be traced to a specific KB chunk? |
| **Semantic Fidelity** | 0.25 | How closely does the claim match the KB language? |
| **Inferential Distance** | 0.20 | How many logical steps from KB to claim? |
| **Clinical Specificity** | 0.10 | Is the claim specific (dosage, timing) or generic? |
| **Consensus Alignment** | 0.10 | Does the claim align with multiple KB sources? |

### 11.5 Future Research Directions (v2+ — Journal Publication Track)

| Method | Description | Target |
|---|---|---|
| **Multi-Sample Consistency** | Generate N protocol variants, measure claim-level agreement | Calibration |
| **Semantic Entailment Verification** | NLI model (e.g., DeBERTa-v3) to verify claim↔KB entailment | Grounding |
| **Token-Level Log-Probability** | Extract logprobs from generation, aggregate per-claim | Fluency vs. confidence disentanglement |
| **Retrieval Confidence Fusion** | Combine similarity scores of supporting chunks with LLM confidence | Hybrid scoring |
| **Human Calibration Study** | Correlate system scores with expert therapist assessments | Validation |

### 11.6 Output Example

```json
{
  "global_uncertainty_score": 0.78,
  "global_rationale": "Protocol is well-grounded in the uploaded CBT-OCD manual with strong source traceability for exposure and response prevention techniques. Moderate uncertainty in timing recommendations (25-min exposure) as the KB provides range guidance rather than exact prescriptions. Homework design is closely aligned with KB Chapter 9.",
  "per_claim_assessments": [
    {
      "claim_text": "Conduct guided exposure to hierarchy item #4 for approximately 25 minutes",
      "uncertainty_score": 0.65,
      "supporting_kb_evidence": "CBT-OCD Manual Ch.7: 'Exposure duration should be sufficient to observe a minimum 50% reduction in SUDS, typically 20-45 minutes'",
      "reasoning": "KB provides a range (20-45 min), not exactly 25 min. The specific claim is a reasonable inference but not directly prescribed."
    },
    {
      "claim_text": "Use Socratic questioning: 'What evidence do you have that touching this surface will cause harm?'",
      "uncertainty_score": 0.91,
      "supporting_kb_evidence": "CBT-OCD Manual Ch.8: 'Socratic questioning examples: What is the evidence for this belief? What would you tell a friend?...'",
      "reasoning": "Directly supported by KB with near-verbatim match to example prompts."
    }
  ],
  "high_risk_flags": [
    "Timing recommendation of 25 min is inferred (score 0.65) — therapist should use clinical judgement"
  ]
}
```

---

## 12. Knowledge Base Integration Layer

### 12.1 Existing RAG Infrastructure

The system leverages Nirbaan's existing RAG pipeline (already implemented):

| Component | Technology | Status |
|---|---|---|
| Document Storage | Cloudflare R2 (S3-compatible) | ✅ Implemented |
| Document Ingestion | Celery + Redis async pipeline | ✅ Implemented |
| Text Chunking | LangChain RecursiveCharacterTextSplitter (800 tokens, 100 overlap) | ✅ Implemented |
| Embedding Model | OpenAI `text-embedding-3-small` (1536 dims) | ✅ Implemented |
| Vector Store | PostgreSQL + pgvector (IVFFlat index) | ✅ Implemented |
| Similarity Search | Cosine distance (`<=>` operator) | ✅ Implemented |
| Multi-Tenant Scope | `therapist_id` filter on all queries | ✅ Implemented |

### 12.2 Protocol Generator KB Access Pattern

The multi-agent pipeline accesses the KB through the existing `RAGService`:

```python
class RAGService:
    def retrieve_chunks(
        self,
        db: Session,
        therapist_id: int,
        query: str,
        top_k: int = 6
    ) -> List[Dict[str, Any]]:
        """
        Vector similarity search scoped by therapist_id.
        Returns: [{chunk_text, resource_title, resource_id, similarity_score}]
        """
```

### 12.3 Agent-Specific Retrieval Parameters

| Agent | top_k | Minimum Similarity Threshold | Query Strategy |
|---|---|---|---|
| Stage Picker | 8 | 0.30 | Single composite query (condition + week + focus) |
| Blueprint Generator | 10 | 0.30 | Single query (stage + condition + session structure) |
| Protocol Generator | 5 × N phases | 0.25 | Per-phase queries for technique-specific detail |
| Uncertainty Scorer | 0 (no new retrieval) | N/A | Reuses all chunks retrieved by agents 3–5 |

### 12.4 KB Sufficiency Decision Logic

Each KB-consuming agent applies a **two-tier sufficiency test**:

```
Tier 1 (Deterministic — Pre-LLM):
  IF retrieved_chunks == 0:
    → HALT: "No KB material found"
  IF max(similarity_scores) < threshold:
    → HALT: "No sufficiently relevant KB material"

Tier 2 (LLM-Assessed — Post-Retrieval):
  LLM evaluates whether retrieved chunks contain enough information
  to complete its specific task.
  IF LLM determines insufficient:
    → HALT: "{agent_name}: {specific explanation of what's missing}"
```

This two-tier approach prevents both:
- Wasting LLM calls when KB is clearly empty (Tier 1)
- Generating poorly-grounded content when KB is tangentially relevant but insufficient (Tier 2)

---

## 13. Memory Architecture — Per-Patient Per-Therapist Isolation

### 13.1 Multi-Tenant Isolation Model

Every piece of data in the system is scoped by a `(therapist_id, patient_id)` pair:

```
Therapist A ─┬── Patient 1 ─── [History, Sessions, Protocols, KB Context]
             ├── Patient 2 ─── [History, Sessions, Protocols, KB Context]
             └── Patient 3 ─── [History, Sessions, Protocols, KB Context]

Therapist B ─┬── Patient 4 ─── [History, Sessions, Protocols, KB Context]
             └── Patient 5 ─── [History, Sessions, Protocols, KB Context]
```

- Therapist A **cannot** see Therapist B's patients, protocols, or KB
- Patient 1's data is **not** mixed with Patient 2's data during generation
- Generated protocols are stored **per-patient** for session-over-session continuity

### 13.2 Protocol Memory Store

Each generated protocol is persisted to enable:
- **Protocol history browsing** — therapist can review past generated protocols
- **Cross-session continuity** — future pipeline runs can reference past protocols
- **Audit trail** — full provenance of what was generated and from which KB sources

**New table: `generated_protocols`**

```python
class GeneratedProtocol(Base):
    __tablename__ = "generated_protocols"

    id: Mapped[int] = mapped_column(Integer, primary_key=True) 
    therapist_id: Mapped[int] = mapped_column(Integer, ForeignKey("therapists.id"), nullable=False)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id"), nullable=False)
    
    # Input context
    session_focus: Mapped[str | None] = mapped_column(Text, nullable=True)
    therapy_week: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Pipeline outputs
    selected_stage: Mapped[str] = mapped_column(String(200), nullable=False)
    stage_rationale: Mapped[str] = mapped_column(Text, nullable=False)
    session_blueprint: Mapped[dict] = mapped_column(JSONB, nullable=False)
    protocol_text: Mapped[str] = mapped_column(Text, nullable=False)
    protocol_sections: Mapped[list] = mapped_column(JSONB, nullable=False)
    
    # Uncertainty annotations 
    uncertainty_global: Mapped[float] = mapped_column(Float, nullable=False)
    uncertainty_per_claim: Mapped[list] = mapped_column(JSONB, nullable=False)
    annotated_protocol: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Provenance
    kb_chunks_used: Mapped[dict] = mapped_column(JSONB, nullable=False)  # agent → [chunks]
    
    # Pipeline metadata
    pipeline_state_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=True)  # full state for audit
    halted: Mapped[bool] = mapped_column(Boolean, default=False)
    halt_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    halted_at_agent: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

### 13.3 LangGraph Checkpointing

LangGraph's built-in checkpointer is configured to persist per `(therapist_id, patient_id)` thread:

```python
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver(conn_string=DATABASE_URL)

# Each invocation uses a unique thread_id
thread_id = f"therapist_{therapist_id}_patient_{patient_id}"

result = protocol_pipeline.invoke(
    initial_state,
    config={"configurable": {"thread_id": thread_id}}
)
```

This enables:
- **State recovery**: If the pipeline fails mid-execution, it can resume from the last checkpoint
- **History access**: Past pipeline states are queryable for debugging and audit
- **Patient continuity**: The checkpoint store maintains thread-level context over time

---

## 14. Error Propagation & Graceful Degradation

### 14.1 Error Categories

| Category | Trigger | Behaviour |
|---|---|---|
| `INSUFFICIENT_KB_INFO` | Agent 3, 4, or 5 cannot find adequate KB material | Pipeline halts; returns structured error with agent name and missing-info explanation |
| `PATIENT_NOT_FOUND` | Agent 1 finds no patient matching `(therapist_id, patient_id)` | Pipeline halts immediately |
| `LLM_ERROR` | OpenAI API failure, timeout, malformed response | Retry with exponential backoff (3 attempts); then halt with error |
| `DB_ERROR` | PostgreSQL connection failure | Retry once; then halt with error |
| `EMBEDDING_ERROR` | OpenAI embedding API failure | Retry once; then halt with error |

### 14.2 Error Response Schema

All errors return a consistent structure:

```json
{
  "success": false,
  "error_type": "INSUFFICIENT_KB_INFO",
  "halted_at_agent": "stage_picker",
  "halt_reason": "The knowledge base does not contain treatment stage definitions for the patient's conditions (OCD, Social Anxiety). Please upload relevant treatment manuals.",
  "partial_state": {
    "patient_history": { ... },
    "recent_sessions": [ ... ]
  },
  "suggestion": "Upload a CBT-OCD treatment manual or structured treatment protocol document to the Resources section."
}
```

### 14.3 Partial Result Delivery

When the pipeline halts at Agent 4 or 5, the system still returns whatever was successfully computed:
- If halted at Blueprint Generator → returns stage selection + rationale
- If halted at Protocol Generator → returns stage + blueprint (usable as a high-level plan)

The frontend renders partial results with a clear indicator of where the pipeline stopped and why.

---

## 15. Backend API Design

### 15.1 Endpoints

```
POST   /ai/generate-protocol         Generate a new treatment protocol
GET    /ai/protocols/{patient_id}     List all protocols for a patient
GET    /ai/protocol/{protocol_id}     Get a specific protocol with full detail
DELETE /ai/protocol/{protocol_id}     Delete a protocol
GET    /ai/patients                   List patients for AI workspace (with protocol counts)
```

### 15.2 Request/Response Schemas

**POST /ai/generate-protocol**

Request:
```json
{
  "patient_id": 5,
  "session_focus": "Focus on exposure hierarchy item #4. Patient reported anxiety about touching unwashed surfaces between sessions."
}
```

Success Response:
```json
{
  "success": true,
  "protocol": {
    "protocol_id": 42,
    "patient_id": 5,
    "therapy_week": 3,
    "selected_stage": "exposure_response_prevention_phase_2",
    "stage_rationale": "...",
    "session_blueprint": { ... },
    "protocol_text": "...",
    "protocol_sections": [ ... ],
    "uncertainty": {
      "global_score": 0.78,
      "global_rationale": "...",
      "per_claim_scores": [ ... ],
      "high_risk_flags": [ ... ]
    },
    "annotated_protocol": "...",
    "sources_used": [ ... ],
    "created_at": "2026-02-11T14:30:00Z"
  }
}
```

Failure Response (Insufficient KB):
```json
{
  "success": false,
  "error_type": "INSUFFICIENT_KB_INFO",
  "halted_at_agent": "blueprint_generator",
  "halt_reason": "The knowledge base contains stage definitions but lacks specific session structure templates for the 'exposure_response_prevention_phase_2' stage. Please upload session planning resources.",
  "partial_state": {
    "selected_stage": "exposure_response_prevention_phase_2",
    "stage_rationale": "..."
  },
  "suggestion": "Upload ERP session planning guides or CBT session structure templates."
}
```

### 15.3 Authentication & Authorization

All `/ai/*` endpoints require:
1. Valid JWT token (existing auth middleware)
2. `role == "therapist"` (only therapists can generate protocols)
3. Patient must belong to the authenticated therapist (`patient.therapist_id == current_user.id`)

---

## 16. Database Schema Extensions

### 16.1 New Tables

```sql
-- Generated protocols with full provenance
CREATE TABLE generated_protocols (
    id SERIAL PRIMARY KEY,
    therapist_id INTEGER NOT NULL REFERENCES therapists(id),
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    
    -- Input context
    session_focus TEXT,
    therapy_week INTEGER NOT NULL,
    
    -- Pipeline outputs (stored as JSON for flexibility)
    selected_stage VARCHAR(200) NOT NULL,
    stage_rationale TEXT NOT NULL,
    session_blueprint JSONB NOT NULL,
    protocol_text TEXT NOT NULL,
    protocol_sections JSONB NOT NULL,
    
    -- Uncertainty annotations
    uncertainty_global FLOAT NOT NULL,
    uncertainty_per_claim JSONB NOT NULL,
    annotated_protocol TEXT NOT NULL,
    
    -- Provenance
    kb_chunks_used JSONB NOT NULL,
    pipeline_state_snapshot JSONB,
    
    -- Status
    halted BOOLEAN DEFAULT FALSE,
    halt_reason TEXT,
    halted_at_agent VARCHAR(100),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Indexes
    CONSTRAINT fk_therapist FOREIGN KEY (therapist_id) REFERENCES therapists(id),
    CONSTRAINT fk_patient FOREIGN KEY (patient_id) REFERENCES patients(id)
);

CREATE INDEX idx_protocols_therapist_patient ON generated_protocols(therapist_id, patient_id);
CREATE INDEX idx_protocols_patient_week ON generated_protocols(patient_id, therapy_week);

-- LangGraph checkpoint storage (managed by LangGraph PostgresSaver)
-- Tables are auto-created by LangGraph:
--   checkpoints, checkpoint_writes, checkpoint_migrations
```

### 16.2 Existing Tables Leveraged

| Table | Used By | Purpose |
|---|---|---|
| `patients` | Agent 1 | Demographics, conditions |
| `patient_progress` | Agent 1 | Initial condition, weekly self-reports |
| `therapist_notes` | Agent 1 | Weekly therapist observations, AI instructions |
| `therapy_sessions` | Agent 2 | Session transcripts (last 2) |
| `resources` | KB Layer | Resource metadata |
| `resource_chunks` | KB Layer | Embedded text chunks for similarity search |

---

## 17. Data Flow Diagram — End-to-End

```
THERAPIST (Browser)
    │
    │  POST /ai/generate-protocol
    │  { patient_id: 5, session_focus: "..." }
    │
    ▼
FASTAPI ROUTER (/ai/router.py)
    │
    │  1. Authenticate (JWT)
    │  2. Validate patient ownership
    │  3. Build initial state
    │
    ▼
LANGGRAPH PIPELINE (protocol_pipeline.invoke)
    │
    ├─── [Node 1] HISTORY PICKER ──── PostgreSQL ──── patients, patient_progress, therapist_notes
    │         │
    │         ▼ state.patient_history = {...}
    │
    ├─── [Node 2] SESSION PICKER ──── PostgreSQL ──── therapy_sessions (LIMIT 2)
    │         │
    │         ▼ state.recent_sessions = [...]
    │
    ├─── [Node 3] STAGE PICKER ────── pgvector ────── resource_chunks (top_k=8)
    │         │                            │
    │         │                     OpenAI Embeddings
    │         │                            │
    │         │                     OpenAI GPT-4o (temperature=0)
    │         │
    │         ├── IF kb_sufficient=false → HALT NODE → return error
    │         │
    │         ▼ state.selected_stage = "erp_phase_2"
    │
    ├─── [Node 4] BLUEPRINT GEN ────── pgvector ────── resource_chunks (top_k=10)
    │         │                            │
    │         │                     OpenAI GPT-4o (temperature=0)
    │         │
    │         ├── IF kb_sufficient=false → HALT NODE → return error
    │         │
    │         ▼ state.session_blueprint = {...}
    │
    ├─── [Node 5] PROTOCOL GEN ─────── pgvector ────── resource_chunks (5 × N phases)
    │         │                            │
    │         │                     OpenAI GPT-4o (temperature=0)
    │         │
    │         ├── IF kb_sufficient=false → HALT NODE → return error
    │         │
    │         ▼ state.protocol_text = "..."
    │
    ├─── [Node 6] UNCERTAINTY SCORER ── (reuses chunks from agents 3-5)
    │         │                            │
    │         │                     OpenAI GPT-4o (temperature=0)
    │         │
    │         ▼ state.uncertainty_global = 0.78
    │           state.uncertainty_per_claim = [...]
    │           state.annotated_protocol = "..."
    │
    ▼
FASTAPI ROUTER
    │
    │  1. Persist to generated_protocols table
    │  2. Return JSON response
    │
    ▼
THERAPIST (Browser)
    │
    │  Renders: 60-minute protocol with inline uncertainty badges
    │  Shows:   Global confidence score header
    │  Displays: Source citations from KB
    │  Highlights: High-risk flags for manual review
```

---

## 18. Security & Access Control

| Layer | Mechanism | Implementation |
|---|---|---|
| **API Authentication** | JWT Bearer Token | Existing `get_current_user()` dependency |
| **Role Authorization** | `role == "therapist"` check | Endpoint-level guard |
| **Patient Ownership** | `patient.therapist_id == current_user.id` | Query-level filter |
| **KB Isolation** | `resource_chunks.therapist_id == current_user.id` | All pgvector queries scoped |
| **Protocol Isolation** | `generated_protocols.therapist_id == current_user.id` | All protocol queries scoped |
| **LLM Data Isolation** | No cross-patient/cross-therapist data in LLM context | State assembled per invocation |
| **Checkpoint Isolation** | Thread ID = `therapist_{id}_patient_{id}` | LangGraph scoping |

---

## 19. Future Work

| Item | Description | Timeline |
|---|---|---|
| **Uncertainty Scorer v2** | Multi-sample consistency + NLI entailment verification | Q1 Journal Target |
| **Protocol Feedback Loop** | Therapist rates generated protocols → fine-tune stage/blueprint selection | Post-v1 |
| **Live Session Integration** | Real-time protocol adaptation during video sessions | Future |
| **Patient-Facing Summaries** | Generate patient-appropriate session previews | Future |
| **Multi-Modal KB** | Support video/audio KB materials (lecture recordings, etc.) | Future |
| **Protocol Comparison** | Side-by-side comparison of protocols across sessions for trajectory analysis | Future |
| **Automated Homework Generation** | Separate agent for personalised between-session assignments | Future |

---

## 20. References

1. **LangGraph Documentation** — https://langchain-ai.github.io/langgraph/ — Stateful multi-agent orchestration framework
2. **OpenAI API** — https://platform.openai.com/docs — GPT-4o, text-embedding-3-small
3. **pgvector** — https://github.com/pgvector/pgvector — Vector similarity search for PostgreSQL
4. **Retrieval-Augmented Generation (RAG)** — Lewis et al. (2020), "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks", NeurIPS
5. **Calibrated Uncertainty in NLG** — Kadavath et al. (2022), "Language Models (Mostly) Know What They Know", arXiv:2207.05221
6. **Multi-Agent LLM Systems** — Wu et al. (2023), "AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation", arXiv:2308.08155
7. **Epistemic Uncertainty Estimation** — Xiong et al. (2024), "Can LLMs Express Their Uncertainty? An Empirical Evaluation of Confidence Elicitation in LLMs", ICLR 2024

---

*Document generated: February 11, 2026*  
*System: Nirbaan — A Therapy Management Project*  
*Architecture Version: 1.0*
