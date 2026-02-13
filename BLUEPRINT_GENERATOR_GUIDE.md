# Blueprint Generator (Agent 4) — Implementation Guide

**Date**: February 11, 2026  
**Status**: Complete ✅  
**Agent Type**: LLM + RAG  
**Location**: `backend/app/ai_agents/blueprint_generator.py`

---

## Executive Summary

The **Blueprint Generator** is Agent 4 in the multi-agent therapy protocol generation pipeline. It creates a **high-level session skeleton** — NOT detailed therapist scripts. Think of it as the architectural blueprint that Protocol Generator (Agent 7) will later flesh out with detailed instructions, dialogue prompts, and clinical observation cues.

**Key Design Decision**: Separating structural planning (Blueprint Generator) from detailed scripting (Protocol Generator) mirrors how expert therapists actually plan sessions. Structure first, details second. This separation also enables staged review: therapists can approve the session structure before detailed protocol generation begins.

---

## Why This Agent Matters

### 1. Architectural Clarity

In the initial plan, Protocol Generator was supposed to do both structural planning AND detailed scripting in one pass. This led to:
- Over-long prompts
- Structural decisions buried in detail
- Harder to verify session logic
- No checkpoint for therapist review before full generation

Blueprint Generator solves this by providing a clear structural plan that both humans and downstream agents can evaluate before committing to detailed protocol generation.

### 2. Research Contribution

The blueprint layer is a **publishable architectural insight**:
- Demonstrates hierarchical planning in clinical AI (structure then details)
- Enables evaluation of structural quality independent of script quality
- Mirrors cognitive load management in human therapist planning
- Creates explainable checkpoints in the generation pipeline

### 3. Clinical Safety

By separating structure from details, Safety Gate (Agent 5) can screen the blueprint for contraindications BEFORE Protocol Generator spends tokens on detailed scripts. If Safety Gate flags issues, the pipeline can revise the structure without wasting detailed generation effort.

### 4. Efficiency

Blueprint Generator uses **top_k=10** (broader KB coverage) to explore session structures. Once structure is approved, Protocol Generator can use targeted per-phase retrieval (top_k=5 per phase) for efficient detailed generation. This two-phase retrieval strategy reduces redundant KB queries.

---

## Input Context

Blueprint Generator receives:

```python
{
    "clinical_summary": {
        "patient_profile": {...},
        "symptom_trajectory": "...",
        "recent_session_themes": "...",
        "therapist_priorities": "...",
        "previous_protocol_summary": "...",
        "open_concerns": "..."
    },
    "stage": "Active Skills Development with Exposure",
    "stage_rationale": "Patient shows readiness indicators...",
    "session_focus": "Introduce exposure hierarchy"
}
```

