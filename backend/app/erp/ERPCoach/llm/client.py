# app/erp/ERPCoach/llm/client.py
from __future__ import annotations

import os
from typing import Any, Dict, Optional, Type, TypeVar

from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.erp.ERPCoach.llm.structured import StructuredModelConfig, build_structured_runnable
from app.erp.ERPCoach.llm.retry import invoke_with_retries, repair_to_schema

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class LLMClient:
    """
    Thin LangChain-based client for GPT-5.2 usage in ERPCoach.

    Design goals:
      - One place to control model + temperature
      - One place to enforce structured outputs
      - Built-in retry + optional repair pass
    """

    def __init__(
        self,
        *,
        model: Optional[str] = None,
        temperature: float = 0.2,
        timeout: int = 30,
        max_retries: int = 0,
    ) -> None:
        self.model = model or os.getenv("LLM_MODEL", "gpt-5.2")
        api_key = os.getenv("OPENAI_API_KEY")

        # ChatOpenAI reads OPENAI_API_KEY from env too, but we set explicitly if present.
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "temperature": temperature,
            "timeout": timeout,
            "max_retries": max_retries,  # we handle retries ourselves
        }
        if api_key:
            kwargs["api_key"] = api_key

        self.llm = ChatOpenAI(**kwargs)

    def structured_call(
        self,
        *,
        schema: Type[SchemaT],
        prompt: str,
        method: str = "function_calling",
        strict: bool = True,
        attempts: int = 3,
        repair_attempts: int = 1,
        repair_context: str = "",
    ) -> SchemaT:
        """
        Makes a structured call and returns an instance of `schema`.

        Flow:
          1) Try structured output via function_calling (supports Dict[str, Any] fields)
          2) Retry transient failures
          3) If still invalid/unexpected, do one repair pass
        """
        runnable = build_structured_runnable(
            self.llm,
            schema,
            config=StructuredModelConfig(method=method, strict=strict),
        )

        try:
            result = invoke_with_retries(
                runnable,
                prompt,
                attempts=attempts,
                base_backoff=0.6,
            )
            # result should already be a Pydantic model instance
            return result
        except Exception as e:
            if repair_attempts <= 0:
                raise

            # Last chance: ask model to repair into schema
            repaired = repair_to_schema(
                llm=self.llm,
                schema=schema,
                bad_text=str(e),
                context=repair_context or prompt,
                attempts=repair_attempts,
            )
            return repaired

    def text_call(
        self,
        *,
        prompt: str,
        attempts: int = 3,
    ) -> str:
        """
        Non-structured call (rarely needed in your pipeline).
        """
        result = invoke_with_retries(self.llm, prompt, attempts=attempts, base_backoff=0.6)
        # LangChain returns an AIMessage; str(...) yields content
        return getattr(result, "content", str(result))