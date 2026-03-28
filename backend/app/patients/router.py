from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List

from app.database.deps import get_db
from app.schemas.patient import PatientRegister, PatientLogin, PatientResponse, PatientUpdate
from app.schemas.auth import Token
from app.patients.models import Patient
from app.therapists.models import Therapist
from app.auth.utils import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_therapist,
    get_current_patient
)

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
