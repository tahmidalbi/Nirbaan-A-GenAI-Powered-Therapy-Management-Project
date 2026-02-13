"""
LangGraph Workflow for Multi-Agent Therapy Protocol Generation

This module implements the complete 8-agent pipeline using LangGraph's StateGraph.

Author: Nirbaan AI Research Team
Date: February 11, 2026
"""

from dotenv import load_dotenv
load_dotenv()

import logging
import os
from typing import TypedDict, Literal, Optional, Dict, Any, List
from datetime import datetime
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from sqlalchemy.orm import Session

# Enable LangSmith tracing - set BEFORE any LangChain imports
if not os.getenv("LANGCHAIN_TRACING_V2"):
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
if not os.getenv("LANGCHAIN_ENDPOINT"):
    os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
if not os.getenv("LANGCHAIN_API_KEY") and os.getenv("LANGSMITH_API_KEY"):
    os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGSMITH_API_KEY")
if not os.getenv("LANGCHAIN_PROJECT"):
    os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGSMITH_PROJECT", "NIRBAAN")

logger = logging.getLogger(__name__)

# Import all agents
from .history_picker import HistoryPickerAgent
from .session_picker import SessionPickerAgent
from .context_synthesiser import ContextSynthesiserAgent
from .stage_picker import StagePickerAgent
from .blueprint_generator import BlueprintGeneratorAgent
from .safety_gate import SafetyGateAgent
from .clarification_agent import ClarificationAgent
from .protocol_generator import ProtocolGeneratorAgent
from .uncertainty_scorer import UncertaintyScorer


# ==============================================================================
# State Definition
# ==============================================================================

class ProtocolGenerationState(TypedDict):
    patient_id: int
    therapist_id: int
    session_focus: Optional[str]

    history_data: Optional[Dict[str, Any]]
    session_data: Optional[Dict[str, Any]]

    clinical_summary: Optional[Dict[str, Any]]

    selected_stage: Optional[Dict[str, Any]]
    stage_name: Optional[str]                 # ✅ ADDED
    stage_verification_attempts: int
    stage_verified: bool

    blueprint: Optional[Dict[str, Any]]
    blueprint_kb_chunks: Optional[List[Dict[str, Any]]]

    safety_flags: Optional[List[Dict[str, Any]]]
    safety_kb_chunks: Optional[List[Dict[str, Any]]]

    clarification_needed: bool
    clarification_questions: Optional[List[Dict[str, Any]]]
    clarification_answers: Optional[Dict[str, Any]]

    protocol: Optional[Dict[str, Any]]
    protocol_kb_chunks: Optional[List[Dict[str, Any]]]
    all_kb_chunks_used: Optional[List[Dict[str, Any]]]

    uncertainty_result: Optional[Dict[str, Any]]
    revision_attempts: int

    halted: bool
    halt_reason: Optional[str]

    final_protocol: Optional[Dict[str, Any]]
    confidence_score: Optional[float]
    audit_trail: List[Dict[str, Any]]


# ==============================================================================
# Node Functions
# ==============================================================================

async def history_picker_node(state: ProtocolGenerationState, db_session: Session) -> Dict[str, Any]:
    logger.info("NODE: History Picker (Agent 1a)")
    agent = HistoryPickerAgent(db=db_session)
    result = await agent.execute(patient_id=state["patient_id"], therapist_id=state["therapist_id"])

    audit_entry = {
        "agent": "HistoryPicker",
        "status": result.get("status"),
        "timestamp": result.get("metadata", {}).get("timestamp")
    }

    return {"history_data": result, "audit_trail": state.get("audit_trail", []) + [audit_entry]}


async def session_picker_node(state: ProtocolGenerationState, db_session: Session) -> Dict[str, Any]:
    logger.info("NODE: Session Picker (Agent 1b)")
    agent = SessionPickerAgent(db=db_session)
    result = await agent.execute(patient_id=state["patient_id"], therapist_id=state["therapist_id"])

    audit_entry = {
        "agent": "SessionPicker",
        "status": result.get("status"),
        "timestamp": result.get("metadata", {}).get("timestamp")
    }

    return {"session_data": result, "audit_trail": state.get("audit_trail", []) + [audit_entry]}


