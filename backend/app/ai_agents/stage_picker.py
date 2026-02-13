"""
Stage Picker Agent - LLM + RAG with Self-Verification Loop (Agent 3)

FULL UPDATED VERSION (Feb 12, 2026) — includes all fixes discussed:

✅ Fix 1: Universal chunk schema adapter that works for:
   - dict chunks
   - SQLAlchemy ORM objects
   - nested metadata fields

✅ Fix 2: Correctly handles "distance" as distance (lower=better) by converting to similarity.

✅ Fix 3: Less-fragile stage-evidence gate:
   - min_stage_signal_per_chunk = 1
   - min_stage_evidence_chunks_required = 2
   - adds "session 1/2/3/4" to stage term detector

✅ Fix 4: Debug proof fields:
   - sample_texts_top5 so you can instantly confirm if chunks are empty
   - first_chunk_keys + first_chunk_text_preview

✅ Fix 5: Quota merge still enforced:
   - stage chunks forced in final context (if present)
   - diagnosis-heavy chunks capped

Assumptions:
- RAGService.retrieve_chunks(db, therapist_id, query, top_k) returns list[dict] OR list[ORM objects]
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List, Tuple
import os
import json
from datetime import datetime

from openai import AsyncOpenAI
from sqlalchemy.orm import Session

from app.resources.rag_service import RAGService

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class StagePickerAgent:
    def __init__(self, db: Session, max_iterations: int = 2):
        self.db = db
        self.agent_name = "StagePickerAgent"
        self.llm_model = LLM_MODEL
        self.rag_service = RAGService()
        self.max_iterations = max_iterations

        # Retrieval controls
        self.selection_top_k_per_query = 6
        self.selection_final_top_k = 16
        self.verification_top_k = 10

        # Quota controls (prevents diagnosis chunks from drowning stage chunks)
        self.min_stage_chunks = 6
        self.max_diag_chunks = 3

        # Evidence gate (LESS STRICT to avoid false negatives)
        self.min_stage_signal_per_chunk = 1
        self.min_stage_evidence_chunks_required = 2

    # --------------------------------------------------------------------------
    # Universal chunk accessor (dict OR ORM object)  ✅ FIX
    # --------------------------------------------------------------------------

    def _val(self, ch: Any, key: str, default=None):
        """Read value from dict OR object attribute. Also checks ch.metadata dict."""
        if ch is None:
            return default

        # dict
        if isinstance(ch, dict):
            if key in ch and ch[key] is not None:
                return ch[key]
            md = ch.get("metadata")
            if isinstance(md, dict) and key in md and md[key] is not None:
                return md[key]
            return default

        # ORM object / Pydantic model
        if hasattr(ch, key):
            v = getattr(ch, key)
            if v is not None:
                return v

        # metadata attribute (common on chunk objects)
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
            or self._val(ch, "raw_text")
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
        """
        Handles:
        - similarity_score / similarity / score (higher = better)
        - distance (lower = better) -> convert to similarity

        NOTE:
        If your distance is cosine distance in [0,1], similarity = 1 - distance
        If your distance is cosine distance in [0,2], we clamp conservatively.
        """
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
                # conservative clamp
                if d <= 2.0:
                    # treat anything >1 as very low similarity
                    return max(0.0, 1.0 - min(1.0, d))
                return 0.0
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

    # --------------------------------------------------------------------------
    # Diagnosis vs Stage evidence classifiers
    # --------------------------------------------------------------------------

    def _is_diagnosis_heavy(self, text: str) -> bool:
        t = (text or "").lower()
        diag_terms = [
            "diagnostic criteria", "dsm", "criterion", "criteria a", "criteria b",
            "obsessions", "compulsions", "recurrent and persistent", "intrusive",
            "marked anxiety", "neutralize", "thought insertion",
            "product of his or her own mind",
        ]
        hits = sum(1 for s in diag_terms if s in t)
        return hits >= 2

    def _stage_signal_score(self, text: str) -> int:
        t = (text or "").lower()
        stage_terms = [
            # session outline keywords
            "session 1", "session 2", "session 3", "session 4",
            "session 5", "session 6", "session 7", "session 8",
            "session", "outline", "agenda",

            # planning & structure
            "treatment planning", "psychoeducation", "information gathering",
            "phase", "stage", "module", "step",

            # ERP-specific structure
            "erp", "exposure", "response prevention", "ritual prevention", "hierarchy",
            "homework", "assignment", "between-session",

            # progression & readiness
            "progression", "readiness", "prerequisite", "entry criteria", "requirements",
            "before beginning exposure",

            # closure
            "relapse prevention", "maintenance", "final session",
        ]
        return sum(1 for s in stage_terms if s in t)

    def _is_stage_evidence(self, text: str) -> bool:
        return self._stage_signal_score(text) >= self.min_stage_signal_per_chunk

    # --------------------------------------------------------------------------
    # Prompt building
    # --------------------------------------------------------------------------

    def _build_selection_prompt(self, clinical_summary_text: str, session_focus: Optional[str]) -> str:
        focus_text = f"\n\nTHERAPIST SESSION FOCUS:\n{session_focus}" if session_focus else ""
        return f"""You are a therapy stage classification expert.

