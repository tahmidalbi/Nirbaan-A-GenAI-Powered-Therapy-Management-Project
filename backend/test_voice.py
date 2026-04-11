import os
import sounddevice as sd
import numpy as np
import tempfile
from scipy.io.wavfile import write
from openai import OpenAI

# ===== CONFIG =====
GROQ_API_KEY = "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"

client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

# =========================
# 🎤 RECORD FROM MIC
# =========================
def record_audio(duration=5, sample_rate=16000):
    print(f"\n🎤 Recording for {duration} seconds... Speak now!")

    recording = sd.rec(int(duration * sample_rate),
                       samplerate=sample_rate,
                       channels=1,
                       dtype='int16')

    sd.wait()
    print("✅ Recording complete")

    return recording, sample_rate


# =========================
# 🎤 STT TEST (MIC → TEXT)
# =========================
def test_stt_from_mic():
    print("\n🎤 Testing STT from microphone...")

    try:
        audio_data, sr = record_audio()

        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            write(tmp.name, sr, audio_data)
            temp_path = tmp.name

        with open(temp_path, "rb") as f:
            transcription = client.audio.transcriptions.create(
                model="whisper-large-v3-turbo",
                file=f
            )

        print("✅ STT SUCCESS")
        print("Transcript:", transcription.text)

    except Exception as e:
        print("❌ STT FAILED:", str(e))


# =========================
# 🔊 TTS TEST
# =========================
def test_tts():
    print("\n🔊 Testing TTS...")

    try:
        response = client.audio.speech.create(
            model="canopylabs/orpheus-v1-english",
            voice="hannah",
            input="Hello, this is a live microphone test of your ERP voice system.",
            response_format="wav"
        )

        with open("output.wav", "wb") as f:
            f.write(response.read())

        print("✅ TTS SUCCESS")
        print("Saved as output.wav")

    except Exception as e:
        print("❌ TTS FAILED:", str(e))


# =========================
# 🚀 RUN TESTS
# =========================
if __name__ == "__main__":
    test_stt_from_mic()
    test_tts()