# How the AI Sends a Message to the EP Group — Full Explanation

> This covers the entire journey from a patient typing a message, to an AI-generated
> alert appearing live in the human helpers' group chat.

---

## 1. The Big Picture

```
Patient types: "I need a human helper right now"
         │
         ▼
   chat_service.py           ← saves message, calls the central graph
         │
         ▼
   CentralAgent/graph.py     ← LangGraph state machine
         │
    [router node]
         │ decides: "human_escalation"
         ▼
   HumanEscalationAgent/graph.py   ← second LangGraph state machine
         │
    [load_context]     ← DB query: patient profile, ERP pairs, progress
         │
    [verifier]         ← LLM decides: does this REALLY need a human?
         │
    ┌────┴────┐
    │YES      │NO
    ▼         ▼
[generate_  [no_help_    ← "Let's keep talking" response to patient
 helper_    needed]
 message]
    │
    ▼
[send_to_   ← saves EPGroupMessage to DB + WebSocket broadcast
 ep_group]
    │
    ▼
EP group chat lights up instantly for all connected helpers
```

---

## 2. Entry Point — chat_service.py

**File:** `backend/app/NirbaanAIPatient/chat_service.py`

Everything starts here. When a patient sends a message through the frontend:

```python
def send_message(self, *, patient_id, message, thread_id):
    # 1. validate patient
    patient = self._get_patient_or_raise(patient_id)

    # 2. save the patient's message to DB
    user_msg = self._save_message(thread_id=thread.id, role="user", content=clean_message)

    # 3. build initial state dict — this is what gets passed through the entire graph
    initial_state = {
        "patient_id": patient.id,
        "therapist_id": patient.therapist_id,   # ← key: needed to find the EP group
        "thread_id": thread.id,
        "user_message": clean_message,
        "recent_chat_history": recent_chat_history,
    }

    # 4. invoke the central brain — this runs everything
    final_state = central_graph.invoke(initial_state)

    # 5. check if escalation happened
    return PsychoeducationChatSendResponse(
        ...
        is_escalation=bool(final_state.get("ep_group_message_id")),
        ep_group_message_id=final_state.get("ep_group_message_id"),
    )
```

The `ep_group_message_id` being set in `final_state` is how we know escalation actually happened — it's the database row ID of the message that was posted to the EP group.

---

## 3. What is LangGraph? (Plain English)

LangGraph is a library for building AI workflows as a **graph of nodes and edges**, like a flowchart.

- **Node** = a function that takes the current state dict and returns changes to it
- **Edge** = fixed connection "always go from A to B"
- **Conditional Edge** = "look at the state, then decide which node to go to next"
- **State** = a shared dictionary that accumulates data as it passes through nodes

Each node receives the full state, does its work (LLM call, DB query, etc.), and returns only the keys it wants to update. The graph merges those updates back into the state before passing to the next node.

---

## 4. The Central Agent Graph

**File:** `backend/app/NirbaanAIPatient/CentralAgent/graph.py`

This is the **top-level brain**. It has 4 nodes:

```
START → [router] → conditional edge ─┬→ [psychoeducation] → END
                                      ├→ [support]          → END
                                      └→ [human_escalation] → END
```

```python
def router_decision(state):
    route = state.get("route")
    if route == "psychoeducation": return "psychoeducation"
    if route == "human_escalation": return "human_escalation"
    return "support"

builder.add_conditional_edges("router", router_decision, {
    "psychoeducation": "psychoeducation",
    "support": "support",
    "human_escalation": "human_escalation",
})
```

### The Router Node

**File:** `backend/app/NirbaanAIPatient/CentralAgent/router.py`

This is a small LLM call (cheap model, `gpt-5-nano`) that reads the patient's message and outputs one route string:

```python
prompt = f"""
You are routing a patient message to the correct AI agent.

Agents:
  psychoeducation  - questions about OCD concepts, ERP theory
  support          - emotional distress, burnout, rough day
  human_escalation - patient asks for human helper, crisis, in-person intervention

Patient message: {state["user_message"]}

Return route.
"""
result = llm.invoke(prompt)   # returns RouterOutput(route="human_escalation")
return {"route": result.route}
```

If the patient says anything like *"I need someone to come help me"* or *"I need a human helper"*, the router returns `"human_escalation"` and the central graph jumps to the `human_escalation` node.

### The human_escalation Node (in central graph)

**File:** `backend/app/NirbaanAIPatient/CentralAgent/subgraph_nodes.py`

```python
def human_escalation_node(state: Dict):
    result = human_escalation_graph.invoke(state)   # runs the SECOND graph
    return {
        "final_response": result.get("final_response", "")
    }
```

This calls `human_escalation_graph.invoke(state)` — it hands off the entire state to a separate LangGraph — and waits for it to complete. Note: `ep_group_message_id` is already in the state dict returned by the sub-graph, and since LangGraph merges state, it passes back up to `final_state` in `chat_service.py`.

---

## 5. The Human Escalation Sub-Graph

**File:** `backend/app/NirbaanAIPatient/HumanEscalationAgent/graph.py`

A second, independent LangGraph with its own nodes:

```
START → [load_context] → [verifier] ─┬→ [generate_helper_message] → [send_to_ep_group] → END
                                      └→ [no_help_needed]                                → END
```

```python
builder.add_edge(START, "load_context")
builder.add_edge("load_context", "verifier")

builder.add_conditional_edges("verifier", verifier_decision, {
    "generate_helper_message": "generate_helper_message",
    "no_help_needed": "no_help_needed",
})

builder.add_edge("generate_helper_message", "send_to_ep_group")
builder.add_edge("send_to_ep_group", END)
builder.add_edge("no_help_needed", END)
```

---

## 6. Node 1 — load_context (No LLM — Pure DB Query)

**File:** `backend/app/NirbaanAIPatient/HumanEscalationAgent/Nodes/load_context.py`

This node makes **zero LLM calls**. It just pulls data from the database using the `patient_id` from state:

```python
def load_context_node(state, db):
    patient_id = state["patient_id"]

    # 1. Patient profile
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    # → patient_name, patient_conditions, patient_conditions_description, patient_address

    # 2. Recent chat history (last 10 messages from this thread)
    msgs = db.query(PsychoeducationChatMessage)
             .filter(thread_id == state["thread_id"])
             .order_by(created_at.desc()).limit(10).all()
    # → recent_chat_history = [{"role": "user", "content": "..."}, ...]

    # 3. ERP obsession/compulsion pairs
    erp_items = db.query(ERPItem).filter(ERPItem.patient_id == patient_id).all()
    # → db_obsession_compulsion_pairs = [
    #     {"obsession": "...", "compulsions": ["...", "..."]}, ...
    #   ]

    # 4. Latest weekly progress report
    latest_progress = db.query(WeeklyProgress)
                        .filter(patient_id == patient_id)
                        .order_by(created_at.desc()).first()
    # → db_latest_weekly_progress = {week_number, detailed_progress, homework_reflection, ...}

    return { all of the above }
```

Why this matters: the context loaded here is what makes the AI-generated alert message **specific and useful** for the human helpers — they get the patient's exact ERP profile and how therapy has been going.

---

## 7. Node 2 — verifier (LLM Decision)

**File:** `backend/app/NirbaanAIPatient/HumanEscalationAgent/Nodes/verifier.py`

This is the **gatekeeper**. Just because a patient asks for human help doesn't mean human helpers should be called. The verifier LLM makes a strict clinical decision.

```python
class VerifierOutput(BaseModel):
    needs_human_help: bool
    reasoning: str

llm = ChatOpenAI(model="gpt-5.2", temperature=0).with_structured_output(VerifierOutput)
```

