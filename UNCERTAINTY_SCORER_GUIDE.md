# Uncertainty Scorer Implementation Guide

**Agent 8: The Core Research Contribution**

---

## Executive Summary

The **Uncertainty Scorer** is the defining feature that elevates the Nirbaan AI system from "impressive undergraduate project" to "publishable research." It quantifies epistemic uncertainty for generated therapy protocols at **two granularities**:

1. **Global confidence score** (0.0-1.0): Overall KB-groundedness of the entire protocol
2. **Per-claim scores**: Individual confidence for every clinically significant statement

When global confidence falls below a threshold (default: 0.50), the agent **triggers a conditional revision loop**: it identifies the weakest claims, sends explicit revision instructions back to the Protocol Generator, and re-scores the revised protocol. This mechanism ensures that low-confidence protocols are **never delivered as-is**.

**Key Research Contributions:**
- **Epistemic uncertainty quantification** for generated clinical text (active research frontier)
- **Self-correction through KB re-grounding** (demonstrates LLM self-improvement)
- **Two-pass quality assurance** with measurable confidence improvement
- **Calibrated trust signals** for human therapists (correlation with expert judgment)

**Architectural Position:**
- **Final node** before `__END__` in LangGraph pipeline
- **Receives**: Full protocol + all KB chunks used + clinical context
- **Returns**: Scored protocol with confidence metrics + revised protocol (if triggered)
- **Conditional edge**: If score < 0.50 → loop back to Protocol Generator; else → END

---

## Why This Matters

### The Publication Hook

Most AI-in-therapy papers face one critical question from reviewers: **"How do you know the system isn't hallucinating?"** The Uncertainty Scorer provides three defensible answers:

1. **Quantified Uncertainty**: Every clinical claim has an explicit confidence score backed by KB evidence
2. **Self-Correction**: Low-confidence protocols are automatically revised, not blindly delivered
3. **Calibration Evidence**: You can measure whether system scores correlate with expert therapist judgments

Without this agent, you have a protocol generator. **With it, you have a research contribution.**

### What It Enables for Journal Publication

**Evaluable Claims:**
- "Per-claim uncertainty scores correlate with expert therapist assessments at r = X"
- "The revision loop improves average confidence by Y% (p < 0.05)"
- "Protocols that undergo revision receive Z% higher quality ratings from therapists"
- "System correctly flags W% of clinically unsound claims as low-confidence"

**Reportable Findings:**
- Revision trigger rate (% of protocols scoring < 0.50 initially)
- Confidence improvement delta (before vs after revision)
- Semantic diff analysis (how much content changes during revision)
- Calibration curves (system confidence vs human judgment)

**Research Positioning:**
- Builds on: Recent work on LLM uncertainty (Kuhn et al. 2023, Kadavath et al. 2022)
- Extends to: Clinical domain with safety-critical requirements
- Novel contribution: Conditional revision loop for uncertainty-guided self-improvement

---

## Input/Output Structure

### Inputs

```python
{
    "protocol": {
        # Full generated protocol from Protocol Generator (Agent 7)
        "session_title": "...",
        "phases": [...],
        "instructions": [...],
        "kb_citations": [...]
    },
    "kb_chunks_used": [
        {
            "id": "chunk_001",
            "content": "KB text...",
            "source": "Document name",
            "similarity_score": 0.92
        },
        # All chunks used by any RAG-using agent (4, 5, 7)
    ],
    "clinical_summary": {
        # From Context Synthesiser (Agent 2)
        "patient_profile": "...",
        "symptom_trajectory": "...",
        "therapist_priorities": "..."
    },
    "blueprint": {
        # From Blueprint Generator (Agent 4)
        "phases": [...],
        "duration_minutes": 60
    },
    "protocol_generator": <ProtocolGeneratorAgent instance>
    # REQUIRED for revision loop - must have revise_protocol() method
}
```

### Outputs

**Without Revision (Global Confidence ≥ 0.50):**
```python
{
    "global_confidence": 0.78,
    "per_claim_scores": [
        {
            "claim_text": "Begin with 3-minute breathing exercise",
            "confidence": 0.92,
            "kb_evidence": "Chunk 12: 'Breathing exercises should be 2-5 minutes...'",
            "reasoning": "Directly supported by KB with explicit timing guidance"
        },
        {
            "claim_text": "Spend 25 minutes on exposure role-play",
            "confidence": 0.85,
            "kb_evidence": "Chunk 3: 'Exposure duration 15-30 minutes for habituation'",
            "reasoning": "KB specifies range; protocol value falls within it"
        }
        # ... all clinically significant claims
    ],
    "high_risk_flags": [],  # Empty if no claims < 0.50
    "overall_assessment": "Protocol is well-grounded. 18/20 claims strongly supported by KB.",
    "revision_triggered": false,
    "initial_score": 0.78,
    "score_after_revision": null,
    "revised_protocol": null,
    "metadata": {
        "agent": "UncertaintyScorer",
        "timestamp": "2026-02-11T14:23:45",
        "latency_seconds": 6.3,
        "model": "gpt-4o-mini",
        "num_claims_scored": 20,
        "num_high_risk_claims": 0,
        "revision_threshold": 0.50,
        "num_kb_chunks_evaluated": 15
    }
}
```

