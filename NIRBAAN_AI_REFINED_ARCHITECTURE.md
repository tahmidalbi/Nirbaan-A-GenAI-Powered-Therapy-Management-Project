# Nirbaan AI — Refined Multi-Agent Architecture

## Critical Review & Revised Pipeline Design

**Date**: February 11, 2026  
**Status**: Refined Plan v2 — Supersedes initial architecture  
**Purpose**: Research-grade redesign for journal publication + undergraduate project

---

## Part A: Honest Assessment of the Idea

### Is this idea noble and publishable?

**Yes — without reservation.** Here is why:

1. **Real clinical gap.** Therapists spend 15–30 minutes before each session reviewing case notes and mentally constructing a session plan. There is no widely adopted tool that automates this from the therapist's own clinical literature. Existing "AI therapy" tools (Woebot, Wysa) target the *patient* side. Almost nothing targets the *therapist's clinical planning workflow* with knowledge-base grounding.

2. **Safety-first framing.** Most AI-in-therapy papers are criticised for hallucination risk. Your design addresses this head-on: every clinical claim must trace back to the therapist's uploaded KB, and anything that cannot be traced is flagged with an uncertainty score. This is a defensible, publishable stance.

3. **Uncertainty quantification is the publication hook.** Per-claim epistemic uncertainty scoring on generated clinical text is an active research frontier. If you can show that your scoring correlates even moderately with expert therapist judgement, that is a Q1-level contribution.

4. **Undergraduate-appropriate scope.** The system is ambitious but decomposable. You can implement the pipeline incrementally and evaluate each agent independently. The evaluation itself (therapist ratings of generated protocols) is straightforward to design.

**What could make it *not* publishable:**
- If the KB is empty or trivial and the system just parrots GPT-4 pretraining — you lose the grounding claim
- If you cannot recruit even 2–3 therapists for a small evaluation study — you lose the validation story
- If you skip the uncertainty scorer and just ship a protocol generator — that is an engineering project, not a research one

**Bottom line:** The idea is strong. The uncertainty scorer is what elevates it from "cool undergrad project" to "publishable research." Protect that component.

---

## Part B: What is Wrong with the Initial Plan

### Problem 1: History and Session Picker run sequentially for no reason

They query different tables (`patient_progress` + `therapist_notes` vs `therapy_sessions`). There is zero data dependency between them. Running them sequentially wastes time and misses a basic LangGraph capability: **parallel node execution**.

**Fix:** Run them as a parallel fan-out. LangGraph supports this natively. The merged output feeds into the next stage.

---

### Problem 2: Raw data is dumped directly into LLM context

History Picker returns raw JSON from the database — week-by-week progress entries, raw therapist notes, the initial condition blob. Session Picker returns full transcripts. Concatenating all of this raw text and passing it to Stage Picker means:
- **Token waste:** You are spending thousands of tokens on verbose, unstructured text
- **Signal dilution:** The important clinical signals (trajectory direction, key breakthroughs, red flags) are buried in noise
- **Worse retrieval:** When Stage Picker builds its KB query from noisy raw data, the embedding quality degrades

**Fix:** Insert a **Context Synthesiser Agent** between the data-fetching stage and the reasoning stage. This agent reads the raw data and produces a focused clinical summary: current symptom severity, trajectory (improving/stagnant/worsening), key events, and therapist priorities. Every downstream agent reads this summary, not the raw data.

This alone will measurably improve protocol quality. It is also independently evaluable (summary quality as a metric).

---

### Problem 3: Stage Picker makes a one-shot irreversible decision

In your initial plan, Stage Picker picks a stage and passes it forward. If it picks wrong, the entire downstream pipeline generates the wrong protocol. There is no self-check.

**Fix:** Add a **self-verification loop** inside Stage Picker. After selecting a stage, the agent retrieves KB material specifically for that stage's entry criteria and compares them against the patient's actual status. If the criteria do not match, it revises its pick. This loop runs a maximum of 2 iterations (pick → verify → revise if needed → verify → accept or escalate to therapist).

This is not just engineering polish — it is a publishable design pattern ("self-reflective stage selection with KB-grounded verification").

---

### Problem 4: The Checker Agent is underspecified

