import os
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.auth.utils import get_current_therapist
from app.therapists.models import Therapist
from app.resources.models import Resource, ResourceChunk, IngestionJob
from app.resources.schemas import (
    ResourceInitUploadRequest,
    ResourceInitUploadResponse,
    ResourceConfirmUploadResponse,
    ResourceStatusResponse,
    ResourceListItem,
    ResourceDeleteResponse,
    RAGSearchRequest,
    RAGSearchResponse,
    RAGAnswerRequest,
    RAGAnswerResponse,
    ChunkResult,
    SourceReference
)
from app.resources.r2_storage import r2_storage
from app.resources.rag_service import rag_service
from app.resources.tasks import ingest_resource_task

from app.resources.url_processor import url_processor
from app.resources.schemas import ResourceFromURLRequest
import tempfile

router = APIRouter(prefix="/resources", tags=["resources"])

# ============ FILE UPLOAD ENDPOINTS ============

@router.post("/init-upload", response_model=ResourceInitUploadResponse)
def init_upload(
    request: ResourceInitUploadRequest,
    db: Session = Depends(get_db),
    current_therapist: Therapist = Depends(get_current_therapist)
):
    """
    Step 1: Initialize upload - Create resource record and generate presigned R2 URL
    """
    # Validate file type
    if request.file_type not in ["pdf", "txt"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {request.file_type}"
        )
    
    # Create resource record
    resource = Resource(
        therapist_id=current_therapist.id,
        title=request.title,
        original_filename=request.filename,
        r2_bucket=os.getenv("R2_BUCKET_NAME"),
        r2_key="",  # Will set after generating
        file_type=request.file_type,
        mime_type=request.mime_type,
        size_bytes=request.size_bytes,
        status="initiated"
    )
    db.add(resource)
    db.flush()  # Get resource.id
    
    # Generate R2 key
    r2_key = r2_storage.generate_r2_key(
        therapist_id=current_therapist.id,
        resource_id=resource.id,
        filename=request.filename
    )
    resource.r2_key = r2_key
    
    # Generate presigned PUT URL for R2 (R2 doesn't support POST!)
    upload_url = r2_storage.generate_presigned_upload_url(
        r2_key=r2_key,
        file_type=request.mime_type
    )
    
    db.commit()
    
    return ResourceInitUploadResponse(
        resource_id=resource.id,
        upload_url=upload_url,
        r2_key=r2_key
    )

@router.post("/{resource_id}/confirm-upload", response_model=ResourceConfirmUploadResponse)
def confirm_upload(
    resource_id: int,
    db: Session = Depends(get_db),
    current_therapist: Therapist = Depends(get_current_therapist)
):
    """
    Step 2: Confirm upload - Verify R2 file exists and trigger async processing
    """
    # Get resource
    resource = db.query(Resource).filter(
        Resource.id == resource_id,
        Resource.therapist_id == current_therapist.id
    ).first()
    
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    
    if resource.status != "initiated":
        raise HTTPException(
            status_code=400,
            detail=f"Resource already processed or processing (status: {resource.status})"
        )
    
    # Verify file exists in R2
    exists, actual_size = r2_storage.verify_file_exists(resource.r2_key)
    
    if not exists:
        resource.status = "failed"
        resource.error_message = "File not found in R2 after upload"
        db.commit()
        raise HTTPException(
            status_code=400,
            detail="File upload verification failed - file not found in R2"
        )
    
    # Update resource
    resource.status = "uploaded"
    resource.size_bytes = actual_size
    
    # Create ingestion job
    job = IngestionJob(
        resource_id=resource.id,
        therapist_id=current_therapist.id,
        status="queued",
        progress=0
    )
    db.add(job)
    db.commit()
    
    # Trigger Celery task
    task = ingest_resource_task.delay(resource.id)
    
    # Store Celery task ID
    job.celery_task_id = task.id
    db.commit()
    
    return ResourceConfirmUploadResponse(
        resource_id=resource.id,
        job_id=job.id,
        status="queued",
        message="Document queued for processing"
    )

@router.get("/{resource_id}/status", response_model=ResourceStatusResponse)
def get_resource_status(
    resource_id: int,
    db: Session = Depends(get_db),
    current_therapist: Therapist = Depends(get_current_therapist)
):
    """
    Get resource processing status and progress
    """
    resource = db.query(Resource).filter(
        Resource.id == resource_id,
        Resource.therapist_id == current_therapist.id
    ).first()
    
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    
    # Get latest ingestion job
    job = db.query(IngestionJob).filter(
        IngestionJob.resource_id == resource_id
    ).order_by(IngestionJob.created_at.desc()).first()
    
    return ResourceStatusResponse(
        resource_id=resource.id,
        status=resource.status,
        progress=job.progress if job else None,
        current_step=job.current_step if job else None,
        total_chunks=resource.total_chunks,
        error_message=resource.error_message or (job.error_message if job else None),
        created_at=resource.created_at,
        updated_at=resource.updated_at
    )

