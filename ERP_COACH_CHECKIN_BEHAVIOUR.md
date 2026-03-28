# ERPCoach Auto Check-in Behaviour — Complete Reference

> **Source files covered:**
> `tasks/erp_checkins.py` · `nodes/compute_metrics.py` · `nodes/live_intent_router.py` · `nodes/live_handlers.py` · `prompts/live_handlers.py` · `graph.py` · `core/celery_app.py` · `services/coach_storage.py`

---

## 1. Big Picture

The ERPCoach has two ways it sends messages to a patient:

| Trigger | Path | Who initiates |
|---|---|---|
| **Patient writes a message** | `USER_MESSAGE` event → LLM intent classifier → handler | Patient |
| **Automatic check-in** | `CHECK_IN` event → deterministic router → handler | Celery Beat (background timer) |

This document covers only **automatic check-ins** (the second row), though `USER_MESSAGE` routing is explained in Section 8 for contrast.

---

## 2. The Three-Layer Stack

```
┌────────────────────────────────────────────────────────────────┐
│  Layer 1 — CELERY BEAT (every 60 s)                           │
│  dispatch_due_checkins()                                       │
│  → reads DB, finds sessions whose last_checkin_at is stale    │
│  → enqueues run_checkin(session_id) per due session           │
└────────────────────────────────────────────────────────────────┘
                          ↓ one task per session
┌────────────────────────────────────────────────────────────────┐
│  Layer 2 — CELERY WORKER (run_checkin)                        │
│  → skip if session.status != "running"                        │
│  → stamp last_checkin_at immediately (idempotency lock)       │
│  → call LangGraph with event_type = CHECK_IN                  │
│  → if result is NO_MESSAGE: return silently                   │
│  → else: graph already persisted message, return summary      │
└────────────────────────────────────────────────────────────────┘
                          ↓ LangGraph invoked
┌────────────────────────────────────────────────────────────────┐
│  Layer 3 — LANGGRAPH (ERPCoach graph)                         │
│  load_context → compute_metrics → mode_router(LIVE)           │
│  → log_user (no-op for CHECK_IN) → live_intent_router        │
│  → handler node → finalize → log_coach → END                  │
└────────────────────────────────────────────────────────────────┘
```

---

## 3. Timing Constants

All values are set in the code. "Dev" = current values with TODO comments to restore "Prod" values before production.

| Constant | Dev value | Prod value | Where set | What it controls |
|---|---|---|---|---|
| `CHECKIN_SECONDS` | **120 s (2 min)** | 300 s (5 min) | `erp_checkins.py` line 17 | How often `dispatch_due_checkins` considers a session stale for a new check-in wave |
| `reminder_seconds` | **120 s (2 min)** | 300 s (5 min) | `compute_metrics.py` line 37 | How long without a SUDS rating before `rate_reminder_flag` flips True |
| `cooldown_seconds` | **60 s (1 min)** | 60 s (1 min) | `compute_metrics.py` line 38 | Minimum gap between any two real coach messages (prevents spam) |
| `engagement_window` | **300 s (5 min)** | 300 s (5 min) | `compute_metrics.py` line 42 | If the patient sent a message or rated SUDS within this window, they are considered "recently engaged" and non-spike check-ins are suppressed |
| `spike_delta_threshold` | **15 SUDS points** | 15 points | `compute_metrics.py` line 39 | A single jump of ≥15 SUDS points triggers a spike |
| `spike_slope_threshold` | **8.0 SUDS/min** | 8.0/min | `compute_metrics.py` line 40 | If the overall SUDS slope across the session is ≥8 per minute, that also triggers a spike |
| Beat schedule | **every 1 min** | every 1 min | `celery_app.py` beat_schedule | How often `dispatch_due_checkins` runs |

---

## 4. Database Timestamps Tracked

The entire timing logic relies on four timestamps stored per session in the `erp_live_sessions` table:

| Column | Updated when | Used for |
|---|---|---|
| `last_checkin_at` | At the **start** of every `run_checkin` call, even if NO_MESSAGE is returned | Prevents `dispatch_due_checkins` from re-dispatching the same session again within `CHECKIN_SECONDS` |
| `last_agent_run_at` | Only when a **real coach message** is saved (NOT for NO_MESSAGE) | Drives `cooldown_ok` — prevents spamming the patient |
| `last_suds_at` | When patient submits a SUDS rating | Drives `rate_reminder_flag` and `recently_engaged` |
| `last_spike_notified_suds` | When a spike message is sent, saves the SUDS value that triggered it | Spike de-duplication — avoids re-alerting at the same SUDS level |

> **Key distinction**: `last_checkin_at` prevents duplicate *dispatch* (system-level lock). `last_agent_run_at` prevents duplicate *messages* (clinical-level cooldown). They are updated independently.

---

## 5. What Happens When `dispatch_due_checkins` Runs

Every minute, Celery Beat fires `dispatch_due_checkins`. It runs this SQL logic:

```sql
SELECT id FROM erp_live_sessions
WHERE status = 'running'
  AND (last_checkin_at IS NULL OR last_checkin_at <= NOW() - INTERVAL '120 seconds')
ORDER BY created_at ASC
LIMIT 500;
```

For each returned session, it calls `run_checkin.delay(session_id)` asynchronously.

---

## 6. What Happens Inside `run_checkin`

```
run_checkin(session_id)
  │
  ├─ Load ERPLiveSession from DB
  │
  ├─ session.status != "running"?
  │    └─ YES → return {"skipped": True, "reason": "status=completed/paused"}
  │
  ├─ UPDATE last_checkin_at = NOW()   ← idempotency stamp (fires even for NO_MESSAGE)
  │
  ├─ invoke_erp_coach({ session_id, event_type="CHECK_IN", user_message="" })
  │                         │
  │                    LANGGRAPH runs (see Section 7)
  │                         │
  │             ┌───────────┴───────────┐
  │          NO_MESSAGE              REAL message
  │             │                        │
  │    return silently           (graph already persisted it)
  │    last_agent_run_at          last_agent_run_at was updated
  │    NOT updated                inside log_coach node
  │
  └─ return {"ok": True, "type": "NO_MESSAGE" or "COACH_MESSAGE"}
```

---

## 7. LangGraph Flow for CHECK_IN

```
START
  │
  ▼
load_context          ← loads session, SUDS readings, chat transcript, prior summaries
  │
  ▼
compute_metrics       ← calculates all routing signals (see Section 7.1)
  │
  ▼
mode_router           ← CHECK_IN is always "LIVE" (never DEBRIEF_PROMPT or REPORT)
  │ "LIVE"
  ▼
log_user              ← no-op for CHECK_IN (user_message is empty string "")
  │
  ▼
live_intent_router    ← DETERMINISTIC routing for CHECK_IN (see Section 7.2)
  │
  ├─ "SUDS_SPIKE"      → live_spike      → handle_suds_spike()   [LLM]
  ├─ "RATE_REMINDER"   → live_rate_reminder → handle_rate_reminder() [LLM]
  ├─ "NO_MESSAGE"      → live_no_message → handle_no_message()   [no LLM — static]
  │   (also: GENERAL / REASSURANCE_BLOCK / COMPULSION_URGE / AVOIDANCE_QUIT
  │          only reachable from USER_MESSAGE, never from CHECK_IN)
  │
  ▼
finalize_coach_live   ← shapes coach_response_json
  │
  ▼
log_coach             ← persists message to DB + updates last_agent_run_at
                         (skips persist if type == NO_MESSAGE)
  │
  ▼
END
```

### 7.1 Signals Computed by `compute_metrics`

| Signal | How computed | Meaning |
|---|---|---|
| `since_last_suds` | `now - last_suds_at` in seconds (None if never rated) | Age of the last SUDS button press |
| `since_last_patient_msg` | `now - last_patient_message_at` in seconds | Age of last patient chat message |
| `recently_engaged` | `since_last_patient_msg < 300` OR `since_last_suds < 300` | Patient interacted (chat or SUDS) within 5 minutes |
| `rate_reminder_flag` | If no SUDS: `elapsed_seconds >= 120`. If SUDS exists: `since_last_suds >= 120` | SUDS rating is stale — coach should ask for one |
| `cooldown_ok` | `since_last_agent_run >= 60` (or never sent) | Safe gap between coach messages |
| `suds_delta` | `latest_suds - previous_suds` | How much SUDS changed since last reading |
| `suds_slope_per_min` | `(latest - first_suds) / elapsed_minutes_between_them` | Overall rate of SUDS rise across the session |
| `raw_spike` | `suds_delta >= 15` OR `slope_per_min >= 8.0` | A genuine large/fast SUDS rise detected |
| `spike_flag` | `raw_spike AND (last_spike_notified_suds is None OR suds_latest > last_spike_notified_suds)` | A spike that hasn't been notified yet at this level |

