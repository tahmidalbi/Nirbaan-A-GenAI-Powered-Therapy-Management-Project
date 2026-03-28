from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    Text,
    ForeignKey,
    DateTime,
    String,
    JSON,
    Boolean,
)
from sqlalchemy.orm import relationship

from app.database.base import Base


class ImaginalScriptRun(Base):
    __tablename__ = "imaginal_script_runs"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String(128), unique=True, nullable=False, index=True)

    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    therapist_id = Column(Integer, ForeignKey("therapists.id"), nullable=False, index=True)
    erp_item_id = Column(Integer, ForeignKey("erp_items.id"), nullable=False, index=True)

    obsession = Column(Text, nullable=False)
    compulsion = Column(Text, nullable=False)
    feared_consequence = Column(Text, nullable=False)
    script_intensity = Column(String(20), nullable=False)
    exposure_type = Column(String(20), nullable=False, default="imaginal")
    subtype = Column(String(100), nullable=True)

    status = Column(String(30), nullable=False, default="pending_review")
    revision_count = Column(Integer, nullable=False, default=1)
    latest_prompt_text = Column(Text, nullable=True)
    latest_script_text = Column(Text, nullable=True)

    approved_script_text = Column(Text, nullable=True)
    approved_audio_path = Column(Text, nullable=True)
    approved_audio_key = Column(Text, nullable=True)
    approved_script_id = Column(
        Integer,
        ForeignKey("approved_imaginal_scripts.id", use_alter=True, name="fk_run_approved_script_id"),
        nullable=True,
    )

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    versions = relationship(
        "ImaginalScriptVersion",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="ImaginalScriptVersion.version_no",
    )


class ImaginalScriptVersion(Base):
    __tablename__ = "imaginal_script_versions"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("imaginal_script_runs.id"), nullable=False, index=True)

    version_no = Column(Integer, nullable=False)
    prompt_text = Column(Text, nullable=False)
    generated_script = Column(Text, nullable=False)

    therapist_feedback = Column(Text, nullable=True)
    approved = Column(Boolean, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    run = relationship("ImaginalScriptRun", back_populates="versions")


class ApprovedImaginalScript(Base):
    __tablename__ = "approved_imaginal_scripts"

    id = Column(Integer, primary_key=True, index=True)

    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    therapist_id = Column(Integer, ForeignKey("therapists.id"), nullable=False, index=True)
    erp_item_id = Column(Integer, ForeignKey("erp_items.id"), nullable=False, index=True)
    run_id = Column(Integer, ForeignKey("imaginal_script_runs.id"), nullable=False, index=True)

    subtype = Column(String(100), nullable=True)
    approved_script = Column(Text, nullable=False)

    audio_path = Column(Text, nullable=True)
    audio_key = Column(Text, nullable=True)

    metadata_json = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)