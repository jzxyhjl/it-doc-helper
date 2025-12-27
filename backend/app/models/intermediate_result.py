"""
文档中间结果模型（视角无关）
"""
from sqlalchemy import Column, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base


class DocumentIntermediateResult(Base):
    """
    文档中间结果表（视角无关）
    
    难点3解决方案：
    - 中间结果不包含任何视角相关的信息
    - 所有视角共享同一份中间结果
    - 切换视角时复用中间结果，仅重新组织AI处理
    """
    __tablename__ = "document_intermediate_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, unique=True, comment="文档ID")
    
    # 视角无关的中间结果
    content = Column(Text, nullable=False, comment="提取的原始内容（视角无关）")
    preprocessed_content = Column(Text, nullable=True, comment="预处理后的内容（视角无关）")
    segments = Column(JSONB, nullable=True, comment="段落切分结果（视角无关）")
    metadata_json = Column('metadata', JSONB, nullable=True, comment="元数据（视角无关）")
    
    # 注意：不包含任何视角相关的处理结果
    # 视角相关的处理结果存储在 processing_results 表中
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<DocumentIntermediateResult(id={self.id}, document_id={self.document_id})>"

