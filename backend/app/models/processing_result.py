"""
处理结果模型
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base


class ProcessingResult(Base):
    """处理结果表"""
    __tablename__ = "processing_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, unique=True, comment="文档ID")
    document_type = Column(String(50), nullable=False, comment="文档类型")
    result_data = Column(JSONB, nullable=False, comment="处理结果数据（JSON格式）")
    processing_time = Column(Integer, nullable=True, comment="处理耗时（秒）")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    # 唯一约束
    __table_args__ = (
        UniqueConstraint('document_id', name='uq_processing_results_document_id'),
    )

    def __repr__(self):
        return f"<ProcessingResult(id={self.id}, document_id={self.document_id}, type={self.document_type})>"

