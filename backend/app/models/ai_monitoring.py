"""
AI监控数据模型
"""
from sqlalchemy import Column, String, Integer, DateTime, Float, Text, func, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.core.database import Base


class AICallMetrics(Base):
    """AI调用指标表"""
    __tablename__ = "ai_call_metrics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(UUID(as_uuid=True), nullable=True, comment="文档ID")
    call_type = Column(String(50), nullable=True, comment="调用类型（chat_completion/generate_json/generate_with_sources）")
    model = Column(String(50), nullable=True, comment="模型名称")
    status = Column(String(20), nullable=False, comment="状态（success/timeout/error_400/error_429/error_500等）")
    response_time_ms = Column(Integer, nullable=True, comment="响应时间（毫秒）")
    error_type = Column(String(50), nullable=True, comment="错误类型（timeout/rate_limit/server_error/network_error等）")
    error_message = Column(Text, nullable=True, comment="错误信息")
    retry_count = Column(Integer, nullable=False, default=0, comment="重试次数")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间")
    
    __table_args__ = (
        Index('idx_ai_call_metrics_document_id', 'document_id'),
        Index('idx_ai_call_metrics_created_at', 'created_at'),
        Index('idx_ai_call_metrics_status', 'status'),
    )
    
    def __repr__(self):
        return f"<AICallMetrics(id={self.id}, document_id={self.document_id}, status={self.status})>"


class AIResultQuality(Base):
    """AI结果质量表"""
    __tablename__ = "ai_result_quality"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(UUID(as_uuid=True), nullable=False, comment="文档ID")
    document_type = Column(String(50), nullable=True, comment="文档类型（technical/interview/architecture）")
    field_completeness = Column(Float, nullable=True, comment="字段完整性（0-1）")
    confidence_avg = Column(Float, nullable=True, comment="平均置信度")
    confidence_min = Column(Float, nullable=True, comment="最小置信度")
    confidence_max = Column(Float, nullable=True, comment="最大置信度")
    sources_count = Column(Integer, nullable=True, comment="来源片段数量")
    sources_completeness = Column(Float, nullable=True, comment="来源完整性（0-1）")
    quality_score = Column(Float, nullable=True, comment="综合质量分数（0-100）")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间")
    
    __table_args__ = (
        Index('idx_ai_result_quality_document_id', 'document_id'),
        Index('idx_ai_result_quality_document_type', 'document_type'),
        Index('idx_ai_result_quality_created_at', 'created_at'),
        Index('idx_ai_result_quality_quality_score', 'quality_score'),
    )
    
    def __repr__(self):
        return f"<AIResultQuality(id={self.id}, document_id={self.document_id}, quality_score={self.quality_score})>"


class AIResultConsistency(Base):
    """AI结果一致性表（可选，用于结果一致性检查）"""
    __tablename__ = "ai_result_consistency"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(UUID(as_uuid=True), nullable=False, comment="文档ID")
    test_run_id = Column(String(100), nullable=True, comment="测试运行ID（用于对比多次运行）")
    field_name = Column(String(100), nullable=True, comment="字段名")
    field_value_hash = Column(String(64), nullable=True, comment="字段值哈希（用于对比）")
    confidence_diff = Column(Float, nullable=True, comment="置信度差异（与基准对比）")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间")
    
    __table_args__ = (
        Index('idx_ai_result_consistency_document_id', 'document_id'),
        Index('idx_ai_result_consistency_test_run_id', 'test_run_id'),
    )
    
    def __repr__(self):
        return f"<AIResultConsistency(id={self.id}, document_id={self.document_id}, field_name={self.field_name})>"

