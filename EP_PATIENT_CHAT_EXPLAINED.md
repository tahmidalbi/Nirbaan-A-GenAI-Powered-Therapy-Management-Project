# EP ↔ Patient Direct Chat — Full System Explanation

> This document explains everything: the database, the backend, the frontend,
> and — most importantly — **how WebSocket real-time chat actually works**, step by step.

---

## 1. The Big Picture

```
EP (Human Helper)                        Patient
─────────────────                        ──────────────────
Opens "Patients" tab                     Opens "My Helpers" tab
  → sees patient list                      → sees active helpers
  → clicks a patient                       → clicks a helper
  → session is created in DB               → session was already created by EP
  → WebSocket connection opens             → WebSocket connection opens
  → both are now in the SAME room          → both are now in the SAME room
          │                                         │
          └──────── Messages flow both ways ─────────┘
  → EP clicks "Close Session"
      → all messages deleted from DB
      → both sides are notified instantly via WS
      → patient's helper disappears from their list
```

---

## 2. Database Tables (the foundation)

### `ep_patient_sessions`
One row per EP-Patient conversation. Think of it as a "chat room" record.

```
id          | ep_id  | patient_id | status  | created_at          | closed_at
────────────┼────────┼────────────┼─────────┼─────────────────────┼──────────
1           | 3      | 7          | active  | 2026-03-12 00:17:51 | NULL
2           | 3      | 9          | closed  | 2026-03-10 10:00:00 | 2026-03-10 12:30:00
```

- `ep_id` → FK to `emergency_personnel.id`
- `patient_id` → FK to `patients.id`
- `status` → `"active"` means live, `"closed"` means EP ended it
- When EP closes: `status` becomes `"closed"`, all messages are deleted

### `ep_patient_messages`
All messages inside a session.

```
id | session_id | sender_role | sender_id | sender_name | content          | created_at
───┼────────────┼─────────────┼───────────┼─────────────┼──────────────────┼────────────
1  | 1          | ep          | 3         | Dr. Ali     | Hello, how are.. | 2026-03-12
2  | 1          | patient     | 7         | John        | I'm feeling...   | 2026-03-12
3  | 1          | ep          | 3         | Dr. Ali     | That's normal..  | 2026-03-12
```

- `sender_role` is either `"ep"` or `"patient"` (used to decide left/right bubble in UI)
- When session is closed, ALL rows with that `session_id` are deleted

**File:** `backend/app/chat/models.py`

```python
class EPPatientSession(Base):
    __tablename__ = "ep_patient_sessions"
    id         = Integer PK
    ep_id      = FK → emergency_personnel.id
    patient_id = FK → patients.id
    status     = "active" | "closed"
    created_at = auto timestamp
    closed_at  = nullable timestamp

class EPPatientMessage(Base):
    __tablename__ = "ep_patient_messages"
    id          = Integer PK
    session_id  = FK → ep_patient_sessions.id
    sender_role = "ep" | "patient"
    sender_id   = actual user id
    sender_name = display name
    content     = message text
    created_at  = auto timestamp
```

---

## 3. What is a WebSocket? (Plain English)

### Normal HTTP request (what you're used to):
```
Browser → "GET /api/messages" → Server
Browser ←  response with data ← Server
[connection closes]
```
The browser has to **ask** every time it wants new data. To get live updates you'd have to ask every second (polling). Slow and wasteful.

### WebSocket:
```
Browser → "I want to upgrade to WebSocket" → Server
Browser ←  "OK, connection is now open"    → Server
[connection STAYS OPEN — both sides can talk ANY TIME]

Server → "new message!" → Browser   (pushed immediately)
Browser → "user typed X" → Server   (sent immediately)
```

The connection stays open. No asking. When a message arrives, the server **pushes** it directly to the browser — and the browser renders it **instantly**.

