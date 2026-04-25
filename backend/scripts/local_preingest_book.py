import argparse
import os
from pathlib import Path
from datetime import datetime

from app.database.session import SessionLocal
from app.resources.models import Resource
from app.resources.tasks import DocumentProcessor, VectorStoreFactory


def safe_resource_kwargs(**kwargs):
    cols = Resource.__table__.columns.keys()
    return {k: v for k, v in kwargs.items() if k in cols}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Path to local PDF/TXT")
    parser.add_argument("--therapist-id", required=True, type=int)
    parser.add_argument("--title", required=True)
    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        raise FileNotFoundError(file_path)

    file_type = file_path.suffix.lower().replace(".", "")
    if file_type not in ["pdf", "txt"]:
        raise ValueError("Only pdf and txt supported")

    mime_type = "application/pdf" if file_type == "pdf" else "text/plain"
    now = datetime.utcnow()

    db = SessionLocal()

    try:
        resource = Resource(
            **safe_resource_kwargs(
                therapist_id=args.therapist_id,
                title=args.title,
                original_filename=file_path.name,
                r2_bucket=os.getenv("R2_BUCKET_NAME", "local-preingest"),
                r2_key=f"local-preingest/{file_path.name}",
                file_type=file_type,
                mime_type=mime_type,
                size_bytes=file_path.stat().st_size,
                source_url="local-preingest",
                status="processing",
                error_message=None,
                total_pages=0,
                total_chunks=0,
                created_at=now,
                updated_at=now,
            )
        )

        db.add(resource)
        db.commit()
        db.refresh(resource)

        print(f"Created resource_id={resource.id}")

        processor = DocumentProcessor()
        loaded_doc = processor.load_document(str(file_path), file_type)

        full_text = (loaded_doc.get("text") or "").strip()
        if not full_text:
            raise ValueError("No content extracted from document")

        if file_type == "pdf":
            page_spans = loaded_doc.get("page_spans") or []
            if hasattr(resource, "total_pages"):
                resource.total_pages = len(page_spans)

        chunks = processor.chunk_document(loaded_doc)
        if not chunks:
            raise ValueError("No chunks generated")

        if hasattr(resource, "total_chunks"):
            resource.total_chunks = len(chunks)

        db.commit()

        print(f"Generated {len(chunks)} chunks")

        vector_store = VectorStoreFactory.create()
        documents, ids = processor.to_langchain_documents(resource, chunks)
        vector_store.add_documents(documents=documents, ids=ids)

        resource.status = "ready"
        resource.error_message = None
        resource.updated_at = datetime.utcnow()

        db.commit()

        print("DONE: Local book pre-ingested successfully")

    except Exception as e:
        db.rollback()
        print("FAILED:", e)
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()