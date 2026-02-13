"""
Safety Gate Agent - LLM + RAG for Contraindication Screening (Agent 5)

This agent did not exist in the initial plan. It addresses a real clinical safety requirement.

What it does:
- Reviews the blueprint against patient's full clinical profile
- Identifies potential contraindications or safety concerns
- Queries KB for contraindication information, cautions, and guidelines
- Outputs safety flags that feed into Clarification Agent

Why it matters:
- Clinical safety is #1 concern for reviewers
- Demonstrates responsible AI design
- Evaluable by seeding test cases with known contraindications
- Publishable contribution: explicit safety screening layer

Safety checks:
1. Do proposed techniques conflict with comorbid conditions?
2. Are there trauma-related contraindications for proposed activities?
3. Does progression pace match KB recommendations for severity level?
4. Has therapist explicitly noted any inappropriate techniques for this patient?
"""
from typing import Dict, Any, List, Optional
import os
from openai import OpenAI
from sqlalchemy.orm import Session
from app.resources.rag_service import RAGService

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")


class SafetyGateAgent:
    """
    Agent 5: Safety Gate - Contraindication and safety screening
    
    This agent sits between Blueprint Generator and Clarification Agent.
    It performs KB-grounded safety checks before detailed protocol generation.
    """
    
    def __init__(self, db: Session):
        """
        Initialize Safety Gate Agent
        
        Args:
            db: SQLAlchemy database session (for RAG queries)
        """
        self.db = db
        self.agent_name = "SafetyGateAgent"
        self.llm_model = LLM_MODEL
        self.rag_service = RAGService()
        
    def _build_safety_screening_prompt(
        self,
        blueprint: Dict[str, Any],
        clinical_summary: str,
        patient_conditions: str,
        therapist_notes_summary: str = None
    ) -> str:
        """
        Build system prompt for safety screening
        
        This prompt guides the LLM to:
        1. Review proposed techniques against patient profile
        2. Identify potential contraindications
        3. Check KB for safety guidelines
        4. Flag concerns for therapist review
        """
        notes_section = ""
        if therapist_notes_summary:
            notes_section = f"""
THERAPIST NOTES & CONCERNS:
{therapist_notes_summary}
"""
        
        return f"""You are a clinical safety screening expert reviewing a proposed therapy session blueprint.

YOUR TASK: Identify potential contraindications, safety concerns, or mismatches between the proposed interventions and the patient's specific situation.

PATIENT CLINICAL PROFILE:
{clinical_summary}

PATIENT CONDITIONS:
{patient_conditions}
{notes_section}

PROPOSED BLUEPRINT:
{self._format_blueprint(blueprint)}

KB SAFETY INFORMATION:
{{kb_context}}

CRITICAL SAFETY CHECKS:
1. **Comorbidity Conflicts:** Do any proposed techniques conflict with the patient's conditions?
   - Example: Exposure therapy contraindicated for certain trauma histories
   - Example: Mindfulness exercises may be problematic for dissociative symptoms
   
2. **Trauma-Related Contraindications:** Are there techniques that could re-traumatize?
   - Check patient's trauma history
   - Review KB for contraindications specific to this trauma type
   
3. **Progression Pace:** Is the proposed pace appropriate for patient's severity?
   - Too aggressive for current functioning level?
   - Does KB recommend slower/faster progression for this stage?
   
4. **Therapist-Noted Restrictions:** Has the therapist explicitly flagged certain approaches as inappropriate?
   - Review therapist notes for prior concerns
   - Check for documented patient preferences or boundaries

5. **Medication Interactions:** Any techniques that interact with patient's medications?
   - Check KB for medication-related cautions
   
6. **Cultural/Religious Considerations:** Any techniques that may conflict with patient values?

OUTPUT FORMAT:
{{
    "safety_flags": [
        {{
            "severity": "high/medium/low",
            "concern_type": "type of concern (comorbidity/trauma/pace/therapist_restriction/medication/cultural)",
            "concern_description": "detailed description of the safety concern",
            "affected_blueprint_component": "which phase/activity is affected",
            "kb_evidence": "KB source that raised this concern (or 'patient_data' if from clinical profile)",
            "suggested_modification": "recommended change or alternative approach",
            "requires_therapist_decision": true/false
        }}
    ],
    "overall_risk_level": "safe/caution/high_risk",
    "proceed_recommendation": "proceed/proceed_with_modifications/therapist_review_required",
    "screening_notes": "additional context or observations"
}}

If NO safety concerns are identified, return:
{{
    "safety_flags": [],
    "overall_risk_level": "safe",
    "proceed_recommendation": "proceed",
    "screening_notes": "No contraindications or safety concerns identified."
}}

IMPORTANT: 
- Be conservative - flag anything that raises concern
- Cite specific KB sources when available
- If KB lacks contraindication information but concern exists based on clinical judgment, flag it with "requires_therapist_decision": true
- Better to over-flag than miss a safety issue"""

    def _format_blueprint(self, blueprint: Dict[str, Any]) -> str:
        """Format blueprint for readability in prompt"""
        if not blueprint:
            return "No blueprint provided"
        
        formatted = []
        
        # Extract key information from blueprint
        if isinstance(blueprint, dict):
            if "phases" in blueprint:
                formatted.append("PHASES:")
                for idx, phase in enumerate(blueprint["phases"], 1):
                    formatted.append(f"\n{idx}. {phase.get('name', 'Unnamed Phase')}")
                    formatted.append(f"   Time: {phase.get('duration', 'N/A')} minutes")
                    formatted.append(f"   Activities: {', '.join(phase.get('activities', []))}")
                    formatted.append(f"   Techniques: {', '.join(phase.get('techniques', []))}")
            
            if "materials_needed" in blueprint:
                formatted.append(f"\nMATERIALS: {', '.join(blueprint['materials_needed'])}")
            
            if "homework_preview" in blueprint:
                formatted.append(f"\nHOMEWORK: {blueprint['homework_preview']}")
        
        return "\n".join(formatted) if formatted else str(blueprint)
    
    def _query_kb_for_safety_info(
        self,
        therapist_id: int,
        blueprint: Dict[str, Any],
        patient_conditions: str
    ) -> List[Dict[str, Any]]:
        """
        Query KB for contraindication and safety information
        
        Args:
            therapist_id: Therapist's ID for KB scoping
            blueprint: The proposed session blueprint
            patient_conditions: Patient's conditions/diagnoses
            
        Returns:
            List of relevant KB chunks about safety and contraindications
        """
        # Extract techniques from blueprint for targeted safety query
        techniques = []
        if isinstance(blueprint, dict) and "phases" in blueprint:
            for phase in blueprint.get("phases", []):
                techniques.extend(phase.get("techniques", []))
                techniques.extend(phase.get("activities", []))
        
        # Build safety-focused query
        query_parts = [
            "contraindications",
            "cautions",
            "safety guidelines",
            "warnings",
            patient_conditions
        ]
        
        if techniques:
            query_parts.extend(techniques[:3])  # Add up to 3 main techniques
        
        query = " ".join(query_parts)
        
        # Retrieve safety-related chunks (top_k=6 as per architecture)
        chunks = self.rag_service.retrieve_chunks(
            db=self.db,
            therapist_id=therapist_id,
            query=query,
            top_k=6
        )
        
        return chunks
    
    def _check_kb_sufficiency(self, chunks: List[Dict[str, Any]], threshold: float = 0.40) -> bool:
        """
        Check if retrieved KB chunks are sufficient for safety screening
        
        Note: Lower threshold (0.40) than other agents because:
        - Safety info may not always be explicitly stated in KB
        - LLM can still flag concerns based on clinical judgment
        - Better to proceed with caution than halt completely
        
        Args:
            chunks: Retrieved KB chunks
            threshold: Minimum similarity score threshold
            
        Returns:
            True if KB has some relevant safety info, False if completely empty
        """
        if not chunks:
            return False
        
        # Check if at least one chunk has reasonable similarity
        return any(chunk.get("similarity_score", 0) >= threshold for chunk in chunks)
    
    def _format_kb_context(self, chunks: List[Dict[str, Any]]) -> str:
        """Format KB chunks into context string for LLM"""
        if not chunks:
            return "No specific safety information found in knowledge base. Rely on clinical judgment and patient data."
        
        context_parts = []
        for idx, chunk in enumerate(chunks, 1):
            context_parts.append(
                f"[Safety Source {idx}: {chunk['resource_title']} (similarity: {chunk['similarity_score']:.2f})]\\n{chunk['chunk_text']}"
            )
        
        return "\\n\\n---\\n\\n".join(context_parts)
    
    def screen_for_safety(
        self,
        therapist_id: int,
        blueprint: Dict[str, Any],
        clinical_summary: str,
        patient_conditions: str,
        therapist_notes_summary: str = None
    ) -> Dict[str, Any]:
        """
        Perform safety screening on blueprint
        
        Args:
            therapist_id: Therapist's ID for KB scoping
            blueprint: The proposed session blueprint
            clinical_summary: Output from Context Synthesiser
            patient_conditions: Patient's conditions/diagnoses
            therapist_notes_summary: Optional summary of therapist concerns
            
        Returns:
            Dictionary with safety flags and recommendations
        """
        try:
            # Query KB for safety information
            kb_chunks = self._query_kb_for_safety_info(therapist_id, blueprint, patient_conditions)
            
            # Check KB sufficiency (lower threshold, proceed even with limited info)
            has_kb_safety_info = self._check_kb_sufficiency(kb_chunks)
            
            # Format KB context (include note if KB is limited)
            kb_context = self._format_kb_context(kb_chunks)
            if not has_kb_safety_info:
                kb_context += "\\n\\n**Note:** Limited safety information in KB. Screening based primarily on clinical judgment and patient profile."
            
            # Build prompt
            prompt = self._build_safety_screening_prompt(
                blueprint, 
                clinical_summary, 
                patient_conditions,
                therapist_notes_summary
            )
            prompt = prompt.replace("{kb_context}", kb_context)
            
            # Call LLM for safety screening
            response = client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0,  # Deterministic for safety critical task
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            # Parse response
            import json
            result = json.loads(response.choices[0].message.content)
            
            # Add metadata
            result["kb_chunks"] = kb_chunks
            result["kb_sufficiency"] = "sufficient" if has_kb_safety_info else "limited"
            result["tokens_used"] = {
                "prompt": response.usage.prompt_tokens,
                "completion": response.usage.completion_tokens,
                "total": response.usage.total_tokens
            }
            
            return result
            
        except Exception as e:
            return {
                "status": "error",
                "error_message": str(e),
                "safety_flags": [],
                "overall_risk_level": "unknown",
                "proceed_recommendation": "therapist_review_required"
            }
    
    async def execute(
        self,
        therapist_id: int,
        blueprint: Dict[str, Any],
        clinical_summary: str,
        patient_conditions: str,
        therapist_notes_summary: str = None
    ) -> Dict[str, Any]:
        """
        Execute Safety Gate agent (main entry point for LangGraph)
        
        This method is designed to be called from a LangGraph node.
        It screens the blueprint for safety concerns and returns flags.
        
        Args:
            therapist_id: Therapist's ID for KB scoping
            blueprint: Output from Blueprint Generator (Agent 4)
            clinical_summary: Output from Context Synthesiser (Agent 2)
            patient_conditions: Patient's conditions/diagnoses
            therapist_notes_summary: Optional therapist concerns
            
        Returns:
            Dictionary containing:
            - status: success/error
            - safety_flags: List of identified safety concerns (0 or more)
            - overall_risk_level: safe/caution/high_risk
            - proceed_recommendation: proceed/proceed_with_modifications/therapist_review_required
            - agent_metadata: Execution metadata
        """
        # Validate inputs
        if not blueprint:
            return {
                "status": "error",
                "error_type": "invalid_input",
                "error_message": "Blueprint is missing",
                "safety_flags": [],
                "overall_risk_level": "unknown",
                "proceed_recommendation": "therapist_review_required",
                "agent_metadata": {
                    "agent_name": self.agent_name,
                    "llm_calls": 0,
                }
            }
        
        try:
            # Perform safety screening
            result = self.screen_for_safety(
                therapist_id=therapist_id,
                blueprint=blueprint,
                clinical_summary=clinical_summary,
                patient_conditions=patient_conditions,
                therapist_notes_summary=therapist_notes_summary
            )
            
            # Return structured response
            return {
                "status": "success",
                "safety_flags": result.get("safety_flags", []),
                "overall_risk_level": result.get("overall_risk_level", "unknown"),
                "proceed_recommendation": result.get("proceed_recommendation", "proceed"),
                "screening_notes": result.get("screening_notes", ""),
                "kb_sufficiency": result.get("kb_sufficiency", "unknown"),
                "kb_chunks": result.get("kb_chunks", []),
                "agent_metadata": {
                    "agent_name": self.agent_name,
                    "agent_type": "llm_with_rag_safety_screening",
                    "model": self.llm_model,
                    "llm_calls": 1,
                    "kb_queries": 1,
                    "num_safety_flags": len(result.get("safety_flags", [])),
                    "tokens_used": result.get("tokens_used", {}),
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error_type": "system_error",
                "error_message": str(e),
                "safety_flags": [],
                "overall_risk_level": "unknown",
                "proceed_recommendation": "therapist_review_required",
                "agent_metadata": {
                    "agent_name": self.agent_name,
                    "llm_calls": 0,
                }
            }
