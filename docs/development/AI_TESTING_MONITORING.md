# AI测试和监控文档

## 概述

本文档介绍系统的AI测试和监控功能，包括自动回归测试、API失败模拟和结果稳定性监控。

## 目录

1. [自动回归测试](#自动回归测试)
2. [API失败模拟](#api失败模拟)
3. [结果稳定性监控](#结果稳定性监控)
4. [使用指南](#使用指南)

## 自动回归测试

### 功能说明

自动回归测试用于验证核心场景的处理结果，确保系统功能稳定。测试覆盖三个核心场景：

1. **技术文档处理**：验证学习路径、前置条件、学习方法、技术关联等字段
2. **面试题文档处理**：验证内容总结、问题生成、答案提取等字段
3. **架构文档处理**：验证配置步骤、组件识别、架构视图、白话解释、检查清单等字段

### 测试框架

- **测试工具**：pytest + pytest-asyncio
- **测试目录**：`backend/tests/test_regression/`
- **测试文档**：`backend/tests/fixtures/test_documents/`
- **测试报告**：`backend/tests/reports/report.html`

### 运行测试

#### 在Docker容器中运行

```bash
# 确保服务已启动
docker-compose up -d

# 运行所有回归测试
docker-compose exec backend pytest backend/tests/test_regression/ -v

# 运行特定场景测试
docker-compose exec backend pytest backend/tests/test_regression/test_technical_document.py -v

# 生成HTML报告
docker-compose exec backend pytest backend/tests/test_regression/ -v --html=backend/tests/reports/report.html
```

#### 在本地运行

```bash
cd backend
source venv/bin/activate
pytest tests/test_regression/ -v
```

### 测试文档准备

测试文档存放在 `backend/tests/fixtures/test_documents/` 目录：

- `test_technical.pdf` - 技术文档测试用例
- `test_interview.docx` - 面试题文档测试用例
- `test_architecture.md` - 架构文档测试用例

**注意**：测试文档应该是固定版本，确保测试结果可复现。

### 测试验证内容

#### 通用验证（所有场景）

1. 文档能成功上传和处理
2. 输出结构正确（包含期望的字段）
3. 字段不为空
4. 置信度和来源字段格式正确（如果要求）

#### 场景特定验证

**技术文档**：
- 学习路径至少包含一个阶段
- 每个阶段包含stage、title、content字段
- 前置条件包含required和recommended字段
- 学习方法包含theory和practice字段

**面试题文档**：
- 生成的问题列表不为空
- 内容总结包含key_points、question_types、difficulty、total_questions
- 答案提取包含answers列表

**架构文档**：
- 配置步骤列表不为空
- 组件识别列表不为空
- 架构视图不为空
- 白话解释不为空
- 检查清单包含items字段

## API失败模拟

### 功能说明

API失败模拟用于测试系统在API调用失败时的错误处理能力。支持模拟多种失败场景：

- **timeout**：超时错误
- **rate_limit**：限流错误（429）
- **server_error**：服务器错误（500）
- **network_error**：网络错误
- **invalid_response**：无效响应
- **unauthorized**：认证失败（401）
- **bad_request**：请求错误（400）
- **service_unavailable**：服务不可用（503）

### 配置

在 `.env` 文件中配置：

```bash
# 启用AI Mock（仅测试环境）
ENABLE_AI_MOCK=true
AI_MOCK_FAILURE_TYPE=timeout
AI_MOCK_FAILURE_PROBABILITY=0.3  # 30%失败概率
```

**重要**：生产环境必须设置 `ENABLE_AI_MOCK=false`。

### 使用场景

1. **测试错误处理**：验证系统在API失败时能否正确处理
2. **测试重试机制**：验证重试逻辑是否正常工作
3. **测试降级策略**：验证系统在API不可用时的降级处理

### 重试机制

系统实现了自动重试机制，使用 `tenacity` 库：

- **最大重试次数**：3次
- **重试策略**：指数退避（2秒、4秒、8秒）
- **可重试错误**：
  - 超时错误（TimeoutError）
  - 网络错误（ConnectionError）
  - 限流错误（429）
  - 服务器错误（5xx）

## 结果稳定性监控

### 功能说明

结果稳定性监控用于收集和分析AI调用的指标、结果质量和一致性数据。

### 监控数据表

系统创建了三个监控数据表：

1. **ai_call_metrics**：AI调用指标
   - 调用类型、模型、状态
   - 响应时间、错误类型、重试次数
   
2. **ai_result_quality**：AI结果质量
   - 字段完整性、置信度统计
   - 来源完整性、综合质量分数
   
3. **ai_result_consistency**：AI结果一致性（可选）
   - 字段值哈希、置信度差异
   - 用于对比多次运行的结果

### 配置

在 `.env` 文件中配置：

```bash
# 启用AI监控
ENABLE_AI_MONITORING=true
MONITORING_RETENTION_DAYS=30  # 监控数据保留30天
```

### 监控指标

#### AI调用指标

- **调用类型**：chat_completion、generate_json、generate_with_sources
- **状态**：success、timeout、error_400、error_429、error_500等
- **响应时间**：毫秒级响应时间统计
- **错误类型**：timeout、rate_limit、server_error、network_error等
- **重试次数**：记录每次调用的重试次数

#### 结果质量指标

- **字段完整性**：有置信度字段的占比（0-1）
- **置信度统计**：平均、最小、最大置信度
- **来源完整性**：有来源字段的占比（0-1）
- **综合质量分数**：加权平均质量分数（0-100）

#### 结果一致性指标

- **字段值哈希**：用于对比多次运行的结果
- **置信度差异**：与基准对比的置信度差异

### 数据查询

#### 查询AI调用指标

```sql
-- 查询最近24小时的调用统计
SELECT 
    status,
    COUNT(*) as count,
    AVG(response_time_ms) as avg_response_time,
    MAX(response_time_ms) as max_response_time
FROM ai_call_metrics
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY status;
```

#### 查询结果质量

```sql
-- 查询最近7天的质量统计
SELECT 
    document_type,
    AVG(quality_score) as avg_quality,
    AVG(confidence_avg) as avg_confidence,
    AVG(sources_completeness) as avg_sources_completeness
FROM ai_result_quality
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY document_type;
```

### 监控告警

建议设置以下监控告警：

1. **API调用失败率**：超过10%时告警
2. **平均响应时间**：超过5秒时告警
3. **结果质量分数**：低于60分时告警
4. **重试率**：超过20%时告警

## 使用指南

### 1. 运行回归测试

```bash
# 准备测试文档（如果还没有）
cp uploads/your_technical_doc.pdf backend/tests/fixtures/test_documents/test_technical.pdf
cp uploads/your_interview_doc.docx backend/tests/fixtures/test_documents/test_interview.docx
cp test_document.md backend/tests/fixtures/test_documents/test_architecture.md

# 运行测试
docker-compose exec backend pytest backend/tests/test_regression/ -v
```

### 2. 测试API失败处理

```bash
# 在.env中配置Mock
ENABLE_AI_MOCK=true
AI_MOCK_FAILURE_TYPE=timeout
AI_MOCK_FAILURE_PROBABILITY=0.5

# 重启服务
docker-compose restart backend

# 上传文档测试
# 应该看到超时错误和重试日志
```

### 3. 查看监控数据

```bash
# 连接数据库
docker-compose exec postgres psql -U it_doc_helper -d it_doc_helper

# 查询调用指标
SELECT * FROM ai_call_metrics ORDER BY created_at DESC LIMIT 10;

# 查询结果质量
SELECT * FROM ai_result_quality ORDER BY created_at DESC LIMIT 10;
```

### 4. 生成测试报告

```bash
# 运行测试并生成HTML报告
docker-compose exec backend pytest backend/tests/test_regression/ -v \
    --html=backend/tests/reports/report.html \
    --self-contained-html

# 查看报告
open backend/tests/reports/report.html
```

## 注意事项

1. **测试文档固定性**：确保测试文档内容固定，避免测试结果不稳定
2. **Mock服务安全**：生产环境必须禁用Mock服务（`ENABLE_AI_MOCK=false`）
3. **监控数据清理**：定期清理过期的监控数据，避免数据库膨胀
4. **测试时间**：回归测试可能需要较长时间（5-10分钟），请耐心等待
5. **API依赖**：测试需要真实的DeepSeek API调用，确保API密钥配置正确

## 故障排查

### 测试失败

1. **检查测试文档是否存在**
   ```bash
   ls -lh backend/tests/fixtures/test_documents/
   ```

2. **检查服务是否正常运行**
   ```bash
   docker-compose ps
   ```

3. **查看测试日志**
   ```bash
   docker-compose logs backend | grep -i test
   ```

### 监控数据缺失

1. **检查监控是否启用**
   ```bash
   grep ENABLE_AI_MONITORING .env
   ```

2. **检查数据库表是否存在**
   ```bash
   docker-compose exec postgres psql -U it_doc_helper -d it_doc_helper -c "\dt ai_*"
   ```

3. **运行数据库迁移**
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

## 相关文档

- [测试文档](../tests/README.md)
- [技术方案设计](../../.trae/documents/ai_testing_monitoring_design.md)
- [需求文档](../../.trae/documents/ai_testing_monitoring_requirements.md)

