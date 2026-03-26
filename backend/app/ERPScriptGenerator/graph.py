from __future__ import annotations

import os
from typing import Literal
from uuid import uuid4

from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.postgres import PostgresSaver

from app.database.session import SessionLocal

from .state import ImaginalGraphState
from .repository import (
    get_erp_item_or_raise,
    stringify_compulsions,
    create_run,
    get_run_by_thread_id,
    save_version,
    update_run_latest,
    approve_run,
)
from .gemini_builder import build_initial_prompt, build_revised_prompt
from .ollama_client import generate_script_with_ollama
from .piper_tts import synthesize_with_piper
from .r2_storage import upload_file_to_r2, build_audio_object_key
from .config import settings


def load_case_context(state: ImaginalGraphState) -> ImaginalGraphState:
    db = SessionLocal()
    try:
        erp_item = get_erp_item_or_raise(db, state["erp_item_id"])
        obsession = erp_item.obsession
        compulsion = stringify_compulsions(erp_item.compulsions)

        thread_id = state["thread_id"]
        run = get_run_by_thread_id(db, thread_id)
        if not run:
            run = create_run(
                db,
                thread_id=thread_id,
                patient_id=state["patient_id"],
                therapist_id=state["therapist_id"],
                erp_item_id=state["erp_item_id"],
                obsession=obsession,
                compulsion=compulsion,
                feared_consequence=state["feared_consequence"],
                script_intensity=state["script_intensity"],
                subtype=state.get("subtype"),
            )

        return {
            "run_id": run.id,
            "obsession": obsession,
            "compulsion": compulsion,
            "exposure_type": "imaginal",
            "status": "building_prompt",
            "version_no": run.revision_count,
        }
    finally:
        db.close()


def build_prompt_node(state: ImaginalGraphState) -> ImaginalGraphState:
    if state.get("therapist_feedback"):
        prompt_text = build_revised_prompt(
            obsession=state["obsession"],
            compulsion=state["compulsion"],
            feared_consequence=state["feared_consequence"],
            script_intensity=state["script_intensity"],
            subtype=state.get("subtype"),
            therapist_feedback=state["therapist_feedback"],
            previous_prompt=state.get("prompt_text", ""),
            previous_script=state.get("generated_script", ""),
        )
    else:
        prompt_text = build_initial_prompt(
            obsession=state["obsession"],
            compulsion=state["compulsion"],
            feared_consequence=state["feared_consequence"],
            script_intensity=state["script_intensity"],
            subtype=state.get("subtype"),
        )

    return {
        "prompt_text": prompt_text,
        "status": "generating",
    }


def generate_script_node(state: ImaginalGraphState) -> ImaginalGraphState:
    script = generate_script_with_ollama(state["prompt_text"])

    db = SessionLocal()
    try:
        run = get_run_by_thread_id(db, state["thread_id"])
        version_no = run.revision_count if run else state.get("version_no", 1)
        save_version(
            db,
            run_id=run.id,
            version_no=version_no,
            prompt_text=state["prompt_text"],
            generated_script=script,
            therapist_feedback=state.get("therapist_feedback"),
            approved=None,
        )
        update_run_latest(
            db,
            run=run,
            latest_prompt_text=state["prompt_text"],
            latest_script_text=script,
            revision_count=version_no,
            status="pending_review",
        )
    finally:
        db.close()

    return {
        "generated_script": script,
        "status": "pending_review",
    }


def therapist_review_node(
    state: ImaginalGraphState,
) -> Command[Literal["finalize_approved_node", "prepare_revision_node"]]:
    decision = interrupt({
        "action": "review_script",
        "thread_id": state["thread_id"],
        "run_id": state["run_id"],
        "version_no": state["version_no"],
        "obsession": state["obsession"],
        "compulsion": state["compulsion"],
        "feared_consequence": state["feared_consequence"],
        "script_intensity": state["script_intensity"],
        "exposure_type": state["exposure_type"],
        "subtype": state.get("subtype"),
        "generated_script": state["generated_script"],
        "message": "Therapist must approve or reject this imaginal exposure script.",
    })

    approved = bool(decision.get("approved", False))
    feedback = decision.get("feedback")

    if approved:
        return Command(
            update={
                "approved": True,
                "therapist_feedback": None,
                "status": "approved_pending_audio",
            },
            goto="finalize_approved_node",
        )

    return Command(
        update={
            "approved": False,
            "therapist_feedback": feedback or "",
            "status": "revising",
        },
        goto="prepare_revision_node",
    )


def prepare_revision_node(state: ImaginalGraphState) -> ImaginalGraphState:
    db = SessionLocal()
    try:
        run = get_run_by_thread_id(db, state["thread_id"])
        next_version = (run.revision_count + 1) if run else (state.get("version_no", 1) + 1)
        if run:
            run.revision_count = next_version
            run.status = "revising"
            db.commit()
    finally:
        db.close()

    return {
        "version_no": next_version,
        "status": "building_prompt",
    }


def finalize_approved_node(state: ImaginalGraphState) -> ImaginalGraphState:
    local_audio_path = synthesize_with_piper(state["generated_script"])

    audio_url = local_audio_path  # default: local file path
    audio_key = None

    if settings.has_r2_config:
        object_key = build_audio_object_key(
            patient_id=state["patient_id"],
            run_id=state["run_id"],
            extension=".wav",
        )
        uploaded = upload_file_to_r2(
            local_path=local_audio_path,
            object_key=object_key,
            content_type="audio/wav",
        )
        audio_url = uploaded["url"]
        audio_key = uploaded["object_key"]

        try:
            if os.path.exists(local_audio_path):
                os.remove(local_audio_path)
        except Exception:
            pass

    db = SessionLocal()
    try:
        run = get_run_by_thread_id(db, state["thread_id"])
        approved = approve_run(
            db,
            run=run,
            approved_script=state["generated_script"],
            audio_url=audio_url,
            audio_key=audio_key,
        )
        latest_version = run.versions[-1]
        latest_version.approved = True
        db.commit()
        # Read the id while the session is still open — accessing it after
        # db.close() raises DetachedInstanceError because SQLAlchemy would
        # try to lazy-reload the expired attribute.
        approved_script_id = approved.id
    finally:
        db.close()

    return {
        "audio_path": audio_url,
        "approved_script_id": approved_script_id,
        "status": "done",
    }


def build_graph():
    builder = StateGraph(ImaginalGraphState)

    builder.add_node("load_case_context", load_case_context)
    builder.add_node("build_prompt_node", build_prompt_node)
    builder.add_node("generate_script_node", generate_script_node)
    builder.add_node("therapist_review_node", therapist_review_node)
    builder.add_node("prepare_revision_node", prepare_revision_node)
    builder.add_node("finalize_approved_node", finalize_approved_node)

    builder.add_edge(START, "load_case_context")
    builder.add_edge("load_case_context", "build_prompt_node")
    builder.add_edge("build_prompt_node", "generate_script_node")
    builder.add_edge("generate_script_node", "therapist_review_node")
    builder.add_edge("prepare_revision_node", "build_prompt_node")
    builder.add_edge("finalize_approved_node", END)

    return builder


def compile_graph():
    checkpointer_cm = PostgresSaver.from_conn_string(settings.checkpoint_db_url)
    checkpointer = checkpointer_cm.__enter__()
    checkpointer.setup()
    graph = build_graph().compile(checkpointer=checkpointer)
    return graph, checkpointer_cm