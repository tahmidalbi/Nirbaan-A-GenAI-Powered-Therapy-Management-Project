"""
Post-session AI analysis using GPT.

After a session ends, call `generate_session_analysis(session_id)` to:
  1. Retrieve the full transcript from the DB
  2. Send it to GPT with a structured prompt
  3. Parse the response into summary / topics / interventions
  4. Save a LiveSessionAnalysis row
"""

import json
import logging
import os
from typing import Optional

from openai import OpenAI
from sqlalchemy.orm import Session

from app.live_sessions.models import (
    LiveSession,
    LiveSessionTranscript,
    LiveSessionAnalysis,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are an expert clinical psychologist reviewing a therapy session transcript.
Analyse the conversation and return a JSON object with EXACTLY these keys:

{
  "summary": "<2-4 paragraph narrative summary of the session>",
  "detected_topics": ["<topic1>", "<topic2>", ...],
  "therapist_interventions": [
    {"type": "<intervention type>", "description": "<short description>"},
    ...
  ],
  "patient_emotions": [
    {"emotion": "<emotion name>", "intensity": "<low|medium|high>", "context": "<brief context when this emotion was expressed>"},
    ...
  ],
  "homeworks": [
    {"task": "<specific homework task>", "rationale": "<why this homework is beneficial>", "frequency": "<how often to practice>"},
    ...
  ]
}

Rules:
- this is very sensitive topic as we are working with real OCD patients, so only return correnct information about the homework, only give the homework that the therapist actually discussed with the patient during the session, do not make up homework that was not discussed, if no specific homework was given, return an empty list for "homeworks". and if you are confused about some homewoks then leave it out, do not make up homeworks. only deliver that is said in the transcript, do not make up any information that is not explicitly mentioned in the transcript.
- detected_topics: list of psychological themes/topics discussed (e.g. "anxiety", "family conflict", "exposure hierarchy").
- therapist_interventions: list of clinical techniques the therapist used (e.g. "Socratic questioning", "psychoeducation", "cognitive restructuring").
- patient_emotions: list of emotions the patient expressed during the session with intensity level and context.
- homeworks: list of therapeutic homework assignments for the patient based on the session content. the session may Include practical exercises, journaling tasks, exposure exercises, or behavioral experiments. this is very sensitive topic as we are working with real OCD patients, so only return correnct information about the homework, only give the homework that the therapist actually discussed with the patient during the session, do not make up homework that was not discussed, if no specific homework was given, return an empty list for "homeworks". and if you are confused about some homewoks then leave it out, do not make up homeworks. only deliver that is said in the transcript, do not make up any information that is not explicitly mentioned in the transcript. 
- Return ONLY valid JSON, no markdown, no extra text.
"""


def _build_transcript_text(transcripts: list[LiveSessionTranscript]) -> str:
    lines = []
    for t in sorted(transcripts, key=lambda x: x.timestamp):
        ts = t.timestamp.strftime("%H:%M:%S")
        lines.append(f"[{ts}] {t.speaker}: {t.text}")
    return "\n".join(lines)


def generate_session_analysis(session_id: int, db: Session) -> Optional[LiveSessionAnalysis]:
    """
    Generate AI analysis for a completed therapy session.
    Returns the saved LiveSessionAnalysis object, or None on failure.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY not configured – skipping analysis")
        return None

    session = db.query(LiveSession).filter(LiveSession.id == session_id).first()
    if not session:
        logger.error(f"Session {session_id} not found")
        return None

    transcripts = (
        db.query(LiveSessionTranscript)
        .filter(LiveSessionTranscript.session_id == session_id)
        .order_by(LiveSessionTranscript.timestamp)
        .all()
    )
    if not transcripts:
        logger.info(f"Session {session_id} has no transcripts – skipping analysis")
        return None

    transcript_text = _build_transcript_text(transcripts)

    llm_model = os.getenv("LLM_MODEL", "gpt-5.3-chat-latest")
    client = OpenAI(api_key=api_key)

    try:
        response = client.chat.completions.create(
            model=llm_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Session transcript:\n\n{transcript_text}"},
            ],
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content
        data = json.loads(raw)

        analysis = LiveSessionAnalysis(
            session_id=session_id,
            summary=data.get("summary", ""),
            detected_topics=data.get("detected_topics", []),
            therapist_interventions=data.get("therapist_interventions", []),
            patient_emotions=data.get("patient_emotions", []),
            homeworks=data.get("homeworks", []),
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        logger.info(f"Session {session_id} analysis saved (id={analysis.id})")
        return analysis

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to generate analysis for session {session_id}: {e}")
        return None
