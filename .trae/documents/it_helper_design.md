# IT学习辅助系统 - 技术方案设计

## 一、系统架构设计

### 1.1 整体架构

系统采用前后端分离架构，使用Docker容器化部署，支持水平扩展。

```mermaid
graph TB
    subgraph "用户层"
        User[用户浏览器]
    end
    
    subgraph "前端服务"
        Frontend[React + Vite<br/>TailwindCSS UI]
        WS[WebSocket客户端]
    end
    
    subgraph "后端服务"
        API[FastAPI后端服务]
        Queue[Celery任务队列]
        Worker[Celery Worker<br/>文档处理工作进程]
    end
    
    subgraph "AI服务"
        DeepSeek[DeepSeek API]
    end
    
    subgraph "数据存储"
        PostgreSQL[(PostgreSQL数据库<br/>+ pgvector扩展)]
        Redis[(Redis缓存<br/>+ 任务队列)]
        FileStorage[文件存储<br/>本地文件系统]
    end
    
    User -->|HTTP/WebSocket| Frontend
    Frontend -->|REST API| API
    Frontend -->|WebSocket| WS
    WS --> API
    API -->|任务分发| Queue
    Queue -->|任务执行| Worker
    Worker -->|文档处理| FileStorage
    Worker -->|AI调用| DeepSeek
    Worker -->|数据存储| PostgreSQL
    API -->|数据查询| PostgreSQL
    API -->|缓存| Redis
    Queue -->|任务队列| Redis
```

### 1.2 系统组件说明

| 组件 | 技术栈 | 职责 |
|------|--------|------|
| **前端服务** | React + Vite + TailwindCSS | 用户界面、文档上传、结果展示、实时进度 |
| **后端API** | FastAPI | RESTful API、WebSocket服务、任务管理 |
| **任务队列** | Celery + Redis | 异步任务分发、任务状态管理 |
| **工作进程** | Celery Worker | 文档处理、AI调用、结果生成 |
| **数据库** | PostgreSQL + pgvector | 数据持久化、历史记录、向量存储 |
| **缓存** | Redis | 任务队列、进度缓存、临时数据 |
| **文件存储** | 本地文件系统 | 上传文档存储 |

### 1.3 数据流设计

```mermaid
sequenceDiagram
    participant U as 用户
    participant F as 前端
    participant API as 后端API
    participant Q as 任务队列
    participant W as Worker
    participant DS as DeepSeek
    participant DB as PostgreSQL
    
    U->>F: 上传文档
    F->>API: POST /api/documents/upload
    API->>DB: 保存文档元数据
    API->>Q: 创建处理任务
    API-->>F: 返回文档ID和任务ID
    F->>API: WebSocket连接
    API->>W: 分发任务
    W->>W: 提取文档内容
    W->>API: 更新进度(20%)
    API-->>F: WebSocket推送进度
    W->>DS: 识别文档类型
    W->>API: 更新进度(40%)
    API-->>F: WebSocket推送进度
    W->>DS: 处理文档(根据类型)
    W->>API: 更新进度(80%)
    API-->>F: WebSocket推送进度
    W->>DB: 保存处理结果
    W->>API: 更新进度(100%)
    API-->>F: WebSocket推送完成
    F->>U: 展示处理结果
```

---

## 二、数据库设计

### 2.1 数据库选型

- **主数据库**：PostgreSQL 15+
- **向量扩展**：pgvector（用于系统学习，MVP阶段预留）
- **连接池**：SQLAlchemy + asyncpg

### 2.2 数据表设计

#### 2.2.1 documents（文档表）

存储上传文档的基本信息。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PRIMARY KEY | 文档ID |
| filename | VARCHAR(255) | NOT NULL | 文件名 |
| file_path | VARCHAR(500) | NOT NULL | 文件存储路径 |
| file_size | BIGINT | NOT NULL | 文件大小（字节） |
| file_type | VARCHAR(50) | NOT NULL | 文件类型（pdf/docx/pptx/md/txt） |
| upload_time | TIMESTAMP | NOT NULL, DEFAULT NOW() | 上传时间 |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'pending' | 处理状态（pending/processing/completed/failed） |
| content_extracted | TEXT | NULL | 提取的文档内容 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 更新时间 |

