"""
处理异常类
定义明确的失败状态和错误信息结构
"""
from typing import Dict, List, Optional
from enum import Enum


class ProcessingStatus(str, Enum):
    """处理状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    LOW_QUALITY = "low_quality"
    UNKNOWN = "unknown"


class ErrorType(str, Enum):
    """错误类型枚举"""
    AI_CALL_FAILED = "ai_call_failed"
    TIMEOUT = "timeout"
    INVALID_FILE = "invalid_file"
    PARSE_ERROR = "parse_error"
    LOW_QUALITY = "low_quality"
    CONTENT_TOO_SHORT = "content_too_short"
    CONTENT_TOO_LONG = "content_too_long"
    FILE_CORRUPTED = "file_corrupted"
    UNSUPPORTED_FORMAT = "unsupported_format"


class ProcessingException(Exception):
    """处理异常类"""
    
    def __init__(
        self,
        status: ProcessingStatus,
        error_type: ErrorType,
        error_message: str,
        error_details: Optional[Dict] = None,
        user_actions: Optional[List[Dict]] = None
    ):
        """
        初始化处理异常
        
        Args:
            status: 失败状态
            error_type: 错误类型
            error_message: 错误消息
            error_details: 错误详情
            user_actions: 用户操作建议
        """
        super().__init__(error_message)
        self.status = status
        self.error_type = error_type
        self.error_message = error_message
        self.error_details = error_details or {}
        self.user_actions = user_actions or []
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "status": self.status.value,
            "error_type": self.error_type.value,
            "error_message": self.error_message,
            "error_details": self.error_details,
            "user_actions": self.user_actions
        }


class UserActionMapper:
    """用户操作建议映射器"""
    
    @staticmethod
    def get_actions_for_error(error_type: ErrorType, error_details: Dict) -> List[Dict]:
        """
        根据错误类型获取用户操作建议
        
        Args:
            error_type: 错误类型
            error_details: 错误详情
            
        Returns:
            用户操作建议列表
        """
        actions_map = {
            ErrorType.AI_CALL_FAILED: [
                {
                    "action": "retry",
                    "label": "重试处理",
                    "description": "重新处理当前文档"
                },
                {
                    "action": "check_config",
                    "label": "检查配置",
                    "description": "请检查API密钥配置和网络连接"
                }
            ],
            ErrorType.TIMEOUT: [
                {
                    "action": "retry",
                    "label": "重试处理",
                    "description": "可以稍后重试"
                },
                {
                    "action": "split_document",
                    "label": "拆分文档",
                    "description": "文档过大，建议拆分后处理"
                }
            ],
            ErrorType.INVALID_FILE: [
                {
                    "action": "check_file",
                    "label": "检查文件",
                    "description": "文件可能损坏，请检查文件完整性"
                },
                {
                    "action": "re_upload",
                    "label": "重新上传",
                    "description": "尝试重新上传文件"
                }
            ],
            ErrorType.CONTENT_TOO_SHORT: [
                {
                    "action": "check_content",
                    "label": "检查内容",
                    "description": "文档内容过少（<50字符），无法处理"
                }
            ],
            ErrorType.CONTENT_TOO_LONG: [
                {
                    "action": "split_document",
                    "label": "拆分文档",
                    "description": "文档内容过长，建议拆分后处理"
                }
            ],
            ErrorType.FILE_CORRUPTED: [
                {
                    "action": "re_upload",
                    "label": "重新上传",
                    "description": "文件可能损坏，请重新上传"
                }
            ],
            ErrorType.UNSUPPORTED_FORMAT: [
                {
                    "action": "check_format",
                    "label": "检查格式",
                    "description": f"不支持的文件格式。支持的类型: {error_details.get('supported_formats', 'PDF, Word, PPT, Markdown, TXT')}"
                }
            ],
            ErrorType.PARSE_ERROR: [
                {
                    "action": "retry",
                    "label": "重试处理",
                    "description": "解析失败，可以尝试重试"
                }
            ],
            ErrorType.LOW_QUALITY: [
                {
                    "action": "retry",
                    "label": "重试处理",
                    "description": "结果质量较低，可以尝试重试"
                },
                {
                    "action": "view_anyway",
                    "label": "仍然查看",
                    "description": "查看结果（可能不准确）"
                }
            ]
        }
        
        return actions_map.get(error_type, [
            {
                "action": "retry",
                "label": "重试处理",
                "description": "可以尝试重新处理"
            }
        ])

