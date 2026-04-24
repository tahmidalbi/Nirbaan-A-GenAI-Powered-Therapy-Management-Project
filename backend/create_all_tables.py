"""
Complete database setup script - creates ALL tables.
Safe to re-run: SQLAlchemy uses CREATE TABLE IF NOT EXISTS semantics.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from app.database.session import engine
from app.database.base import Base

# ── Core auth / user models ───────────────────────────────────────────────────
from app.users.models import User                                   # noqa: F401
from app.therapists.models import Therapist                         # noqa: F401
from app.patients.models import Patient                             # noqa: F401
from app.emergency_personnel.models import EmergencyPersonnel       # noqa: F401

# ── Resources / RAG ───────────────────────────────────────────────────────────
from app.resources.models import Resource, IngestionJob             # noqa: F401

# ── Intakes ───────────────────────────────────────────────────────────────────
from app.intakes.models import PatientIntake                        # noqa: F401

# ── ERP ───────────────────────────────────────────────────────────────────────
from app.erp.models import (                                        # noqa: F401
    ERPItem,
    ERPImaginalCard,
    ERPLiveSession,
    ERPSUDSReading,
    ERPExerciseNote,
    ERPChatMessage,
)

# ── ERP Script Generator ──────────────────────────────────────────────────────
from app.ERPScriptGenerator.models import (                         # noqa: F401
    ImaginalScriptRun,
    ImaginalScriptVersion,
    ApprovedImaginalScript,
)

# ── Fear ladder + AI ladder review ───────────────────────────────────────────
from app.fear_ladder.models import (                                # noqa: F401
    FearLadder,
    FearLadderItem,
    AILadderReview,
    AILadderSuggestion,
    AILadderEvidence,
)

# ── Live sessions (video therapy calls) ──────────────────────────────────────
from app.live_sessions.models import (                              # noqa: F401
    LiveSession,
    LiveSessionTranscript,
    LiveSessionAnalysis,
)

# ── Therapy sessions (written transcripts) ───────────────────────────────────
from app.therapy_sessions.models import TherapySession              # noqa: F401

# ── Patient homeworks ─────────────────────────────────────────────────────────
from app.patient_homework.models import PatientHomework             # noqa: F401

# ── Self-monitoring ───────────────────────────────────────────────────────────
from app.self_monitoring.models import (                            # noqa: F401
    SelfMonitoringDay,
    SelfMonitoringEntry,
)

# ── Progress ──────────────────────────────────────────────────────────────────
from app.progress.models import WeeklyProgress                      # noqa: F401

# ── Chat ──────────────────────────────────────────────────────────────────────
from app.chat.models import (                                       # noqa: F401
    ChatGroup,
    ChatGroupMember,
    ChatMessage,
    EPDirectMessage,
    EPGroup,
    EPGroupMessage,
    EPPatientSession,
    EPPatientMessage,
)

# ── NirbaanAI patient chatbot ─────────────────────────────────────────────────
from app.NirbaanAIPatient.models import (                           # noqa: F401
    PsychoeducationChatThread,
    PsychoeducationChatMessage,
)

# ── NirbaanAI therapist chatbot ───────────────────────────────────────────────
from app.NirbaanAITherapist.models import (                         # noqa: F401
    TherapistAIChatThread,
    TherapistAIChatMessage,
    PatientAnalysisRun,
    PatientAnalysisClarification,
)

# ── Education caches ──────────────────────────────────────────────────────────
from app.education.ocd_core.models import OCDCoreEducationCache     # noqa: F401
from app.education.fear_ladder.models import FearLadderEducationCache  # noqa: F401
from app.education.erp.models import ERPEducationCache              # noqa: F401

# ── AI Ladder Review v2 RAG (pgvector) ───────────────────────────────────────
from app.ai_ladder_review_v2.rag.taxonomy_model import TaxonomyChunk  # noqa: F401


def create_all_tables():
    """Create all database tables (idempotent)."""
    print("Creating all database tables...")
    Base.metadata.create_all(bind=engine)
    print("All tables created successfully!")


if __name__ == "__main__":
    create_all_tables()


