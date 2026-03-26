import os
from typing import Any, Dict, List

from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from openai import OpenAI


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-5.2")

PGVECTOR_CONNECTION = os.getenv("PGVECTOR_CONNECTION", os.getenv("DATABASE_URL", ""))
PGVECTOR_COLLECTION_NAME = os.getenv("PGVECTOR_COLLECTION_NAME", "therapist_kb")

# MMR tuning
RAG_TOP_K_DEFAULT = int(os.getenv("RAG_TOP_K_DEFAULT", "6"))
RAG_MMR_FETCH_K = int(os.getenv("RAG_MMR_FETCH_K", "20"))
RAG_MMR_LAMBDA = float(os.getenv("RAG_MMR_LAMBDA", "0.5"))


class RAGService:
    """RAG service using LangChain PGVector + retriever."""

    def __init__(self) -> None:
        if not PGVECTOR_CONNECTION:
            raise ValueError("PGVECTOR_CONNECTION (or DATABASE_URL) is not configured")

        self.embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
        self.vector_store = PGVector(
            embeddings=self.embeddings,
            collection_name=PGVECTOR_COLLECTION_NAME,
            connection=PGVECTOR_CONNECTION,
            use_jsonb=True,
        )

    def _build_filter(
        self,
        therapist_id: int,
        resource_id: int | None = None,
    ) -> Dict[str, Any]:
        filters: List[Dict[str, Any]] = [
            {"therapist_id": {"$eq": therapist_id}},
        ]

        if resource_id is not None:
            filters.append({"resource_id": {"$eq": resource_id}})

        if len(filters) == 1:
            return filters[0]

        return {"$and": filters}

    def retrieve_chunks(
        self,
        therapist_id: int,
        query: str,
        top_k: int = RAG_TOP_K_DEFAULT,
        resource_id: int | None = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant chunks via LangChain retriever using MMR.
        """
        metadata_filter = self._build_filter(
            therapist_id=therapist_id,
            resource_id=resource_id,
        )

        retriever = self.vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": top_k,
                "fetch_k": max(top_k, RAG_MMR_FETCH_K),
                "lambda_mult": RAG_MMR_LAMBDA,
                "filter": metadata_filter,
            },
        )

        docs = retriever.invoke(query)

        chunks: List[Dict[str, Any]] = []
        for doc in docs:
            metadata = dict(doc.metadata or {})
            chunks.append(
                {
                    "chunk_text": doc.page_content,
                    "resource_title": metadata.get("resource_title", "Untitled"),
                    "resource_id": metadata.get("resource_id"),
                    "similarity_score": 0.0,  # MMR retriever doesn't return score here
                    "metadata": metadata,
                }
            )

        return chunks

    def generate_answer(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not chunks:
            return {
                "answer": "I don't have enough information from the knowledge base to answer that.",
                "sources": [],
                "chunks_used": 0,
            }

        context_parts: List[str] = []
        for idx, chunk in enumerate(chunks, 1):
            title = chunk["resource_title"]
            metadata = chunk.get("metadata") or {}

            location_bits: List[str] = []
            if metadata.get("source_type"):
                location_bits.append(str(metadata["source_type"]))
            if metadata.get("page_start") and metadata.get("page_end"):
                if metadata["page_start"] == metadata["page_end"]:
                    location_bits.append(f"page {metadata['page_start']}")
                else:
                    location_bits.append(f"pages {metadata['page_start']}-{metadata['page_end']}")
            elif metadata.get("page_start"):
                location_bits.append(f"page {metadata['page_start']}")

            location_suffix = f" ({', '.join(location_bits)})" if location_bits else ""

            context_parts.append(
                f"[Source {idx}: {title}{location_suffix}]\n{chunk['chunk_text']}"
            )

        context_str = "\n\n---\n\n".join(context_parts)

        system_instruction = (
            "You are a knowledgeable therapy assistant helping therapists find information from their knowledge base.\n"
            "CRITICAL RULES:\n"
            "1. Answer ONLY using the provided sources.\n"
            "2. If the sources do not contain enough information, say exactly: "
            "'I don't have enough information from the knowledge base to answer that.'\n"
            "3. Do not invent facts.\n"
            "4. Cite source titles naturally in the answer when relevant.\n\n"
            "SOURCES:\n"
            f"{context_str}"
        )

        try:
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": query},
                ],
                temperature=0,
                max_completion_tokens=800,
            )

            answer = response.choices[0].message.content or ""

            sources = [
                {
                    "resource_title": chunk["resource_title"],
                    "resource_id": chunk["resource_id"],
                    "chunk_text": chunk["chunk_text"][:500],
                }
                for chunk in chunks
            ]

            return {
                "answer": answer,
                "sources": sources,
                "chunks_used": len(chunks),
            }

        except Exception as e:
            return {
                "answer": f"Error generating answer: {str(e)}",
                "sources": [],
                "chunks_used": 0,
            }


rag_service = RAGService()