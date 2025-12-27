# 技术方案设计 - AI服务自动回归测试、失败模拟和稳定性监控

## 一、架构设计

### 1.0 核心理解

**系统核心功能**：解析文档，并整理内容

虽然三个场景（技术文档、面试题、架构文档）的核心功能相同，但它们有不同的：
- **输出结构**：不同的字段和数据结构
- **处理复杂度**：架构文档最复杂（6步 vs 3-4步）
- **特殊机制**：架构文档有进度回调、长文本截断
- **失败风险**：架构文档处理步骤最多，失败风险最高

**测试策略**：
- 使用统一的测试基础框架（复用通用验证逻辑）
- 场景差异化验证（验证不同的输出字段）
- 重点测试架构文档（最复杂，需要完整测试）

**场景对比**：

| 场景 | 处理步骤 | AI调用次数 | 输出字段 | 特殊机制 | 测试重点 |
|------|---------|-----------|---------|---------|---------|
| 技术文档 | 4步 | 4次 | 4个字段 | 技术名词清理 | 核心测试 |
| 面试题 | 3步 | 3次 | 3个字段 | 弱展示模式 | 核心测试 |
| 架构文档 | **6步** | **6次** | **6个字段** | **进度回调、长文本截断** | **完整测试** |

### 1.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    测试和监控系统架构                        │
└─────────────────────────────────────────────────────────────┘

┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│  回归测试框架    │      │  API失败模拟器    │      │  监控数据收集    │
│  (pytest)        │      │  (Mock/Stub)     │      │  (Metrics)       │
└────────┬─────────┘      └────────┬─────────┘      └────────┬─────────┘
         │                         │                         │
         │                         │                         │
         └─────────────────────────┼─────────────────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │    AI服务增强层              │
                    │  (AIService + Retry/Fallback)│
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │    DeepSeek API             │
                    │  (真实API调用)               │
                    └─────────────────────────────┘
