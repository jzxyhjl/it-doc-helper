"""
文档类型模型
"""
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.core.database import Base


class DocumentType(Base):
    """文档类型表"""
    __tablename__ = "document_types"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, comment="文档ID")
    detected_type = Column(String(50), nullable=False, comment="识别的类型（interview/technical/architecture/unknown）")
    confidence = Column(Float, nullable=True, comment="识别置信度（0-1）")
    detection_method = Column(String(50), nullable=False, comment="识别方法（rule/ai/hybrid）")
    detected_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="识别时间")

    # 关系
    document = relationship("Document", backref="document_types")

    def __repr__(self):
        return f"<DocumentType(id={self.id}, document_id={self.document_id}, type={self.detected_type})>"

