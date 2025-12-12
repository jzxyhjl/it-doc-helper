# DeepSeek向量化实现方案

## 一、方案概述

文档向量化服务将使用DeepSeek API实现，与现有AI服务保持一致，复用相同的API配置。

---

## 二、技术方案

### 方案A：使用DeepSeek Embeddings API（优先）⭐

如果DeepSeek提供专门的Embeddings API端点，直接使用。

**实现方式**:
```python
# app/services/embedding_service.py
from app.services.ai_service import AIService
from typing import List
import numpy as np

class EmbeddingService:
    def __init__(self):
        self.ai_service = AIService()
    
    async def generate_embedding(self, text: str) -> List[float]:
        """生成文本向量"""
        try:
            # 使用OpenAI兼容的SDK调用DeepSeek Embeddings API
            response = self.ai_service.client.embeddings.create(
                model="deepseek-embedding",  # 需要确认模型名称
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error("向量生成失败", error=str(e))
            raise
```

**优点**:
- 直接使用专门的Embeddings API，效率高
- 向量维度固定，便于存储和索引

**缺点**:
- 需要确认DeepSeek是否提供此API

---

### 方案B：使用DeepSeek Chat API生成向量（备选）⭐

如果DeepSeek不提供Embeddings API，使用Chat API + 特殊prompt生成向量表示。

**实现方式**:
```python
# app/services/embedding_service.py
from app.services.ai_service import AIService
from typing import List
import json
import re

class EmbeddingService:
    def __init__(self):
        self.ai_service = AIService()
    
    async def generate_embedding(self, text: str) -> List[float]:
        """使用Chat API生成向量"""
        prompt = f"""请将以下文本转换为一个数值向量表示，用于相似度搜索。
要求：
1. 返回一个JSON格式的数组，包含1536个浮点数
2. 数值范围在-1到1之间
3. 向量应该能够反映文本的语义信息

文本内容：
{text}

请只返回JSON数组，格式：[0.123, -0.456, ...]"""
        
        try:
            response = await self.ai_service.generate_text(
                prompt=prompt,
                model="deepseek-chat",
                temperature=0.1  # 低温度保证一致性
            )
            
            # 提取JSON数组
            json_match = re.search(r'\[[^\]]+\]', response, re.DOTALL)
            if json_match:
                embedding = json.loads(json_match.group())
                # 确保维度为1536
                if len(embedding) != 1536:
                    # 截断或填充到1536维
                    embedding = embedding[:1536] + [0.0] * (1536 - len(embedding))
                return embedding
            else:
                raise Exception("无法从响应中提取向量")
                
        except Exception as e:
            logger.error("向量生成失败", error=str(e))
            raise
```

**优点**:
- 可以使用现有的DeepSeek Chat API
- 不需要额外的API端点

**缺点**:
- 向量质量可能不如专门的Embeddings API
- 需要后处理确保维度一致
- 成本可能较高（Chat API通常比Embeddings API贵）

---

### 方案C：使用本地嵌入模型（备选）⭐

如果DeepSeek API不可用或成本过高，使用本地嵌入模型。

**实现方式**:
```python
# app/services/embedding_service.py
from sentence_transformers import SentenceTransformer
from typing import List
import numpy as np

class EmbeddingService:
    def __init__(self):
        # 使用中文优化的嵌入模型
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        # 或使用其他模型，如：
        # self.model = SentenceTransformer('text2vec-base-chinese')
    
    async def generate_embedding(self, text: str) -> List[float]:
        """使用本地模型生成向量"""
        try:
            # 生成向量（同步操作，但可以异步包装）
            embedding = self.model.encode(text, convert_to_numpy=True)
            
            # 转换为列表并归一化
            embedding_list = embedding.tolist()
            
            # 如果维度不是1536，需要调整
            if len(embedding_list) != 1536:
                # 使用PCA或其他方法调整维度
                # 或直接截断/填充
                embedding_list = embedding_list[:1536] + [0.0] * (1536 - len(embedding_list))
            
            return embedding_list
        except Exception as e:
            logger.error("向量生成失败", error=str(e))
            raise
```

**优点**:
- 完全本地化，不依赖外部API
- 成本低，无API调用费用
- 响应速度快

**缺点**:
- 需要安装额外的Python包（sentence-transformers）
- 模型文件较大，需要下载
- 向量质量可能不如专门的API

---

## 三、推荐方案

### 实施步骤

1. **第一步**：验证DeepSeek API是否提供Embeddings端点
   - 查看DeepSeek API文档
   - 测试API调用
   - 如果提供，使用方案A

2. **第二步**：如果DeepSeek不提供Embeddings API
   - 优先尝试方案B（使用Chat API）
   - 如果效果不理想或成本过高，考虑方案C

3. **第三步**：实现统一的EmbeddingService接口
   - 封装不同方案的实现
   - 提供统一的调用接口
   - 支持方案切换

---

## 四、实现建议

### 统一接口设计

```python
# app/services/embedding_service.py
from abc import ABC, abstractmethod
from typing import List
from app.core.config import settings

class EmbeddingServiceBase(ABC):
    """向量化服务基类"""
    
    @abstractmethod
    async def generate_embedding(self, text: str) -> List[float]:
        """生成文本向量"""
        pass
    
    @abstractmethod
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """批量生成向量"""
        pass


class DeepSeekEmbeddingService(EmbeddingServiceBase):
    """DeepSeek向量化服务"""
    
    def __init__(self, use_chat_api: bool = False):
        """
        Args:
            use_chat_api: 是否使用Chat API（如果Embeddings API不可用）
        """
        from app.services.ai_service import AIService
        self.ai_service = AIService()
        self.use_chat_api = use_chat_api
    
    async def generate_embedding(self, text: str) -> List[float]:
        """生成向量"""
        if self.use_chat_api:
            return await self._generate_via_chat(text)
        else:
            return await self._generate_via_embeddings_api(text)
    
    async def _generate_via_embeddings_api(self, text: str) -> List[float]:
        """使用Embeddings API生成向量"""
        # 方案A实现
        pass
    
    async def _generate_via_chat(self, text: str) -> List[float]:
        """使用Chat API生成向量"""
        # 方案B实现
        pass


# 工厂函数
def get_embedding_service() -> EmbeddingServiceBase:
    """获取向量化服务实例"""
    # 根据配置选择实现方案
    if settings.USE_LOCAL_EMBEDDING:
        return LocalEmbeddingService()
    else:
        return DeepSeekEmbeddingService(use_chat_api=settings.USE_CHAT_API_FOR_EMBEDDING)
```

---

## 五、配置建议

在`config.py`中添加配置项：

```python
# 向量化服务配置
USE_LOCAL_EMBEDDING: bool = False  # 是否使用本地嵌入模型
USE_CHAT_API_FOR_EMBEDDING: bool = False  # 是否使用Chat API生成向量
EMBEDDING_MODEL: str = "deepseek-embedding"  # 嵌入模型名称
EMBEDDING_DIMENSION: int = 1536  # 向量维度
```

---

## 六、注意事项

1. **向量维度一致性**：确保所有方案生成的向量维度一致（建议1536维）

2. **文本长度限制**：如果文档内容过长，需要截断或分块处理

3. **错误处理**：向量生成失败不应影响文档处理主流程

4. **性能优化**：考虑批量生成向量，减少API调用次数

5. **成本控制**：如果使用Chat API，注意控制调用频率和成本

---

**文档版本**: v1.0
**创建时间**: 2025-12-09
**最后更新**: 2025-12-09

