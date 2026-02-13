"""
Context Synthesiser Agent - LLM-Based Clinical Summary Generator (Agent 2)

This agent condenses raw data from History Picker and Session Picker into a focused
clinical summary. This is the single most impactful addition to the refined architecture.

What it does:
- Takes raw JSON dumps from Agents 1a and 1b
- Produces a structured 6-section clinical summary
- This summary is what ALL downstream agents read (not the raw data)

Why it matters:
- Reduces token waste (thousands of tokens → focused summary)
- Improves signal quality (key clinical signals no longer buried in noise)
- Better retrieval (cleaner context for KB queries)
- Independently evaluable (summary quality as a metric)

NO KB retrieval - this agent works purely on patient's own data.
"""
from typing import Dict, Any
import os
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")


class ContextSynthesiserAgent:
    """
    Agent 2: Context Synthesiser - Condenses raw data into clinical summary
    
    This agent sits between the data-fetching stage (Agents 1a + 1b) and the
    reasoning stage (Agent 3+). It's a pure LLM summarization task.
    """
    
    def __init__(self):
        """Initialize Context Synthesiser Agent"""
        self.agent_name = "ContextSynthesiserAgent"
        self.llm_model = LLM_MODEL
        
    def _build_system_prompt(self) -> str:
        """
        Build the system prompt for clinical summarization
        
        The prompt enforces a strict 6-section output structure that matches
        what downstream agents expect.
        """
        return """You are a clinical data synthesizer for a therapy management system.

Your task: Condense raw patient data into a focused clinical summary for therapy protocol generation.

CRITICAL RULES:
1. Extract only clinically relevant information
2. Identify trajectory (improving/stagnant/worsening) from progress data
3. Highlight key breakthroughs, red flags, and unresolved issues
4. Be concise but preserve critical details
5. Output VALID JSON with the exact structure specified below

OUTPUT STRUCTURE (6 required sections as JSON):

{
  "patient_profile": {
    "name": "patient name",
    "conditions": ["condition1", "condition2"],
    "current_week": number,
    "conditions_description": "brief description"
  },
  "symptom_trajectory": {
    "direction": "improving" | "stagnant" | "worsening",
    "key_inflection_points": ["point1", "point2"],
    "evidence": "summary of evidence from progress reports"
  },
  "recent_session_themes": {
    "attempted": ["what was tried in last sessions"],
    "what_worked": ["successful interventions"],
    "what_didnt_work": ["unsuccessful attempts"],
    "continuity_signals": "key patterns"
  },
  "therapist_priorities": {
    "from_notes": ["priority1", "priority2"],
    "ai_instruction": "therapist's AI protocol preference",
    "current_session_focus": "focus for this session or null"
  },
  "open_concerns": {
    "red_flags": ["flag1", "flag2"],
    "stagnation_signals": ["signal1", "signal2"],
    "unresolved_issues": ["issue1", "issue2"],
    "safety_considerations": ["consideration1", "consideration2"]
  },
  "data_completeness": {
    "quality_assessment": "brief assessment",
    "notable_gaps": ["gap1", "gap2"]
  }
}

Return ONLY valid JSON. No markdown, no code blocks, just the JSON object."""

    def _build_user_prompt(
        self, 
        history_data: Dict[str, Any],
        session_data: Dict[str, Any],
        session_focus: str = None
    ) -> str:
        """
        Build the user prompt with raw data
        
        Args:
            history_data: Output from History Picker Agent
            session_data: Output from Session Picker Agent
            session_focus: Optional therapist's current session focus
            
        Returns:
            Formatted prompt string with all raw data
        """
        # Extract structured summary from history data (this is pre-organized)
        history_summary = history_data.get("structured_summary", {})
        
        # Build patient profile section
        patient_profile = history_summary.get("patient_profile", {})
        profile_text = f"""
PATIENT PROFILE DATA:
- Name: {patient_profile.get('name', 'Unknown')}
- Conditions: {patient_profile.get('conditions', 'Not specified')}
- Current Week: {patient_profile.get('current_week', 0)}
- Conditions Description: {patient_profile.get('conditions_description', 'Not provided')}
"""
        
        # Build clinical history section
        clinical_history = history_summary.get("clinical_history", {})
        history_text = f"""
CLINICAL HISTORY:
- Initial Condition: {clinical_history.get('initial_condition', 'Not provided')}

Weekly Progress Reports:
"""
        for week_progress in clinical_history.get("weekly_progress", []):
            history_text += f"  [{week_progress['week']}]: {week_progress['content']}\n"
        
        # Build therapist observations section
        therapist_obs = history_summary.get("therapist_observations", {})
        therapist_text = f"""
THERAPIST OBSERVATIONS:
- AI Protocol Instruction: {therapist_obs.get('ai_protocol_instruction', 'Not provided')}

Weekly Therapist Notes:
"""
        for note in therapist_obs.get("weekly_notes", []):
            therapist_text += f"  [{note['week']}]: {note['content']}\n"
        
        # Build session transcripts section
        sessions = session_data.get("sessions", [])
        session_summary = session_data.get("session_summary", {})
        
        session_text = f"""
RECENT SESSION TRANSCRIPTS:
- Number of sessions: {session_summary.get('count', 0)}
- Weeks covered: {', '.join(map(str, session_summary.get('weeks_covered', [])))}

"""
        if sessions:
            for session in sessions:
                session_text += f"""
[Week {session['week_number']} - {session.get('session_date', 'Date unknown')}]
Transcript ({len(session['transcript'])} chars):
{session['transcript']}

---
"""
        else:
            session_text += "No previous session transcripts available (first-time patient).\n"
        
        # Build current session focus section
        focus_text = f"""
CURRENT SESSION FOCUS:
{session_focus if session_focus else 'Not specified by therapist'}
"""
        
        # Combine all sections
        full_prompt = f"""Please synthesize the following raw patient data into a structured clinical summary.

{profile_text}

{history_text}

{therapist_text}

{session_text}

{focus_text}

Generate a clinical summary following the 6-section structure specified in your instructions."""
        
        return full_prompt
    
    def synthesize(
        self,
        history_data: Dict[str, Any],
        session_data: Dict[str, Any],
        session_focus: str = None
    ) -> Dict[str, Any]:
        """
        Synthesize raw data into clinical summary
        
        Args:
            history_data: Output from History Picker Agent
            session_data: Output from Session Picker Agent  
            session_focus: Optional current session focus from therapist
            
        Returns:
            Dictionary containing:
            - clinical_summary: The 6-section synthesized text
            - metadata: Token usage, model, etc.
        """
        try:
            # Build prompts
            system_prompt = self._build_system_prompt()
            user_prompt = self._build_user_prompt(history_data, session_data, session_focus)
            
            # Call LLM with temperature 0 (deterministic) and JSON mode
            response = client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0,  # Deterministic summarization
                max_tokens=2000,  # Enough for detailed 6-section summary
                response_format={"type": "json_object"}  # Enforce JSON output
            )
            
            # Parse the JSON response
            import json
            clinical_summary_dict = json.loads(response.choices[0].message.content)
            
            # Also create a formatted string version for agents that need text
            clinical_summary_text = self._format_summary_as_text(clinical_summary_dict)
            
            return {
                "status": "success",
                "clinical_summary": clinical_summary_dict,  # Structured dict
                "clinical_summary_text": clinical_summary_text,  # Formatted string
                "metadata": {
                    "agent_name": self.agent_name,
                    "agent_type": "llm_summarization",
                    "model": self.llm_model,
                    "llm_calls": 1,
                    "temperature": 0,
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error_type": "llm_error",
                "error_message": str(e),
                "metadata": {
                    "agent_name": self.agent_name,
                    "agent_type": "llm_summarization",
                    "llm_calls": 0,
                }
            }
    
    def _format_summary_as_text(self, summary_dict: Dict[str, Any]) -> str:
        """
        Format the structured summary dict as readable text for LLM prompts
        
        Args:
            summary_dict: The structured clinical summary dict
            
        Returns:
            Formatted multi-line string with clear section headers
        """
        import json
        
        text_parts = ["=== CLINICAL SUMMARY ===\n"]
        
        # Patient Profile
        if "patient_profile" in summary_dict:
            pp = summary_dict["patient_profile"]
            text_parts.append(f"**PATIENT PROFILE**")
            text_parts.append(f"Name: {pp.get('name', 'Unknown')}")
            text_parts.append(f"Conditions: {', '.join(pp.get('conditions', []))}")
            text_parts.append(f"Current Week: {pp.get('current_week', 'Unknown')}")
            if pp.get('conditions_description'):
                text_parts.append(f"Description: {pp['conditions_description']}")
            text_parts.append("")
        
        # Symptom Trajectory
        if "symptom_trajectory" in summary_dict:
            st = summary_dict["symptom_trajectory"]
            text_parts.append(f"**SYMPTOM TRAJECTORY**")
            text_parts.append(f"Direction: {st.get('direction', 'Unknown')}")
            if st.get('key_inflection_points'):
                text_parts.append(f"Key Points: {', '.join(st['key_inflection_points'])}")
            text_parts.append(f"Evidence: {st.get('evidence', 'N/A')}")
            text_parts.append("")
        
        # Recent Session Themes
        if "recent_session_themes" in summary_dict:
            rst = summary_dict["recent_session_themes"]
            text_parts.append(f"**RECENT SESSION THEMES**")
            if rst.get('attempted'):
                text_parts.append(f"Attempted: {', '.join(rst['attempted'])}")
            if rst.get('what_worked'):
                text_parts.append(f"What Worked: {', '.join(rst['what_worked'])}")
            if rst.get('what_didnt_work'):
                text_parts.append(f"What Didn't Work: {', '.join(rst['what_didnt_work'])}")
            text_parts.append(f"Continuity: {rst.get('continuity_signals', 'N/A')}")
            text_parts.append("")
        
        # Therapist Priorities
        if "therapist_priorities" in summary_dict:
            tp = summary_dict["therapist_priorities"]
            text_parts.append(f"**THERAPIST PRIORITIES**")
            if tp.get('from_notes'):
                text_parts.append(f"From Notes: {', '.join(tp['from_notes'])}")
            text_parts.append(f"AI Instruction: {tp.get('ai_instruction', 'None specified')}")
            if tp.get('current_session_focus'):
                text_parts.append(f"Session Focus: {tp['current_session_focus']}")
            text_parts.append("")
        
        # Open Concerns
        if "open_concerns" in summary_dict:
            oc = summary_dict["open_concerns"]
            text_parts.append(f"**OPEN CONCERNS**")
            if oc.get('red_flags'):
                text_parts.append(f"Red Flags: {', '.join(oc['red_flags'])}")
            if oc.get('stagnation_signals'):
                text_parts.append(f"Stagnation: {', '.join(oc['stagnation_signals'])}")
            if oc.get('unresolved_issues'):
                text_parts.append(f"Unresolved: {', '.join(oc['unresolved_issues'])}")
            if oc.get('safety_considerations'):
                text_parts.append(f"Safety: {', '.join(oc['safety_considerations'])}")
            text_parts.append("")
        
        # Data Completeness
        if "data_completeness" in summary_dict:
            dc = summary_dict["data_completeness"]
            text_parts.append(f"**DATA COMPLETENESS**")
            text_parts.append(f"Quality: {dc.get('quality_assessment', 'Unknown')}")
            if dc.get('notable_gaps'):
                text_parts.append(f"Gaps: {', '.join(dc['notable_gaps'])}")
        
        return "\n".join(text_parts)
    
    async def execute(
        self,
        history_data: Dict[str, Any],
        session_data: Dict[str, Any],
        session_focus: str = None
    ) -> Dict[str, Any]:
        """
        Execute the Context Synthesiser agent (main entry point for LangGraph)
        
        This method is designed to be called from a LangGraph node.
        It takes outputs from parallel data-fetch stage and produces a summary.
        
        Args:
            history_data: Output from History Picker Agent (Agent 1a)
            session_data: Output from Session Picker Agent (Agent 1b)
            session_focus: Optional current session focus from therapist
            
        Returns:
            Dictionary containing:
            - status: success/error
            - clinical_summary: The synthesized 6-section summary
            - agent_metadata: Execution metadata
        """
        # Validate inputs
        if not history_data or history_data.get("status") != "success":
            return {
                "status": "error",
                "error_type": "invalid_input",
                "error_message": "History data is missing or invalid",
                "agent_metadata": {
                    "agent_name": self.agent_name,
                    "llm_calls": 0,
                }
            }
        
        # Session data can have "no_data" status for first-time patients - this is OK
        if not session_data or session_data.get("status") not in ["success", "no_data"]:
            return {
                "status": "error",
                "error_type": "invalid_input",
                "error_message": "Session data is missing or invalid",
                "agent_metadata": {
                    "agent_name": self.agent_name,
                    "llm_calls": 0,
                }
            }
        
        # Synthesize the summary
        result = self.synthesize(history_data, session_data, session_focus)
        
        return result
