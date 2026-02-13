# Safety Gate Agent - Implementation Guide

## Overview

**Agent 5: Safety Gate** is a critical safety layer that did not exist in the initial architecture. It screens proposed therapy session blueprints for contraindications and safety concerns before detailed protocol generation.

---

## Why This Agent Matters

### Clinical Safety is #1 Reviewer Concern

Most AI-in-therapy papers are criticized for hallucination risk and lack of safety mechanisms. The Safety Gate demonstrates:

1. **Responsible AI design** - explicit safety checking layer
2. **Proactive risk mitigation** - catches concerns before they become protocol recommendations
3. **KB-grounded safety** - queries therapist's own safety guidelines
4. **Evaluable contribution** - can measure contraindication detection rate

### Publication Value

**Evaluable Claim:** "The Safety Gate correctly identified X/Y seeded contraindication scenarios in evaluation with Y% recall rate."

This addresses reviewer concerns head-on and provides measurable safety metrics.

---

## How It Works

### Input (from earlier agents)

```python
# From Agent 4 (Blueprint Generator)
blueprint = {
    "phases": [...],  # 4-6 session phases
    "techniques": [...],  # KB-grounded techniques
    "materials_needed": [...],
    "homework_preview": "..."
}

# From Agent 2 (Context Synthesiser)
clinical_summary = "6-section patient summary"

# From patient data
patient_conditions = "OCD, ADHD, PTSD"

# Optional: from therapist notes
therapist_notes_summary = "Therapist concerns and restrictions"
```

### Processing

```
┌────────────────────────────────────┐
│  1. Query KB for Safety Info      │
│     Query: contraindications +     │
│            techniques + conditions │
│     top_k: 6 chunks                │
└────────────────┬───────────────────┘
                 │
                 ▼
┌────────────────────────────────────┐
│  2. LLM Safety Screening           │
│     Reviews blueprint vs:          │
│     - Patient conditions           │
│     - Trauma history               │
│     - Therapist restrictions       │
│     - KB contraindications         │
└────────────────┬───────────────────┘
                 │
                 ▼
┌────────────────────────────────────┐
│  3. Generate Safety Flags          │
│     Each flag:                     │
│     - Severity (high/med/low)      │
│     - Concern type                 │
│     - Affected component           │
│     - Evidence source              │
│     - Suggested modification       │
│     - Requires therapist decision? │
└────────────────┬───────────────────┘
                 │
                 ▼
┌────────────────────────────────────┐
│  4. Overall Risk Assessment        │
│     - Risk level: safe/caution/high│
│     - Recommendation: proceed/     │
│       modify/review                │
└────────────────────────────────────┘
```

### Output (to Clarification Agent)

```python
{
    "status": "success",
    "safety_flags": [
        {
            "severity": "high",
            "concern_type": "trauma",
            "concern_description": "Proposed exposure may trigger dissociation given trauma history",
            "affected_blueprint_component": "Phase 2: Exposure Exercise",
            "kb_evidence": "Trauma-Informed ERP Guidelines (similarity: 0.78)",
            "suggested_modification": "Start with imaginal exposure before in-vivo",
            "requires_therapist_decision": true
        }
    ],
    "overall_risk_level": "caution",
    "proceed_recommendation": "proceed_with_modifications",
    "screening_notes": "Patient has recent trauma activation. Recommend slower exposure progression."
}
```

---

## The 6 Safety Checks

### 1. Comorbidity Conflicts

**What it checks:** Do proposed techniques conflict with patient's comorbid conditions?

**Examples:**
- Prolonged exposure contraindicated for active psychosis
- Certain mindfulness exercises problematic for dissociative disorders
- High-intensity exposure risky with severe depression

**Flag example:**
```json
{
    "severity": "high",
    "concern_type": "comorbidity",
    "concern_description": "Patient has comorbid dissociative symptoms. Prolonged exposure at SUDS 9/10 may trigger dissociation.",
    "affected_blueprint_component": "Phase 2: Flooding Exposure",
    "suggested_modification": "Use graduated exposure with SUDS ceiling at 7/10"
}
```

### 2. Trauma-Related Contraindications

**What it checks:** Could techniques cause re-traumatization or trauma activation?

**Examples:**
- Exposure pacing too aggressive for trauma history
- Techniques that may trigger flashbacks
- Activities that mirror traumatic events

**Flag example:**
```json
{
    "severity": "high",
    "concern_type": "trauma",
    "concern_description": "Blueprint includes car-related exposure. Patient's trauma involved car accident.",
    "kb_evidence": "Trauma-Focused CBT Guidelines",
    "suggested_modification": "Postpone car-related exposure until later stage. Start with less triggering exposures."
}
```

### 3. Progression Pace

**What it checks:** Is the proposed pace appropriate for patient's current functioning?

**Examples:**
- Too fast for patient's current symptom severity
- Skipping necessary foundational work
- Not matching KB progression recommendations

**Flag example:**
```json
{
    "severity": "medium",
    "concern_type": "pace",
    "concern_description": "Patient at Week 3. KB recommends psychoeducation phase until Week 5 before exposure.",
    "kb_evidence": "OCD Treatment Protocol - Stage Progression",
    "suggested_modification": "Continue psychoeducation. Delay exposure exercises."
}
```

### 4. Therapist Restrictions

**What it checks:** Has therapist explicitly noted certain approaches as inappropriate?

**Examples:**
- "Do not use flooding with this patient"
- "Patient prefers cognitive approaches over exposure"
- "Avoid mindfulness due to past negative experience"

**Flag example:**
```json
{
    "severity": "high",
    "concern_type": "therapist_restriction",
    "concern_description": "Therapist notes from Week 5: 'Patient had panic attack during prolonged exposure. Use short exposures only.'",
    "kb_evidence": "patient_data",
    "suggested_modification": "Limit exposure duration to 5-10 minutes maximum."
}
```

### 5. Medication Interactions

**What it checks:** Do techniques interact with patient's medications?

**Examples:**
- Relaxation exercises with sedative medications
- High-arousal exposures with stimulant medications
- Timing conflicts with medication schedules

**Flag example:**
```json
{
    "severity": "medium",
    "concern_type": "medication",
    "concern_description": "Patient on SSRIs. Blueprint schedules exposure during typical SSRI peak (2-3 hours post-dose). May amplify anxiety.",
    "suggested_modification": "Schedule exposure exercises before SSRI dose or 6+ hours after."
}
```

### 6. Cultural/Religious Considerations

**What it checks:** Any techniques that conflict with patient's values or beliefs?

**Examples:**
- Mindfulness meditation with religious objections
- Exposure content that violates cultural norms
- Gender-specific considerations

**Flag example:**
```json
{
    "severity": "low",
    "concern_type": "cultural",
    "concern_description": "Blueprint includes meditation. Patient profile notes religious preference for prayer over meditation.",
    "suggested_modification": "Substitute prayer-based grounding technique or remove meditation component."
}
```

---

## Key Design Decisions

### 1. Lower KB Threshold (0.40 vs 0.50)

**Why:** Safety info may not always be explicitly in KB. System should flag concerns based on clinical judgment even with limited KB support.

```python
# Lower threshold allows proceeding with warnings
if similarity >= 0.40:
    # Has some safety info - proceed with LLM screening
    proceed_with_llm()
else:
    # Even without KB, LLM can flag obvious concerns
    proceed_with_clinical_judgment_note()
```

### 2. Conservative Flagging

**Philosophy:** Better to over-flag than miss a safety issue.

- Medium threshold for flagging concerns
- "When in doubt, flag it"
- Therapist can always ignore false positives
- Cannot un-do missed safety issues

### 3. Temperature 0 (Deterministic)

**Why:** Safety screening is a critical task requiring consistency, not creativity.

```python
temperature=0  # Always same safety assessment for same input
```

### 4. Structured Output Format

**Why:** Clarification Agent needs structured data to generate therapist questions.

```python
response_format={"type": "json_object"}  # Enforces JSON structure
```

---

## Integration with Pipeline

### Flow Position

```
Agent 4: Blueprint Generator
         │
         ▼
Agent 5: Safety Gate ◄──── YOU ARE HERE
         │
         ├─── No flags → Skip to Agent 7
         │
         └─── Has flags → Agent 6: Clarification
                         │
                         └─── Agent 7: Protocol Generator
```

### Clarification Agent Integration

Safety flags become therapist questions:

