from fastapi import APIRouter, Request, UploadFile, File, Form
import requests
import os
import tempfile
import base64

from openai import OpenAI  # used for both OpenAI whisper and Groq (OpenAI-compatible)

router = APIRouter(prefix="/voice", tags=["Voice"])

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

@router.post("/session")
async def create_realtime_session():
    """
    Creates ephemeral key for frontend to connect directly to OpenAI Realtime API
    """

    response = requests.post(
        "https://api.openai.com/v1/realtime/sessions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "gpt-4o-realtime-preview",
            "voice": "alloy",
            "input_audio_transcription": {
                "model": "whisper-1"
            },
        },
    )

    return response.json()


@router.post("/erp-voice-message")
async def erp_voice_message(req: Request):
    """
    This is called by frontend when user speech is converted to text.
    It sends text to LangGraph.
    """

    body = await req.json()
    session_id = body["session_id"]
    text = body["text"]

    from app.erp.ERPCoach.graph import invoke_erp_coach

    result = invoke_erp_coach({
        "session_id": session_id,
        "event_type": "USER_MESSAGE",
        "user_message": text,
    })

    # 🔥 DEBUG PRINT (IMPORTANT)
    print("🔥 FULL GRAPH RESULT:", result)

    # 🔥 SAFE RETURN (ALWAYS WORKS)
    coach_json = result.get("coach_response_json", {})


    return {
    "coach_message": coach_json.get("coach_message"),
    "full_response": coach_json   # optional (for debugging)
}


@router.post("/transcribe-and-respond")
async def transcribe_and_respond(
    audio: UploadFile = File(...),
    session_id: str = Form(...),
):
    print("🔥 VOICE ENDPOINT HIT")
    if not session_id or session_id == "undefined":
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="session_id is required")
    """
    1. Transcribe audio via Groq whisper (free) or OpenAI whisper-1 as fallback.
    2. Send transcript to ERP coach (xAI Grok).
    3. Return { transcript, coach_message }.
    """
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        stt_client = OpenAI(
            api_key=groq_key,
            base_url="https://api.groq.com/openai/v1",
        )
        stt_model = "whisper-large-v3-turbo"
    else:
        stt_client = OpenAI(api_key=OPENAI_API_KEY)
        stt_model = "whisper-1"

    audio_bytes = await audio.read()

    # Write to a temp file — OpenAI client needs a seekable file-like object
    suffix = os.path.splitext(audio.filename or "voice.webm")[1] or ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as f:
            transcription = stt_client.audio.transcriptions.create(
                model=stt_model,
                file=f,
                language="en",
                prompt="This is English speech.",
                temperature=0, # improves consistency
            )
        transcript = transcription.text
    finally:
        os.unlink(tmp_path)

    if not transcript or len(transcript.strip()) < 3:
        return {"transcript": "", "coach_message": None}

    from app.erp.ERPCoach.graph import invoke_erp_coach

    result = invoke_erp_coach({
        "session_id": session_id,
        "event_type": "USER_MESSAGE",
        "user_message": transcript,
    })

    coach_json = result.get("coach_response_json", {})
    coach_message = coach_json.get("coach_message")

    # Generate TTS via Groq (canopylabs/orpheus-v1-english, same config as test_voice.py)
    audio_b64 = None
    if coach_message and groq_key:
        try:
            tts_client = OpenAI(
                api_key=groq_key,
                base_url="https://api.groq.com/openai/v1",
            )
            tts_response = tts_client.audio.speech.create(
                model="canopylabs/orpheus-v1-english",
                voice="hannah",
                input=coach_message,
                response_format="wav",
            )
            audio_b64 = base64.b64encode(tts_response.read()).decode("utf-8")
        except Exception as tts_err:
            print(f"TTS exception: {tts_err}")

    return {
        "transcript": transcript,
        "coach_message": coach_message,
        "audio_b64": audio_b64,   # None → frontend falls back to SpeechSynthesis
    }