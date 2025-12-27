# 测试文档占位符说明

## 重要提示

此目录用于存放回归测试的固定测试文档。由于无法直接创建二进制文件（PDF、DOCX），请按照以下方式准备测试文档：

## 测试文档要求

### 1. test_technical.pdf
- **类型**：技术文档
- **内容**：IT技术教程（建议使用Python、Java、Docker等技术文档）
- **大小**：1-5MB
- **预期结果**：
  - 包含前置条件分析
  - 包含学习路径规划（至少3个阶段）
  - 包含学习方法建议
  - 包含技术关联分析

**获取方式**：
- 从项目的 `uploads/` 目录选择合适的PDF技术文档
- 或从公开资源下载示例技术文档
- 复制到 `backend/tests/fixtures/test_documents/test_technical.pdf`

### 2. test_interview.docx
- **类型**：面试题文档
- **内容**：技术面试题目（建议使用Java、Python等面试题）
- **大小**：500KB-2MB
- **预期结果**：
  - 包含内容总结（key_points, question_types, difficulty, total_questions）
  - 包含生成的问题列表（至少3个问题）
  - 包含提取的答案列表

**获取方式**：
- 从项目的 `uploads/` 目录选择合适的DOCX面试题文档
- 或创建Word文档，包含面试题目和答案
- 复制到 `backend/tests/fixtures/test_documents/test_interview.docx`

### 3. test_architecture.md
- **类型**：架构文档
- **内容**：系统架构/搭建文档（建议使用Spring Boot、Docker等搭建文档）
- **大小**：50KB-500KB
- **预期结果**：
  - 包含配置步骤列表（至少5个步骤）
  - 包含组件识别列表（至少3个组件）
  - 包含架构视图（可能包含Mermaid代码）
  - 包含白话解释
  - 包含检查清单
  - 包含技术栈列表

**获取方式**：
- 可以使用项目的 `test_document.md` 作为基础
- 或创建Markdown文档，包含系统搭建步骤
- 复制到 `backend/tests/fixtures/test_documents/test_architecture.md`

## 快速开始

如果项目 `uploads/` 目录已有合适的文档，可以快速创建测试文档：

```bash
# 复制技术文档
cp uploads/your_technical_doc.pdf backend/tests/fixtures/test_documents/test_technical.pdf

# 复制面试题文档
cp uploads/your_interview_doc.docx backend/tests/fixtures/test_documents/test_interview.docx

# 复制或创建架构文档
cp test_document.md backend/tests/fixtures/test_documents/test_architecture.md
```

## 注意事项

1. **文档内容固定**：确保测试文档内容固定，避免测试结果不稳定
2. **版本控制**：测试文档应该纳入版本控制（如果文件不太大）
3. **文档大小**：建议使用中等大小的文档，避免测试时间过长
4. **不包含敏感信息**：确保测试文档不包含敏感信息，可以公开使用

## 验证测试文档

运行以下命令验证测试文档是否存在：

```bash
ls -lh backend/tests/fixtures/test_documents/
```

应该看到三个文件：
- test_technical.pdf
- test_interview.docx
- test_architecture.md

