
import os
import tempfile
import json
from typing import List, Dict, Any
from datetime import datetime

from celery import Task
from sqlalchemy.orm import Session
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from openai import OpenAI

from app.core.celery_app import celery_app
from app.database.session import SessionLocal
from app.resources.models import Resource, ResourceChunk, IngestionJob
from app.resources.r2_storage import r2_storage

# OpenAI Configuration
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
MAX_CHUNK_SIZE = int(os.getenv("MAX_CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))


class DocumentProcessor:
    """Process documents: extract text, chunk, embed"""
    
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=MAX_CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    def load_document(self, file_path: str, file_type: str) -> List[Dict[str, Any]]:
        """Load document and extract text with metadata"""
        if file_type == "pdf":
            loader = PyPDFLoader(file_path)
            pages = loader.load()
            return [
                {
                    "text": page.page_content,
                    "metadata": {"page": page.metadata.get("page", i + 1)}
                }
                for i, page in enumerate(pages)
            ]
        elif file_type == "txt":
            loader = TextLoader(file_path, encoding="utf-8")
            docs = loader.load()
            return [{"text": doc.page_content, "metadata": {}} for doc in docs]
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
    
    def chunk_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Split documents into chunks with metadata"""
        chunks = []
        for doc in documents:
            text_chunks = self.text_splitter.split_text(doc["text"])
            for chunk_text in text_chunks:
                chunks.append({
                    "text": chunk_text,
                    "metadata": doc["metadata"]
                })
        return chunks
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for text chunks (batch processing)"""
        # OpenAI allows up to 2048 inputs per request
        batch_size = 100
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = client.embeddings.create(
                input=batch,
                model=EMBEDDING_MODEL
            )
            embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(embeddings)
        
        return all_embeddings


@celery_app.task(bind=True, name="ingest_resource_task")
def ingest_resource_task(self: Task, resource_id: int):
    """
    Main ingestion task: download → extract → chunk → embed → store
    
    CRITICAL: Uses own DB session, enforces therapist ownership
    """
    db: Session = SessionLocal()
    
    try:
        # Step 1: Load resource and job (with ownership check)
        resource = db.query(Resource).filter(Resource.id == resource_id).first()
        if not resource:
            raise ValueError(f"Resource {resource_id} not found")
        
        job = db.query(IngestionJob).filter(
            IngestionJob.resource_id == resource_id
        ).order_by(IngestionJob.created_at.desc()).first()
        
        if not job:
            raise ValueError(f"No ingestion job found for resource {resource_id}")
        
        # Update job status
        job.status = "running"
        job.started_at = datetime.utcnow()
        job.progress = 0
        job.current_step = "Downloading from R2..."
        db.commit()
        
        resource.status = "processing"
        db.commit()
        
        # Step 2: Download file from R2 to temp location
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{resource.file_type}") as tmp_file:
            temp_path = tmp_file.name
        
        try:
            r2_storage.download_file(resource.r2_key, temp_path)
            
            job.progress = 10
            job.current_step = "Extracting text..."
            db.commit()
            
            # Step 3: Load and extract text
            processor = DocumentProcessor()
            documents = processor.load_document(temp_path, resource.file_type)
            
            if not documents:
                raise ValueError("No content extracted from document")
            
            # Update total pages for PDFs
            if resource.file_type == "pdf":
                resource.total_pages = len(documents)
                db.commit()
            
            job.progress = 30
            job.current_step = "Chunking text..."
            db.commit()
            
            # Step 4: Chunk documents
            chunks = processor.chunk_documents(documents)
            
            if not chunks:
                raise ValueError("No chunks generated from document")
            
            resource.total_chunks = len(chunks)
            db.commit()
            
            job.progress = 50
            job.current_step = f"Generating embeddings for {len(chunks)} chunks..."
            db.commit()
            
            # Step 5: Generate embeddings (batch)
            chunk_texts = [chunk["text"] for chunk in chunks]
            embeddings = processor.generate_embeddings(chunk_texts)
            
            job.progress = 80
            job.current_step = "Storing chunks in database..."
            db.commit()
            
            # Step 6: Bulk insert chunks (IMPORTANT: Use resource.therapist_id for security)
            chunk_objects = []
            for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                chunk_obj = ResourceChunk(
                    resource_id=resource.id,
                    therapist_id=resource.therapist_id,  # Enforce ownership!
                    chunk_index=idx,
                    chunk_text=chunk["text"],
                    metadata_=chunk["metadata"],  # Now stored as JSONB
                    embedding=embedding
                )
                chunk_objects.append(chunk_obj)
            
            db.bulk_save_objects(chunk_objects)
            db.commit()
            
            # Step 7: Mark as complete
            resource.status = "ready"
            resource.error_message = None
            db.commit()
            
            job.status = "completed"
            job.progress = 100
            job.current_step = "Completed successfully"
            job.completed_at = datetime.utcnow()
            job.log = f"Processed {len(chunks)} chunks successfully"
            db.commit()
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    except Exception as e:
        # Handle errors
        error_msg = str(e)
        
        if resource:
            resource.status = "failed"
            resource.error_message = error_msg
            db.commit()
        
        if job:
            job.status = "failed"
            job.error_message = error_msg
            job.completed_at = datetime.utcnow()
            db.commit()
        
        # Re-raise for Celery retry logic
        raise
    
    finally:
        db.close()