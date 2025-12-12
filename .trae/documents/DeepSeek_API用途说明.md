# DeepSeek API 用途说明

## 一、概述

DeepSeek API 在系统中**仅用于文档处理的核心功能**，**不用于向量化服务**。

## 二、DeepSeek API 的具体用途

### 1. 文档类型识别（Document Classification）

**位置**：`backend/app/services/document_classifier.py`

**用途**：
- 当规则匹配的置信度较低时，使用 AI 进行文档类型识别
- 识别文档类型：`interview`（面试题）、`technical`（技术文档）、`architecture`（架构文档）

**API 调用**：
- 使用 `deepseek-chat` 模型
- 调用方式：Chat Completion API

---

### 2. 面试题文档处理（Interview Document Processing）

**位置**：`backend/app/services/interview_processor.py`

**用途**：
- **内容总结**：提取关键知识点和重点内容
- **问题生成**：基于文档内容生成新的面试问题
- **答案提取**：从文档中提取问题的答案

**API 调用**：
- 使用 `deepseek-chat` 模型
- 多次调用，分别处理不同任务

---

### 3. IT技术文档处理（Technical Document Processing）

**位置**：`backend/app/services/technical_processor.py`

**用途**：
- **前置条件分析**：分析学习该技术所需的前置知识
- **学习路径规划**：制定从入门到精通的学习路径
- **学习方法建议**：提供学习方法和资源推荐

**API 调用**：
- 使用 `deepseek-chat` 模型
- 从架构师/讲师角度提供学习指导

---

### 4. 架构/搭建文档处理（Architecture Document Processing）

**位置**：`backend/app/services/architecture_processor.py`

**用途**：
- **配置流程提取**：提取清晰的配置步骤
- **组件识别**：识别系统中的各个组件
- **全景视图生成**：生成系统组件的全景视图
- **白话串讲**：用通俗易懂的语言解释系统架构
- **配置检查清单**：生成配置检查清单

**API 调用**：
- 使用 `deepseek-chat` 模型
- 多次调用，处理不同任务

---

## 三、向量化服务不使用 DeepSeek API

### 原因

1. **DeepSeek 不提供 Embeddings API**
   - DeepSeek 目前不提供专门的向量化 API
   - 尝试调用会返回 404 错误

2. **Chat API 不适合向量化**
   - 成本高：需要生成大量文本
   - 速度慢：响应时间长
   - 质量不稳定：向量质量可能不如专门的 Embeddings API
   - 影响用户体验：处理时间长，可能超时

### 向量化服务的实现方案

**位置**：`backend/app/services/embedding_service.py`

**方案**：
1. **优先**：本地嵌入模型（`sentence-transformers`）
   - 完全本地化，无网络延迟
   - 成本低，无 API 调用费用
   - 速度快，质量稳定

2. **备选**：其他云服务的 Embeddings API（如 OpenAI）
   - 如果配置了 `OPENAI_API_KEY`，可以使用 OpenAI Embeddings API

---

## 四、配置说明

### 必需的配置

```env
# DeepSeek API配置（必需，用于文档处理）
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_API_BASE=https://api.deepseek.com
```

### 可选的配置

```env
# 向量化服务配置（可选）
USE_LOCAL_EMBEDDING=true  # 默认启用本地嵌入模型
EMBEDDING_MODEL_NAME=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

# OpenAI Embeddings API（可选，用于向量化）
OPENAI_API_KEY=your_openai_key  # 如果不想使用本地模型，可以配置此项
```

---

## 五、总结

| 功能模块 | 是否使用 DeepSeek API | 说明 |
|---------|---------------------|------|
| 文档类型识别 | ✅ 是 | 使用 Chat API 进行 AI 识别 |
| 面试题文档处理 | ✅ 是 | 使用 Chat API 进行内容总结、问题生成、答案提取 |
| 技术文档处理 | ✅ 是 | 使用 Chat API 进行前置条件分析、学习路径规划 |
| 架构文档处理 | ✅ 是 | 使用 Chat API 进行配置流程提取、组件识别、全景视图生成 |
| **向量化服务** | ❌ **否** | 使用本地嵌入模型或 OpenAI Embeddings API |

---

**文档版本**: v1.0  
**创建时间**: 2025-12-10  
**最后更新**: 2025-12-10