### 7.2 CHECK_IN Routing — Priority Order (fully deterministic, no LLM)

```
live_intent_router (event_type == CHECK_IN):

  1. spike_flag == True AND cooldown_ok == True
     → SUDS_SPIKE
        Reason: Clinically urgent. Fires even if patient is engaged.
        Only blocked by cooldown (prevents spam),
        but NOT blocked by recently_engaged.

  2. recently_engaged == True
     → NO_MESSAGE
        Reason: Patient is actively participating (chat or SUDS within 5 min).
        Interrupting would be disruptive.

  3. cooldown_ok == False
     → NO_MESSAGE
        Reason: A real coach message was sent <60 seconds ago.
        Anti-spam guard.

  4. rate_reminder_flag == True
     → RATE_REMINDER
        Reason: Patient is idle AND hasn't rated SUDS for >= 2 min.
        Safe time to ask for a rating.

  5. (none of the above)
     → NO_MESSAGE
        Reason: Patient is idle but SUDS is still recent enough.
        Nothing useful to send.
```

---

## 8. What Each Check-in Type Sends

### 8.1 `SUDS_SPIKE` — Emergency Stability Message

**When**: Raw SUDS jump ≥15 points OR slope ≥8/min AND this level hasn't been notified yet AND cooldown OK.

