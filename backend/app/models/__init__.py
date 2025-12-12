"""
数据模型模块
"""
from app.models.document import Document
from app.models.document_type import DocumentType
from app.models.processing_result import ProcessingResult
from app.models.processing_task import ProcessingTask
from app.models.system_learning_data import SystemLearningData

__all__ = [
    "Document",
    "DocumentType",
    "ProcessingResult",
    "ProcessingTask",
    "SystemLearningData",
]
