"""
文档模型
"""
from sqlalchemy import Column, String, BigInteger, DateTime, Text, func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.core.database import Base


class Document(Base):
    """文档表"""
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False, comment="文件名")
    file_path = Column(String(500), nullable=False, comment="文件存储路径")
    file_size = Column(BigInteger, nullable=False, comment="文件大小（字节）")
    file_type = Column(String(50), nullable=False, comment="文件类型（pdf/docx/pptx/md/txt）")
    upload_time = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="上传时间")
    status = Column(String(20), nullable=False, default="pending", comment="处理状态（pending/processing/completed/failed）")
    content_extracted = Column(Text, nullable=True, comment="提取的文档内容")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<Document(id={self.id}, filename={self.filename}, status={self.status})>"

