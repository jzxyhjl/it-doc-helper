# 实施计划 - AI服务自动回归测试、失败模拟和稳定性监控

## 任务拆分

### 任务0: 搭建pytest测试框架基础

**优先级**: P0
**预计工作量**: 2-3天
**依赖**: 无

**具体要做的事情**:
- 创建 `backend/tests/` 目录结构
- 创建 `backend/tests/conftest.py`，配置pytest
- 安装测试依赖（pytest, pytest-asyncio, pytest-mock, pytest-html）
- 创建测试辅助函数（`backend/tests/utils/test_helpers.py`）
  - `upload_test_document()` - 上传测试文档
  - `trigger_processing()` - 触发文档处理
  - `wait_for_completion()` - 等待处理完成
  - `monitor_progress()` - 监听进度更新
- 创建通用验证函数（`backend/tests/utils/validators.py`）
  - `validate_confidence_and_sources()` - 验证置信度和来源字段
  - `validate_result_structure()` - 验证结果结构
- 配置测试环境变量（`.env.test`）
- 编写测试文档说明（`backend/tests/README.md`）

**需求**: REQ-1.1, REQ-1.2

---

### 任务1: 创建统一的测试基础框架

**优先级**: P0
**预计工作量**: 2-3天
**依赖**: 任务0

**具体要做的事情**:
- 创建 `backend/tests/test_regression/test_base.py`
- 实现 `test_document_processing_base()` 函数
  - 统一的文档上传流程
  - 统一的处理触发流程
  - 统一的等待完成流程
  - 统一的基础结构验证（document_type, status, result字段）
  - 统一的置信度和来源验证
- 实现场景特定字段验证接口（可扩展）
- 编写单元测试验证基础框架功能
- 更新测试文档说明

**需求**: REQ-1.1, REQ-1.2, REQ-1.3

---

### 任务2: 准备测试文档和测试数据

**优先级**: P0
**预计工作量**: 1-2天
**依赖**: 任务0

**具体要做的事情**:
- 创建 `backend/tests/fixtures/test_documents/` 目录
- 准备三个固定测试文档：
  - `test_technical.pdf` - 技术文档（如Python教程）
  - `test_interview.docx` - 面试题文档（如Java面试题）
  - `test_architecture.md` - 架构文档（如Spring Boot搭建文档）
- 确保测试文档内容固定，便于结果可复现
- 创建测试文档说明（`backend/tests/fixtures/README.md`）
  - 文档来源
  - 文档内容说明
  - 预期处理结果说明（可选）

**需求**: REQ-1.4

---

### 任务3: 实现技术文档回归测试

**优先级**: P0
**预计工作量**: 2-3天
**依赖**: 任务1, 任务2

**具体要做的事情**:
- 创建 `backend/tests/test_regression/test_technical_document.py`
- 实现 `test_technical_document_processing()` 测试用例
  - 调用 `test_document_processing_base()` 基础框架
  - 验证4个主要字段：`prerequisites`, `learning_path`, `learning_methods`, `related_technologies`
- 实现场景特定验证：
  - 验证学习路径的完整性（阶段数量、每个阶段的字段）
  - 验证前置条件的结构（required/recommended）
  - 验证技术关联的结构（technologies列表）
- 编写测试用例文档说明
- 运行测试验证功能

**需求**: REQ-1.2, REQ-1.3

---

### 任务4: 实现面试题文档回归测试

**优先级**: P0
**预计工作量**: 2-3天
**依赖**: 任务1, 任务2

**具体要做的事情**:
- 创建 `backend/tests/test_regression/test_interview_document.py`
- 实现 `test_interview_document_processing()` 测试用例
  - 调用 `test_document_processing_base()` 基础框架
  - 验证3个主要字段：`summary`, `generated_questions`, `extracted_answers`
- 实现场景特定验证：
  - 验证问题生成的准确性（问题格式、答案格式）
  - 验证内容总结的结构（key_points, question_types, difficulty, total_questions）
  - 验证答案提取的结构（answers列表）
- 编写测试用例文档说明
- 运行测试验证功能

**需求**: REQ-1.2, REQ-1.3

---

### 任务5: 实现架构文档回归测试（重点）

**优先级**: P0
**预计工作量**: 3-4天
**依赖**: 任务1, 任务2

