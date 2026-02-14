import json
import os
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
from openai import OpenAI

# Initialize OpenAI client (OpenAI 2.x)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# CONFIGURATION
# GPT-5.2 standard embedding model
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
# GPT-5.2 is the correct model ID for the 2026 release
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-5.2")

class RAGService:
    """Retrieval-Augmented Generation service"""
    
    def _generate_query_embedding(self, query: str) -> List[float]:
        """Generate embedding for search query"""
        try:
            response = client.embeddings.create(
                input=[query],
                model=EMBEDDING_MODEL
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Embedding error: {e}")
            return []
    
    def retrieve_chunks(
        self,
        db: Session,
        therapist_id: int,
        query: str,
        top_k: int = 6
    ) -> List[Dict[str, Any]]:
        """
        Retrieve most relevant chunks using vector similarity
        """
        query_embedding = self._generate_query_embedding(query)
        
        if not query_embedding:
            return []
        
        # Format for pgvector: plain string representation of the list "[0.1, 0.2, ...]"
        embedding_str = f"[{','.join(f'{x:.8f}' for x in query_embedding)}]"
        
        # SQL Query
        # NOTE: used CAST(:query_embedding AS vector) to ensure type safety with binding
        sql = text("""
            SELECT 
                rc.chunk_text,
                r.title as resource_title,
                r.id as resource_id,
                1 - (rc.embedding <=> CAST(:query_embedding AS vector)) as similarity
            FROM resource_chunks rc
            JOIN resources r ON rc.resource_id = r.id
            WHERE rc.therapist_id = :therapist_id
                AND r.status = 'ready'
            ORDER BY rc.embedding <=> CAST(:query_embedding AS vector)
            LIMIT :top_k
        """)
        
        result = db.execute(
            sql,
            {
                "query_embedding": embedding_str,
                "therapist_id": therapist_id,
                "top_k": top_k
            }
        )
        
        chunks = []
        # FIX: Use .mappings() to safely access columns by name in SQLAlchemy 2.0+
        for row in result.mappings():
            chunks.append({
                "chunk_text": row['chunk_text'],
                "resource_title": row['resource_title'],
                "resource_id": row['resource_id'],
                "similarity_score": float(row['similarity'])
            })
        
        return chunks
    
    def generate_answer(
        self,
        query: str,
        chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate answer using retrieved chunks
        """
        if not chunks:
            return {
                "answer": "I don't have enough information to answer this question.",
                "sources": [],
                "chunks_used": 0
            }
        
        # Build context safely
        context_parts = []
        for idx, chunk in enumerate(chunks, 1):
            context_parts.append(
                f"[Source {idx}: {chunk['resource_title']}]\n{chunk['chunk_text']}"
            )
        
        context_str = "\n\n---\n\n".join(context_parts)
        
        # FIX: Do NOT use .format() on the system prompt if context contains curly braces.
        # Instead, inject the context via a formatted string literal or a separate message.
        system_instruction = (
            "You are a knowledgeable therapy assistant helping therapists find information from their knowledge base.\n"
            "CRITICAL RULES:\n"
            "1. Answer ONLY using information from the provided sources\n"
            "2. If sources don't contain the answer, say 'I don't have enough information'\n"
            "3. Cite sources by title\n"
            "SOURCES:\n"
            f"{context_str}" 
        )
        
        try:
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": query}
                ],
                temperature=0,
                # NOTE: GPT-5.2 supports 'max_completion_tokens' but 'max_tokens' still works for backward comp.
                max_completion_tokens=800
            )
            
            answer = response.choices[0].message.content
            
            sources = [
                {
                    "resource_title": chunk['resource_title'],
                    "resource_id": chunk['resource_id'],
                    "chunk_text": chunk['chunk_text'][:500]
                }
                for chunk in chunks
            ]
            
            return {
                "answer": answer,
                "sources": sources,
                "chunks_used": len(chunks)
            }
            
        except Exception as e:
            return {
                "answer": f"Error generating answer: {str(e)}",
                "sources": [],
                "chunks_used": 0
            }

# Singleton instance
rag_service = RAGService()