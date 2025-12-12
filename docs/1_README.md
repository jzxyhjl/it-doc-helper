# IT学习辅助系统

基于文档识别的智能学习辅助平台，能够自动识别上传文档的类型（面试题文档、IT技术文档、架构/搭建文档），并根据不同类型提供针对性的学习辅助功能。

## 功能特性

- 📄 **多格式文档支持**：PDF、Word、PPT、Markdown、TXT
- 🤖 **智能文档识别**：自动识别文档类型（面试题/技术文档/架构文档）
- 📝 **面试题处理**：内容总结、问题生成、答案提取
- 📚 **技术文档处理**：前置条件分析、学习路径规划、学习方法建议
- 🏗️ **架构文档处理**：配置流程提取、组件全景视图、白话串讲
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

- Docker & Docker Compose
- DeepSeek API Key

### 安装步骤

1. 克隆项目
```bash
git clone <repository-url>
cd it-helper
```

2. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 文件，填入你的配置：
#   - POSTGRES_PASSWORD: 数据库密码
#   - DEEPSEEK_API_KEY: DeepSeek API密钥（必填，用于AI功能）
```

3. 启动服务（使用Docker，推荐）
```bash
docker-compose up -d
```

4. 等待服务启动（数据库会自动初始化）

5. 访问应用
- 前端：http://localhost
- API文档：http://localhost:8000/docs

## 项目结构

```
it-helper/
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

按阅读顺序：

1. **README** - 项目介绍和快速开始（本文档）
2. **一键部署指南** - 详细的Docker部署说明
3. **DeepSeek配置** - AI服务配置说明
4. **数据库设置** - 数据库配置和初始化（可选）
5. **系统测试** - 测试指南和测试结果
6. **问题排查** - 常见问题和解决方案

## 许可证

MIT License