```

### 1.2 核心组件

1. **回归测试框架** (`backend/tests/`)
   - 使用 pytest 作为测试框架
   - 测试用例管理（关键场景）
   - 测试数据管理（固定测试文档）
   - 测试报告生成

2. **API失败模拟器** (`backend/app/services/ai_mock_service.py`)
   - Mock/Stub机制模拟API失败
   - 支持多种失败场景（超时、错误码、限流等）
   - 通过环境变量控制启用/禁用

3. **AI服务增强层** (`backend/app/services/ai_service.py` 增强)
   - 重试机制（指数退避）
   - 降级策略（缓存、默认值）
   - 错误分类和处理

4. **监控数据收集** (`backend/app/services/ai_monitor.py`)
   - 指标收集（成功率、响应时间、错误类型）
   - 数据存储（PostgreSQL）
   - 结果一致性检查

5. **监控数据存储** (数据库表)
   - `ai_call_metrics` - API调用指标
   - `ai_result_quality` - 结果质量指标

---

## 二、技术栈选型

### 2.1 测试框架

**选择：pytest**

**理由**：
- ✅ 项目已安装 pytest（`requirements.txt` 中已有）
- ✅ 支持异步测试（`pytest-asyncio`）
- ✅ 丰富的插件生态（fixtures、参数化、报告）
- ✅ 易于集成CI/CD

**依赖**：
```python
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
pytest-mock==3.12.0  # 新增：用于Mock
pytest-html==4.1.1   # 新增：HTML报告
```

### 2.2 Mock/Stub框架

**选择：pytest-mock + unittest.mock**

**理由**：
- ✅ pytest-mock 是 pytest 的标准Mock插件
- ✅ unittest.mock 是Python标准库，无需额外依赖
- ✅ 支持异步Mock
- ✅ 易于配置和使用

### 2.3 监控数据存储

**选择：PostgreSQL（现有数据库）**

**理由**：
- ✅ 无需引入新的数据库
- ✅ 支持复杂查询和聚合
- ✅ 与现有系统集成简单

### 2.4 HTTP客户端Mock

**选择：responses 或 httpx-mock**

**理由**：
- ✅ 可以Mock HTTP请求，模拟API响应
- ✅ 支持异步请求Mock
- ✅ 易于配置各种响应场景

**依赖**：
```python
responses==0.24.1  # 或 httpx-mock==0.5.0
```

---

## 三、数据库设计

### 3.1 API调用指标表 (`ai_call_metrics`)

```sql
CREATE TABLE ai_call_metrics (
    id SERIAL PRIMARY KEY,
    document_id UUID,
    call_type VARCHAR(50),  -- 'chat_completion', 'generate_json', 'generate_with_sources'
    model VARCHAR(50),       -- 'deepseek-chat'
    status VARCHAR(20),      -- 'success', 'timeout', 'error_400', 'error_429', 'error_500', etc.
    response_time_ms INTEGER,
    error_type VARCHAR(50),  -- 'timeout', 'rate_limit', 'server_error', 'network_error', etc.
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_document_id (document_id),
    INDEX idx_created_at (created_at),
    INDEX idx_status (status)
);
```

### 3.2 结果质量指标表 (`ai_result_quality`)

```sql
CREATE TABLE ai_result_quality (
    id SERIAL PRIMARY KEY,
    document_id UUID,
    document_type VARCHAR(50),  -- 'technical', 'interview', 'architecture'
    field_completeness FLOAT,  -- 字段完整性（0-1）
    confidence_avg FLOAT,      -- 平均置信度
    confidence_min FLOAT,      -- 最小置信度
    confidence_max FLOAT,      -- 最大置信度
    sources_count INTEGER,     -- 来源片段数量
    sources_completeness FLOAT, -- 来源完整性（0-1）
    quality_score FLOAT,       -- 综合质量分数（0-100）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_document_id (document_id),
    INDEX idx_document_type (document_type),
    INDEX idx_created_at (created_at),
    INDEX idx_quality_score (quality_score)
);
```

### 3.3 结果一致性检查表 (`ai_result_consistency`)

```sql
CREATE TABLE ai_result_consistency (
    id SERIAL PRIMARY KEY,
    document_id UUID,
    test_run_id VARCHAR(100),  -- 测试运行ID（用于对比多次运行）
    field_name VARCHAR(100),   -- 字段名
    field_value_hash VARCHAR(64),  -- 字段值哈希（用于对比）
    confidence_diff FLOAT,     -- 置信度差异（与基准对比）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_document_id (document_id),
    INDEX idx_test_run_id (test_run_id)
);
```

---

## 四、接口设计

### 4.1 回归测试API（内部测试接口）

**测试执行接口**：
```python
POST /api/v1/internal/tests/regression/run
{
    "test_scenarios": ["technical", "interview", "architecture"],  # 可选，默认全部
    "test_documents": ["doc1.pdf", "doc2.docx"],  # 可选，使用默认测试文档
    "timeout": 600  # 可选，默认600秒
}

Response:
{
    "test_run_id": "test_20251219_123456",
    "status": "running" | "completed" | "failed",
    "total_tests": 9,
    "passed_tests": 8,
    "failed_tests": 1,
    "duration_seconds": 120,
    "results": [...]
}
```

**测试结果查询接口**：
```python
GET /api/v1/internal/tests/regression/{test_run_id}

Response:
{
    "test_run_id": "test_20251219_123456",
    "status": "completed",
    "results": [
        {
            "scenario": "technical",
            "document": "test_technical.pdf",
            "status": "passed",
            "duration_seconds": 45,
            "validations": {
                "structure": "passed",
                "confidence": "passed",
                "sources": "passed"
            }
        },
        ...
    ]
}
```

### 4.2 监控数据查询接口

**API调用统计接口**：
```python
GET /api/v1/internal/monitoring/ai-calls
?start_time=2025-12-19T00:00:00
&end_time=2025-12-19T23:59:59
&group_by=hour  # hour, day

Response:
{
    "period": {
        "start": "2025-12-19T00:00:00",
        "end": "2025-12-19T23:59:59"
    },
    "summary": {
        "total_calls": 150,
        "success_count": 142,
        "failure_count": 8,
        "success_rate": 0.947,
        "avg_response_time_ms": 1250,
        "p95_response_time_ms": 2100,
        "p99_response_time_ms": 3500
    },
    "error_distribution": {
        "timeout": 3,
        "rate_limit": 2,
        "server_error": 2,
        "network_error": 1
    }
}
```

**结果质量统计接口**：
```python
GET /api/v1/internal/monitoring/result-quality
?start_time=2025-12-19T00:00:00
&end_time=2025-12-19T23:59:59
&document_type=technical  # 可选

Response:
{
    "period": {...},
    "summary": {
        "avg_quality_score": 78.5,
        "avg_confidence": 72.3,
        "avg_sources_completeness": 0.85,
        "low_quality_count": 5  # quality_score < 60
    },
    "trend": {
        "quality_score": [75, 76, 78, 79, 78.5],  # 按时间序列
        "confidence": [70, 71, 72, 73, 72.3]
    }
}
```

---

## 五、实现细节

### 5.1 回归测试框架实现

**测试用例结构**：
```
backend/tests/
├── conftest.py              # pytest配置和fixtures
├── test_regression/
│   ├── __init__.py
│   ├── test_base.py         # 统一的测试基础框架（新增）
│   ├── test_technical_document.py
│   ├── test_interview_document.py
│   └── test_architecture_document.py  # 重点测试（最复杂）
├── fixtures/
│   ├── test_documents/      # 固定测试文档
│   │   ├── test_technical.pdf
│   │   ├── test_interview.docx
│   │   └── test_architecture.md
│   └── expected_results/    # 预期结果（可选，用于对比）
└── utils/
    ├── test_helpers.py      # 测试辅助函数
    └── validators.py        # 结果验证器（通用验证函数）
```

**测试用例示例**：

```python
# backend/tests/test_regression/test_base.py
"""统一的测试基础框架"""
import pytest
from typing import List, Dict

async def test_document_processing_base(
    document_type: str,
    expected_fields: List[str],
    test_document: str
):
    """
    统一的文档处理测试基础流程
    
    Args:
        document_type: 文档类型（technical/interview/architecture）
        expected_fields: 期望的输出字段列表
        test_document: 测试文档文件名
    """
    # 1. 上传测试文档
    document_id = await upload_test_document(test_document)
    
    # 2. 触发处理
    task_id = await trigger_processing(document_id)
    
    # 3. 等待处理完成
    result = await wait_for_completion(document_id, timeout=600)
    
    # 4. 验证基础结构（所有场景通用）
    assert result["document_type"] == document_type
    assert "result" in result
    assert result["status"] == "completed"
    
    # 5. 验证场景特定字段
    for field in expected_fields:
        assert field in result["result"], f"缺少字段: {field}"
        assert result["result"][field] is not None, f"字段为空: {field}"
    
    # 6. 验证置信度和来源（所有场景通用）
    validate_confidence_and_sources(result["result"], expected_fields)
    
    return result

def validate_confidence_and_sources(result_data: Dict, fields: List[str]):
    """验证置信度和来源字段（通用验证）"""
    for field in fields:
        field_data = result_data.get(field)
        if isinstance(field_data, dict):
            # 检查是否有置信度字段（可能不存在，取决于展示模式）
            if "confidence" in field_data:
                assert 0 <= field_data["confidence"] <= 100
            # 检查是否有来源字段
            if "sources" in field_data:
                assert isinstance(field_data["sources"], list)

# backend/tests/test_regression/test_technical_document.py
@pytest.mark.asyncio
async def test_technical_document_processing():
    """测试技术文档处理核心场景"""
    result = await test_document_processing_base(
        document_type="technical",
        expected_fields=["prerequisites", "learning_path", "learning_methods", "related_technologies"],
        test_document="test_technical.pdf"
    )
    
    # 场景特定验证
    # 验证学习路径的完整性
    learning_path = result["result"]["learning_path"]
    assert isinstance(learning_path, list)
    assert len(learning_path) > 0
    for stage in learning_path:
        assert "stage" in stage
        assert "title" in stage
        assert "content" in stage
    
    # 验证前置条件
    prerequisites = result["result"]["prerequisites"]
    assert "required" in prerequisites
    assert "recommended" in prerequisites

# backend/tests/test_regression/test_interview_document.py
@pytest.mark.asyncio
async def test_interview_document_processing():
    """测试面试题文档处理核心场景"""
    result = await test_document_processing_base(
        document_type="interview",
        expected_fields=["summary", "generated_questions", "extracted_answers"],
        test_document="test_interview.docx"
    )
    
    # 场景特定验证
    # 验证问题生成
    questions = result["result"]["generated_questions"]
    assert isinstance(questions, list)
    for question in questions:
        assert "question" in question
        assert "answer" in question
    
    # 验证内容总结
    summary = result["result"]["summary"]
    assert "key_points" in summary
    assert "total_questions" in summary

