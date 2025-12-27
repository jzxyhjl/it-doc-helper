"""
处理结果模型（每个view独立存储）
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Boolean, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base


class ProcessingResult(Base):
    """
    处理结果表（每个view独立存储）
    
    难点1解决方案：
    - 每个view独立存储，互不影响
    - 一个view的生成/更新，不影响其他view的稳定性
    - 支持view的增量更新
    """
    __tablename__ = "processing_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, comment="文档ID")
    view = Column(String(50), nullable=False, comment="视角名称（learning/qa/system）")
    document_type = Column(String(50), nullable=False, comment="文档类型（向后兼容）")
    result_data = Column(JSONB, nullable=False, comment="该view的结果（保持原生结构）")
    is_primary = Column(Boolean, nullable=False, default=False, comment="是否为主视角")
    processing_time = Column(Integer, nullable=True, comment="处理耗时（秒）")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    # 唯一约束：一个文档的同一个view只能有一条记录（难点1：独立存储）
    __table_args__ = (
        UniqueConstraint('document_id', 'view', name='uq_processing_result_document_view'),
    )

    def __repr__(self):
        return f"<ProcessingResult(id={self.id}, document_id={self.document_id}, view={self.view}, type={self.document_type})>"

