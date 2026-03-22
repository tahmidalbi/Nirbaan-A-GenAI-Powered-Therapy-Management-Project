from __future__ import annotations

from sqlalchemy.orm import Session

from app.erp.models import ERPItem
from .models import (
    ImaginalScriptRun,
    ImaginalScriptVersion,
    ApprovedImaginalScript,
)


def get_erp_item_or_raise(db: Session, erp_item_id: int) -> ERPItem:
    item = db.query(ERPItem).filter(ERPItem.id == erp_item_id).first()
    if not item:
        raise ValueError(f"ERPItem {erp_item_id} not found")
    return item


def stringify_compulsions(compulsions) -> str:
    if isinstance(compulsions, list):
        return "; ".join([str(x).strip() for x in compulsions if str(x).strip()])
    return str(compulsions or "").strip()


def create_run(
    db: Session,
    *,
    thread_id: str,
    patient_id: int,
    therapist_id: int,
    erp_item_id: int,
    obsession: str,
    compulsion: str,
    feared_consequence: str,
    script_intensity: str,
    subtype: str | None,
) -> ImaginalScriptRun:
    run = ImaginalScriptRun(
        thread_id=thread_id,
        patient_id=patient_id,
        therapist_id=therapist_id,
        erp_item_id=erp_item_id,
        obsession=obsession,
        compulsion=compulsion,
        feared_consequence=feared_consequence,
        script_intensity=script_intensity,
        exposure_type="imaginal",
        subtype=subtype,
        status="pending_review",
        revision_count=1,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def get_run_by_thread_id(db: Session, thread_id: str) -> ImaginalScriptRun | None:
    return db.query(ImaginalScriptRun).filter(ImaginalScriptRun.thread_id == thread_id).first()


def save_version(
    db: Session,
    *,
    run_id: int,
    version_no: int,
    prompt_text: str,
    generated_script: str,
    therapist_feedback: str | None = None,
    approved: bool | None = None,
) -> ImaginalScriptVersion:
    version = ImaginalScriptVersion(
        run_id=run_id,
        version_no=version_no,
        prompt_text=prompt_text,
        generated_script=generated_script,
        therapist_feedback=therapist_feedback,
        approved=approved,
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


def update_run_latest(
    db: Session,
    *,
    run: ImaginalScriptRun,
    latest_prompt_text: str,
    latest_script_text: str,
    revision_count: int,
    status: str,
) -> ImaginalScriptRun:
    run.latest_prompt_text = latest_prompt_text
    run.latest_script_text = latest_script_text
    run.revision_count = revision_count
    run.status = status
    db.commit()
    db.refresh(run)
    return run


def approve_run(
    db: Session,
    *,
    run: ImaginalScriptRun,
    approved_script: str,
    audio_url: str | None,
    audio_key: str | None,
) -> ApprovedImaginalScript:
    approved = ApprovedImaginalScript(
        patient_id=run.patient_id,
        therapist_id=run.therapist_id,
        erp_item_id=run.erp_item_id,
        run_id=run.id,
        subtype=run.subtype,
        approved_script=approved_script,
        audio_path=audio_url,
        audio_key=audio_key,
        metadata_json={
            "obsession": run.obsession,
            "compulsion": run.compulsion,
            "feared_consequence": run.feared_consequence,
            "script_intensity": run.script_intensity,
            "exposure_type": run.exposure_type,
            "subtype": run.subtype,
        },
    )
    db.add(approved)
    db.commit()
    db.refresh(approved)

    run.approved_script_text = approved_script
    run.approved_audio_path = audio_url
    run.approved_audio_key = audio_key
    run.approved_script_id = approved.id
    run.status = "approved"
    db.commit()
    db.refresh(run)
    return approved


def list_approved_for_patient(db: Session, patient_id: int):
    return (
        db.query(ApprovedImaginalScript)
        .filter(ApprovedImaginalScript.patient_id == patient_id)
        .order_by(ApprovedImaginalScript.created_at.desc())
        .all()
    )


def get_approved_by_id(db: Session, script_id: int) -> ApprovedImaginalScript | None:
    return db.query(ApprovedImaginalScript).filter(ApprovedImaginalScript.id == script_id).first()


def list_approved_for_erp_item(db: Session, erp_item_id: int):
    return (
        db.query(ApprovedImaginalScript)
        .filter(ApprovedImaginalScript.erp_item_id == erp_item_id)
        .order_by(ApprovedImaginalScript.created_at.desc())
        .all()
    )