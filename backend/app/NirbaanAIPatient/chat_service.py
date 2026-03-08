from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from app.NirbaanAIPatient.models import (
    ChatRole,
    PsychoeducationChatMessage,
    PsychoeducationChatThread,
)
from app.NirbaanAIPatient.schemas import PsychoeducationChatSendResponse
from app.NirbaanAIPatient.PsychoeducationChatbot.state import PsychoeducationState
from app.patients.models import Patient

# Adjust this import to your exact graph function name/path later
from app.NirbaanAIPatient.PsychoeducationChatbot.graph import invoke_psychoeducation_graph


class PsychoeducationChatService:
    RECENT_HISTORY_LIMIT = 4  # last 4 messages

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def send_message(
        self,
        *,
        patient_id: int,
        message: str,
        thread_id: Optional[int] = None,
    ) -> PsychoeducationChatSendResponse:
        """
        Main entrypoint for psychoeducation chat.

        Flow:
        1. Validate patient
        2. Create or validate thread
        3. Save user message
        4. Run graph
        5. Save assistant message
        6. Return structured response
        """
        patient = self._get_patient_or_raise(patient_id)

        clean_message = message.strip()
        if not clean_message:
            raise ValueError("Message cannot be empty.")

        thread = self._get_or_create_thread(
            patient_id=patient.id,
            thread_id=thread_id,
        )

        user_msg = self._save_message(
            thread_id=thread.id,
            role=ChatRole.USER.value,
            content=clean_message,
        )

        recent_chat_history = self._get_recent_chat_history(thread.id)

        initial_state: PsychoeducationState = {
            "patient_id": patient.id,
            "therapist_id": patient.therapist_id,
            "thread_id": thread.id,
            "user_message": clean_message,
            "recent_chat_history": recent_chat_history,
            "retry_count": 0,
            "max_retries": 2,
            "web_used": False,
            "db_obsession_compulsion_pairs": [],
            "db_latest_weekly_progress": None,
            "selected_obsession_compulsion_pairs": [],
            "selected_progress_snippets": [],
            "selected_db_context_summary": "",
            "retrieval_query": clean_message,
            "original_retrieval_query": clean_message,
            "refined_query_history": [],
            "kb_chunks": [],
            "kb_context_summary": "",
            "retrieval_sufficient": False,
            "insufficiency_reason": "",
            "missing_concept": "",
            "web_results": [],
            "web_context_summary": "",
            "final_grounding_summary": "",
            "final_response": "",
            "used_sources": [],
            "error_message": "",
        }

        final_state = invoke_psychoeducation_graph(initial_state)

        assistant_text = (
            final_state.get("final_response", "").strip()
            or "I'm sorry, I couldn't generate a response right now."
        )

        assistant_msg = self._save_message(
            thread_id=thread.id,
            role=ChatRole.ASSISTANT.value,
            content=assistant_text,
        )

        return PsychoeducationChatSendResponse(
            thread_id=thread.id,
            user_message=user_msg,
            assistant_message=assistant_msg,
            used_web_fallback=bool(final_state.get("web_used", False)),
        )

    def get_thread(self, *, patient_id: int, thread_id: int) -> PsychoeducationChatThread:
        """
        Returns the thread after validating ownership.
        """
        thread = (
            self.db.query(PsychoeducationChatThread)
            .filter(
                PsychoeducationChatThread.id == thread_id,
                PsychoeducationChatThread.patient_id == patient_id,
            )
            .first()
        )
        if not thread:
            raise ValueError("Chat thread not found.")
        return thread

    def get_thread_messages(
        self,
        *,
        patient_id: int,
        thread_id: int,
    ) -> List[PsychoeducationChatMessage]:
        """
        Returns all messages for a thread in chronological order.
        """
        self.get_thread(patient_id=patient_id, thread_id=thread_id)

        return (
            self.db.query(PsychoeducationChatMessage)
            .filter(PsychoeducationChatMessage.thread_id == thread_id)
            .order_by(PsychoeducationChatMessage.created_at.asc(), PsychoeducationChatMessage.id.asc())
            .all()
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_patient_or_raise(self, patient_id: int) -> Patient:
        patient = self.db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            raise ValueError("Patient not found.")
        return patient

    def _get_or_create_thread(
        self,
        *,
        patient_id: int,
        thread_id: Optional[int],
    ) -> PsychoeducationChatThread:
        """
        If thread_id is provided, validates ownership and returns it.
        Otherwise creates a new thread.
        """
        if thread_id is not None:
            thread = (
                self.db.query(PsychoeducationChatThread)
                .filter(
                    PsychoeducationChatThread.id == thread_id,
                    PsychoeducationChatThread.patient_id == patient_id,
                )
                .first()
            )
            if not thread:
                raise ValueError("Chat thread not found.")
            return thread

        thread = PsychoeducationChatThread(
            patient_id=patient_id,
            title=None,
        )
        self.db.add(thread)
        self.db.commit()
        self.db.refresh(thread)
        return thread

    def _save_message(
        self,
        *,
        thread_id: int,
        role: str,
        content: str,
    ) -> PsychoeducationChatMessage:
        """
        Persists one message and bumps thread.updated_at automatically.
        """
        msg = PsychoeducationChatMessage(
            thread_id=thread_id,
            role=role,
            content=content,
        )
        self.db.add(msg)

        thread = (
            self.db.query(PsychoeducationChatThread)
            .filter(PsychoeducationChatThread.id == thread_id)
            .first()
        )
        if thread:
            # Touch thread so updated_at changes on commit
            thread.title = thread.title

        self.db.commit()
        self.db.refresh(msg)
        return msg

    def _get_recent_chat_history(self, thread_id: int) -> list[dict]:
        """
        Loads the most recent messages and returns them in chronological order
        for graph input.
        """
        messages = (
            self.db.query(PsychoeducationChatMessage)
            .filter(PsychoeducationChatMessage.thread_id == thread_id)
            .order_by(PsychoeducationChatMessage.created_at.desc(), PsychoeducationChatMessage.id.desc())
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