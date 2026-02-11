"""
History Picker Agent - Parallel Data Fetch (Agent 1a)

This agent fetches and structures the patient's clinical history from the database.
It is a pure database query agent with no LLM calls.

Retrieves:
- Patient demographics and conditions
- Initial condition and weekly self-reports (from patient_progress)
- Therapist week-by-week notes (from therapist_notes)
- Therapist's global AI protocol instruction

Note: Does NOT fetch last generated protocol. Session-to-session continuity 
is handled by analyzing previous actual therapy session transcripts.
"""
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.patients.models import Patient
from app.progress.models import PatientProgress, TherapistNote


class HistoryPickerAgent:
    """
    Agent 1a: History Picker - Fetches patient clinical history
    
    This agent runs in parallel with Session Picker (Agent 1b) to minimize latency.
    Both are pure database reads with no dependencies on each other.
    """
    
    def __init__(self, db: Session):
        """
        Initialize History Picker Agent
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def fetch_patient_history(
        self, 
        patient_id: int, 
        therapist_id: int
    ) -> Dict[str, Any]:
        """
        Fetch complete patient clinical history
        
        Args:
            patient_id: Patient's database ID
            therapist_id: Therapist's database ID
            
        Returns:
            Dictionary containing:
            - patient_demographics: Patient profile (name, conditions, etc.)
            - patient_progress: Initial condition and weekly progress reports
            - therapist_notes: Week-by-week therapist notes
            - ai_protocol_instruction: Therapist's global AI preferences
            - metadata: Query metadata (current_week, timestamps)
            
        Raises:
            ValueError: If patient not found or therapist-patient mismatch
        """
        # Fetch patient demographics
        patient = self.db.query(Patient).filter(
            Patient.id == patient_id,
            Patient.therapist_id == therapist_id
        ).first()
        
        if not patient:
            raise ValueError(
                f"Patient {patient_id} not found or does not belong to therapist {therapist_id}"
            )
        
        # Fetch patient progress data
        progress = self.db.query(PatientProgress).filter(
            PatientProgress.patient_id == patient_id
        ).first()
        
        # Fetch therapist notes
        notes = self.db.query(TherapistNote).filter(
            TherapistNote.patient_id == patient_id,
            TherapistNote.therapist_id == therapist_id
        ).first()
        
        # Structure the output
        history_data = {
            "patient_demographics": {
                "id": patient.id,
                "name": patient.name,
                "email": patient.email,
                "conditions": patient.conditions,
                "conditions_description": patient.conditions_description,
                "address": patient.address,
                "created_at": patient.created_at.isoformat() if patient.created_at else None,
                "updated_at": patient.updated_at.isoformat() if patient.updated_at else None,
            },
            "patient_progress": {
                "id": progress.id if progress else None,
                "initial_condition": progress.initial_condition if progress else None,
                "weekly_progress": progress.weekly_progress if progress else {},
                "current_week": progress.current_week if progress else 0,
                "created_at": progress.created_at.isoformat() if progress and progress.created_at else None,
                "updated_at": progress.updated_at.isoformat() if progress and progress.updated_at else None,
            },
            "therapist_notes": {
                "id": notes.id if notes else None,
                "week_notes": notes.week_notes if notes else {},
                "ai_protocol_instruction": notes.ai_protocol_instruction if notes else None,
                "created_at": notes.created_at.isoformat() if notes and notes.created_at else None,
                "updated_at": notes.updated_at.isoformat() if notes and notes.updated_at else None,
            },
            "metadata": {
                "patient_id": patient_id,
                "therapist_id": therapist_id,
                "current_week": progress.current_week if progress else 0,
                "has_progress_data": progress is not None,
                "has_therapist_notes": notes is not None,
            }
        }
        
        return history_data
    
    def get_structured_summary(self, history_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a structured summary from raw history data
        
        This is a convenience method that extracts key information for downstream agents.
        
        Args:
            history_data: Raw history data from fetch_patient_history()
            
        Returns:
            Structured summary with key clinical markers
        """
        demographics = history_data["patient_demographics"]
        progress = history_data["patient_progress"]
        notes = history_data["therapist_notes"]
        metadata = history_data["metadata"]
        
        # Extract key progress indicators
        weekly_progress_list = []
        if progress["weekly_progress"]:
            for week_key in sorted(progress["weekly_progress"].keys(), 
                                   key=lambda x: int(x.split("_")[1]) if "_" in x else 0):
                weekly_progress_list.append({
                    "week": week_key,
                    "content": progress["weekly_progress"][week_key]
                })
        
        # Extract therapist notes chronologically
        therapist_notes_list = []
        if notes["week_notes"]:
            for week_key in sorted(notes["week_notes"].keys(),
                                   key=lambda x: 0 if x == "initial" else int(x.split("_")[1]) if "_" in x else 0):
                therapist_notes_list.append({
                    "week": week_key,
                    "content": notes["week_notes"][week_key]
                })
        
        summary = {
            "patient_profile": {
                "name": demographics["name"],
                "conditions": demographics["conditions"],
                "conditions_description": demographics["conditions_description"],
                "current_week": metadata["current_week"],
            },
            "clinical_history": {
                "initial_condition": progress["initial_condition"],
                "weekly_progress": weekly_progress_list,
                "total_weeks_tracked": len(weekly_progress_list),
            },
            "therapist_observations": {
                "weekly_notes": therapist_notes_list,
                "ai_protocol_instruction": notes["ai_protocol_instruction"],
                "total_weeks_documented": len(therapist_notes_list),
            },
            "data_completeness": {
                "has_initial_condition": progress["initial_condition"] is not None,
                "has_weekly_progress": len(weekly_progress_list) > 0,
                "has_therapist_notes": len(therapist_notes_list) > 0,
                "has_ai_instruction": notes["ai_protocol_instruction"] is not None,
            }
        }
        
        return summary
    
    async def execute(
        self, 
        patient_id: int, 
        therapist_id: int
    ) -> Dict[str, Any]:
        """
        Execute the History Picker agent (main entry point for LangGraph)
        
        This method is designed to be called from a LangGraph node.
        It fetches the raw data and returns both raw and structured formats.
        
        Args:
            patient_id: Patient's database ID
            therapist_id: Therapist's database ID
            
        Returns:
            Dictionary containing:
            - raw_data: Complete database query results
            - structured_summary: Organized clinical summary
            - agent_metadata: Execution metadata
        """
        try:
            # Fetch raw history data
            raw_data = self.fetch_patient_history(patient_id, therapist_id)
            
            # Generate structured summary
            structured_summary = self.get_structured_summary(raw_data)
            
            return {
                "status": "success",
                "raw_data": raw_data,
                "structured_summary": structured_summary,
                "agent_metadata": {
                    "agent_name": "HistoryPickerAgent",
                    "agent_type": "database_query",
                    "llm_calls": 0,
                    "patient_id": patient_id,
                    "therapist_id": therapist_id,
                }
            }
            
        except ValueError as e:
            return {
                "status": "error",
                "error_type": "validation_error",
                "error_message": str(e),
                "agent_metadata": {
                    "agent_name": "HistoryPickerAgent",
                    "agent_type": "database_query",
                    "llm_calls": 0,
                }
            }
        
        except Exception as e:
            return {
                "status": "error",
                "error_type": "system_error",
                "error_message": str(e),
                "agent_metadata": {
                    "agent_name": "HistoryPickerAgent",
                    "agent_type": "database_query",
                    "llm_calls": 0,
                }
            }
