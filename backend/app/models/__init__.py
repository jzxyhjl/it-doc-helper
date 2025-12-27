"""
数据模型模块
"""
from app.models.document import Document
from app.models.document_type import DocumentType
from app.models.processing_result import ProcessingResult
from app.models.processing_task import ProcessingTask
from app.models.system_learning_data import SystemLearningData
from app.models.intermediate_result import DocumentIntermediateResult

__all__ = [
    "Document",
    "DocumentType",
    "ProcessingResult",
    "ProcessingTask",
    "SystemLearningData",
    "DocumentIntermediateResult",  # 新增：中间结果模型
]
