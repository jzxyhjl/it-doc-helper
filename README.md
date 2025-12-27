# IT学习辅助系统

基于文档识别的智能学习辅助平台，能够自动识别上传文档的类型（面试题文档、IT技术文档、架构/搭建文档），并根据不同类型提供针对性的学习辅助功能。

## 功能特性

- 📄 **多格式文档支持**：PDF、Word (.docx)、PPT (.pptx)、Markdown、TXT
  - ⚠️ **注意**：暂不支持旧版 Word 文档（.doc），请先转换为 .docx 格式
- 🎯 **多视角处理**：支持学习视角、问答视角、系统视角，一个文档可以同时拥有多个视角的处理结果
- 🤖 **智能视角识别**：自动识别文档特征，推荐主视角和次视角
- ⚡ **快速视角切换**：复用中间结果，5秒内完成视角切换
- 📝 **问答视角处理**：内容总结、问题生成、答案提取
- 📚 **学习视角处理**：前置条件分析、学习路径规划、学习方法建议
- 🏗️ **系统视角处理**：配置流程提取、组件全景视图、白话串讲
- ⚡ **实时进度显示**：WebSocket实时推送处理进度
- 📊 **历史记录**：保存处理历史，支持查看和管理

## 技术栈

### 后端
- Python 3.11+
- FastAPI - Web框架
- PostgreSQL - 数据库
- Redis - 缓存和任务队列
- Celery - 异步任务处理
- DeepSeek API - AI能力

### 前端
- React 18+
- Vite - 构建工具
- TailwindCSS - UI框架
- TypeScript - 类型安全

### 部署
- Docker - 容器化
- docker-compose - 多容器编排

## 快速开始

### 前置要求

- **Docker & Docker Compose** (版本 20.10+)
- **DeepSeek API Key**（用于AI功能，[获取方式](#获取-deepseek-api-key)）

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd it-doc-helper
```

2. **配置环境变量**
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，至少配置以下必需项：
#   - POSTGRES_PASSWORD: 数据库密码（必填，请使用强密码）
#   - DEEPSEEK_API_KEY: DeepSeek API密钥（必填，用于AI功能）
```

**`.env` 文件配置示例：**
```env
# 必需配置
POSTGRES_PASSWORD=your_secure_password_here
DEEPSEEK_API_KEY=sk-your-deepseek-api-key-here

# 其他配置有默认值，可根据需要修改
```

3. **启动服务（使用Docker，推荐）**
```bash
docker-compose up -d
```

4. **等待服务启动**（首次启动需要 5-10 分钟）
   - 下载 Docker 镜像
   - 构建应用镜像
   - 初始化数据库（自动执行）

5. **访问应用**
   - **前端界面**: http://localhost/it-doc-helper
   - **API文档**: http://localhost:8000/docs
   - **健康检查**: http://localhost:8000/health

### 获取 DeepSeek API Key

DeepSeek API Key 是系统运行**必需**的配置，用于AI文档处理功能。

**获取步骤：**
1. 访问 [DeepSeek 官网](https://www.deepseek.com/)
2. 注册/登录账号
3. 进入 **API 管理**页面
4. 点击 **创建新的 API Key**
5. 复制 API Key（格式通常为 `sk-xxxxx`）
6. 将 API Key 填入 `.env` 文件的 `DEEPSEEK_API_KEY` 字段

**详细配置说明：** 请查看 [DeepSeek配置文档](docs/3_DeepSeek配置.md)

**注意：** 
- 数据库使用Docker容器化部署，无需本地安装PostgreSQL
- 所有服务都已容器化，一键启动即可使用
- 详细部署说明请查看 [一键部署指南](docs/2_一键部署指南.md)

## 项目结构

```
it-doc-helper/
├── backend/              # 后端代码
│   ├── app/             # 应用主目录
│   │   ├── api/         # API路由
│   │   ├── models/      # 数据模型
│   │   ├── services/    # 业务逻辑
│   │   ├── tasks/       # Celery任务
│   │   └── core/        # 核心配置
│   ├── requirements.txt # Python依赖
│   └── Dockerfile       # Docker配置
├── frontend/            # 前端代码
│   ├── src/             # 源代码
│   └── Dockerfile       # Docker配置
├── uploads/             # 文件上传存储
├── docker-compose.yml   # Docker编排
└── README.md           # 项目说明
```

## 开发指南

### 后端开发

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 前端开发

```bash
cd frontend
npm install
npm run dev
```

## 文档导航

### 快速开始
按阅读顺序：

1. **[快速开始检查清单](docs/0_快速开始检查清单.md)** - 部署前检查清单（推荐先看）
2. **[项目介绍](docs/1_README.md)** - 项目介绍和快速开始
3. **[一键部署指南](docs/2_一键部署指南.md)** - 详细的Docker部署说明
4. **[DeepSeek配置](docs/3_DeepSeek配置.md)** - AI服务配置说明（**必读**）
5. **[数据库设置](docs/4_数据库设置.md)** - 数据库配置和初始化（可选）
6. **[系统测试](docs/5_系统测试.md)** - 测试指南和测试结果
7. **[问题排查](docs/6_问题排查.md)** - 常见问题和解决方案

### 开发文档
- **[多视角API接口文档](docs/development/API_MULTI_VIEW.md)** - 多视角系统的API接口说明
- **[文档视角分类机制](docs/development/DOCUMENT_CLASSIFICATION.md)** - 视角识别和分类机制
- **[处理结果结构说明](docs/development/PROCESSING_RESULT_STRUCTURE.md)** - 处理结果的数据结构
- **[数据库迁移指南](docs/development/MIGRATION_GUIDE.md)** - 数据库迁移操作指南
- **[AI测试和监控](docs/development/AI_TESTING_MONITORING.md)** - AI服务测试和监控说明

### 需求文档（历史）
详细需求文档请查看 `.trae/documents/` 目录：
- `perspective_based_classification_requirements.md` - 多视角系统需求文档
- `perspective_based_classification_design.md` - 多视角系统技术方案
- `perspective_based_classification_tasks.md` - 多视角系统实施计划

## 许可证

MIT License

