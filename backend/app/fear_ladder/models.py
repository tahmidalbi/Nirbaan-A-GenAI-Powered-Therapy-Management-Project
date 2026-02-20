from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database.base import Base


class FearLadderStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


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
