import os
import tempfile
from pathlib import Path
from typing import Optional

from openai import OpenAI

class TranscriptionService:
    """Service for transcribing audio using OpenAI Whisper API."""
    
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        self.client = OpenAI(api_key=api_key)
        self.model = "whisper-1"
    
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
        try:
            kwargs = {
                "model": self.model,
                "file": audio_file,
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
