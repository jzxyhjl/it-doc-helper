# 集成测试指南 - 新功能验证

## 概述

本文档提供新功能的集成测试指南，包括可信度估计、来源片段引用、异常处理、文档大小控制和失败策略的测试方法。

## 测试环境准备

### 1. 启动服务

```bash
# 启动所有服务
docker-compose up -d

# 检查服务状态
docker-compose ps

# 查看日志
docker-compose logs -f backend
docker-compose logs -f worker
```

### 2. 验证服务健康

```bash
# 健康检查
curl http://localhost:8000/health

# 应该返回: {"status": "healthy"}
```

## 测试方法

### 方法1: 单元测试（服务组件测试）

在Docker容器中运行：

```bash
docker-compose exec backend python /app/test_unit_services.py
```

或在本地运行（需要安装依赖）：

```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
python ../test_unit_services.py
```

**测试内容**：
- ✅ 文本预处理服务
- ✅ 段落切分服务
- ✅ 可信度计算服务
- ✅ 文档大小验证服务

### 方法2: 集成测试（完整流程测试）

```bash
# 确保服务已启动
docker-compose up -d

# 运行集成测试
python3 test_integration_new_features.py
```

**测试内容**：
- ✅ 服务健康检查
- ✅ 文档上传
- ✅ 文档处理流程
- ✅ 可信度和来源片段验证
- ✅ 错误处理

### 方法3: 手动测试（前端功能测试）

#### 3.1 访问前端

```bash
# 开发环境
http://localhost:5173/it-doc-helper

# 生产环境
http://localhost/it-doc-helper
```

#### 3.2 测试正常流程

1. **上传技术文档**
   - 上传一个技术文档（如Python教程）
   - 观察处理进度
   - 查看结果页面，验证：
     - ✅ 可信度标签显示（高/中/低）
     - ✅ 来源片段完整展示
     - ✅ 每个部分都有可信度和来源

2. **上传面试题文档**
   - 上传一个面试题文档
   - 查看结果页面，验证：
     - ✅ 可信度和来源弱展示（默认隐藏）
     - ✅ 可点击展开查看详情

3. **上传架构文档**
   - 上传一个架构/配置文档
   - 查看结果页面，验证：
     - ✅ 可信度和来源弱展示
     - ✅ 可点击展开查看详情

#### 3.3 测试边界情况

1. **超长段落测试**
   - 创建一个包含超长段落（>2000字符）的文档
   - 验证段落切分是否正确处理

2. **低可信度测试**
   - 上传一个内容较少或质量较低的文档
   - 验证可信度标签是否为"低"

3. **高可信度测试**
   - 上传一个内容完整、结构清晰的文档
   - 验证可信度标签是否为"高"

#### 3.4 测试异常场景

1. **无效文件类型**
   ```bash
   # 尝试上传.exe文件
   curl -X POST http://localhost:8000/api/v1/documents/upload \
     -F "file=@test.exe"
   ```
   - 应该返回400错误，提示不支持的文件类型

2. **空文件**
   ```bash
   # 创建一个空文件
   touch empty.txt
   curl -X POST http://localhost:8000/api/v1/documents/upload \
     -F "file=@empty.txt"
   ```
   - 应该被拒绝或标记为failed/low_quality

3. **超大文件**
   ```bash
   # 创建一个超过30MB的文件（需要手动创建）
   # 应该被拒绝，提示文件过大
   ```

#### 3.5 测试失败策略

1. **AI调用失败**
   - 临时修改API密钥为错误值
   - 上传文档，观察是否：
     - ✅ 状态标记为failed
     - ✅ 有明确的错误信息
     - ✅ 有用户操作建议（重试、检查配置）

2. **处理超时**
   - 上传一个非常大的文档（>5MB）
   - 观察是否在600秒内超时
   - 验证：
     - ✅ 状态标记为timeout
     - ✅ 有明确的超时信息
     - ✅ 有用户操作建议（拆分文档）