**Prompt recipe**:
- Normalize the spike ("spikes are part of ERP working")
- ONE grounding cue (not to reduce anxiety, just to stay present)
- ONE response-prevention action (keep going, don't escape)
- At most ONE question; usually none
- 2–5 short sentences

**Output tags**: `["suds_spike"]`
**`next_action`**: `CONTINUE` or `DELAY_COMPULSION` or `RATE_SUDS_NOW`

**After sending**: `last_agent_run_at` updated, `last_spike_notified_suds` = current SUDS value (de-duplication stored).

---

### 8.2 `RATE_REMINDER` — SUDS Rating Request

**When**: Patient idle (not engaged in last 5 min) AND no SUDS for ≥2 min AND cooldown OK.

**Prompt recipe**:
- Warm one-liner about WHY tracking matters
- Ask for SUDS 0–100
- Fallback option: "low / medium / high" or "5-word description"
- 1–3 short sentences total

**Output tags**: `["rate_reminder"]`
**`next_action`**: `RATE_SUDS_NOW`

**In the prompt**: includes a time hint such as `"Last rating was 3.2m ago."` or `"No rating yet in 240 seconds."`

---

### 8.3 `NO_MESSAGE` — Silent (Nothing Sent)

**When**: Any case where a message is suppressed (patient active, cooldown active, nothing urgent).

**No LLM call**. Returns a static object:
```json
{
  "type": "NO_MESSAGE",
  "source": "CHECK_IN",
  "coach_message": null,
  "next_action": { "type": "NONE", "payload": {} },
  "tags": ["cooldown_no_message"]
}
```

**`last_checkin_at`** is still updated (system-level lock).
**`last_agent_run_at`** is NOT updated (cooldown is not reset).
**Nothing** is written to `erp_chat_messages`.

---

### 8.4 `GENERAL` (CHECK_IN variant) — Dead Path in Current Routing

The `handle_general` node calls `prompt_checkin_general` when `event_type == CHECK_IN`. However, `live_intent_router` currently never routes CHECK_IN to GENERAL — it always lands on SUDS_SPIKE, RATE_REMINDER, or NO_MESSAGE. This handler is ready but currently unreachable from CHECK_IN (it is reachable from USER_MESSAGE where it uses `prompt_general_coaching` instead).

---

## 9. Contrast: USER_MESSAGE Routing (patient-triggered, not auto)

When a patient sends a message, the same LangGraph runs but with `event_type = USER_MESSAGE`. The routing is **LLM-based** (not deterministic):

```
live_intent_router (event_type == USER_MESSAGE):
  → call LLM structured classifier (router_prompt.py)
  → REASSURANCE   → REASSURANCE_BLOCK  (blocks certainty-seeking)
  → COMPULSION_URGE → COMPULSION_URGE (urge surfing + RP plan)
  → AVOIDANCE_QUIT  → AVOIDANCE_QUIT  (gentle push or real choice)
  → GENERAL         → GENERAL         (default coaching)
```

KEY DIFFERENCE: USER_MESSAGE always results in a coach reply (no NO_MESSAGE possible). It also updates `last_patient_message_at`, which resets the `recently_engaged` signal for 5 minutes, suppressing subsequent auto check-ins.

---

## 10. Complete Real-World Timeline Example

**Scenario**: Patient *Aisha* running a contamination OCD exposure session. She reads a script about touching a dirty doorknob. No therapist is online. All times are UTC.

**Parameters**:
- `CHECKIN_SECONDS = 120` (dispatch window)
- `reminder_seconds = 120` (SUDS idle threshold)
- `cooldown_seconds = 60`
- `engagement_window = 300` (5 min)
- `spike_delta_threshold = 15`

---

### Session starts at **10:00:00**

| DB column | Value |
|---|---|
| `status` | `running` |
| `last_checkin_at` | `NULL` |
| `last_agent_run_at` | `NULL` |
| `last_suds_at` | `NULL` |
| `last_spike_notified_suds` | `NULL` |

---

### **10:01:00** — Beat tick #1

```
cutoff = 10:01:00 − 120s = 09:59:00
last_checkin_at = NULL → IS NULL → DUE ✅
```

`run_checkin` fires at **10:01:03**

| Computation | Value |
|---|---|
| `last_checkin_at` stamped | 10:01:03 |
| `elapsed_seconds` | 63 s |
| `since_last_suds` | None (never rated) |
| `rate_reminder_flag` | `63 >= 120` → **False** |
| `since_last_patient_msg` | None |
| `recently_engaged` | False OR False = **False** |
| `since_last_agent` | None (never sent) |
| `cooldown_ok` | **True** |
| `spike_flag` | No SUDS → **False** |

**Router decision**: spike=F, engaged=F, cooldown=T, reminder=F → **NO_MESSAGE** ✅

**Result**: Nothing sent. `last_agent_run_at` NOT updated.

---

### **10:02:00** — Beat tick #2
```
cutoff = 10:00:00
last_checkin_at = 10:01:03 > 10:00:00 → NOT DUE ❌
```
Session skipped entirely.

---

### **10:03:00** — Beat tick #3
```
cutoff = 10:01:00
last_checkin_at = 10:01:03 > 10:01:00 → NOT DUE ❌
```
Session skipped.

---

### **10:04:00** — Beat tick #4
```
cutoff = 10:02:00
last_checkin_at = 10:01:03 ≤ 10:02:00 → DUE ✅
```

`run_checkin` fires at **10:04:02**

| Computation | Value |
|---|---|
| `last_checkin_at` stamped | 10:04:02 |
| `elapsed_seconds` | 242 s (≈ 4 min) |
| `since_last_suds` | None |
| `rate_reminder_flag` | `elapsed=242 >= 120` → **True** |
| `recently_engaged` | False |
| `cooldown_ok` | **True** (no prior message) |
| `spike_flag` | No SUDS → **False** |

**Router decision**: spike=F, engaged=F, cooldown=T, **reminder=T** → **RATE_REMINDER** 📊

**Prompt sent to LLM**:
> *"No rating yet in 242 seconds."*
> + base context (obsession, compulsions, transcript)
> + instruction: 1–3 sentences, ask SUDS 0–100, offer "low/medium/high" fallback

**LLM-generated coach message** (example):
> *"You've been in it for about 4 minutes — can you give me a SUDS number from 0 to 100?
> If numbers feel off, even just 'low', 'medium', or 'high' is helpful."*

**Persisted**: ✅ Message saved to `erp_chat_messages`
**`last_agent_run_at`** ← **10:04:05**

---

### **10:04:30** — Aisha rates SUDS = 65

| DB column | Value |
|---|---|
| `last_suds_at` | 10:04:30 |
| `suds_stats` | latest=65, previous=None, delta=None |

---

### **10:05:00** — Aisha sends: *"What if the contamination actually spreads to my family?"*

This is a **USER_MESSAGE** (not a check-in). LLM classifier identifies intent as **REASSURANCE** (seeking certainty about the feared outcome).

**Route**: `REASSURANCE_BLOCK`

**LLM-generated coach message** (example):
> *"OCD wants a guaranteed answer right now — and I can't give you one, and that's exactly the point. Maybe it will, maybe it won't — that's the uncertainty you're sitting with. Instead of chasing the answer, stay with the script for one more paragraph."*

**Persisted**: ✅
**`last_agent_run_at`** ← **10:05:04**
**`last_patient_message_at`** ← **10:05:00**

---

### **10:05:00 and 10:06:00** — Beat ticks #5 and #6

```
Beat #5 → cutoff = 10:03:00, last_checkin_at = 10:04:02 > 10:03:00 → NOT DUE ❌
Beat #6 → cutoff = 10:04:00, last_checkin_at = 10:04:02 > 10:04:00 → NOT DUE ❌
```

---

### **10:07:00** — Beat tick #7
```
cutoff = 10:05:00
last_checkin_at = 10:04:02 ≤ 10:05:00 → DUE ✅
```

`run_checkin` fires at **10:07:04**

| Computation | Value |
|---|---|
| `last_checkin_at` stamped | 10:07:04 |
| `elapsed_seconds` | 424 s |
| `since_last_suds` | 10:07:04 − 10:04:30 = **154 s** |
| `rate_reminder_flag` | `154 >= 120` → True |
| `since_last_patient_msg` | 10:07:04 − 10:05:00 = **124 s < 300** → engagement active |
| `recently_engaged` | True (patient messaged 2 min ago) |
| `since_last_agent` | 10:07:04 − 10:05:04 = 120 s > 60 → `cooldown_ok=True` |
| `spike_flag` | No new SUDS since 65, delta=None → **False** |

**Router decision**: spike=F, **engaged=True** → **NO_MESSAGE** 🔇

**Reason**: Even though SUDS reminder is due, Aisha sent a message just 2 minutes ago — she is actively engaged. Suppressing to avoid interrupting.

**Result**: Nothing sent. `last_agent_run_at` NOT updated.

---

### **10:08:30** — Aisha rates SUDS = 85

| DB column | Value |
|---|---|
| `last_suds_at` | 10:08:30 |
| `suds_stats` | latest=85, previous=65, **delta=20**, slope=(85−65)/[(long session elapsed calculation)] |

**Spike calculation**:
- `delta = 20 >= 15` → `raw_spike = True`
- `last_spike_notified_suds = None` → first time → `spike_flag = True`

---

### **10:08:00 and 10:09:00** — Beat ticks #8 and #9

```
Beat #8 → cutoff = 10:06:00, last_checkin_at = 10:07:04 > 10:06:00 → NOT DUE ❌
Beat #9 → cutoff = 10:07:00, last_checkin_at = 10:07:04 > 10:07:00 → NOT DUE ❌
```

---

### **10:10:00** — Beat tick #10
```
cutoff = 10:08:00
last_checkin_at = 10:07:04 ≤ 10:08:00 → DUE ✅
```

`run_checkin` fires at **10:10:02**

| Computation | Value |
|---|---|
| `last_checkin_at` stamped | 10:10:02 |
| `elapsed_seconds` | 602 s (≈ 10 min) |
| `since_last_suds` | 10:10:02 − 10:08:30 = **92 s** |
| `rate_reminder_flag` | `92 >= 120` → **False** (SUDS recent) |
| `since_last_patient_msg` | 10:10:02 − 10:05:00 = **302 s > 300** → expired |
| `since_last_suds` | 92 s < 300 → engagement via SUDS still active |
| `recently_engaged` | False OR **True** = **True** (SUDS 92 s ago) |
| `since_last_agent` | 10:10:02 − 10:05:04 = **298 s > 60** → `cooldown_ok = True` |
| `spike_flag` | delta=20 >= 15, last_notified=None → **True** |

**Router decision**: **spike=True AND cooldown=True** → **SUDS_SPIKE** 🚨

*Even though `recently_engaged = True`, the spike bypasses the engagement suppression. Clinical urgency takes priority.*

**Prompt sent to LLM**:
> *suds_latest=85, suds_peak=85, suds_trend_hint="rising (delta=20)"*
> + instruction: normalize spike, ground, RP action, no reassurance

**LLM-generated coach message** (example):
> *"That jump is the exposure doing its work — a spike like this is normal, not a sign something's wrong.
> Let it crest without escaping the thought. Take one slow breath and stay with the uncertainty for just a bit longer.
> Give me a rating when it shifts at all."*

**Persisted**: ✅ Message saved
**`last_agent_run_at`** ← **10:10:06**
**`last_spike_notified_suds`** ← **85** (de-duplication stored)

---

### **10:11:00** — Aisha rates SUDS = 88

| DB column | Value |
|---|---|
| `last_suds_at` | 10:11:00 |
| `suds_stats` | latest=88, previous=85, delta=3 |

**Spike check**:
- `delta = 3 < 15` → `raw_spike = False`
- `suds_latest=88 > last_spike_notified_suds=85` but `raw_spike=False` → `spike_flag = False`
- Even if raw_spike were True: suds_latest (88) > last_notified (85) → would allow a new spike
- But delta=3 is not enough → no spike fires

---

### **10:10:00–10:15:00** — Beat ticks (no more due checks)

```
Beat #11 10:11:00 → cutoff=10:09:00, last_checkin_at=10:10:02 > 10:09:00 → NOT DUE ❌
Beat #12 10:12:00 → cutoff=10:10:00, last_checkin_at=10:10:02 > 10:10:00 → NOT DUE ❌
Beat #13 10:13:00 → cutoff=10:11:00, last_checkin_at=10:10:02 ≤ 10:11:00 → DUE ✅
```

`run_checkin` fires at **10:13:02**

| Computation | Value |
|---|---|
| `since_last_suds` | 10:13:02 − 10:11:00 = **122 s** |
| `rate_reminder_flag` | `122 >= 120` → **True** (barely) |
| `since_last_patient_msg` | 10:13:02 − 10:05:00 = **482 s > 300** → expired |
| `since_last_suds` | 122 s < 300 → engagement via SUDS still active |
| `recently_engaged` | **True** (SUDS 2 min ago) |
| `cooldown_ok` | 10:13:02 − 10:10:06 = 176 s > 60 → **True** |
| `spike_flag` | delta=3 < 15 → **False** |

**Router decision**: spike=F, **engaged=True** → **NO_MESSAGE** 🔇

Aisha rated SUDS only 2 minutes ago — still in the engagement window. Reminder suppressed.

---

### **10:16:00** — Beat tick #16
```
cutoff = 10:14:00
last_checkin_at = 10:13:02 ≤ 10:14:00 → DUE ✅
```

`run_checkin` fires at **10:16:02**

| Computation | Value |
|---|---|
| `since_last_suds` | 10:16:02 − 10:11:00 = **302 s** |
| `rate_reminder_flag` | `302 >= 120` → **True** |
| `since_last_patient_msg` | 682 s > 300 → **expired** |
| `since_last_suds` | 302 s > 300 → **expired** |
| `recently_engaged` | False AND False = **False** |
| `cooldown_ok` | 10:16:02 − 10:10:06 = 356 s > 60 → **True** |
| `spike_flag` | **False** |

**Router decision**: spike=F, engaged=F, cooldown=T, **reminder=T** → **RATE_REMINDER** 📊

**Prompt time hint**:
> *"Last rating was 5.0m ago."*

**LLM-generated coach message** (example):
> *"It's been about 5 minutes since your last number. Where would you put it now — 0 to 100?
> Or just 'higher', 'lower', or 'same' is fine."*

**Persisted**: ✅
**`last_agent_run_at`** ← **10:16:05**

---

## 11. Full Timeline Summary

```
10:00:00  Session starts
10:01:03  run_checkin → NO_MESSAGE  (session too young, reminder not yet due)
10:04:02  run_checkin → RATE_REMINDER  (4 min elapsed, patient idle, no SUDS)
10:04:30  Patient rates SUDS=65
10:05:00  Patient sends message → USER_MESSAGE/REASSURANCE_BLOCK  (not auto)
10:07:04  run_checkin → NO_MESSAGE  (patient messaged 2 min ago, engaged)
10:08:30  Patient rates SUDS=85 (delta=+20, spike_flag=True)
10:10:02  run_checkin → SUDS_SPIKE  (spike bypasses engagement, clinically urgent)
10:11:00  Patient rates SUDS=88 (delta=+3, no new spike)
10:13:02  run_checkin → NO_MESSAGE  (SUDS rated 2 min ago, still engaged)
10:16:02  run_checkin → RATE_REMINDER  (both engagement signals expired >5 min)
```

---

## 12. Spike De-duplication Logic

The system prevents the same spike being announced multiple times:

```python
# Only fire if SUDS climbed higher than last notification level
if raw_spike:
    if last_spike_notified_suds is None:
        spike_flag = True          # first ever spike → allow
    elif suds_latest > last_spike_notified_suds:
        spike_flag = True          # climbed to new height → allow
    else:
        spike_flag = False         # same or lower SUDS → suppress
```

**Example**:
- SUDS = 85 → spike fires, `last_spike_notified_suds` = 85
- SUDS = 83 → delta=-2, raw_spike=False → no spike (falling)
- SUDS = 88 → delta=+3 < 15 → raw_spike=False → no spike (delta too small)
- SUDS = 95 → delta=+12... if slope triggers raw_spike, AND 95 > 85 → **new spike fires**
             → `last_spike_notified_suds` = 95

---

## 13. Common Scenarios Summary

| Patient state | Spike? | Engaged? | Cooldown OK? | Reminder due? | Result |
|---|---|---|---|---|---|
| Session brand new, 0 activity | No | No | Yes | No | NO_MESSAGE |
| Idle 4+ min, no SUDS yet | No | No | Yes | **Yes** | RATE_REMINDER |
| Just sent a message (< 5 min) | No | **Yes** | Yes | Yes | NO_MESSAGE |
| Just rated SUDS (< 5 min) | No | **Yes** | Yes | Yes | NO_MESSAGE |
| SUDS jumped +20, idle patient | **Yes** | No | Yes | Any | SUDS_SPIKE |
| SUDS jumped +20, active patient | **Yes** | Yes | Yes | Any | SUDS_SPIKE (spike overrides) |
| SUDS jumped +20, cooldown < 60s | **Yes** | Any | **No** | Any | NO_MESSAGE (spike blocked by cooldown) |
| Coach just messaged 30s ago | No | No | **No** | Yes | NO_MESSAGE |
| Patient idle >5 min, SUDS stale | No | No | Yes | **Yes** | RATE_REMINDER |
| Patient idle >5 min, SUDS recent | No | No | Yes | No | NO_MESSAGE |

---

## 14. Production vs Development Differences

In production (when TODOs in the code are resolved):

| Behaviour | Dev (current) | Prod |
|---|---|---|
| Check-in dispatch window | Every **2 min** (sessions get a tick wave every 2 min) | Every **5 min** |
| SUDS idle threshold for reminder | **2 min** without rating | **5 min** without rating |
| Cooldown between messages | **1 min** (same) | **1 min** (same) |
| Engagement suppression window | **5 min** (same) | **5 min** (same) |
| Spike thresholds | **15 points / 8/min** (same) | **15 points / 8/min** (same) |

In dev, the system is more aggressive to allow easier testing without waiting real ERP session lengths (usually 20–45 min).

---

## 15. What the Coach Never Does (Hardcoded Rules in Prompts)

Regardless of which check-in type fires, the LLM is always instructed:

- **No reassurance**: Never confirm safety, disprove the fear, or say "you'll be fine"
- **No compulsion help**: Never encourage checking, washing, googling, confessing, or any neutralizing behavior
- **No robot template**: Never use "Next step:" or an identical opener every message
- **Ask at most ONE question per message** (often zero)
- **Variety guard**: Scans transcript — if the last 2 coach turns already asked for SUDS, does NOT ask again; if both last turns ended in a question, this turn must end without one
- **2–5 sentences max** for check-in messages