### The WebSocket URL in this project:
```
ws://127.0.0.1:8000/chat/ep-patient/ws/{session_id}?token=eyJ...
```
- `ws://` instead of `http://` (or `wss://` for secure, like `https://`)
- `session_id` identifies which chat room to join
- `token` is the JWT so the backend can verify who you are

---

## 4. The Connection Manager — The "Room" System

**File:** `backend/app/chat/manager.py`

```python
class ChatConnectionManager:
    def __init__(self):
        # A dictionary: room_id → set of open WebSocket connections
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket, group_id):
        await websocket.accept()          # completes the handshake
        self.active_connections[group_id].add(websocket)

    def disconnect(self, websocket, group_id):
        self.active_connections[group_id].discard(websocket)

    async def broadcast(self, group_id, message: dict):
        # Send to EVERY connected websocket in this room
        for connection in self.active_connections[group_id]:
            await connection.send_text(json.dumps(message))
```

**Imagine it like a walkie-talkie channel system:**
- `group_id` (or `session_id`) = the channel number
- `connect()` = tuning your radio to that channel
- `broadcast()` = speaking — everyone on the channel hears it
- `disconnect()` = turning off your radio

For EP-Patient chat, this is instantiated once:
```python
# backend/app/chat/ep_patient_router.py  line 18
ep_patient_manager = ChatConnectionManager()
```

This is a **single Python object** that lives in memory for the entire lifetime of the server. It holds ALL open connections for ALL EP-Patient sessions simultaneously.

---

## 5. Backend WebSocket Endpoint — Step by Step

**File:** `backend/app/chat/ep_patient_router.py` — lines 195–250

```python
@ep_patient_router.websocket("/ws/{session_id}")
async def websocket_ep_patient(websocket: WebSocket, session_id: int, token: str = Query(...)):
```

### Phase 1: Handshake & Auth (runs once when browser connects)

```python
td = decode_access_token(token)             # Who is this? (EP or Patient)
session = db.query(EPPatientSession)...     # Does this session exist?

if not session or session.status != "active":
    await websocket.close(code=4004)        # Reject — no such session
    return

if td.role == "emergency_personnel":
    if td.id != session.ep_id:
        await websocket.close(code=4003)    # Reject — wrong EP
        return
    sender_role = "ep"
    sender_name = ep.name

elif td.role == "patient":
    if td.id != session.patient_id:
        await websocket.close(code=4003)    # Reject — wrong patient
        return
    sender_role = "patient"
    sender_name = patient.name

await ep_patient_manager.connect(websocket, session_id)  # ADD to room
```

At this point the connection is accepted and the user is in the room.

### Phase 2: The Infinite Loop (runs forever until disconnect)

```python
while True:
    data = await websocket.receive_text()       # WAIT for user to type something
    payload = json.loads(data)                  # parse JSON
    content = payload.get("content", "").strip()

    # Save to database
    msg = EPPatientMessage(
        session_id=session_id,
        sender_role=sender_role,
        sender_id=td.id,
        sender_name=sender_name,
        content=content,
    )
    db.add(msg)
    db.commit()

    # Broadcast to EVERYONE in the room (both EP and patient)
    await ep_patient_manager.broadcast(session_id, _msg_to_dict(msg))
```

`await websocket.receive_text()` **blocks** — the code just waits there doing nothing until the user sends a message. When a message arrives, it:
1. Parses it
2. Saves it to the DB (so history is preserved)
3. Broadcasts it to everyone in the session (both the sender AND the other person)

### Phase 3: Disconnect

```python
except WebSocketDisconnect:
    ep_patient_manager.disconnect(websocket, session_id)
```

When the browser tab closes or the user navigates away, `WebSocketDisconnect` is raised. The connection is removed from the room dictionary. The other person stays connected.

---

## 6. REST Endpoints (the non-WebSocket parts)

These are normal HTTP calls used before the WebSocket opens.

**File:** `backend/app/chat/ep_patient_router.py`

### `GET /chat/ep-patient/patients` — EP gets patient list

