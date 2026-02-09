
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List, Dict, Any

# Resource Schemas
class ResourceInitUploadRequest(BaseModel):
    """Request to initialize upload"""
    title: str = Field(..., min_length=1, max_length=500)
    filename: str = Field(..., min_length=1, max_length=500)
    file_type: str = Field(..., pattern="^(pdf|txt)$")
    mime_type: str
    size_bytes: int = Field(..., gt=0, le=100*1024*1024)  # Max 100MB

class ResourceInitUploadResponse(BaseModel):
    """Response with presigned upload URL"""
    resource_id: int
    upload_url: str  # Presigned PUT URL (R2 doesn't support POST)
    r2_key: str

class ResourceConfirmUploadResponse(BaseModel):
    """Response after confirming upload"""
    resource_id: int
    job_id: int
    status: str
    message: str

class ResourceStatusResponse(BaseModel):
    """Resource and job status"""
    resource_id: int
    status: str  # initiated, uploaded, processing, ready, failed
    progress: Optional[int] = None  # 0-100
    current_step: Optional[str] = None
    total_chunks: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class ResourceListItem(BaseModel):
    """Resource list item"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    original_filename: str
    file_type: str
    size_bytes: int
    status: str
    total_pages: Optional[int]
    total_chunks: Optional[int]
    created_at: datetime
    updated_at: datetime

class ResourceDeleteResponse(BaseModel):
    """Delete confirmation"""
    message: str
    resource_id: int

class ResourceFromURLRequest(BaseModel):
    """Request to create resource from URL"""
    title: str = Field(..., min_length=1, max_length=500)
    url: str = Field(..., min_length=1, max_length=2000)
    resource_type: str = Field(default="webpage")  # webpage, blog, article

# RAG Schemas
class RAGSearchRequest(BaseModel):
    """Search query"""
    query: str = Field(..., min_length=3, max_length=1000)
    top_k: int = Field(default=6, ge=1, le=20)

class ChunkResult(BaseModel):
    """Retrieved chunk"""
    chunk_text: str
    resource_title: str
    resource_id: int
    similarity_score: float

class RAGSearchResponse(BaseModel):
    """Search results"""
    query: str
    chunks: List[ChunkResult]
    total_results: int

class RAGAnswerRequest(BaseModel):
    """Answer generation request"""
    query: str = Field(..., min_length=3, max_length=1000)
    top_k: int = Field(default=6, ge=1, le=20)

class SourceReference(BaseModel):
    """Citation source"""
    resource_title: str
    resource_id: int
    chunk_text: str

class RAGAnswerResponse(BaseModel):
    """Generated answer with sources"""
    query: str
    answer: str
    sources: List[SourceReference]
    chunks_used: int