Your initial plan says the Checker Agent "checks whether it needs to ask therapist specific info, if it does it asks therapist the info." This is the right instinct but needs serious architectural thought because it introduces **human-in-the-loop interruption** into the pipeline.

Questions:
- Does the pipeline pause and wait for the therapist to respond? (Yes — it must.)
- What if the therapist does not respond? (Timeout with fallback.)
- Can the Checker ask multiple questions at once? (It should — one round-trip, not a chatbot loop.)
- What kind of questions would it ask? (Specific clinical decisions the KB cannot resolve: "The KB describes two approaches for exposure — flooding vs graduated. Which do you prefer for this patient?")

**Fix:** Rename to **Clarification Agent**. It analyses the blueprint and identifies exactly where the KB is ambiguous or where therapist preference is needed. It bundles all questions into a single structured request. The pipeline uses LangGraph's `interrupt` mechanism to pause, the frontend shows the questions, the therapist answers, and the pipeline resumes. If the therapist does not respond within a configurable timeout, the agent selects the most conservative KB-supported default and flags those decisions.

---

### Problem 5: No revision cycle after uncertainty scoring

In the initial plan, the Uncertainty Scorer runs once and that is the end. But what if the global uncertainty score comes back at 0.35? You are handing the therapist a protocol the system itself does not trust. That is irresponsible.

**Fix:** Add a **conditional revision loop**: if the Uncertainty Scorer returns a global score below a threshold (e.g., 0.50), the pipeline loops back to Protocol Generator with explicit instructions to revise the low-confidence claims. This loop runs a maximum of 1 time (generate → score → revise → re-score → accept). If the score is still low after revision, the protocol is delivered with a prominent warning banner.

This is important for both safety and publication — you can measure whether the revision loop improves calibration.

---

### Problem 6: No contraindication safety check

The pipeline generates a protocol based on what the KB *recommends* for the stage, but never checks whether any recommended intervention *conflicts* with the patient's specific situation — medication interactions, trauma history that contraindicates certain exposure techniques, cultural factors, comorbidities.

**Fix:** Add a **Safety Gate Agent** between Blueprint Generator and Clarification Agent. This agent reviews the blueprint against the patient's conditions, history, and any contraindication information in the KB. If it flags a potential issue, that flag is passed to the Clarification Agent which includes it in the therapist questions ("The KB mentions graduated exposure, but the patient's history includes trauma flashbacks. Do you want to proceed, modify, or skip this component?").

This is a significant safety feature and a strong contribution for the paper.

---

### Problem 7: Session continuity is implicit, not explicit

If a patient has had 5 previous protocols generated, the current generation does not explicitly check whether the new protocol contradicts or unnecessarily repeats a previous one. The only continuity signal comes from the raw session transcripts (last 2), but those are *recordings of what happened*, not *plans of what was intended*.

**Fix:** The History Picker should also retrieve the **last generated protocol** (if any) from the `generated_protocols` table. The Context Synthesiser should include a "previous protocol summary" in its output. This gives downstream agents explicit awareness of what was planned last time.

---

## Part C: The Refined Pipeline

### Overview of Changes from Initial Plan

| # | Initial Plan | Refined Plan | Why |
|---|---|---|---|
| 1 | History Picker → Session Picker (sequential) | History Picker ∥ Session Picker (parallel) | No dependency; saves latency |
| 2 | Raw data passes directly to Stage Picker | New **Context Synthesiser Agent** condenses raw data | Reduces tokens, improves signal, independently evaluable |
| 3 | Stage Picker is one-shot | Stage Picker has **self-verification loop** (max 2 iter) | Catches misclassification before it cascades |
| 4 | No safety check | New **Safety Gate Agent** after blueprint | Contraindication screening, key for clinical safety |
| 5 | Checker Agent (vague) | **Clarification Agent** with structured questions + interrupt + timeout/fallback | Proper human-in-the-loop design |
| 6 | Protocol Generator → Uncertainty Scorer (one-shot) | Uncertainty Scorer has **conditional revision loop** (max 1 iter) | Low-confidence protocols get a second pass |
| 7 | No previous protocol awareness | History Picker also fetches last generated protocol | Explicit session-over-session continuity |
| 8 | 6 agents | 8 agents (+ Context Synthesiser + Safety Gate) | Cleaner separation of concerns |

---

### Refined Graph Topology