CLINICAL SUMMARY:
{clinical_summary_text}
{focus_text}

KNOWLEDGE BASE CONTEXT:
{{kb_context}}

TASK:
1) Choose the most appropriate therapy stage/phase/module for the upcoming session using ONLY treatment-stage/session-structure evidence.
2) Justify using ONLY evidence from the clinical summary + KB context.

STRICT RULES:
- Do NOT use diagnostic criteria alone to infer treatment stage.
- If KB context lacks stage/phase/session structure or ERP sequencing guidance, output status="insufficient_stage_evidence".
- Do not invent stages or cite sources not present in KB context.
- Cite KB by chunk_id only. Use citations like [chunk:abc123].

OUTPUT JSON:
{{
  "status": "proposed" | "insufficient_stage_evidence",
  "proposed_stage": "string (required if proposed)",
  "reasoning": "string (required if proposed) - include citations [chunk:...]",
  "confidence": "high" | "medium" | "low",
  "kb_sources_used": ["chunk_id1", "chunk_id2"],
  "reason_if_insufficient": "string (required if insufficient_stage_evidence)"
}}"""

    def _build_verification_prompt(self, clinical_summary_text: str, proposed_stage: str, selection_reasoning: str) -> str:
        return f"""You are a therapy stage verification expert.

CLINICAL SUMMARY:
{clinical_summary_text}

PROPOSED STAGE: {proposed_stage}
SELECTION REASONING:
{selection_reasoning}

KB ENTRY CRITERIA / PREREQUISITES:
{{kb_context}}

TASK:
1) Extract entry criteria/prerequisites for "{proposed_stage}" from KB.
2) Compare patient status to those criteria.
3) Decide confirmed vs rejected.

STRICT RULES:
- If KB lacks explicit entry criteria for this stage, verification_status="rejected" and revision_suggestion="insufficient_stage_evidence".
- Cite KB by chunk_id only. Use citations like [chunk:abc123].
- If rejected, suggest an alternative stage OR "insufficient_stage_evidence".

