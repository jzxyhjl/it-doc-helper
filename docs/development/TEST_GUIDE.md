# 系统测试指南

## 当前部署状态

### ✅ 已启动的服务

1. **PostgreSQL数据库** - 运行正常
2. **Redis缓存** - 运行正常  
3. **后端API服务** - 运行正常
4. **Celery Worker** - 运行正常

### ⚠️ 前端服务

前端服务构建遇到TypeScript编译问题，可以：
1. 本地运行前端进行测试
2. 或使用API文档直接测试后端功能

## 测试步骤

### 1. 检查服务状态

```bash
cd /Users/ggsk/Cursor/it-helper
docker-compose ps
```

### 2. 测试API健康检查

```bash
curl http://localhost:8000/health
```

预期响应：
```json
{"status": "healthy"}
```

### 3. 访问API文档

打开浏览器访问：
```
http://localhost:8000/docs
```

### 4. 测试文档上传（使用API文档）

1. 在API文档页面找到 `POST /api/v1/documents/upload`
2. 点击 "Try it out"
3. 选择一个测试文件（PDF/Word/PPT/Markdown/TXT）
4. 点击 "Execute"
5. 查看响应，获取 `document_id` 和 `task_id`

### 5. 测试获取处理进度

```bash
# 替换 {document_id} 为实际文档ID
curl http://localhost:8000/api/v1/documents/{document_id}/progress
```

### 6. 测试获取处理结果

```bash
# 替换 {document_id} 为实际文档ID
curl http://localhost:8000/api/v1/documents/{document_id}/result
```

### 7. 测试历史记录

```bash
curl http://localhost:8000/api/v1/documents/history
```

## 本地运行前端（可选）

如果需要在浏览器中测试完整功能：

```bash
cd frontend
npm install
npm run dev
```

然后访问：http://localhost:3000

## 查看日志

### 后端日志
```bash
docker-compose logs -f backend
```

### Worker日志
```bash
docker-compose logs -f worker
```

### 数据库日志
```bash
docker-compose logs -f postgres
```

## 常见问题

### 1. 后端启动失败

检查环境变量配置：
```bash
cat .env
```

确保 `POSTGRES_PASSWORD` 和 `DEEPSEEK_API_KEY` 已设置。

### 2. 数据库连接失败

检查数据库容器状态：
```bash
docker-compose ps postgres
docker-compose logs postgres
```

### 3. Celery任务不执行

检查Worker日志：
```bash
docker-compose logs worker
```

检查Redis连接：
```bash
docker-compose exec redis redis-cli ping
```

## 测试检查清单

- [ ] 所有容器运行正常
- [ ] API健康检查通过
- [ ] API文档可访问
- [ ] 文档上传功能正常
- [ ] 文档处理任务创建成功
- [ ] 处理进度可查询
- [ ] 处理结果可获取
- [ ] 历史记录可查询

## 下一步

1. 修复前端构建问题
2. 启动前端服务
3. 进行端到端测试
4. 性能测试