```
                         ┌──────────────────┐
                         │    __START__      │
                         │  therapist_id     │
                         │  patient_id       │
                         │  session_focus    │
                         └────────┬─────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │      PARALLEL FAN-OUT      │
                    ▼                            ▼
           ┌────────────────┐          ┌────────────────┐
           │ History Picker  │          │ Session Picker  │
           │ Agent (DB)      │          │ Agent (DB)      │
           │                 │          │                 │
           │ • patient demos │          │ • last 2        │
           │ • progress      │          │   session       │
           │ • therapist     │          │   transcripts   │
           │   notes         │          │                 │
           │ • last protocol │          │                 │
           └────────┬───────┘          └────────┬───────┘
                    │                            │
                    └─────────────┬──────────────┘
                                  │  FAN-IN (merge)
                                  ▼
                       ┌──────────────────┐
                       │ Context           │
                       │ Synthesiser       │
                       │ Agent (LLM)       │
                       │                   │
                       │ Condenses raw     │
                       │ data into focused │
                       │ clinical summary  │
                       └────────┬─────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │                       │
                    │   Stage Picker Agent  │◄──────┐
                    │   (LLM + RAG)        │       │
                    │                       │       │ Self-verification
                    └───────────┬───────────┘       │ loop (max 2 iter)
                                │                   │
                                ▼                   │
                    ┌───────────────────────┐       │
                    │  Stage Verifier       │       │
                    │  (same agent,         │───────┘
                    │   verification pass)  │  if entry criteria
                    │                       │  mismatch → revise
                    └───────────┬───────────┘
                                │
                       ┌────────┴────────┐
                       │  KB sufficient?  │
                       └───┬─────────┬───┘
                      YES  │         │ NO
                           ▼         ▼
              ┌──────────────┐   ┌──────────────┐
              │  Blueprint    │   │    HALT      │
              │  Generator    │   │ Insufficient │
              │  Agent        │   │ KB Info      │
              │  (LLM + RAG)  │   └──────────────┘
              └──────┬───────┘
                     │
            ┌────────┴────────┐
            │  KB sufficient?  │
            └───┬─────────┬───┘
           YES  │         │ NO
                ▼         ▼
     ┌──────────────┐   ┌──────────────┐
     │  Safety Gate  │   │    HALT      │
     │  Agent        │   │ Insufficient │
     │  (LLM + RAG)  │   │ KB Info      │
     │               │   └──────────────┘
     │ Contraind.    │
     │ screening     │
     └──────┬───────┘
            │
            ▼
     ┌──────────────────┐
     │  Clarification    │
     │  Agent            │
     │  (LLM)            │
     │                   │
     │ Analyses gaps,    │
     │ safety flags,     │
     │ & therapist prefs │
     └──────┬───────────┘
            │
            ▼
    ┌───────────────────┐
    │ Has questions for  │
    │ therapist?         │
    └──┬────────────┬───┘
   YES │            │ NO
       ▼            │
┌──────────────┐    │
│  INTERRUPT    │    │
│  (pause,      │    │
│   send Qs to  │    │
│   frontend)   │    │
│              │    │
│  therapist   │    │
│  answers →   │    │
│  resume      │    │
└──────┬───────┘    │
       │            │
       └─────┬──────┘
             │
             ▼
      ┌──────────────┐
      │  Protocol     │
      │  Generator    │
      │  Agent        │
      │  (LLM + RAG)  │
      └──────┬───────┘
             │
        ┌────┴────┐
        │ KB suf? │
        └─┬────┬──┘
     YES  │    │ NO → HALT
          ▼
   ┌──────────────┐
   │  Uncertainty  │◄─────────┐
   │  Scorer       │          │
   │  Agent        │          │ Revision loop
   │  (LLM)        │          │ (max 1 iteration)
   └──────┬───────┘          │
          │                   │
          ▼                   │
   ┌──────────────────┐      │
   │ Global score      │      │
   │ ≥ 0.50?           │      │
   └──┬───────────┬───┘      │
  YES │           │ NO        │
      │           ▼           │
      │    ┌────────────┐     │
      │    │ Protocol    │────┘
      │    │ Reviser     │  feeds revision
      │    │ (same LLM   │  instructions back
      │    │  re-call)    │  to Protocol Gen
      │    └────────────┘
      ▼
   ┌────────────────┐
   │   __END__      │
   │                │
   │ Return:        │
   │ • protocol     │
   │ • uncertainty  │
   │ • sources      │
   │ • audit trail  │
   └────────────────┘
```