**索引：**
- `idx_documents_status`: (status)
- `idx_documents_upload_time`: (upload_time DESC)

#### 2.2.2 document_types（文档类型表）

存储文档类型识别结果。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PRIMARY KEY | 类型记录ID |
| document_id | UUID | FOREIGN KEY, NOT NULL | 文档ID |
| detected_type | VARCHAR(50) | NOT NULL | 识别的类型（interview/technical/architecture/unknown） |
| confidence | FLOAT | NULL | 识别置信度（0-1） |
| detection_method | VARCHAR(50) | NOT NULL | 识别方法（rule/ai/hybrid） |
| detected_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 识别时间 |

**索引：**
- `idx_document_types_document_id`: (document_id)
- `idx_document_types_type`: (detected_type)

#### 2.2.3 processing_results（处理结果表）

存储文档处理结果。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PRIMARY KEY | 结果ID |
| document_id | UUID | FOREIGN KEY, NOT NULL, UNIQUE | 文档ID |
| document_type | VARCHAR(50) | NOT NULL | 文档类型 |
| result_data | JSONB | NOT NULL | 处理结果数据（JSON格式） |
| processing_time | INTEGER | NULL | 处理耗时（秒） |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 更新时间 |

**索引：**
- `idx_processing_results_document_id`: (document_id)
- `idx_processing_results_type`: (document_type)
- `idx_processing_results_created_at`: (created_at DESC)

**result_data JSON结构示例：**

面试题文档：
```json
{
  "summary": {
    "key_points": ["知识点1", "知识点2"],
    "question_types": {"选择题": 10, "问答题": 5},
    "difficulty": {"简单": 5, "中等": 8, "困难": 2},
    "total_questions": 15
  },
  "generated_questions": [
    {"question": "问题1", "hint": "提示1"},
    {"question": "问题2", "hint": "提示2"}
  ],
  "extracted_answers": ["答案1", "答案2"]
}
```

技术文档：
```json
{
  "prerequisites": {
    "required": ["前置知识1", "前置知识2"],
    "recommended": ["推荐知识1"]
  },
  "learning_path": [
    {"stage": 1, "title": "基础阶段", "content": "..."},
    {"stage": 2, "title": "进阶阶段", "content": "..."}
  ],
  "learning_methods": {
    "theory": "理论学习建议",
    "practice": "实践建议"
  },
  "related_technologies": ["技术1", "技术2"]
}
```

架构文档：
```json
{
  "config_steps": [
    {"step": 1, "title": "步骤1", "description": "..."},
    {"step": 2, "title": "步骤2", "description": "..."}
  ],
  "components": [
    {"name": "组件1", "description": "...", "dependencies": ["组件2"]}
  ],
  "architecture_view": "组件全景视图描述或Mermaid代码",
  "plain_explanation": "白话串讲内容",
  "checklist": ["检查项1", "检查项2"]
}
```

#### 2.2.4 processing_tasks（处理任务表）

存储文档处理任务信息，用于任务管理和进度跟踪。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PRIMARY KEY | 任务ID |
| document_id | UUID | FOREIGN KEY, NOT NULL | 文档ID |
| task_type | VARCHAR(50) | NOT NULL | 任务类型（extract/identify/process） |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'pending' | 任务状态（pending/running/completed/failed） |
| progress | INTEGER | NOT NULL, DEFAULT 0 | 进度百分比（0-100） |
| current_stage | VARCHAR(100) | NULL | 当前处理阶段 |
| error_message | TEXT | NULL | 错误信息 |
| started_at | TIMESTAMP | NULL | 开始时间 |
| completed_at | TIMESTAMP | NULL | 完成时间 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 创建时间 |

**索引：**
- `idx_processing_tasks_document_id`: (document_id)
- `idx_processing_tasks_status`: (status)

#### 2.2.5 system_learning_data（系统学习数据表）

