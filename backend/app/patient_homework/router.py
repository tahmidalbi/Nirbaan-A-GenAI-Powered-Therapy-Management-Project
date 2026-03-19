from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.database.deps import get_db
from app.patient_homework.models import PatientHomework, HomeworkStatus
from app.patient_homework.schemas import (
    PatientHomeworkResponse,
    HomeworksByWeekResponse,
    SessionWithHomeworksResponse,
    EditHomeworksRequest,
    ApproveHomeworksRequest,
    HomeworkItemBase,
    MarkCompleteRequest,
    TranscriptItemResponse,
)
from app.therapy_sessions.models import TherapySession, TherapySessionAnalysis
from app.patients.models import Patient
from app.therapists.models import Therapist
from app.auth.utils import get_current_therapist, get_current_patient

router = APIRouter(prefix="/homeworks", tags=["Patient Homeworks"])


# ============ THERAPIST ENDPOINTS ============

@router.get("/therapist/active-sessions", response_model=List[SessionWithHomeworksResponse])
async def get_active_sessions_with_homeworks(
    db: Session = Depends(get_db),
    current_therapist: Therapist = Depends(get_current_therapist)
):
    """
    Get all completed sessions with their AI-generated homeworks for therapist review.
    """
    # Query sessions that belong to therapist's patients and have ended
    sessions = (
        db.query(TherapySession)
        .join(Patient, TherapySession.patient_id == Patient.id)
        .filter(
            Patient.therapist_id == current_therapist.id,
            TherapySession.ended_at.isnot(None)
        )
        .order_by(TherapySession.ended_at.desc())
        .all()
    )

    result = []
    for session in sessions:
        # Get patient info
        patient = db.query(Patient).filter(Patient.id == session.patient_id).first()
        patient_name = patient.name if patient else "Unknown"

        # Count approved homeworks for this session
        approved_count = db.query(PatientHomework).filter(
            PatientHomework.session_id == session.id
        ).count()

        # Get transcripts sorted by timestamp
        transcripts = sorted(session.transcripts, key=lambda t: t.timestamp)
        transcript_responses = [
            TranscriptItemResponse(
                id=t.id,
                speaker=t.speaker,
                text=t.text,
                timestamp=t.timestamp
            )
            for t in transcripts
        ]

        # Get AI-generated homeworks from analysis
        ai_homeworks = []
        analysis_summary = None
        if session.analysis:
            raw_homeworks = session.analysis.homeworks or []
            # Convert to HomeworkItemBase format
            ai_homeworks = [
                HomeworkItemBase(
                    task=hw.get("task", ""),
                    rationale=hw.get("rationale", ""),
                    frequency=hw.get("frequency", "")
                )
                for hw in raw_homeworks
            ]
            analysis_summary = session.analysis.summary

        result.append(SessionWithHomeworksResponse(
            session_id=session.id,
            patient_id=session.patient_id,
            patient_name=patient_name,
            started_at=session.started_at,
            ended_at=session.ended_at,
            transcript_count=len(session.transcripts),
            transcripts=transcript_responses,
            analysis_summary=analysis_summary,
            homeworks=ai_homeworks,
            approved_count=approved_count
        ))

    return result


@router.put("/sessions/{session_id}/analysis/homeworks")
async def update_session_homeworks(
    session_id: int,
    homework_data: EditHomeworksRequest,
    db: Session = Depends(get_db),
    current_therapist: Therapist = Depends(get_current_therapist)
):
    """
    Edit AI-generated homeworks in the session analysis before approval.
    """
    # Verify session belongs to therapist's patient
    session = (
        db.query(TherapySession)
        .join(Patient, TherapySession.patient_id == Patient.id)
        .filter(
            TherapySession.id == session_id,
            Patient.therapist_id == current_therapist.id
        )
        .first()
    )

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.analysis:
        raise HTTPException(status_code=404, detail="Session has no analysis")

    # Update homeworks in analysis JSON
    session.analysis.homeworks = [hw.model_dump() for hw in homework_data.homeworks]
    db.commit()

    return {"message": "Homeworks updated successfully", "homeworks": session.analysis.homeworks}


@router.post("/sessions/{session_id}/approve", response_model=List[PatientHomeworkResponse])
async def approve_session_homeworks(
    session_id: int,
    homework_data: ApproveHomeworksRequest,
    db: Session = Depends(get_db),
    current_therapist: Therapist = Depends(get_current_therapist)
):
    """
    Approve homeworks for a session - creates PatientHomework records.
    """
    # Verify session belongs to therapist's patient
    session = (
        db.query(TherapySession)
        .join(Patient, TherapySession.patient_id == Patient.id)
        .filter(
            TherapySession.id == session_id,
            Patient.therapist_id == current_therapist.id
        )
        .first()
    )

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Calculate week number based on patient's first session
    first_session = (
        db.query(TherapySession)
        .filter(TherapySession.patient_id == session.patient_id)
        .order_by(TherapySession.started_at)
        .first()
    )

    if first_session:
        days_diff = (session.started_at - first_session.started_at).days
        week_number = (days_diff // 7) + 1
    else:
        week_number = 1

    # Create PatientHomework records
    created_homeworks = []
    for hw in homework_data.homeworks:
        patient_homework = PatientHomework(
            patient_id=session.patient_id,
            session_id=session_id,
            task=hw.task,
            rationale=hw.rationale,
            frequency=hw.frequency,
            week_number=week_number,
            status=HomeworkStatus.active,
            approved_at=datetime.utcnow(),
            approved_by=current_therapist.id
        )
        db.add(patient_homework)
        created_homeworks.append(patient_homework)

    db.commit()

    for hw in created_homeworks:
        db.refresh(hw)

    return created_homeworks


# ============ PATIENT ENDPOINTS ============

@router.get("/me", response_model=List[HomeworksByWeekResponse])
async def get_my_homeworks(
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient)
):
    """
    Get current patient's homeworks organized by week.
    """
    homeworks = (
        db.query(PatientHomework)
        .filter(PatientHomework.patient_id == current_patient.id)
        .order_by(PatientHomework.week_number.desc(), PatientHomework.created_at)
        .all()
    )

    # Group by week
    weeks_dict = {}
    for hw in homeworks:
        if hw.week_number not in weeks_dict:
            weeks_dict[hw.week_number] = []
        weeks_dict[hw.week_number].append(hw)

    return [
        HomeworksByWeekResponse(week_number=week, homeworks=hws)
        for week, hws in sorted(weeks_dict.items(), reverse=True)
    ]


@router.post("/me/{homework_id}/complete", response_model=PatientHomeworkResponse)
async def mark_homework_complete(
    homework_id: int,
    complete_data: MarkCompleteRequest = None,
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient)
):
    """
    Mark a homework as completed with optional notes.
    """
    homework = db.query(PatientHomework).filter(
        PatientHomework.id == homework_id,
        PatientHomework.patient_id == current_patient.id
    ).first()

    if not homework:
        raise HTTPException(status_code=404, detail="Homework not found")

    homework.status = HomeworkStatus.completed
    homework.completed_at = datetime.utcnow()
    if complete_data and complete_data.notes:
        homework.patient_notes = complete_data.notes

    db.commit()
    db.refresh(homework)

    return homework