**With Revision (Global Confidence < 0.50):**
```python
{
    "global_confidence": 0.68,  # AFTER revision
    "per_claim_scores": [...],  # Scores for REVISED protocol
    "high_risk_flags": [
        "1 claim still below threshold after revision (see per-claim scores)"
    ],
    "overall_assessment": "Protocol revised to improve grounding. Score increased from 0.42 to 0.68.",
    "revision_triggered": true,
    "initial_score": 0.42,  # BEFORE revision
    "score_after_revision": 0.68,
    "revised_protocol": {
        # Full revised protocol (replaces original)
        "session_title": "... (REVISED)",
        "phases": [...],
        "revision_metadata": {
            "revision_reason": "Low confidence score",
            "changes_made": "Replaced unsupported claims, added KB citations"
        }
    },
    "warning_banner": null,  # Set if score still < 0.50 after revision
    "metadata": {
        "latency_seconds": 18.7,  # Higher due to revision
        "revision_triggered": true
    }
}
```

**Still Low After Revision (< 0.50):**
```python
{
    "global_confidence": 0.47,  # Still below threshold
    "revision_triggered": true,
    "initial_score": 0.35,
    "score_after_revision": 0.47,
    "revised_protocol": {...},  # Delivered despite low score
    "warning_banner": "⚠️ WARNING: This protocol has undergone revision but still has low confidence (0.47). Review carefully before use. 3 high-risk claims identified.",
    # ... rest of output
}
```

---

## Core Design Principles

### 1. Two-Granularity Scoring

**Global confidence** captures overall protocol quality. **Per-claim scores** enable:
- **Granular inspection**: Therapist can see exactly which claims are uncertain
- **Targeted revision**: Only low-confidence claims are replaced
- **Error attribution**: Pin-point where KB gaps cause problems
- **Research evaluation**: Measure per-claim correlation with expert judgment

### 2. Conservative Scoring Philosophy

**"It is better to underestimate confidence than to overstate it."**

- When in doubt, score lower
- Ambiguous KB support → score in 0.5-0.7 range, not 0.8+
- Missing KB evidence → score < 0.50 (high-risk)
- Clinical safety requires conservative trust signals

### 3. Conditional Revision, Not Rejection

**Bad design**: Score protocol, flag problems, stop.  
**Our design**: Score protocol, identify problems, **fix them automatically**, re-score.

This demonstrates **AI self-correction** — a key research contribution. The system does not passively report uncertainty; it **actively works to reduce it**.

### 4. Single Revision Iteration (No Infinite Loops)

**Maximum 1 revision cycle**: Generate → Score → Revise → Re-Score → Deliver.

**Why limit to 1?**
- Prevents infinite revision loops
- Forces Protocol Generator to fix problems in one pass (encourages good revision prompts)
- Keeps latency predictable (< 30 seconds total)
- If score is still low after 1 revision, that's a signal the KB is insufficient → deliver with warning

### 5. Explicit Warning Banners for Persistent Low Confidence

If a protocol scores < 0.50 even **after** revision, it is delivered with a **prominent warning banner**:

> ⚠️ **WARNING**: This protocol has undergone revision but still has low confidence (0.47). Review carefully before use. 3 high-risk claims identified.

This ensures therapists are **never** handed a low-confidence protocol without knowing it.

---

## Scoring Methodology

### Scoring Rubric

The LLM is instructed to use this 5-tier rubric:

| Score Range | Interpretation | Example |
|---|---|---|
| **0.9-1.0** | Directly stated in KB with explicit details | "Use 3-minute breathing exercise" when KB says "breathing exercises should be 2-5 minutes" |
| **0.7-0.89** | Strongly supported, minor details inferred | "Spend 20 minutes on exposure" when KB says "15-30 minutes typical" |
| **0.5-0.69** | Partially supported, some extrapolation | "Homework 3x/week" when KB mentions "regular practice" but no frequency |
| **0.3-0.49** | Weakly supported, significant extrapolation | "Assign 5 exposures daily" when KB says "graduated homework" (no frequency) |
| **0.0-0.29** | Not supported, likely hallucination | "Use flooding technique" when KB only describes graduated exposure |

### What Counts as "Clinically Significant Claim"?

**Include:**
- Specific techniques/exercises ("3-minute breathing", "role-play exposure")
- Clinical instructions ("If anxiety > 8/10, pause and ground")
- Homework assignments ("Practice 3 times this week")
- Timing/dosage ("Spend 15 minutes on cognitive restructuring")
- Contraindications ("Avoid this if patient has trauma history")
- Expected outcomes ("Should reduce panic by 30%")

**Exclude:**
- Generic transitions ("Then move to next phase")
- Session logistics ("Welcome the patient")
- Non-clinical metadata (session title, duration fields)

### Global Confidence Computation

**Weighted average** of per-claim scores, with higher weight on:
- Safety-critical claims (contraindications, risk flags)
- Core intervention claims (the main therapy technique)
- Lower weight on supplementary claims (homework reminders, logistics)

The LLM is prompted to compute this implicitly (no explicit formula given — allows flexibility).

