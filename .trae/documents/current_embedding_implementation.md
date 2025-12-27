# 当前向量生成实现方式

## 1. 实际使用的方案

### 方案1：本地嵌入模型（sentence-transformers）- **当前主要方案**

**配置**：
- `USE_LOCAL_EMBEDDING: True`
- `EMBEDDING_MODEL_NAME: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- `sentence-transformers` 已安装（版本 5.2.0）

**工作原理**：
1. 使用 `sentence-transformers` 库加载本地模型
2. 模型首次加载：需要下载和初始化（30-60秒，CPU环境）
3. 模型已加载后：生成向量很快（0.5-5秒，取决于文本长度）
4. 向量维度：模型原生维度（通常是384维），然后调整到1536维（截断或填充）

**优点**：
- ✅ 无需API调用，无网络延迟
- ✅ 无API费用
- ✅ 数据隐私好（本地处理）
- ✅ 模型加载后速度很快

**缺点**：
- ❌ 首次加载模型慢（30-60秒）
- ❌ 需要本地存储空间（模型文件）
- ❌ CPU环境下较慢（GPU会快很多）

### 方案2：OpenAI Embeddings API - **备选方案**

**配置**：
- `OPENAI_API_KEY: ""` （当前未配置）
- 如果配置了，会在本地模型不可用时使用

**工作原理**：
1. 调用 OpenAI Embeddings API
2. 使用 `text-embedding-ada-002` 模型
3. 返回1536维向量

**优点**：
- ✅ 速度快（1-3秒，网络延迟）
- ✅ 无需本地存储
- ✅ 无需模型加载时间

**缺点**：
- ❌ 需要API费用
- ❌ 需要网络连接
- ❌ 数据需要发送到外部服务

## 2. 不使用 DeepSeek API 的原因

**代码注释明确说明**：
```python
# 已删除：DeepSeek Embeddings API方案（DeepSeek不提供此API）
# 已删除：Chat API降级方案（影响用户体验，不再使用）
```

**原因**：
1. DeepSeek **不提供**专门的 Embeddings API
2. 虽然可以使用 Chat API 降级方案，但：
   - 影响向量质量
   - 速度慢（需要生成文本再解析）
   - 成本高（Chat API 比 Embeddings API 贵）
   - 已被删除，不再使用

## 3. 当前实现的工作流程

```
1. 检查是否使用本地模型（USE_LOCAL_EMBEDDING）
   ├─ 是 → 尝试加载本地模型（sentence-transformers）
   │   ├─ 成功 → 生成向量（0.5-5秒）
   │   └─ 失败 → 继续下一步
   └─ 否 → 继续下一步

2. 检查是否配置了 OpenAI API Key
   ├─ 是 → 调用 OpenAI Embeddings API
   │   ├─ 成功 → 返回向量（1-3秒）
   │   └─ 失败 → 继续下一步
   └─ 否 → 继续下一步

3. 所有方案都失败
   └─ 返回 None（向量生成失败）
```

## 4. 性能优化

### 模型预热
- 在服务启动时后台预热模型（30秒超时）
- 如果预热成功，后续生成向量很快
- 如果预热超时，在首次使用时加载（会慢一些）

### 同步生成（当前实现）
- 在文档处理时同步生成向量
- 设置30秒超时，避免首次加载模型时卡死
- 如果超时，跳过向量生成但不阻塞主流程

## 5. 总结

**当前实际使用**：**本地嵌入模型（sentence-transformers）**

**为什么不用 DeepSeek**：
- DeepSeek 不提供 Embeddings API
- 使用 Chat API 降级方案已被删除（影响质量）

**如果要用 DeepSeek**：
- 需要等待 DeepSeek 提供 Embeddings API
- 或者重新实现 Chat API 降级方案（不推荐）