async def context_synthesiser_node(state: ProtocolGenerationState) -> Dict[str, Any]:
    logger.info("NODE: Context Synthesiser (Agent 2)")
    agent = ContextSynthesiserAgent()

    result = await agent.execute(
        history_data=state["history_data"],
        session_data=state["session_data"],
        session_focus=state.get("session_focus")
    )

    audit_entry = {
        "agent": "ContextSynthesiser",
        "status": "success",
        "timestamp": result.get("metadata", {}).get("timestamp")
    }

    return {"clinical_summary": result, "audit_trail": state.get("audit_trail", []) + [audit_entry]}


async def stage_picker_node(state: ProtocolGenerationState, db_session: Session) -> Dict[str, Any]:
    logger.info("NODE: Stage Picker (Agent 3)")
    agent = StagePickerAgent(db=db_session)

    clinical_summary_dict = (state["clinical_summary"] or {}).get("clinical_summary", {}) or {}

    result = await agent.execute(
        therapist_id=state["therapist_id"],
        clinical_summary=clinical_summary_dict,
        session_focus=state.get("session_focus")
    )

    if result.get("kb_insufficient"):
        return {
            "halted": True,
            "halt_reason": f"Stage Picker: {result.get('halt_reason', 'KB insufficient for stage selection')}",
            "audit_trail": state.get("audit_trail", []) + [{
                "agent": "StagePicker",
                "status": "halted",
                "reason": result.get("halt_reason")
            }]
        }

    # ✅ stage_name is required later; store it explicitly
    stage_name = result.get("selected_stage") or ""

    audit_entry = {
        "agent": "StagePicker",
        "status": "success",
        "stage_selected": stage_name,
        "verification_attempts": len(result.get("verification_history", [])),
        "timestamp": datetime.now().isoformat()
    }

    return {
        "selected_stage": result,
        "stage_name": stage_name,      # ✅ ADDED
        "stage_verified": True,
        "audit_trail": state.get("audit_trail", []) + [audit_entry]
    }


async def blueprint_generator_node(state: ProtocolGenerationState, db_session: Session) -> Dict[str, Any]:
    logger.info("NODE: Blueprint Generator (Agent 4)")
    agent = BlueprintGeneratorAgent()

    clinical_summary_dict = (state["clinical_summary"] or {}).get("clinical_summary", {}) or {}
    stage_result = state.get("selected_stage") or {}
    stage_name = state.get("stage_name") or stage_result.get("selected_stage", "")
    stage_rationale = stage_result.get("selection_reasoning", "")

    result = await agent.execute(
        db=db_session,
        therapist_id=state["therapist_id"],
        clinical_summary=clinical_summary_dict,
        stage=stage_name,
        stage_rationale=stage_rationale,
        session_focus=state.get("session_focus", "")
    )

    if result is None:
        return {
            "halted": True,
            "halt_reason": "Blueprint Generator: Internal error (None result)",
            "audit_trail": state.get("audit_trail", []) + [{
                "agent": "BlueprintGenerator",
                "status": "error",
                "reason": "Agent returned None"
            }]
        }

    if result.get("status") == "insufficient_kb":
        llm_assessment = result.get("llm_assessment", {})
        reason = llm_assessment.get("reasoning", "KB insufficient for blueprint generation")
        return {
            "halted": True,
            "halt_reason": f"Blueprint Generator: {reason}",
            "audit_trail": state.get("audit_trail", []) + [{
                "agent": "BlueprintGenerator",
                "status": "halted",
                "reason": reason
            }]
        }

    if result.get("status") == "error":
        return {
            "halted": True,
            "halt_reason": f"Blueprint Generator: {result.get('error', 'Unknown error')}",
            "audit_trail": state.get("audit_trail", []) + [{
                "agent": "BlueprintGenerator",
                "status": "error",
                "error": result.get("error")
            }]
        }

    audit_entry = {
        "agent": "BlueprintGenerator",
        "status": "success",
        "num_phases": len((result.get("blueprint") or {}).get("phases", [])),
        "timestamp": (result.get("metadata") or {}).get("timestamp")
    }

    return {
        "blueprint": result.get("blueprint"),
        "blueprint_kb_chunks": result.get("kb_chunks_used", []),
        "audit_trail": state.get("audit_trail", []) + [audit_entry]
    }


