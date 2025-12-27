"""
AI服务 - DeepSeek API集成
提供统一的AI调用接口
"""
from typing import Optional, Dict, List, Callable, AsyncGenerator
from openai import OpenAI
import structlog
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    retry_if_exception
)

from app.core.config import settings
from app.services.ai_mock_service import AIMockService
from app.services.ai_monitoring_service import AIMonitoringService
import time

logger = structlog.get_logger()


class AIService:
    """AI服务类，封装DeepSeek API调用"""
    
    def __init__(self, api_key: Optional[str] = None, api_base: Optional[str] = None):
        """
        初始化AI服务
        
        Args:
            api_key: DeepSeek API密钥，如果为None则从配置读取
            api_base: DeepSeek API基础URL，如果为None则从配置读取
        """
        self.api_key = api_key or settings.DEEPSEEK_API_KEY
        self.api_base = api_base or settings.DEEPSEEK_API_BASE
        
        if not self.api_key:
            raise ValueError("DeepSeek API Key未配置，请在.env文件中设置DEEPSEEK_API_KEY")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.api_base
        )
        
        # 初始化Mock服务（如果启用）
        self.mock_service = AIMockService.get_instance()
        if self.mock_service:
            logger.info("AI Mock服务已集成", 
                       failure_type=self.mock_service.failure_type.value,
                       failure_probability=self.mock_service.failure_probability)
        
        # 初始化监控服务（如果启用）
        self.monitoring_service = AIMonitoringService.get_instance()
        if self.monitoring_service and self.monitoring_service.enabled:
            logger.info("AI监控服务已集成")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((TimeoutError, ConnectionError)) | 
              retry_if_exception(lambda e: _is_retryable_error(e)),
        reraise=True
    )
    async def chat_completion_stream(
        self,
        messages: List[Dict[str, str]],
        model: str = "deepseek-chat",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        document_id: Optional[str] = None,
        **kwargs
    ):
        """
        AI对话完成（流式响应）
        
        Args:
            messages: 消息列表，格式 [{"role": "user", "content": "..."}]
            model: 模型名称，默认 deepseek-chat
            temperature: 温度参数，控制随机性（0-1）
            max_tokens: 最大token数
            document_id: 文档ID（用于监控）
            **kwargs: 其他参数
        
        Yields:
            流式返回的文本块（str）
        """
        try:
            # 创建流式响应
            stream = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,  # 启用流式响应
                **kwargs
            )
            
            # 逐块返回内容
            for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        yield delta.content
                        
        except Exception as e:
            logger.error("流式AI调用失败", model=model, error=str(e))
            raise
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "deepseek-chat",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        document_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        AI对话完成（带重试机制和监控）
        
        Args:
            messages: 消息列表，格式 [{"role": "user", "content": "..."}]
            model: 模型名称，默认 deepseek-chat
            temperature: 温度参数，控制随机性（0-1）
            max_tokens: 最大token数
            document_id: 文档ID（用于监控）
            **kwargs: 其他参数
        
        Returns:
            AI返回的文本内容
        """
        start_time = time.time()
        retry_count = 0
        error_type = None
        error_message = None
        
        # 检查Mock服务（如果启用，先尝试模拟失败）
        if self.mock_service and await self.mock_service.should_fail():
            logger.info("Mock服务触发失败模拟", 
                       failure_type=self.mock_service.failure_type.value)
            await self.mock_service.simulate_failure()
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            content = response.choices[0].message.content.strip()
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # 记录成功指标
            if self.monitoring_service.enabled:
                await self.monitoring_service.record_call_metrics(
                    document_id=document_id,
                    call_type="chat_completion",
                    model=model,
                    status="success",
                    response_time_ms=response_time_ms,
                    retry_count=retry_count
                )
            
            logger.info("AI调用成功", model=model, tokens=response.usage.total_tokens if response.usage else 0)
            return content
            
        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            error_message = str(e)
            error_type = type(e).__name__
            
            # 判断错误类型
            status = "error_unknown"
            if isinstance(e, TimeoutError) or "timeout" in error_message.lower():
                status = "timeout"
                error_type = "timeout"
            elif isinstance(e, ConnectionError):
                status = "error_network"
                error_type = "network_error"
            else:
                from openai import APIError
                if isinstance(e, APIError):
                    if e.code == 429:
                        status = "error_429"
                        error_type = "rate_limit"
                    elif e.code == 400:
                        status = "error_400"
                        error_type = "bad_request"
                    elif e.code and 500 <= e.code < 600:
                        status = "error_500"
                        error_type = "server_error"
            
            # 记录失败指标
            if self.monitoring_service.enabled:
                await self.monitoring_service.record_call_metrics(
                    document_id=document_id,
                    call_type="chat_completion",
                    model=model,
                    status=status,
                    response_time_ms=response_time_ms,
                    error_type=error_type,
                    error_message=error_message,
                    retry_count=retry_count
                )
            
            logger.error("AI调用失败", error=error_message, model=model, error_type=error_type)
            raise Exception(f"AI服务调用失败: {error_message}")
    
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: str = "deepseek-chat",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        document_id: Optional[str] = None,
        stream: bool = False,
        stream_callback: Optional[callable] = None
    ) -> str:
        """
        生成文本（简化接口）
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示（可选）
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大token数
            document_id: 文档ID（用于监控）
            stream: 是否使用流式生成
            stream_callback: 流式回调函数，接收文本块 (chunk: str) -> None
        
        Returns:
            生成的文本
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        if stream and stream_callback:
            # 流式生成
            full_content = ""
            async for chunk in self.chat_completion_stream(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                document_id=document_id
            ):
                full_content += chunk
                if stream_callback:
                    stream_callback(chunk)
            return full_content
        else:
            # 非流式生成
            return await self.chat_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                document_id=document_id
            )
    
    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: str = "deepseek-chat",
        temperature: float = 0.3,
        require_sources: bool = False,
        require_confidence: bool = False,
        document_id: Optional[str] = None,
        stream: bool = False,
        stream_callback: Optional[callable] = None
    ) -> Dict:
        """
        生成JSON格式响应
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示（可选）
            model: 模型名称
            temperature: 温度参数（JSON生成使用较低温度）
            require_sources: 是否要求返回source_ids
            require_confidence: 是否要求返回confidence
        
        Returns:
            解析后的JSON字典
        """
        import json
        import re
        
        # 添加JSON格式要求
        json_prompt = f"{prompt}\n\n请只返回JSON格式，不要包含其他文字说明。"
        
        # 如果要求返回来源和可信度，添加说明
        if require_sources or require_confidence:
            requirements = []
            if require_sources:
                requirements.append("- source_ids: 数组，包含引用的段落编号（如 [1, 2, 3]）")
            if require_confidence:
                requirements.append("- confidence: 数字，可信度分数（0-100）")
            
            if requirements:
                json_prompt += f"\n\n返回的JSON必须包含以下字段：\n" + "\n".join(requirements)
        
        response_text = await self.generate_text(
            prompt=json_prompt,
            system_prompt=system_prompt,
            model=model,
            temperature=temperature,
            document_id=document_id
        )
        
        # 清理响应文本：移除markdown代码块标记
        cleaned_text = response_text.strip()
        
        # 处理markdown代码块（```json ... ``` 或 ``` ... ```）
        if cleaned_text.startswith('```'):
            # 移除开头的 ```json 或 ```
            cleaned_text = re.sub(r'^```(?:json)?\s*\n?', '', cleaned_text, flags=re.IGNORECASE)
            # 移除结尾的 ```
            cleaned_text = re.sub(r'\n?```\s*$', '', cleaned_text)
            cleaned_text = cleaned_text.strip()
        
        # 尝试提取JSON数组（匹配最外层的方括号）
        array_match = re.search(r'\[.*\]', cleaned_text, re.DOTALL)
        if array_match:
            try:
                result = json.loads(array_match.group())
                # 验证和修正结果
                return self._validate_and_fix_json(result, require_sources, require_confidence)
            except json.JSONDecodeError:
                logger.warning("JSON数组提取后解析失败，尝试对象提取", response=cleaned_text[:100])
        
        # 尝试提取JSON对象（匹配最外层的大括号）
        json_match = re.search(r'\{.*\}', cleaned_text, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group())
                # 验证和修正结果
                return self._validate_and_fix_json(result, require_sources, require_confidence)
            except json.JSONDecodeError:
                logger.warning("JSON对象提取后解析失败，尝试直接解析", response=cleaned_text[:100])
        
        # 如果提取失败，尝试直接解析清理后的文本
        try:
            result = json.loads(cleaned_text)
            # 验证和修正结果
            return self._validate_and_fix_json(result, require_sources, require_confidence)
        except json.JSONDecodeError as e:
            logger.error("JSON解析失败", error=str(e), response=cleaned_text[:200], original=response_text[:200])
            raise Exception(f"AI返回的JSON格式无效: {str(e)}")
    
    def _validate_and_fix_json(
        self,
        result: Dict,
        require_sources: bool,
        require_confidence: bool
    ) -> Dict:
        """
        验证和修正JSON结果
        
        确保包含必需的字段，修正无效值
        """
        # 如果是列表，取第一个元素（如果期望字典）
        if isinstance(result, list):
            if len(result) > 0 and isinstance(result[0], dict):
                # 如果列表只有一个元素且是字典，使用该字典
                result = result[0]
            else:
                # 否则返回空字典
                logger.warning("AI返回了列表但期望字典，使用空字典")
                result = {}
        
        if not isinstance(result, dict):
            logger.warning(f"AI返回了非字典类型: {type(result)}，使用空字典")
            result = {}
        
        # 验证source_ids
        if require_sources:
            if "source_ids" not in result:
                result["source_ids"] = []
                logger.warning("AI返回结果缺少source_ids字段，使用空数组")
            elif not isinstance(result["source_ids"], list):
                result["source_ids"] = []
                logger.warning("AI返回的source_ids不是数组，使用空数组")
            else:
                # 确保source_ids是整数列表
                result["source_ids"] = [int(id) for id in result["source_ids"] if isinstance(id, (int, str)) and str(id).isdigit()]
        
        # 验证confidence
        if require_confidence:
            if "confidence" not in result:
                result["confidence"] = 50  # 默认中等可信度
                logger.warning("AI返回结果缺少confidence字段，使用默认值50")
            else:
                try:
                    confidence = float(result["confidence"])
                    # 确保在0-100范围内
                    result["confidence"] = max(0, min(100, confidence))
                except (ValueError, TypeError):
                    result["confidence"] = 50
                    logger.warning("AI返回的confidence无效，使用默认值50")
        
        return result
    
    async def generate_with_sources(
        self,
        prompt: str,
        segments: List[Dict],
        system_prompt: Optional[str] = None,
        model: str = "deepseek-chat",
        temperature: float = 0.3,
        require_confidence: bool = True,
        document_id: Optional[str] = None
    ) -> Dict:
        """
        生成带来源和可信度的JSON响应
        
        Args:
            prompt: 用户提示
            segments: 段落列表，格式 [{"id": 1, "text": "...", ...}, ...]
            system_prompt: 系统提示（可选）
            model: 模型名称
            temperature: 温度参数
            require_confidence: 是否要求返回confidence
        
        Returns:
            解析后的JSON字典，包含source_ids和confidence
        """
        from app.services.source_segmenter import SourceSegmenter
        
        # 格式化段落为prompt格式
        segments_text = SourceSegmenter.format_segments_for_prompt(segments)
        
        # 增强prompt，包含段落信息
        enhanced_prompt = f"""文档内容已按段落编号：

{segments_text}

{prompt}

请分析并返回JSON，每个结论/结果项必须包含：
- source_ids: 数组，包含引用的段落编号（如 [1, 2, 3]）
- confidence: 数字，可信度分数（0-100），表示该结论的可靠性"""
        
        # 调用generate_json，要求返回来源和可信度
        return await self.generate_json(
            prompt=enhanced_prompt,
            system_prompt=system_prompt,
            model=model,
            temperature=temperature,
            require_sources=True,
            require_confidence=require_confidence,
            document_id=document_id
        )


def _is_retryable_error(exception: Exception) -> bool:
    """
    判断错误是否可重试
    
    Args:
        exception: 异常对象
        
    Returns:
        如果可重试返回True
    """
    from openai import APIError
    
    # 429 Too Many Requests - 限流，可重试
    if isinstance(exception, APIError):
        if exception.code == 429:
            return True
        # 5xx服务器错误，可重试
        if exception.code and 500 <= exception.code < 600:
            return True
    
    # 网络错误，可重试
    if isinstance(exception, (ConnectionError, TimeoutError)):
        return True
    
    # 超时错误，可重试
    if "timeout" in str(exception).lower() or "超时" in str(exception):
        return True
    
    return False


# 全局AI服务实例（延迟初始化）
_ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
    """获取AI服务实例（单例模式）"""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service