**具体要做的事情**:
- 创建 `backend/tests/test_regression/test_architecture_document.py`
- 实现 `test_architecture_document_processing()` 测试用例
  - 调用 `test_document_processing_base()` 基础框架
  - 验证6个主要字段：`config_steps`, `components`, `architecture_view`, `plain_explanation`, `checklist`, `related_technologies`
- 实现场景特定验证：
  - 验证配置步骤的完整性（步骤数量、每个步骤的字段）
  - 验证组件识别的结构（components列表）
  - 验证架构视图的格式（可能包含Mermaid代码）
  - 验证白话解释的格式（文本内容）
  - 验证检查清单的结构（items列表）
- 实现 `test_architecture_progress_callback()` 测试用例
  - 监听进度更新
  - 验证5个步骤的进度回调（步骤1/5到步骤5/5）
  - 验证进度回调的stage信息包含正确的步骤描述
- 实现长文本处理测试（可选）
  - 测试文档内容超过20000字符时的截断逻辑
- 编写测试用例文档说明
- 运行测试验证功能

**需求**: REQ-1.2, REQ-1.3

---

### 任务6: 实现测试报告生成

**优先级**: P0
**预计工作量**: 1-2天
**依赖**: 任务3, 任务4, 任务5

**具体要做的事情**:
- 配置pytest-html生成HTML测试报告
- 创建测试报告模板（可选，自定义报告格式）
- 实现测试结果统计：
  - 总测试数、通过数、失败数
  - 每个场景的测试结果
  - 测试执行时间
  - 失败原因汇总
- 实现测试报告保存（`backend/tests/reports/`）
- 更新测试文档说明报告查看方法

**需求**: REQ-1.1

---

### 任务7: 实现API失败模拟服务

**优先级**: P0
**预计工作量**: 3-4天
**依赖**: 无

**具体要做的事情**:
- 创建 `backend/app/services/ai_mock_service.py`
- 实现 `MockFailureType` 枚举（timeout, rate_limit, server_error, network_error, invalid_response）
- 实现 `AIMockService` 类：
  - `__init__()` - 初始化Mock服务（failure_type, failure_probability）
  - `mock_chat_completion()` - 模拟chat_completion调用
  - `_simulate_failure()` - 模拟各种失败场景
  - `_real_call()` - 真实API调用（Mock禁用时）
- 实现超时模拟：
  - 设置超时时间（30秒、60秒）
  - 抛出 `asyncio.TimeoutError`
- 实现错误状态码模拟：
  - 400 Bad Request
  - 401 Unauthorized
  - 429 Too Many Requests（包含Retry-After头）
  - 500 Internal Server Error
  - 503 Service Unavailable
- 实现无效响应模拟：
  - 空响应
  - JSON解析失败
  - 格式错误
- 实现失败概率控制（通过 `failure_probability` 参数）
- 添加环境变量配置支持（`.env`）：
  - `ENABLE_AI_MOCK` - 启用/禁用Mock
  - `AI_MOCK_FAILURE_TYPE` - 失败类型
  - `AI_MOCK_FAILURE_PROBABILITY` - 失败概率
- 编写单元测试验证Mock功能
- 更新配置文档说明

**需求**: REQ-2.1, REQ-2.2

---

### 任务8: 集成Mock服务到AI服务

**优先级**: P0
**预计工作量**: 2-3天
**依赖**: 任务7

**具体要做的事情**:
- 修改 `backend/app/services/ai_service.py`
- 在 `AIService.__init__()` 中初始化Mock服务（如果启用）
- 在 `chat_completion()` 方法中集成Mock调用：
  - 如果Mock启用，先调用Mock服务
  - 如果Mock返回失败，抛出相应异常
  - 如果Mock未启用或返回成功，调用真实API
- 确保Mock服务不影响生产环境（通过环境变量控制）
- 添加日志记录Mock使用情况
- 编写集成测试验证Mock集成
- 更新AI服务文档说明

**需求**: REQ-2.2, REQ-4.1

---

### 任务9: 实现AI服务重试机制

**优先级**: P0
**预计工作量**: 2-3天
**依赖**: 任务8