存储系统学习所需的数据，为后续优化做准备（MVP阶段预留）。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PRIMARY KEY | 记录ID |
| document_id | UUID | FOREIGN KEY, NOT NULL | 文档ID |
| content_summary | TEXT | NOT NULL | 内容摘要 |
| content_vector | VECTOR(1536) | NULL | 内容向量（使用pgvector） |
| document_type | VARCHAR(50) | NOT NULL | 文档类型 |
| processing_result_summary | TEXT | NULL | 处理结果摘要 |
| processing_time | INTEGER | NULL | 处理耗时 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 创建时间 |

**索引：**
- `idx_system_learning_document_id`: (document_id)
- `idx_system_learning_type`: (document_type)
- `idx_system_learning_vector`: (content_vector) -- 向量索引（使用pgvector）

### 2.3 数据库关系图

```mermaid
erDiagram
    documents ||--o| document_types : "has"
    documents ||--o| processing_results : "has"
    documents ||--o{ processing_tasks : "has"
    documents ||--o| system_learning_data : "has"
    
    documents {
        uuid id PK
        varchar filename
        varchar file_path
        bigint file_size
        varchar file_type
        timestamp upload_time
        varchar status
        text content_extracted
    }
    
    document_types {
        uuid id PK
        uuid document_id FK
        varchar detected_type
        float confidence
        varchar detection_method
    }
    
    processing_results {
        uuid id PK
        uuid document_id FK
        varchar document_type
        jsonb result_data
        integer processing_time
    }
    
    processing_tasks {
        uuid id PK
        uuid document_id FK
        varchar task_type
        varchar status
        integer progress
        varchar current_stage
    }
    
    system_learning_data {
        uuid id PK
        uuid document_id FK
        text content_summary
        vector content_vector
        varchar document_type
    }
```

---

## 三、API设计

### 3.1 API架构

- **协议**：RESTful API + WebSocket
- **认证**：MVP阶段暂不需要（单用户）
- **数据格式**：JSON
- **API版本**：v1

### 3.2 RESTful API端点

#### 3.2.1 文档上传

**POST** `/api/v1/documents/upload`

上传文档文件。

**请求：**
- Content-Type: `multipart/form-data`
- Body:
  - `file`: 文件（必填，<30MB）

**响应：**
```json
{
  "document_id": "uuid",
  "filename": "example.pdf",
  "file_size": 1024000,
  "file_type": "pdf",
  "status": "pending",
  "upload_time": "2024-12-19T10:00:00Z"
}
```

**错误响应：**
```json
{
  "error": "FILE_TOO_LARGE",
  "message": "文件大小超过30MB限制"
}
```

#### 3.2.2 获取文档信息

**GET** `/api/v1/documents/{document_id}`

获取文档基本信息。

**响应：**
```json
{
  "document_id": "uuid",
  "filename": "example.pdf",
  "file_size": 1024000,
  "file_type": "pdf",
  "status": "processing",
  "upload_time": "2024-12-19T10:00:00Z",
  "processing_task_id": "uuid"
}
```

#### 3.2.3 获取处理进度

**GET** `/api/v1/documents/{document_id}/progress`

获取文档处理进度。

**响应：**
```json
{
  "document_id": "uuid",
  "progress": 65,
  "current_stage": "AI处理中",
  "status": "processing",
  "estimated_time_remaining": 30
}
```

#### 3.2.4 获取处理结果

**GET** `/api/v1/documents/{document_id}/result`

获取文档处理结果。

**响应：**
```json
{
  "document_id": "uuid",
  "document_type": "interview",
  "result": {
    "summary": {...},
    "generated_questions": [...],
    "extracted_answers": [...]
  },
  "processing_time": 45,
  "created_at": "2024-12-19T10:01:00Z"
}
```

#### 3.2.5 获取历史记录列表

**GET** `/api/v1/documents/history`

获取处理历史记录列表。

**查询参数：**
- `page`: 页码（默认1）
- `page_size`: 每页数量（默认20）
- `document_type`: 文档类型筛选（可选）
- `start_date`: 开始日期（可选）
- `end_date`: 结束日期（可选）

