# app/erp/ERPCoach/llm/retry.py
from __future__ import annotations

import random
import time
from typing import Any, Callable, Dict, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

from app.erp.ERPCoach.llm.structured import StructuredModelConfig, build_structured_runnable

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class LLMRetryError(RuntimeError):
    pass


def _sleep_with_jitter(base_seconds: float) -> None:
    time.sleep(base_seconds + random.uniform(0, 0.25 * base_seconds))


def invoke_with_retries(
    runnable: Any,
    payload: Any,
    *,
    attempts: int = 3,
    base_backoff: float = 0.6,
) -> Any:
    """
    Generic retry wrapper for runnable.invoke(payload).

    Retries on transient exceptions (network/provider hiccups).
    """
    last_exc: Optional[Exception] = None
    for i in range(attempts):
        try:
            return runnable.invoke(payload)
        except Exception as e:
            last_exc = e
            if i < attempts - 1:
                _sleep_with_jitter(base_backoff * (2**i))
            continue
    raise LLMRetryError(f"LLM invoke failed after {attempts} attempts: {last_exc}") from last_exc


def repair_to_schema(
    *,
    llm: Any,
    schema: Type[SchemaT],
    bad_text: str,
    context: str = "",
    attempts: int = 2,
) -> SchemaT:
    """
    Uses a formatting-only call to coerce/repair bad output into the required schema.
    This is a common production pattern when strict JSON output fails.

    We ask the model to output ONLY a JSON object that matches the schema.
    """
    runnable = build_structured_runnable(
        llm,
        schema,
        config=StructuredModelConfig(method="function_calling"),
    )

    prompt = (
        "You are a strict JSON formatter.\n"
        "Return ONLY a JSON object that matches the required schema.\n"
        "Do not include markdown fences.\n"
    )
    if context.strip():
        prompt += f"\nContext:\n{context.strip()}\n"
    prompt += f"\nBad output to repair:\n{bad_text.strip()}\n"

    result = invoke_with_retries(
        runnable,
        prompt,
        attempts=attempts,
        base_backoff=0.6,
    )
    # When schema is Pydantic, LangChain returns an instance of that model
    return result