async def safety_gate_node(state: ProtocolGenerationState, db_session: Session) -> Dict[str, Any]:
    logger.info("NODE: Safety Gate (Agent 5)")
    agent = SafetyGateAgent(db=db_session)

    history_structured = (state.get("history_data") or {}).get("structured_summary", {})
    patient_profile = history_structured.get("patient_profile", {})
    patient_conditions = patient_profile.get("conditions", [])

    clinical_summary_text = (state.get("clinical_summary") or {}).get("clinical_summary_text", "")

    result = await agent.execute(
        therapist_id=state["therapist_id"],
        blueprint=state.get("blueprint") or {},
        clinical_summary=clinical_summary_text,
        patient_conditions=patient_conditions
    )

    if result.get("kb_insufficient"):
        return {
            "halted": True,
            "halt_reason": f"Safety Gate: {result.get('halt_reason', 'KB insufficient for safety screening')}",
            "audit_trail": state.get("audit_trail", []) + [{
                "agent": "SafetyGate",
                "status": "halted",
                "reason": result.get("halt_reason")
            }]
        }

    audit_entry = {
        "agent": "SafetyGate",
        "status": "success",
        "num_safety_flags": len(result.get("safety_flags", [])),
        "timestamp": (result.get("metadata") or {}).get("timestamp")
    }

    return {
        "safety_flags": result.get("safety_flags", []),
        "safety_kb_chunks": result.get("kb_chunks_used", []),
        "audit_trail": state.get("audit_trail", []) + [audit_entry]
    }


async def clarification_agent_node(state: ProtocolGenerationState) -> Dict[str, Any]:
    logger.info("NODE: Clarification Agent (Agent 6)")
    agent = ClarificationAgent()

    if state.get("clarification_answers") is not None:
        return {
            "clarification_needed": False,
            "audit_trail": state.get("audit_trail", []) + [{
                "agent": "ClarificationAgent",
                "status": "answers_provided",
                "timestamp": None
            }]
        }

    clinical_summary_dict = (state.get("clinical_summary") or {}).get("clinical_summary", {}) or {}

    result = await agent.execute(
        blueprint=state.get("blueprint") or {},
        safety_flags=state.get("safety_flags") or [],
        clinical_summary=clinical_summary_dict,
        kb_gaps=[]
    )

    clarification_needed = result.get("decision") == "needs_clarification"

    audit_entry = {
        "agent": "ClarificationAgent",
        "status": "needs_clarification" if clarification_needed else "no_questions",
        "num_questions": len(result.get("questions", [])),
        "timestamp": (result.get("metadata") or {}).get("timestamp")
    }

    return {
        "clarification_needed": clarification_needed,
        "clarification_questions": result.get("questions", []) if clarification_needed else None,
        "audit_trail": state.get("audit_trail", []) + [audit_entry]
    }