**响应：**
```json
{
  "total": 100,
  "page": 1,
  "page_size": 20,
  "items": [
    {
      "document_id": "uuid",
      "filename": "example.pdf",
      "file_type": "pdf",
      "document_type": "interview",
      "status": "completed",
      "upload_time": "2024-12-19T10:00:00Z",
      "processing_time": 45
    }
  ]
}
```

#### 3.2.6 删除历史记录

**DELETE** `/api/v1/documents/{document_id}`

删除文档及其处理结果。

**响应：**
```json
{
  "message": "文档已删除",
  "document_id": "uuid"
}
```

### 3.3 WebSocket API

#### 3.3.1 连接

**WS** `/ws/progress/{task_id}`

建立WebSocket连接，实时接收处理进度更新。

**连接参数：**
- `task_id`: 处理任务ID

**消息格式（服务器→客户端）：**
```json
{
  "type": "progress",
  "task_id": "uuid",
  "document_id": "uuid",
  "progress": 65,
  "current_stage": "AI处理中",
  "status": "processing"
}
```

**完成消息：**
```json
{
  "type": "completed",
  "task_id": "uuid",
  "document_id": "uuid",
  "progress": 100,
  "status": "completed"
}
```

**错误消息：**
```json
{
  "type": "error",
  "task_id": "uuid",
  "error": "处理失败",
  "message": "详细错误信息"
}
```

---

## 四、技术栈详细说明

### 4.1 后端技术栈

#### 4.1.1 核心框架
- **FastAPI**: 现代、快速的Web框架，支持异步、自动API文档
- **Python 3.11+**: 编程语言

#### 4.1.2 文档处理库
- **python-pptx**: PPT文档处理
- **pdfplumber**: PDF文档处理（比PyPDF2更强大）
- **python-docx**: Word文档处理
- **markdown**: Markdown文档处理
- **chardet**: 字符编码检测

#### 4.1.3 AI集成
- **openai**: DeepSeek API客户端（兼容OpenAI格式）
- **httpx**: 异步HTTP客户端

#### 4.1.4 数据库
- **SQLAlchemy**: ORM框架
- **asyncpg**: 异步PostgreSQL驱动
- **alembic**: 数据库迁移工具
- **pgvector**: PostgreSQL向量扩展（系统学习）

#### 4.1.5 任务队列
- **Celery**: 分布式任务队列
- **Redis**: 任务队列后端、缓存

#### 4.1.6 WebSocket
- **fastapi-websocket**: WebSocket支持

#### 4.1.7 其他
- **pydantic**: 数据验证
- **python-multipart**: 文件上传支持
- **uvicorn**: ASGI服务器

### 4.2 前端技术栈

#### 4.2.1 核心框架
- **React 18+**: UI框架
- **Vite**: 构建工具
- **TypeScript**: 类型安全（可选，建议使用）

#### 4.2.2 UI框架
- **TailwindCSS**: 实用优先的CSS框架
- **shadcn/ui**: 基于Tailwind的组件库（轻松风格）

#### 4.2.3 状态管理
- **Zustand**: 轻量级状态管理
- **React Query**: 数据获取和缓存

#### 4.2.4 HTTP客户端
- **Axios**: HTTP请求库

#### 4.2.5 WebSocket
- **原生WebSocket API** 或 **socket.io-client**

#### 4.2.6 其他
- **react-dropzone**: 文件上传组件
- **react-markdown**: Markdown渲染
- **mermaid**: 图表渲染（架构图）

### 4.3 基础设施

#### 4.3.1 容器化
- **Docker**: 容器化
- **docker-compose**: 多容器编排

#### 4.3.2 数据库
- **PostgreSQL 15+**: 主数据库
- **Redis 7+**: 缓存和任务队列

#### 4.3.3 文件存储
- **本地文件系统**: MVP阶段使用本地存储
- **未来可扩展**: MinIO对象存储

---

## 五、部署方案

### 5.1 Docker容器架构

