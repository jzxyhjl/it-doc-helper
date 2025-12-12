# 部署文档

## Docker部署

### 前置要求
- Docker & Docker Compose
- DeepSeek API Key

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd it-helper
```

2. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件，填入你的配置：
#   - POSTGRES_PASSWORD: 数据库密码
#   - DEEPSEEK_API_KEY: DeepSeek API密钥（必填，用于AI功能）
#   详细配置说明请查看 docs/DEEPSEEK_CONFIG.md
```

3. **启动服务**
```bash
docker-compose up -d
```

4. **等待服务启动**（数据库会自动初始化）

5. **访问应用**
- 前端：http://localhost/it-doc-helper
- API文档：http://localhost:8000/docs

## 服务状态

### ✅ 已启动的服务

1. **PostgreSQL数据库** (it-helper-postgres)
   - 端口: 5432
   - 状态: 运行中
   - 数据持久化: Docker Volume

2. **Redis缓存** (it-helper-redis)
   - 端口: 6379
   - 状态: 运行中
   - 数据持久化: Docker Volume

3. **后端API服务** (it-helper-backend)
   - 端口: 8000
   - 状态: 运行中
   - API文档: http://localhost:8000/docs
   - 健康检查: http://localhost:8000/health

4. **Celery Worker** (it-helper-worker)
   - 状态: 运行中
   - 任务队列: Redis

5. **前端服务** (it-helper-frontend)
   - 端口: 80
   - 状态: 运行中

## 常用命令

### 查看服务状态
```bash
docker-compose ps
```

### 查看日志
```bash
# 后端日志
docker-compose logs -f backend

# Worker日志
docker-compose logs -f worker

# 所有服务日志
docker-compose logs -f
```

### 重启服务
```bash
# 重启所有服务
docker-compose restart

# 重启特定服务
docker-compose restart backend
```

### 停止服务
```bash
docker-compose down
```

### 重新构建
```bash
docker-compose build
docker-compose up -d
```

## 访问地址

- **前端**: http://localhost/it-doc-helper
- **API服务**: http://localhost:8000
- **API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

## 数据库设置

数据库使用Docker容器化部署，无需本地安装PostgreSQL。详细说明请查看 [数据库设置文档](DATABASE_SETUP.md)

---

**最后更新**: 2024-12-11

