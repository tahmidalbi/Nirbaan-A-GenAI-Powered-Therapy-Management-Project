# ai_ladder_review_v2/rag/embedding_client.py
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional

from openai import OpenAI


class EmbeddingClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class EmbeddingConfig:
    # Choose ONE model and keep it consistent with your DB Vector dimension.
    # If you change this model later, you must also migrate / re-embed.
    model: str = "text-embedding-3-large"

    # Optional safety: you can assert the expected vector length.
    # For text-embedding-3-large it's commonly 3072; for -3-small it's commonly 1536.
    expected_dim: Optional[int] = 3072


class EmbeddingClient:
    """
    Tiny wrapper around OpenAI embeddings.
    - Single responsibility: embed text -> vector
    - Ensures dimension consistency
    """

    def __init__(self, api_key: Optional[str] = None, config: Optional[EmbeddingConfig] = None):
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise EmbeddingClientError("OPENAI_API_KEY is not set.")
        self._client = OpenAI(api_key=api_key)
        self._config = config or EmbeddingConfig()

    @property
    def model(self) -> str:
        return self._config.model

    def embed_text(self, text: str) -> List[float]:
        if not text or not text.strip():
            raise EmbeddingClientError("Cannot embed empty text.")

        resp = self._client.embeddings.create(
            model=self._config.model,
            input=text,
        )
        vec = resp.data[0].embedding

        if self._config.expected_dim is not None and len(vec) != self._config.expected_dim:
            raise EmbeddingClientError(
                f"Embedding dimension mismatch: got {len(vec)}, expected {self._config.expected_dim}. "
                f"Check model vs DB Vector dimension."
            )

        return vec