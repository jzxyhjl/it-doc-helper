# 操作日志

## 2025-12-18 05:45

### 操作类型：修改

### 影响文件：
- `frontend/src/components/FileUpload.tsx`
- `frontend/src/pages/Upload.tsx`
- `backend/app/api/v1/documents.py`
- `README.md`
- `docs/1_README.md`
- `docs/5_系统测试.md`
- `docs/6_问题排查.md`

### 变更摘要：
添加 .doc 格式的友好提示和文档说明，引导用户使用 .docx 格式

### 原因：
经过可行性分析，发现 .doc 格式支持存在中文编码风险和不稳定性，决定放弃实现。改为在前端和后端添加友好提示，引导用户转换为 .docx 格式。

### 具体变更：
1. **前端 FileUpload 组件**：
   - 添加 .doc 格式的特殊检测
   - 提供友好的错误提示，引导用户转换为 .docx
   - 在上传区域添加格式提示

2. **前端 Upload 页面**：
   - 添加醒目的格式提示框，说明不支持 .doc 格式

3. **后端 API**：
   - 优化错误信息，对 .doc 格式提供明确的转换建议

4. **文档更新**：
   - README.md：更新功能特性说明
   - docs/1_README.md：添加格式说明
   - docs/5_系统测试.md：添加格式限制说明
   - docs/6_问题排查.md：更新文件类型错误排查说明

### 测试状态：待测试

---

## 2025-12-18 06:30

### 操作类型：修改

### 影响文件：
- `backend/app/services/document_size_validator.py`
- `backend/app/tasks/document_processing.py`
- `docs/INTEGRATION_TEST_GUIDE.md`

### 变更摘要：
调整文档处理时间限制，从300秒提高到600秒，以支持更大的文档处理

### 原因：
7MB文档处理失败，原因是处理时间估算314秒超过了300秒的限制。为了提高系统对大文档的支持能力，将处理时间限制从5分钟提高到10分钟。

### 具体变更：
1. **DocumentSizeValidator**：
   - `PROCESS_TIME_WARNING`: 240秒 → 480秒（8分钟）
   - `PROCESS_TIME_MAX`: 300秒 → 600秒（10分钟）

2. **document_processing.py**：
   - `PROCESSING_TIMEOUT`: 300秒 → 600秒（10分钟）

3. **文档更新**：
   - `docs/INTEGRATION_TEST_GUIDE.md`: 更新超时测试说明

### 验证结果：
- 7MB文档（237416字符，架构类型）处理时间估算：314秒
- 新限制：600秒（10分钟）
- 状态：✅ 可以通过验证

### 测试状态：待测试

