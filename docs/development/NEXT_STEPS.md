# 下一步操作指南

## 已完成的工作

✅ 测试框架搭建完成
✅ API失败模拟服务实现
✅ 监控数据收集服务实现
✅ 测试文档准备完成（test_technical.pdf, test_interview.docx, test_architecture.md）

## 需要执行的步骤

### 1. 运行数据库迁移

在Docker容器中运行迁移，创建监控数据表：

```bash
# 确保服务已启动
docker-compose up -d

# 运行数据库迁移
docker-compose exec backend alembic upgrade head
```

或者使用迁移脚本：

```bash
docker-compose exec backend python scripts/run_migrations.py
```

**预期输出**：
```
INFO  [alembic.runtime.migration] Running upgrade bb57d8568340 -> 003_add_ai_monitoring, add_ai_monitoring_tables
```

### 2. 验证监控表创建

检查监控表是否创建成功：

```bash
docker-compose exec postgres psql -U it_doc_helper -d it_doc_helper -c "\dt ai_*"
```

**预期输出**：
```
                    List of relations
 Schema |           Name            | Type  |     Owner      
--------+---------------------------+-------+----------------
 public | ai_call_metrics          | table | it_doc_helper
 public | ai_result_consistency     | table | it_doc_helper
 public | ai_result_quality         | table | it_doc_helper
```

### 3. 配置监控服务（可选）

如果需要启用监控，在 `.env` 文件中添加：

```bash
# AI监控配置
ENABLE_AI_MONITORING=true
MONITORING_RETENTION_DAYS=30

# AI Mock配置（仅测试环境，生产环境必须为false）
ENABLE_AI_MOCK=false
AI_MOCK_FAILURE_TYPE=timeout
AI_MOCK_FAILURE_PROBABILITY=0.0
```

然后重启服务：

```bash
docker-compose restart backend
```

### 4. 运行回归测试

运行完整的回归测试套件：

```bash
# 运行所有回归测试
docker-compose exec backend pytest backend/tests/test_regression/ -v

# 运行特定场景测试
docker-compose exec backend pytest backend/tests/test_regression/test_technical_document.py -v
docker-compose exec backend pytest backend/tests/test_regression/test_interview_document.py -v
docker-compose exec backend pytest backend/tests/test_regression/test_architecture_document.py -v

# 生成HTML测试报告
docker-compose exec backend pytest backend/tests/test_regression/ -v \
    --html=backend/tests/reports/report.html \
    --self-contained-html
```

**注意**：
- 测试需要真实的DeepSeek API调用，确保API密钥配置正确
- 测试可能需要5-10分钟，请耐心等待
- 如果测试失败，检查日志：`docker-compose logs backend`

### 5. 查看测试报告

测试报告保存在 `backend/tests/reports/report.html`：

```bash
# 在容器中查看报告路径
docker-compose exec backend ls -lh backend/tests/reports/

# 或者将报告复制到本地
docker cp it-doc-helper-backend:/app/tests/reports/report.html ./test_report.html
```

### 6. 验证监控数据收集

上传一个测试文档，然后检查监控数据：

```bash
# 上传文档（通过API或前端）
# 等待处理完成

# 查询AI调用指标
docker-compose exec postgres psql -U it_doc_helper -d it_doc_helper -c "
SELECT 
    call_type,
    status,
    COUNT(*) as count,
    AVG(response_time_ms) as avg_response_time
FROM ai_call_metrics
GROUP BY call_type, status
ORDER BY created_at DESC
LIMIT 10;
"

# 查询结果质量
docker-compose exec postgres psql -U it_doc_helper -d it_doc_helper -c "
SELECT 
    document_type,
    AVG(quality_score) as avg_quality,
    AVG(confidence_avg) as avg_confidence
FROM ai_result_quality
GROUP BY document_type;
"
```

## 故障排查

### 迁移失败

如果迁移失败，检查：

1. **数据库连接**：
   ```bash
   docker-compose exec postgres psql -U it_doc_helper -d it_doc_helper -c "SELECT version();"
   ```

2. **迁移版本**：
   ```bash
   docker-compose exec backend alembic current
   docker-compose exec backend alembic history
   ```

3. **查看迁移文件**：
   ```bash
   docker-compose exec backend cat alembic/versions/003_add_ai_monitoring_tables.py
   ```

### 测试失败

如果测试失败，检查：

1. **测试文档是否存在**：
   ```bash
   docker-compose exec backend ls -lh backend/tests/fixtures/test_documents/
   ```

2. **服务是否正常运行**：
   ```bash
   docker-compose ps
   docker-compose logs backend | tail -50
   ```

3. **API密钥配置**：
   ```bash
   docker-compose exec backend env | grep DEEPSEEK
   ```

### 监控数据缺失

如果监控数据缺失，检查：

1. **监控是否启用**：
   ```bash
   docker-compose exec backend env | grep ENABLE_AI_MONITORING
   ```

2. **表是否存在**：
   ```bash
   docker-compose exec postgres psql -U it_doc_helper -d it_doc_helper -c "\dt ai_*"
   ```

3. **查看应用日志**：
   ```bash
   docker-compose logs backend | grep -i monitoring
   ```

## 快速验证清单

- [ ] 数据库迁移成功运行
- [ ] 监控表创建成功（3个表）
- [ ] 测试文档准备完成（3个文件）
- [ ] 回归测试可以运行
- [ ] 监控数据可以收集
- [ ] 测试报告可以生成

## 相关文档

- [AI测试和监控文档](./AI_TESTING_MONITORING.md)
- [测试README](../../backend/tests/README.md)
- [技术方案设计](../../.trae/documents/ai_testing_monitoring_design.md)

