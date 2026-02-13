"""
Agent 7: Protocol Generator (FULL UPDATED, crash-proof + schema-proof)

Fixes:
- ✅ AsyncOpenAI (no event-loop blocking)
- ✅ Universal chunk adapter (dict OR ORM object + nested metadata)
- ✅ distance -> similarity conversion
- ✅ No chunk['text'] KeyError
- ✅ Tier-1 sufficiency: per-phase top1 similarity + technique/stage evidence count (not avg >= 0.50)
- ✅ Optional fallback structure-only pass per phase
- ✅ ALWAYS returns protocol as dict (never None) so LangGraph never crashes
- ✅ ALWAYS returns llm_assessment as dict (never None)
"""

from __future__ import annotations

import os
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from openai import AsyncOpenAI
from sqlalchemy.orm import Session

from app.resources.rag_service import RAGService

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")


class ProtocolGeneratorAgent:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = LLM_MODEL
        self.rag_service = RAGService()

        # retrieval controls
        self.top_k_per_phase = 5
        self.top_k_fallback = 6  # for fallback structure-only pass

        # sufficiency gates (tuned)
        self.min_similarity_top1 = 0.25
        self.min_evidence_chunks_per_phase = 2
        self.min_signal_per_chunk = 1

    # --------------------------------------------------------------------------
    # Universal chunk accessor (dict OR ORM object) ✅
    # --------------------------------------------------------------------------

    def _val(self, ch: Any, key: str, default=None):
        if ch is None:
            return default

        if isinstance(ch, dict):
            if key in ch and ch[key] is not None:
                return ch[key]
            md = ch.get("metadata")
            if isinstance(md, dict) and key in md and md[key] is not None:
                return md[key]
            return default

        if hasattr(ch, key):
            v = getattr(ch, key)
            if v is not None:
                return v

        if hasattr(ch, "metadata"):
            md = getattr(ch, "metadata")
            if isinstance(md, dict) and key in md and md[key] is not None:
                return md[key]

        return default

    def _chunk_text(self, ch: Any) -> str:
        return (
            self._val(ch, "chunk_text")
            or self._val(ch, "text")
            or self._val(ch, "content")
            or self._val(ch, "page_content")
            or self._val(ch, "document_text")
            or self._val(ch, "body")
            or self._val(ch, "chunk")
            or ""
        )

    def _chunk_similarity(self, ch: Any) -> float:
        sim = (
            self._val(ch, "similarity_score")
            or self._val(ch, "similarity")
            or self._val(ch, "score")
        )
        if sim is not None:
            try:
                return float(sim)
            except Exception:
                return 0.0

        dist = self._val(ch, "distance")
        if dist is not None:
            try:
                d = float(dist)
                if d <= 2.0:
                    return max(0.0, 1.0 - min(1.0, d))
            except Exception:
                return 0.0

        return 0.0

    def _chunk_title(self, ch: Any) -> str:
        return (
            self._val(ch, "resource_title")
            or self._val(ch, "title")
            or self._val(ch, "source_title")
            or self._val(ch, "source")
            or "Unknown source"
        )

    def _chunk_id(self, ch: Any, fallback_idx: int) -> str:
        return (
            str(self._val(ch, "id") or "")
            or str(self._val(ch, "chunk_id") or "")
            or f"{self._val(ch,'resource_id','res')}_{self._val(ch,'chunk_index', fallback_idx)}"
        )

    def _dedupe_chunks(self, chunks: List[Any]) -> List[Any]:
        seen = set()
        out = []
        for i, c in enumerate(chunks, 1):
            cid = self._chunk_id(c, i)
            if cid in seen:
                continue
            seen.add(cid)
            out.append(c)
        return out

    # --------------------------------------------------------------------------
    # Signal detectors (technique / session structure)
    # --------------------------------------------------------------------------

    def _signal_score(self, text: str) -> int:
        t = (text or "").lower()
        terms = [
            # structure
            "session", "session 1", "session 2", "agenda", "outline", "phase", "module", "step", "minutes",
            # ERP / OCD techniques
            "erp", "exposure", "response prevention", "ritual prevention", "hierarchy",
            "homework", "between-session", "relapse prevention", "maintenance",
            # therapist guidance markers
            "therapist", "instructions", "procedure", "guidelines", "what to do",
        ]
        return sum(1 for s in terms if s in t)

    def _is_evidence(self, text: str) -> bool:
        return self._signal_score(text) >= self.min_signal_per_chunk

    # --------------------------------------------------------------------------
    # Retrieval per phase (with fallback pass)
    # --------------------------------------------------------------------------

    def _retrieve(self, db: Session, therapist_id: int, query: str, top_k: int) -> List[Any]:
        chunks = self.rag_service.retrieve_chunks(db=db, therapist_id=therapist_id, query=query, top_k=top_k) or []
        chunks = self._dedupe_chunks(chunks)
        chunks.sort(key=lambda c: self._chunk_similarity(c), reverse=True)
        return chunks

    def _query_kb_per_phase(
        self,
        db: Session,
        therapist_id: int,
        phase: Dict[str, Any],
        patient_conditions: List[str],
        top_k: int = 5
    ) -> Tuple[List[Any], Dict[str, Any]]:
        phase_name = phase.get("phase_name", "") or ""
        activities = phase.get("activities", []) or []

        activity_names = [str(act.get("activity_name", "") or "") for act in activities]
        kb_techniques = [str(act.get("kb_technique_reference", "") or "") for act in activities]

        conditions_str = ", ".join(patient_conditions) if patient_conditions else "OCD"

        # Pass A (targeted)
        query_a = (
            f"{conditions_str} detailed therapist instructions for {phase_name}. "
            f"Activities: {', '.join(activity_names)}. "
            f"Techniques: {', '.join(kb_techniques)}. "
            f"Include steps, dialogue examples, observation cues, guidelines."
        )
        chunks_a = self._retrieve(db, therapist_id, query_a, top_k=top_k)

        # If A is weak, do fallback structure-only
        top1_a = self._chunk_similarity(chunks_a[0]) if chunks_a else 0.0
        evidence_a = sum(1 for c in chunks_a if self._is_evidence(self._chunk_text(c)))

        debug = {
            "phase_name": phase_name,
            "query_a": query_a,
            "retrieved_a": len(chunks_a),
            "top1_a": top1_a,
            "evidence_chunks_a": evidence_a,
            "sample_texts_a_top3": [self._chunk_text(c)[:120] for c in chunks_a[:3]],
        }

        if (top1_a < self.min_similarity_top1) or (evidence_a < self.min_evidence_chunks_per_phase):
            query_b = (
                f"therapist instructions {phase_name} session agenda outline steps dialogue prompts "
                f"ERP exposure response prevention homework"
            )
            chunks_b = self._retrieve(db, therapist_id, query_b, top_k=self.top_k_fallback)

            merged = self._dedupe_chunks(chunks_a + chunks_b)
            merged.sort(key=lambda c: self._chunk_similarity(c), reverse=True)
            merged = merged[: max(top_k, self.top_k_fallback)]

            top1_m = self._chunk_similarity(merged[0]) if merged else 0.0
            evidence_m = sum(1 for c in merged if self._is_evidence(self._chunk_text(c)))

            debug.update({
                "query_b": query_b,
                "retrieved_b": len(chunks_b),
                "merged_selected": len(merged),
                "top1_merged": top1_m,
                "evidence_chunks_merged": evidence_m,
                "sample_texts_merged_top3": [self._chunk_text(c)[:120] for c in merged[:3]],
                "fallback_used": True,
            })
            return merged[:top_k], debug

        debug["fallback_used"] = False
        return chunks_a[:top_k], debug

    # --------------------------------------------------------------------------
    # Dedup across phases (by chunk_id, not by text)
    # --------------------------------------------------------------------------

    def _deduplicate_across_phases(self, phase_chunk_lists: List[List[Any]]) -> List[Any]:
        flat = [c for lst in phase_chunk_lists for c in lst]
        flat = self._dedupe_chunks(flat)
        flat.sort(key=lambda c: self._chunk_similarity(c), reverse=True)
        return flat

    # --------------------------------------------------------------------------
    # Tier-1 sufficiency check across phases
    # --------------------------------------------------------------------------

    def _check_kb_sufficiency(self, phase_chunks: Dict[int, List[Any]]) -> Dict[str, Any]:
        insufficient = []

        for phase_num, chunks in phase_chunks.items():
            if not chunks:
                insufficient.append({
                    "phase_number": phase_num,
                    "reason": "No KB chunks retrieved",
                    "top1_similarity": 0.0,
                    "evidence_chunks": 0,
                })
                continue

            top1 = self._chunk_similarity(chunks[0])
            evidence = sum(1 for c in chunks if self._is_evidence(self._chunk_text(c)))

            ok = (top1 >= self.min_similarity_top1) and (evidence >= self.min_evidence_chunks_per_phase)
            if not ok:
                insufficient.append({
                    "phase_number": phase_num,
                    "reason": f"Phase lacks usable technique/structure evidence (top1={top1:.2f}, evidence={evidence})",
                    "top1_similarity": top1,
                    "evidence_chunks": evidence,
                    "chunk_count": len(chunks),
                })

        if insufficient:
            return {
                "sufficient": False,
                "insufficient_phases": insufficient,
                "reason": f"{len(insufficient)} phases lack adequate KB evidence",
            }

        return {
            "sufficient": True,
            "insufficient_phases": [],
            "reason": None,
        }

    # --------------------------------------------------------------------------
    # Prompt build
    # --------------------------------------------------------------------------

    def _format_kb_sources(self, chunks: List[Any]) -> str:
        parts = []
        for i, ch in enumerate(chunks, 1):
            sim = self._chunk_similarity(ch)
            cid = self._chunk_id(ch, i)
            title = self._chunk_title(ch)
            text = self._chunk_text(ch)
            parts.append(f"[KB Source {i}] chunk_id={cid} | title={title} | similarity={sim:.2f}\n{text}")
        return "\n\n---\n\n".join(parts)

    def _build_protocol_prompt(
        self,
        clinical_summary: Dict[str, Any],
        stage: str,
        blueprint: Dict[str, Any],
        kb_chunks_deduplicated: List[Any],
        clarification_answers: Optional[Dict[str, Any]] = None,
        safety_modifications: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str]:

        kb_text = self._format_kb_sources(kb_chunks_deduplicated)

        phases = blueprint.get("phases", []) or []
        phases_summary = "\n".join([
            f"Phase {p.get('phase_number')}: {p.get('phase_name')} ({p.get('time_allocation_minutes')}min)"
            for p in phases
        ])

        patient_profile = (clinical_summary or {}).get("patient_profile") or {}
        symptom_trajectory = (clinical_summary or {}).get("symptom_trajectory") or {}
        therapist_priorities = (clinical_summary or {}).get("therapist_priorities") or {}
        open_concerns = (clinical_summary or {}).get("open_concerns") or {}

        clarification_text = ""
        if clarification_answers:
            clarification_text = "THERAPIST CLARIFICATIONS:\n" + json.dumps(clarification_answers, indent=2)

        safety_text = ""
        if safety_modifications:
            safety_text = "SAFETY MODIFICATIONS:\n" + json.dumps(safety_modifications, indent=2)

        system_prompt = """You are an expert clinical therapist protocol writer.

Generate a DETAILED 60-minute therapy session protocol.

CRITICAL CONSTRAINTS:
1) Follow the blueprint EXACTLY (phase names, timing, activities)
2) Every clinical claim must cite a KB source using [KB Source X]
3) Do NOT invent techniques not supported by KB sources
4) Provide detailed steps, dialogue prompts, observation cues

OUTPUT JSON:
{
  "protocol_assessment": {
    "kb_sufficient": true/false,
    "sufficiency_reasoning": "brief explanation",
    "missing_critical_elements": []
  },
  "session_protocol": {
    "session_metadata": {
      "patient_name": "string",
      "session_week": number,
      "therapy_stage": "string",
      "session_duration_minutes": 60,
      "materials_needed": []
    },
    "phases": [
      {
        "phase_number": number,
        "phase_name": "string",
        "time_start": number,
        "time_end": number,
        "duration_minutes": number,
        "objective": "string (single clear objective for this phase)",
        "activities": [
          {
            "activity_name": "string",
            "description": "string with [KB Source X] citations",
            "time_allocation": "string (e.g., '5-10 min')"
          }
        ],
        "dialogue_prompts": [
          "Example question or prompt to say to patient"
        ],
        "observation_cues": [
          "What to watch for in patient responses"
        ],
        "clinical_notes": "string (brief notes for therapist)"
      }
    ],
    "post_session": {
      "summary_template": "string",
      "homework_assignment": {
        "description": "string",
        "rationale": "string with [KB Source X]",
        "patient_handout_text": "string"
      },
      "next_session_preview": "string"
    },
    "risk_flags": []
  },
  "kb_citations_used": [
    {"source_index": number, "where_cited": "string", "what_it_supported": "string"}
  ]
}
"""

        user_prompt = f"""CLINICAL CONTEXT:
{json.dumps(patient_profile, indent=2)}

SYMPTOM TRAJECTORY:
{json.dumps(symptom_trajectory, indent=2)}

THERAPIST PRIORITIES:
{json.dumps(therapist_priorities, indent=2)}

OPEN CONCERNS:
{json.dumps(open_concerns, indent=2)}

THERAPY STAGE: {stage}

BLUEPRINT TO FOLLOW:
{phases_summary}

Materials: {', '.join(blueprint.get('materials_summary', []) or [])}
Homework Preview: {blueprint.get('homework_preview', '')}

{clarification_text}

{safety_text}

KB SOURCES:
{kb_text}

Generate the full protocol now."""
        return system_prompt, user_prompt

    # --------------------------------------------------------------------------
    # OpenAI call
    # --------------------------------------------------------------------------

    async def _call_llm_json(self, system_prompt: str, user_prompt: str, max_tokens: int = 4000):
        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        data = json.loads(resp.choices[0].message.content or "{}")
        usage = {
            "prompt_tokens": getattr(resp.usage, "prompt_tokens", 0),
            "completion_tokens": getattr(resp.usage, "completion_tokens", 0),
            "total_tokens": getattr(resp.usage, "total_tokens", 0),
        }
        return data, usage

    # --------------------------------------------------------------------------
    # Execute (LangGraph)
    # --------------------------------------------------------------------------

    async def execute(
        self,
        db: Session,
        therapist_id: int,
        clinical_summary: Dict[str, Any],
        stage: str,
        blueprint: Dict[str, Any],
        clarification_answers: Optional[Dict[str, Any]] = None,
        safety_modifications: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        started = datetime.now()
        llm_calls = 0

        phases = (blueprint or {}).get("phases", []) or []
        patient_profile = (clinical_summary or {}).get("patient_profile") or {}
        patient_conditions = patient_profile.get("conditions") or []

        phase_chunks: Dict[int, List[Any]] = {}
        phase_debug: Dict[int, Dict[str, Any]] = {}
        all_phase_lists: List[List[Any]] = []

        # per-phase retrieval
        for phase in phases:
            phase_num = int(phase.get("phase_number") or 0)
            chunks, debug = self._query_kb_per_phase(
                db=db,
                therapist_id=therapist_id,
                phase=phase,
                patient_conditions=patient_conditions,
                top_k=self.top_k_per_phase,
            )
            phase_chunks[phase_num] = chunks
            phase_debug[phase_num] = debug
            all_phase_lists.append(chunks)

        kb_chunks_dedup = self._deduplicate_across_phases(all_phase_lists)
        suff = self._check_kb_sufficiency(phase_chunks)

        # Always return dicts (never None)
        protocol_assessment: Dict[str, Any] = {}
        llm_assessment: Dict[str, Any] = {}

        if not suff["sufficient"]:
            protocol_assessment = {
                "kb_sufficient": False,
                "sufficiency_reasoning": suff["reason"] or "KB insufficient (tier-1).",
                "missing_critical_elements": ["per-phase technique guidance"],
            }
            llm_assessment = {"reasoning": "Tier-1 gate failed; LLM not called."}

            return {
                "agent_name": "ProtocolGenerator",
                "status": "insufficient_kb",
                "protocol": {},  # ✅ never None
                "protocol_assessment": protocol_assessment,
                "llm_assessment": llm_assessment,
                "kb_sources": kb_chunks_dedup,
                "kb_citations_used": [],
                "phase_chunks": phase_chunks,
                "phase_debug": phase_debug,
                "sufficiency_check": suff,
                "agent_metadata": {
                    "llm_calls": llm_calls,
                    "total_tokens": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "kb_queries": len(phases),
                    "chunks_retrieved": sum(len(v) for v in phase_chunks.values()),
                    "chunks_deduplicated": len(kb_chunks_dedup),
                    "generation_time_seconds": (datetime.now() - started).total_seconds(),
                },
                "timestamp": datetime.now().isoformat(),
            }

        # LLM generation
        system_prompt, user_prompt = self._build_protocol_prompt(
            clinical_summary=clinical_summary,
            stage=stage,
            blueprint=blueprint,
            kb_chunks_deduplicated=kb_chunks_dedup,
            clarification_answers=clarification_answers,
            safety_modifications=safety_modifications,
        )

        try:
            result, usage = await self._call_llm_json(system_prompt, user_prompt)
            llm_calls += 1

            protocol_assessment = result.get("protocol_assessment") or {}
            session_protocol = result.get("session_protocol") or {}
            kb_citations_used = result.get("kb_citations_used") or []

            kb_ok = bool(protocol_assessment.get("kb_sufficient", False))
            if not kb_ok or not session_protocol:
                llm_assessment = {"reasoning": protocol_assessment.get("sufficiency_reasoning", "LLM judged KB insufficient.")}
                return {
                    "agent_name": "ProtocolGenerator",
                    "status": "insufficient_kb",
                    "protocol": {},  # ✅ never None
                    "protocol_assessment": protocol_assessment,
                    "llm_assessment": llm_assessment,
                    "kb_sources": kb_chunks_dedup,
                    "kb_citations_used": kb_citations_used,
                    "phase_chunks": phase_chunks,
                    "phase_debug": phase_debug,
                    "sufficiency_check": suff,
                    "agent_metadata": {
                        "llm_calls": llm_calls,
                        "total_tokens": usage.get("total_tokens", 0),
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "kb_queries": len(phases),
                        "chunks_retrieved": sum(len(v) for v in phase_chunks.values()),
                        "chunks_deduplicated": len(kb_chunks_dedup),
                        "generation_time_seconds": (datetime.now() - started).total_seconds(),
                    },
                    "timestamp": datetime.now().isoformat(),
                }

            return {
                "agent_name": "ProtocolGenerator",
                "status": "success",
                "protocol": session_protocol,  # dict
                "protocol_assessment": protocol_assessment,
                "llm_assessment": {"reasoning": "Protocol generated successfully."},
                "kb_sources": kb_chunks_dedup,
                "kb_citations_used": kb_citations_used,
                "phase_chunks": phase_chunks,
                "phase_debug": phase_debug,
                "sufficiency_check": suff,
                "agent_metadata": {
                    "llm_calls": llm_calls,
                    "total_tokens": usage.get("total_tokens", 0),
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "kb_queries": len(phases),
                    "chunks_retrieved": sum(len(v) for v in phase_chunks.values()),
                    "chunks_deduplicated": len(kb_chunks_dedup),
                    "generation_time_seconds": (datetime.now() - started).total_seconds(),
                },
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            protocol_assessment = {
                "kb_sufficient": False,
                "sufficiency_reasoning": "System error during LLM call.",
                "missing_critical_elements": [],
            }
            llm_assessment = {"reasoning": str(e)}
            return {
                "agent_name": "ProtocolGenerator",
                "status": "error",
                "protocol": {},  # ✅ never None
                "protocol_assessment": protocol_assessment,
                "llm_assessment": llm_assessment,
                "kb_sources": kb_chunks_dedup,
                "kb_citations_used": [],
                "phase_chunks": phase_chunks,
                "phase_debug": phase_debug,
                "sufficiency_check": suff,
                "agent_metadata": {
                    "llm_calls": llm_calls,
                    "total_tokens": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "kb_queries": len(phases),
                    "chunks_retrieved": sum(len(v) for v in phase_chunks.values()),
                    "chunks_deduplicated": len(kb_chunks_dedup),
                    "generation_time_seconds": (datetime.now() - started).total_seconds(),
                },
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }
