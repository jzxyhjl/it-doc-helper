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
    enabled_views: Optional[list[str]] = Field(None, description="启用的视角列表")
    primary_view: Optional[str] = Field(None, description="主视角")
    task_id: Optional[str] = Field(None, description="处理任务ID（用于WebSocket连接）")


class DocumentResultResponse(BaseModel):
    """文档处理结果响应（单个视角）"""
    document_id: str
    document_type: str
    result: dict
    processing_time: Optional[int] = None
    quality_score: Optional[int] = Field(None, ge=0, le=100, description="处理结果质量分数（0-100）")
    created_at: datetime


class MultiViewResultResponse(BaseModel):
    """多视角结果响应"""
    document_id: str
    views: dict[str, dict] = Field(description="各视角的结果（保持原生结构）")
    meta: dict = Field(description="元数据（enabled_views, primary_view, confidence等）")


class ViewsResultResponse(BaseModel):
    """多个视角结果响应"""
    document_id: str
    requested_views: list[str] = Field(description="请求的视角列表")
    results: dict[str, dict] = Field(description="各视角的结果（保持原生结构）")


class ViewStatusItem(BaseModel):
    """视角状态项"""
    view: str = Field(description="视角名称")
    status: str = Field(description="状态（completed/processing/pending/failed）")
    ready: bool = Field(description="是否就绪")
    is_primary: bool = Field(description="是否为主视角")
    processing_time: Optional[int] = Field(None, description="处理耗时（秒）")
    has_content: bool = Field(True, description="是否有内容（用于判断是否显示切换按钮）")


class ViewsStatusResponse(BaseModel):
    """视角状态响应"""
    document_id: str
    views_status: dict[str, ViewStatusItem] = Field(description="各视角的状态")
    primary_view: Optional[str] = Field(None, description="主视角")
    enabled_views: list[str] = Field(description="启用的视角列表")


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


class ViewRecommendationResponse(BaseModel):
    """视角推荐响应"""
    primary_view: str = Field(description="主视角（用于UI初始状态和算力分配）")
    enabled_views: list[str] = Field(description="启用的视角列表")
    detection_scores: dict[str, float] = Field(description="系统检测的特征得分（用于缓存key）")
    cache_key: Optional[str] = Field(None, description="基于检测得分生成的缓存key")
    type_mapping: Optional[str] = Field(None, description="向后兼容的类型映射")
    method: Optional[str] = Field(None, description="推荐方法（rule/ai/user_specified）")

