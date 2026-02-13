"""
Agent 6: Clarification Agent
Analyzes blueprint + safety flags to determine if therapist input is needed.
Bundles all questions into single structured request for human-in-the-loop interaction.

This agent is the gateway to LangGraph's interrupt mechanism. It identifies:
1. Safety flags requiring therapist decisions
2. Ambiguous KB guidance where therapist preference is needed
3. Missing patient-specific preferences

Design decisions:
- ONE-ROUND-TRIP constraint: asks all questions at once (NOT a chatbot)
- Temperature 0 for deterministic question generation
- No RAG needed - analyzes existing blueprint and safety flags
- LangGraph-compatible: returns needs_clarification status for interrupt
- Timeout/fallback: conservative defaults if therapist doesn't respond
"""

import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from openai import OpenAI


class ClarificationAgent:
    """
    Agent 6: Clarification Agent
    
    Determines if therapist input is needed before protocol generation.
    Bundles all questions into single structured request for human-in-the-loop.
    
    Input:
        - blueprint: Session structure from Blueprint Generator
        - safety_flags: Contraindications from Safety Gate
        - clinical_summary: Patient context from Context Synthesiser
        - kb_gaps: Optional known gaps in KB coverage
        
    Output:
        - status: "no_questions" | "needs_clarification" | "error"
        - questions: Structured list of questions (if needs_clarification)
        - default_answers: Conservative fallbacks for each question
        - question_analysis: Why each question is being asked
    """
    
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        
    def _build_question_analysis_prompt(
        self,
        blueprint: Dict[str, Any],
        safety_flags: List[Dict[str, Any]],
        clinical_summary: Dict[str, Any],
        kb_gaps: Optional[List[str]] = None
    ) -> tuple[str, str]:
        """
        Build system + user prompt for question analysis.
        
        LLM identifies where therapist input is needed and bundles questions.
        """
        # Extract blueprint phases
        phases = blueprint.get("phases", [])
        phases_text = "\n".join([
            f"Phase {p.get('phase_number')}: {p.get('phase_name')} ({p.get('time_allocation_minutes')}min) - Activities: {', '.join([a.get('activity_name', 'unnamed') for a in p.get('activities', [])])}"
            for p in phases
        ])
        
        # Format safety flags
        safety_text = ""
        if safety_flags:
            safety_text = "\n".join([
                f"[Flag {i+1}] Severity: {flag.get('severity', 'unknown')} | Type: {flag.get('concern_type', 'unknown')}\n"
                f"  Concern: {flag.get('concern_description', 'No description')}\n"
                f"  Affects: {flag.get('affected_blueprint_component', 'Unknown component')}\n"
                f"  Suggested Modification: {flag.get('suggested_modification', 'None')}\n"
                f"  Requires Decision: {flag.get('requires_therapist_decision', False)}"
                for i, flag in enumerate(safety_flags)
            ])
        else:
            safety_text = "No safety flags raised."
        
        # Extract clinical context
        patient_profile = clinical_summary.get("patient_profile", {})
        therapist_priorities = clinical_summary.get("therapist_priorities", "")
        open_concerns = clinical_summary.get("open_concerns", "")
        
        # KB gaps
        gaps_text = ""
        if kb_gaps:
            gaps_text = "\n".join([f"  • {gap}" for gap in kb_gaps])
        else:
            gaps_text = "No known KB gaps."
        
        system_prompt = """You are a clinical decision analyst. Your job is to determine whether a proposed therapy session blueprint has enough information to proceed to detailed protocol generation, or whether therapist input is needed.

CRITICAL CONSTRAINTS:
1. This is ONE-ROUND-TRIP interaction - bundle ALL questions into a single request
2. Do NOT ask questions that can be resolved from the KB or clinical context
3. Only ask questions that REQUIRE therapist judgment or preference
4. For every question, provide a conservative default answer that will be used if therapist doesn't respond
5. Questions should be clear, specific, and actionable

SOURCES OF QUESTIONS:
1. **Safety Flags** - Safety Gate raised concerns that require therapist decision
2. **Ambiguous KB Guidance** - Multiple valid approaches, therapist preference needed
3. **Patient-Specific Preferences** - Techniques that may not work for this specific patient
4. **KB Gaps** - Critical information missing from knowledge base

REQUIRED OUTPUT FORMAT (JSON):
{
  "question_analysis": {
    "has_questions": true/false,
    "question_count": number,
    "urgency_level": "low/medium/high",
    "reasoning": "brief explanation of why questions are needed or not"
  },
  "questions": [
    {
      "question_id": "q1",
      "question_type": "safety_flag/kb_ambiguity/patient_preference/kb_gap",
      "source": "which safety flag or blueprint component triggered this",
      "question_text": "Clear, specific question for therapist",
      "context": "Why this question matters",
      "options": [
        {
          "option_id": "a",
          "option_text": "string",
          "implications": "what happens if this option is chosen"
        }
      ],
      "requires_response": true/false,
      "default_answer": {
        "option_id": "string",
        "reasoning": "why this is the conservative default"
      }
    }
  ],
  "can_proceed_with_defaults": true/false,
  "default_strategy_description": "if therapist doesn't respond, what happens"
}

ANALYSIS RULES:
- If NO safety flags requiring decisions AND no ambiguities AND no KB gaps → has_questions: false
- If safety flags have severity "high" → urgency_level: "high"
- For safety questions, default should ALWAYS be most conservative option (skip technique, use safer alternative)
- For preference questions, default should be KB-supported standard approach
- If multiple safety flags relate to same issue, bundle into one question"""

        user_prompt = f"""CLINICAL CONTEXT:
Patient: {patient_profile.get('name', 'Unknown')}, {patient_profile.get('age', 'unknown')}yo
Conditions: {', '.join(patient_profile.get('conditions', []))}
Week: {patient_profile.get('current_week', 'unknown')}

THERAPIST PRIORITIES:
{therapist_priorities}

OPEN CONCERNS:
{open_concerns}

PROPOSED BLUEPRINT:
{phases_text}

Materials Needed: {', '.join(blueprint.get('materials_summary', []))}
Homework Preview: {blueprint.get('homework_preview', 'None specified')}

SAFETY FLAGS:
{safety_text}

KNOWN KB GAPS:
{gaps_text}

Analyze whether therapist clarification is needed before generating detailed protocol. If yes, bundle ALL questions into the output. If no, explain why we can proceed."""

        return system_prompt, user_prompt
    
    def analyze_for_clarification(
        self,
        blueprint: Dict[str, Any],
        safety_flags: List[Dict[str, Any]],
        clinical_summary: Dict[str, Any],
        kb_gaps: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Analyze blueprint and safety flags to determine if clarification is needed.
        
        Returns:
            - status: "no_questions" | "needs_clarification" | "error"
            - questions: structured questions (if any)
            - default_answers: fallbacks for each question
            - analysis: why questions are/aren't needed
        """
        start_time = datetime.now()
        
        # Build prompt
        system_prompt, user_prompt = self._build_question_analysis_prompt(
            blueprint=blueprint,
            safety_flags=safety_flags,
            clinical_summary=clinical_summary,
            kb_gaps=kb_gaps
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0,  # Deterministic question generation
                max_tokens=2500,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            question_analysis = result.get("question_analysis", {})
            has_questions = question_analysis.get("has_questions", False)
            questions = result.get("questions", [])
            can_proceed_with_defaults = result.get("can_proceed_with_defaults", True)
            
            if not has_questions:
                return {
                    "status": "no_questions",
                    "questions": [],
                    "default_answers": {},
                    "question_analysis": question_analysis,
                    "can_proceed_with_defaults": True,
                    "llm_metadata": {
                        "llm_calls": 1,
                        "total_tokens": response.usage.total_tokens,
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "analysis_time_seconds": (datetime.now() - start_time).total_seconds()
                    }
                }
            
            # Has questions - prepare structured output
            default_answers = {}
            for q in questions:
                q_id = q.get("question_id", "")
                default = q.get("default_answer", {})
                default_answers[q_id] = default
            
            return {
                "status": "needs_clarification",
                "questions": questions,
                "default_answers": default_answers,
                "question_analysis": question_analysis,
                "can_proceed_with_defaults": can_proceed_with_defaults,
                "default_strategy_description": result.get("default_strategy_description", ""),
                "llm_metadata": {
                    "llm_calls": 1,
                    "total_tokens": response.usage.total_tokens,
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "analysis_time_seconds": (datetime.now() - start_time).total_seconds()
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "questions": [],
                "default_answers": {},
                "llm_metadata": {
                    "llm_calls": 1,
                    "total_tokens": 0,
                    "analysis_time_seconds": (datetime.now() - start_time).total_seconds()
                }
            }
    
    def apply_answers_or_defaults(
        self,
        questions: List[Dict[str, Any]],
        therapist_answers: Optional[Dict[str, Any]] = None,
        use_defaults: bool = False
    ) -> Dict[str, Any]:
        """
        Apply therapist answers or use default answers.
        
        Args:
            questions: List of questions from analyze_for_clarification
            therapist_answers: Dict mapping question_id to selected option_id
            use_defaults: If True, use default answers (timeout scenario)
            
        Returns:
            - resolved_decisions: Dict mapping question_id to final decision
            - decision_metadata: How each decision was made
        """
        resolved_decisions = {}
        decision_metadata = {}
        
        for question in questions:
            q_id = question.get("question_id", "")
            default = question.get("default_answer", {})
            
            if use_defaults or not therapist_answers or q_id not in therapist_answers:
                # Use default answer
                resolved_decisions[q_id] = {
                    "selected_option_id": default.get("option_id", ""),
                    "decision_source": "default",
                    "reasoning": default.get("reasoning", "Therapist did not respond - using conservative default")
                }
                decision_metadata[q_id] = {
                    "question_text": question.get("question_text", ""),
                    "how_resolved": "default_fallback",
                    "requires_flag_in_protocol": True  # Flag this in final protocol
                }
            else:
                # Use therapist answer
                selected_option_id = therapist_answers[q_id]
                selected_option = next(
                    (opt for opt in question.get("options", []) if opt.get("option_id") == selected_option_id),
                    None
                )
                
                resolved_decisions[q_id] = {
                    "selected_option_id": selected_option_id,
                    "decision_source": "therapist",
                    "implications": selected_option.get("implications", "") if selected_option else ""
                }
                decision_metadata[q_id] = {
                    "question_text": question.get("question_text", ""),
                    "how_resolved": "therapist_answer",
                    "requires_flag_in_protocol": False
                }
        
        return {
            "resolved_decisions": resolved_decisions,
            "decision_metadata": decision_metadata,
            "used_defaults": use_defaults or (not therapist_answers)
        }
    
    async def execute(
        self,
        blueprint: Dict[str, Any],
        safety_flags: List[Dict[str, Any]],
        clinical_summary: Dict[str, Any],
        kb_gaps: Optional[List[str]] = None,
        therapist_answers: Optional[Dict[str, Any]] = None,
        use_defaults: bool = False
    ) -> Dict[str, Any]:
        """
        Main entry point for Clarification Agent.
        LangGraph-compatible async execute method.
        
        Args:
            blueprint: Session blueprint from Blueprint Generator
            safety_flags: Safety concerns from Safety Gate
            clinical_summary: Patient context from Context Synthesiser
            kb_gaps: Optional known KB coverage gaps
            therapist_answers: If resuming after interrupt, therapist's responses
            use_defaults: If True, use default answers (timeout scenario)
            
        Returns:
            {
                "agent_name": "ClarificationAgent",
                "status": "no_questions" | "needs_clarification" | "clarifications_resolved" | "error",
                "questions": structured questions (if needs_clarification),
                "resolved_decisions": final decisions (if clarifications_resolved),
                "agent_metadata": analysis metrics,
                "timestamp": ISO timestamp
            }
        """
        # If therapist_answers provided, we're resuming after interrupt
        if therapist_answers is not None or use_defaults:
            # This is post-interrupt - apply answers
            # Note: This assumes questions were previously generated and stored in state
            # In real LangGraph workflow, questions would be in pipeline state
            return {
                "agent_name": "ClarificationAgent",
                "status": "clarifications_resolved",
                "resolved_decisions": {},  # Would be populated from stored questions
                "decision_metadata": {},
                "timestamp": datetime.now().isoformat()
            }
        
        # Analyze for clarification needs
        result = self.analyze_for_clarification(
            blueprint=blueprint,
            safety_flags=safety_flags,
            clinical_summary=clinical_summary,
            kb_gaps=kb_gaps
        )
        
        return {
            "agent_name": "ClarificationAgent",
            "status": result["status"],
            "questions": result.get("questions", []),
            "default_answers": result.get("default_answers", {}),
            "question_analysis": result.get("question_analysis", {}),
            "can_proceed_with_defaults": result.get("can_proceed_with_defaults", True),
            "default_strategy_description": result.get("default_strategy_description", ""),
            "agent_metadata": {
                "llm_calls": result["llm_metadata"]["llm_calls"],
                "total_tokens": result["llm_metadata"]["total_tokens"],
                "prompt_tokens": result["llm_metadata"].get("prompt_tokens", 0),
                "completion_tokens": result["llm_metadata"].get("completion_tokens", 0),
                "analysis_time_seconds": result["llm_metadata"]["analysis_time_seconds"],
                "question_count": len(result.get("questions", [])),
                "requires_interrupt": result["status"] == "needs_clarification"
            },
            "error": result.get("error"),
            "timestamp": datetime.now().isoformat()
        }
