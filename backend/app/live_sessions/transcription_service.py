import os
import logging
import tempfile
from pathlib import Path
from typing import Optional

from openai import OpenAI

logger = logging.getLogger(__name__)

# Domain-specific prompt for Whisper — improves accuracy for therapy vocabulary.
# Whisper uses this as prior context to bias towards these words/phrases.
THERAPY_WHISPER_PROMPT = (
    "OCD, ERP, exposure and response prevention, fear ladder, SUDS, anxiety, "
    "obsession, compulsion, avoidance, ritual, homework homework, trigger, "
    "intrusive thoughts, distress, habituation, therapist, patient, "
    "cognitive behavioral therapy, rumination, reassurance seeking, "
    "psychoeducation, neutralizing, checking, contamination, harm, "
    "uncertainty, coping strategy, relaxation, mindfulness."
)


class TranscriptionService:
    """Service for transcribing audio using OpenAI Whisper API."""
    
    def __init__(self):
        self.model = "whisper-1"
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.client = OpenAI(api_key=api_key)
            logger.info("TranscriptionService initialized with OpenAI API key")
        else:
            self.client = None
            logger.warning("OPENAI_API_KEY not set — transcription will be disabled")
    
    @property
    def is_available(self) -> bool:
        return self.client is not None
    
    def transcribe_audio(
        self, 
        audio_file,
        language: Optional[str] = None,
        prompt: Optional[str] = None
    ) -> dict:
        """
        Transcribe audio file using OpenAI Whisper API.
        
        Args:
            audio_file: File-like object or path to audio file
            language: Optional language code (e.g., 'en', 'es')
            prompt: Optional prompt to guide transcription
            
        Returns:
            Dictionary with transcription results
        """
        if not self.is_available:
            return {"text": "", "success": False, "error": "OPENAI_API_KEY not configured"}
        try:
            kwargs = {
                "model": self.model,
                "file": audio_file,
                "temperature": 0,   # more deterministic
            }
            
            if language:
                kwargs["language"] = language
            
            if prompt:
                kwargs["prompt"] = prompt
            
            response = self.client.audio.transcriptions.create(**kwargs)
            
            return {
                "text": response.text,
                "success": True
            }
        except Exception as e:
            return {
                "text": "",
                "success": False,
                "error": str(e)
            }
    
    def transcribe_audio_bytes(
        self,
        audio_bytes: bytes,
        filename: str = "audio.webm",
        language: Optional[str] = None,
        prompt: Optional[str] = None
    ) -> dict:
        """
        Transcribe audio from bytes using a temporary file.
        
        Args:
            audio_bytes: Audio file bytes
            filename: Filename with extension (determines format)
            language: Optional language code
            prompt: Optional prompt to guide transcription
            
        Returns:
            Dictionary with transcription results
        """
        # Create temporary file
        suffix = Path(filename).suffix or ".webm"
        
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
            temp_file.write(audio_bytes)
            temp_path = temp_file.name
        
        try:
            # Open and transcribe
            with open(temp_path, "rb") as audio_file:
                result = self.transcribe_audio(
                    audio_file,
                    language=language,
                    prompt=prompt
                )
            return result
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except Exception:
                pass


# Global instance
transcription_service = TranscriptionService()
