# app/erp/ERPCoach/llm/structured.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Type, TypeVar, Union, cast

from pydantic import BaseModel

SchemaT = TypeVar("SchemaT", bound=BaseModel)


@dataclass(frozen=True)
class StructuredModelConfig:
    """
    Controls how we ask the model for structured outputs.

    method:
      - "function_calling": OpenAI function calling (default; supports Dict[str, Any] fields)
      - "json_schema": OpenAI native strict structured outputs (requires no additionalProperties)
      - "json_mode": fallback (not strict), only if you want it as last resort
    """
    method: str = "function_calling"
    strict: bool = True  # OpenAI strict schema adherence (when supported)


def build_structured_runnable(
    llm: Any,
    schema: Type[SchemaT],
    *,
    config: Optional[StructuredModelConfig] = None,
) -> Any:
    """
    Returns an LLM runnable that outputs `schema`.

    Prefer OpenAI native structured outputs:
      llm.with_structured_output(MySchema, method="json_schema")

    Falls back to function calling if json_schema errors.
    """
    cfg = config or StructuredModelConfig()

    # Primary path: OpenAI native structured outputs
    if cfg.method == "json_schema":
        try:
            # Some LangChain versions accept strict=... for json_schema;
            # if not supported, it will raise TypeError -> fallback.
            return llm.with_structured_output(schema, method="json_schema", strict=cfg.strict)
        except TypeError:
            # strict argument not supported in this version
            return llm.with_structured_output(schema, method="json_schema")
        except Exception:
            # schema/provider incompatibility -> fallback
            return llm.with_structured_output(schema, method="function_calling")

    # Fallback path
    if cfg.method == "function_calling":
        return llm.with_structured_output(schema, method="function_calling")

    # Last resort (non-strict) JSON mode
    # NOTE: Not guaranteed strict schema adherence.
    return llm.with_structured_output(schema, method="json_mode")


def schema_to_json_schema(schema: Type[BaseModel]) -> Dict[str, Any]:
    """
    Returns a JSON Schema dict from a Pydantic v2 model.
    Useful for debugging/logging or custom enforcement.
    """
    return cast(Dict[str, Any], schema.model_json_schema())