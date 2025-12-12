"""
文档相关的Pydantic Schema
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class DocumentBase(BaseModel):
    """文档基础Schema"""
    filename: str
    file_type: str
    file_size: int


class DocumentUploadResponse(BaseModel):
    """文档上传响应"""
    document_id: str
    task_id: Optional[str] = None
    filename: str
    file_size: int
    file_type: str
    status: str
    upload_time: datetime
    message: Optional[str] = None  # 提示信息，如"已覆盖同名文档"


class DocumentResponse(BaseModel):
    """文档信息响应"""
    document_id: str
    filename: str
    file_size: int
    file_type: str
    status: str
    upload_time: datetime
    created_at: datetime
    updated_at: datetime


class DocumentProgressResponse(BaseModel):
    """文档处理进度响应"""
    document_id: str
    progress: int = Field(ge=0, le=100, description="进度百分比")
    current_stage: Optional[str] = None
    status: str


class DocumentResultResponse(BaseModel):
    """文档处理结果响应"""
    document_id: str
    document_type: str
    result: dict
    processing_time: Optional[int] = None
    quality_score: Optional[int] = Field(None, ge=0, le=100, description="处理结果质量分数（0-100）")
    created_at: datetime


class DocumentHistoryItem(BaseModel):
    """历史记录项"""
    document_id: str
    filename: str
    file_type: str
    document_type: Optional[str] = None
    status: str
    upload_time: datetime
    processing_time: Optional[int] = None


class DocumentHistoryResponse(BaseModel):
    """历史记录响应"""
    total: int
    page: int
    page_size: int
    items: list[DocumentHistoryItem]


class SimilarDocumentItem(BaseModel):
    """相似文档项"""
    document_id: str
    filename: str
    file_type: str
    document_type: str
    similarity: float = Field(ge=0.0, le=1.0, description="相似度分数（0-1）")
    content_summary: Optional[str] = None
    upload_time: datetime


class SimilarDocumentsResponse(BaseModel):
    """相似文档响应"""
    document_id: str
    total: int
    limit: int
    threshold: Optional[float] = None
    items: list[SimilarDocumentItem]


class RecommendedDocumentItem(BaseModel):
    """推荐文档项"""
    document_id: str
    filename: str
    file_type: str
    document_type: str
    content_summary: Optional[str] = None
    quality_score: Optional[int] = None
    upload_time: Optional[str] = None
    similarity: Optional[float] = None
    recommendation_score: float
    reasons: list[str]


class RecommendationsResponse(BaseModel):
    """推荐响应"""
    recommendations: list[RecommendedDocumentItem]
    total: int
    generated_at: str
    error: Optional[str] = None