---

## Revision Loop Logic

### When Revision Triggers

```python
if global_confidence < revision_threshold:  # Default: 0.50
    trigger_revision()
```

### Revision Workflow

1. **Identify Low-Confidence Claims**
   - Filter `per_claim_scores` where `confidence < high_risk_threshold` (default: 0.50)
   - Sort by confidence (lowest first) — prioritize worst claims

2. **Build Revision Instructions**
   - For each low-confidence claim:
     - State the claim text
     - Explain why it scored low (from `reasoning` field)
     - Note KB evidence (or lack thereof)
     - Directive: "Replace with KB-grounded alternative OR remove"
   - Include list of high-confidence claims to **preserve unchanged**
   - Remind Protocol Generator: "Do NOT introduce new unsupported claims"

3. **Call Protocol Generator**
   ```python
   revised_protocol = await protocol_generator.revise_protocol(
       original_protocol=protocol,
       revision_instructions=revision_instructions,
       kb_chunks=kb_chunks_used,
       clinical_summary=clinical_summary,
       blueprint=blueprint
   )
   ```

4. **Re-Score Revised Protocol**
   ```python
   final_scoring = await self.score_protocol(
       protocol=revised_protocol,
       kb_chunks=kb_chunks_used,
       clinical_summary=clinical_summary,
       blueprint=blueprint
   )
   ```

5. **Deliver Result**
   - If `final_scoring['global_confidence'] >= 0.50`: Success, no warning
   - If still < 0.50: Deliver with **warning banner**

### Example Revision Instructions

```
REVISION REQUIRED — Global confidence score: 0.42

The following 4 claims scored below 0.50 and must be revised or removed:

1. CLAIM: "Assign 5 high-intensity exposure exercises to be completed daily."
   SCORE: 0.28
   REASON: Specific frequency (5 daily) not found in KB; appears to be extrapolation.
   KB EVIDENCE: Chunk 6 mentions "graduated homework" but no frequency specified.
   
   ACTION: Replace with a KB-grounded alternative OR remove if no KB support exists.

2. CLAIM: "Each homework exposure should last minimum 45 minutes."
   SCORE: 0.31
   REASON: 45-minute duration not supported by KB; KB suggests 15-30 minutes.
   KB EVIDENCE: Chunk 3 states "15-30 minutes typical for exposure duration."
   
   ACTION: Replace with KB-supported duration (15-30 min range).

...

AVAILABLE KB CHUNKS FOR REVISION:
7 chunks are available. Use ONLY these for grounding. Do not introduce new claims without KB support.

HIGH-CONFIDENCE CLAIMS (DO NOT CHANGE):
- "Begin exposure by establishing baseline anxiety (0-10 scale)" (score: 0.94)
- "Monitor anxiety every 5 minutes during exposure" (score: 0.89)
...

REVISION GUIDELINES:
1. Replace low-confidence claims with KB-grounded alternatives when possible
2. Remove claims entirely if no KB support can be found
3. Preserve all high-confidence claims unchanged
4. Maintain session timing and structure from blueprint
5. Ensure revised protocol is still coherent and clinically complete
6. Do NOT introduce new unsupported claims to fill gaps

This is the ONLY revision pass. Make it count.
```

---

## Prompt Engineering

### System Prompt Structure

**Section 1: Role & Task**
```
You are an epistemic uncertainty scorer for clinical therapy protocols.

Your task is to score the KB-groundedness of a generated therapy session protocol. You will:
1. Extract ALL clinically significant claims from the protocol
2. Score each claim's confidence (0.0-1.0) based on how well it is supported by the KB
3. Identify the specific KB evidence supporting each claim (or "none" if unsupported)
4. Explain your reasoning for each score
5. Compute a global confidence score for the entire protocol
6. Flag claims that are HIGH RISK (score < 0.50)
```

**Section 2: Scoring Rubric**
- Explicit 5-tier rubric (0.9-1.0, 0.7-0.89, 0.5-0.69, 0.3-0.49, 0.0-0.29)
- Examples for each tier

**Section 3: What to Score**
- List of clinically significant claim types
- List of what NOT to score (logistics, metadata)

**Section 4: Context**
- Clinical summary (patient profile, trajectory)
- Blueprint (session structure)
- KB chunks (all chunks used in generation)
- Protocol to score

**Section 5: Output Format**
```json
{
    "global_confidence": 0.75,
    "per_claim_scores": [...],
    "high_risk_flags": [...],
    "overall_assessment": "...",
    "revision_needed": false
}
```

**Section 6: Calibration Instruction**
```
The global_confidence should be a WEIGHTED AVERAGE of per-claim scores, with higher weight on claims that have greater clinical significance (e.g., safety-critical claims).

Set "revision_needed" to true if global_confidence < 0.50.

Be CONSERVATIVE. It is better to underestimate confidence than to overstate it. This is a clinical safety system.
```

### Temperature = 0

**Always.** Uncertainty scoring must be **deterministic**. Re-running the scorer on the same protocol should produce the same scores (within minor LLM variance).

Non-zero temperature would introduce randomness into safety-critical trust signals — unacceptable.

### Structured JSON Output