```
Token (EP) → decode → find EP → EP.therapist_id
→ SELECT * FROM patients WHERE therapist_id = ep.therapist_id
→ For each patient: check if active session exists
→ Return list with { id, name, conditions, active_session_id }
```

Used by: `EPChatPage.jsx` when EP switches to "Patients" tab.

### `POST /chat/ep-patient/session/{patient_id}` — EP opens a session

```
Token (EP) → verify → check if session already exists (active)
  IF exists → return existing session
  IF not    → INSERT into ep_patient_sessions → return new session
→ Returns: { id, ep_name, patient_name, status, … }
```

Called when EP clicks a patient in the list. If they already had a session it just reopens it. No duplicate sessions.

### `GET /chat/ep-patient/session/{session_id}/messages` — Load history

```
Token (EP or Patient) → verify access → SELECT messages ORDER BY created_at
→ Returns list of messages
```

Called once when first joining the session, to load old messages.

### `POST /chat/ep-patient/session/{session_id}/close` — EP closes session

```
Token (EP) → verify they own this session
→ DELETE FROM ep_patient_messages WHERE session_id = ?
→ UPDATE ep_patient_sessions SET status='closed', closed_at=now()
→ ep_patient_manager.broadcast(session_id, {"type": "session_closed"})
→ Return { "detail": "Session closed and messages deleted" }
```

The `broadcast` here is **crucial** — even though this is a REST endpoint (not WebSocket), we use the manager to push to any currently-open WebSocket connections. The patient's browser receives `{"type": "session_closed"}` and immediately removes that helper from their list.

### `GET /chat/ep-patient/my-sessions` — Patient gets their EP list

```
Token (Patient) → SELECT sessions WHERE patient_id=? AND status='active'
→ For each session: look up EP name
→ Returns list of { session_id, ep_id, ep_name }
```

Called when patient opens "My Helpers" tab.

---

## 7. Frontend — EP Side

**File:** `frontend/src/pages/EPChatPage.jsx`

### Step 1: EP switches to "Patients" tab

```jsx
// useEffect runs when activeTab changes to 'patients'
useEffect(() => {
  if (activeTab !== 'patients') return;
  setPatientsLoading(true);
  getEPPatientsList()                    // → GET /chat/ep-patient/patients
    .then(setPatients)                   // store patient list in state
    .finally(() => setPatientsLoading(false));
}, [activeTab]);
```

`getEPPatientsList` is in `frontend/src/api/chat.api.js`:
```js
export async function getEPPatientsList() {
  const token = getToken();  // reads JWT from localStorage
  const res = await axiosInstance.get(`${BASE}/ep-patient/patients?token=${token}`);
  return res.data;           // array of patients
}
```

### Step 2: EP clicks a patient

The click sets `selectedPatient`. A `useEffect` watches `selectedPatient.id`:

```jsx
useEffect(() => {
  if (!selectedPatient) return;

  // 1. Open or resume session
  const openSession = selectedPatient.active_session_id
    ? Promise.resolve({ id: selectedPatient.active_session_id, ... })
    : getOrCreateEPPatientSession(selectedPatient.id);  // POST /session/{patient_id}

  openSession.then((sess) => {
    setPatientSession(sess);    // store session info

    // 2. Load message history
    getEPPatientSessionMessages(sess.id)  // GET /session/{id}/messages
      .then(setPatientMessages);

    // 3. Open WebSocket connection
    const ws = openEPPatientSocket(sess.id);
    patientWsRef.current = ws;

    ws.onopen = () => setPatientWsStatus('open');

    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      if (data.type === 'session_closed') {
        // EP themselves closed it from another tab (edge case)
        setPatientSession(null);
        setPatientMessages([]);
        setSelectedPatient(null);
      } else {
        // New message arrived — append to list
        setPatientMessages((prev) => [...prev, data]);
      }
    };

    ws.onclose = () => setPatientWsStatus('closed');
    ws.onerror = () => setPatientWsStatus('closed');
  });
}, [selectedPatient?.id]);
```