# ============ RESOURCE MANAGEMENT ============

@router.get("", response_model=List[ResourceListItem])
def list_resources(
    db: Session = Depends(get_db),
    current_therapist: Therapist = Depends(get_current_therapist)
):
    """
    List all resources for current therapist
    """
    resources = db.query(Resource).filter(
        Resource.therapist_id == current_therapist.id
    ).order_by(Resource.created_at.desc()).all()
    
    return [ResourceListItem.model_validate(r) for r in resources]

@router.delete("/{resource_id}", response_model=ResourceDeleteResponse)
def delete_resource(
    resource_id: int,
    db: Session = Depends(get_db),
    current_therapist: Therapist = Depends(get_current_therapist)
):
    """
    Delete resource (R2 file + database records)
    """
    resource = db.query(Resource).filter(
        Resource.id == resource_id,
        Resource.therapist_id == current_therapist.id
    ).first()
    
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    
    # Delete from R2
    try:
        r2_storage.delete_file(resource.r2_key)
    except Exception as e:
        # Log but don't fail - might already be deleted
        print(f"R2 deletion warning: {e}")
    
    # Delete from database (cascades to chunks and jobs)
    db.delete(resource)
    db.commit()
    
    return ResourceDeleteResponse(
        message="Resource deleted successfully",
        resource_id=resource_id
    )

@router.post("/from-url", response_model=ResourceConfirmUploadResponse)
def create_resource_from_url(
    request: ResourceFromURLRequest,
    db: Session = Depends(get_db),
    current_therapist: Therapist = Depends(get_current_therapist)
):
    """
    Create resource from web URL (blog, article, webpage)
    """
    try:
        # Fetch content from URL
        fetched_title, content = url_processor.fetch_url_content(request.url)

        # Use provided title or fetched title
        final_title = request.title or fetched_title

        # Create resource record
        resource = Resource(
            therapist_id=current_therapist.id,
            title=final_title,
            original_filename=f"{request.resource_type}_from_url.txt",
            r2_bucket=os.getenv("R2_BUCKET_NAME"),
            r2_key="",
            file_type="txt",
            mime_type="text/plain",
            size_bytes=len(content.encode("utf-8")),
            status="uploaded",
        )
        db.add(resource)
        db.flush()  # get resource.id

        # Generate R2 key
        r2_key = r2_storage.generate_r2_key(
            therapist_id=current_therapist.id,
            resource_id=resource.id,
            filename=f"{request.resource_type}_{resource.id}.txt",
        )
        resource.r2_key = r2_key

        # Save content to temp file
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            delete=False,
            encoding="utf-8",
        ) as tmp:
            tmp.write(content)
            temp_path = tmp.name

        try:
            # Upload to R2
            r2_storage.s3_client.upload_file(
                temp_path,
                r2_storage.bucket_name,
                r2_key,
                ExtraArgs={"ContentType": "text/plain"},
            )
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

        # Create ingestion job
        job = IngestionJob(
            resource_id=resource.id,
            therapist_id=current_therapist.id,
            status="queued",
            progress=0,
        )
        db.add(job)
        db.commit()

        # Trigger Celery task
        task = ingest_resource_task.delay(resource.id)
        job.celery_task_id = task.id
        db.commit()

        return ResourceConfirmUploadResponse(
            resource_id=resource.id,
            job_id=job.id,
            status="queued",
            message=f"Content from URL queued for processing ({len(content)} characters extracted)",
        )

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to process URL: {str(e)}",
        )

# ============ RAG ENDPOINTS ============

@router.post("/rag/search", response_model=RAGSearchResponse)
def search_knowledge_base(
    request: RAGSearchRequest,
    db: Session = Depends(get_db),
    current_therapist: Therapist = Depends(get_current_therapist)
):
    """
    Search knowledge base using vector similarity
    """
    chunks = rag_service.retrieve_chunks(
        db=db,
        therapist_id=current_therapist.id,
        query=request.query,
        top_k=request.top_k
    )
    
    return RAGSearchResponse(
        query=request.query,
        chunks=[ChunkResult(**chunk) for chunk in chunks],
        total_results=len(chunks)
    )

@router.post("/rag/answer", response_model=RAGAnswerResponse)
def generate_answer(
    request: RAGAnswerRequest,
    db: Session = Depends(get_db),
    current_therapist: Therapist = Depends(get_current_therapist)
):
    """
    Generate RAG answer with citations
    """
    try:
        # Retrieve chunks
        chunks = rag_service.retrieve_chunks(
            db=db,
            therapist_id=current_therapist.id,
            query=request.query,
            top_k=request.top_k
        )
        
        # Generate answer
        result = rag_service.generate_answer(
            query=request.query,
            chunks=chunks
        )
        
        return RAGAnswerResponse(
            query=request.query,
            answer=result["answer"],
            sources=[SourceReference(**src) for src in result["sources"]],
            chunks_used=result["chunks_used"]
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG error: {str(e)}"
        )