async def protocol_generator_node(state: ProtocolGenerationState, db_session: Session) -> Dict[str, Any]:
    logger.info("NODE: Protocol Generator (Agent 7)")
    agent = ProtocolGeneratorAgent()

    clinical_summary_dict = (state.get("clinical_summary") or {}).get("clinical_summary", {}) or {}

    # ✅ FIX: stage name is now correctly stored in state
    stage_name = state.get("stage_name") or ""

    result = await agent.execute(
        db=db_session,
        therapist_id=state["therapist_id"],
        clinical_summary=clinical_summary_dict,
        stage=stage_name,
        blueprint=state.get("blueprint") or {},
        clarification_answers=state.get("clarification_answers"),
        safety_modifications=state.get("safety_flags") or []
    )

    if not result:
        return {
            "halted": True,
            "halt_reason": "Protocol Generator: returned None",
            "audit_trail": state.get("audit_trail", []) + [{
                "agent": "ProtocolGenerator",
                "status": "error",
                "reason": "Agent returned None"
            }]
        }

    status = result.get("status")
    if status in ("insufficient_kb", "error"):
        reason = (
            ((result.get("llm_assessment") or {}).get("reasoning"))
            or ((result.get("protocol_assessment") or {}).get("sufficiency_reasoning"))
            or result.get("error")
            or "Protocol generation failed."
        )
        return {
            "halted": True,
            "halt_reason": f"Protocol Generator: {reason}",
            "audit_trail": state.get("audit_trail", []) + [{
                "agent": "ProtocolGenerator",
                "status": "halted" if status == "insufficient_kb" else "error",
                "reason": reason
            }]
        }

    protocol = result.get("protocol") or {}
    phases = protocol.get("phases") or protocol.get("session_protocol", {}).get("phases") or []

    if status == "success" and len(phases) == 0:
        return {
            "halted": True,
            "halt_reason": "Protocol Generator: Generated protocol contains no therapy phases",
            "audit_trail": state.get("audit_trail", []) + [{
                "agent": "ProtocolGenerator",
                "status": "error",
                "reason": "Protocol has no phases"
            }]
        }

    # Aggregate KB chunks
    all_kb = []
    all_kb.extend(state.get("blueprint_kb_chunks") or [])
    all_kb.extend(state.get("safety_kb_chunks") or [])
    all_kb.extend(result.get("kb_sources") or [])

    # Dedupe
    seen = set()
    dedup = []
    for i, ch in enumerate(all_kb, 1):
        cid = ch.get("id") or ch.get("chunk_id") or f"fallback_{i}"
        if cid in seen:
            continue
        seen.add(cid)
        dedup.append(ch)

    audit_entry = {
        "agent": "ProtocolGenerator",
        "status": "success",
        "num_phases": len(phases),
        "num_kb_chunks": len(result.get("kb_sources") or []),
        "timestamp": result.get("timestamp"),
    }

    return {
        "protocol": protocol,
        "protocol_kb_chunks": result.get("kb_sources") or [],
        "all_kb_chunks_used": dedup,
        "audit_trail": state.get("audit_trail", []) + [audit_entry]
    }


async def uncertainty_scorer_node(state: ProtocolGenerationState) -> Dict[str, Any]:
    logger.info("NODE: Uncertainty Scorer (Agent 8)")

    scorer = UncertaintyScorer()
    protocol_generator = ProtocolGeneratorAgent()

    clinical_summary_dict = (state.get("clinical_summary") or {}).get("clinical_summary", {}) or {}

    result = await scorer.execute(
        protocol=state.get("protocol") or {},
        kb_chunks_used=state.get("all_kb_chunks_used") or [],
        clinical_summary=clinical_summary_dict,
        blueprint=state.get("blueprint") or {},
        protocol_generator=protocol_generator
    )

    final_protocol = result.get("revised_protocol") if result.get("revision_triggered") else state.get("protocol")

    audit_entry = {
        "agent": "UncertaintyScorer",
        "status": "success",
        "global_confidence": result.get("global_confidence"),
        "revision_triggered": result.get("revision_triggered"),
        "num_claims_scored": (result.get("metadata") or {}).get("num_claims_scored"),
        "num_high_risk_claims": (result.get("metadata") or {}).get("num_high_risk_claims"),
        "timestamp": (result.get("metadata") or {}).get("timestamp")
    }

    return {
        "uncertainty_result": result,
        "final_protocol": final_protocol,
        "confidence_score": result.get("global_confidence"),
        "revision_attempts": 1 if result.get("revision_triggered") else 0,
        "audit_trail": state.get("audit_trail", []) + [audit_entry]
    }


# ==============================================================================
# Conditional Routing
# ==============================================================================

def should_halt_after_stage_picker(state: ProtocolGenerationState) -> Literal["blueprint_generator", "halt"]:
    return "halt" if state.get("halted") else "blueprint_generator"

