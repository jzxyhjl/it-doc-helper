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
        temperature: float = 0.3
    ) -> Dict:
        """
        生成JSON格式响应
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示（可选）
            model: 模型名称
            temperature: 温度参数（JSON生成使用较低温度）
        
        Returns:
            解析后的JSON字典
        """
        import json
        import re
        
        # 添加JSON格式要求
        json_prompt = f"{prompt}\n\n请只返回JSON格式，不要包含其他文字说明。"
        
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
                return json.loads(array_match.group())
            except json.JSONDecodeError:
                logger.warning("JSON数组提取后解析失败，尝试对象提取", response=cleaned_text[:100])
        
        # 尝试提取JSON对象（匹配最外层的大括号）
        json_match = re.search(r'\{.*\}', cleaned_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                logger.warning("JSON对象提取后解析失败，尝试直接解析", response=cleaned_text[:100])
        
        # 如果提取失败，尝试直接解析清理后的文本
        try:
            return json.loads(cleaned_text)
        except json.JSONDecodeError as e:
            logger.error("JSON解析失败", error=str(e), response=cleaned_text[:200], original=response_text[:200])
            raise Exception(f"AI返回的JSON格式无效: {str(e)}")


# 全局AI服务实例（延迟初始化）
_ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
    """获取AI服务实例（单例模式）"""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service