Use OpenAI's `response_format={"type": "json_object"}` to ensure valid JSON. Parse and validate:
- `global_confidence` is float between 0.0 and 1.0
- `per_claim_scores` is non-empty list
- Each claim has required fields: `claim_text`, `confidence`, `kb_evidence`, `reasoning`

---

## Integration Patterns

### With Protocol Generator (Agent 7)

**Forward Integration (Normal Flow):**
```python
# Protocol Generator completes
protocol_result = await protocol_generator.execute(...)

# Pass to Uncertainty Scorer
scoring_result = await uncertainty_scorer.execute(
    protocol=protocol_result["protocol"],
    kb_chunks_used=protocol_result["kb_chunks_used"],  # MUST track in Agent 7
    clinical_summary=clinical_summary,
    blueprint=blueprint,
    protocol_generator=protocol_generator  # For revision
)

# Use final protocol (revised if revision_triggered)
final_protocol = (
    scoring_result["revised_protocol"]
    if scoring_result["revision_triggered"]
    else protocol_result["protocol"]
)
```

**Backward Integration (Revision Loop):**
```python
# Inside Uncertainty Scorer
if global_confidence < revision_threshold:
    revised_protocol = await protocol_generator.revise_protocol(
        original_protocol=protocol,
        revision_instructions=revision_instructions,
        kb_chunks=kb_chunks_used,
        clinical_summary=clinical_summary,
        blueprint=blueprint
    )
```

**Requirements for Protocol Generator:**
- Must implement `revise_protocol()` method
- Must accept `revision_instructions` parameter (string)
- Must return revised protocol in same format as original
- Should track which claims were changed (optional: `revision_metadata` field)

### With LangGraph Workflow

**Node Definition:**
```python
from langgraph.graph import StateGraph

async def uncertainty_scorer_node(state: ProtocolState) -> Dict:
    scorer = UncertaintyScorer()
    protocol_generator = ProtocolGeneratorAgent()
    
    result = await scorer.execute(
        protocol=state["protocol"],
        kb_chunks_used=state["kb_chunks_used"],
        clinical_summary=state["clinical_summary"],
        blueprint=state["blueprint"],
        protocol_generator=protocol_generator
    )
    
    return {
        "scoring_result": result,
        "final_protocol": (
            result["revised_protocol"]
            if result["revision_triggered"]
            else state["protocol"]
        ),
        "confidence_metadata": result["metadata"]
    }

workflow.add_node("uncertainty_scorer", uncertainty_scorer_node)
```

**Conditional Edge (Revision Loop):**
```python
# OPTION 1: Implicit revision (handled inside node)
workflow.add_edge("protocol_generator", "uncertainty_scorer")
workflow.add_edge("uncertainty_scorer", END)

# OPTION 2: Explicit revision edge (if you want to track revision in graph state)
def should_revise(state: ProtocolState) -> str:
    if state["initial_confidence"] < 0.50 and not state["revision_attempted"]:
        return "revise"
    return "end"

workflow.add_conditional_edges(
    "uncertainty_scorer",
    should_revise,
    {
        "revise": "protocol_generator",  # Loop back
        "end": END
    }
)
```

**Recommendation:** Use **OPTION 1** (implicit revision). The Uncertainty Scorer handles the revision loop internally, making the LangGraph workflow cleaner. The graph does not need to know about revision details.

### With Frontend Display

**Display Global Confidence:**
```jsx
<div className="confidence-badge">
  <span className="score">{confidenceScore.toFixed(2)}</span>
  <span className="label">Confidence Score</span>
  {confidenceScore < 0.50 && (
    <span className="warning">⚠️ Low Confidence</span>
  )}
</div>
```

**Display Per-Claim Scores:**
```jsx
{protocol.phases.map(phase => (
  <div key={phase.phase_number}>
    <h3>{phase.name}</h3>
    {phase.instructions.map((instruction, idx) => {
      const claim_score = findClaimScore(instruction);
      return (
        <div className={`instruction ${claim_score < 0.50 ? 'high-risk' : ''}`}>
          <p>{instruction}</p>
          {claim_score && (
            <div className="claim-confidence">
              <span>Confidence: {claim_score.confidence.toFixed(2)}</span>
              <span>KB Evidence: {claim_score.kb_evidence}</span>
            </div>
          )}
        </div>
      );
    })}
  </div>
))}
```

**Display Warning Banner:**
```jsx
{scoringResult.warning_banner && (
  <div className="alert alert-warning">
    <strong>⚠️ Warning</strong>
    <p>{scoringResult.warning_banner}</p>
  </div>
)}
```

---

## Error Handling

### Scenario 1: LLM Returns Invalid JSON

**Cause**: LLM outputs malformed JSON despite `response_format` instruction.

**Handling**:
```python
try:
    result = json.loads(response.choices[0].message.content)
except json.JSONDecodeError as e:
    logger.error(f"Failed to parse scoring result: {e}")
    return {
        "global_confidence": 0.0,  # Conservative fallback
        "per_claim_scores": [],
        "high_risk_flags": ["SCORING FAILED - Could not parse LLM output"],
        "overall_assessment": "Scoring failed due to JSON parsing error",
        "revision_needed": True,
        "error": str(e)
    }
```

