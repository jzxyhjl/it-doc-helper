# 数据库迁移执行指南

## 迁移脚本信息

**迁移文件**：`backend/alembic/versions/004_add_intermediate_results_and_views.py`

**迁移内容**：
1. 创建 `document_intermediate_results` 表（视角无关的中间结果）
2. 修改 `processing_results` 表（添加view和is_primary字段，支持每个view独立存储）
3. 修改 `document_types` 表（添加primary_view、enabled_views、detection_scores字段）
4. 历史数据迁移（填充默认view值）

---

## 执行方式

### 方式1：在Docker容器中执行（推荐）

#### 步骤1：启动Docker服务

```bash
# 在项目根目录执行
docker compose up -d

# 或者使用 docker-compose（旧版本）
docker-compose up -d
```

#### 步骤2：检查服务状态

```bash
docker compose ps
# 或
docker-compose ps
```

确保以下服务运行：
- `it-doc-helper-postgres` (PostgreSQL数据库)
- `it-doc-helper-backend` (后端服务)

#### 步骤3：执行迁移

```bash
# 在backend容器中执行迁移
docker compose exec backend alembic upgrade head

# 或使用 docker-compose
docker-compose exec backend alembic upgrade head
```

**预期输出**：
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 003_add_ai_monitoring -> 004_add_intermediate_results_and_views, add_intermediate_results_and_views
```

#### 步骤4：验证迁移

```bash
# 检查迁移版本
docker compose exec backend alembic current

# 检查新表是否创建
docker compose exec postgres psql -U it_doc_helper -d it_doc_helper -c "\dt document_intermediate_results"

# 检查processing_results表结构
docker compose exec postgres psql -U it_doc_helper -d it_doc_helper -c "\d processing_results"

# 检查document_types表结构
docker compose exec postgres psql -U it_doc_helper -d it_doc_helper -c "\d document_types"
```

---

### 方式2：直接连接数据库执行（如果Docker未运行）

#### 前提条件

1. PostgreSQL数据库已安装并运行
2. 数据库连接信息正确（在`.env`文件中配置）
3. Python环境已安装Alembic

#### 步骤1：检查数据库连接

```bash
cd backend

# 检查.env文件是否存在
ls -la .env

# 测试数据库连接（需要先配置环境变量）
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()
from app.core.config import settings
print('DATABASE_URL:', settings.DATABASE_URL)
"
```

#### 步骤2：执行迁移

```bash
cd backend

# 设置环境变量（如果.env文件不存在）
export DATABASE_URL="postgresql://user:password@localhost:5432/dbname"

# 执行迁移
alembic upgrade head
```

---

### 方式3：使用迁移脚本

项目提供了迁移脚本：

```bash
cd backend

# 使用Python脚本执行迁移
python3 scripts/run_migrations.py
```

---

## 验证迁移结果

### 1. 检查迁移版本

```bash
docker compose exec backend alembic current
```

**预期输出**：
```
004_add_intermediate_results_and_views (head)
```

### 2. 检查新表

```bash
docker compose exec postgres psql -U it_doc_helper -d it_doc_helper -c "\dt document_intermediate_results"
```

**预期输出**：
```
                    List of relations
 Schema |              Name               | Type  |     Owner      
--------+---------------------------------+-------+----------------
 public | document_intermediate_results   | table | it_doc_helper
```

### 3. 检查processing_results表结构

```bash
docker compose exec postgres psql -U it_doc_helper -d it_doc_helper -c "\d processing_results"
```

**预期输出**应包含：
- `view` 字段 (VARCHAR(50))
- `is_primary` 字段 (BOOLEAN)
- 唯一约束 `uq_processing_result_document_view`

### 4. 检查document_types表结构

```bash
docker compose exec postgres psql -U it_doc_helper -d it_doc_helper -c "\d document_types"
```

**预期输出**应包含：
- `primary_view` 字段 (VARCHAR(50))
- `enabled_views` 字段 (JSONB)
- `detection_scores` 字段 (JSONB)

### 5. 检查历史数据迁移

```bash
docker compose exec postgres psql -U it_doc_helper -d it_doc_helper -c "SELECT document_id, view, is_primary FROM processing_results LIMIT 5;"
```

**预期输出**：所有记录都应该有view和is_primary值

---

## 回滚迁移（如果需要）

```bash
# 回滚到上一个版本
docker compose exec backend alembic downgrade -1

# 回滚到特定版本
docker compose exec backend alembic downgrade 003_add_ai_monitoring
```

---

## 常见问题

### 问题1：Docker daemon未运行

**错误信息**：
```
Cannot connect to the Docker daemon... Is the docker daemon running?
```

**解决方案**：
1. 启动Docker Desktop（MacOS）
2. 或使用 `sudo systemctl start docker` (Linux)

### 问题2：迁移失败 - 表已存在

**错误信息**：
```
relation "document_intermediate_results" already exists
```

**解决方案**：
- 如果表已存在但迁移未记录，手动标记迁移版本：
```bash
docker compose exec backend alembic stamp 004_add_intermediate_results_and_views
```

### 问题3：唯一约束冲突

**错误信息**：
```
duplicate key value violates unique constraint "uq_processing_result_document_view"
```

**解决方案**：
- 检查是否有重复的document_id + view组合
- 清理重复数据后重新执行迁移

### 问题4：历史数据迁移失败

**错误信息**：
```
column "view" does not exist
```

**解决方案**：
- 确保迁移脚本按顺序执行
- 检查是否有未完成的迁移

---

## 迁移脚本内容摘要

### 创建的表

1. **document_intermediate_results**
   - 存储视角无关的中间结果
   - 字段：content, preprocessed_content, segments, metadata

### 修改的表

1. **processing_results**
   - 添加 `view` 字段
   - 添加 `is_primary` 字段
   - 更新唯一约束为 `(document_id, view)`

2. **document_types**
   - 添加 `primary_view` 字段
   - 添加 `enabled_views` 字段
   - 添加 `detection_scores` 字段

### 历史数据迁移

- 为所有现有记录填充默认view值
- 根据detected_type映射到对应的view

---

## 执行检查清单

- [ ] Docker服务已启动
- [ ] 数据库容器运行正常
- [ ] 后端容器运行正常
- [ ] 执行迁移命令
- [ ] 验证迁移版本
- [ ] 检查新表创建
- [ ] 检查表结构更新
- [ ] 检查历史数据迁移
- [ ] 测试应用功能

---

**文档版本**：v1.0  
**创建时间**：2025-12-21

