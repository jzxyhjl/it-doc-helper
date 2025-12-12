# 前端完整测试指南

## 测试环境

### 服务状态检查

**后端服务**:
- API服务: http://localhost:8000
- 健康检查: http://localhost:8000/health
- API文档: http://localhost:8000/docs

**前端服务**:
- 开发服务器: http://localhost:5173/it-doc-helper (或自动分配的端口，如5176)
- 代理配置: `/api` -> `http://localhost:8000`
- WebSocket: `/ws` -> `ws://localhost:8000`
- **注意**: 如果5173端口被占用，Vite会自动使用下一个可用端口

## 测试流程

### 1. 启动服务

```bash
# 启动后端服务（Docker）
cd /Users/ggsk/Cursor/it-helper
docker-compose up -d

# 启动前端服务
cd frontend
npm install  # 如果还没安装依赖
npm run dev
```

### 2. 访问前端界面

打开浏览器访问: **http://localhost:5173/it-doc-helper**

### 3. 功能测试

#### 3.1 文档上传测试

1. **进入上传页面**
   - 点击导航栏的"上传文档"
   - 或直接访问: http://localhost:5173/it-doc-helper/upload

2. **上传文档**
   - 拖拽文件到上传区域，或点击选择文件
   - 支持格式: PDF, DOCX, PPTX, MD, TXT
   - 文件大小限制: 30MB

3. **验证上传**
   - 上传成功后应自动跳转到进度页面
   - URL应包含 `document_id` 和 `task_id`

#### 3.2 实时进度测试

1. **进度页面**
   - 自动显示处理进度（0-100%）
   - 显示当前处理阶段
   - 进度条实时更新

2. **WebSocket连接**
   - 检查浏览器控制台，确认WebSocket连接成功
   - 观察进度实时更新（不刷新页面）

3. **进度状态**
   - `pending`: 等待处理
   - `running`: 处理中
   - `completed`: 处理完成
   - `failed`: 处理失败

#### 3.3 处理结果测试

1. **结果展示**
   - 处理完成后自动跳转到结果页面
   - 根据文档类型显示不同格式的结果

2. **技术文档结果**
   - 显示学习路径（阶段列表）
   - 显示前置条件（必需和推荐）
   - 显示学习方法（理论和实践）
   - 显示相关技术

3. **面试题文档结果**
   - 显示内容摘要
   - 显示生成的新问题
   - 显示答案提取

4. **架构文档结果**
   - 显示配置流程
   - 显示组件全景视图
   - 显示白话解释

#### 3.4 历史记录测试

1. **访问历史页面**
   - 点击导航栏的"历史记录"
   - 或访问: http://localhost:5173/it-doc-helper/history

2. **查看历史**
   - 显示所有已处理的文档列表
   - 显示文档信息（文件名、类型、状态、时间）
   - 支持分页和筛选

3. **查看详情**
   - 点击文档可查看详细信息
   - 可重新查看处理结果

## API测试（命令行）

### 上传文档

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@test_document.md" | python3 -m json.tool
```

### 查询进度

```bash
DOCUMENT_ID="your-document-id"
curl http://localhost:8000/api/v1/documents/$DOCUMENT_ID/progress | python3 -m json.tool
```

### 查询结果

```bash
DOCUMENT_ID="your-document-id"
curl http://localhost:8000/api/v1/documents/$DOCUMENT_ID/result | python3 -m json.tool
```

### 查询历史

```bash
curl "http://localhost:8000/api/v1/history?page=1&page_size=10" | python3 -m json.tool
```

## WebSocket测试

### 连接WebSocket

```javascript
// 在浏览器控制台执行
const ws = new WebSocket('ws://localhost:8000/ws/task_progress/your-task-id')
ws.onmessage = (event) => {
  console.log('收到进度更新:', JSON.parse(event.data))
}
```

## 测试检查清单

### 前端功能
- [ ] 页面加载正常
- [ ] 导航栏工作正常
- [ ] 文件上传功能正常
- [ ] 进度显示实时更新
- [ ] 结果页面正确显示
- [ ] 历史记录页面正常
- [ ] 错误提示友好

### 后端集成
- [ ] API调用成功
- [ ] 文件上传到服务器
- [ ] 处理任务正确启动
- [ ] 进度更新及时
- [ ] 结果保存正确
- [ ] WebSocket连接稳定

### 用户体验
- [ ] 界面美观（轻松风格）
- [ ] 操作流畅
- [ ] 加载状态清晰
- [ ] 错误提示明确
- [ ] 响应速度快

## 已知测试文档

**测试文档ID**: `7849b02b-c251-4b95-a96d-b2e059ed2ae0`
- 状态: completed
- 类型: technical
- 处理时间: 72秒

可用此ID直接测试结果查看功能。

## 故障排查

### 前端无法连接后端

1. 检查后端服务是否运行: `docker-compose ps`
2. 检查API健康状态: `curl http://localhost:8000/health`
3. 检查CORS配置是否正确

### WebSocket连接失败

1. 检查后端WebSocket端点: `ws://localhost:8000/ws/task_progress/{task_id}`
2. 检查浏览器控制台错误信息
3. 确认task_id是否正确

### 进度不更新

1. 检查Worker服务是否运行: `docker-compose logs worker`
2. 检查Redis连接: `docker exec it-helper-redis redis-cli ping`
3. 检查任务状态: 查询数据库 `processing_tasks` 表

---

**测试完成后，请记录测试结果和发现的问题！**

