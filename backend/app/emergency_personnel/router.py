from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List

from app.database.deps import get_db
from app.schemas.emergency_personnel import (
    EmergencyPersonnelRegister,
    EmergencyPersonnelLogin,
    EmergencyPersonnelResponse,
    EmergencyPersonnelUpdate
)
from app.schemas.auth import Token
from app.emergency_personnel.models import EmergencyPersonnel
from app.therapists.models import Therapist
from app.auth.utils import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_therapist,
    get_current_emergency_personnel
)

router = APIRouter(prefix="/emergency-personnel", tags=["Emergency Personnel"])

@router.post("/register", response_model=EmergencyPersonnelResponse, status_code=status.HTTP_201_CREATED)
async def register_emergency_personnel(
    personnel_data: EmergencyPersonnelRegister,
    db: Session = Depends(get_db),
    current_therapist: Therapist = Depends(get_current_therapist)
):
    """
    Register a new emergency personnel (therapist only)
    
    Required fields:
    - name: Full name
    - email: Valid email address (must be unique)
    - password: Password (minimum 8 characters)
    - education: Educational background
    - experience: Professional experience
    - details: Additional details
    - address: Physical address
    """
    # Check if email already exists
    existing_personnel = db.query(EmergencyPersonnel).filter(
        EmergencyPersonnel.email == personnel_data.email
    ).first()
    if existing_personnel:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash the password
    hashed_password = get_password_hash(personnel_data.password)
    
    # Create new emergency personnel
    new_personnel = EmergencyPersonnel(
        name=personnel_data.name,
        email=personnel_data.email,
        hashed_password=hashed_password,
        education=personnel_data.education,
        experience=personnel_data.experience,
        details=personnel_data.details,
        address=personnel_data.address,
        therapist_id=current_therapist.id
    )
    
    try:
        db.add(new_personnel)
        db.commit()
        db.refresh(new_personnel)
        return new_personnel
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed. Please check your information."
        )

@router.get("/", response_model=List[EmergencyPersonnelResponse])
async def get_emergency_personnel_list(
    db: Session = Depends(get_db),
    current_therapist: Therapist = Depends(get_current_therapist)
):
    """
    Get all emergency personnel for the current therapist
    """
    personnel_list = db.query(EmergencyPersonnel).filter(
        EmergencyPersonnel.therapist_id == current_therapist.id
    ).all()
    return personnel_list

@router.get("/{personnel_id}", response_model=EmergencyPersonnelResponse)
async def get_emergency_personnel(
    personnel_id: int,
    db: Session = Depends(get_db),
    current_therapist: Therapist = Depends(get_current_therapist)
):
    """
    Get a specific emergency personnel by ID (must belong to current therapist)
    """
    personnel = db.query(EmergencyPersonnel).filter(
        EmergencyPersonnel.id == personnel_id,
        EmergencyPersonnel.therapist_id == current_therapist.id
    ).first()
    
    if not personnel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergency personnel not found"
        )
    
    return personnel

@router.put("/{personnel_id}", response_model=EmergencyPersonnelResponse)
async def update_emergency_personnel(
    personnel_id: int,
    personnel_data: EmergencyPersonnelUpdate,
    db: Session = Depends(get_db),
    current_therapist: Therapist = Depends(get_current_therapist)
):
    """
    Update emergency personnel information (therapist only)
    """
    personnel = db.query(EmergencyPersonnel).filter(
        EmergencyPersonnel.id == personnel_id,
        EmergencyPersonnel.therapist_id == current_therapist.id
    ).first()
    
    if not personnel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergency personnel not found"
        )
    
    # Update only provided fields
    update_data = personnel_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(personnel, field, value)
    
    try:
        db.commit()
        db.refresh(personnel)
        return personnel
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Update failed. Email may already be in use."
        )

@router.post("/login", response_model=Token)
async def login_emergency_personnel(
    login_data: EmergencyPersonnelLogin,
    db: Session = Depends(get_db)
):
    """
    Emergency personnel login endpoint
    """
    # Check if personnel exists
    personnel = db.query(EmergencyPersonnel).filter(
        EmergencyPersonnel.email == login_data.email
    ).first()
    
    if not personnel:
        print(f"[LOGIN FAILED] Emergency personnel not found with email: {login_data.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify password
    password_valid = verify_password(login_data.password, personnel.hashed_password)
    print(f"[LOGIN ATTEMPT] Email: {login_data.email}, Personnel: {personnel.name}, Password Valid: {password_valid}")
    
    if not password_valid:
        print(f"[LOGIN FAILED] Invalid password for personnel: {personnel.name} ({personnel.email})")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": personnel.email, "id": personnel.id, "role": "emergency_personnel"})
    print(f"[LOGIN SUCCESS] Emergency Personnel: {personnel.name} ({personnel.email})")
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=EmergencyPersonnelResponse)
async def get_current_emergency_personnel_info(
    db: Session = Depends(get_db),
    current_personnel: EmergencyPersonnel = Depends(get_current_emergency_personnel)
):
    """
    Get current emergency personnel information (for authenticated personnel)
    """
    return current_personnel