```python
# Safety Gate output
safety_flags = [
    {
        "severity": "high",
        "concern_description": "Risk of dissociation during high-intensity exposure",
        "suggested_modification": "Use graduated approach",
        "requires_therapist_decision": true
    }
]

# Clarification Agent converts to question
clarification_questions = [
    {
        "question": "The Safety Gate flagged a concern: Risk of dissociation during high-intensity exposure. The KB suggests using a graduated approach. Do you want to:",
        "options": [
            "Use graduated exposure (recommended)",
            "Proceed with high-intensity exposure anyway",
            "Skip exposure exercises this session"
        ],
        "source": "safety_gate",
        "severity": "high"
    }
]
```

---

## Testing

### Basic Test

```bash
python backend/test_safety_gate.py
```

This runs a mock scenario with:
- Patient with OCD + ADHD + PTSD
- Blueprint proposing exposure therapy
- Recent trauma activation in history
- Therapist restriction on flooding

**Expected:** Multiple safety flags related to trauma, pace, and therapist restrictions.

### Test with Real Data

```python
from app.ai_agents import SafetyGateAgent

agent = SafetyGateAgent(db)
result = await agent.execute(
    therapist_id=1,
    blueprint=blueprint_from_agent_4,
    clinical_summary=summary_from_agent_2,
    patient_conditions="OCD, Depression",
    therapist_notes_summary="Previous panic during exposure"
)

# Check results
assert result["status"] == "success"
assert isinstance(result["safety_flags"], list)
print(f"Risk level: {result['overall_risk_level']}")
```

---

## Performance Characteristics

- **Latency:** ~3-7 seconds (1 LLM call + 1 KB query)
- **Token Usage:** ~2000-4000 tokens (depends on blueprint complexity)
- **Cost:** ~$0.002-0.006 per screening (gpt-4o-mini)
- **KB Queries:** 1 (contraindications + safety guidelines)
- **LLM Calls:** 1 (safety screening)

---

## Error Handling

```python
result = await safety_gate.execute(...)

if result["status"] == "error":
    # System error - default to requiring therapist review
    proceed_recommendation = "therapist_review_required"
    
elif result["overall_risk_level"] == "high_risk":
    # High-risk concerns - MUST have therapist review
    trigger_clarification_agent()
    
elif len(result["safety_flags"]) > 0:
    # Some concerns - may need modification
    pass_to_clarification_agent()
    
else:
    # No concerns - skip clarification, go to protocol generator
    proceed_directly_to_protocol_generator()
```

---

## Evaluation Metrics (for Research Paper)

### 1. Detection Rate (Recall)

Seed test cases with known contraindications:

```python
test_cases = [
    {
        "blueprint": "Flooding exposure",
        "patient": "Recent trauma + dissociation",
        "expected_flag": "trauma contraindication",
        "severity": "high"
    },
    # ... 20 more test cases
]

detected = sum(1 for case in test_cases if agent_flagged_concern(case))
recall = detected / len(test_cases)
```

**Target:** >85% recall on seeded contraindications

### 2. False Positive Rate

Therapist rates flagged concerns:

```python
flags = collect_all_flags_from_real_usage()
therapist_ratings = [therapist_agrees(flag) for flag in flags]

true_positives = sum(therapist_ratings)
false_positive_rate = 1 - (true_positives / len(flags))
```

**Target:** <30% false positive rate (conservative flagging is acceptable)

### 3. Severity Calibration

Do LLM severity ratings match therapist judgments?

```python
agreement = cohen_kappa(llm_severity, therapist_severity)
```

**Target:** Moderate agreement (κ > 0.4)

---

## Future Enhancements (v2)

1. **Multi-agent consensus** - Run 3 independent LLM calls, flag if 2/3 agree
2. **Patient history lookup** - Automatically check for past adverse reactions
3. **Severity scoring model** - Train classifier on therapist ratings
4. **Contraindication knowledge graph** - Structured relationships between conditions and techniques

---

## References

- **Architecture:** `NIRBAAN_AI_REFINED_ARCHITECTURE.md` - Agent 6
- **Source Code:** `backend/app/ai_agents/safety_gate.py`
- **Test Script:** `backend/test_safety_gate.py`
- **RAG Service:** `backend/app/resources/rag_service.py`