---

## Part D: Each Agent in the Refined Pipeline — Detailed Design

---

### Agent 1 & 2: History Picker + Session Picker (Parallel Data Fetch)

**What changed:** These now run in parallel and History Picker additionally retrieves the last generated protocol.

**History Picker collects:**
- Patient demographics and conditions (from `patients`)
- Initial condition and weekly self-reports (from `patient_progress`)
- Therapist week-by-week notes (from `therapist_notes`)
- Therapist's global AI protocol instruction (from `therapist_notes.ai_protocol_instruction`)
- **NEW:** Last generated protocol summary if one exists (from `generated_protocols`)

**Session Picker collects:**
- Last 2 session transcripts ordered by week number (from `therapy_sessions`)

**No LLM calls.** Both are pure database reads. Running in parallel cuts this stage's latency in half.

**Why parallel matters for the paper:** You can report the latency savings as a system optimisation. Even small things like this show engineering maturity in a publication.

---

### Agent 3: Context Synthesiser (NEW)

**This agent did not exist in your initial plan. It is the single most impactful addition.**

**What it does:** Takes the raw data dump from Agents 1 and 2 and produces a structured clinical summary. This summary is what every downstream agent reads — not the raw JSON.

**The clinical summary contains:**

| Section | Content | Why it matters |
|---|---|---|
| **Patient Profile** | Name, conditions, week number — one paragraph | Context anchor for all agents |
| **Symptom Trajectory** | Is the patient improving, stagnant, or worsening? Key inflection points. | Stage Picker uses this to decide direction |
| **Recent Session Themes** | What was attempted in the last 2 sessions? What worked? What did not? | Prevents repetition, ensures continuity |
| **Therapist Priorities** | Extracted from therapist notes + AI instruction field + session focus input | Ensures therapist intent is honoured |
| **Previous Protocol Synopsis** | If a protocol was generated before, one-paragraph summary of what it planned | Explicit continuity signal |
| **Open Concerns** | Any red flags, stagnation signals, or unresolved issues | Safety Gate and Clarification Agent use this |

**Why this matters for publication:** You can evaluate the summarisation quality independently. You can A/B test: pipeline with raw data vs pipeline with synthesised context. If the synthesised path produces better protocols, that is a finding.

**LLM call:** Yes, one call. Temperature 0. The prompt is a summarisation prompt with the six sections above as a required output template. No KB retrieval needed — this agent works purely on the patient's own data.

---

### Agent 4: Stage Picker with Self-Verification Loop

**What changed:** No longer a one-shot decision. Now has an internal verify-and-revise cycle.

**Pass 1 — Selection:**
The agent receives the clinical summary + therapist session focus. It queries the KB for therapy stage definitions, stage progression criteria, and treatment model structures. It proposes a stage.

**Pass 2 — Verification:**
The same agent (second LLM call) receives its own proposed stage and retrieves KB material specifically about the **entry criteria** for that stage. It checks:
- Does the patient's current status match the entry criteria described in the KB?
- Has the patient completed the prerequisites the KB specifies for this stage?
- Does the therapist's explicit session focus align with or override this stage?

If verification fails, the agent revises its stage pick and verifies once more (maximum 2 total iterations). If it still cannot find a well-supported stage, it halts.

**KB search queries:**
- Pass 1 query: condition + week + trajectory + therapist focus → retrieve stage definitions
- Pass 2 query: "entry criteria for {selected_stage}" + "prerequisites for {selected_stage}" → verify match

**Why the loop matters for publication:** You can report the percentage of cases where the verification loop changed the initial pick. If it is non-trivial (say 15–25% of the time), that is evidence the loop is necessary and not just overhead.

---

### Agent 5: Blueprint Generator

**What changed from initial plan:** Mostly the same, but now receives:
- The clinical summary (from Context Synthesiser) instead of raw data
- The verified stage with verification rationale
- Therapist session focus

The blueprint is a **high-level session skeleton**: phases, time blocks, activities, and which KB techniques to use. It does NOT contain detailed scripts — that is the Protocol Generator's job.

