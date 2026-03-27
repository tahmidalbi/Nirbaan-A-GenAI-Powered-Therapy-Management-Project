from __future__ import annotations

from typing import TypedDict


class ImaginalGraphState(TypedDict, total=False):
    thread_id: str
    run_id: int
    patient_id: int
    therapist_id: int
    erp_item_id: int

    obsession: str
    compulsion: str
    feared_consequence: str
    script_intensity: str
    exposure_type: str
    subtype: str | None

    prompt_text: str
    generated_script: str
    version_no: int

    therapist_feedback: str | None
    approved: bool | None

    audio_path: str | None
    approved_script_id: int | None

    status: str