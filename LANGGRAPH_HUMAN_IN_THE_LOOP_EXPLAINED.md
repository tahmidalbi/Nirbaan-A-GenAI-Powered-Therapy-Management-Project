# LangGraph Human-in-the-Loop — Explained Simply

> How the "therapist must review the script" pause works in `graph.py`

---

## The Simple Idea

Imagine you're playing a video game and the game **saves your progress**, then asks you a question.  
You go away, think about it, come back the next day, answer the question, and the game **continues exactly where it left off**.

That's exactly what LangGraph's human-in-the-loop does.

---

## What "interrupt" Actually Does

In your code (`graph.py`, the `therapist_review_node` function):

```python
decision = interrupt({
    "action":           "review_script",
    "generated_script": state["generated_script"],
    "message":          "Therapist must approve or reject this imaginal exposure script.",
    ...
})
```

When Python hits this line, **three things happen instantly**:

1. ✅ **The entire graph state is saved** to PostgreSQL (your checkpoint database).
2. 🛑 **Execution stops** — the function freezes right here.
3. 📤 **`graph.invoke()` returns** back to your router/API as if it finished.

The therapist hasn't done anything yet. The script is just... waiting. Frozen. Safe in the database.

---

## The Two HTTP Requests — The Key to Understanding This

Your system uses **two separate HTTP calls** to complete one full generation:

```
Request 1:  POST /imaginal-generator/start
                 │
                 │  graph runs:  load_case_context
                 │               → build_prompt_node
                 │               → generate_script_node
                 │               → therapist_review_node ← FREEZES HERE
                 │
                 └─ returns: {script_text: "...", interrupt_required: true}
                    (therapist sees the script)

    ... therapist reads the script, decides ...

Request 2:  POST /imaginal-generator/review  {approved: true}
                 │
                 │  graph WAKES UP from exactly where it froze
                 │               → finalize_approved_node
                 │               → END
                 │
                 └─ returns: {audio_path: "...", interrupt_required: false}
```

The graph doesn't start over on Request 2. It **resumes from the frozen point**.

---

## How Does It Know Where to Resume?

The magic is the **`thread_id`**.

```python
# service.py — when starting
thread_id = "imaginal-42-12-5-a3f8c21b"
config = {"configurable": {"thread_id": thread_id}}

graph.invoke(initial_state, config=config)
```

```python
# service.py — when reviewing
config = {"configurable": {"thread_id": "imaginal-42-12-5-a3f8c21b"}}  # SAME id

graph.invoke(Command(resume=decision), config=config)
```

LangGraph uses this `thread_id` as a **key** to look up the saved checkpoint in PostgreSQL.  
It's like a bookmark. When you pass the same bookmark back, it opens to the exact same page.

---

## What `Command(resume=...)` Does

When the therapist clicks Approve or Reject, your frontend sends the decision to the router, which calls:

```python
# service.py
graph.invoke(Command(resume={"approved": True, "feedback": None}), config=config)
```

`Command(resume=...)` is LangGraph's way of saying:

> "Wake up the frozen graph for this thread_id, and give it this answer."

The frozen `interrupt()` call **unpauses** and the value you pass in `resume=` becomes the return value of `interrupt()`:

```python
# graph.py — therapist_review_node
decision = interrupt({...})   # ← this was frozen
# NOW it wakes up and decision = {"approved": True, "feedback": None}

approved = bool(decision.get("approved", False))   # True
```

---

## The Full Picture in Your Code

```
graph.py                          PostgreSQL checkpoint DB
────────────────────────────────  ─────────────────────────────────

load_case_context runs...         checkpoint saved: {run_id:99,
build_prompt_node runs...             obsession:"...",
generate_script_node runs...          generated_script:"...",
                                      version_no:1, ...}
therapist_review_node:
  ┌─ interrupt({...}) ───────────────────────────────────┐
  │  FROZEN                                              │
  │  graph.invoke() returns to router ◄──────────────────┘
  │  router returns HTTP response to browser
  │  therapist reads script...
  │
  │  (time passes — could be seconds, could be hours)
  │
  │  therapist clicks Approve
  │  browser POSTs to /review
  │  graph.invoke(Command(resume={approved:true}))
  │  LangGraph looks up checkpoint by thread_id
  │  restores full state from PostgreSQL
  └─ interrupt() WAKES UP, returns {approved:true}

  decision = {approved: true}
  return Command(goto="finalize_approved_node")

finalize_approved_node runs...
END
```

---

## Why Does the Graph Need a Database?

Because the Python process doesn't remember anything between HTTP requests.

Every time a new HTTP request comes in, it's a fresh function call. There's no variable in memory holding "oh yes, the script for patient 42 is waiting for review."

The PostgreSQL checkpoint stores:
- Every field in `ImaginalGraphState` (obsession, script text, version number, etc.)
- Which node the graph was at when it paused
- The `thread_id` so it can be looked up later

This also means: if your server restarts while a script is waiting for review, **it doesn't get lost**. The therapist can still come back and approve it.

---

## What Happens on Rejection (The Loop)

When the therapist rejects:

```python
# therapist_review_node — after interrupt() wakes up
approved = False
feedback = "Too graphic, needs more focus on fear"

return Command(
    update={
        "approved":           False,
        "therapist_feedback": "Too graphic...",
        "status":             "revising",
    },
    goto="prepare_revision_node",    # ← go HERE next, not finalize
)
```

`Command(update=..., goto=...)` does two things at once:
1. **Updates the state** — adds `therapist_feedback` into the running state dict
2. **Jumps to a specific node** — skips the normal edge routing

Then `prepare_revision_node` increments the version count and the graph follows the edge back to `build_prompt_node` — the loop:

```
prepare_revision_node ──── edge ────► build_prompt_node
                                            │
                                     (therapist_feedback
                                      is now in state,
                                      so it calls
                                      build_revised_prompt)
                                            │
                                       generate_script_node
                                            │
                                       therapist_review_node
                                            │
                                       interrupt() ←── PAUSES AGAIN
```

The graph pauses again, a new script is shown to the therapist, and the whole cycle repeats.

---

## Summary in 5 Lines

1. `interrupt()` **saves state to PostgreSQL** and **freezes the graph**.
2. Your API returns the generated script to the frontend.
3. The therapist reads it and submits a decision.
4. `Command(resume=...)` **wakes the graph up** using the same `thread_id`.
5. The graph continues from exactly where it stopped — no data is lost.

---

## The Two Key Lines to Remember

```python
# This PAUSES the graph and saves everything
decision = interrupt({...})

# This WAKES IT UP and gives it the answer
graph.invoke(Command(resume={"approved": True}), config)
```

Everything else — PostgreSQL checkpoints, thread IDs, state TypedDicts — is just the machinery that makes those two lines work across separate HTTP requests.
