# 快速启动指南

## Docker部署已成功！

### ✅ 当前运行的服务

- PostgreSQL数据库 ✅
- Redis缓存 ✅
- 后端API服务 ✅
- Celery Worker ✅

## 立即测试

### 1. 访问API文档

打开浏览器访问：
```
http://localhost:8000/docs
```

### 2. 测试文档上传

在API文档页面：
1. 找到 `POST /api/v1/documents/upload`
2. 点击 "Try it out"
3. 选择一个测试文件（PDF/Word/PPT/Markdown/TXT，<30MB）
4. 点击 "Execute"
5. 查看响应，获取 `document_id`

### 3. 查看处理进度

在API文档页面：
1. 找到 `GET /api/v1/documents/{document_id}/progress`
2. 输入刚才获取的 `document_id`
3. 点击 "Execute"
4. 查看处理进度

### 4. 查看处理结果

处理完成后（约30秒-2分钟）：
1. 找到 `GET /api/v1/documents/{document_id}/result`
2. 输入 `document_id`
3. 点击 "Execute"
4. 查看处理结果

## 命令行测试

### 健康检查
```bash
curl http://localhost:8000/health
```

### 查看历史记录
```bash
curl 'http://localhost:8000/api/v1/documents/history?page=1&page_size=5'
```

## 查看日志

```bash
# 后端日志
docker-compose logs -f backend

# Worker日志
docker-compose logs -f worker

# 所有服务日志
docker-compose logs -f
```

## 停止服务

```bash
docker-compose down
```

## 重启服务

```bash
docker-compose restart
```

## 重新构建

```bash
docker-compose build
docker-compose up -d
```

---

**系统已就绪，可以开始测试！**

