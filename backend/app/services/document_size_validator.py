"""
文档大小验证服务
验证文档大小、内容长度和处理时间，防止超时
"""
from typing import Dict, Optional
import structlog

logger = structlog.get_logger()


class DocumentSizeValidator:
    """文档大小验证器"""
    
    # 阈值定义
    FILE_SIZE_WARNING = 20 * 1024 * 1024  # 20MB
    FILE_SIZE_MAX = 30 * 1024 * 1024      # 30MB
    CONTENT_LENGTH_WARNING = 300000       # 30万字符
    CONTENT_LENGTH_MAX = 500000           # 50万字符
    PROCESS_TIME_WARNING = 480             # 480秒（8分钟）
    PROCESS_TIME_MAX = 600                 # 600秒（10分钟）
    
    @staticmethod
    def estimate_processing_time(content_length: int, doc_type: str = "technical") -> int:
        """
        估算处理时间（秒）
        
        Args:
            content_length: 内容长度（字符数）
            doc_type: 文档类型（technical/interview/architecture）
            
        Returns:
            估算的处理时间（秒）
        """
        base_time = 30
        content_factor = (content_length / 10000) * 10
        type_factor = {
            "technical": 1.0,
            "interview": 0.8,
            "architecture": 1.2
        }
        estimated = int(base_time + (content_factor * type_factor.get(doc_type, 1.0)))
        return estimated
    
    @staticmethod
    def validate_file_size(file_size: int) -> Dict:
        """
        验证文件大小
        
        Args:
            file_size: 文件大小（字节）
            
        Returns:
            {
                "valid": bool,
                "warnings": List[str]
            }
            
        Raises:
            ValueError: 如果文件大小超过限制
        """
        if file_size > DocumentSizeValidator.FILE_SIZE_MAX:
            raise ValueError(
                f"文件大小超过限制: {file_size / 1024 / 1024:.2f}MB > "
                f"{DocumentSizeValidator.FILE_SIZE_MAX / 1024 / 1024}MB。"
                "建议拆分后处理。"
            )
        
        warnings = []
        if file_size > DocumentSizeValidator.FILE_SIZE_WARNING:
            warnings.append(
                f"文件较大 ({file_size / 1024 / 1024:.2f}MB)，处理时间可能较长"
            )
        
        return {"valid": True, "warnings": warnings}
    
    @staticmethod
    def validate_content_length(
        content_length: int, 
        doc_type: str = "technical"
    ) -> Dict:
        """
        验证内容长度和处理时间
        
        Args:
            content_length: 内容长度（字符数）
            doc_type: 文档类型（technical/interview/architecture）
            
        Returns:
            {
                "valid": bool,
                "estimated_time": int,
                "warnings": List[str]
            }
            
        Raises:
            ValueError: 如果内容长度或处理时间超过限制
        """
        # 内容长度检查
        if content_length > DocumentSizeValidator.CONTENT_LENGTH_MAX:
            raise ValueError(
                f"文档内容过长: {content_length} 字符，超过限制 "
                f"{DocumentSizeValidator.CONTENT_LENGTH_MAX} 字符。"
                "建议拆分后处理。"
            )
        
        # 处理时间估算
        estimated_time = DocumentSizeValidator.estimate_processing_time(
            content_length, doc_type
        )
        
        if estimated_time > DocumentSizeValidator.PROCESS_TIME_MAX:
            raise ValueError(
                f"文档过大，预计处理时间 {estimated_time} 秒，"
                f"超过最大限制 {DocumentSizeValidator.PROCESS_TIME_MAX} 秒。"
                "建议拆分后处理。"
            )
        
        warnings = []
        if content_length > DocumentSizeValidator.CONTENT_LENGTH_WARNING:
            warnings.append(
                f"文档内容较长 ({content_length} 字符)，处理时间可能较长"
            )
        if estimated_time > DocumentSizeValidator.PROCESS_TIME_WARNING:
            warnings.append(
                f"预计处理时间约 {estimated_time} 秒，请耐心等待"
            )
        
        return {
            "valid": True,
            "estimated_time": estimated_time,
            "warnings": warnings
        }
    
    @staticmethod
    def validate_document(
        file_size: int,
        content_length: Optional[int] = None,
        doc_type: str = "technical"
    ) -> Dict:
        """
        完整的文档验证（文件大小 + 内容长度）
        
        Args:
            file_size: 文件大小（字节）
            content_length: 内容长度（字符数），如果为None则只验证文件大小
            doc_type: 文档类型
            
        Returns:
            {
                "valid": bool,
                "estimated_time": Optional[int],
                "warnings": List[str]
            }
            
        Raises:
            ValueError: 如果验证失败
        """
        # 1. 验证文件大小
        file_validation = DocumentSizeValidator.validate_file_size(file_size)
        warnings = file_validation.get("warnings", [])
        
        # 2. 如果提供了内容长度，验证内容长度和处理时间
        estimated_time = None
        if content_length is not None:
            content_validation = DocumentSizeValidator.validate_content_length(
                content_length, doc_type
            )
            estimated_time = content_validation.get("estimated_time")
            warnings.extend(content_validation.get("warnings", []))
        
        return {
            "valid": True,
            "estimated_time": estimated_time,
            "warnings": warnings
        }