`openEPPatientSocket` in `chat.api.js`:
```js
export function openEPPatientSocket(sessionId) {
  const token = getToken();
  return new WebSocket(`ws://127.0.0.1:8000/chat/ep-patient/ws/${sessionId}?token=${token}`);
}
```

This is just the **browser's built-in WebSocket constructor** — it connects to the backend endpoint.

### Step 3: EP types and sends a message

```jsx
const handlePatientSend = () => {
  const text = patientInputText.trim();
  if (!text || patientWsRef.current.readyState !== WebSocket.OPEN) return;

  // Send JSON text through the WebSocket
  patientWsRef.current.send(JSON.stringify({ content: text }));

  setPatientInputText('');   // clear input box
};
```

The message goes:
```
Browser sends JSON → WS connection → Backend receive_text() → saves to DB → broadcast back to all in room
```

Note: **the EP's own message also comes back via broadcast**. So `ws.onmessage` handles the EP's own messages too. That's why we don't manually add the message to state — we wait for the broadcast to do it.

### Step 4: EP clicks "Close Session"

```jsx
const handleCloseSession = async () => {
  if (!window.confirm("Close chat? All messages will be deleted.")) return;

  await closeEPPatientSession(patientSession.id);  // POST /session/{id}/close

  // Clean up local state
  setPatientSession(null);
  setPatientMessages([]);
  setSelectedPatient(null);

  // Refresh patient list
  getEPPatientsList().then(setPatients);
};
```

`closeEPPatientSession` → REST call → backend deletes messages + broadcasts `session_closed`.

---

## 8. Frontend — Patient Side

**File:** `frontend/src/pages/PatientChatPage.jsx`

### Step 1: Patient switches to "My Helpers" tab

```jsx
useEffect(() => {
  if (activeTab !== 'helpers') return;
  getPatientEPSessions()           // → GET /chat/ep-patient/my-sessions
    .then(setEpSessions);
}, [activeTab]);
```

This returns only EPs with `status = 'active'`. The patient **never sees** closed sessions or EPs who haven't started a session.

### Step 2: Patient clicks a helper

```jsx
useEffect(() => {
  if (!selectedEpSession) return;

  // Load existing messages
  getEPPatientSessionMessages(selectedEpSession.session_id)
    .then(setEpMessages);

  // Open WebSocket
  const ws = openEPPatientSocket(selectedEpSession.session_id);
  epWsRef.current = ws;

  ws.onmessage = (e) => {
    const data = JSON.parse(e.data);

    if (data.type === 'session_closed') {
      // EP ended the session — remove from patient's list immediately
      setEpSessions((prev) => prev.filter(s => s.session_id !== selectedEpSession.session_id));
      setSelectedEpSession(null);
      setEpMessages([]);
      ws.close();
    } else {
      setEpMessages((prev) => [...prev, data]);
    }
  };
}, [selectedEpSession?.session_id]);
```

### Step 3: Patient replies

Exactly the same as EP side:
```jsx
const handleEpSend = () => {
  epWsRef.current.send(JSON.stringify({ content: epInputText }));
  setEpInputText('');
};
```

---

## 9. Complete Message Flow (End-to-End)

Here's what happens when **EP types "Hello John"** and **Patient John receives it**:

```
1. EP types "Hello John" and presses Enter
   EPChatPage.jsx → handlePatientSend()

2. Browser sends JSON through open WebSocket connection:
   patientWsRef.current.send('{"content": "Hello John"}')

3. The WebSocket tunnel carries it to the server:
   ws://127.0.0.1:8000/chat/ep-patient/ws/1?token=eyJ...

4. Backend is waiting in the infinite loop:
   data = await websocket.receive_text()
   → data = '{"content": "Hello John"}'

5. Backend saves to database:
   INSERT INTO ep_patient_messages 
     (session_id=1, sender_role='ep', sender_id=3, sender_name='Dr. Ali', content='Hello John')