**Blueprint structure:**
- 4–6 phases that tile a 60-minute session
- Each phase has: name, time allocation, listed activities, KB technique references
- Materials/worksheets needed
- Homework preview

**KB retrieval:** Queries for session structures and activity descriptions for the selected stage. top_k = 10.

**Halt condition:** Same two-tier check (pre-LLM retrieval threshold + LLM-assessed sufficiency).

---

### Agent 6: Safety Gate (NEW)

**This agent did not exist in your initial plan. It addresses a real clinical safety requirement.**

**What it does:** Reviews the blueprint against the patient's full profile to identify potential contraindications or safety concerns. It queries the KB for contraindication information.

**What it checks:**
- Does any proposed technique conflict with the patient's comorbid conditions?
- Are there trauma-related contraindications for proposed homework?
- Does the progression pace match KB recommendations for the patient's severity level?
- Are there any techniques the therapist has explicitly noted as inappropriate for this patient (in their notes)?

**Output:**
- A list of **safety flags** (potentially 0 if no concerns)
- Each flag: what the concern is, which KB source or patient data raised it, and a suggested modification

**This output feeds into the Clarification Agent.** Safety flags become part of the questions the therapist may need to answer.

**KB retrieval:** Queries for contraindications, cautions, and clinical guidelines related to the selected techniques + patient's conditions. top_k = 6.

**Why this matters for publication:** Clinical safety is the #1 concern reviewers will raise. Having an explicit safety gate — even if it is LLM-based — demonstrates responsible design. You can evaluate it by seeding test cases with known contraindications and measuring detection rate.

---

### Agent 7: Clarification Agent (Refined from "Checker Agent")

**What changed:** Complete redesign from the vague "checker" in the initial plan.

**What it does:** Analyses the blueprint + safety flags and determines whether the pipeline has enough information to proceed, or whether it needs therapist input. It bundles all questions into a single structured request.

**Sources of questions:**
1. **Safety flags** from the Safety Gate — "The KB mentions graduated exposure, but the patient's trauma history may contraindicate this. Proceed, modify, or skip?"
2. **Ambiguous KB guidance** — "The KB describes two approaches for this stage (X and Y). Which do you prefer?"
3. **Missing patient-specific preferences** — "The blueprint includes a mindfulness exercise. Does this patient engage well with mindfulness, or should we substitute?"

**Decision logic:**
- If no questions → proceed directly to Protocol Generator (no interrupt)
- If questions exist → use LangGraph's `interrupt` mechanism to pause the pipeline

**Interrupt mechanism:**
- The pipeline pauses and returns a `NEEDS_CLARIFICATION` response to the frontend
- The frontend renders the questions as a form
- The therapist answers and submits
- The backend resumes the pipeline from the checkpoint with the therapist's answers injected into the state
- The Protocol Generator now has everything it needs

**Timeout/fallback:** If the therapist does not respond within a configurable window (e.g., the interrupt sits for too long and the therapist clicks "Skip — use defaults"), the agent selects the most conservative KB-supported option for each question and flags those decisions in the final protocol as "default selection — therapist did not specify."

**Why the one-round-trip constraint matters:** This is NOT a chatbot. The agent must be smart enough to ask all its questions at once. Multiple back-and-forth rounds would destroy the user experience. One pause, one answer, pipeline resumes.

---

### Agent 8: Protocol Generator

**What changed from initial plan:** Now receives:
- The clinical summary (richer context)
- The verified stage
- The blueprint
- Therapist's clarification answers (if any were needed)
- Safety modifications (if any flags were raised)

**What it produces:** A full 60-minute session protocol with:
- Time-blocked sections (matching the blueprint phases)
- Detailed step-by-step therapist instructions per section
- Verbatim dialogue prompts the therapist can use
- Clinical observation cues ("Watch for...", "If the patient..., then...")
- KB source citations inline
- Post-session summary template
- Risk flags (things that may require the therapist to deviate from protocol)

**KB retrieval strategy:** Performs **per-phase retrieval** — one targeted KB query per blueprint phase, each fetching the 5 most relevant chunks for that specific technique/activity. Chunks are deduplicated across phases. This is the most KB-intensive agent in the pipeline.

**Halt condition:** Same two-tier sufficiency check. If any phase cannot be adequately grounded in the KB, the whole protocol halts rather than generating a half-grounded document.

