from __future__ import annotations

import os
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from openai import AsyncOpenAI
from sqlalchemy.orm import Session

from app.resources.rag_service import RAGService

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")


class BlueprintGeneratorAgent:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = LLM_MODEL
        self.rag_service = RAGService()

        self.top_k = 12

        # gates (reasonable for pgvector cosine similarity)
        self.min_similarity_top1 = 0.25
        self.min_stage_signal_per_chunk = 1
        self.min_stage_evidence_chunks_required = 2

    # -------------------- universal chunk adapter --------------------

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

    def _chunk_title(self, ch: Any) -> str:
        return (
            self._val(ch, "resource_title")
            or self._val(ch, "title")
            or self._val(ch, "source_title")
            or self._val(ch, "source")
            or "Unknown source"
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

    # -------------------- structure detection --------------------

    def _stage_signal_score(self, text: str) -> int:
        t = (text or "").lower()
        terms = [
            "session 1", "session 2", "session 3", "session 4", "session 5",
            "agenda", "outline", "phase", "module", "time allocation", "minutes",
            "homework", "between-session",
            "erp", "exposure", "response prevention", "hierarchy",
            "relapse prevention", "maintenance",
        ]
        return sum(1 for s in terms if s in t)

    def _is_stage_evidence(self, text: str) -> bool:
        return self._stage_signal_score(text) >= self.min_stage_signal_per_chunk

    # -------------------- retrieval (two-pass with fallback) --------------------

    def _retrieve(self, db: Session, therapist_id: int, queries: List[str], top_k: int) -> List[Any]:
        all_chunks: List[Any] = []
        for q in queries:
            all_chunks.extend(self.rag_service.retrieve_chunks(
                db=db, therapist_id=therapist_id, query=q, top_k=top_k
            ) or [])
        all_chunks = self._dedupe_chunks(all_chunks)
        all_chunks.sort(key=lambda c: self._chunk_similarity(c), reverse=True)
        return all_chunks

    def _build_queries_pass_a(self, clinical_summary: Dict[str, Any], stage: str, session_focus: str) -> List[str]:
        profile = (clinical_summary or {}).get("patient_profile") or {}
        conditions = profile.get("conditions") or []
        condition_str = ", ".join(conditions) if conditions else "OCD"
        return [
            f"{condition_str} {stage} session structure phases time allocation agenda",
            f"{stage} therapy session outline phases activities homework",
            f"{condition_str} ERP session agenda hierarchy homework relapse prevention",
            f"{stage} session structure for {session_focus}",
        ]

    def _build_queries_pass_b_structure_only(self) -> List[str]:
        return [
            # very “session-outline” shaped queries
            "ERP treatment sessions Session 1 agenda Session 2 agenda Session 3 agenda",
            "OCD ERP treatment phases early middle late sessions outline",
            "constructing exposure hierarchy session agenda homework",
            "introducing exposure and response prevention session outline",
            "homework assignments between-session ERP outline",
            "relapse prevention maintenance final sessions agenda",
        ]

    def _check_kb_sufficiency(self, chunks: List[Any]) -> Dict[str, Any]:
        if not chunks:
            return {
                "sufficient": False,
                "chunk_count": 0,
                "highest_similarity": 0.0,
                "stage_evidence_chunks": 0,
                "reason": "No KB chunks retrieved for blueprint query",
            }

        sims = [self._chunk_similarity(c) for c in chunks]
        top1 = max(sims) if sims else 0.0
        stage_evidence = sum(1 for c in chunks if self._is_stage_evidence(self._chunk_text(c)))

        ok = (top1 >= self.min_similarity_top1) and (stage_evidence >= self.min_stage_evidence_chunks_required)
        return {
            "sufficient": ok,
            "chunk_count": len(chunks),
            "highest_similarity": top1,
            "stage_evidence_chunks": stage_evidence,
            "reason": None if ok else (
                f"Insufficient structure evidence: top1_sim={top1:.2f} (need ≥{self.min_similarity_top1}), "
                f"stage_chunks={stage_evidence} (need ≥{self.min_stage_evidence_chunks_required})."
            ),
        }

    # -------------------- prompts --------------------

    def _format_kb_text(self, kb_chunks: List[Any]) -> str:
        parts = []
        for i, ch in enumerate(kb_chunks, 1):
            cid = self._chunk_id(ch, i)
            title = self._chunk_title(ch)
            sim = self._chunk_similarity(ch)
            text = self._chunk_text(ch)
            parts.append(f"[Source {i}] chunk_id={cid} | title={title} | similarity={sim:.2f}\n{text}")
        return "\n\n---\n\n".join(parts)

    def _build_prompts(
        self,
        clinical_summary: Dict[str, Any],
        stage: str,
        stage_rationale: str,
        session_focus: str,
        kb_chunks: List[Any],
    ) -> Tuple[str, str]:
        kb_text = self._format_kb_text(kb_chunks)

        profile = (clinical_summary or {}).get("patient_profile") or {}
        traj = (clinical_summary or {}).get("symptom_trajectory") or {}
        priorities = (clinical_summary or {}).get("therapist_priorities") or {}
        concerns = (clinical_summary or {}).get("open_concerns") or {}

        system_prompt = """You are a clinical therapy session architect.

Create a HIGH-LEVEL SESSION BLUEPRINT (structure only) for a 60-minute session.

Rules:
- 4–6 phases
- Total minutes must equal exactly 60
- NO detailed scripts/dialogue
- Every activity must cite KB chunk_id as "chunk:..."

OUTPUT JSON:
{
  "blueprint_assessment": {
    "kb_sufficient": true/false,
    "sufficiency_reasoning": "one sentence",
    "missing_elements": []
  },
  "session_blueprint": {
    "phases": [
      {
        "phase_number": 1,
        "phase_name": "string",
        "time_allocation_minutes": number,
        "objectives": ["string"],
        "activities": [
          {
            "activity_name": "string",
            "kb_technique_reference": "string",
            "brief_description": "one sentence",
            "citations": ["chunk:..."]
          }
        ],
        "materials_needed": []
      }
    ],
    "materials_summary": [],
    "homework_preview": "string",
    "timing_check": "string"
  },
  "kb_sources_used": [
    {"chunk_id": "chunk:...", "what_it_contributed": "string"}
  ]
}
"""

        user_prompt = f"""CLINICAL CONTEXT:
{json.dumps(profile, indent=2)}

SYMPTOM TRAJECTORY:
{json.dumps(traj, indent=2)}

THERAPIST PRIORITIES:
{json.dumps(priorities, indent=2)}

OPEN CONCERNS:
{json.dumps(concerns, indent=2)}

STAGE: {stage}
STAGE RATIONALE: {stage_rationale}
SESSION FOCUS: {session_focus}

KB SOURCES:
{kb_text}

Generate the blueprint now."""
        return system_prompt, user_prompt

    async def _call_llm_json(self, system_prompt: str, user_prompt: str, max_tokens: int = 2000):
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

    # -------------------- execute --------------------

    async def execute(
        self,
        db: Session,
        therapist_id: int,
        clinical_summary: Dict[str, Any],
        stage: str,
        stage_rationale: str,
        session_focus: str
    ) -> Dict[str, Any]:
        started = datetime.now()
        llm_calls = 0

        blueprint_assessment: Dict[str, Any] = {}
        llm_assessment: Dict[str, Any] = {}
        kb_sources_used: List[Dict[str, Any]] = []

        # Pass A
        pass_a_queries = self._build_queries_pass_a(clinical_summary, stage, session_focus)
        pass_a_chunks = self._retrieve(db, therapist_id, pass_a_queries, top_k=self.top_k)
        pass_a_selected = pass_a_chunks[: self.top_k]
        suff_a = self._check_kb_sufficiency(pass_a_selected)

        retrieval_debug = {
            "pass_a_queries": pass_a_queries,
            "pass_a_selected_top_k": len(pass_a_selected),
            "pass_a_sample_texts_top5": [self._chunk_text(c)[:120] for c in pass_a_selected[:5]],
            "pass_a_sufficiency": suff_a,
        }

        # Fallback Pass B if Pass A insufficient
        final_chunks = pass_a_selected
        suff_final = suff_a

        if not suff_a["sufficient"]:
            pass_b_queries = self._build_queries_pass_b_structure_only()
            pass_b_chunks = self._retrieve(db, therapist_id, pass_b_queries, top_k=self.top_k)
            pass_b_selected = pass_b_chunks[: self.top_k]

            merged = self._dedupe_chunks(pass_a_selected + pass_b_selected)
            merged.sort(key=lambda c: self._chunk_similarity(c), reverse=True)
            final_chunks = merged[: self.top_k]

            suff_final = self._check_kb_sufficiency(final_chunks)

            retrieval_debug.update({
                "pass_b_queries": pass_b_queries,
                "pass_b_selected_top_k": len(pass_b_selected),
                "pass_b_sample_texts_top5": [self._chunk_text(c)[:120] for c in pass_b_selected[:5]],
                "merged_selected_top_k": len(final_chunks),
                "merged_sample_texts_top5": [self._chunk_text(c)[:120] for c in final_chunks[:5]],
                "merged_sufficiency": suff_final,
            })

        # If STILL insufficient, return safely
        if not suff_final["sufficient"]:
            blueprint_assessment = {
                "kb_sufficient": False,
                "sufficiency_reasoning": suff_final["reason"] or "KB insufficient for blueprint generation.",
                "missing_elements": ["session structure / phase guidance for stage"],
            }
            llm_assessment = {"reasoning": "Tier-1 gates failed after Pass A + fallback Pass B."}

            return {
                "agent_name": "BlueprintGenerator",
                "status": "insufficient_kb",
                "blueprint": None,
                "blueprint_assessment": blueprint_assessment,
                "llm_assessment": llm_assessment,
                "kb_sources": final_chunks,
                "kb_sources_used": kb_sources_used,
                "sufficiency_check": suff_final,
                "retrieval_debug": retrieval_debug,
                "agent_metadata": {
                    "llm_calls": llm_calls,
                    "total_tokens": 0,
                    "generation_time_seconds": (datetime.now() - started).total_seconds(),
                    "kb_chunks_retrieved": len(final_chunks),
                },
                "timestamp": datetime.now().isoformat(),
            }

        # Call LLM
        system_prompt, user_prompt = self._build_prompts(
            clinical_summary=clinical_summary,
            stage=stage,
            stage_rationale=stage_rationale,
            session_focus=session_focus,
            kb_chunks=final_chunks,
        )

        result, usage = await self._call_llm_json(system_prompt, user_prompt)
        llm_calls += 1

        blueprint_assessment = result.get("blueprint_assessment") or {}
        session_blueprint = result.get("session_blueprint") or None
        kb_sources_used = result.get("kb_sources_used") or []
        kb_ok = bool(blueprint_assessment.get("kb_sufficient", False))

        if not kb_ok or not session_blueprint:
            llm_assessment = {"reasoning": blueprint_assessment.get("sufficiency_reasoning", "LLM judged KB insufficient.")}
            return {
                "agent_name": "BlueprintGenerator",
                "status": "insufficient_kb",
                "blueprint": None,
                "blueprint_assessment": blueprint_assessment,
                "llm_assessment": llm_assessment,
                "kb_sources": final_chunks,
                "kb_sources_used": kb_sources_used,
                "sufficiency_check": suff_final,
                "retrieval_debug": retrieval_debug,
                "agent_metadata": {
                    "llm_calls": llm_calls,
                    "total_tokens": usage.get("total_tokens", 0),
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "generation_time_seconds": (datetime.now() - started).total_seconds(),
                    "kb_chunks_retrieved": len(final_chunks),
                },
                "timestamp": datetime.now().isoformat(),
            }

        return {
            "agent_name": "BlueprintGenerator",
            "status": "success",
            "blueprint": session_blueprint,
            "blueprint_assessment": blueprint_assessment,
            "llm_assessment": {"reasoning": "Blueprint generated successfully."},
            "kb_sources": final_chunks,
            "kb_sources_used": kb_sources_used,
            "sufficiency_check": suff_final,
            "retrieval_debug": retrieval_debug,
            "agent_metadata": {
                "llm_calls": llm_calls,
                "total_tokens": usage.get("total_tokens", 0),
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "generation_time_seconds": (datetime.now() - started).total_seconds(),
                "kb_chunks_retrieved": len(final_chunks),
            },
            "timestamp": datetime.now().isoformat(),
        }