# backend/tests/test_regression/test_architecture_document.py
@pytest.mark.asyncio
async def test_architecture_document_processing():
    """测试架构文档处理核心场景（重点测试）"""
    result = await test_document_processing_base(
        document_type="architecture",
        expected_fields=["config_steps", "components", "architecture_view", 
                        "plain_explanation", "checklist", "related_technologies"],
        test_document="test_architecture.md"
    )
    
    # 场景特定验证（最复杂）
    # 验证配置步骤的完整性
    config_steps = result["result"]["config_steps"]
    assert isinstance(config_steps, list)
    assert len(config_steps) > 0
    for step in config_steps:
        assert "step" in step
        assert "description" in step
    
    # 验证组件识别
    components = result["result"]["components"]
    assert isinstance(components, list)
    for component in components:
        assert "name" in component
        assert "description" in component
    
    # 验证架构视图（可能包含Mermaid代码）
    architecture_view = result["result"]["architecture_view"]
    assert isinstance(architecture_view, str)
    assert len(architecture_view) > 0
    
    # 验证进度回调机制（需要额外测试）
    await test_architecture_progress_callback()

@pytest.mark.asyncio
async def test_architecture_progress_callback():
    """测试架构文档的进度回调机制"""
    document_id = await upload_test_document("test_architecture.md")
    task_id = await trigger_processing(document_id)
    
    # 监听进度更新
    progress_updates = []
    async for progress in monitor_progress(task_id):
        progress_updates.append(progress)
        # 验证进度回调包含架构文档的5个步骤
        if "步骤1/5" in progress.get("stage", ""):
            assert "提取配置流程" in progress["stage"]
        elif "步骤2/5" in progress.get("stage", ""):
            assert "识别组件" in progress["stage"]
        # ... 其他步骤验证
    
    # 验证至少有5个进度更新（5个步骤）
    assert len(progress_updates) >= 5
```

### 5.2 API失败模拟实现

**Mock服务实现**：
```python
# backend/app/services/ai_mock_service.py
from typing import Optional, Dict, List
from enum import Enum
import asyncio
from openai import OpenAI

class MockFailureType(Enum):
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    SERVER_ERROR = "server_error"
    NETWORK_ERROR = "network_error"
    INVALID_RESPONSE = "invalid_response"

class AIMockService:
    """AI服务Mock，用于模拟API失败场景"""
    
    def __init__(self, failure_type: Optional[MockFailureType] = None, 
                 failure_probability: float = 0.0):
        self.failure_type = failure_type
        self.failure_probability = failure_probability
        self.enabled = failure_type is not None
    
    async def mock_chat_completion(self, messages: List[Dict], **kwargs):
        """模拟chat_completion调用"""
        if not self.enabled:
            # 正常调用真实API
            return await self._real_call(messages, **kwargs)
        
        # 根据概率决定是否失败
        import random
        if random.random() < self.failure_probability:
            return await self._simulate_failure()
        else:
            return await self._real_call(messages, **kwargs)
    
    async def _simulate_failure(self):
        """模拟失败场景"""
        if self.failure_type == MockFailureType.TIMEOUT:
            await asyncio.sleep(60)  # 模拟超时
            raise asyncio.TimeoutError("API调用超时")
        elif self.failure_type == MockFailureType.RATE_LIMIT:
            raise Exception("429 Too Many Requests")
        elif self.failure_type == MockFailureType.SERVER_ERROR:
            raise Exception("500 Internal Server Error")
        # ... 其他失败场景
```

**使用方式**：
```python
# 通过环境变量控制
# .env
ENABLE_AI_MOCK=true
AI_MOCK_FAILURE_TYPE=timeout
AI_MOCK_FAILURE_PROBABILITY=0.3  # 30%概率失败
```

### 5.3 AI服务增强（重试和降级）

**重试机制实现**：
```python
# backend/app/services/ai_service.py 增强
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class AIService:
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((TimeoutError, ConnectionError))
    )
    async def chat_completion(self, messages, **kwargs):
        """带重试的AI调用"""
        try:
            response = self.client.chat.completions.create(...)
            return response.choices[0].message.content.strip()
        except Exception as e:
            # 记录错误
            await self._record_error(e)
            raise
```

**降级策略实现**：
```python
async def chat_completion_with_fallback(self, messages, **kwargs):
    """带降级策略的AI调用"""
    try:
        return await self.chat_completion(messages, **kwargs)
    except Exception as e:
        # 尝试使用缓存
        cached_result = await self._get_cached_result(messages)
        if cached_result:
            logger.warning("使用缓存结果", error=str(e))
            return cached_result
        
        # 返回默认值
        logger.error("AI调用失败，使用默认值", error=str(e))
        return self._get_default_response(messages)