```mermaid
graph TB
    subgraph "Docker Network: it-helper-network"
        subgraph "前端容器"
            FrontendContainer[nginx:alpine<br/>静态文件服务]
        end
        
        subgraph "后端容器"
            APIContainer[FastAPI应用<br/>uvicorn]
            WorkerContainer[Celery Worker<br/>文档处理]
        end
        
        subgraph "数据容器"
            PostgresContainer[PostgreSQL 15<br/>+ pgvector]
            RedisContainer[Redis 7]
        end
        
        subgraph "存储卷"
            FileVolume[文件存储卷<br/>/app/uploads]
            PostgresVolume[PostgreSQL数据卷]
            RedisVolume[Redis数据卷]
        end
    end
    
    User[用户] -->|HTTP:80| FrontendContainer
    FrontendContainer -->|API请求| APIContainer
    APIContainer -->|任务分发| RedisContainer
    WorkerContainer -->|任务执行| RedisContainer
    APIContainer -->|数据查询| PostgresContainer
    WorkerContainer -->|数据存储| PostgresContainer
    WorkerContainer -->|文件读写| FileVolume
    PostgresContainer -->|数据持久化| PostgresVolume
    RedisContainer -->|数据持久化| RedisVolume
```

### 5.2 docker-compose.yml结构

```yaml
version: '3.8'

services:
  # PostgreSQL数据库
  postgres:
    image: pgvector/pgvector:pg15
    environment:
      POSTGRES_DB: it_helper
      POSTGRES_USER: it_helper
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    networks:
      - it-helper-network

  # Redis缓存
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    networks:
      - it-helper-network

  # 后端API服务
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    environment:
      DATABASE_URL: postgresql://it_helper:${POSTGRES_PASSWORD}@postgres:5432/it_helper
      REDIS_URL: redis://redis:6379/0
      DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY}
      UPLOAD_DIR: /app/uploads
    volumes:
      - ./uploads:/app/uploads
      - ./backend:/app
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    networks:
      - it-helper-network

  # Celery Worker
  worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: celery -A app.celery_app worker --loglevel=info
    environment:
      DATABASE_URL: postgresql://it_helper:${POSTGRES_PASSWORD}@postgres:5432/it_helper
      REDIS_URL: redis://redis:6379/0
      DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY}
      UPLOAD_DIR: /app/uploads
    volumes:
      - ./uploads:/app/uploads
      - ./backend:/app
    depends_on:
      - postgres
      - redis
    networks:
      - it-helper-network

  # 前端服务
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "80:80"
    depends_on:
      - backend
    networks:
      - it-helper-network

volumes:
  postgres_data:
  redis_data:

networks:
  it-helper-network:
    driver: bridge
```

### 5.3 环境变量配置

创建 `.env` 文件：

```env
# 数据库配置
POSTGRES_PASSWORD=your_secure_password

# DeepSeek API配置
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_API_BASE=https://api.deepseek.com

# 应用配置
UPLOAD_MAX_SIZE=31457280  # 30MB
ALLOWED_EXTENSIONS=pdf,docx,pptx,md,txt
```

---

## 六、安全性设计

### 6.1 文件上传安全
- 文件大小限制（30MB）
- 文件类型验证（白名单）
- 文件名安全处理（防止路径遍历）
- 文件内容扫描（可选，防病毒）

### 6.2 API安全
- 请求频率限制（Rate Limiting）
- 输入验证（Pydantic）
- SQL注入防护（ORM参数化查询）
- XSS防护（前端转义）

### 6.3 数据安全
- API密钥环境变量存储（不硬编码）
- 数据库连接加密
- 敏感数据加密存储（如需要）

---

## 七、测试策略

### 7.1 单元测试
- 后端：pytest + pytest-asyncio
- 前端：Vitest + React Testing Library

### 7.2 集成测试
- API端点测试
- 数据库操作测试
- 文档处理流程测试

### 7.3 端到端测试
- 完整文档处理流程测试
- WebSocket连接测试

---

## 八、监控与日志

### 8.1 日志
- 应用日志：结构化日志（JSON格式）
- 错误日志：详细错误堆栈
- 访问日志：API请求日志

### 8.2 监控指标
- 文档处理成功率
- 平均处理时间
- API响应时间
- 系统资源使用率

---

**文档版本**：v1.0  
**创建时间**：2025-12-09  
**最后更新**：2025-12-09

