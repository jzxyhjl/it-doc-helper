# 多视角API接口测试文档

## 概述

本文档描述了任务11、12、13实现的API接口的测试情况。

## 测试文件

- `backend/tests/test_regression/test_api_multi_view.py`

## 测试覆盖

### 任务11：上传接口支持views参数

#### 测试用例

1. **test_upload_without_views**
   - 测试上传文档时不指定views（应该自动推荐）
   - 状态：✅ 通过

2. **test_upload_with_single_view**
   - 测试上传文档时指定单个view（如：learning）
   - 状态：✅ 通过

3. **test_upload_with_multiple_views**
   - 测试上传文档时指定多个views（如：learning,system）
   - 状态：✅ 通过

4. **test_upload_with_invalid_view**
   - 测试上传文档时指定无效的view（应该返回400错误）
   - 状态：✅ 通过

#### API使用示例

```bash
# 不指定views（自动推荐）
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@document.pdf"

# 指定单个view
curl -X POST "http://localhost:8000/api/v1/documents/upload?views=learning" \
  -F "file=@document.pdf"

# 指定多个views
curl -X POST "http://localhost:8000/api/v1/documents/upload?views=learning,system" \
  -F "file=@document.pdf"

# 指定无效的view（返回400错误）
curl -X POST "http://localhost:8000/api/v1/documents/upload?views=invalid_view" \
  -F "file=@document.pdf"
```

### 任务12：推荐视角接口

#### 测试用例

1. **test_recommend_views_after_upload**
   - 测试推荐视角接口（需要先上传文档并等待内容提取完成）
   - 状态：⏳ 需要文档处理完成后测试

#### API使用示例

```bash
# 推荐视角（需要文档内容已提取）
curl -X POST "http://localhost:8000/api/v1/documents/{document_id}/recommend-views"
```

#### 返回结构

```json
{
  "primary_view": "learning",
  "enabled_views": ["learning", "system"],
  "detection_scores": {
    "learning": 0.85,
    "qa": 0.15,
    "system": 0.65
  },
  "cache_key": "...",
  "type_mapping": "technical",
  "method": "rule"
}
```

### 任务13：结果接口支持view和views参数

#### 测试用例

1. **test_get_result_without_params**
   - 测试获取结果时不指定view/views（应该返回完整容器）
   - 状态：⏳ 需要文档处理完成后测试

2. **test_get_result_with_single_view**
   - 测试获取结果时指定单个view
   - 状态：⏳ 需要文档处理完成后测试

3. **test_get_result_with_multiple_views**
   - 测试获取结果时指定多个views
   - 状态：⏳ 需要文档处理完成后测试

4. **test_get_result_with_invalid_view**
   - 测试获取结果时指定无效的view（应该返回400错误）
   - 状态：⏳ 需要文档处理完成后测试

#### API使用示例

```bash
# 获取完整多视角容器
curl "http://localhost:8000/api/v1/documents/{document_id}/result"

# 获取单个视角结果
curl "http://localhost:8000/api/v1/documents/{document_id}/result?view=learning"

# 获取多个视角结果
curl "http://localhost:8000/api/v1/documents/{document_id}/result?views=learning,system"
```

## 修复的问题

### 问题1：views参数验证返回500错误

**问题描述**：
- 当指定无效的view时，接口返回500错误而不是400错误
- 错误信息为空

**根本原因**：
- `HTTPException`被外层的`Exception`捕获，导致返回500错误

**解决方案**：
- 在异常处理中添加`except HTTPException: raise`，确保`HTTPException`不被外层`Exception`捕获
- 在views参数验证中添加try-except块，确保异常被正确捕获

**修复代码**：
```python
except HTTPException:
    raise  # 重新抛出HTTPException，不要被Exception捕获
except ValueError as e:
    # ...
except Exception as e:
    # ...
```

## 运行测试

### 运行所有多视角API测试

```bash
docker-compose exec backend python -m pytest tests/test_regression/test_api_multi_view.py -v
```

### 运行特定测试类

```bash
# 测试上传接口
docker-compose exec backend python -m pytest tests/test_regression/test_api_multi_view.py::TestUploadWithViews -v

# 测试推荐接口
docker-compose exec backend python -m pytest tests/test_regression/test_api_multi_view.py::TestRecommendViews -v

# 测试结果接口
docker-compose exec backend python -m pytest tests/test_regression/test_api_multi_view.py::TestGetResultWithViews -v
```

## 注意事项

1. **文档处理时间**：
   - 推荐视角和结果接口的测试需要等待文档处理完成
   - 处理时间取决于文档大小和复杂度
   - 建议在测试中使用较小的测试文档

2. **测试环境**：
   - 确保Docker容器正在运行
   - 确保数据库和Redis服务正常
   - 确保有测试文档可用

3. **测试文档**：
   - 测试文档位于`backend/tests/fixtures/test_documents/`
   - 需要准备实际的PDF、DOCX等测试文档

## 下一步

- [ ] 完成推荐视角接口的完整测试（需要文档处理完成）
- [ ] 完成结果接口的完整测试（需要文档处理完成）
- [ ] 添加集成测试，验证完整流程
- [ ] 添加性能测试，验证多视角处理的性能

