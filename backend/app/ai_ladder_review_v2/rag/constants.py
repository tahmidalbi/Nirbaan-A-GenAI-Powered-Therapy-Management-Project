# ai_ladder_review_v2/rag/constants.py
from __future__ import annotations

# Keep these aligned with:
# - EmbeddingClient.model / expected_dim
# - TaxonomyChunk.embedding Vector(dim)
# - Your seed script

TAXONOMY_VERSION_DEFAULT = "1.1"

# Embedding model used for taxonomy chunks + query embedding
EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_DIM = 3072

# Retrieval defaults
DEFAULT_TOP_K = 6

# Always include this chunk (by exact title) in retrieval output.
# This guarantees structural + boundary rules are always present.
CORE_CHUNK_TITLE = "Core OCD Structural Model + Extraction Rules"

# Fallback: if for some reason core title changes, you can also enforce by tag.
CORE_CHUNK_TAG = "core"