def should_halt_after_blueprint(state: ProtocolGenerationState) -> Literal["safety_gate", "halt"]:
    return "halt" if state.get("halted") else "safety_gate"

def should_halt_after_safety_gate(state: ProtocolGenerationState) -> Literal["clarification_agent", "halt"]:
    return "halt" if state.get("halted") else "clarification_agent"

def check_clarification_or_halt(state: ProtocolGenerationState) -> Literal["protocol_generator", "halt"]:
    return "halt" if state.get("halted") else "protocol_generator"

def should_halt_after_protocol_generator(state: ProtocolGenerationState) -> Literal["uncertainty_scorer", "halt"]:
    return "halt" if state.get("halted") else "uncertainty_scorer"


async def halt_node(state: ProtocolGenerationState) -> Dict[str, Any]:
    logger.error("PIPELINE HALTED: %s", state.get("halt_reason"))
    return {"halted": True, "final_protocol": None, "confidence_score": None}


# ==============================================================================
# Graph Construction
# ==============================================================================

def create_protocol_generation_workflow(db_session: Session) -> StateGraph:
    workflow = StateGraph(ProtocolGenerationState)

    async def history_picker_with_db(state): return await history_picker_node(state, db_session)
    async def session_picker_with_db(state): return await session_picker_node(state, db_session)
    async def stage_picker_with_db(state): return await stage_picker_node(state, db_session)
    async def blueprint_generator_with_db(state): return await blueprint_generator_node(state, db_session)
    async def safety_gate_with_db(state): return await safety_gate_node(state, db_session)
    async def protocol_generator_with_db(state): return await protocol_generator_node(state, db_session)

    workflow.add_node("history_picker", history_picker_with_db)
    workflow.add_node("session_picker", session_picker_with_db)
    workflow.add_node("context_synthesiser", context_synthesiser_node)
    workflow.add_node("stage_picker", stage_picker_with_db)
    workflow.add_node("blueprint_generator", blueprint_generator_with_db)
    workflow.add_node("safety_gate", safety_gate_with_db)
    workflow.add_node("clarification_agent", clarification_agent_node)
    workflow.add_node("protocol_generator", protocol_generator_with_db)
    workflow.add_node("uncertainty_scorer", uncertainty_scorer_node)
    workflow.add_node("halt", halt_node)

    workflow.set_entry_point("history_picker")
    workflow.add_edge("history_picker", "session_picker")
    workflow.add_edge("session_picker", "context_synthesiser")
    workflow.add_edge("context_synthesiser", "stage_picker")

    workflow.add_conditional_edges("stage_picker", should_halt_after_stage_picker,
                                   {"blueprint_generator": "blueprint_generator", "halt": "halt"})

    workflow.add_conditional_edges("blueprint_generator", should_halt_after_blueprint,
                                   {"safety_gate": "safety_gate", "halt": "halt"})

    workflow.add_conditional_edges("safety_gate", should_halt_after_safety_gate,
                                   {"clarification_agent": "clarification_agent", "halt": "halt"})

    workflow.add_conditional_edges("clarification_agent", check_clarification_or_halt,
                                   {"protocol_generator": "protocol_generator", "halt": "halt"})

    workflow.add_conditional_edges("protocol_generator", should_halt_after_protocol_generator,
                                   {"uncertainty_scorer": "uncertainty_scorer", "halt": "halt"})

    workflow.add_edge("uncertainty_scorer", END)
    workflow.add_edge("halt", END)

    return workflow


# ==============================================================================
# Workflow Execution
# ==============================================================================

