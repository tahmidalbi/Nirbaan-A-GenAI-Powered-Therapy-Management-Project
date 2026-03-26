from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.patients.models import Patient
from app.therapists.models import Therapist

from app.NirbaanAITherapist.models import (
    AnalysisRunStatus,
    ClarificationStatus,
    PatientAnalysisClarification,
    PatientAnalysisRun,
    TherapistAIChatMessage,
    TherapistAIChatThread,
    TherapistChatRole,
)
from app.NirbaanAITherapist.schemas import (
    ResumePatientAnalysisResponse,
    TherapistChatSendResponse,
)
from app.NirbaanAITherapist.state import NirbaanAITherapistState
from app.NirbaanAITherapist.graph import (
    invoke_resume_therapist_analysis_graph,
    invoke_therapist_analysis_graph,
)
from app.NirbaanAITherapist.Nodes.load_patient_context import load_patient_context_node
from app.NirbaanAITherapist.Nodes.retrieve_kb import retrieve_kb_node


class TherapistAIChatService:
    RECENT_HISTORY_LIMIT = 6

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def send_message(
        self,
        *,
        therapist_id: int,
        message: str,
        patient_id: Optional[int] = None,
        thread_id: Optional[int] = None,
    ) -> TherapistChatSendResponse:
        """
        Therapist sends a chat message to the AI.

        Flow:
        1. Validate therapist / patient
        2. Create or validate chat thread
        3. Save therapist message
        4. Create analysis run
        5. Invoke analysis graph
        6. If clarification needed -> persist question and return it
        7. Else save assistant response and return it
        """
        therapist = self._get_therapist_or_raise(therapist_id)
        clean_message = message.strip()
        if not clean_message:
            raise ValueError("Message cannot be empty.")

        if patient_id is None:
            raise ValueError("Patient ID is required for therapist-side patient analysis.")

        self._get_patient_or_raise(patient_id)

        thread = self._get_or_create_thread(
            therapist_id=therapist.id,
            patient_id=patient_id,
            thread_id=thread_id,
        )

        user_msg = self._save_chat_message(
            thread_id=thread.id,
            role=TherapistChatRole.THERAPIST.value,
            content=clean_message,
        )

        recent_chat_history = self._get_recent_chat_history(thread.id)

        run = self._create_analysis_run(
            therapist_id=therapist.id,
            patient_id=patient_id,
            thread_id=thread.id,
            analysis_goal=clean_message,
        )

        initial_state: NirbaanAITherapistState = {
            "therapist_id": therapist.id,
            "patient_id": patient_id,
            "thread_id": thread.id,
            "analysis_run_id": run.id,
            "user_message": clean_message,
            "recent_chat_history": recent_chat_history,
            "analysis_goal": clean_message,
            "latest_weekly_progress": None,
            "initial_fear_ladder": None,
            "obsession_compulsion_pairs": [],
            "patient_context_summary": "",
            "retrieval_query": "",
            "kb_chunks": [],
            "kb_context_summary": "",
            "draft_analysis": "",
            "analysis_summary": "",
            "needs_clarification": False,
            "clarification_question": "",
            "clarification_answer": "",
            "final_analysis": "",
            "final_response": "",
            "used_sources": [],
            "error_message": "",
            "status": "running",
        }

        final_state = invoke_therapist_analysis_graph(initial_state)

        run.draft_analysis = (final_state.get("draft_analysis") or "").strip() or None
        run.analysis_summary = (final_state.get("analysis_summary") or "").strip() or None

        if final_state.get("needs_clarification", False):
            run.status = AnalysisRunStatus.NEEDS_CLARIFICATION.value

            clarification = self._create_clarification(
                analysis_run_id=run.id,
                question=(final_state.get("clarification_question") or "").strip(),
            )

            self.db.commit()
            self.db.refresh(run)
            self.db.refresh(clarification)

            return TherapistChatSendResponse(
                thread_id=thread.id,
                user_message=user_msg,
                assistant_message=None,
                needs_clarification=True,
                clarification=clarification,
                analysis_run=run,
            )

        assistant_text = (
            (final_state.get("final_response") or "").strip()
            or (final_state.get("final_analysis") or "").strip()
            or (final_state.get("analysis_summary") or "").strip()
            or "I couldn't generate an analysis right now."
        )

        assistant_msg = self._save_chat_message(
            thread_id=thread.id,
            role=TherapistChatRole.ASSISTANT.value,
            content=assistant_text,
        )

        run.status = AnalysisRunStatus.COMPLETED.value
        run.draft_analysis = (final_state.get("draft_analysis") or "").strip() or run.draft_analysis
        run.analysis_summary = (
            (final_state.get("final_analysis") or "").strip()
            or (final_state.get("analysis_summary") or "").strip()
            or run.analysis_summary
        )

        self.db.commit()
        self.db.refresh(run)

        return TherapistChatSendResponse(
            thread_id=thread.id,
            user_message=user_msg,
            assistant_message=assistant_msg,
            needs_clarification=False,
            clarification=None,
            analysis_run=run,
        )

    def submit_clarification_answer(
        self,
        *,
        therapist_id: int,
        analysis_run_id: int,
        answer: str,
    ) -> ResumePatientAnalysisResponse:
        """
        Therapist answers the AI clarification question through a separate form.

        Flow:
        1. Validate run ownership
        2. Load pending clarification
        3. Save therapist answer
        4. Reload patient context + KB
        5. Resume graph
        6. Save assistant response into the same chat thread
        7. Mark run completed
        """
        clean_answer = answer.strip()
        if not clean_answer:
            raise ValueError("Answer cannot be empty.")

        run = self._get_analysis_run_or_raise(
            therapist_id=therapist_id,
            analysis_run_id=analysis_run_id,
        )

        clarification = self._get_pending_clarification_or_raise(run.id)

        clarification.answer = clean_answer
        clarification.status = ClarificationStatus.ANSWERED.value
        clarification.answered_at = datetime.utcnow()

        recent_chat_history: List[dict] = []
        if run.thread_id:
            recent_chat_history = self._get_recent_chat_history(run.thread_id)

        resume_state: NirbaanAITherapistState = {
            "therapist_id": run.therapist_id,
            "patient_id": run.patient_id,
            "thread_id": run.thread_id or 0,
            "analysis_run_id": run.id,
            "user_message": run.analysis_goal or "",
            "recent_chat_history": recent_chat_history,
            "analysis_goal": run.analysis_goal or "",
            "draft_analysis": run.draft_analysis or "",
            "analysis_summary": run.analysis_summary or "",
            "clarification_question": clarification.question,
            "clarification_answer": clean_answer,
            "needs_clarification": False,
            "latest_weekly_progress": None,
            "initial_fear_ladder": None,
            "obsession_compulsion_pairs": [],
            "patient_context_summary": "",
            "retrieval_query": "",
            "kb_chunks": [],
            "kb_context_summary": "",
            "final_analysis": "",
            "final_response": "",
            "used_sources": [],
            "error_message": "",
            "status": "running",
        }

        # Reload patient context and KB before resuming
        patient_context_updates = load_patient_context_node(resume_state, self.db)
        resume_state.update(patient_context_updates)

        kb_updates = retrieve_kb_node(resume_state)
        resume_state.update(kb_updates)

        final_state = invoke_resume_therapist_analysis_graph(resume_state)

        final_analysis = (
            (final_state.get("final_analysis") or "").strip()
            or (final_state.get("analysis_summary") or "").strip()
            or "I couldn't finalize the analysis."
        )

        if run.thread_id:
            self._save_chat_message(
                thread_id=run.thread_id,
                role=TherapistChatRole.ASSISTANT.value,
                content=final_analysis,
            )

        run.status = AnalysisRunStatus.COMPLETED.value
        run.draft_analysis = (final_state.get("draft_analysis") or "").strip() or run.draft_analysis
        run.analysis_summary = final_analysis

        self.db.commit()
        self.db.refresh(run)
        self.db.refresh(clarification)

        return ResumePatientAnalysisResponse(
            run=run,
            needs_clarification=False,
            clarification=clarification,
            analysis_summary=final_analysis,
        )

    def get_thread(
        self,
        *,
        therapist_id: int,
        thread_id: int,
    ) -> TherapistAIChatThread:
        thread = (
            self.db.query(TherapistAIChatThread)
            .filter(
                TherapistAIChatThread.id == thread_id,
                TherapistAIChatThread.therapist_id == therapist_id,
            )
            .first()
        )
        if not thread:
            raise ValueError("Chat thread not found.")
        return thread

    def get_thread_messages(
        self,
        *,
        therapist_id: int,
        thread_id: int,
    ) -> List[TherapistAIChatMessage]:
        self.get_thread(therapist_id=therapist_id, thread_id=thread_id)

        return (
            self.db.query(TherapistAIChatMessage)
            .filter(TherapistAIChatMessage.thread_id == thread_id)
            .order_by(
                TherapistAIChatMessage.created_at.asc(),
                TherapistAIChatMessage.id.asc(),
            )
            .all()
        )

    def list_threads(
        self,
        *,
        therapist_id: int,
    ) -> List[TherapistAIChatThread]:
        return (
            self.db.query(TherapistAIChatThread)
            .filter(TherapistAIChatThread.therapist_id == therapist_id)
            .order_by(
                TherapistAIChatThread.updated_at.desc(),
                TherapistAIChatThread.id.desc(),
            )
            .all()
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_therapist_or_raise(self, therapist_id: int) -> Therapist:
        therapist = self.db.query(Therapist).filter(Therapist.id == therapist_id).first()
        if not therapist:
            raise ValueError("Therapist not found.")
        return therapist

    def _get_patient_or_raise(self, patient_id: int) -> Patient:
        patient = self.db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            raise ValueError("Patient not found.")
        return patient

    def _get_or_create_thread(
        self,
        *,
        therapist_id: int,
        patient_id: Optional[int],
        thread_id: Optional[int],
    ) -> TherapistAIChatThread:
        if thread_id is not None:
            thread = (
                self.db.query(TherapistAIChatThread)
                .filter(
                    TherapistAIChatThread.id == thread_id,
                    TherapistAIChatThread.therapist_id == therapist_id,
                )
                .first()
            )
            if not thread:
                raise ValueError("Chat thread not found.")

            if patient_id is not None and thread.patient_id is None:
                thread.patient_id = patient_id
                self.db.commit()
                self.db.refresh(thread)

            return thread

        thread = TherapistAIChatThread(
            therapist_id=therapist_id,
            patient_id=patient_id,
            title=None,
        )
        self.db.add(thread)
        self.db.commit()
        self.db.refresh(thread)
        return thread

    def _save_chat_message(
        self,
        *,
        thread_id: int,
        role: str,
        content: str,
    ) -> TherapistAIChatMessage:
        msg = TherapistAIChatMessage(
            thread_id=thread_id,
            role=role,
            content=content,
        )
        self.db.add(msg)

        thread = (
            self.db.query(TherapistAIChatThread)
            .filter(TherapistAIChatThread.id == thread_id)
            .first()
        )
        if thread:
            thread.title = thread.title

        self.db.commit()
        self.db.refresh(msg)
        return msg

    def _get_recent_chat_history(self, thread_id: int) -> list[dict]:
        messages = (
            self.db.query(TherapistAIChatMessage)
            .filter(TherapistAIChatMessage.thread_id == thread_id)
            .order_by(
                TherapistAIChatMessage.created_at.desc(),
                TherapistAIChatMessage.id.desc(),
            )
            .limit(self.RECENT_HISTORY_LIMIT)
            .all()
        )

        messages = list(reversed(messages))

        return [
            {
                "role": m.role,
                "content": m.content,
            }
            for m in messages
        ]

    def _create_analysis_run(
        self,
        *,
        therapist_id: int,
        patient_id: int,
        thread_id: int,
        analysis_goal: str,
    ) -> PatientAnalysisRun:
        run = PatientAnalysisRun(
            therapist_id=therapist_id,
            patient_id=patient_id,
            thread_id=thread_id,
            status=AnalysisRunStatus.RUNNING.value,
            analysis_goal=analysis_goal,
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def _create_clarification(
        self,
        *,
        analysis_run_id: int,
        question: str,
    ) -> PatientAnalysisClarification:
        clarification = PatientAnalysisClarification(
            analysis_run_id=analysis_run_id,
            question=question,
            status=ClarificationStatus.PENDING.value,
        )
        self.db.add(clarification)
        self.db.commit()
        self.db.refresh(clarification)
        return clarification

    def _get_analysis_run_or_raise(
        self,
        *,
        therapist_id: int,
        analysis_run_id: int,
    ) -> PatientAnalysisRun:
        run = (
            self.db.query(PatientAnalysisRun)
            .filter(
                PatientAnalysisRun.id == analysis_run_id,
                PatientAnalysisRun.therapist_id == therapist_id,
            )
            .first()
        )
        if not run:
            raise ValueError("Analysis run not found.")
        return run

    def _get_pending_clarification_or_raise(
        self,
        analysis_run_id: int,
    ) -> PatientAnalysisClarification:
        clarification = (
            self.db.query(PatientAnalysisClarification)
            .filter(
                PatientAnalysisClarification.analysis_run_id == analysis_run_id,
                PatientAnalysisClarification.status == ClarificationStatus.PENDING.value,
            )
            .order_by(
                PatientAnalysisClarification.created_at.desc(),
                PatientAnalysisClarification.id.desc(),
            )
            .first()
        )
        if not clarification:
            raise ValueError("Pending clarification not found.")
        return clarification