**具体要做的事情**:
- 安装 `tenacity` 库（重试库）
- 修改 `backend/app/services/ai_service.py`
- 在 `chat_completion()` 方法上添加重试装饰器：
  - 最多重试3次
  - 指数退避策略（multiplier=1, min=2秒, max=10秒）
  - 只对特定异常重试（TimeoutError, ConnectionError, 429错误）
- 实现重试计数记录（记录到监控系统）
- 实现重试日志记录
- 编写单元测试验证重试机制
- 测试各种失败场景下的重试行为

**需求**: REQ-2.3

---

### 任务10: 实现AI服务降级策略

**优先级**: P1
**预计工作量**: 2-3天
**依赖**: 任务9

**具体要做的事情**:
- 修改 `backend/app/services/ai_service.py`
- 实现 `chat_completion_with_fallback()` 方法：
  - 先尝试正常调用
  - 如果失败，尝试使用缓存结果
  - 如果缓存不存在，返回默认值
- 实现缓存机制（可选，使用Redis）：
  - `_get_cached_result()` - 从缓存获取结果
  - `_set_cached_result()` - 保存结果到缓存
- 实现默认值生成：
  - `_get_default_response()` - 根据消息内容生成默认响应
- 实现降级日志记录
- 编写单元测试验证降级策略
- 测试各种失败场景下的降级行为

**需求**: REQ-2.4

---

### 任务11: 创建监控数据表

**优先级**: P0
**预计工作量**: 1-2天
**依赖**: 无

**具体要做的事情**:
- 创建Alembic迁移脚本
- 创建 `ai_call_metrics` 表：
  - id, document_id, call_type, model, status, response_time_ms
  - error_type, error_message, retry_count, created_at
  - 创建索引（document_id, created_at, status）
- 创建 `ai_result_quality` 表：
  - id, document_id, document_type, field_completeness
  - confidence_avg, confidence_min, confidence_max
  - sources_count, sources_completeness, quality_score, created_at
  - 创建索引（document_id, document_type, created_at, quality_score）
- 创建 `ai_result_consistency` 表（可选）：
  - id, document_id, test_run_id, field_name, field_value_hash
  - confidence_diff, created_at
  - 创建索引（document_id, test_run_id）
- 运行数据库迁移
- 验证表结构正确性

**需求**: REQ-3.4

---

### 任务12: 实现监控数据收集服务

**优先级**: P0
**预计工作量**: 3-4天
**依赖**: 任务11

**具体要做的事情**:
- 创建 `backend/app/services/ai_monitor.py`
- 实现 `AIMonitor` 类：
  - `record_api_call()` - 记录API调用指标
  - `record_result_quality()` - 记录结果质量指标
  - `check_consistency()` - 检查结果一致性（可选）
- 实现 `record_api_call()` 方法：
  - 接收参数：document_id, call_type, status, response_time_ms, error_type, error_message, retry_count
  - 插入数据到 `ai_call_metrics` 表
  - 异步执行，不阻塞主流程
- 实现 `record_result_quality()` 方法：
  - 接收参数：document_id, document_type, quality_metrics
  - 计算质量指标（field_completeness, confidence_avg, sources_completeness等）
  - 插入数据到 `ai_result_quality` 表
- 实现 `check_consistency()` 方法（可选）：
  - 对比当前结果和基准结果
  - 计算置信度差异
  - 记录到 `ai_result_consistency` 表
- 编写单元测试验证监控功能
- 更新监控服务文档说明

**需求**: REQ-3.1, REQ-3.2

---

### 任务13: 集成监控服务到AI服务

**优先级**: P0
**预计工作量**: 2-3天
**依赖**: 任务12

**具体要做的事情**:
- 修改 `backend/app/services/ai_service.py`
- 在 `chat_completion()` 方法中集成监控：
  - 记录调用开始时间
  - 调用成功后记录成功指标（status=success, response_time_ms）
  - 调用失败后记录失败指标（status=failed, error_type, error_message）
  - 记录重试次数（如果有重试）
- 修改 `backend/app/tasks/document_processing.py`
- 在文档处理完成后集成质量监控：
  - 调用 `AIMonitor.record_result_quality()`
  - 计算质量指标（field_completeness, confidence_avg等）
- 确保监控数据收集不阻塞主流程（异步执行）
- 添加监控开关（环境变量 `ENABLE_AI_MONITORING`）
- 编写集成测试验证监控集成
- 更新文档说明

