from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List
from datetime import datetime

from app.database.deps import get_db
from app.schemas.patient import (
    PatientRegister, PatientLogin, PatientResponse, PatientUpdate,
    InviteCreate, InviteCreateResponse, InviteValidateResponse, InviteRegisterRequest,
    InviteSendEmailRequest,
)
from app.schemas.auth import Token
from app.patients.models import Patient
from app.patients.invitation_model import PatientInvitation
from app.therapists.models import Therapist
from app.auth.utils import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_therapist,
    get_current_patient
)
from app.core.config import settings
from app.core.email_utils import send_invite_email as _send_invite_email

router = APIRouter(prefix="/patients", tags=["Patients"])

@router.post("/register", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def register_patient(
    patient_data: PatientRegister,
    db: Session = Depends(get_db),
    current_therapist: Therapist = Depends(get_current_therapist)
):
    """
    Register a new patient (therapist only)

    Required fields:
    - name: Patient's full name
    - email: Valid email address (must be unique)
    - password: Password (minimum 8 characters)
    - conditions: Patient's conditions (e.g., "OCD, ADHD")
    - conditions_description: Detailed description of conditions
    - address: Physical address
    """
    # Check if email already exists
    existing_patient = db.query(Patient).filter(
        Patient.email == patient_data.email
    ).first()
    if existing_patient:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Hash the password
    hashed_password = get_password_hash(patient_data.password)

    # Create new patient
    new_patient = Patient(
        name=patient_data.name,
        email=patient_data.email,
        hashed_password=hashed_password,
        conditions=patient_data.conditions,
        conditions_description=patient_data.conditions_description,
        address=patient_data.address,
        therapist_id=current_therapist.id
    )

    try:
        db.add(new_patient)
        db.commit()
        db.refresh(new_patient)
        return new_patient
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed. Please check your information."
        )

@router.get("/", response_model=List[PatientResponse])
async def get_patients(
    db: Session = Depends(get_db),
    current_therapist: Therapist = Depends(get_current_therapist)
):
    """
    Get all patients for the current therapist
    """
    patients = db.query(Patient).filter(
        Patient.therapist_id == current_therapist.id
    ).all()
    return patients

@router.get("/me", response_model=PatientResponse)
async def get_current_patient_info(
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_patient)
):
    """
    Get current patient information (for authenticated patients)
    """
    return current_patient

@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_therapist: Therapist = Depends(get_current_therapist)
):
    """
    Get a specific patient by ID (must belong to current therapist)
    """
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.therapist_id == current_therapist.id
    ).first()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )

    return patient

@router.put("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: int,
    patient_data: PatientUpdate,
    db: Session = Depends(get_db),
    current_therapist: Therapist = Depends(get_current_therapist)
):
    """
    Update a patient's information (therapist only)
    """
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.therapist_id == current_therapist.id
    ).first()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )

    # Update only provided fields
    update_data = patient_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(patient, field, value)

    try:
        db.commit()
        db.refresh(patient)
        return patient
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Update failed. Email may already be in use."
        )

