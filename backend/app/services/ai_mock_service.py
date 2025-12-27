"""
AI服务Mock - 用于模拟API失败场景
仅在测试环境使用，生产环境必须禁用
"""
from typing import Optional, Dict, List
from enum import Enum
import asyncio
import random
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class MockFailureType(Enum):
    """Mock失败类型"""
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    SERVER_ERROR = "server_error"
    NETWORK_ERROR = "network_error"
    INVALID_RESPONSE = "invalid_response"
    UNAUTHORIZED = "unauthorized"
    BAD_REQUEST = "bad_request"
    SERVICE_UNAVAILABLE = "service_unavailable"


class AIMockService:
    """AI服务Mock，用于模拟API失败场景"""
    
    def __init__(
        self,
        failure_type: Optional[MockFailureType] = None,
        failure_probability: float = 0.0,
        timeout_seconds: int = 60
    ):
        """
        初始化Mock服务
        
        Args:
            failure_type: 失败类型，如果为None则从配置读取
            failure_probability: 失败概率（0.0-1.0），如果为None则从配置读取
            timeout_seconds: 超时时间（秒），用于timeout失败类型
        """
        # 从配置读取或使用传入参数
        self.enabled = settings.ENABLE_AI_MOCK
        
        if failure_type is None:
            failure_type_str = settings.AI_MOCK_FAILURE_TYPE
            try:
                self.failure_type = MockFailureType(failure_type_str)
            except ValueError:
                logger.warning("无效的Mock失败类型，使用timeout", failure_type=failure_type_str)
                self.failure_type = MockFailureType.TIMEOUT
        else:
            self.failure_type = failure_type
        
        if failure_probability is None:
            self.failure_probability = settings.AI_MOCK_FAILURE_PROBABILITY
        else:
            self.failure_probability = failure_probability
        
        self.timeout_seconds = timeout_seconds
        
        if self.enabled:
            logger.info("AI Mock服务已启用", 
                       failure_type=self.failure_type.value,
                       failure_probability=self.failure_probability)
        else:
            logger.debug("AI Mock服务已禁用")
    
    async def should_fail(self) -> bool:
        """
        判断是否应该模拟失败
        
        Returns:
            如果应该失败返回True
        """
        if not self.enabled:
            return False
        
        # 根据概率决定是否失败
        return random.random() < self.failure_probability
    
    async def simulate_failure(self) -> None:
        """
        模拟失败场景
        
        Raises:
            各种异常，根据failure_type决定
        """
        if not self.enabled:
            return
        
        logger.info("模拟API失败", failure_type=self.failure_type.value)
        
        if self.failure_type == MockFailureType.TIMEOUT:
            # 模拟超时
            await asyncio.sleep(self.timeout_seconds)
            raise asyncio.TimeoutError(f"API调用超时（模拟，{self.timeout_seconds}秒）")
        
        elif self.failure_type == MockFailureType.RATE_LIMIT:
            # 模拟限流（429 Too Many Requests）
            from openai import APIError
            raise APIError(
                message="429 Too Many Requests",
                request=None,
                body=None,
                code=429
            )
        
        elif self.failure_type == MockFailureType.SERVER_ERROR:
            # 模拟服务器错误（500 Internal Server Error）
            from openai import APIError
            raise APIError(
                message="500 Internal Server Error",
                request=None,
                body=None,
                code=500
            )
        
        elif self.failure_type == MockFailureType.NETWORK_ERROR:
            # 模拟网络错误
            raise ConnectionError("网络连接失败（模拟）")
        
        elif self.failure_type == MockFailureType.INVALID_RESPONSE:
            # 模拟无效响应（JSON解析失败）
            raise ValueError("无效的API响应格式（模拟）")
        
        elif self.failure_type == MockFailureType.UNAUTHORIZED:
            # 模拟认证失败（401 Unauthorized）
            from openai import APIError
            raise APIError(
                message="401 Unauthorized",
                request=None,
                body=None,
                code=401
            )
        
        elif self.failure_type == MockFailureType.BAD_REQUEST:
            # 模拟请求错误（400 Bad Request）
            from openai import APIError
            raise APIError(
                message="400 Bad Request",
                request=None,
                body=None,
                code=400
            )
        
        elif self.failure_type == MockFailureType.SERVICE_UNAVAILABLE:
            # 模拟服务不可用（503 Service Unavailable）
            from openai import APIError
            raise APIError(
                message="503 Service Unavailable",
                request=None,
                body=None,
                code=503
            )
    
    async def mock_chat_completion(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> str:
        """
        模拟chat_completion调用
        
        Args:
            messages: 消息列表
            **kwargs: 其他参数
            
        Returns:
            AI返回的文本内容（如果未失败）
            
        Raises:
            各种异常（根据failure_type）
        """
        # 判断是否应该失败
        if await self.should_fail():
            await self.simulate_failure()
        
        # 如果未失败，返回模拟的成功响应
        # 注意：在实际使用中，Mock服务应该调用真实API
        # 这里返回一个简单的模拟响应
        return "Mock响应：这是一个模拟的AI响应，用于测试。"
    
    @staticmethod
    def get_instance() -> Optional['AIMockService']:
        """
        获取Mock服务实例（单例模式）
        
        Returns:
            Mock服务实例，如果未启用则返回None
        """
        if not settings.ENABLE_AI_MOCK:
            return None
        
        return AIMockService(
            failure_type=None,  # 从配置读取
            failure_probability=None,  # 从配置读取
            timeout_seconds=60
        )