async def run_protocol_generation(
    patient_id: int,
    therapist_id: int,
    db_session: Session,
    session_focus: Optional[str] = None,
    checkpointer: Optional[Any] = None
) -> Dict[str, Any]:

    workflow = create_protocol_generation_workflow(db_session)

    if checkpointer is None:
        checkpointer = MemorySaver()

    app = workflow.compile(checkpointer=checkpointer)

    initial_state: ProtocolGenerationState = {
        "patient_id": patient_id,
        "therapist_id": therapist_id,
        "session_focus": session_focus,

        "history_data": None,
        "session_data": None,
        "clinical_summary": None,

        "selected_stage": None,
        "stage_name": None,                    # ✅ ADDED
        "stage_verification_attempts": 0,
        "stage_verified": False,

        "blueprint": None,
        "blueprint_kb_chunks": None,

        "safety_flags": None,
        "safety_kb_chunks": None,

        "clarification_needed": False,
        "clarification_questions": None,
        "clarification_answers": None,

        "protocol": None,
        "protocol_kb_chunks": None,
        "all_kb_chunks_used": None,

        "uncertainty_result": None,
        "revision_attempts": 0,

        "halted": False,
        "halt_reason": None,

        "final_protocol": None,
        "confidence_score": None,
        "audit_trail": []
    }

    thread_id = f"{therapist_id}_{patient_id}_{os.urandom(4).hex()}"
    config = {"configurable": {"thread_id": thread_id}}

    try:
        # ✅ CRITICAL FIX: stream full state snapshots, not update events
        final_state = None
        async for state_snapshot in app.astream(
            initial_state,
            config=config,
            stream_mode="values"   # ✅ THIS is what fixes your issue
        ):
            final_state = state_snapshot

        if final_state is None:
            final_state = initial_state

        if final_state.get("halted"):
            status = "halted"
        elif final_state.get("clarification_needed") and not final_state.get("clarification_answers"):
            status = "needs_clarification"
        else:
            final_protocol = final_state.get("final_protocol")
            if not final_protocol or (isinstance(final_protocol, dict) and len(final_protocol) == 0):
                status = "error"
                if not final_state.get("halt_reason"):
                    final_state["halt_reason"] = "Protocol generation completed but no protocol data was produced"
            else:
                phases = final_protocol.get("phases", []) or final_protocol.get("session_protocol", {}).get("phases", [])
                if not phases:
                    status = "error"
                    if not final_state.get("halt_reason"):
                        final_state["halt_reason"] = "Protocol generated but contains no therapy phases"
                else:
                    status = "success"

        return {
            "status": status,
            "final_protocol": final_state.get("final_protocol"),
            "confidence_score": final_state.get("confidence_score"),
            "uncertainty_result": final_state.get("uncertainty_result"),
            "clarification_questions": final_state.get("clarification_questions"),
            "halt_reason": final_state.get("halt_reason"),
            "audit_trail": final_state.get("audit_trail", []),
            "thread_id": thread_id
        }

    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}", exc_info=True)
        return {
            "status": "error",
            "final_protocol": None,
            "confidence_score": None,
            "uncertainty_result": None,
            "clarification_questions": None,
            "halt_reason": f"Execution error: {str(e)}",
            "audit_trail": [],
            "thread_id": thread_id
        }


async def resume_after_clarification(
    thread_id: str,
    clarification_answers: Dict[str, Any],
    checkpointer: Any,
    db_session: Session                   # ✅ REQUIRED
) -> Dict[str, Any]:

    workflow = create_protocol_generation_workflow(db_session)  # ✅ FIXED
    app = workflow.compile(checkpointer=checkpointer)

    config = {"configurable": {"thread_id": thread_id}}
    update_state = {"clarification_answers": clarification_answers}

    try:
        # When resuming, ainvoke gives a full final state
        final_state = await app.ainvoke(update_state, config=config)

        status = "halted" if final_state.get("halted") else "success"

        return {
            "status": status,
            "final_protocol": final_state.get("final_protocol"),
            "confidence_score": final_state.get("confidence_score"),
            "uncertainty_result": final_state.get("uncertainty_result"),
            "clarification_questions": None,
            "halt_reason": final_state.get("halt_reason"),
            "audit_trail": final_state.get("audit_trail", []),
            "thread_id": thread_id
        }

    except Exception as e:
        logger.error(f"Resume failed: {e}", exc_info=True)
        return {
            "status": "error",
            "final_protocol": None,
            "confidence_score": None,
            "uncertainty_result": None,
            "clarification_questions": None,
            "halt_reason": f"Resume error: {str(e)}",
            "audit_trail": [],
            "thread_id": thread_id
        }
