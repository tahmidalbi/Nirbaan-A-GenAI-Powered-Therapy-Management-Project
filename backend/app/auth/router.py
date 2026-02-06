from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database.deps import get_db
from app.schemas.auth import TherapistRegister, TherapistLogin, Token, TherapistResponse
from app.therapists.models import Therapist
from app.auth.utils import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_therapist
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=TherapistResponse, status_code=status.HTTP_201_CREATED)
async def register_therapist(
    therapist_data: TherapistRegister,
    db: Session = Depends(get_db)
):
    """
    Register a new therapist
    
    Required fields:
    - name: Therapist's full name
    - email: Valid email address (must be unique)
    - password: Password (minimum 8 characters)
    - license_number: Professional license number (must be unique)
    - specialty: Area of specialization
    - address: Physical address
    """
    # Check if email already exists
    existing_therapist = db.query(Therapist).filter(
        Therapist.email == therapist_data.email
    ).first()
    if existing_therapist:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if license number already exists
    existing_license = db.query(Therapist).filter(
        Therapist.license_number == therapist_data.license_number
    ).first()
    if existing_license:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="License number already registered"
        )
    
    # Hash the password
    hashed_password = get_password_hash(therapist_data.password)
    
    # Create new therapist
    new_therapist = Therapist(
        name=therapist_data.name,
        email=therapist_data.email,
        hashed_password=hashed_password,
        license_number=therapist_data.license_number,
        specialty=therapist_data.specialty,
        address=therapist_data.address
    )
    
    try:
        db.add(new_therapist)
        db.commit()
        db.refresh(new_therapist)
        return new_therapist
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed. Please check your information."
        )

@router.post("/login", response_model=Token)
async def login_therapist(
    login_data: TherapistLogin,
    db: Session = Depends(get_db)
):
    """
    Login endpoint for therapists
    
    Returns JWT access token on successful authentication
    """
    # Find therapist by email
    therapist = db.query(Therapist).filter(
        Therapist.email == login_data.email
    ).first()
    
    if not therapist:
        print(f"[THERAPIST LOGIN FAILED] Therapist not found with email: {login_data.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify password
    password_valid = verify_password(login_data.password, therapist.hashed_password)
    print(f"[THERAPIST LOGIN ATTEMPT] Email: {login_data.email}, Therapist: {therapist.name}, Password Valid: {password_valid}")
    
    if not password_valid:
        print(f"[THERAPIST LOGIN FAILED] Invalid password for therapist: {therapist.name} ({therapist.email})")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = create_access_token(
        data={"sub": therapist.email, "id": therapist.id}
    )
    print(f"[THERAPIST LOGIN SUCCESS] Therapist: {therapist.name} ({therapist.email})")
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.get("/me", response_model=TherapistResponse)
async def get_therapist_profile(
    current_therapist: Therapist = Depends(get_current_therapist)
):
    """
    Get current authenticated therapist's profile
    
    Requires valid JWT token in Authorization header
    """
    return current_therapist
