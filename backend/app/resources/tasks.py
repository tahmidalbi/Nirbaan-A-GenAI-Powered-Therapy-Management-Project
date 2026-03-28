import os
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from celery import Task
from sqlalchemy.orm import Session

from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_openai import OpenAIEmbeddings
from langchain_experimental.text_splitter import SemanticChunker
from langchain_postgres import PGVector

from app.core.celery_app import celery_app
from app.database.session import SessionLocal
from app.resources.models import Resource, IngestionJob
from app.resources.r2_storage import r2_storage


EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")

# LangChain PGVector requires psycopg3-style connection string, e.g.
# postgresql+psycopg://user:password@host:5432/dbname
PGVECTOR_CONNECTION = os.getenv("PGVECTOR_CONNECTION", os.getenv("DATABASE_URL", ""))

# Use a single collection and isolate tenants via metadata filter.
PGVECTOR_COLLECTION_NAME = os.getenv("PGVECTOR_COLLECTION_NAME", "therapist_kb")

SEMANTIC_CHUNK_BREAKPOINT_TYPE = os.getenv(
    "SEMANTIC_CHUNK_BREAKPOINT_TYPE",
    "percentile",
)
SEMANTIC_CHUNK_BREAKPOINT_AMOUNT = float(
    os.getenv("SEMANTIC_CHUNK_BREAKPOINT_AMOUNT", "90")
)

PDF_PAGE_SEPARATOR = "\n\n"


class VectorStoreFactory:
    @staticmethod
    def create() -> PGVector:
        if not PGVECTOR_CONNECTION:
            raise ValueError("PGVECTOR_CONNECTION (or DATABASE_URL) is not configured")

        embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)

        return PGVector(
            embeddings=embeddings,
            collection_name=PGVECTOR_COLLECTION_NAME,
            connection=PGVECTOR_CONNECTION,
            use_jsonb=True,
        )


class DocumentProcessor:
    """
    Load documents, concatenate PDFs into one long text for better semantic flow,
    estimate page spans, chunk semantically, then convert to LangChain Documents.
    """

    def __init__(self) -> None:
        self.embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
        self.text_splitter = SemanticChunker(
            embeddings=self.embeddings,
            breakpoint_threshold_type=SEMANTIC_CHUNK_BREAKPOINT_TYPE,
            breakpoint_threshold_amount=SEMANTIC_CHUNK_BREAKPOINT_AMOUNT,
        )

    def load_document(self, file_path: str, file_type: str) -> Dict[str, Any]:
        if file_type == "pdf":
            return self._load_pdf_as_single_text(file_path)

        if file_type == "txt":
            loader = TextLoader(file_path, encoding="utf-8")
            docs = loader.load()
            full_text = "\n\n".join((doc.page_content or "").strip() for doc in docs).strip()
            return {
                "text": full_text,
                "metadata": {"source_type": "txt"},
                "page_spans": None,
            }

        raise ValueError(f"Unsupported file type: {file_type}")

    def _load_pdf_as_single_text(self, file_path: str) -> Dict[str, Any]:
        loader = PyPDFLoader(file_path)
        pages = loader.load()

        if not pages:
            return {
                "text": "",
                "metadata": {"source_type": "pdf"},
                "page_spans": [],
            }

        text_parts: List[str] = []
        page_spans: List[Dict[str, int]] = []

        cursor = 0
        for i, page in enumerate(pages):
            page_text = (page.page_content or "").strip()
            if not page_text:
                continue

            if text_parts:
                text_parts.append(PDF_PAGE_SEPARATOR)
                cursor += len(PDF_PAGE_SEPARATOR)

            start = cursor
            text_parts.append(page_text)
            cursor += len(page_text)
            end = cursor

            raw_page_num = page.metadata.get("page", i + 1)
            try:
                page_num = int(raw_page_num)
            except Exception:
                page_num = i + 1

            if page_num == i:
                page_num = i + 1

            page_spans.append(
                {
                    "page": page_num,
                    "start": start,
                    "end": end,
                }
            )

        full_text = "".join(text_parts).strip()

        return {
            "text": full_text,
            "metadata": {"source_type": "pdf"},
            "page_spans": page_spans,
        }

    def chunk_document(self, loaded_doc: Dict[str, Any]) -> List[Dict[str, Any]]:
        full_text = (loaded_doc.get("text") or "").strip()
        base_metadata = loaded_doc.get("metadata", {}) or {}
        page_spans = loaded_doc.get("page_spans")

        if not full_text:
            return []

        docs = self.text_splitter.create_documents(
            texts=[full_text],
            metadatas=[base_metadata],
        )

        chunks: List[Dict[str, Any]] = []
        search_start = 0

        for doc in docs:
            chunk_text = (doc.page_content or "").strip()
            if not chunk_text:
                continue

            chunk_start, chunk_end = self._find_chunk_span(
                full_text=full_text,
                chunk_text=chunk_text,
                search_start=search_start,
            )
            search_start = max(search_start, chunk_end)

            metadata = dict(doc.metadata or {})
            if page_spans:
                page_start, page_end = self._estimate_page_range(
                    chunk_start=chunk_start,
                    chunk_end=chunk_end,
                    page_spans=page_spans,
                )
                if page_start is not None:
                    metadata["page_start"] = page_start
                if page_end is not None:
                    metadata["page_end"] = page_end

            chunks.append(
                {
                    "text": chunk_text,
                    "metadata": metadata,
                }
            )

        return chunks

    def _find_chunk_span(
        self,
        full_text: str,
        chunk_text: str,
        search_start: int,
    ) -> Tuple[int, int]:
        idx = full_text.find(chunk_text, search_start)
        if idx == -1:
            idx = full_text.find(chunk_text)
        if idx == -1:
            idx = search_start
        return idx, idx + len(chunk_text)

    def _estimate_page_range(
        self,
        chunk_start: int,
        chunk_end: int,
        page_spans: List[Dict[str, int]],
    ) -> Tuple[Optional[int], Optional[int]]:
        overlapping_pages: List[int] = []

        for span in page_spans:
            page_start = span["start"]
            page_end = span["end"]

            overlap_start = max(chunk_start, page_start)
            overlap_end = min(chunk_end, page_end)

            if overlap_start < overlap_end:
                overlapping_pages.append(span["page"])

        if not overlapping_pages:
            return None, None

        return min(overlapping_pages), max(overlapping_pages)

    def to_langchain_documents(
        self,
        resource: Resource,
        chunks: List[Dict[str, Any]],
    ) -> tuple[List[Document], List[str]]:
        documents: List[Document] = []
        ids: List[str] = []

        for idx, chunk in enumerate(chunks):
            metadata = dict(chunk["metadata"])
            metadata.update(
                {
                    "therapist_id": resource.therapist_id,
                    "resource_id": resource.id,
                    "resource_title": resource.title,
                    "file_type": resource.file_type,
                    "chunk_index": idx,
                }
            )

            documents.append(
                Document(
                    page_content=chunk["text"],
                    metadata=metadata,
                )
            )
            ids.append(f"resource-{resource.id}-chunk-{idx}")

        return documents, ids


