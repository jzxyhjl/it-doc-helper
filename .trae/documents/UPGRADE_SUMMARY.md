# IT学习辅助系统 - 升级文档汇总

## 文档版本：v1.0
**创建时间**：2025-12-19
**最后更新**：2025-12-19

---

## 一、系统概述

IT学习辅助系统是一个基于文档识别的智能学习辅助平台，能够自动识别上传文档的类型（面试题文档、IT技术文档、架构/搭建文档），并根据不同类型提供针对性的学习辅助功能。

### 核心功能

1. **文档管理**
   - 文档上传（支持PDF, DOCX, PPTX, MD, TXT）
   - 文件大小限制（30MB）
   - 文档删除和列表查询

2. **文档处理**
   - 文档内容提取
   - 文档类型自动识别（规则+AI混合）
   - 异步任务处理（Celery）
   - 实时进度更新（WebSocket）

3. **AI处理能力**
   - 面试题文档处理（总结、生成问题、提取答案）
   - 技术文档处理（前置条件、学习路径、学习方法、相关技术）
   - 架构文档处理（配置流程、组件识别、全景视图、白话串讲、检查清单）

4. **系统学习能力**
   - 文档向量化存储（pgvector）
   - 相似文档推荐（基于向量相似度）
   - 置信度评估和来源片段引用
   - 文档大小验证和处理时间控制

5. **用户界面**
   - 文档上传页面
   - 处理进度页面
   - 处理结果展示页面
   - 历史记录页面
   - 响应式设计

---

## 二、技术架构

### 后端技术栈
- **框架**：FastAPI
- **语言**：Python 3.11+
- **数据库**：PostgreSQL + pgvector（向量存储）
- **任务队列**：Celery + Redis
- **AI服务**：DeepSeek API
- **向量化**：本地嵌入模型（sentence-transformers）

### 前端技术栈
- **框架**：React 18+ + TypeScript
- **构建工具**：Vite
- **UI框架**：TailwindCSS
- **状态管理**：Zustand
- **路由**：React Router

### 部署架构
- **容器化**：Docker + Docker Compose
- **Web服务器**：Nginx（前端反向代理）
- **服务编排**：docker-compose

---

## 三、核心文档

### 已实现功能文档

1. **需求文档**
   - `it_helper_requirements.md` - 核心需求文档
   - `confidence_and_sources_requirements.md` - 置信度和来源功能需求

2. **技术方案**
   - `it_helper_design.md` - 系统技术方案设计
   - `confidence_and_sources_design.md` - 置信度和来源功能技术方案

3. **实施计划**
   - `it_helper_tasks.md` - 核心功能实施计划
   - `confidence_and_sources_tasks.md` - 置信度和来源功能实施计划

### 技术参考文档

1. **API和配置**
   - `DeepSeek_API用途说明.md` - DeepSeek API使用说明
   - `DeepSeek向量化实现方案.md` - 向量化服务实现方案
   - `向量化服务替代方案.md` - 向量化服务备选方案

2. **技术选型**
   - `技术栈推荐.md` - 技术栈选型说明
   - `需求分析_IT学习辅助系统.md` - 需求分析文档

---

## 四、已归档文档

### 过程分析文档（已归档到 `.trae/archive/process_analysis/`）

1. **doc_format_support_analysis.md** - .doc格式支持可行性分析
   - **决策**：不实现 .doc 格式支持
   - **原因**：中文编码稳定性风险、维护成本高
   - **替代方案**：引导用户转换为 .docx 格式

2. **doc_format_risk_analysis.md** - .doc格式风险分析
   - **决策**：不实现 .doc 格式支持
   - **原因**：引入外部工具带来稳定性风险

3. **知识图谱和智能推荐可行性分析.md** - 知识图谱和智能推荐功能可行性分析
   - **状态**：部分功能已实现（向量搜索、相似文档推荐），部分功能未实现（知识图谱可视化、智能推荐算法）

### 未实现需求文档（已归档到 `.trae/archive/unimplemented/`）

1. **扩展功能规划.md** - 扩展功能规划
   - **状态**：大部分功能未实现

2. **第二阶段需求规划.md** - 第二阶段需求规划
   - **状态**：大部分功能未实现

3. **第二阶段实施计划.md** - 第二阶段实施计划
   - **状态**：大部分任务未实现

---

## 五、系统限制和配置

### 文档大小限制
- **文件大小**：最大 30MB（警告阈值：20MB）
- **内容长度**：最大 50万字符（警告阈值：30万字符）
- **处理时间**：最大 600秒（10分钟，警告阈值：480秒）

### 支持的文件格式
- PDF (`.pdf`)
- Word (`.docx`) - ⚠️ 不支持旧版 `.doc` 格式
- PowerPoint (`.pptx`)
- Markdown (`.md`)
- TXT (`.txt`)

### 错误处理
- 完善的异常处理机制（`ProcessingException`）
- 结构化错误类型和用户操作建议
- 文档大小验证和处理时间控制
- 超时检测和兜底策略

---

## 六、主要变更记录

### v1.0（2025-12-19）

1. **错误处理增强**
   - 新增 `ProcessingException` 和结构化错误类型
   - 所有处理器增加异常处理和兜底策略

2. **文档大小限制调整**
   - 处理时间限制：300秒 → 600秒
   - 新增文档大小验证服务

3. **格式支持优化**
   - `.doc` 格式友好提示
   - 引导用户转换为 `.docx`

4. **新功能**
   - 置信度和来源显示（ConfidenceBadge、SourceList）
   - 段落切分服务（SourceSegmenter）
   - 文本预处理服务

5. **修复与优化**
   - 修复 Nginx 502 错误（动态 DNS 解析）
   - 改进 AI 服务 JSON 解析
   - 优化前端错误提示

---

## 七、文档维护说明

### 文档分类

1. **核心文档**（`.trae/documents/`）
   - 已实现功能的需求、设计、实施计划
   - 技术参考文档

2. **归档文档**（`.trae/archive/`）
   - `process_analysis/` - 过程分析文档（可行性分析、风险评估等）
   - `unimplemented/` - 未实现需求文档（扩展功能规划、第二阶段需求等）

### 文档更新原则

1. **核心文档**：随功能实现持续更新
2. **归档文档**：仅归档，不再更新
3. **升级文档**：记录重大变更和系统状态

---

## 八、快速导航

### 开发文档
- 需求文档：`it_helper_requirements.md`
- 技术方案：`it_helper_design.md`
- 实施计划：`it_helper_tasks.md`

### 功能文档
- 置信度功能：`confidence_and_sources_requirements.md`、`confidence_and_sources_design.md`、`confidence_and_sources_tasks.md`

### 技术参考
- DeepSeek API：`DeepSeek_API用途说明.md`
- 向量化方案：`DeepSeek向量化实现方案.md`、`向量化服务替代方案.md`

### 归档文档
- 过程分析：`.trae/archive/process_analysis/`
- 未实现需求：`.trae/archive/unimplemented/`

---

**文档维护者**：开发团队
**最后更新**：2025-12-19