The prompt tells the LLM to be **conservative** — only escalate for:
- Intense, acute distress the AI cannot contain
- Patient unable to cope in the current moment
- Need for real-world human presence

And **explicitly NOT to escalate** for:
- Patient merely asking for a human
- OCD intrusive thoughts about self-harm (ego-dystonic, not real intent)
- General distress where the patient is still conversational

The LLM returns a structured object:
```json
{
  "needs_human_help": true,
  "reasoning": "Patient is expressing acute panic with inability to stay safe..."
}
```

The conditional edge function reads `state["needs_human_help"]`:
```python
def verifier_decision(state):
    if state.get("needs_human_help"):
        return "generate_helper_message"
    return "no_help_needed"
```

### If NO escalation needed → no_help_needed node

**File:** `Nodes/no_help_needed.py`

Simple terminal node — returns a reassuring message to the patient:
```python
return {
    "final_response": (
        "I understand you're going through a tough time, and I'm here for you. "
        "Based on what you've shared, I believe we can continue working through this together..."
    )
}
```
No message is sent to the EP group. Helpers are never notified.

---

## 8. Node 3 — generate_helper_message (LLM Writes the Alert)

**File:** `backend/app/NirbaanAIPatient/HumanEscalationAgent/Nodes/generate_helper_message.py`

Only runs if `needs_human_help = True`. Uses all the context loaded earlier to generate a professional alert for the human helpers group:

```python
class HelperMessageOutput(BaseModel):
    message: str

llm = ChatOpenAI(model="gpt-5-nano", temperature=0.3).with_structured_output(HelperMessageOutput)
```

The prompt assembles:
- Patient name, conditions, address
- ERP pairs (up to 5, compulsions truncated to 3 each)
- Latest weekly progress (truncated to 300/200 chars)
- The verifier's reasoning (why escalation was triggered)
- The patient's actual message
- Last 6 turns of chat history

```python
prompt = f"""
You are composing an urgent alert for human helpers (emergency personnel).
A patient needs in-person help.

Patient Name: {patient_name}
Patient Conditions: {patient_conditions}
Patient Address: {patient_address}

ERP Obsession/Compulsion Profile:
  - Obsession: contamination | Compulsions: hand-washing, avoidance
  - Obsession: harm OCD    | Compulsions: checking knives

Latest Weekly Progress:
  Week 4 (2026-03-08):
  Progress: Patient completed 3 ERP exposures...

Escalation Reason: {verifier_reasoning}

Patient's latest message: "{user_message}"

Recent conversation:
  Patient: I can't cope anymore, please send help
  AI: I hear you...

Write the helper alert message.
"""

result = llm.invoke(prompt)
return {"helper_message": result.message}
```

The output is a rich, context-aware message that might look like:

> **URGENT — Patient Needs In-Person Help**
> Patient: John Smith (Contamination OCD + Harm OCD)
> Address: 14 Oak Street, Lahore
> Reason for escalation: Patient is in acute distress, expressing inability to stay safe...
> Active ERP concerns: contamination obsession (hand-washing), harm intrusions...
> Recent progress: Week 4 — patient had a setback after difficult ERP exposure...
> Please respond here if you are taking this patient.

---

## 9. Node 4 — send_to_ep_group (Saves to DB + Broadcasts via WebSocket)

**File:** `backend/app/NirbaanAIPatient/HumanEscalationAgent/Nodes/send_to_ep_group.py`

This is where the AI message actually **enters the EP group chat**.

### Step 1: Get or create the therapist's EP group

```python
group = db.query(EPGroup).filter(EPGroup.therapist_id == therapist_id).first()
if not group:
    group = EPGroup(therapist_id=therapist_id)
    db.add(group)
    db.commit()
```

One EP group per therapist exists (`unique=True` on `therapist_id` in the model). The `therapist_id` came from the patient's profile — every patient belongs to a therapist, and every therapist has one EP group.

### Step 2: Create the EPGroupMessage record

