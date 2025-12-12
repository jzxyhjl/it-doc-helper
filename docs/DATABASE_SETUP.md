# 数据库设置说明

## 数据库部署方案

本项目支持两种数据库部署方式：

### 方案一：Docker容器化部署（推荐）⭐

**优点：**
- ✅ 环境统一，避免本地环境差异
- ✅ 包含pgvector扩展，支持系统学习功能
- ✅ 数据持久化，使用Docker Volume
- ✅ 易于迁移和部署
- ✅ 开发和生产环境一致

**配置方式：**
1. 使用 `docker-compose.yml` 中配置的PostgreSQL容器
2. 数据库连接地址：`postgres:5432`（容器内）或 `localhost:5432`（宿主机）
3. 数据库会在容器启动时自动初始化

**启动步骤：**
```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，设置 POSTGRES_PASSWORD

# 2. 启动所有服务（包括数据库）
docker-compose up -d

# 3. 数据库会自动初始化（通过 backend 容器的启动脚本）
```

**数据库连接信息：**
- 主机：`postgres`（容器内）或 `localhost`（宿主机）
- 端口：`5432`
- 数据库：`it_helper`（默认）
- 用户：`it_helper`（默认）
- 密码：从 `.env` 文件中的 `POSTGRES_PASSWORD` 读取

---

### 方案二：本地PostgreSQL（开发用）

**适用场景：**
- 本地已有PostgreSQL环境
- 需要直接访问数据库进行调试
- 不想使用Docker

**配置方式：**
1. 确保本地已安装PostgreSQL 15+ 和 pgvector 扩展
2. 创建数据库：
```sql
CREATE DATABASE it_helper;
CREATE USER it_helper WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE it_helper TO it_helper;
```

3. 启用pgvector扩展：
```sql
\c it_helper
CREATE EXTENSION vector;
```

4. 配置 `.env` 文件：
```env
DATABASE_URL=postgresql://it_helper:your_password@localhost:5432/it_helper
```

5. 运行数据库迁移：
```bash
cd backend
alembic upgrade head
```

---

## 数据库初始化

### Docker环境（自动）

数据库会在 `backend` 容器启动时自动初始化：
- 执行 `scripts/init_db.py` 创建所有表
- 启用 pgvector 扩展（如果可用）

### 本地环境（手动）

```bash
# 方式1：使用初始化脚本
cd backend
python scripts/init_db.py

# 方式2：使用Alembic迁移
cd backend
alembic upgrade head
```

---

## 数据库迁移

### 创建新迁移

```bash
cd backend
alembic revision --autogenerate -m "描述信息"
```

### 应用迁移

```bash
cd backend
alembic upgrade head
```

### 回滚迁移

```bash
cd backend
alembic downgrade -1
```

---

## 数据持久化

### Docker环境

数据存储在Docker Volume中：
- Volume名称：`it-helper_postgres_data`
- 数据位置：Docker管理的卷中
- 备份：可以使用 `docker volume` 命令备份

### 本地环境

数据存储在PostgreSQL默认数据目录中。

---

## 推荐方案

**强烈推荐使用Docker方案**，原因：
1. 环境一致性：开发、测试、生产环境完全一致
2. 易于部署：一键启动所有服务
3. 数据隔离：不影响本地其他PostgreSQL实例
4. 扩展支持：已包含pgvector扩展
5. 团队协作：所有开发者使用相同环境

---

## 常见问题

### Q: Docker容器内如何连接数据库？
A: 使用服务名 `postgres` 作为主机名，端口 `5432`

### Q: 宿主机如何连接Docker中的数据库？
A: 使用 `localhost:5432`，端口已映射到宿主机

### Q: 如何查看数据库数据？
A: 
```bash
# 进入PostgreSQL容器
docker exec -it it-helper-postgres psql -U it_helper -d it_helper

# 或使用本地客户端连接
psql -h localhost -U it_helper -d it_helper
```

### Q: 如何重置数据库？
A:
```bash
# 停止并删除容器和数据卷
docker-compose down -v

# 重新启动
docker-compose up -d
```