---

### Agent 9: Uncertainty Scorer with Revision Loop

**What changed from initial plan:** No longer a terminal one-shot. Now has a conditional revision cycle.

**Pass 1 — Scoring:**
The scorer receives the full protocol + all KB chunks used across the pipeline. It produces:
- **Global confidence score** (0.0–1.0): Overall KB-groundedness of the protocol
- **Per-claim scores**: Individual scores for every clinically significant statement
  - Each score includes: the claim text, the confidence value, the supporting KB evidence (or "none"), and a reasoning explanation
- **High-risk flags**: Claims with score < 0.50 that have clinical significance

**Pass 2 — Conditional Revision (if global score < 0.50):**
If the global score is below 0.50, the pipeline does NOT deliver the protocol as-is. Instead:
1. The scorer identifies the weakest claims (those dragging the score down)
2. These are sent back to the Protocol Generator with explicit revision instructions: "Replace or remove the following low-confidence claims: [list]. Ground replacements strictly in these KB chunks: [specific chunks]."
3. The Protocol Generator produces a revised protocol
4. The Uncertainty Scorer re-scores the revision
5. The revised protocol is delivered regardless of the new score, but with a **prominent warning banner** if the score is still below 0.50

**Maximum iterations:** 1 revision cycle. The loop is: Generate → Score → (if low) Revise → Re-Score → Deliver. Never more than 2 scoring passes.

**Why the loop matters for publication:** You can measure:
- How often the revision loop triggers (% of protocols that score < 0.50 initially)
- Whether average confidence improves after revision
- Whether the revision loop changes the actual content meaningfully (semantic diff)

These are all reportable findings.

---

## Part E: Architectural Properties That Make This Publishable

### 1. KB-Grounded Generation with Explicit Refusal

Every agent that generates clinical content (Stages 4, 5, 6, 8) has a hard sufficiency constraint. The system **refuses to generate** rather than hallucinate. This is a direct answer to the most common criticism of clinical AI systems.

**Evaluable claim:** "The system produces zero clinical recommendations that cannot be traced to a specific KB source, or explicitly flags when grounding is insufficient."

### 2. Epistemic Uncertainty Quantification at Two Granularities

Global score + per-claim scores. The v1 implementation uses prompt engineering; v2 (journal target) should add:
- Multi-sample consistency (generate 3 protocol variants, measure agreement)
- NLI-based entailment verification (does KB actually entail the claim?)

**Evaluable claim:** "Per-claim uncertainty scores correlate with expert therapist assessments of claim reliability at r = X."

### 3. Self-Reflective Stage Selection

The verify-and-revise loop on Stage Picker is a form of **LLM self-reflection**. This is an active area of research (Reflexion, Self-Refine, etc.) applied to a clinical domain.

**Evaluable claim:** "The self-verification loop corrected X% of initial stage selections, improving downstream protocol relevance by Y%."

### 4. Human-in-the-Loop Clarification with Graceful Degradation

The Clarification Agent demonstrates a principled approach to the human-AI collaboration boundary: the AI does what it can, identifies where it cannot decide, asks once, and falls back to conservative defaults if the human does not respond.

**Evaluable claim:** "The system identifies and resolves clinical ambiguities through structured therapist consultation, reducing post-generation revision by X%."

### 5. Safety Gate for Contraindication Screening

An explicit agent that checks for clinical safety concerns before protocol generation. This is unusual in generative AI systems and directly addresses reviewer concerns about patient safety.

**Evaluable claim:** "The Safety Gate correctly identified X/Y seeded contraindication scenarios in evaluation."

### 6. Parallel Data Fetching + Context Condensation

These are system-level optimisations but they also have research value: you can report latency improvements (parallel fetch) and protocol quality improvements (synthesised context vs raw data).

---

## Part F: What the Paper Would Look Like

### Suggested Title

*"Knowledge-Grounded Multi-Agent Treatment Protocol Generation with Epistemic Uncertainty Quantification: A LangGraph-Based Architecture for Therapist Decision Support"*

### Core Contributions (for a 4-contribution paper)

1. **System Architecture:** A multi-agent pipeline for therapy session protocol generation that enforces KB grounding at every generative stage, with explicit refusal when evidence is insufficient.