**需求**: REQ-3.1, REQ-4.1

---

### 任务14: 实现监控数据查询API

**优先级**: P1
**预计工作量**: 2-3天
**依赖**: 任务13

**具体要做的事情**:
- 创建 `backend/app/api/v1/internal/monitoring.py`
- 实现 `GET /api/v1/internal/monitoring/ai-calls` 接口：
  - 查询参数：start_time, end_time, group_by (hour/day)
  - 返回API调用统计（成功率、响应时间、错误分布）
  - 实现数据聚合（按小时/按天）
- 实现 `GET /api/v1/internal/monitoring/result-quality` 接口：
  - 查询参数：start_time, end_time, document_type (可选)
  - 返回结果质量统计（平均质量分数、置信度分布、趋势）
- 实现数据查询逻辑：
  - 使用SQLAlchemy查询数据库
  - 实现时间范围过滤
  - 实现数据聚合（COUNT, AVG, MAX, MIN）
- 添加API访问控制（IP白名单或API密钥）
- 编写API测试验证功能
- 更新API文档说明

**需求**: REQ-3.4, REQ-3.5

---

### 任务15: 实现监控报告生成

**优先级**: P1
**预计工作量**: 2-3天
**依赖**: 任务14

**具体要做的事情**:
- 创建 `backend/app/services/monitoring_report.py`
- 实现 `generate_monitoring_report()` 方法：
  - 接收参数：start_time, end_time
  - 生成监控报告（API调用统计、结果质量统计、质量趋势、异常情况汇总）
- 实现报告内容：
  - API调用统计（成功率、平均响应时间、错误分布）
  - 结果质量统计（平均质量分数、置信度分布）
  - 质量趋势图表数据（可选，返回数据供前端渲染）
  - 异常情况汇总（低质量结果、高错误率等）
- 实现报告导出功能（JSON格式）
- 创建报告生成API（可选）：
  - `GET /api/v1/internal/monitoring/report`
- 编写单元测试验证报告生成
- 更新文档说明

**需求**: REQ-3.5

---

### 任务16: 实现告警机制（可选）

**优先级**: P2
**预计工作量**: 2-3天
**依赖**: 任务13

**具体要做的事情**:
- 创建 `backend/app/services/monitoring_alert.py`
- 实现告警规则：
  - API成功率 < 90%：警告
  - API成功率 < 80%：严重告警
  - 平均响应时间 > 5秒：警告
  - 结果质量分数 < 60：警告
- 实现告警触发逻辑：
  - 定期检查监控指标（每5分钟）
  - 如果触发告警规则，记录告警信息
- 实现告警通知（可选）：
  - 记录到日志
  - 发送邮件（可选）
  - 发送Webhook（可选）
- 实现告警历史记录
- 编写单元测试验证告警功能
- 更新文档说明

**需求**: REQ-3.6

---

### 任务17: 集成CI/CD（可选）

**优先级**: P1
**预计工作量**: 2-3天
**依赖**: 任务6

**具体要做的事情**:
- 创建 `.github/workflows/regression-tests.yml`（GitHub Actions）
- 配置CI/CD流程：
  - 代码提交时自动触发
  - 启动Docker服务
  - 运行回归测试
  - 生成测试报告
  - 如果测试失败，阻止代码合并
- 实现测试结果通知（可选）：
  - 发送测试结果到Slack
  - 发送测试报告到邮件
- 配置测试环境变量
- 编写CI/CD文档说明
- 测试CI/CD流程

**需求**: REQ-1.5

---

### 任务18: 编写测试和监控文档

**优先级**: P0
**预计工作量**: 1-2天
**依赖**: 任务6, 任务13

**具体要做的事情**:
- 创建 `docs/testing/REGRESSION_TEST_GUIDE.md`
  - 测试框架说明
  - 如何运行回归测试
  - 如何查看测试报告
  - 如何添加新的测试用例
- 创建 `docs/monitoring/MONITORING_GUIDE.md`
  - 监控系统说明
  - 如何查看监控数据
  - 如何配置告警
  - 监控指标说明
- 更新 `README.md`，添加测试和监控说明
- 更新 `docs/5_系统测试.md`，添加回归测试说明

