"""
系统学习数据模型
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
import uuid
from app.core.database import Base


class SystemLearningData(Base):
    """系统学习数据表"""
    __tablename__ = "system_learning_data"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, comment="文档ID")
    content_summary = Column(Text, nullable=False, comment="内容摘要")
    embedding = Column(Vector(1536), nullable=True, comment="内容向量（使用pgvector，1536维）")
    document_type = Column(String(50), nullable=False, comment="文档类型")
    processing_result_summary = Column(Text, nullable=True, comment="处理结果摘要")
    processing_time = Column(Integer, nullable=True, comment="处理耗时")
    quality_score = Column(Integer, nullable=True, comment="处理结果质量分数（0-100）")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间")

    def __repr__(self):
        return f"<SystemLearningData(id={self.id}, document_id={self.document_id}, type={self.document_type})>"