OUTPUT JSON:
{{
  "verification_status": "confirmed" | "rejected",
  "verification_reasoning": "string - include citations [chunk:...]",
  "patient_criteria_match": "high" | "medium" | "low",
  "kb_sources_used": ["chunk_id1", "chunk_id2"],
  "revision_suggestion": "alternative_stage_string" | "insufficient_stage_evidence"
}}"""

    # --------------------------------------------------------------------------
    # Clinical summary formatting
    # --------------------------------------------------------------------------

    def _format_clinical_summary_for_prompt(self, clinical_summary: Dict[str, Any]) -> str:
        sections: List[str] = []

        profile = clinical_summary.get("patient_profile", {}) or {}
        sections.append(f"PATIENT: {profile.get('name', 'Unknown')}")
        sections.append(f"CONDITIONS: {', '.join(profile.get('conditions', []) or [])}")
        sections.append(f"WEEK: {profile.get('current_week', 'Unknown')}")
        sections.append(f"DESCRIPTION: {profile.get('conditions_description', '')}")
        sections.append("")

        trajectory = clinical_summary.get("symptom_trajectory", {}) or {}
        sections.append(f"SYMPTOM TRAJECTORY: {str(trajectory.get('direction', 'unknown')).upper()}")
        sections.append(f"EVIDENCE: {trajectory.get('evidence', '')}")
        if trajectory.get("key_inflection_points"):
            sections.append(f"KEY POINTS: {', '.join(trajectory.get('key_inflection_points', []) or [])}")
        sections.append("")

        themes = clinical_summary.get("recent_session_themes", {}) or {}
        if themes:
            sections.append("RECENT SESSION THEMES:")
            if themes.get("attempted"):
                sections.append(f"- Attempted: {', '.join(themes.get('attempted', []) or [])}")
            if themes.get("what_worked"):
                sections.append(f"- Worked: {', '.join(themes.get('what_worked', []) or [])}")
            if themes.get("what_didnt_work"):
                sections.append(f"- Didn't work: {', '.join(themes.get('what_didnt_work', []) or [])}")
            sections.append("")

        priorities = clinical_summary.get("therapist_priorities", {}) or {}
        if priorities:
            sections.append("THERAPIST PRIORITIES:")
            if priorities.get("from_notes"):
                sections.append(f"- From notes: {', '.join(priorities.get('from_notes', []) or [])}")
            if priorities.get("ai_instruction"):
                sections.append(f"- AI instruction: {priorities.get('ai_instruction')}")
            sections.append("")

        concerns = clinical_summary.get("open_concerns", {}) or {}
        if any(concerns.values()):
            sections.append("OPEN CONCERNS:")
            if concerns.get("red_flags"):
                sections.append(f"- Red flags: {', '.join(concerns.get('red_flags', []) or [])}")
            if concerns.get("stagnation_signals"):
                sections.append(f"- Stagnation: {', '.join(concerns.get('stagnation_signals', []) or [])}")
            if concerns.get("unresolved_issues"):
                sections.append(f"- Unresolved: {', '.join(concerns.get('unresolved_issues', []) or [])}")
            sections.append("")

        rev = clinical_summary.get("_revision_feedback")
        if rev:
            sections.append("REVISION FEEDBACK:")
            sections.append(f"- Previous proposed: {rev.get('previous_proposed')}")
            sections.append(f"- Reason rejected: {rev.get('reason')}")
            sections.append(f"- Suggested alternative: {rev.get('suggested_alternative')}")
            sections.append("")

        return "\n".join(sections).strip()

    # --------------------------------------------------------------------------
    # KB retrieval helpers
    # --------------------------------------------------------------------------

    def _retrieve_multiquery(self, therapist_id: int, queries: List[str], top_k_per_query: int) -> List[Any]:
        all_chunks: List[Any] = []
        for q in queries:
            chunks = self.rag_service.retrieve_chunks(
                db=self.db,
                therapist_id=therapist_id,
                query=q,
                top_k=top_k_per_query,
            )
            all_chunks.extend(chunks or [])
        return all_chunks

    def _merge_with_quota(
        self,
        chunks: List[Any],
        final_top_k: int,
        min_stage_chunks: int,
        max_diag_chunks: int,
    ) -> List[Any]:
        """Guarantee stage evidence cannot be drowned out by diagnosis-heavy chunks."""
        chunks = self._dedupe_chunks(chunks)
        chunks.sort(key=lambda c: self._chunk_similarity(c), reverse=True)

        stage_chunks: List[Any] = []
        diag_chunks: List[Any] = []
        other_chunks: List[Any] = []

        for c in chunks:
            txt = self._chunk_text(c)
            if self._is_stage_evidence(txt):
                stage_chunks.append(c)
            elif self._is_diagnosis_heavy(txt):
                diag_chunks.append(c)
            else:
                other_chunks.append(c)

        stage_chunks.sort(
            key=lambda c: (self._chunk_similarity(c), self._stage_signal_score(self._chunk_text(c))),
            reverse=True
        )
        other_chunks.sort(key=lambda c: self._chunk_similarity(c), reverse=True)
        diag_chunks.sort(key=lambda c: self._chunk_similarity(c), reverse=True)

        selected: List[Any] = []

        selected.extend(stage_chunks[:min_stage_chunks])

        for c in other_chunks:
            if len(selected) >= final_top_k:
                break
            selected.append(c)

        for c in diag_chunks[:max_diag_chunks]:
            if len(selected) >= final_top_k:
                break
            selected.append(c)

        return self._dedupe_chunks(selected)[:final_top_k]

    def _compute_stage_evidence_count(self, chunks: List[Any]) -> int:
        return sum(1 for c in chunks if self._is_stage_evidence(self._chunk_text(c)))

    def _compute_diag_count(self, chunks: List[Any]) -> int:
        return sum(1 for c in chunks if self._is_diagnosis_heavy(self._chunk_text(c)))

    def _query_kb_for_selection_two_pass(
        self,
        therapist_id: int,
        clinical_summary: Dict[str, Any],
        session_focus: Optional[str] = None,
    ) -> Tuple[List[Any], Dict[str, Any]]:
        """
        PASS A: symptom/condition focused
        PASS B: stage/session-outline focused
        MERGE: quota composition to force stage chunks in final context
        """
        patient_conditions = (clinical_summary.get("patient_profile", {}) or {}).get("conditions", []) or []
        condition_str = ", ".join(patient_conditions) if patient_conditions else "OCD"

        symptoms_hint = ""
        themes = clinical_summary.get("recent_session_themes", {})
        if isinstance(themes, dict):
            attempted = themes.get("attempted") or []
            if isinstance(attempted, list):
                symptoms_hint = " ".join(attempted)[:140]

        # PASS A
        pass_a_queries: List[str] = [f"{condition_str} severe symptoms compulsions obsessions"]
        if symptoms_hint:
            pass_a_queries.append(f"{condition_str} {symptoms_hint}")
        if session_focus:
            pass_a_queries.append(f"{condition_str} {session_focus}")

        pass_a_chunks = self._retrieve_multiquery(
            therapist_id=therapist_id,
            queries=pass_a_queries,
            top_k_per_query=self.selection_top_k_per_query,
        )

        # PASS B (structure)
        pass_b_queries: List[str] = [
            "OCD treatment planning Session 1 Session 2 outline",
            "information gathering sessions OCD treatment program outline",
            "introducing exposure response prevention Session 3 Session 4",
            "constructing exposure hierarchy treatment planning",
            "homework assignments exposure response prevention ritual prevention",
            "relapse prevention maintenance final sessions OCD",
            "ERP treatment phases progression criteria prerequisites",
            "therapy phase module step entry criteria prerequisites response prevention",
            "before beginning exposure what must be completed hierarchy psychoeducation",
        ]
        if session_focus:
            pass_b_queries.append(f"{session_focus} which session treatment planning exposure")

        pass_b_chunks = self._retrieve_multiquery(
            therapist_id=therapist_id,
            queries=pass_b_queries,
            top_k_per_query=max(self.selection_top_k_per_query, 7),
        )

        merged = pass_a_chunks + pass_b_chunks
        final_chunks = self._merge_with_quota(
            chunks=merged,
            final_top_k=self.selection_final_top_k,
            min_stage_chunks=self.min_stage_chunks,
            max_diag_chunks=self.max_diag_chunks,
        )

        debug: Dict[str, Any] = {
            "pass_a_queries": pass_a_queries,
            "pass_b_queries": pass_b_queries,
            "pass_a_retrieved": len(pass_a_chunks),
            "pass_b_retrieved": len(pass_b_chunks),
            "merged_total": len(self._dedupe_chunks(merged)),
            "final_selected": len(final_chunks),
            "final_stage_evidence_chunks": self._compute_stage_evidence_count(final_chunks),
            "final_diag_chunks": self._compute_diag_count(final_chunks),
        }

        if pass_b_chunks:
            # show dict keys OR object attributes
            if isinstance(pass_b_chunks[0], dict):
                debug["first_chunk_keys"] = sorted(list(pass_b_chunks[0].keys()))
            else:
                debug["first_chunk_keys"] = sorted([a for a in dir(pass_b_chunks[0]) if not a.startswith("_")])[:50]
            debug["first_chunk_text_preview"] = self._chunk_text(pass_b_chunks[0])[:200]

        # ✅ DEBUG PROOF: show whether top chunks are empty
        debug["sample_texts_top5"] = [self._chunk_text(c)[:120] for c in final_chunks[:5]]

        return final_chunks, debug

    def _query_kb_for_verification(self, therapist_id: int, proposed_stage: str) -> List[Any]:
        queries = [
            f'entry criteria prerequisites requirements "{proposed_stage}"',
            f'"{proposed_stage}" stage prerequisites readiness criteria',
            f'before beginning "{proposed_stage}" what must be completed',
            "ERP prerequisites hierarchy psychoeducation readiness criteria",
        ]
        chunks = self._retrieve_multiquery(therapist_id, queries, top_k_per_query=self.verification_top_k)
        chunks = self._dedupe_chunks(chunks)
        chunks.sort(
            key=lambda c: (
                self._chunk_similarity(c),
                self._stage_signal_score(self._chunk_text(c)),
                -int(self._is_diagnosis_heavy(self._chunk_text(c))),
            ),
            reverse=True
        )
        return chunks[: self.verification_top_k]

    # --------------------------------------------------------------------------
    # KB sufficiency
    # --------------------------------------------------------------------------

    def _kb_stats(self, chunks: List[Any]) -> Dict[str, Any]:
        if not chunks:
            return {"kb_chunks_retrieved": 0, "highest_similarity": 0.0, "avg_top3_similarity": 0.0}
        sims = sorted([self._chunk_similarity(c) for c in chunks], reverse=True)
        top1 = sims[0]
        top3 = sims[:3]
        avg3 = sum(top3) / max(len(top3), 1)
        return {"kb_chunks_retrieved": len(chunks), "highest_similarity": top1, "avg_top3_similarity": avg3}

    def _check_kb_sufficiency_selection(self, chunks: List[Any]) -> Tuple[bool, Dict[str, Any]]:
        stats = self._kb_stats(chunks)
        stage_evidence = self._compute_stage_evidence_count(chunks)
        diag_count = self._compute_diag_count(chunks)

        sim_ok = (stats["highest_similarity"] >= 0.30)
        stage_ok = (stage_evidence >= self.min_stage_evidence_chunks_required)

        return (sim_ok and stage_ok), {
            "sim_stats": stats,
            "stage_evidence_chunks": stage_evidence,
            "diagnosis_heavy_chunks": diag_count,
        }

    def _check_kb_sufficiency_verification(self, chunks: List[Any]) -> Tuple[bool, Dict[str, Any]]:
        stats = self._kb_stats(chunks)
        diag_count = self._compute_diag_count(chunks)
        ok = (stats["highest_similarity"] >= 0.28 and diag_count < len(chunks))
        return ok, {"sim_stats": stats, "diagnosis_heavy_chunks": diag_count}

    # --------------------------------------------------------------------------
    # KB formatting
    # --------------------------------------------------------------------------

    def _format_kb_context(self, chunks: List[Any]) -> str:
        if not chunks:
            return "No knowledge base information available."

        parts = []
        for idx, ch in enumerate(chunks, 1):
            cid = self._chunk_id(ch, idx)
            title = self._chunk_title(ch)
            sim = self._chunk_similarity(ch)
            text = self._chunk_text(ch)
            parts.append(f"[Source {idx}] chunk_id={cid} | title={title} | similarity={sim:.2f}\n{text}")
        return "\n\n---\n\n".join(parts)

    # --------------------------------------------------------------------------
    # LLM call (async, JSON enforced)
    # --------------------------------------------------------------------------

    async def _call_llm_json(self, prompt: str, max_tokens: int = 1000) -> Tuple[Dict[str, Any], Dict[str, int]]:
        resp = await client.chat.completions.create(
            model=self.llm_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content or "{}"
        data = json.loads(content)
        usage = {
            "prompt": getattr(resp.usage, "prompt_tokens", 0),
            "completion": getattr(resp.usage, "completion_tokens", 0),
            "total": getattr(resp.usage, "total_tokens", 0),
        }
        return data, usage

    # --------------------------------------------------------------------------
    # Main execute
    # --------------------------------------------------------------------------

    async def execute(
        self,
        therapist_id: int,
        clinical_summary: Dict[str, Any],
        session_focus: Optional[str] = None
    ) -> Dict[str, Any]:
        verification_history: List[Dict[str, Any]] = []
        started_at = datetime.now().isoformat()
        llm_calls = 0

        kb_chunks_used: List[Any] = []

        def add_kb(chunks: List[Any]):
            nonlocal kb_chunks_used
            kb_chunks_used = self._dedupe_chunks(kb_chunks_used + (chunks or []))

        try:
            # -----------------------
            # Iteration 1: Selection (PASS A + PASS B + QUOTA MERGE)
            # -----------------------
            sel_chunks, retrieval_debug = self._query_kb_for_selection_two_pass(
                therapist_id=therapist_id,
                clinical_summary=clinical_summary,
                session_focus=session_focus,
            )
            add_kb(sel_chunks)

            ok_sel, sel_stats = self._check_kb_sufficiency_selection(sel_chunks)
            if not ok_sel:
                return {
                    "status": "needs_clarification",
                    "reason": (
                        "After pass A + pass B, KB still lacks enough treatment-stage/session-structure evidence "
                        "to select a stage. Check retrieval_debug.sample_texts_top5: if empty, your chunk schema "
                        "was mismatched; if not empty, your chunking likely split headings away from outlines."
                    ),
                    "kb_stats": sel_stats,
                    "retrieval_debug": retrieval_debug,
                    "kb_chunks_used": kb_chunks_used,
                    "verification_history": verification_history,
                    "agent_metadata": {
                        "agent_name": self.agent_name,
                        "llm_calls": llm_calls,
                        "iterations": 0,
                        "started_at": started_at,
                    },
                }

            clinical_text = self._format_clinical_summary_for_prompt(clinical_summary)
            sel_context = self._format_kb_context(sel_chunks)
            sel_prompt = self._build_selection_prompt(clinical_text, session_focus).replace("{kb_context}", sel_context)

            sel_result, sel_usage = await self._call_llm_json(sel_prompt)
            llm_calls += 1

            verification_history.append({
                "iteration": 1,
                "phase": "selection",
                "result": sel_result,
                "tokens_used": sel_usage,
                "kb_stats": sel_stats,
                "retrieval_debug": retrieval_debug,
            })

            if sel_result.get("status") == "insufficient_stage_evidence":
                return {
                    "status": "needs_clarification",
                    "reason": sel_result.get("reason_if_insufficient") or "KB context lacks stage evidence to select stage.",
                    "kb_stats": sel_stats,
                    "retrieval_debug": retrieval_debug,
                    "kb_chunks_used": kb_chunks_used,
                    "verification_history": verification_history,
                    "agent_metadata": {
                        "agent_name": self.agent_name,
                        "llm_calls": llm_calls,
                        "iterations": 1,
                        "started_at": started_at,
                    },
                }

            proposed_stage = sel_result.get("proposed_stage")
            selection_reasoning = sel_result.get("reasoning", "")

            # --------------------------
            # Iteration 1: Verification
            # --------------------------
            ver_chunks = self._query_kb_for_verification(therapist_id, proposed_stage)
            add_kb(ver_chunks)

            ok_ver, ver_stats = self._check_kb_sufficiency_verification(ver_chunks)
            if not ok_ver:
                return {
                    "status": "needs_clarification",
                    "reason": "Cannot verify stage because KB lacks explicit entry criteria/prerequisites content.",
                    "selected_stage": proposed_stage,
                    "verification_status": "rejected",
                    "kb_stats": ver_stats,
                    "kb_chunks_used": kb_chunks_used,
                    "verification_history": verification_history,
                    "agent_metadata": {
                        "agent_name": self.agent_name,
                        "llm_calls": llm_calls,
                        "iterations": 1,
                        "loop_triggered": True,
                        "started_at": started_at,
                    },
                }

            ver_context = self._format_kb_context(ver_chunks)
            ver_prompt = self._build_verification_prompt(clinical_text, proposed_stage, selection_reasoning).replace(
                "{kb_context}", ver_context
            )

            ver_result, ver_usage = await self._call_llm_json(ver_prompt)
            llm_calls += 1

            verification_history.append({
                "iteration": 1,
                "phase": "verification",
                "result": ver_result,
                "tokens_used": ver_usage,
                "kb_stats": ver_stats,
            })

            if ver_result.get("verification_status") == "confirmed":
                return {
                    "status": "success",
                    "selected_stage": proposed_stage,
                    "selection_reasoning": selection_reasoning,
                    "verification_status": "confirmed",
                    "verification_reasoning": ver_result.get("verification_reasoning"),
                    "confidence": sel_result.get("confidence"),
                    "kb_chunks_used": kb_chunks_used,
                    "verification_history": verification_history,
                    "agent_metadata": {
                        "agent_name": self.agent_name,
                        "agent_type": "llm_with_rag_and_verification",
                        "llm_calls": llm_calls,
                        "iterations": 1,
                        "loop_triggered": False,
                        "verified_on_first_attempt": True,
                        "started_at": started_at,
                    },
                }

            # -----------------------
            # Iteration 2: Revision
            # -----------------------
            if self.max_iterations < 2:
                return {
                    "status": "needs_clarification",
                    "reason": "Stage verification rejected; revision disabled by max_iterations.",
                    "selected_stage": proposed_stage,
                    "verification_status": "rejected",
                    "kb_chunks_used": kb_chunks_used,
                    "verification_history": verification_history,
                }

            revision_suggestion = ver_result.get("revision_suggestion")
            if revision_suggestion == "insufficient_stage_evidence":
                return {
                    "status": "needs_clarification",
                    "reason": "Verification rejected and KB lacked enough evidence to revise safely; therapist confirmation required.",
                    "selected_stage": proposed_stage,
                    "verification_status": "rejected",
                    "kb_chunks_used": kb_chunks_used,
                    "verification_history": verification_history,
                }

            revised_summary = dict(clinical_summary)
            revised_summary["_revision_feedback"] = {
                "previous_proposed": proposed_stage,
                "verification_result": "REJECTED",
                "reason": ver_result.get("verification_reasoning"),
                "suggested_alternative": revision_suggestion,
            }

            revised_text = self._format_clinical_summary_for_prompt(revised_summary)

            sel2_chunks, retrieval_debug_2 = self._query_kb_for_selection_two_pass(
                therapist_id=therapist_id,
                clinical_summary=revised_summary,
                session_focus=session_focus,
            )
            add_kb(sel2_chunks)

            ok_sel2, sel2_stats = self._check_kb_sufficiency_selection(sel2_chunks)
            if not ok_sel2:
                return {
                    "status": "needs_clarification",
                    "reason": "Still lacking treatment-stage evidence after revision retrieval; therapist input needed.",
                    "kb_stats": sel2_stats,
                    "retrieval_debug": retrieval_debug_2,
                    "kb_chunks_used": kb_chunks_used,
                    "verification_history": verification_history,
                }

            sel2_context = self._format_kb_context(sel2_chunks)
            sel2_prompt = self._build_selection_prompt(revised_text, session_focus).replace("{kb_context}", sel2_context)
            sel2_result, sel2_usage = await self._call_llm_json(sel2_prompt)
            llm_calls += 1

            revised_stage = sel2_result.get("proposed_stage")
            revised_reasoning = sel2_result.get("reasoning", "")

            ver2_chunks = self._query_kb_for_verification(therapist_id, revised_stage)
            add_kb(ver2_chunks)

            ver2_context = self._format_kb_context(ver2_chunks)
            ver2_prompt = self._build_verification_prompt(revised_text, revised_stage, revised_reasoning).replace(
                "{kb_context}", ver2_context
            )
            ver2_result, ver2_usage = await self._call_llm_json(ver2_prompt)
            llm_calls += 1

            if ver2_result.get("verification_status") == "confirmed":
                return {
                    "status": "success",
                    "selected_stage": revised_stage,
                    "selection_reasoning": revised_reasoning,
                    "verification_status": "confirmed",
                    "verification_reasoning": ver2_result.get("verification_reasoning"),
                    "confidence": sel2_result.get("confidence"),
                    "kb_chunks_used": kb_chunks_used,
                    "verification_history": verification_history,
                }

            return {
                "status": "needs_clarification",
                "reason": "Stage remains unverified after max iterations; therapist confirmation required.",
                "selected_stage": revised_stage,
                "selection_reasoning": revised_reasoning,
                "verification_status": "rejected",
                "verification_reasoning": ver2_result.get("verification_reasoning"),
                "kb_chunks_used": kb_chunks_used,
                "verification_history": verification_history,
            }

        except Exception as e:
            return {
                "status": "error",
                "error_type": "system_error",
                "error_message": str(e),
                "selected_stage": None,
                "kb_chunks_used": kb_chunks_used,
                "verification_history": verification_history,
                "agent_metadata": {
                    "agent_name": self.agent_name,
                    "llm_calls": llm_calls,
                    "started_at": started_at,
                },
            }
