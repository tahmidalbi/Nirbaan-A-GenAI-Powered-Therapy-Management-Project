
import json
import os
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
from openai import OpenAI

from app.resources.models import ResourceChunk, Resource

# Initialize OpenAI client (OpenAI 2.x)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

class RAGService:
    """Retrieval-Augmented Generation service"""
    
    def _generate_query_embedding(self, query: str) -> List[float]:
        """Generate embedding for search query"""
        response = client.embeddings.create(
            input=[query],
            model=EMBEDDING_MODEL
        )
        return response.data[0].embedding
    
    def retrieve_chunks(
        self,
        db: Session,
        therapist_id: int,
        query: str,
        top_k: int = 6
    ) -> List[Dict[str, Any]]:
        """
        Retrieve most relevant chunks using vector similarity
        
        Returns:
            List of dicts with chunk_text, resource_title, similarity_score
        """
        # Embed the query
        query_embedding = self._generate_query_embedding(query)
        
        # Format embedding for SQL (proper vector literal format)
        embedding_str = "[" + ",".join(f"{x:.8f}" for x in query_embedding) + "]"
        
        # Vector similarity search with pgvector (cosine distance)
        # Uses ivfflat index created in migrations
        # NOTE: Using CAST() instead of :: for bind parameter compatibility
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
        for row in result:
            chunks.append({
                "chunk_text": row.chunk_text,
                "resource_title": row.resource_title,
                "resource_id": row.resource_id,
                "similarity_score": float(row.similarity)
            })
        
        return chunks
    
    def generate_answer(
        self,
        query: str,
        chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate answer using retrieved chunks
        
        Returns:
            {
                answer: str,
                sources: List[{resource_title, chunk_text}],
                chunks_used: int
            }
        """
        if not chunks:
            return {
                "answer": "I don't have enough information in the knowledge base to answer this question.",
                "sources": [],
                "chunks_used": 0
            }
        
        # Build context from chunks
        context_parts = []
        for idx, chunk in enumerate(chunks, 1):
            context_parts.append(
                f"[Source {idx}: {chunk['resource_title']}]\\n{chunk['chunk_text']}"
            )
        
        context = "\\n\\n---\\n\\n".join(context_parts)
        
        # System prompt
        system_prompt = """You are a knowledgeable therapy assistant helping therapists find information from their knowledge base.

CRITICAL RULES:
1. Answer ONLY using information from the provided sources
2. If sources don't contain the answer, say "I don't have enough information to answer this question"
3. Always cite your sources by mentioning the resource title
4. Be concise, clear, and professional
5. Do NOT make up or infer information beyond what's in the sources
6. If multiple sources support a claim, mention all relevant titles

SOURCES:
{context}"""
        
        # Generate answer using OpenAI
        try:
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt.format(context=context)},
                    {"role": "user", "content": query}
                ],
                temperature=0,
                max_tokens=800
            )
            
            answer = response.choices[0].message.content
            
            # Extract sources for frontend display
            sources = [
                {
                    "resource_title": chunk['resource_title'],
                    "resource_id": chunk['resource_id'],
                    "chunk_text": chunk['chunk_text'][:500]  # First 500 chars
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