**Impact**: Protocol flagged as zero confidence. Therapist sees error message. Safe failure mode.

### Scenario 2: Protocol Generator Not Provided (revision needed but unavailable)

**Cause**: Caller forgets to pass `protocol_generator` parameter, but revision is needed.

**Handling**:
```python
if revision_needed and protocol_generator is None:
    logger.error("Revision needed but Protocol Generator not provided")
    initial_scoring["high_risk_flags"].append(
        "REVISION NEEDED BUT NOT PERFORMED - Protocol Generator unavailable"
    )
    return initial_scoring
```

**Impact**: Original protocol delivered with additional high-risk flag. Therapist warned.

### Scenario 3: Revision Fails (Protocol Generator raises exception)

**Cause**: Protocol Generator's `revise_protocol()` method fails (API error, timeout, etc.).

**Handling**:
```python
try:
    revised_protocol = await protocol_generator.revise_protocol(...)
except Exception as e:
    logger.error(f"Revision failed: {e}")
    initial_scoring["high_risk_flags"].append(f"REVISION FAILED - {str(e)}")
    return initial_scoring  # Deliver original protocol with error flag
```

**Impact**: Original protocol delivered with error message. Therapist decides whether to use it.

### Scenario 4: Revised Protocol Scores Even Lower (regression)

**Cause**: Revision introduces new problems, final score < initial score.

**Handling**: Deliver revised protocol anyway (the system tried its best). Warning banner shows both scores:
```python
if score_after_revision < initial_score:
    result["warning_banner"] = (
        f"⚠️ CAUTION: Revision decreased confidence "
        f"({initial_score:.2f} → {score_after_revision:.2f}). "
        f"Manual review recommended."
    )
```

**Impact**: Therapist sees regression, knows to review carefully. Still better than delivering without any revision attempt.

---

## Evaluation Metrics

### 1. Calibration (System Confidence vs Human Judgment)

**What**: Do system scores correlate with expert therapist confidence ratings?

**How to Measure**:
1. Generate 50 protocols with uncertainty scores
2. Have 2-3 expert therapists independently rate confidence for each claim (0-10 scale)
3. Convert therapist ratings to 0.0-1.0 scale
4. Compute **Pearson correlation** between system scores and mean therapist scores

**Target**: r ≥ 0.60 (moderate correlation) for per-claim scores

**Publishable Finding**: "Per-claim uncertainty scores correlate with expert judgments at r = 0.68 (p < 0.001)"

### 2. Revision Effectiveness

**What**: Does the revision loop improve protocol quality?

**How to Measure**:
1. Select protocols where revision was triggered (global confidence < 0.50)
2. Measure:
   - **Confidence delta**: `score_after_revision - initial_score`
   - **High-risk claim reduction**: Count of claims < 0.50 before vs after
   - **Therapist quality ratings**: Do therapists rate revised protocols higher?

**Target**:
- Mean confidence improvement ≥ 0.15
- High-risk claim reduction ≥ 30%
- Revised protocols score ≥ 0.5 points higher on therapist quality ratings (5-point Likert)

**Publishable Finding**: "Revision loop improved mean confidence by 0.18 (p = 0.003) and reduced high-risk claims by 42%."

### 3. Revision Trigger Rate

**What**: What % of protocols score < 0.50 initially and need revision?

**How to Measure**: Track `revision_triggered` across 100+ protocols

**Expected**: 10-20% (if higher, KB may be insufficient; if lower, threshold may be too stringent)

**Publishable Finding**: "Revision loop was triggered for 16% of protocols, indicating the system appropriately identifies low-confidence cases."

### 4. False Positive Rate (Over-Flagging)

**What**: Does the system flag well-supported claims as low-confidence?

**How to Measure**:
1. Human experts review claims scored < 0.50
2. Label each as "correctly flagged" (actually unsupported) or "false positive" (well-supported but scored low)
3. Compute: `FP_rate = false_positives / total_flagged`

**Target**: FP rate < 20%

**Publishable Finding**: "System correctly identified 85% of low-confidence claims (FP rate = 15%)."

### 5. False Negative Rate (Under-Flagging)