@celery_app.task(bind=True, name="ingest_resource_task")
def ingest_resource_task(self: Task, resource_id: int):
    """
    Main ingestion task:
    download -> extract -> semantic chunk -> add_documents to LangChain PGVector
    """
    db: Session = SessionLocal()
    resource: Optional[Resource] = None
    job: Optional[IngestionJob] = None

    try:
        resource = db.query(Resource).filter(Resource.id == resource_id).first()
        if not resource:
            raise ValueError(f"Resource {resource_id} not found")

        job = (
            db.query(IngestionJob)
            .filter(IngestionJob.resource_id == resource_id)
            .order_by(IngestionJob.created_at.desc())
            .first()
        )
        if not job:
            raise ValueError(f"No ingestion job found for resource {resource_id}")

        job.status = "running"
        job.started_at = datetime.utcnow()
        job.progress = 0
        job.current_step = "Downloading from R2..."
        db.commit()

        resource.status = "processing"
        db.commit()

        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{resource.file_type}") as tmp_file:
            temp_path = tmp_file.name

        try:
            r2_storage.download_file(resource.r2_key, temp_path)

            job.progress = 10
            job.current_step = "Extracting text..."
            db.commit()

            processor = DocumentProcessor()
            loaded_doc = processor.load_document(temp_path, resource.file_type)

            full_text = (loaded_doc.get("text") or "").strip()
            if not full_text:
                raise ValueError("No content extracted from document")

            if resource.file_type == "pdf":
                page_spans = loaded_doc.get("page_spans") or []
                resource.total_pages = len(page_spans)
                db.commit()

            job.progress = 35
            job.current_step = "Semantic chunking document..."
            db.commit()

            chunks = processor.chunk_document(loaded_doc)
            if not chunks:
                raise ValueError("No chunks generated from document")

            resource.total_chunks = len(chunks)
            db.commit()

            job.progress = 65
            job.current_step = f"Indexing {len(chunks)} chunks into vector store..."
            db.commit()

            vector_store = VectorStoreFactory.create()
            documents, ids = processor.to_langchain_documents(resource, chunks)

            # LangChain docs state add_documents with matching IDs overwrites existing docs.
            vector_store.add_documents(documents=documents, ids=ids)

            job.progress = 90
            job.current_step = "Finalizing..."
            db.commit()

            resource.status = "ready"
            resource.error_message = None
            db.commit()

            job.status = "completed"
            job.progress = 100
            job.current_step = "Completed successfully"
            job.completed_at = datetime.utcnow()
            job.log = (
                f"Processed {len(chunks)} chunks successfully with "
                f"LangChain PGVector semantic indexing"
            )
            db.commit()

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    except Exception as e:
        error_msg = str(e)

        if resource is not None:
            resource.status = "failed"
            resource.error_message = error_msg
            db.commit()

        if job is not None:
            job.status = "failed"
            job.error_message = error_msg
            job.completed_at = datetime.utcnow()
            db.commit()

        raise

    finally:
        db.close()
