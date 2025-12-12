"""
处理任务模型
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.core.database import Base


class ProcessingTask(Base):
    """处理任务表"""
    __tablename__ = "processing_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, comment="文档ID")
    task_type = Column(String(50), nullable=False, comment="任务类型（extract/identify/process）")
    status = Column(String(20), nullable=False, default="pending", comment="任务状态（pending/running/completed/failed）")
    progress = Column(Integer, nullable=False, default=0, comment="进度百分比（0-100）")
    current_stage = Column(String(100), nullable=True, comment="当前处理阶段")
    error_message = Column(Text, nullable=True, comment="错误信息")
    started_at = Column(DateTime(timezone=True), nullable=True, comment="开始时间")
    completed_at = Column(DateTime(timezone=True), nullable=True, comment="完成时间")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间")

    def __repr__(self):
        return f"<ProcessingTask(id={self.id}, document_id={self.document_id}, status={self.status}, progress={self.progress})>"