@router.post("/login", response_model=Token)
async def login_patient(
    login_data: PatientLogin,
    db: Session = Depends(get_db)
):
    """
    Patient login endpoint
    """
    # First check if patient exists
    patient = db.query(Patient).filter(
        Patient.email == login_data.email
    ).first()

    if not patient:
        print(f"[LOGIN FAILED] Patient not found with email: {login_data.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Now verify password
    password_valid = verify_password(login_data.password, patient.hashed_password)
    print(f"[LOGIN ATTEMPT] Email: {login_data.email}, Patient: {patient.name}, Password Valid: {password_valid}")

    if not password_valid:
        print(f"[LOGIN FAILED] Invalid password for patient: {patient.name} ({patient.email})")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token = create_access_token(data={"sub": patient.email, "id": patient.id, "role": "patient"})
    print(f"[LOGIN SUCCESS] Patient: {patient.name} ({patient.email})")

    return {"access_token": access_token, "token_type": "bearer"}


# ── Invitation endpoints ──────────────────────────────────────────────────────

@router.post("/invite", response_model=InviteCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_patient_invitation(
    body: InviteCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_therapist: Therapist = Depends(get_current_therapist),
):
    """
    Therapist generates a one-time invitation link for a patient.
    Optionally locks the link to a specific email address.
    The link expires in 7 days.
    """
    invitation = PatientInvitation(
        therapist_id=current_therapist.id,
        invited_email=body.invited_email,
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)

    base_url = str(request.base_url).rstrip("/")
    invite_url = f"{base_url}/invite/{invitation.token}"

    return InviteCreateResponse(
        token=invitation.token,
        invite_url=invite_url,
        expires_at=invitation.expires_at,
        invited_email=invitation.invited_email,
    )


@router.get("/invite/{token}", response_model=InviteValidateResponse)
async def validate_invitation(
    token: str,
    db: Session = Depends(get_db),
):
    """
    Public endpoint. Validates an invitation token and returns the therapist name.
    Used by the frontend to pre-fill / confirm the invite page.
    """
    invitation = db.query(PatientInvitation).filter(
        PatientInvitation.token == token
    ).first()

    if not invitation or invitation.status != "pending" or invitation.expires_at < datetime.utcnow():
        return InviteValidateResponse(valid=False, therapist_name="", invited_email=None)

    therapist = db.get(Therapist, invitation.therapist_id)
    return InviteValidateResponse(
        valid=True,
        therapist_name=therapist.name if therapist else "",
        invited_email=invitation.invited_email,
    )


@router.post("/invite/{token}/register", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def register_via_invitation(
    token: str,
    patient_data: InviteRegisterRequest,
    db: Session = Depends(get_db),
):
    """
    Public endpoint. Patient self-registers using a valid invitation token.
    The new account is automatically linked to the inviting therapist.
    """
    invitation = db.query(PatientInvitation).filter(
        PatientInvitation.token == token
    ).first()

    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid invitation link.")

    if invitation.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This invitation has already been used.")

    if invitation.expires_at < datetime.utcnow():
        invitation.status = "expired"
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This invitation has expired.")

    if invitation.invited_email and invitation.invited_email.lower() != patient_data.email.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invitation was sent to a different email address.",
        )

    existing = db.query(Patient).filter(Patient.email == patient_data.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered.")

    new_patient = Patient(
        name=patient_data.name,
        email=patient_data.email,
        hashed_password=get_password_hash(patient_data.password),
        conditions=patient_data.conditions,
        conditions_description=patient_data.conditions_description,
        address=patient_data.address,
        therapist_id=invitation.therapist_id,
    )

    try:
        db.add(new_patient)
        invitation.status = "used"
        db.commit()
        db.refresh(new_patient)
        return new_patient
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Registration failed.")


@router.post("/invite/{token}/send-email", status_code=status.HTTP_200_OK)
async def send_invite_email_endpoint(
    token: str,
    body: InviteSendEmailRequest,
    db: Session = Depends(get_db),
    current_therapist: Therapist = Depends(get_current_therapist),
):
    """
    Therapist sends the invitation link to a patient's email address.
    The token must be pending and not expired, and must belong to this therapist.
    """
    invitation = db.query(PatientInvitation).filter(
        PatientInvitation.token == token,
        PatientInvitation.therapist_id == current_therapist.id,
    ).first()

    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found.")

    if invitation.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This invitation has already been used or expired.")

    if invitation.expires_at < datetime.utcnow():
        invitation.status = "expired"
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This invitation has expired.")

    invite_url = f"{settings.FRONTEND_URL}/invite/{token}"

    try:
        _send_invite_email(
            recipient_email=body.recipient_email,
            therapist_name=current_therapist.name,
            invite_url=invite_url,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))

    return {"message": f"Invitation email sent to {body.recipient_email}."}

