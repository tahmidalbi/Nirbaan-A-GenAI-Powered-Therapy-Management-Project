from __future__ import annotations

import os
import subprocess
from pathlib import Path
from uuid import uuid4

from .config import settings

# Resolve model path as absolute so it works regardless of cwd.
# If the config value is already absolute, Path() keeps it as-is.
# If relative, resolve it relative to this file's directory first;
# fall back to cwd-relative so an explicit override still works.
_MODEL_PATH_RAW = settings.PIPER_MODEL_PATH
_MODEL_PATH = (
    Path(_MODEL_PATH_RAW)
    if Path(_MODEL_PATH_RAW).is_absolute()
    else (Path(__file__).parent.parent.parent / _MODEL_PATH_RAW).resolve()
)
# voices/ lives right next to piper_tts.py — prefer that absolute path
_VOICES_DIR = Path(__file__).parent / "voices"
_DEFAULT_VOICE = _VOICES_DIR / "en_US-lessac-medium.onnx"
RESOLVED_MODEL_PATH = str(_DEFAULT_VOICE if _DEFAULT_VOICE.exists() else _MODEL_PATH)


def ensure_output_dir() -> None:
    # Resolve output dir relative to backend/ (parent of app/)
    out = Path(settings.PIPER_OUTPUT_DIR)
    if not out.is_absolute():
        out = Path(__file__).parent.parent.parent / settings.PIPER_OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    return str(out)


def prepare_text_for_audio(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = text.replace("\n", "\n\n")
    return text.strip()


def synthesize_with_piper(text: str) -> str:
    output_dir = ensure_output_dir()
    output_name = f"{uuid4().hex}.wav"
    output_path = os.path.join(output_dir, output_name)

    prepared = prepare_text_for_audio(text)

    cmd = [
        "piper",
        "--model",
        RESOLVED_MODEL_PATH,
        "--output_file",
        output_path,
        "--length_scale",
        "1.08",
    ]

    proc = subprocess.run(
        cmd,
        input=prepared.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    if proc.returncode != 0:
        raise RuntimeError(
            f"Piper failed with code {proc.returncode}: {proc.stderr.decode('utf-8', errors='ignore')}"
        )

    return output_path