**What it does NOT receive:**
- Raw database dumps (that's what Context Synthesiser condenses)
- Unverified stage picks (Stage Picker verifies before passing forward)
- Therapist clarifications (those come later via Clarification Agent)

---

## Output Structure

### Success Case

```json
{
  "agent_name": "BlueprintGenerator",
  "status": "success",
  "blueprint": {
    "phases": [
      {
        "phase_number": 1,
        "phase_name": "Check-in and Homework Review",
        "time_allocation_minutes": 10,
        "objectives": [
          "Review patient's week",
          "Check homework completion",
          "Assess current mood and anxiety levels"
        ],
        "activities": [
          {
            "activity_name": "Weekly mood check",
            "kb_technique_reference": "PHQ-9 screener",
            "brief_description": "Quick standardized mood assessment"
          },
          {
            "activity_name": "Homework review",
            "kb_technique_reference": "Thought record analysis",
            "brief_description": "Review completed thought records from last week"
          }
        ],
        "materials_needed": ["PHQ-9 form"]
      },
      {
        "phase_number": 2,
        "phase_name": "Exposure Hierarchy Introduction",
        "time_allocation_minutes": 25,
        "objectives": [
          "Explain exposure therapy rationale",
          "Co-create exposure hierarchy",
          "Select first graduated exposure task"
        ],
        "activities": [
          {
            "activity_name": "Psychoeducation on exposure",
            "kb_technique_reference": "Graduated exposure principles (CBT)",
            "brief_description": "Explain habituation curve and safety signal removal"
          },
          {
            "activity_name": "Build exposure ladder",
            "kb_technique_reference": "Subjective Units of Distress (SUDS) scaling",
            "brief_description": "Co-create 10-step hierarchy from 0-100 SUDS"
          }
        ],
        "materials_needed": ["Exposure hierarchy worksheet", "SUDS scale handout"]
      },
      {
        "phase_number": 3,
        "phase_name": "In-session Practice",
        "time_allocation_minutes": 15,
        "objectives": [
          "Practice first exposure task in safe environment",
          "Monitor SUDS ratings during exposure",
          "Demonstrate habituation process"
        ],
        "activities": [
          {
            "activity_name": "Guided first exposure",
            "kb_technique_reference": "In-vivo exposure with therapist support",
            "brief_description": "Patient practices selected exposure with therapist present"
          }
        ],
        "materials_needed": []
      },
      {
        "phase_number": 4,
        "phase_name": "Closure and Homework Assignment",
        "time_allocation_minutes": 10,
        "objectives": [
          "Process exposure experience",
          "Assign homework exposure task",
          "Plan next session focus"
        ],
        "activities": [
          {
            "activity_name": "Post-exposure debrief",
            "kb_technique_reference": "Socratic questioning",
            "brief_description": "Explore what patient learned from exposure"
          },
          {
            "activity_name": "Homework assignment",
            "kb_technique_reference": "Between-session exposure practice",
            "brief_description": "Assign 2-3 repetitions of selected exposure task"
          }
        ],
        "materials_needed": ["Homework log sheet"]
      }
    ],
    "materials_summary": [
      "PHQ-9 form",
      "Exposure hierarchy worksheet",
      "SUDS scale handout",
      "Homework log sheet"
    ],
    "homework_preview": "Patient will practice selected exposure task 2-3 times before next session, recording SUDS ratings and observations in homework log.",
    "timing_check": "Total: 60 minutes (10 + 25 + 15 + 10)"
  },
  "blueprint_assessment": {
    "kb_sufficient": true,
    "sufficiency_reasoning": "KB provides comprehensive session structures for exposure therapy, including graduated hierarchy development and in-session practice protocols.",
    "missing_elements": []
  },
  "kb_sources_used": [
    {
      "source_index": 1,
      "what_it_contributed": "Exposure therapy session structure and phase timing"
    },
    {
      "source_index": 3,
      "what_it_contributed": "SUDS scaling technique and hierarchy building protocol"
    },
    {
      "source_index": 5,
      "what_it_contributed": "In-vivo exposure guidelines with therapist support"
    }
  ],
  "agent_metadata": {
    "llm_calls": 1,
    "total_tokens": 3247,
    "prompt_tokens": 2156,
    "completion_tokens": 1091,
    "generation_time_seconds": 4.3,
    "kb_chunks_retrieved": 10,
    "avg_kb_similarity": 0.73
  }
}
```

### Insufficient KB Case

```json
{
  "agent_name": "BlueprintGenerator",
  "status": "insufficient_kb",
  "blueprint": null,
  "sufficiency_check": {
    "sufficient": false,
    "avg_similarity": 0.42,
    "chunk_count": 10,
    "reason": "Average KB similarity (0.42) below threshold (0.50)"
  },
  "llm_assessment": {
    "kb_sufficient": false,
    "sufficiency_reasoning": "KB lacks specific session structures for exposure therapy with social anxiety. Generic CBT frameworks present but no detailed phase breakdowns or activity sequences.",
    "missing_elements": [
      "Exposure therapy session phase timing",
      "Social anxiety hierarchy building protocol",
      "In-session exposure practice guidelines"
    ]
  },
  "agent_metadata": {
    "llm_calls": 1,
    "total_tokens": 1823,
    "generation_time_seconds": 2.1
  }
}
```

---

## Core Design Principles

### 1. Structure Only, No Scripts

**What Blueprint Generator DOES:**
- Defines 4-6 phases that tile 60 minutes
- Names each phase and allocates time
- Lists objectives per phase
- References KB techniques to use
- Identifies materials needed

**What Blueprint Generator DOES NOT DO:**
- Write therapist dialogue prompts
- Provide step-by-step instructions
- Generate observation cues ("Watch for...")
- Create worksheet content
- Write detailed homework descriptions

Protocol Generator (Agent 7) handles all the "DOES NOT" items.

### 2. Every Activity Must Reference KB

The blueprint enforces KB grounding at the structural level. Every activity listed must include:
- `kb_technique_reference`: Specific technique name from KB
- `brief_description`: One-sentence summary

If the LLM cannot find KB support for an activity, the sufficiency check fails.

### 3. Timing Constraint: Exactly 60 Minutes

Phases must sum to 60 minutes. The blueprint includes a `timing_check` field that confirms the math. Typical structure:
- Check-in: 5-10 minutes
- Core intervention: 35-45 minutes (1-2 phases)
- Closure/homework: 5-10 minutes

### 4. Two-Tier Sufficiency Enforcement

**Tier 1 (Pre-LLM):**
Average KB similarity ≥ 0.50. If chunks are too dissimilar, don't call LLM.

**Tier 2 (LLM Assessment):**
LLM evaluates whether KB provides adequate session structures. Sets `kb_sufficient: true/false`. If false, explains what's missing in `missing_elements`.

If either tier fails → `status: "insufficient_kb"`, no blueprint generated.

---

## KB Retrieval Strategy

### Query Construction

```python
query = (
    f"session structure framework for {stage} stage treating {conditions}. "
    f"Session focus: {session_focus}. "
    f"Activities, phases, time allocation, techniques, exercises, interventions."
)
```

**Example:**
```
session structure framework for Active Skills Development with Exposure stage 
treating Generalized Anxiety Disorder, Social Anxiety. 
Session focus: Introduce exposure hierarchy and select first graduated exposure task. 
Activities, phases, time allocation, techniques, exercises, interventions.
```

### top_k = 10 (Higher Than Other Agents)

Why 10 instead of 8 (Stage Picker) or 6 (Safety Gate)?

Blueprint Generator needs **broader coverage** of session structural patterns. It's looking for:
- Multiple session structure examples
- Variety of phase sequences
- Different activity combinations
- Time allocation patterns

More chunks = more structural options for LLM to synthesize into coherent 60-minute plan.

### Similarity Threshold: 0.50

Same as Stage Picker. Exposure-focused session structures should match well if KB contains relevant treatment protocols.

---

## Prompt Engineering Details

### System Prompt (Key Constraints)

```
CRITICAL CONSTRAINTS:
1. The blueprint is STRUCTURAL ONLY - phases, time blocks, activities, KB technique references
2. Do NOT write detailed therapist scripts, dialogue prompts, or step-by-step instructions
3. Do NOT invent techniques - every activity must reference a specific technique from KB
4. The blueprint must tile exactly 60 minutes across 4-6 phases
```

**Why these constraints:**
- Prevents scope creep (Blueprint Generator trying to do Protocol Generator's job)
- Forces KB grounding at structural level
- Ensures downstream agents receive clean structural input

### Required JSON Structure

The prompt enforces strict JSON schema:
- `blueprint_assessment` with `kb_sufficient` boolean
- `session_blueprint` with array of `phases`
- Each phase requires: `phase_number`, `phase_name`, `time_allocation_minutes`, `objectives`, `activities`, `materials_needed`
- Each activity requires: `activity_name`, `kb_technique_reference`, `brief_description`
- Top-level: `materials_summary`, `homework_preview`, `timing_check`
- `kb_sources_used` with explanations

### Phase Design Principles (Embedded in Prompt)

```
PHASE DESIGN PRINCIPLES:
1. Check-in/grounding phase (~5-10 min) - review week, mood check, homework review
2. Core intervention phases (~35-45 min) - stage-appropriate therapeutic work
3. Closure/homework assignment phase (~5-10 min) - summarize, assign homework, plan next week
```

These are standard therapy session structures. Blueprint Generator applies them to the specific clinical context.

---

## Integration with Adjacent Agents

### Upstream: Receives from Stage Picker (Agent 3)

```python
# Stage Picker output
stage_result = {
    "status": "success",
    "selected_stage": "Active Skills Development with Exposure",
    "stage_rationale": "...",
    "verification_status": "confirmed"
}

# Blueprint Generator input
blueprint_result = await blueprint_agent.execute(
    db=db_session,
    therapist_id=therapist_id,
    clinical_summary=context_summary["clinical_summary"],
    stage=stage_result["selected_stage"],
    stage_rationale=stage_result["stage_rationale"],
    session_focus=session_focus
)
```

### Downstream: Passes to Safety Gate (Agent 5)

```python
# Blueprint Generator output
if blueprint_result["status"] == "success":
    # Safety Gate screens blueprint
    safety_result = await safety_agent.execute(
        therapist_id=therapist_id,
        blueprint=blueprint_result["blueprint"],
        clinical_summary=clinical_summary,
        patient_conditions="GAD, Social Anxiety",
        therapist_notes_summary="Graduated approach required, avoid re-traumatization"
    )
    
    if safety_result["safety_flags"]:
        # Pass flags to Clarification Agent
        clarification_result = await clarification_agent.execute(
            blueprint=blueprint_result["blueprint"],
            safety_flags=safety_result["safety_flags"],
            ...
        )
```

### Alternate Flow: Insufficient KB

```python
if blueprint_result["status"] == "insufficient_kb":
    # Pipeline halts
    return {
        "pipeline_status": "halted",
        "halt_reason": "insufficient_kb_for_blueprint",
        "missing_elements": blueprint_result["llm_assessment"]["missing_elements"],
        "recommendation": "Therapist should upload session structure documents for this stage"
    }
```

---

## Error Handling

### 1. Empty KB Results

```python
if not chunks:
    return {
        "sufficient": False,
        "avg_similarity": 0.0,
        "chunk_count": 0,
        "reason": "No KB chunks retrieved for session structure query"
    }
```

**Resolution:** Therapist needs to upload treatment protocol documents.

### 2. Low Similarity (Tier 1 Failure)

```python
if avg_similarity < 0.50:
    return {
        "sufficient": False,
        "avg_similarity": 0.42,
        "chunk_count": 10,
        "reason": "Average KB similarity (0.420) below threshold (0.50)"
    }
```

**Resolution:** KB may contain documents but not specific session structures for this stage. Therapist should add stage-specific protocol guides.

### 3. LLM Assesses Insufficient (Tier 2 Failure)

LLM returns `kb_sufficient: false` even when Tier 1 passed. This means chunks have decent similarity but lack critical structural elements.

```python
"llm_assessment": {
    "kb_sufficient": false,
    "sufficiency_reasoning": "KB provides general CBT principles but lacks specific exposure therapy session phase breakdowns.",
    "missing_elements": [
        "Exposure hierarchy building protocol",
        "In-session exposure practice timing",
        "SUDS monitoring procedure"
    ]
}
```

**Resolution:** More granular, protocol-level KB documents needed (not just conceptual articles).

### 4. JSON Parsing Errors

```python
try:
    result = json.loads(response.choices[0].message.content)
except json.JSONDecodeError:
    return {
        "status": "error",
        "error": "LLM returned invalid JSON",
        ...
    }
```

**Resolution:** Rare with `response_format={"type": "json_object"}`. If it happens, log the raw response for prompt debugging.

### 5. Timing Constraint Violation

If LLM generates phases that don't sum to 60 minutes, the `timing_check` field should catch it:

```python
"timing_check": "Total: 58 minutes (10 + 25 + 15 + 8). WARNING: 2 minutes short of 60-minute target."
```

Protocol Generator can adjust timing during detailed generation.

---

## Evaluation Metrics (For Research Paper)

### 1. Structural Quality

**Human Evaluation (Therapist Ratings):**
- **Coherence**: Do phases flow logically? (1-5 Likert)
- **Completeness**: Are all necessary session components present? (1-5 Likert)
- **Timing Realism**: Is time allocation practical? (1-5 Likert)
- **Stage Appropriateness**: Does structure match selected stage? (1-5 Likert)

**Target:** Mean score ≥ 4.0 across all dimensions

### 2. KB Grounding Accuracy

**Verification Method:**
For each activity's `kb_technique_reference`, human rater checks:
- Does this technique appear in the KB? (Yes/No)
- Is it appropriate for the listed activity? (Yes/No)

**Metrics:**
- **KB Citation Accuracy**: % of technique references that exist in KB
- **Technique Appropriateness**: % of cited techniques that are appropriate for activity

**Target:** >95% citation accuracy, >90% appropriateness

### 3. Timing Constraint Compliance

**Automated:**
- Sum all `time_allocation_minutes` across phases
- Check if total == 60 ± 2 minutes

**Target:** 100% compliance (this is a hard constraint, should never fail)

### 4. Phase Count Distribution

**Descriptive:**
Analyze frequency of 4-phase, 5-phase, 6-phase blueprints across different stages and conditions.

**Research Question:** Do certain stages or conditions consistently require more phases? (E.g., exposure therapy might need 5-6 phases for graduated steps, while maintenance therapy might use 4 simpler phases.)

### 5. Tier 1 vs Tier 2 Failure Rate

**Metric:**
- % of cases where Tier 1 passed but Tier 2 failed

**Research Value:**
If Tier 2 catches failures that Tier 1 missed, this validates the two-tier design. If Tier 2 rarely disagrees with Tier 1, the two-tier approach may be over-engineered (but better safe than sorry for clinical applications).

### 6. Blueprint-to-Protocol Consistency

**Evaluation After Protocol Generator:**
Compare blueprint phases with Protocol Generator's final protocol:
- Did Protocol Generator follow the blueprint structure?
- Were any phases added/removed/reordered?
- Were all KB technique references expanded correctly?

**Target:** >95% structural fidelity (Protocol Generator should respect blueprint)

---

## Performance Characteristics

### Latency

**Typical:**
- KB retrieval: 0.5-1.0 seconds
- LLM generation: 3-5 seconds
- Total: **3.5-6.0 seconds**

**Worst Case (Insufficient KB):**
- KB retrieval: 0.5-1.0 seconds
- LLM sufficiency assessment: 2-3 seconds
- Total: **2.5-4.0 seconds** (faster because no blueprint generation)

### Token Usage

**Prompt Tokens:** ~2000-2500
- System prompt: ~600 tokens
- Clinical summary: ~800-1000 tokens
- KB chunks (10 × ~100 tokens): ~1000 tokens
- Stage info: ~200 tokens

**Completion Tokens:** ~1000-1500 (blueprint structure)

**Total:** ~3000-4000 tokens per call

**Cost (GPT-4o-mini):**
- Input: $0.150 per 1M tokens
- Output: $0.600 per 1M tokens
- **Per Blueprint:** ~$0.001-0.002

### Comparison to Other Agents

| Agent | LLM Calls | Tokens | Cost | Latency |
|---|---|---|---|---|
| Context Synthesiser | 1 | 2000-3000 | $0.001 | 2-4s |
| Stage Picker | 2-4 | 4000-8000 | $0.002-0.004 | 5-10s |
| **Blueprint Generator** | **1** | **3000-4000** | **$0.001-0.002** | **3.5-6s** |
| Safety Gate | 1 | 2000-4000 | $0.001-0.002 | 3-7s |

Blueprint Generator is mid-range in cost and latency. Stage Picker is more expensive due to verification loop.

---

## Common Pitfalls & Solutions

### Pitfall 1: Blueprint Too Detailed

**Problem:** LLM starts writing detailed therapist instructions instead of structural skeleton.

**Solution:** Reinforce in system prompt:
```
Do NOT write detailed therapist scripts, dialogue prompts, or step-by-step instructions 
(that is Protocol Generator's job)
```

Also enforce in few-shot examples if needed.

### Pitfall 2: Inventing Techniques Not in KB

**Problem:** LLM references "mindfulness breathing exercise" but KB doesn't mention this technique.

**Solution:**
- System prompt: "Do NOT invent techniques - every activity must reference a specific technique from KB"
- Tier 2 sufficiency check should catch this if LLM follows schema
- Post-generation validation: check all `kb_technique_reference` values against actual KB chunk content

### Pitfall 3: Phases Don't Sum to 60 Minutes

**Problem:** Phases total 55 or 65 minutes due to LLM miscalculation.

**Solution:**
- Include `timing_check` field in output schema
- Prompt emphasizes: "The blueprint must tile exactly 60 minutes across 4-6 phases"
- Post-generation validation can auto-correct small deviations (±2 minutes)

### Pitfall 4: Over-Reliance on First Few KB Chunks

**Problem:** LLM only references high-similarity chunks (first 3-4) and ignores the rest.

**Solution:**
- `top_k=10` provides variety
- System prompt should encourage synthesizing across sources
- `kb_sources_used` field makes LLM explain what each chunk contributed

### Pitfall 5: Generic Blueprints (Not Patient-Specific)

**Problem:** Blueprint looks like a textbook session structure, doesn't reflect patient's specific context.

**Solution:**
- Context Synthesiser provides rich clinical summary (trajectory, concerns, priorities)
- Blueprint prompt includes: "Therapist Priorities" and "Open Concerns" sections
- Evaluation metric: "Stage Appropriateness" should catch overly generic blueprints

---

## Testing Strategy

### Unit Test: Mock KB Query

```python
def test_blueprint_with_mock_kb():
    """Test Blueprint Generator with mock KB chunks."""
    agent = BlueprintGeneratorAgent()
    
    # Mock high-similarity KB chunks
    agent.rag_service.retrieve_chunks = Mock(return_value=[
        {"text": "Exposure therapy sessions typically include...", "similarity": 0.78},
        {"text": "Building exposure hierarchies using SUDS...", "similarity": 0.75},
        # ... 8 more chunks
    ])
    
    result = await agent.execute(
        db=mock_db,
        therapist_id=123,
        clinical_summary=mock_summary,
        stage="Exposure Therapy",
        stage_rationale="Patient ready for behavioral work",
        session_focus="Introduce hierarchy"
    )
    
    assert result["status"] == "success"
    assert len(result["blueprint"]["phases"]) in [4, 5, 6]
    assert sum(p["time_allocation_minutes"] for p in result["blueprint"]["phases"]) == 60
```

### Integration Test: Agents 3 → 4 → 5

```python
async def test_stage_to_blueprint_to_safety():
    """Test Stage Picker → Blueprint Generator → Safety Gate flow."""
    
    # Stage Picker
    stage_result = await stage_agent.execute(...)
    assert stage_result["status"] == "success"
    
    # Blueprint Generator
    blueprint_result = await blueprint_agent.execute(
        stage=stage_result["selected_stage"],
        stage_rationale=stage_result["stage_rationale"],
        ...
    )
    assert blueprint_result["status"] == "success"
    
    # Safety Gate
    safety_result = await safety_agent.execute(
        blueprint=blueprint_result["blueprint"],
        ...
    )
    assert safety_result["status"] == "success"
    
    # Verify data flows correctly
    assert "phases" in blueprint_result["blueprint"]
    assert len(safety_result["safety_flags"]) >= 0  # May or may not have flags
```

### Evaluation Test: Therapist Rating

```python
def test_therapist_rating_blueprint_quality():
    """Human evaluation script for blueprint quality."""
    blueprints = load_test_blueprints()  # 20 blueprints
    
    for bp in blueprints:
        print(format_blueprint_for_review(bp))
        
        coherence = int(input("Coherence (1-5): "))
        completeness = int(input("Completeness (1-5): "))
        timing_realism = int(input("Timing Realism (1-5): "))
        stage_appropriate = int(input("Stage Appropriateness (1-5): "))
        
        save_rating(bp["id"], {
            "coherence": coherence,
            "completeness": completeness,
            "timing_realism": timing_realism,
            "stage_appropriateness": stage_appropriate
        })
    
    # Compute mean ratings
    ratings_df = pd.DataFrame(load_all_ratings())
    print(ratings_df.mean())  # Target: ≥ 4.0 for all dimensions
```

---

## Future Enhancements (v2)

### 1. Multi-Blueprint Sampling

Generate 3 different blueprints and let LLM/therapist choose best one:
- Diversity in phase structures
- Different activity sequences
- Varying time allocations

**Research Value:** Study structural diversity preferences across therapists.

### 2. Blueprint Revision Loop

Similar to Stage Picker's verification loop:
- Generate blueprint
- Verify phase sequence logic
- Revise if incoherent
- Max 1 iteration

**When to add:** If human evaluation shows coherence scores < 4.0 consistently.

### 3. Patient Preference Integration

If patient has expressed preferences about session structure:
- "I prefer shorter check-ins, more time on exercises"
- "I need more processing time after exposures"

Pull from patient notes and incorporate into blueprint objectives.

### 4. Adaptive Timing Allocation

Instead of fixed 60 minutes, support variable session lengths:
- 45-minute sessions (common in some settings)
- 90-minute sessions (intensive therapy)

Currently hardcoded to 60; could be parameterized.

### 5. Blueprint Templates per Stage

Cache high-quality blueprints for common stage + condition combinations:
- "Exposure therapy for social anxiety" template
- "Cognitive restructuring for depression" template

Use as few-shot examples or starting points for customization.

**When to add:** After collecting 50+ blueprints, analyze which structures recur and formalize as templates.

---

## LangGraph Integration Notes

### State Update

```python
from langgraph.graph import StateGraph

class PipelineState(TypedDict):
    clinical_summary: Dict[str, Any]
    selected_stage: str
    stage_rationale: str
    blueprint: Optional[Dict[str, Any]]  # Blueprint Generator writes here
    blueprint_status: str
    # ... other fields

def blueprint_generator_node(state: PipelineState) -> PipelineState:
    """LangGraph node for Blueprint Generator."""
    agent = BlueprintGeneratorAgent()
    
    result = await agent.execute(
        db=state["db_session"],
        therapist_id=state["therapist_id"],
        clinical_summary=state["clinical_summary"],
        stage=state["selected_stage"],
        stage_rationale=state["stage_rationale"],
        session_focus=state["session_focus"]
    )
    
    state["blueprint"] = result.get("blueprint")
    state["blueprint_status"] = result["status"]
    state["blueprint_metadata"] = result["agent_metadata"]
    
    return state
```

### Conditional Edge: Proceed or Halt

```python
def check_blueprint_status(state: PipelineState) -> str:
    """Conditional routing after Blueprint Generator."""
    if state["blueprint_status"] == "success":
        return "safety_gate"  # Next: Safety Gate (Agent 5)
    elif state["blueprint_status"] == "insufficient_kb":
        return "halt_insufficient_kb"
    else:
        return "halt_error"

graph = StateGraph(PipelineState)
graph.add_node("blueprint_generator", blueprint_generator_node)
graph.add_node("safety_gate", safety_gate_node)
graph.add_node("halt_insufficient_kb", halt_node)

graph.add_conditional_edges(
    "blueprint_generator",
    check_blueprint_status,
    {
        "safety_gate": "safety_gate",
        "halt_insufficient_kb": "halt_insufficient_kb",
        "halt_error": "halt_error"
    }
)
```

---

## Summary: Blueprint Generator in the Pipeline

```
┌─────────────────────────────────────────┐
│ Stage Picker (Agent 3)                  │
│ Selects & verifies therapy stage        │
└───────────────┬─────────────────────────┘
                │ stage + rationale
                ▼
┌─────────────────────────────────────────┐
│ Blueprint Generator (Agent 4) ← YOU ARE HERE
│ Creates 4-6 phase session skeleton      │
│ • KB query (top_k=10)                   │
│ • Two-tier sufficiency check            │
│ • Structural planning only              │
│ • Timing constraint (60 minutes)        │
└───────────────┬─────────────────────────┘
                │ blueprint
                ▼
┌─────────────────────────────────────────┐
│ Safety Gate (Agent 5)                   │
│ Screens for contraindications           │
└─────────────────────────────────────────┘
```

**Status:** ✅ **COMPLETE**  
**Pipeline Progress:** **6/8 agents (75%)**

**Remaining Agents:**
- Agent 6: Clarification Agent (Human-in-the-Loop)
- Agent 7: Protocol Generator (Detailed session protocol)
- Agent 8: Uncertainty Scorer (Confidence scoring + revision loop)

---

## References

- **Architecture Document**: `NIRBAAN_AI_REFINED_ARCHITECTURE.md` (Lines 353-371)
- **Agent Implementation**: `backend/app/ai_agents/blueprint_generator.py`
- **Test Script**: `backend/test_blueprint_generator.py`
- **README**: `backend/app/ai_agents/README.md` (Agent 4 section)

---

*Document Version: 1.0*  
*Last Updated: February 11, 2026*
