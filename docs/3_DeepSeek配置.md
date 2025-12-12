# DeepSeek API 配置说明

## 配置位置

DeepSeek API Key 通过环境变量配置，支持两种方式：

### 方式一：使用 .env 文件（推荐）⭐

1. **创建 .env 文件**
```bash
cd /Users/ggsk/Cursor/it-doc-helper
cp .env.example .env
```

2. **编辑 .env 文件，填入你的 DeepSeek API Key**
```env
# DeepSeek API配置
DEEPSEEK_API_KEY=sk-your-deepseek-api-key-here
DEEPSEEK_API_BASE=https://api.deepseek.com
```

3. **保存文件**

### 方式二：直接设置环境变量

```bash
export DEEPSEEK_API_KEY=sk-your-deepseek-api-key-here
export DEEPSEEK_API_BASE=https://api.deepseek.com
```

---

## 获取 DeepSeek API Key

1. 访问 [DeepSeek 官网](https://www.deepseek.com/)
2. 注册/登录账号
3. 进入 API 管理页面
4. 创建新的 API Key
5. 复制 API Key（格式通常为 `sk-xxxxx`）

---

## 配置验证

### Docker 环境

配置后，重启服务：
```bash
docker-compose down
docker-compose up -d
```

检查配置是否生效：
```bash
# 查看后端容器环境变量
docker exec it-doc-helper-backend env | grep DEEPSEEK
```

### 本地开发环境

配置后，重启应用：
```bash
cd backend
uvicorn app.main:app --reload
```

---

## 配置说明

### 配置文件位置

- **环境变量文件**：项目根目录的 `.env` 文件
- **配置读取**：`backend/app/core/config.py` 中的 `Settings` 类
- **Docker 使用**：`docker-compose.yml` 会读取 `.env` 文件中的变量

### 配置项说明

| 配置项 | 说明 | 默认值 | 是否必填 |
|--------|------|--------|----------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | 空 | ✅ 是 |
| `DEEPSEEK_API_BASE` | DeepSeek API 基础URL | `https://api.deepseek.com` | ❌ 否 |

---

## 使用场景

DeepSeek API Key 会在以下场景中使用：

1. **文档类型识别**（`app/services/document_classifier.py`）
   - 当规则匹配置信度低时，使用 AI 进行识别

2. **面试题文档处理**（后续实现）
   - 内容总结
   - 问题生成

3. **技术文档处理**（后续实现）
   - 前置条件分析
   - 学习路径规划

4. **架构文档处理**（后续实现）
   - 配置流程提取
   - 白话串讲生成

---

## 安全提示

⚠️ **重要安全提示：**

1. **不要将 .env 文件提交到 Git**
   - `.env` 文件已在 `.gitignore` 中
   - 只提交 `.env.example` 作为模板

2. **生产环境使用环境变量**
   - 不要在代码中硬编码 API Key
   - 使用环境变量或密钥管理服务

3. **定期轮换 API Key**
   - 如果 API Key 泄露，立即在 DeepSeek 平台撤销
   - 生成新的 API Key 并更新配置

---

## 常见问题

### Q: API Key 在哪里获取？
A: 访问 DeepSeek 官网，登录后在 API 管理页面创建。

### Q: 配置后还是不工作？
A: 
1. 检查 `.env` 文件是否在项目根目录
2. 检查 API Key 格式是否正确（通常以 `sk-` 开头）
3. 重启服务（Docker 或本地应用）
4. 查看日志确认配置是否读取成功

### Q: Docker 环境下如何配置？
A: 在项目根目录创建 `.env` 文件，`docker-compose.yml` 会自动读取。

### Q: 本地开发如何配置？
A: 同样在项目根目录创建 `.env` 文件，应用会自动读取。

---

## 测试配置

配置完成后，可以通过以下方式测试：

1. **查看日志**
```bash
# Docker 环境
docker logs it-doc-helper-backend | grep -i deepseek

# 本地环境
# 启动应用后查看控制台输出
```

2. **测试 API 调用**
- 上传一个文档
- 查看文档类型识别是否使用 AI
- 检查日志中是否有 API 调用记录

---

**配置完成后，即可继续开发 AI 处理功能！**

