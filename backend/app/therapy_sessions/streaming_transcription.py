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
from app.therapy_sessions.models import TherapySession, TherapyTranscript
from app.therapy_sessions.transcription_service import transcription_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Streaming Transcription"])

# How many seconds of audio we accumulate before triggering a transcription
CHUNK_WINDOW_SECONDS = 3


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

    # Persist to DB
    db = SessionLocal()
    try:
        entry = TherapyTranscript(
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
    session = db.query(TherapySession).filter(TherapySession.id == session_id).first()
    db.close()
    if not session:
        await websocket.close(code=1008, reason="Session not found")
        return

    await websocket.accept()
    logger.info(f"[Transcription WS] {user_type}#{user_id} connected to session {session_id}")

    buffer = bytearray()
    running = True

    async def flush_buffer():
        """Transcribe whatever has accumulated in *buffer*, send result."""
        nonlocal buffer
        if not buffer:
            return
        chunk = bytes(buffer)
        buffer = bytearray()

        payload = await _transcribe_and_save(chunk, session_id, user_type, language)
        if payload and websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_json(payload)

    # Timer task: flush buffer every CHUNK_WINDOW_SECONDS
    async def timer_loop():
        nonlocal running
        while running:
            await asyncio.sleep(CHUNK_WINDOW_SECONDS)
            if running:
                try:
                    await flush_buffer()
                except Exception as e:
                    logger.warning(f"[Transcription WS] flush error: {e}")

    timer_task = asyncio.create_task(timer_loop())

    try:
        while True:
            msg = await websocket.receive()
            if "bytes" in msg and msg["bytes"]:
                buffer.extend(msg["bytes"])
            elif "text" in msg:
                import json
                try:
                    data = json.loads(msg["text"])
                except Exception:
                    continue
                if data.get("type") == "stop":
                    await flush_buffer()
                    break
    except WebSocketDisconnect:
        logger.info(f"[Transcription WS] {user_type}#{user_id} disconnected")
    except Exception as e:
        logger.error(f"[Transcription WS] Error: {e}")
    finally:
        running = False
        timer_task.cancel()
        # Flush remaining audio
        try:
            await flush_buffer()
        except Exception:
            pass
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close()
        logger.info(f"[Transcription WS] Cleaned up session {session_id} / {user_type}#{user_id}")
