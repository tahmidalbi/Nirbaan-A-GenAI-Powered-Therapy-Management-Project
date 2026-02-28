# app/education/fear_ladder/models.py
from sqlalchemy import Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime
from app.database.base import Base


class FearLadderEducationCache(Base):
    """Stores generated fear ladder education content for patients"""
    __tablename__ = "fear_ladder_education_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("patients.id"), 
        nullable=False,
        unique=True,  # One education per patient
        index=True
    )
    
    # Store the full education JSON
    topic: Mapped[str] = mapped_column(String, nullable=False)
    reading_level: Mapped[str] = mapped_column(String, default="simple")
    sections_json: Mapped[dict] = mapped_column(JSON, nullable=False)  # List of Section objects
    sources_json: Mapped[dict] = mapped_column(JSON, nullable=False)   # List of Source objects
    disclaimer: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        server_default=func.now(), 
        onupdate=func.now()
    )