**需求**: REQ-4.3

---

## 实施顺序建议

### 第一阶段（P0核心功能，2-3周）

**并行任务**：
- 任务0: 搭建pytest测试框架基础
- 任务7: 实现API失败模拟服务
- 任务11: 创建监控数据表

**顺序任务**：
1. 任务1: 创建统一的测试基础框架（依赖任务0）
2. 任务2: 准备测试文档和测试数据（依赖任务0）
3. 任务3: 实现技术文档回归测试（依赖任务1, 任务2）
4. 任务4: 实现面试题文档回归测试（依赖任务1, 任务2）
5. 任务5: 实现架构文档回归测试（依赖任务1, 任务2）
6. 任务6: 实现测试报告生成（依赖任务3, 任务4, 任务5）
7. 任务8: 集成Mock服务到AI服务（依赖任务7）
8. 任务9: 实现AI服务重试机制（依赖任务8）
9. 任务12: 实现监控数据收集服务（依赖任务11）
10. 任务13: 集成监控服务到AI服务（依赖任务12）
11. 任务18: 编写测试和监控文档（依赖任务6, 任务13）

**里程碑**: 
- 回归测试框架完成，三个场景测试通过
- API失败模拟功能完成，容错机制验证通过
- 监控数据收集完成，数据正常记录

---

### 第二阶段（P1重要功能，1-2周）

**顺序任务**：
1. 任务10: 实现AI服务降级策略（依赖任务9）
2. 任务14: 实现监控数据查询API（依赖任务13）
3. 任务15: 实现监控报告生成（依赖任务14）
4. 任务17: 集成CI/CD（依赖任务6，可选）

**里程碑**: 
- 降级策略完成，系统容错能力增强
- 监控查询和报告功能完成

---

### 第三阶段（P2可选功能，1周）

**顺序任务**：
1. 任务16: 实现告警机制（依赖任务13，可选）

**里程碑**: 
- 告警机制完成（可选）

---

## 工作量估算

| 优先级 | 任务数 | 预计工作量 | 说明 |
|--------|--------|-----------|------|
| P0 | 11个 | 25-35天 | 核心功能，必须完成 |
| P1 | 4个 | 8-12天 | 重要功能，建议完成 |
| P2 | 1个 | 2-3天 | 可选功能 |
| **总计** | **16个** | **35-50天** | **约5-7周** |

**优化后的时间安排**：
- 第一阶段（2-3周）：P0核心功能
- 第二阶段（1-2周）：P1重要功能
- 第三阶段（1周）：P2可选功能

**实际工期**: 约5-7周（按单人开发估算）

---

## 风险与注意事项

### 技术风险

1. **测试文档稳定性**
   - 风险：测试文档内容变化导致测试结果不稳定
   - 应对：使用固定版本的测试文档，版本控制管理

2. **Mock服务复杂性**
   - 风险：Mock服务可能影响真实API调用
   - 应对：通过环境变量严格控制，生产环境强制禁用

3. **监控数据量**
   - 风险：监控数据量过大，影响数据库性能
   - 应对：定期清理历史数据，设置数据保留期限

### 业务风险

1. **测试时间**
   - 风险：回归测试执行时间过长
   - 应对：优化测试用例，并行执行测试

2. **监控开销**
   - 风险：监控数据收集影响系统性能
   - 应对：异步执行监控，批量写入数据

---

## 验收标准总结

### 核心功能（P0）验收

- ✅ 回归测试框架完成，三个场景测试通过
- ✅ 测试报告生成正常，包含测试结果统计
- ✅ API失败模拟功能完成，各种失败场景可模拟
- ✅ AI服务重试机制完成，超时和网络错误可自动重试
- ✅ 监控数据收集完成，API调用和结果质量数据正常记录
- ✅ 监控数据查询API正常工作

### 重要功能（P1）验收

- ✅ 降级策略完成，API失败时可使用缓存或默认值
- ✅ 监控报告生成完成，可生成JSON格式报告
- ✅ CI/CD集成完成（可选），代码提交时自动运行测试

### 可选功能（P2）验收

- ✅ 告警机制完成（可选），异常情况可触发告警

---

**文档版本**：v1.0
**创建时间**：2025-12-19
**最后更新**：2025-12-19