6. Backend broadcasts to ALL connections in session 1:
   ep_patient_manager.broadcast(1, {
     "type": "message",
     "id": 42,
     "sender_role": "ep",
     "sender_name": "Dr. Ali",
     "content": "Hello John",
     "created_at": "2026-03-12T00:30:00"
   })

7. The manager loops through active_connections[1]:
   - EP's WebSocket → receives the broadcast (their own message comes back)
   - Patient's WebSocket → receives the broadcast

8. Both browsers' ws.onmessage fires:
   setPatientMessages((prev) => [...prev, data])   ← EP side appends
   setEpMessages((prev) => [...prev, data])        ← Patient side appends

9. React re-renders, bubble appears on both screens simultaneously
```

---

## 10. Close Session Flow

When EP clicks "✕ Close Session":

```
1. EPChatPage.jsx → handleCloseSession()

2. REST call: POST /chat/ep-patient/session/1/close?token=...

3. Backend:
   a. DELETE FROM ep_patient_messages WHERE session_id = 1
   b. UPDATE ep_patient_sessions SET status='closed', closed_at=now()
   c. ep_patient_manager.broadcast(1, {"type": "session_closed"})

4. The broadcast reaches patient's STILL-OPEN WebSocket connection:
   Patient's ws.onmessage fires with data.type === 'session_closed'

5. Patient side:
   setEpSessions(prev => prev.filter(s => s.session_id !== 1))  ← helper removed
   setSelectedEpSession(null)                                    ← chat clears
   setEpMessages([])
   ws.close()                                                    ← WS closed

6. EP side (in handleCloseSession after await returns):
   setPatientSession(null)
   setPatientMessages([])
   setSelectedPatient(null)
   getEPPatientsList().then(setPatients)   ← refresh to show active_session_id=null
```

The patient's helper **disappears instantly** — not because of polling, but because the server pushed `session_closed` through the still-open WebSocket.

---

## 11. File Map

```
backend/
  app/
    chat/
      models.py             ← EPPatientSession + EPPatientMessage (DB tables)
      manager.py            ← ChatConnectionManager (the room/channel system)
      ep_patient_router.py  ← All endpoints: REST + WebSocket
    main.py                 ← Registers ep_patient_router with FastAPI

  create_ep_patient_tables.py  ← Migration: creates the two tables in PostgreSQL

frontend/
  src/
    api/
      chat.api.js           ← All HTTP + WebSocket API functions
    pages/
      EPChatPage.jsx        ← EP's "Patients" tab (patient list + chat + close)
      EPChatPage.css        ← Styles for patient sidebar, session header, close btn
      PatientChatPage.jsx   ← Patient's "My Helpers" tab (EP list + chat)
      PatientChatPage.css   ← Styles for helpers layout, tab bar
```

---

## 12. Why Only That EP Appears on Patient Side

The key is `GET /chat/ep-patient/my-sessions`:

```python
sessions = db.query(EPPatientSession).filter(
    EPPatientSession.patient_id == patient.id,
    EPPatientSession.status == "active",   # ← only active sessions
).all()
```

A patient may have 50 EPs in the system, but they will only see the ones with `status = 'active'` sessions **specifically with them**. If EP#3 never opened a session with Patient#7, EP#3 simply never appears in Patient#7's list.

---

## 13. Security Notes

- **Authentication via JWT on every connection**: Both REST and WebSocket endpoints call `decode_access_token(token)` before doing anything.
- **Session ownership enforced**: The backend checks `session.ep_id == td.id` for EPs and `session.patient_id == td.id` for patients. An EP from another therapist cannot enter.
- **Patient isolation**: Patients can only see their own sessions. The query always filters by `patient_id = current_user.id`.
- **No orphan sessions**: Only one active session per EP-Patient pair is possible (the `POST /session/{patient_id}` endpoint checks for an existing active session before creating).
