# AI Agents - Multi-Agent Protocol Generation Pipeline

This module implements the multi-agent architecture for KB-grounded therapy protocol generation, as specified in `NIRBAAN_AI_REFINED_ARCHITECTURE.md`.

## Architecture Overview

The pipeline consists of 8 specialized agents that work together to generate evidence-based, personalized therapy session protocols:

```
┌─────────────────────────────────────────────────────────────┐
│                    PARALLEL FAN-OUT STAGE                    │
│  Agent 1a: History Picker  ∥  Agent 1b: Session Picker      │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│            Agent 2: Context Synthesiser (LLM)                │
│         Condenses raw data into clinical summary             │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│     Agent 3: Stage Picker (LLM + RAG + Verification Loop)   │
│         Selects and verifies therapy stage                   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│         Agent 4: Blueprint Generator (LLM + RAG)             │
│         Creates session structure skeleton                    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│          Agent 5: Safety Gate (LLM + RAG)                    │
│         Screens for contraindications                         │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│     Agent 6: Clarification Agent (LLM + Human-in-the-Loop)  │
│         Identifies gaps, asks therapist questions            │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│         Agent 7: Protocol Generator (LLM + RAG)              │
│         Generates detailed session protocol                   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│   Agent 8: Uncertainty Scorer (LLM + Revision Loop)          │
│         Scores confidence, revises if needed                  │
└─────────────────────────────────────────────────────────────┘
```

## Implemented Agents

### ✅ Agent 1a: History Picker (COMPLETED)

**Type**: Database Query Agent (No LLM)  
**Location**: `history_picker.py`  
**Purpose**: Fetches patient clinical history from database

**Retrieves:**
- Patient demographics and conditions
- Initial condition description
- Weekly progress self-reports
- Therapist week-by-week notes
- Therapist's AI protocol instruction

**Key Design Decision:**
Does NOT fetch last generated protocol. Session-to-session continuity is derived from actual therapy session transcripts (Agent 1b), not from previous AI-generated plans.

**Usage:**
```python
from app.ai_agents import HistoryPickerAgent

agent = HistoryPickerAgent(db=db_session)
result = await agent.execute(patient_id=123, therapist_id=456)

# Access data
raw_data = result["raw_data"]
summary = result["structured_summary"]
```

**Parallel Execution:**
Runs in parallel with Session Picker to minimize latency. Both agents are independent database reads with no dependencies.

---

### ✅ Agent 1b: Session Picker (COMPLETED)

**Type**: Database Query Agent (No LLM)  
**Location**: `session_picker.py`  
**Purpose**: Fetches recent therapy session transcripts

**Retrieves:**
- Last 2 session transcripts (configurable)
- Session metadata (week numbers, dates)
- Transcript length statistics

**Key Features:**
- Handles first-time patients gracefully (returns `no_data` status instead of error)
- Provides session summaries for quick overview
- Can fetch specific week sessions if needed

**Usage:**
```python
from app.ai_agents import SessionPickerAgent

agent = SessionPickerAgent(db=db_session)
result = await agent.execute(patient_id=123, therapist_id=456, num_sessions=2)

# Access data
sessions = result["sessions"]
summary = result["session_summary"]
```

**Parallel Execution:**
Runs in parallel with History Picker. Together they form the data-fetching stage that feeds into Context Synthesiser.

---

## Agents To Be Implemented

### 🔲 Agent 2: Context Synthesiser
- **Type**: LLM (No RAG)
- **Purpose**: Condenses raw data into focused clinical summary
- **Status**: Not yet implemented

### 🔲 Agent 3: Stage Picker
- **Type**: LLM + RAG + Self-Verification Loop
- **Purpose**: Selects and verifies therapy stage
- **Status**: Not yet implemented

### 🔲 Agent 4: Blueprint Generator
- **Type**: LLM + RAG
- **Purpose**: Creates session structure skeleton
- **Status**: Not yet implemented

### 🔲 Agent 5: Safety Gate
- **Type**: LLM + RAG
- **Purpose**: Screens for contraindications
- **Status**: Not yet implemented

### 🔲 Agent 6: Clarification Agent
- **Type**: LLM + Human-in-the-Loop
- **Purpose**: Identifies gaps, asks therapist questions
- **Status**: Not yet implemented

### 🔲 Agent 7: Protocol Generator
- **Type**: LLM + RAG
- **Purpose**: Generates detailed 60-minute session protocol
- **Status**: Not yet implemented

### 🔲 Agent 8: Uncertainty Scorer
- **Type**: LLM + Revision Loop
- **Purpose**: Scores confidence, triggers revision if needed
- **Status**: Not yet implemented

---

## Design Principles

1. **Parallel Data Fetching**: Agents 1a and 1b run simultaneously to reduce latency
2. **Pure DB Queries First**: No LLM calls until Context Synthesiser (Agent 2)
3. **Structured Output**: All agents return consistent JSON format with metadata
4. **Error Handling**: Graceful degradation for missing data (especially for first-time patients)
5. **Traceability**: Every agent tracks execution metadata (LLM calls, timing, etc.)

---

## Integration with LangGraph

Each agent's `execute()` method is designed as a LangGraph node entry point:

```python
from langgraph.graph import StateGraph

# Define state
class ProtocolState(TypedDict):
    patient_id: int
    therapist_id: int
    history_data: Dict
    session_data: Dict
    # ... more fields

# Create graph
workflow = StateGraph(ProtocolState)

# Add parallel nodes
workflow.add_node("history_picker", history_picker_node)
workflow.add_node("session_picker", session_picker_node)

# Set parallel edges
workflow.set_entry_point("history_picker")
workflow.add_edge("history_picker", "context_synthesiser")
workflow.add_edge("session_picker", "context_synthesiser")
```

---

## Testing

Each agent includes comprehensive error handling and can be tested independently:

```python
# Test History Picker
agent = HistoryPickerAgent(db)
result = await agent.execute(patient_id=1, therapist_id=1)
assert result["status"] == "success"

# Test Session Picker
agent = SessionPickerAgent(db)
result = await agent.execute(patient_id=1, therapist_id=1)
assert result["status"] in ["success", "no_data"]  # no_data is OK for new patients
```

---

## Next Steps

1. ✅ Implement History Picker (Agent 1a) - **COMPLETED**
2. ✅ Implement Session Picker (Agent 1b) - **COMPLETED**
3. 🔲 Implement Context Synthesiser (Agent 2)
4. 🔲 Implement Stage Picker with verification loop (Agent 3)
5. 🔲 Set up LangGraph workflow for parallel execution
6. 🔲 Implement remaining agents (4-8)
7. 🔲 Add comprehensive testing suite
8. 🔲 Integrate with frontend API endpoints

---

## References

- **Architecture Document**: `NIRBAAN_AI_REFINED_ARCHITECTURE.md`
- **Database Models**: 
  - `app/patients/models.py`
  - `app/progress/models.py`
  - `app/sessions/models.py`