```python
msg = EPGroupMessage(
    group_id=group.id,
    sender_id=None,               # AI has no user ID
    sender_role="ai_agent",       # ← this is how the UI knows to style it purple
    sender_name="Nirbaan AI",
    content=helper_message,       # the text from the previous node
    patient_id=patient_id,        # so helpers know which patient
    patient_name=patient_name,
    is_claimed=False,             # nobody has called dibs yet
)
db.add(msg)
db.commit()
```

This row in `ep_group_messages` is **permanent** unless manually deleted. Helpers can scroll back and see all past AI alerts.

### Step 3: WebSocket broadcast (the live notification)

```python
from app.chat.ep_group_router import ep_group_manager, _msg_to_dict

payload = _msg_to_dict(msg)   # convert to dict for JSON serialization

try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = None

if loop and loop.is_running():
    loop.create_task(ep_group_manager.broadcast(group.id, payload))
else:
    asyncio.run(ep_group_manager.broadcast(group.id, payload))
```

This uses the **same `ep_group_manager`** (a `ChatConnectionManager` instance) that the EP group WebSocket endpoint uses. Any EP or therapist currently connected to the group chat WebSocket receives the message **instantly** — without refreshing the page.

The `loop.create_task()` vs `asyncio.run()` pattern handles the fact that this node runs inside FastAPI's async event loop (we can't call `asyncio.run()` inside a running loop — it would crash).

### Step 4: Return final response to patient

```python
return {
    "ep_group_message_id": msg.id,       # ← proof escalation happened
    "final_response": (
        "I understand you need help right now. "
        "I've alerted your care team's human helpers — one of them will be reaching out to you soon. "
        "Please stay where you are if you can. I'm still here with you while you wait."
    ),
}
```

The patient sees this reassuring message in their NirbaanAI chat. The `ep_group_message_id` bubbles back up through the graph all the way to `chat_service.py`.

---

## 10. How the Frontend Shows Escalation

**File:** `frontend/src/pages/NirbaanAIChat.jsx`

When `chat_service.py` returns the response, the API sends:

```json
{
  "assistant_message": { "content": "I've alerted your care team..." },
  "is_escalation": true,
  "ep_group_message_id": 42
}
```

The frontend detects `msg.is_escalation === true` and:
- Renders the bubble with a dark red background (`.nai-bubble.escalation`)
- Shows a red banner: `🚨 Human helpers have been alerted`
- Switches the AI avatar to `🚨`

---

## 11. What the EP Sees in Real Time

**File:** `frontend/src/pages/EPChatPage.jsx` — Group Chat tab

The EP's browser has an open WebSocket connection:
```
ws://127.0.0.1:8000/chat/ep-group/ws/{group_id}?token=...
```

When `ep_group_manager.broadcast()` fires from inside `send_to_ep_group.py`, the message is pushed immediately. The EP's `ws.onmessage` fires:

```js
ws.onmessage = (e) => {
  const data = JSON.parse(e.data);
  if (data.type === 'claim_update') {
    // someone claimed the patient
    setGroupMessages((prev) => prev.map((m) => m.id === data.id ? data : m));
  } else {
    // new message (including AI alerts)
    setGroupMessages((prev) => [...prev, data]);
  }
};
```

The new AI message has `sender_role: "ai_agent"`, so the UI renders it with a purple bubble and an `AI` badge. If `patient_name` is set, it shows `👤 Patient: John Smith` inside the bubble.

The EP can then click **"I'm Visiting This Patient"** — a claim button that only shows on unclaimed AI messages:

```jsx
{!msg.is_claimed && msg.sender_role === 'ai_agent' && (
  <button onClick={() => handleClaim(msg)}>
    I'm Visiting This Patient
  </button>
)}
```

Clicking this calls `POST /chat/ep-group/{group_id}/messages/{msg_id}/claim`, which sets `is_claimed=True`, `claimed_by_name=ep.name` in the DB, and broadcasts a `claim_update` to all connected helpers so they all see who took the patient.

