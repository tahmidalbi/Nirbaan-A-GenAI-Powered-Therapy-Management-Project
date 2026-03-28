"""
Streaming audio transcription over WebSocket.

Frontend sends binary audio chunks (webm/opus) every ~2-3 seconds.
Backend accumulates chunks, transcribes via Whisper, saves the transcript,
and pushes partial results back to the client in real time.

WS URL:  ws://.../api/therapy-sessions/ws/transcription/{session_id}
         ?userId=<int>&userType=therapist|patient

Incoming messages:
  - binary frames  → raw audio data (webm/opus chunks)
  - JSON {"type": "stop"}  → flush final chunk and close

Outgoing messages:
  - {"type": "transcript", "id": ..., "speaker": ..., "text": ...,
     "timestamp": ..., "confidence": ..., "is_partial": false}
  - {"type": "error", "message": ...}
"""

import asyncio
import logging
import tempfile
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, WebSocketException
from starlette.websockets import WebSocketState

from app.database.session import SessionLocal
from app.live_sessions.models import LiveSession, LiveSessionTranscript
from app.live_sessions.transcription_service import transcription_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Streaming Transcription"])

# Common Whisper hallucinations to filter out
HALLUCINATION_PATTERNS = [
    "thanks for watching",
    "thank you for watching",
    "subscribe",
    "like and subscribe",
    "see you next time",
    "bye bye",
    "goodbye",
    "thank you",
    "you",
    "...",
    "silence",
    "music",
    "[music]",
    "(music)",
    "[applause]",
    "(applause)",
]


def is_hallucination(text: str) -> bool:
    """Check if transcribed text is likely a Whisper hallucination."""
    if not text:
        return True

    cleaned = text.lower().strip()

    # Too short (likely noise)
    if len(cleaned) < 3:
        return True

    # Check against known hallucination patterns
    for pattern in HALLUCINATION_PATTERNS:
        if cleaned == pattern or cleaned.startswith(pattern):
            return True

    # Repetitive text (e.g., "the the the the")
    words = cleaned.split()
    if len(words) >= 3 and len(set(words)) == 1:
        return True

    return False


async def _transcribe_and_save(
    audio_bytes: bytes,
    session_id: int,
    speaker: str,
    language: str | None,
) -> dict | None:
    """Run Whisper on *audio_bytes*, save to DB, return JSON-ready payload."""
    if not audio_bytes or len(audio_bytes) < 500:
        # Too small – likely silence / empty frame
        return None

    if not transcription_service.is_available:
        return None

    suffix = ".webm"
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        tmp.write(audio_bytes)
        tmp.close()

        result = await asyncio.to_thread(
            transcription_service.transcribe_audio,
            open(tmp.name, "rb"),
            language,
        )
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass

    if not result.get("success") or not result.get("text", "").strip():
        return None

    text = result["text"].strip()

    # Filter out hallucinations
    if is_hallucination(text):
        logger.info(f"[Transcription] Filtered hallucination: {text}")
        return None

    # Persist to DB
    db = SessionLocal()
    try:
        entry = LiveSessionTranscript(
            session_id=session_id,
            speaker=speaker,
            text=text,
            confidence=1.0,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)

        return {
            "type": "transcript",
            "id": entry.id,
            "session_id": session_id,
            "speaker": speaker,
            "text": text,
            "timestamp": entry.timestamp.isoformat(),
            "confidence": entry.confidence,
            "is_partial": False,
        }
    finally:
        db.close()


@router.websocket("/ws/transcription/{session_id}")
async def ws_transcription(websocket: WebSocket, session_id: int):
    # Extract query params
    user_id = websocket.query_params.get("userId")
    user_type = websocket.query_params.get("userType")
    language = websocket.query_params.get("language", "en")

    if not user_id or user_type not in ("therapist", "patient"):
        await websocket.close(code=1008, reason="userId and userType required")
        return

    # Validate session exists
    db = SessionLocal()
    session = db.query(LiveSession).filter(LiveSession.id == session_id).first()
    db.close()
    if not session:
        await websocket.close(code=1008, reason="Session not found")
        return

    await websocket.accept()
    logger.info(f"[Transcription WS] {user_type}#{user_id} connected to session {session_id}")

    try:
        while True:
            msg = await websocket.receive()

            # Handle binary audio data (complete WebM blobs from frontend)
            if "bytes" in msg and msg["bytes"]:
                audio_bytes = msg["bytes"]
                logger.info(f"[Transcription WS] Received audio chunk: {len(audio_bytes)} bytes")

                # Process audio in background to not block receiving
                payload = await _transcribe_and_save(audio_bytes, session_id, user_type, language)
                if payload and websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_json(payload)

            # Handle JSON messages
            elif "text" in msg:
                import json
                try:
                    data = json.loads(msg["text"])
                except Exception:
                    continue
                if data.get("type") == "stop":
                    logger.info(f"[Transcription WS] Stop signal received")
                    break

    except WebSocketDisconnect:
        logger.info(f"[Transcription WS] {user_type}#{user_id} disconnected")
    except Exception as e:
        logger.error(f"[Transcription WS] Error: {e}")
    finally:
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close()
        logger.info(f"[Transcription WS] Cleaned up session {session_id} / {user_type}#{user_id}")