3. **文件损坏**
   - 创建一个损坏的PDF文件
   - 上传并观察：
     - ✅ 状态标记为failed
     - ✅ 错误信息明确
     - ✅ 有用户操作建议（重新上传）

## 测试检查清单

### 核心功能
- [ ] 文本预处理正常工作
- [ ] 段落切分正常工作
- [ ] 可信度计算正常工作
- [ ] 文档大小验证正常工作
- [ ] AI服务返回source_ids和confidence
- [ ] 处理器正确集成所有新服务
- [ ] 前端正确显示可信度和来源

### 技术文档（完整展示）
- [ ] 前置条件显示可信度和来源
- [ ] 学习路径每个阶段显示可信度和来源
- [ ] 学习方法建议显示可信度和来源
- [ ] 相关技术显示可信度和来源

### 面试题/架构文档（弱展示）
- [ ] 可信度和来源默认隐藏
- [ ] 可点击展开查看详情
- [ ] 展开后显示可信度标签
- [ ] 展开后显示来源片段列表

### 异常处理
- [ ] 段落切分失败时使用兜底策略
- [ ] 可信度计算失败时使用默认值
- [ ] AI返回格式错误时自动修正
- [ ] 处理器异常时正确降级处理
- [ ] 前端数据缺失时正确显示

### 失败策略
- [ ] AI调用失败时标记为failed
- [ ] 任务超时时标记为timeout
- [ ] 文件损坏时标记为failed
- [ ] 内容过少时标记为failed
- [ ] 内容过长时标记为failed
- [ ] 处理结果为空时标记为low_quality
- [ ] 所有失败情况都有明确的错误信息
- [ ] 所有失败情况都有用户操作建议

### 文档大小控制
- [ ] 文件大小超过30MB时被拒绝
- [ ] 文件大小20-30MB时显示警告
- [ ] 内容长度超过50万字符时被拒绝
- [ ] 内容长度30-50万字符时显示警告
- [ ] 处理时间估算准确
- [ ] 处理时间超过600秒时被拒绝

## API测试命令

### 健康检查
```bash
curl http://localhost:8000/health
```

### 上传文档
```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@test_document.md" | python3 -m json.tool
```

### 查看进度
```bash
DOCUMENT_ID="your-document-id"
curl http://localhost:8000/api/v1/documents/$DOCUMENT_ID/progress | python3 -m json.tool
```

### 查看结果
```bash
DOCUMENT_ID="your-document-id"
curl http://localhost:8000/api/v1/documents/$DOCUMENT_ID/result | python3 -m json.tool
```

### 验证结果结构
```bash
# 检查结果是否包含可信度和来源
curl http://localhost:8000/api/v1/documents/$DOCUMENT_ID/result | \
  python3 -c "import sys, json; data=json.load(sys.stdin); \
  print('可信度:', 'confidence' in str(data)); \
  print('来源:', 'sources' in str(data))"
```

## 测试报告

测试完成后，请填写 `test_integration_report.md` 文件，记录：
- 测试结果
- 发现的问题
- 已修复的问题
- 需要改进的功能

## 常见问题

### Q: 单元测试失败，提示模块未找到
A: 确保在Docker容器中运行，或已安装所有依赖：
```bash
docker-compose exec backend pip install -r requirements.txt
```

### Q: 集成测试无法连接到服务
A: 确保服务已启动：
```bash
docker-compose up -d
docker-compose ps
```

### Q: 前端无法显示可信度和来源
A: 检查：
1. 后端是否正确返回了confidence和sources字段
2. 前端组件是否正确导入
3. 浏览器控制台是否有错误

### Q: 处理失败但没有明确的错误信息
A: 检查：
1. 后端日志：`docker-compose logs backend`
2. Worker日志：`docker-compose logs worker`
3. 确认ProcessingException是否正确使用

## 下一步

完成测试后：
1. 记录测试结果到 `test_integration_report.md`
2. 修复发现的问题
3. 更新文档
4. 准备发布

