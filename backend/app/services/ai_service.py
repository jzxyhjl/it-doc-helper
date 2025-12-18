"""
AI服务 - DeepSeek API集成
提供统一的AI调用接口
"""
from typing import Optional, Dict, List
from openai import OpenAI
import structlog

from app.core.config import settings

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
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "deepseek-chat",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        AI对话完成
        
        Args:
            messages: 消息列表，格式 [{"role": "user", "content": "..."}]
            model: 模型名称，默认 deepseek-chat
            temperature: 温度参数，控制随机性（0-1）
            max_tokens: 最大token数
            **kwargs: 其他参数
        
        Returns:
            AI返回的文本内容
        """
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            content = response.choices[0].message.content.strip()
            logger.info("AI调用成功", model=model, tokens=response.usage.total_tokens if response.usage else 0)
            return content
            
        except Exception as e:
            logger.error("AI调用失败", error=str(e), model=model)
            raise Exception(f"AI服务调用失败: {str(e)}")
    
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: str = "deepseek-chat",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        生成文本（简化接口）
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示（可选）
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大token数
        
        Returns:
            生成的文本
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        return await self.chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
    
    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: str = "deepseek-chat",
        temperature: float = 0.3,
        require_sources: bool = False,
        require_confidence: bool = False
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
            temperature=temperature
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
        require_confidence: bool = True
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
            require_confidence=require_confidence
        )


# 全局AI服务实例（延迟初始化）
_ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
    """获取AI服务实例（单例模式）"""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service