2. **Self-Reflective Stage Selection:** A verify-and-revise mechanism for therapeutic stage classification that improves selection accuracy by re-checking KB entry criteria.

3. **Per-Claim Uncertainty Scoring:** A two-granularity (global + per-claim) epistemic uncertainty annotation system for generated clinical text, providing therapists with calibrated trust signals.

4. **Human-in-the-Loop Safety Design:** A structured clarification mechanism that identifies clinical ambiguities and contraindications, pauses for therapist input, and degrades gracefully to conservative defaults.

### Evaluation Plan

| Evaluation | What It Measures | Method |
|---|---|---|
| **Protocol Quality** | Are generated protocols clinically reasonable? | 2–3 therapists rate 20 protocols on a 5-point Likert scale (relevance, safety, completeness) |
| **Uncertainty Calibration** | Do uncertainty scores match human judgement? | Therapists rate claim confidence independently; compare with system scores (Pearson r) |
| **Stage Selection Accuracy** | Does the system pick the right stage? | Therapists provide ground-truth stage labels for 20 patient scenarios; measure agreement |
| **Safety Gate Recall** | Does the safety gate catch contraindications? | Seed 10 scenarios with known contraindications; measure detection rate |
| **Ablation Study** | Does each agent contribute? | Remove one agent at a time and measure protocol quality change |
| **Latency** | Is the system usable in practice? | Measure end-to-end generation time |

### Target Venues

- **Q1:** Journal of Biomedical Informatics, Artificial Intelligence in Medicine
- **Conferences:** AMIA Annual Symposium, ACM CHI (if framed as HCI), AAAI (if framed as AI safety)
- **Workshops:** NeurIPS Workshop on AI for Science, EMNLP Clinical NLP Workshop

---

## Part G: Summary of the Refined Pipeline

| Step | Agent | Type | Input | Output | Cycles/Loops |
|---|---|---|---|---|---|
| 1a | History Picker | DB only | patient_id, therapist_id | Patient demographics, progress, notes, last protocol | — |
| 1b | Session Picker | DB only | patient_id, therapist_id | Last 2 session transcripts | — |
| 2 | Context Synthesiser | LLM (no RAG) | Raw data from 1a + 1b | Focused clinical summary (6 sections) | — |
| 3 | Stage Picker | LLM + RAG | Clinical summary + session focus | Selected stage + rationale | Self-verification (max 2 iter) |
| 4 | Blueprint Generator | LLM + RAG | Stage + clinical summary | Session blueprint (4–6 phases) | — |
| 5 | Safety Gate | LLM + RAG | Blueprint + patient profile | Safety flags (0 or more) | — |
| 6 | Clarification Agent | LLM | Blueprint + safety flags + gaps | Questions for therapist OR proceed | Human-in-the-loop interrupt (max 1 round) |
| 7 | Protocol Generator | LLM + RAG | Blueprint + clarifications + full context | 60-minute protocol with citations | — |
| 8 | Uncertainty Scorer | LLM | Protocol + all KB chunks used | Global + per-claim scores, annotated protocol | Revision loop if score < 0.50 (max 1 iter) |

**Total agents:** 8 (vs 6 in initial plan)  
**Total LLM calls (typical path, no loops triggered):** 6  
**Total LLM calls (worst case, all loops triggered):** 10  
**Human interrupts:** 0 or 1

---

## Part H: What NOT to Change from the Initial Plan

Some aspects of your initial plan were already correct. Do not over-engineer these:

1. **Per-patient per-therapist isolation** — Your `(therapist_id, patient_id)` scoping model is correct and sufficient. Do not add more complex access control.

2. **KB grounding via existing RAG pipeline** — Your pgvector + cosine similarity setup is production-ready. Do not switch to a different vector DB for the sake of novelty.

3. **Fail-fast on insufficient KB** — Your instinct to halt immediately when the KB cannot support a decision is exactly right. Do not add fallback to GPT-4 pretraining knowledge; that destroys the grounding guarantee.

4. **Storing generated protocols** — Persisting every protocol with full provenance is important for both the clinical use case and for research evaluation. Keep this.

5. **Uncertainty Scorer as a prompt-engineering v1** — This is the right starting point. Ship v1, collect data, then build v2 with proper calibration methods for the journal paper.

---

*This document is the refined architectural plan. The previous architecture document should be treated as superseded.*
