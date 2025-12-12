"""
文档向量化服务
支持多种向量生成方案：
1. 本地嵌入模型（sentence-transformers）- 优先方案
2. 其他云服务Embeddings API（OpenAI等）- 备选方案

注意：向量化服务不使用DeepSeek API。
DeepSeek API仅用于文档处理的其他功能（类型识别、内容总结、问题生成等）。
"""
from typing import List, Optional
from app.core.config import settings
import structlog

logger = structlog.get_logger()


class EmbeddingService:
    """向量化服务类，封装向量生成逻辑"""
    
    def __init__(self):
        """
        初始化向量化服务
        
        注意：向量化服务不使用DeepSeek API。
        DeepSeek API仅用于文档处理的其他功能（类型识别、内容总结、问题生成等）。
        """
        self.embedding_dimension = 1536  # OpenAI标准维度
        
        # 初始化本地嵌入模型（延迟加载）
        self._local_model = None
        self._use_local_model = self._should_use_local_model()
        self._embedding_model_name = settings.EMBEDDING_MODEL_NAME
    
    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        生成文本向量
        
        优先使用本地嵌入模型，如果不可用则尝试其他云服务的Embeddings API。
        
        Args:
            text: 要向量化的文本内容
            
        Returns:
            向量列表（1536维），如果生成失败返回None
        """
        if not text or not text.strip():
            logger.warning("文本为空，跳过向量生成")
            return None
        
        # 截断过长的文本（避免超出API限制）
        # 大多数嵌入API限制在8000-16000 tokens，这里保守估计
        max_length = 8000  # 字符数，约等于2000-3000 tokens
        if len(text) > max_length:
            logger.warning("文本过长，进行截断", original_length=len(text), max_length=max_length)
            text = text[:max_length]
        
        try:
            # 方案1：优先使用本地嵌入模型（如果可用）
            if self._use_local_model:
                embedding = await self._generate_via_local_model(text)
                if embedding:
                    return embedding
            
            # 方案2：尝试使用其他云服务的Embeddings API（如OpenAI）
            embedding = await self._generate_via_other_embeddings_api(text)
            if embedding:
                return embedding
            
            # 如果所有方案都失败，返回None
            logger.warning("所有向量生成方案都不可用", 
                          use_local_model=self._use_local_model,
                          has_openai_key=bool(settings.OPENAI_API_KEY))
            return None
            
        except Exception as e:
            logger.error("向量生成失败", error=str(e), text_length=len(text))
            return None
    
    def _should_use_local_model(self) -> bool:
        """
        判断是否使用本地嵌入模型
        
        Returns:
            True表示使用本地模型，False表示使用API
        """
        # 检查配置
        use_local = settings.USE_LOCAL_EMBEDDING
        if use_local:
            try:
                # 尝试导入sentence-transformers，如果成功则使用本地模型
                import sentence_transformers
                return True
            except ImportError:
                logger.warning("sentence-transformers未安装，将使用API方案")
                return False
        return False
    
    async def _get_local_model(self):
        """
        获取本地嵌入模型实例（延迟加载）
        
        Returns:
            SentenceTransformer模型实例
        """
        if self._local_model is None:
            try:
                import sentence_transformers
                # 使用配置的模型名称
                model_name = self._embedding_model_name
                logger.info("加载本地嵌入模型", model_name=model_name)
                self._local_model = sentence_transformers.SentenceTransformer(model_name)
                actual_dim = self._local_model.get_sentence_embedding_dimension()
                logger.info("本地嵌入模型加载成功", 
                           model_name=model_name,
                           model_dimension=actual_dim,
                           target_dimension=self.embedding_dimension)
            except ImportError:
                logger.error("sentence-transformers未安装，无法使用本地模型")
                raise
            except Exception as e:
                logger.error("加载本地嵌入模型失败", error=str(e))
                raise
        return self._local_model
    
    async def _generate_via_local_model(self, text: str) -> Optional[List[float]]:
        """
        使用本地嵌入模型生成向量（方案1，优先）
        
        Args:
            text: 要向量化的文本
            
        Returns:
            向量列表，如果生成失败返回None
        """
        try:
            model = await self._get_local_model()
            
            # 生成向量（同步操作，在异步环境中运行）
            import asyncio
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(None, model.encode, text)
            
            # 转换为列表
            embedding_list = embedding.tolist() if hasattr(embedding, 'tolist') else list(embedding)
            
            # 调整维度到1536（如果需要）
            actual_dim = len(embedding_list)
            if actual_dim != self.embedding_dimension:
                logger.info("向量维度调整", 
                           original_dim=actual_dim, 
                           target_dim=self.embedding_dimension)
                if actual_dim > self.embedding_dimension:
                    # 截断到1536维
                    embedding_list = embedding_list[:self.embedding_dimension]
                else:
                    # 填充到1536维（使用零填充或重复填充）
                    # 使用零填充更安全
                    embedding_list = embedding_list + [0.0] * (self.embedding_dimension - actual_dim)
            
            logger.info("使用本地嵌入模型生成向量成功", 
                       dimension=len(embedding_list),
                       original_dim=actual_dim)
            return embedding_list
            
        except ImportError:
            logger.warning("sentence-transformers未安装，跳过本地模型方案")
            return None
        except Exception as e:
            logger.error("本地嵌入模型生成向量失败", error=str(e))
            return None
    
    async def _generate_via_other_embeddings_api(self, text: str) -> Optional[List[float]]:
        """
        使用其他云服务的Embeddings API（方案3）
        
        支持OpenAI等兼容OpenAI API格式的服务
        
        Args:
            text: 要向量化的文本
            
        Returns:
            向量列表，如果API不可用返回None
        """
        # 检查是否配置了OpenAI API Key
        openai_api_key = settings.OPENAI_API_KEY
        if not openai_api_key:
            return None
        
        try:
            from openai import OpenAI
            
            client = OpenAI(api_key=openai_api_key)
            response = client.embeddings.create(
                model="text-embedding-ada-002",  # 或 text-embedding-3-small/large
                input=text
            )
            
            embedding = response.data[0].embedding
            
            # 确保维度为1536
            if len(embedding) != self.embedding_dimension:
                logger.warning("向量维度不匹配", 
                             expected=self.embedding_dimension,
                             actual=len(embedding))
                if len(embedding) > self.embedding_dimension:
                    embedding = embedding[:self.embedding_dimension]
                else:
                    embedding = embedding + [0.0] * (self.embedding_dimension - len(embedding))
            
            logger.info("使用OpenAI Embeddings API生成向量成功", dimension=len(embedding))
            return embedding
            
        except Exception as e:
            logger.debug("OpenAI Embeddings API不可用或调用失败", error=str(e))
            return None
    
    # 已删除：DeepSeek Embeddings API方案（DeepSeek不提供此API）
    # 已删除：Chat API降级方案（影响用户体验，不再使用）
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        批量生成向量
        
        Args:
            texts: 文本列表
            
        Returns:
            向量列表，每个元素对应一个文本的向量（失败则为None）
        """
        results = []
        for text in texts:
            embedding = await self.generate_embedding(text)
            results.append(embedding)
        return results


# 全局向量化服务实例（延迟初始化）
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """获取向量化服务实例（单例模式）"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service