**What**: Does the system miss low-confidence claims (score them high when they're unsupported)?

**How to Measure**:
1. Human experts review high-scored claims (≥ 0.70)
2. Label each as "truly supported" or "false negative" (actually unsupported)
3. Compute: `FN_rate = false_negatives / total_high_scored`

**Target**: FN rate < 10% (clinical safety critical — must not miss unsupported claims)

**Publishable Finding**: "False negative rate was 7%, indicating high sensitivity to unsupported claims."

---

## Performance Characteristics

### Latency

| Scenario | Latency | Breakdown |
|---|---|---|
| **No Revision** | 5-10 seconds | 1 LLM call (4000-6000 tokens) |
| **With Revision** | 15-25 seconds | 1 LLM call (scoring) + Protocol Generator re-generation + 1 LLM call (re-scoring) |

**Optimization Opportunities**:
- **Parallel pre-compute**: Start uncertainty scoring while Protocol Generator is still finishing (if using streaming)
- **Caching**: Cache KB chunk embeddings (already done in RAG pipeline)
- **Batching**: If generating multiple protocols, batch scoring calls

### Token Usage

| Scenario | Input Tokens | Output Tokens | Total |
|---|---|---|---|
| **No Revision** | 3000-5000 | 1000-1500 | 4000-6500 |
| **With Revision** | 6000-10000 | 2000-3000 | 8000-13000 |

**Cost (GPT-4o-mini at $0.15/$0.60 per 1M tokens):**
- No revision: ~$0.002-0.003 per protocol
- With revision: ~$0.005-0.008 per protocol

**Cost acceptable?** Yes. Even at scale (1000 protocols/month), cost is $2-8/month for uncertainty scoring.

### Throughput

**Single instance**: ~6-12 protocols/minute (no revision), ~2-4 protocols/minute (with revision)

**Scaling**: Horizontally scalable — each protocol is independent. Can run multiple UncertaintyScorer instances in parallel.

---

## Common Pitfalls

### Pitfall 1: Not Tracking KB Chunks from Upstream Agents

**Problem**: Protocol Generator uses KB chunks but does not pass them to Uncertainty Scorer.

**Symptom**: Scorer has no KB context, assigns low scores to everything.

**Fix**: Protocol Generator MUST track `kb_chunks_used` and include in output:
```python
# In Protocol Generator
self.kb_chunks_used = []  # Initialize

# After each KB query
chunks = await rag_service.search(...)
self.kb_chunks_used.extend(chunks)

# In output
return {
    "protocol": protocol,
    "kb_chunks_used": self.kb_chunks_used  # ← CRITICAL
}
```

### Pitfall 2: Infinite Revision Loops

**Problem**: Revision does not improve score, triggers another revision, ad infinitum.

**Fix**: **Hard limit of 1 revision iteration**. After 2 passes (initial + revision), deliver regardless.

### Pitfall 3: Revision Makes Things Worse

**Problem**: Revised protocol scores lower than original.

**Fix**: Deliver revised protocol anyway (the attempt was made), but add **regression warning**:
```python
if score_after_revision < initial_score:
    result["warning_banner"] = (
        f"⚠️ CAUTION: Revision decreased confidence "
        f"({initial_score:.2f} → {score_after_revision:.2f}). "
        f"Manual review recommended."
    )
```

### Pitfall 4: Scoring Non-Clinical Text

**Problem**: Scorer wastes tokens scoring session metadata, logistics, generic transitions.

**Fix**: Prompt explicitly lists what to score vs what to skip. Example:
```
DO NOT score:
- Generic transitions (e.g., "Then move to the next phase")
- Session logistics (e.g., "Welcome the patient")
- Non-clinical metadata (session title, duration fields)
```

### Pitfall 5: Over-Optimistic Scoring

**Problem**: LLM assigns high scores (0.8+) to weakly-supported claims.

**Fix**: Reinforce conservative calibration in prompt:
```
Be CONSERVATIVE. It is better to underestimate confidence than to overstate it.
When in doubt, score LOWER.
This is a clinical safety system — over-confidence is dangerous.
```

---

## Testing Strategy

### Unit Tests (Per-Method Testing)

**Test `score_protocol()`:**
```python
async def test_score_protocol_high_confidence():
    """Well-supported protocol should score ≥ 0.70"""
    scorer = UncertaintyScorer()
    result = await scorer.score_protocol(
        protocol=WELL_GROUNDED_PROTOCOL,
        kb_chunks=RELEVANT_KB_CHUNKS,
        clinical_summary=SUMMARY,
        blueprint=BLUEPRINT
    )
    assert result["global_confidence"] >= 0.70
    assert len(result["high_risk_flags"]) == 0

async def test_score_protocol_low_confidence():
    """Poorly-supported protocol should score < 0.50"""
    scorer = UncertaintyScorer()
    result = await scorer.score_protocol(
        protocol=POORLY_GROUNDED_PROTOCOL,
        kb_chunks=IRRELEVANT_KB_CHUNKS,
        clinical_summary=SUMMARY,
        blueprint=BLUEPRINT
    )
    assert result["global_confidence"] < 0.50
    assert result["revision_needed"] == True
```

**Test `_identify_revision_targets()`:**
```python
def test_identify_revision_targets():
    """Should extract claims < 0.50, sorted by confidence"""
    scorer = UncertaintyScorer()
    scoring_result = {
        "per_claim_scores": [
            {"claim_text": "A", "confidence": 0.85},
            {"claim_text": "B", "confidence": 0.35},
            {"claim_text": "C", "confidence": 0.28},
            {"claim_text": "D", "confidence": 0.65}
        ]
    }
    targets = scorer._identify_revision_targets(scoring_result)
    assert len(targets) == 2
    assert targets[0]["confidence"] == 0.28  # Lowest first
    assert targets[1]["confidence"] == 0.35
```

### Integration Tests (Full Execute Flow)

**Test No Revision Path:**
```python
async def test_execute_no_revision():
    """High-confidence protocol should NOT trigger revision"""
    scorer = UncertaintyScorer()
    result = await scorer.execute(
        protocol=WELL_GROUNDED_PROTOCOL,
        kb_chunks_used=KB_CHUNKS,
        clinical_summary=SUMMARY,
        blueprint=BLUEPRINT,
        protocol_generator=None  # Not needed
    )
    assert result["revision_triggered"] == False
    assert result["revised_protocol"] is None
```

**Test Revision Path:**
```python
async def test_execute_with_revision():
    """Low-confidence protocol should trigger revision loop"""
    scorer = UncertaintyScorer()
    mock_protocol_gen = MockProtocolGenerator()  # Returns improved protocol
    
    result = await scorer.execute(
        protocol=POORLY_GROUNDED_PROTOCOL,
        kb_chunks_used=KB_CHUNKS,
        clinical_summary=SUMMARY,
        blueprint=BLUEPRINT,
        protocol_generator=mock_protocol_gen
    )
    
    assert result["revision_triggered"] == True
    assert result["initial_score"] < 0.50
    assert result["score_after_revision"] > result["initial_score"]
    assert result["revised_protocol"] is not None
```

### Edge Case Tests

**Test: Protocol Generator Missing (revision needed):**
```python
async def test_revision_needed_but_no_generator():
    """Should deliver original protocol with error flag"""
    scorer = UncertaintyScorer()
    result = await scorer.execute(
        protocol=POORLY_GROUNDED_PROTOCOL,
        kb_chunks_used=KB_CHUNKS,
        clinical_summary=SUMMARY,
        blueprint=BLUEPRINT,
        protocol_generator=None  # ← MISSING
    )
    assert result["revision_triggered"] == False
    assert "Protocol Generator unavailable" in str(result["high_risk_flags"])
```

**Test: LLM Returns Invalid JSON:**
```python
async def test_invalid_json_response(monkeypatch):
    """Should return safe fallback (confidence 0.0)"""
    def mock_parse(*args, **kwargs):
        raise json.JSONDecodeError("test error", "", 0)
    
    monkeypatch.setattr(json, "loads", mock_parse)
    
    scorer = UncertaintyScorer()
    result = await scorer.score_protocol(...)
    
    assert result["global_confidence"] == 0.0
    assert "SCORING FAILED" in result["high_risk_flags"][0]
```

### Regression Tests (Revision Effectiveness)

**Test: Revision Actually Improves Score:**
```python
async def test_revision_improves_score():
    """Revised protocol should score higher than original"""
    scorer = UncertaintyScorer()
    mock_protocol_gen = MockProtocolGenerator()  # Simulates good revision
    
    result = await scorer.execute(
        protocol=POORLY_GROUNDED_PROTOCOL,
        kb_chunks_used=KB_CHUNKS,
        clinical_summary=SUMMARY,
        blueprint=BLUEPRINT,
        protocol_generator=mock_protocol_gen
    )
    
    improvement = result["score_after_revision"] - result["initial_score"]
    assert improvement > 0.10, f"Expected ≥0.10 improvement, got {improvement:.3f}"
```

---

## Future Enhancements

### v1 → v2: Multi-Sample Consistency

**Problem**: Single LLM call is unstable — minor prompt variations can change scores significantly.

**Solution**: Generate 3 protocol variants, score each, measure **inter-sample agreement**:
```python
# Generate 3 variants with slight prompt variation
variants = [
    await protocol_generator.execute(..., seed=1),
    await protocol_generator.execute(..., seed=2),
    await protocol_generator.execute(..., seed=3)
]

# Score each
scores = [await scorer.score_protocol(v) for v in variants]

# Compute consistency
mean_score = np.mean([s["global_confidence"] for s in scores])
std_dev = np.std([s["global_confidence"] for s in scores])

if std_dev > 0.15:
    flag_as_unstable()  # High variance → low consistency → low trust
```

**Research Value**: "Protocols with high inter-sample variance (σ > 0.15) received lower therapist ratings, validating consistency as a trust signal."

### v1 → v2: NLI-Based Entailment Verification

**Problem**: LLM scoring is subjective — "does KB support this claim?" is a semantic judgment.

**Solution**: Use **Natural Language Inference (NLI)** model to verify entailment:
```python
from transformers import pipeline

nli = pipeline("text-classification", model="microsoft/deberta-large-mnli")

for claim in protocol_claims:
    for kb_chunk in kb_chunks:
        result = nli({"premise": kb_chunk, "hypothesis": claim})
        # result: "entailment" (KB implies claim), "neutral", "contradiction"
        if result == "entailment":
            score_high()
```

**Research Value**: "NLI-verified claims showed 20% higher therapist agreement than LLM-only scoring."

### v1 → v2: Claim-Level Revision (Not Protocol-Wide)

**Problem**: Current design re-generates entire protocol. Inefficient if only 2-3 claims need fixing.

**Solution**: **Surgical revision** — replace only low-confidence claims:
```python
for claim in low_confidence_claims:
    revised_claim = await llm.generate(
        prompt=f"Revise this claim to be KB-grounded: '{claim}'. Use these KB chunks: {kb_chunks}",
        max_tokens=100
    )
    protocol.replace(claim, revised_claim)
```

**Benefit**: Faster (no full re-generation), preserves high-confidence claims exactly.

### v1 → v2: Uncertainty Over Time (Longitudinal Tracking)

**Problem**: No tracking of whether uncertainty improves as therapist adds more KB documents.

**Solution**: Store uncertainty scores for each patient over time:
```sql
CREATE TABLE protocol_uncertainty_history (
    protocol_id INT,
    patient_id INT,
    week INT,
    global_confidence FLOAT,
    num_high_risk_claims INT,
    kb_size_at_time INT
);
```

**Research Value**: "As therapists added KB documents, average protocol confidence increased from 0.68 to 0.81 (r = 0.72, p < 0.001)."

### v1 → v2: Active Learning (KB Gap Identification)

**Problem**: System knows KB is insufficient but does not tell therapist *what* is missing.

**Solution**: Identify **KB gaps** from low-confidence claims:
```python
kb_gaps = [
    claim["claim_text"]
    for claim in scoring["per_claim_scores"]
    if claim["kb_evidence"] == "none"
]

recommendation = f"To improve confidence, add KB documents covering: {kb_gaps}"
```

**Benefit**: Guides therapist KB curation. Active learning loop.

---

## LangGraph Integration

### Node Definition

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict

class ProtocolState(TypedDict):
    patient_id: int
    therapist_id: int
    # ... upstream fields
    protocol: Dict[str, Any]
    kb_chunks_used: List[Dict[str, Any]]
    clinical_summary: Dict[str, Any]
    blueprint: Dict[str, Any]
    # Uncertainty Scorer outputs:
    scoring_result: Dict[str, Any]
    final_protocol: Dict[str, Any]
    confidence_metadata: Dict[str, Any]

async def uncertainty_scorer_node(state: ProtocolState) -> Dict:
    """
    LangGraph node for Uncertainty Scorer.
    
    Handles scoring + revision loop internally.
    Returns final protocol (original or revised).
    """
    from app.ai_agents import UncertaintyScorer, ProtocolGeneratorAgent
    
    scorer = UncertaintyScorer()
    protocol_generator = ProtocolGeneratorAgent()
    
    result = await scorer.execute(
        protocol=state["protocol"],
        kb_chunks_used=state["kb_chunks_used"],
        clinical_summary=state["clinical_summary"],
        blueprint=state["blueprint"],
        protocol_generator=protocol_generator
    )
    
    return {
        "scoring_result": result,
        "final_protocol": (
            result["revised_protocol"]
            if result["revision_triggered"]
            else state["protocol"]
        ),
        "confidence_metadata": result["metadata"]
    }
```

### Graph Setup

```python
workflow = StateGraph(ProtocolState)

# Add nodes
workflow.add_node("protocol_generator", protocol_generator_node)
workflow.add_node("uncertainty_scorer", uncertainty_scorer_node)

# Set edges
workflow.add_edge("protocol_generator", "uncertainty_scorer")
workflow.add_edge("uncertainty_scorer", END)

# Compile
app = workflow.compile()
```

**Note**: Revision loop is **implicit** (handled inside `uncertainty_scorer_node`). No conditional edge needed in graph.

### Alternative: Explicit Revision Edge (Optional)

If you want graph to show revision loop visually:

```python
def should_revise(state: ProtocolState) -> str:
    """Check if revision needed AND not already attempted."""
    scoring = state.get("scoring_result", {})
    if (scoring.get("global_confidence", 1.0) < 0.50
        and not state.get("revision_attempted", False)):
        return "revise"
    return "end"

workflow.add_conditional_edges(
    "uncertainty_scorer",
    should_revise,
    {
        "revise": "protocol_generator",  # Loop back
        "end": END
    }
)

# Mark revision attempted to prevent infinite loop
async def uncertainty_scorer_node(state: ProtocolState) -> Dict:
    result = await scorer.execute(...)
    return {
        "scoring_result": result,
        "revision_attempted": result["revision_triggered"],
        ...
    }
```

**Recommendation**: Use **implicit** revision (handled in node). Cleaner graph topology.

---

## Conclusion

The **Uncertainty Scorer** is not just another agent — it is **the research contribution** that makes this system publishable.

**What it provides:**
- ✅ **Quantified epistemic uncertainty** (global + per-claim)
- ✅ **Self-correction mechanism** (revision loop)
- ✅ **Calibrated trust signals** (correlate with expert judgment)
- ✅ **Clinical safety guarantee** (low-confidence protocols flagged/revised)

**Why it matters:**
- Answers the reviewer question: "How do you know it's not hallucinating?"
- Enables evaluable claims about confidence calibration
- Demonstrates AI self-improvement (revision loop)
- Provides practical value (therapists see which claims to trust)

**Next steps:**
1. ✅ Implement Uncertainty Scorer (complete)
2. 🔲 Implement `Protocol Generator.revise_protocol()` method
3. 🔲 Test full pipeline with revision loop (Agents 1-8)
4. 🔲 Recruit therapists for calibration study (50 protocols, 2-3 experts)
5. 🔲 Measure revision effectiveness (confidence delta, claim reduction)
6. 🔲 Write results section for journal paper

**You now have a complete, research-grade uncertainty scoring system.** 🎉

---

**Document Version**: 1.0  
**Last Updated**: February 11, 2026  
**Author**: Nirbaan AI Research Team
