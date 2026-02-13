"""
Agent 8: Uncertainty Scorer with Revision Loop

THE CORE RESEARCH CONTRIBUTION — This agent elevates the system from "cool undergrad project" 
to "publishable research."

Purpose:
--------
Quantifies epistemic uncertainty for generated therapy protocols at TWO granularities:
1. Global confidence score (0.0-1.0): Overall KB-groundedness of the entire protocol
2. Per-claim scores: Individual confidence for every clinically significant statement

If the global confidence score falls below 0.50, the agent triggers a CONDITIONAL REVISION LOOP:
- Identifies the weakest claims (those dragging the score down)
- Sends revision instructions back to the Protocol Generator
- Re-scores the revised protocol
- Delivers the protocol with appropriate warnings if still low

Maximum iterations: 1 revision cycle (Generate → Score → Revise → Re-Score → Deliver)

Research Value:
---------------
This mechanism enables you to measure:
- Revision trigger rate (% of protocols scoring < 0.50 initially)
- Confidence improvement after revision (delta between scores)
- Content changes introduced by revision (semantic diff)
- Correlation between system scores and expert therapist judgments

These are all reportable findings for journal publication.

Architecture Specs:
-------------------
From NIRBAAN_AI_REFINED_ARCHITECTURE.md, Agent 9 (lines 449-476)

Input:
------
- Full generated protocol (from Protocol Generator)
- All KB chunks used across the pipeline (from all RAG-using agents)
- Clinical summary (for context)
- Blueprint (to understand session structure)

Output:
-------
{
    "global_confidence": 0.75,  # 0.0-1.0
    "per_claim_scores": [
        {
            "claim_text": "Begin with 3-minute breathing exercise",
            "confidence": 0.92,
            "kb_evidence": "Chunk ID: doc_12_p3 - 'Breathing exercises should...'",
            "reasoning": "Directly supported by KB chunk with explicit timing guidance"
        },
        {
            "claim_text": "Patient should practice exposure 5 times weekly",
            "confidence": 0.35,
            "kb_evidence": "none",
            "reasoning": "Specific frequency not found in KB; appears to be extrapolation"
        }
    ],
    "high_risk_flags": [
        "Claim about exposure frequency (score: 0.35) lacks KB support"
    ],
    "overall_assessment": "Protocol is moderately well-grounded. 3 out of 24 claims lack sufficient KB evidence.",
    "revision_needed": false,
    "revision_triggered": false,  # True if we went through revision loop
    "score_after_revision": null  # Populated if revision happened
}

Clinical Safety:
----------------
- Claims scored < 0.50 are flagged as HIGH RISK
- If global score < 0.50, protocol is NOT delivered as-is; revision is mandatory
- After revision, protocol is delivered even if still low, but with PROMINENT WARNING BANNER
- Therapist receives explicit visibility into which claims are well-supported vs uncertain

LangGraph Integration:
----------------------
This agent is the FINAL node before __END__. It has a conditional edge:
- If global_confidence < 0.50 on first pass → Loop back to Protocol Generator with revision instructions
- After revision (or if score was acceptable) → Proceed to __END__

Usage Example:
--------------
```python
from app.ai_agents.uncertainty_scorer import UncertaintyScorer

scorer = UncertaintyScorer()

# Initial scoring (Pass 1)
result = await scorer.execute(
    protocol=generated_protocol,
    kb_chunks_used=all_kb_chunks,
    clinical_summary=clinical_summary,
    blueprint=blueprint,
    protocol_generator=protocol_generator_instance  # For revision if needed
)

if result["revision_triggered"]:
    print(f"Revision was triggered. Initial score: {result['global_confidence']}")
    print(f"Score after revision: {result['score_after_revision']}")
```

Author: Nirbaan AI Research Team
Date: February 11, 2026
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class UncertaintyScorer:
    """
    Agent 8: Uncertainty Scorer with Revision Loop
    
    Scores protocol confidence at two granularities (global + per-claim) and conditionally
    triggers revision if confidence is too low.
    
    This is THE CORE RESEARCH CONTRIBUTION of the Nirbaan AI system.
    """
    
    def __init__(self):
        """Initialize the Uncertainty Scorer with OpenAI client."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        self.revision_threshold = float(os.getenv("UNCERTAINTY_REVISION_THRESHOLD", "0.50"))
        self.high_risk_threshold = float(os.getenv("UNCERTAINTY_HIGH_RISK_THRESHOLD", "0.50"))
        
        logger.info(f"UncertaintyScorer initialized with model={self.model}, "
                   f"revision_threshold={self.revision_threshold}")
    
    def _build_scoring_prompt(
        self,
        protocol: Dict[str, Any],
        kb_chunks: List[Dict[str, Any]],
        clinical_summary: Dict[str, Any],
        blueprint: Dict[str, Any]
    ) -> str:
        """
        Build the system prompt for uncertainty scoring.
        
        This prompt instructs the LLM to:
        1. Extract all clinically significant claims from the protocol
        2. Score each claim's KB-groundedness (0.0-1.0)
        3. Provide evidence and reasoning for each score
        4. Compute a global confidence score
        5. Flag high-risk claims
        
        Args:
            protocol: The generated therapy protocol to score
            kb_chunks: All KB chunks used during protocol generation
            clinical_summary: Clinical context
            blueprint: Session blueprint (for structural understanding)
        
        Returns:
            System prompt string
        """
        # Format KB chunks for prompt
        kb_context = "\n\n".join([
            f"CHUNK {i+1} (ID: {chunk.get('id', 'unknown')}):\n{chunk.get('content', '')}"
            for i, chunk in enumerate(kb_chunks)
        ])
        
        protocol_text = json.dumps(protocol, indent=2) if isinstance(protocol, dict) else str(protocol)
        
        prompt = f"""You are an epistemic uncertainty scorer for clinical therapy protocols.

Your task is to score the KB-groundedness of a generated therapy session protocol. You will:
1. Extract ALL clinically significant claims from the protocol
2. Score each claim's confidence (0.0-1.0) based on how well it is supported by the KB
3. Identify the specific KB evidence supporting each claim (or "none" if unsupported)
4. Explain your reasoning for each score
5. Compute a global confidence score for the entire protocol
6. Flag claims that are HIGH RISK (score < {self.high_risk_threshold})

SCORING RUBRIC:
- 0.9-1.0: Directly stated in KB with explicit details
- 0.7-0.89: Strongly supported by KB, minor details inferred
- 0.5-0.69: Partially supported, some extrapolation from KB principles
- 0.3-0.49: Weakly supported, significant extrapolation
- 0.0-0.29: Not supported by KB, appears to be hallucination or general knowledge

WHAT COUNTS AS A "CLINICALLY SIGNIFICANT CLAIM":
- Specific techniques or exercises mentioned (e.g., "3-minute breathing exercise")
- Clinical instructions (e.g., "If patient shows anxiety, pause the exposure")
- Homework assignments (e.g., "Practice exposure 3 times this week")
- Timing or dosage (e.g., "Spend 15 minutes on cognitive restructuring")
- Contraindications or safety guidance (e.g., "Avoid this technique if...")
- Expected outcomes (e.g., "This should reduce panic by 30%")

DO NOT score:
- Generic transitions (e.g., "Then move to the next phase")
- Session logistics (e.g., "Welcome the patient")
- Non-clinical metadata

CLINICAL CONTEXT:
{json.dumps(clinical_summary, indent=2)}

SESSION BLUEPRINT:
{json.dumps(blueprint, indent=2)}

KB CHUNKS USED IN PROTOCOL GENERATION:
{kb_context}

PROTOCOL TO SCORE:
{protocol_text}

Return your scoring as a JSON object with this EXACT structure:
{{
    "global_confidence": 0.75,
    "per_claim_scores": [
        {{
            "claim_text": "exact text of the claim from the protocol",
            "confidence": 0.85,
            "kb_evidence": "Chunk ID and relevant excerpt, or 'none'",
            "reasoning": "why this score was assigned"
        }}
    ],
    "high_risk_flags": [
        "description of each high-risk claim (score < {self.high_risk_threshold})"
    ],
    "overall_assessment": "1-2 sentence summary of protocol groundedness",
    "revision_needed": false
}}

The global_confidence should be a WEIGHTED AVERAGE of per-claim scores, with higher weight on claims that have greater clinical significance (e.g., safety-critical claims).

Set "revision_needed" to true if global_confidence < {self.revision_threshold}.

Be CONSERVATIVE. It is better to underestimate confidence than to overstate it. This is a clinical safety system."""
        
        return prompt
    
    async def score_protocol(
        self,
        protocol: Dict[str, Any],
        kb_chunks: List[Dict[str, Any]],
        clinical_summary: Dict[str, Any],
        blueprint: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Score the protocol's uncertainty (Pass 1 or Pass 2).
        
        This is the CORE SCORING LOGIC. It:
        1. Builds the scoring prompt with protocol + KB chunks
        2. Calls OpenAI with structured JSON output
        3. Validates the scoring result
        4. Returns global + per-claim scores
        
        Args:
            protocol: Generated therapy protocol
            kb_chunks: All KB chunks used during generation
            clinical_summary: Clinical context
            blueprint: Session blueprint
        
        Returns:
            Scoring result with global confidence, per-claim scores, and flags
        """
        logger.info("Starting uncertainty scoring...")
        
        system_prompt = self._build_scoring_prompt(
            protocol=protocol,
            kb_chunks=kb_chunks,
            clinical_summary=clinical_summary,
            blueprint=blueprint
        )
        
        try:
            # Call OpenAI with structured output
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "Score the protocol as instructed. Return valid JSON."}
                ],
                temperature=0,  # DETERMINISTIC for safety
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Validate required fields
            required_fields = ["global_confidence", "per_claim_scores", "high_risk_flags", 
                             "overall_assessment", "revision_needed"]
            for field in required_fields:
                if field not in result:
                    logger.error(f"Missing required field in scoring result: {field}")
                    result[field] = None if field != "per_claim_scores" else []
                    if field == "high_risk_flags":
                        result[field] = []
            
            # Ensure global_confidence is a float between 0.0 and 1.0
            if result["global_confidence"] is not None:
                result["global_confidence"] = max(0.0, min(1.0, float(result["global_confidence"])))
            
            logger.info(f"Scoring complete. Global confidence: {result['global_confidence']}")
            logger.info(f"Number of claims scored: {len(result.get('per_claim_scores', []))}")
            logger.info(f"High-risk flags: {len(result.get('high_risk_flags', []))}")
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse scoring result as JSON: {e}")
            # Return a conservative fallback
            return {
                "global_confidence": 0.0,
                "per_claim_scores": [],
                "high_risk_flags": ["SCORING FAILED - Could not parse LLM output"],
                "overall_assessment": "Scoring failed due to JSON parsing error",
                "revision_needed": True,
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error during scoring: {e}")
            return {
                "global_confidence": 0.0,
                "per_claim_scores": [],
                "high_risk_flags": ["SCORING FAILED - Unexpected error"],
                "overall_assessment": f"Scoring failed: {str(e)}",
                "revision_needed": True,
                "error": str(e)
            }
    
    def _identify_revision_targets(
        self,
        scoring_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Identify low-confidence claims that need revision.
        
        Extracts all claims with confidence < high_risk_threshold (default 0.50)
        and prepares them for revision instructions.
        
        Args:
            scoring_result: Output from score_protocol()
        
        Returns:
            List of low-confidence claims with their scores and reasoning
        """
        per_claim_scores = scoring_result.get("per_claim_scores", [])
        
        revision_targets = [
            claim for claim in per_claim_scores
            if claim.get("confidence", 1.0) < self.high_risk_threshold
        ]
        
        # Sort by confidence (lowest first) — prioritize the worst claims
        revision_targets.sort(key=lambda x: x.get("confidence", 0.0))
        
        logger.info(f"Identified {len(revision_targets)} claims needing revision")
        
        return revision_targets
    
    def _build_revision_instructions(
        self,
        revision_targets: List[Dict[str, Any]],
        kb_chunks: List[Dict[str, Any]],
        scoring_result: Dict[str, Any]
    ) -> str:
        """
        Build explicit revision instructions to send back to Protocol Generator.
        
        These instructions tell the Protocol Generator:
        1. Which specific claims to revise or remove
        2. Why those claims scored low
        3. Which KB chunks to use for grounding replacements
        4. What NOT to change (well-supported claims)
        
        Args:
            revision_targets: Low-confidence claims needing revision
            kb_chunks: Available KB chunks for grounding
            scoring_result: Full scoring result
        
        Returns:
            Revision instruction text
        """
        if not revision_targets:
            return ""
        
        instructions = f"""REVISION REQUIRED — Global confidence score: {scoring_result['global_confidence']:.2f}

The following {len(revision_targets)} claims scored below {self.high_risk_threshold} and must be revised or removed:

"""
        
        for i, target in enumerate(revision_targets, 1):
            instructions += f"""
{i}. CLAIM: "{target['claim_text']}"
   SCORE: {target.get('confidence', 0.0):.2f}
   REASON: {target.get('reasoning', 'No reasoning provided')}
   KB EVIDENCE: {target.get('kb_evidence', 'none')}
   
   ACTION: Replace with a KB-grounded alternative OR remove if no KB support exists.
"""
        
        instructions += f"""

AVAILABLE KB CHUNKS FOR REVISION:
{len(kb_chunks)} chunks are available. Use ONLY these for grounding. Do not introduce new claims without KB support.

HIGH-CONFIDENCE CLAIMS (DO NOT CHANGE):
"""
        
        high_confidence_claims = [
            claim for claim in scoring_result.get("per_claim_scores", [])
            if claim.get("confidence", 0.0) >= 0.70
        ]
        
        for claim in high_confidence_claims[:5]:  # Show top 5 as examples
            instructions += f"- \"{claim['claim_text']}\" (score: {claim['confidence']:.2f})\n"
        
        instructions += """
REVISION GUIDELINES:
1. Replace low-confidence claims with KB-grounded alternatives when possible
2. Remove claims entirely if no KB support can be found
3. Preserve all high-confidence claims unchanged
4. Maintain session timing and structure from blueprint
5. Ensure revised protocol is still coherent and clinically complete
6. Do NOT introduce new unsupported claims to fill gaps

This is the ONLY revision pass. Make it count."""
        
        return instructions
    
    async def execute(
        self,
        protocol: Dict[str, Any],
        kb_chunks_used: List[Dict[str, Any]],
        clinical_summary: Dict[str, Any],
        blueprint: Dict[str, Any],
        protocol_generator: Optional[Any] = None  # Protocol Generator instance for revision
    ) -> Dict[str, Any]:
        """
        Main execution method for LangGraph integration.
        
        Implements the full uncertainty scoring + revision loop:
        1. Score the protocol (Pass 1)
        2. If global_confidence < threshold → Trigger revision
        3. Call Protocol Generator with revision instructions
        4. Re-score the revised protocol (Pass 2)
        5. Return final result with metadata
        
        Maximum 1 revision iteration.
        
        Args:
            protocol: Generated therapy protocol
            kb_chunks_used: All KB chunks used during generation
            clinical_summary: Clinical context
            blueprint: Session blueprint
            protocol_generator: Protocol Generator instance (needed for revision)
        
        Returns:
            {
                "global_confidence": 0.75,
                "per_claim_scores": [...],
                "high_risk_flags": [...],
                "overall_assessment": "...",
                "revision_triggered": false,
                "score_after_revision": null,
                "revised_protocol": null,
                "metadata": {...}
            }
        """
        logger.info("=" * 80)
        logger.info("AGENT 8: UNCERTAINTY SCORER WITH REVISION LOOP")
        logger.info("=" * 80)
        
        start_time = datetime.now()
        
        # PASS 1: Initial scoring
        logger.info("PASS 1: Initial uncertainty scoring...")
        initial_scoring = await self.score_protocol(
            protocol=protocol,
            kb_chunks=kb_chunks_used,
            clinical_summary=clinical_summary,
            blueprint=blueprint
        )
        
        global_confidence = initial_scoring.get("global_confidence", 0.0)
        revision_needed = global_confidence < self.revision_threshold
        
        # Check if revision is needed and feasible
        if revision_needed:
            logger.warning(f"Global confidence ({global_confidence:.2f}) below threshold "
                         f"({self.revision_threshold}). REVISION REQUIRED.")
            
            if protocol_generator is None:
                logger.error("Protocol Generator not provided - cannot perform revision!")
                # Return initial scoring with error flagrevision_triggered = False
                revised_protocol = None
                final_scoring = initial_scoring
                final_scoring["high_risk_flags"].append(
                    "REVISION NEEDED BUT NOT PERFORMED - Protocol Generator unavailable"
                )
            else:
                # Trigger revision loop
                logger.info("Triggering revision loop...")
                
                # Identify low-confidence claims
                revision_targets = self._identify_revision_targets(initial_scoring)
                
                # Build revision instructions
                revision_instructions = self._build_revision_instructions(
                    revision_targets=revision_targets,
                    kb_chunks=kb_chunks_used,
                    scoring_result=initial_scoring
                )
                
                logger.info(f"Revision instructions prepared ({len(revision_instructions)} chars)")
                
                # Call Protocol Generator with revision instructions
                # NOTE: The Protocol Generator's execute() method would need to accept
                # an optional "revision_instructions" parameter
                try:
                    logger.info("Calling Protocol Generator for revision...")
                    
                    # This assumes Protocol Generator has a revise() method or accepts revision_instructions
                    if hasattr(protocol_generator, 'revise_protocol'):
                        revised_protocol = await protocol_generator.revise_protocol(
                            original_protocol=protocol,
                            revision_instructions=revision_instructions,
                            kb_chunks=kb_chunks_used,
                            clinical_summary=clinical_summary,
                            blueprint=blueprint
                        )
                    else:
                        # Fallback: treat revision_instructions as additional context
                        logger.warning("Protocol Generator lacks revise_protocol() method - using fallback")
                        revised_protocol = protocol  # No revision possible
                    
                    # PASS 2: Re-score the revised protocol
                    logger.info("PASS 2: Re-scoring revised protocol...")
                    final_scoring = await self.score_protocol(
                        protocol=revised_protocol,
                        kb_chunks=kb_chunks_used,
                        clinical_summary=clinical_summary,
                        blueprint=blueprint
                    )
                    
                    revision_triggered = True
                    
                    logger.info(f"Revision complete. New global confidence: "
                              f"{final_scoring.get('global_confidence', 0.0):.2f}")
                    
                except Exception as e:
                    logger.error(f"Revision failed: {e}")
                    revision_triggered = False
                    revised_protocol = None
                    final_scoring = initial_scoring
                    final_scoring["high_risk_flags"].append(
                        f"REVISION FAILED - {str(e)}"
                    )
        else:
            logger.info(f"Global confidence ({global_confidence:.2f}) acceptable. No revision needed.")
            revision_triggered = False
            revised_protocol = None
            final_scoring = initial_scoring
        
        # Calculate latency
        end_time = datetime.now()
        latency_seconds = (end_time - start_time).total_seconds()
        
        # Prepare final result
        result = {
            "global_confidence": final_scoring.get("global_confidence", 0.0),
            "per_claim_scores": final_scoring.get("per_claim_scores", []),
            "high_risk_flags": final_scoring.get("high_risk_flags", []),
            "overall_assessment": final_scoring.get("overall_assessment", ""),
            "revision_triggered": revision_triggered,
            "initial_score": global_confidence,  # Preserve initial score
            "score_after_revision": final_scoring.get("global_confidence") if revision_triggered else None,
            "revised_protocol": revised_protocol,  # Include revised protocol if generated
            "metadata": {
                "agent": "UncertaintyScorer",
                "timestamp": end_time.isoformat(),
                "latency_seconds": latency_seconds,
                "model": self.model,
                "revision_threshold": self.revision_threshold,
                "high_risk_threshold": self.high_risk_threshold,
                "num_claims_scored": len(final_scoring.get("per_claim_scores", [])),
                "num_high_risk_claims": len(final_scoring.get("high_risk_flags", [])),
                "revision_triggered": revision_triggered,
                "num_kb_chunks_evaluated": len(kb_chunks_used)
            }
        }
        
        # Add warning banner if score is still low after revision
        if revision_triggered and result["global_confidence"] < self.revision_threshold:
            result["warning_banner"] = (
                f"⚠️ WARNING: This protocol has undergone revision but still has low confidence "
                f"({result['global_confidence']:.2f}). Review carefully before use. "
                f"{len(result['high_risk_flags'])} high-risk claims identified."
            )
        
        logger.info("=" * 80)
        logger.info(f"UNCERTAINTY SCORING COMPLETE")
        logger.info(f"  Initial Score: {global_confidence:.3f}")
        if revision_triggered:
            logger.info(f"  Final Score: {result['global_confidence']:.3f}")
            logger.info(f"  Improvement: {result['global_confidence'] - global_confidence:+.3f}")
        logger.info(f"  Claims Scored: {result['metadata']['num_claims_scored']}")
        logger.info(f"  High-Risk Flags: {result['metadata']['num_high_risk_claims']}")
        logger.info(f"  Revision Triggered: {revision_triggered}")
        logger.info(f"  Latency: {latency_seconds:.2f}s")
        logger.info("=" * 80)
        
        return result
