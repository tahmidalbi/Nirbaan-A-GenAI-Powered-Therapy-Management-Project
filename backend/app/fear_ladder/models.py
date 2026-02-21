from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database.base import Base


class FearLadderStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class AILadderReviewStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class FearLadder(Base):
    __tablename__ = "fear_ladders"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    status = Column(SQLEnum(FearLadderStatus), default=FearLadderStatus.pending, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(Integer, ForeignKey("therapists.id"), nullable=True)
    
    # Relationships
    patient = relationship("Patient", backref="fear_ladders")
    approver = relationship("Therapist", foreign_keys=[approved_by])
    items = relationship("FearLadderItem", back_populates="fear_ladder", cascade="all, delete-orphan")


class FearLadderItem(Base):
    __tablename__ = "fear_ladder_items"
    
    id = Column(Integer, primary_key=True, index=True)
    fear_ladder_id = Column(Integer, ForeignKey("fear_ladders.id"), nullable=False)
    item = Column(Text, nullable=False)
    suds = Column(Integer, nullable=False)  # 0-100 rating
    order_index = Column(Integer, nullable=False)  # Order in the ladder
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship
    fear_ladder = relationship("FearLadder", back_populates="items")


class AILadderReview(Base):
    """AI-powered analysis of fear ladder completeness based on intake and daily logs."""
    __tablename__ = "ai_ladder_reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    ladder_id = Column(Integer, ForeignKey("fear_ladders.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    therapist_id = Column(Integer, ForeignKey("therapists.id"), nullable=False, index=True)
    status = Column(SQLEnum(AILadderReviewStatus), default=AILadderReviewStatus.queued, nullable=False, index=True)
    model_name = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    ladder = relationship("FearLadder", backref="ai_reviews")
    patient = relationship("Patient", backref="ai_ladder_reviews")
    therapist = relationship("Therapist", backref="ai_ladder_reviews")
    suggestions = relationship("AILadderSuggestion", back_populates="review", cascade="all, delete-orphan")


class AILadderSuggestion(Base):
    """A missing obsession-compulsion pair detected by AI analysis."""
    __tablename__ = "ai_ladder_suggestions"
    
    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, ForeignKey("ai_ladder_reviews.id"), nullable=False, index=True)
    obsession_label = Column(Text, nullable=False)
    compulsion_summary = Column(Text, nullable=False)
    rationale = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    review = relationship("AILadderReview", back_populates="suggestions")
    evidence = relationship("AILadderEvidence", back_populates="suggestion", cascade="all, delete-orphan")


class AILadderEvidence(Base):
    """Evidence quote supporting an AI ladder suggestion."""
    __tablename__ = "ai_ladder_evidence"
    
    id = Column(Integer, primary_key=True, index=True)
    suggestion_id = Column(Integer, ForeignKey("ai_ladder_suggestions.id"), nullable=False, index=True)
    source_type = Column(String(50), nullable=False)  # 'intake' or 'daily_log'
    source_id = Column(Integer, nullable=False)  # ID of the intake or log entry
    source_date = Column(DateTime, nullable=True)  # Date of the source (for logs)
    field_name = Column(String(100), nullable=True)  # Field name in the source
    quote_text = Column(Text, nullable=False)  # The actual quote
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship
    suggestion = relationship("AILadderSuggestion", back_populates="evidence")
