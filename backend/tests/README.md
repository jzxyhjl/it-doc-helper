# 测试文档

## 目录结构

```
backend/tests/
├── conftest.py              # pytest配置和fixtures
├── test_regression/         # 回归测试
│   ├── test_base.py        # 统一的测试基础框架
│   ├── test_technical_document.py
│   ├── test_interview_document.py
│   └── test_architecture_document.py
├── fixtures/               # 测试数据
│   └── test_documents/     # 固定测试文档
├── utils/                  # 测试工具
│   ├── test_helpers.py     # 测试辅助函数
│   └── validators.py       # 结果验证器
└── reports/                # 测试报告
```

## 运行测试

### 在Docker容器中运行

```bash
# 确保服务已启动
docker-compose up -d

# 运行所有回归测试（自动生成HTML报告）
docker-compose exec backend pytest backend/tests/test_regression/ -v

# 运行特定场景测试
docker-compose exec backend pytest backend/tests/test_regression/test_technical_document.py -v

# 查看测试报告
# 报告位置：backend/tests/reports/report.html
# 覆盖率报告：backend/tests/reports/coverage/index.html
```

### 在本地运行

```bash
# 安装依赖
cd backend
source venv/bin/activate
pip install -r requirements.txt

# 运行测试（自动生成HTML报告）
pytest tests/test_regression/ -v

# 查看测试报告
# 报告位置：tests/reports/report.html
# 覆盖率报告：tests/reports/coverage/index.html
```

### 测试报告说明

测试报告包含以下信息：
- 测试结果统计（总测试数、通过数、失败数、跳过数）
- 每个测试用例的执行结果
- 失败测试的详细错误信息
- 测试执行时间
- 代码覆盖率报告（可选）

报告文件：
- `tests/reports/report.html` - HTML格式测试报告
- `tests/reports/coverage/index.html` - 代码覆盖率报告

## 环境变量配置

测试相关的环境变量（`.env` 或 `.env.test`）：

```bash
# 测试配置
TEST_BASE_URL=http://localhost:8000
TEST_API_BASE=http://localhost:8000/api/v1
TEST_TIMEOUT=600

# AI Mock配置（测试环境）
ENABLE_AI_MOCK=false
AI_MOCK_FAILURE_TYPE=timeout
AI_MOCK_FAILURE_PROBABILITY=0.0

# 监控配置
ENABLE_AI_MONITORING=true
```

## 测试文档

测试文档存放在 `backend/tests/fixtures/test_documents/` 目录：

- `test_technical.pdf` - 技术文档测试用例
- `test_interview.docx` - 面试题文档测试用例
- `test_architecture.md` - 架构文档测试用例

**注意**：测试文档应该是固定版本，确保测试结果可复现。

## 测试报告

测试报告保存在 `backend/tests/reports/` 目录：

- `report.html` - HTML格式测试报告
- 包含测试结果统计、失败原因、执行时间等信息

## 添加新测试用例

1. 在 `test_regression/` 目录创建新的测试文件
2. 使用 `test_document_processing_base()` 基础框架
3. 实现场景特定的验证逻辑
4. 运行测试验证功能

## 注意事项

1. **测试文档固定性**：确保测试文档内容固定，避免测试结果不稳定
2. **测试环境隔离**：测试应该使用独立的测试环境，不影响生产数据
3. **测试时间**：回归测试可能需要较长时间（5-10分钟），请耐心等待
4. **API依赖**：测试需要真实的DeepSeek API调用，确保API密钥配置正确

