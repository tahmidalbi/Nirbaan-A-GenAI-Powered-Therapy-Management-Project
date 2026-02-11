"""
Session Picker Agent - Parallel Data Fetch (Agent 1b)

This agent fetches the last 2 therapy session transcripts from the database.
It is a pure database query agent with no LLM calls.

Retrieves:
- Last 2 session transcripts ordered by week number (descending)
- Session metadata (dates, week numbers)

This agent runs in parallel with History Picker (Agent 1a) to minimize latency.
Session transcripts provide the actual therapeutic content and continuity signal
that the Context Synthesiser agent will use to analyze session-to-session progress.
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.sessions.models import TherapySession


class SessionPickerAgent:
    """
    Agent 1b: Session Picker - Fetches recent session transcripts
    
    This agent runs in parallel with History Picker (Agent 1a) to minimize latency.
    Both are pure database reads with no dependencies on each other.
    """
    
    def __init__(self, db: Session):
        """
        Initialize Session Picker Agent
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def fetch_recent_sessions(
        self,
        patient_id: int,
        therapist_id: int,
        num_sessions: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Fetch the most recent therapy session transcripts
        
        Args:
            patient_id: Patient's database ID
            therapist_id: Therapist's database ID
            num_sessions: Number of recent sessions to fetch (default: 2)
            
        Returns:
            List of session dictionaries, ordered from most recent to oldest
            Each session contains:
            - id: Session database ID
            - week_number: Week number of the session
            - session_date: Date of the session
            - transcript: Full session transcript
            - created_at: Timestamp when transcript was created
            
        Raises:
            ValueError: If no sessions found for the patient-therapist pair
        """
        # Query for recent sessions, ordered by week_number descending
        sessions = self.db.query(TherapySession).filter(
            TherapySession.patient_id == patient_id,
            TherapySession.therapist_id == therapist_id
        ).order_by(
            desc(TherapySession.week_number)
        ).limit(num_sessions).all()
        
        if not sessions:
            raise ValueError(
                f"No therapy sessions found for patient {patient_id} with therapist {therapist_id}"
            )
        
        # Structure the session data
        session_data = []
        for session in sessions:
            session_data.append({
                "id": session.id,
                "week_number": session.week_number,
                "session_date": session.session_date.isoformat() if session.session_date else None,
                "transcript": session.transcript,
                "created_at": session.created_at.isoformat() if session.created_at else None,
                "updated_at": session.updated_at.isoformat() if session.updated_at else None,
            })
        
        return session_data
    
    def get_session_summary(self, sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a summary of the fetched sessions
        
        This is a convenience method that provides metadata about the sessions.
        
        Args:
            sessions: List of session dictionaries from fetch_recent_sessions()
            
        Returns:
            Summary dictionary with session metadata
        """
        if not sessions:
            return {
                "count": 0,
                "week_range": None,
                "has_transcripts": False,
                "total_transcript_length": 0,
            }
        
        # Calculate summary statistics
        week_numbers = [s["week_number"] for s in sessions]
        total_length = sum(len(s["transcript"]) for s in sessions)
        
        summary = {
            "count": len(sessions),
            "week_range": {
                "earliest": min(week_numbers),
                "latest": max(week_numbers),
            },
            "weeks_covered": sorted(week_numbers, reverse=True),
            "has_transcripts": all(s["transcript"] for s in sessions),
            "total_transcript_length": total_length,
            "sessions_detail": [
                {
                    "week": s["week_number"],
                    "date": s["session_date"],
                    "transcript_length": len(s["transcript"]),
                }
                for s in sessions
            ]
        }
        
        return summary
    
    def fetch_specific_week_session(
        self,
        patient_id: int,
        therapist_id: int,
        week_number: int
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch a specific week's session transcript
        
        This is a utility method for when a specific week is needed.
        
        Args:
            patient_id: Patient's database ID
            therapist_id: Therapist's database ID
            week_number: Specific week number to fetch
            
        Returns:
            Session dictionary if found, None otherwise
        """
        session = self.db.query(TherapySession).filter(
            TherapySession.patient_id == patient_id,
            TherapySession.therapist_id == therapist_id,
            TherapySession.week_number == week_number
        ).first()
        
        if not session:
            return None
        
        return {
            "id": session.id,
            "week_number": session.week_number,
            "session_date": session.session_date.isoformat() if session.session_date else None,
            "transcript": session.transcript,
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "updated_at": session.updated_at.isoformat() if session.updated_at else None,
        }
    
    async def execute(
        self,
        patient_id: int,
        therapist_id: int,
        num_sessions: int = 2
    ) -> Dict[str, Any]:
        """
        Execute the Session Picker agent (main entry point for LangGraph)
        
        This method is designed to be called from a LangGraph node.
        It fetches recent sessions and returns both raw data and summary.
        
        Args:
            patient_id: Patient's database ID
            therapist_id: Therapist's database ID
            num_sessions: Number of recent sessions to fetch (default: 2)
            
        Returns:
            Dictionary containing:
            - sessions: List of session transcripts
            - session_summary: Metadata about fetched sessions
            - agent_metadata: Execution metadata
        """
        try:
            # Fetch recent sessions
            sessions = self.fetch_recent_sessions(
                patient_id=patient_id,
                therapist_id=therapist_id,
                num_sessions=num_sessions
            )
            
            # Generate summary
            session_summary = self.get_session_summary(sessions)
            
            return {
                "status": "success",
                "sessions": sessions,
                "session_summary": session_summary,
                "agent_metadata": {
                    "agent_name": "SessionPickerAgent",
                    "agent_type": "database_query",
                    "llm_calls": 0,
                    "patient_id": patient_id,
                    "therapist_id": therapist_id,
                    "num_sessions_requested": num_sessions,
                    "num_sessions_retrieved": len(sessions),
                }
            }
            
        except ValueError as e:
            # No sessions found - this may be acceptable for first-time patients
            return {
                "status": "no_data",
                "sessions": [],
                "session_summary": self.get_session_summary([]),
                "error_message": str(e),
                "agent_metadata": {
                    "agent_name": "SessionPickerAgent",
                    "agent_type": "database_query",
                    "llm_calls": 0,
                    "num_sessions_requested": num_sessions,
                    "num_sessions_retrieved": 0,
                }
            }
        
        except Exception as e:
            return {
                "status": "error",
                "error_type": "system_error",
                "error_message": str(e),
                "agent_metadata": {
                    "agent_name": "SessionPickerAgent",
                    "agent_type": "database_query",
                    "llm_calls": 0,
                }
            }
