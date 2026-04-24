FROM python:3.11-slim

WORKDIR /app

# System deps:
#   libpq-dev   → psycopg2-binary build
#   libgomp1    → onnxruntime used by piper-tts
#   wget        → download voice model at build time
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libgomp1 \
        libmagic1 \
        wget \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (own layer for cache efficiency)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download Piper voice model (git-ignored, fetched at build time)
RUN mkdir -p app/ERPScriptGenerator/voices \
    && wget -q -O app/ERPScriptGenerator/voices/en_US-lessac-medium.onnx \
        "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx" \
    && wget -q -O app/ERPScriptGenerator/voices/en_US-lessac-medium.onnx.json \
        "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json"

# Create audio output directory
RUN mkdir -p media/imaginal_audio

# Copy application source
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