```

**依赖**：
```python
tenacity==8.2.3  # 重试库
```

### 5.4 监控数据收集实现

**指标收集服务**：
```python
# backend/app/services/ai_monitor.py
from datetime import datetime
from typing import Dict, Optional
import structlog

logger = structlog.get_logger()

class AIMonitor:
    """AI服务监控"""
    
    @staticmethod
    async def record_api_call(
        document_id: str,
        call_type: str,
        status: str,
        response_time_ms: int,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        retry_count: int = 0
    ):
        """记录API调用指标"""
        # 存储到数据库
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            # 插入 ai_call_metrics 表
            ...
    
    @staticmethod
    async def record_result_quality(
        document_id: str,
        document_type: str,
        quality_metrics: Dict
    ):
        """记录结果质量指标"""
        # 存储到数据库
        ...
    
    @staticmethod
    async def check_consistency(
        document_id: str,
        current_result: Dict,
        baseline_result: Optional[Dict] = None
    ) -> Dict:
        """检查结果一致性"""
        if baseline_result:
            # 对比关键字段
            confidence_diff = abs(
                current_result.get("confidence", 0) - 
                baseline_result.get("confidence", 0)
            )
            return {
                "consistent": confidence_diff < 5,  # 允许5%差异
                "confidence_diff": confidence_diff
            }
        return {"consistent": True}