---

## 12. Complete End-to-End Flow (All Files)

```
Patient types "I need human help"
│
├─ NirbaanAIChat.jsx                    sends POST /nirbaan-ai/chat
│
├─ NirbaanAIPatient/router.py           FastAPI route handler
│
├─ chat_service.py                      saves user message to DB
│   └─ central_graph.invoke(state)
│
├─ CentralAgent/graph.py                START → router node
├─ CentralAgent/router.py               LLM: route = "human_escalation"
├─ CentralAgent/graph.py                conditional edge → human_escalation node
├─ CentralAgent/subgraph_nodes.py       human_escalation_node()
│   └─ human_escalation_graph.invoke(state)
│
├─ HumanEscalationAgent/graph.py        START → load_context
├─ Nodes/load_context.py                DB: patient, ERP pairs, progress → state
│
├─ HumanEscalationAgent/graph.py        load_context → verifier
├─ Nodes/verifier.py                    LLM (gpt-5.2): needs_human_help = True
│
├─ HumanEscalationAgent/graph.py        conditional: → generate_helper_message
├─ Nodes/generate_helper_message.py     LLM (gpt-5-nano): writes alert text → state
│
├─ HumanEscalationAgent/graph.py        generate_helper_message → send_to_ep_group
├─ Nodes/send_to_ep_group.py
│   ├─ DB: INSERT INTO ep_group_messages (sender_role='ai_agent', ...)
│   ├─ ep_group_manager.broadcast(group_id, payload)    ← WebSocket push
│   └─ returns: ep_group_message_id, final_response
│
├─ HumanEscalationAgent/graph.py        END (state has ep_group_message_id)
├─ CentralAgent/subgraph_nodes.py       returns final_response
├─ CentralAgent/graph.py                END
│
├─ chat_service.py                      saves assistant message to DB
│   └─ returns PsychoeducationChatSendResponse(is_escalation=True, ep_group_message_id=42)
│
├─ NirbaanAIChat.jsx                    receives response
│   ├─ renders red escalation bubble + banner
│
└─ EPChatPage.jsx (Group tab)           ws.onmessage fires instantly
    └─ purple AI bubble with "I'm Visiting This Patient" button
```

---

## 13. File Map

```
backend/
  app/
    NirbaanAIPatient/
      chat_service.py                     ← entry point, calls central_graph
      schemas.py                          ← is_escalation + ep_group_message_id in response
      CentralAgent/
        graph.py                          ← top-level LangGraph (router → agents)
        router.py                         ← LLM: which agent? psychoeducation/support/human_escalation
        subgraph_nodes.py                 ← calls human_escalation_graph.invoke()
        state.py                          ← CentralState TypedDict
      HumanEscalationAgent/
        graph.py                          ← sub-graph: load_context→verifier→generate/no_help→send
        state.py                          ← HumanEscalationState TypedDict (all fields)
        Nodes/
          load_context.py                 ← DB: patient + ERP + progress (no LLM)
          verifier.py                     ← LLM (gpt-5.2): needs_human_help decision
          generate_helper_message.py      ← LLM (gpt-5-nano): writes EP group alert
          send_to_ep_group.py             ← DB insert + WebSocket broadcast
          no_help_needed.py               ← terminal: returns reassuring response
    chat/
      models.py                           ← EPGroup, EPGroupMessage models
      ep_group_router.py                  ← /claim endpoint, WS endpoint, ep_group_manager
      manager.py                          ← ChatConnectionManager (the room system)

frontend/
  src/
    pages/
      NirbaanAIChat.jsx                   ← escalation bubble + banner + 🚨 avatar
      NirbaanAIChat.css                   ← .nai-bubble.escalation, .nai-escalation-banner
      EPChatPage.jsx                      ← Group Chat tab, purple AI bubble, claim button
```