```

**集成到AI服务**：
```python
# backend/app/services/ai_service.py
async def chat_completion(self, messages, **kwargs):
    start_time = datetime.now()
    try:
        response = self.client.chat.completions.create(...)
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # 记录成功指标
        await AIMonitor.record_api_call(
            document_id=kwargs.get("document_id"),
            call_type="chat_completion",
            status="success",
            response_time_ms=int(response_time)
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # 记录失败指标
        await AIMonitor.record_api_call(
            document_id=kwargs.get("document_id"),
            call_type="chat_completion",
            status="failed",
            response_time_ms=int(response_time),
            error_type=self._classify_error(e),
            error_message=str(e)[:500]
        )
        raise
```

---

## 六、测试策略

### 6.1 回归测试策略

**测试频率**：
- 每次代码提交前（本地运行）
- 每次代码合并前（CI/CD自动运行）
- 每天定时运行（可选，验证API行为变化）

**测试场景覆盖**：

虽然三个场景的核心功能都是"解析文档，并整理内容"，但它们有不同的输出结构和处理复杂度，需要分别测试：

#### 6.1.1 统一测试框架

**基础流程**（所有场景通用）：
1. 文档上传
2. 触发处理
3. 等待完成
4. 验证基础结构（document_type, result字段）
5. 验证置信度和来源字段（通用验证）
6. 验证场景特定字段（差异化验证）

#### 6.1.2 场景差异化测试

**1. 技术文档处理**（中等复杂度）
- **处理步骤**：4步（前置条件、学习路径、学习方法、技术关联）
- **AI调用次数**：4次
- **输出字段**：
  - `prerequisites`（required/recommended）
  - `learning_path`（阶段列表）
  - `learning_methods`（theory/practice）
  - `related_technologies`（technologies列表）
- **测试重点**：
  - ✅ 验证4个主要字段存在
  - ✅ 验证学习路径的完整性（阶段数量、内容）
  - ✅ 验证置信度和来源（完整展示模式）
- **测试复杂度**：中等

**2. 面试题文档处理**（简单）
- **处理步骤**：3步（内容总结、问题生成、答案提取）
- **AI调用次数**：3次
- **输出字段**：
  - `summary`（key_points, question_types, difficulty, total_questions）
  - `generated_questions`（问题列表）
  - `extracted_answers`（答案列表）
- **测试重点**：
  - ✅ 验证3个主要字段存在
  - ✅ 验证问题生成的准确性（问题格式、答案格式）
  - ✅ 验证置信度和来源（弱展示模式）
- **测试复杂度**：简单

**3. 架构文档处理**（最复杂，重点测试）
- **处理步骤**：6步（配置流程、组件识别、全景视图、白话串讲、检查清单、技术栈）
- **AI调用次数**：6次
- **输出字段**：
  - `config_steps`（配置步骤列表）
  - `components`（组件列表）
  - `architecture_view`（架构视图文本，可能包含Mermaid代码）
  - `plain_explanation`（白话解释文本）
  - `checklist`（检查清单）
  - `related_technologies`（技术栈列表）
- **特殊机制**：
  - ✅ **进度回调机制**（5个步骤的进度更新）
  - ✅ **长文本截断逻辑**（前15000字符 + 后5000字符）
- **测试重点**：
  - ✅ 验证6个主要字段存在
  - ✅ 验证配置步骤的完整性（步骤数量、描述）
  - ✅ **验证进度回调机制**（进度更新是否正常）
  - ✅ 验证长文本处理（截断逻辑是否正确）
  - ✅ 验证置信度和来源（弱展示模式）
- **测试复杂度**：最复杂（需要重点测试）

#### 6.1.3 测试策略优化

**分层测试策略**：
- **架构文档**：完整测试（6个步骤 + 进度回调 + 长文本处理）
- **技术文档**：核心测试（4个字段验证）
- **面试题**：核心测试（3个字段验证）

**通用验证**（所有场景）：
- 数据结构完整性
- 置信度字段存在且范围正确（0-100）
- 来源片段字段存在且格式正确
- 关键字段不为空
- API调用成功
- 处理时间在合理范围内

### 6.2 API失败模拟策略

**模拟场景**：
1. **超时场景**
   - 网络超时（30秒、60秒）
   - 响应超时

2. **错误状态码**
   - 400 Bad Request
   - 401 Unauthorized
   - 429 Too Many Requests（限流）
   - 500 Internal Server Error
   - 503 Service Unavailable

3. **无效响应**
   - 空响应
   - JSON解析失败
   - 格式错误

**验证内容**：
- 系统是否正确处理异常
- 重试机制是否生效
- 降级策略是否生效
- 用户是否收到友好错误信息

### 6.3 监控策略

**监控指标**：
- API调用成功率（目标：>95%）
- API平均响应时间（目标：<2秒）
- API错误类型分布
- 结果质量分数（目标：>70）
- 结果一致性（目标：置信度差异<5%）

**告警阈值**：
- API成功率 < 90%：警告
- API成功率 < 80%：严重告警
- 平均响应时间 > 5秒：警告
- 结果质量分数 < 60：警告

---

## 七、安全性

### 7.1 测试接口安全

**访问控制**：
- 测试接口仅限内部使用（`/api/v1/internal/`）
- 通过IP白名单或API密钥控制访问
- 生产环境禁用测试接口

### 7.2 监控数据安全

**数据保护**：
- 监控数据不包含敏感信息（如API密钥、用户数据）
- 定期清理历史监控数据（保留30天）
- 监控数据访问需要权限控制

### 7.3 Mock服务安全

**使用限制**：
- Mock服务仅在测试环境启用
- 通过环境变量严格控制启用/禁用
- 生产环境强制禁用Mock服务

---

## 八、部署和配置

### 8.1 环境变量配置

```bash
# 测试和监控配置
ENABLE_REGRESSION_TEST=true
ENABLE_AI_MOCK=false  # 生产环境必须为false
AI_MOCK_FAILURE_TYPE=timeout
AI_MOCK_FAILURE_PROBABILITY=0.0
ENABLE_AI_MONITORING=true
MONITORING_RETENTION_DAYS=30
```

### 8.2 CI/CD集成

**GitHub Actions示例**：
```yaml
name: Regression Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run regression tests
        run: |
          docker-compose up -d
          pytest backend/tests/test_regression/ -v --html=report.html
```

---

## 九、实施计划

### 阶段1：基础框架（1周）
1. 搭建pytest测试框架
2. 创建统一的测试基础框架（`test_base.py`）
3. 创建测试用例结构（三个场景的测试文件）
4. 准备测试文档（三个场景各一个固定测试文档）

### 阶段2：API失败模拟（1周）
1. 实现Mock服务
2. 集成到AI服务
3. 测试各种失败场景

### 阶段3：监控数据收集（1周）
1. 创建监控数据表
2. 实现监控服务
3. 集成到AI服务

### 阶段4：增强和优化（1周）
1. 实现重试和降级机制
2. 实现监控报告
3. 集成CI/CD

---

**文档版本**：v1.0
**创建时间**：2025-12-19
**最后更新**：2025-12-19

