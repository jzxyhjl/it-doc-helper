# 测试数据说明

## 测试文档

测试文档存放在 `test_documents/` 目录，用于回归测试。

### 文档要求

1. **内容固定**：测试文档内容应该固定，确保测试结果可复现
2. **版本控制**：测试文档应该纳入版本控制，避免内容变化
3. **文档大小**：建议使用中等大小的文档（1-5MB），避免测试时间过长

### 测试文档列表

#### test_technical.pdf
- **类型**：技术文档
- **内容**：IT技术教程（如Python、Java、Docker等）
- **预期结果**：
  - `prerequisites` - 前置条件分析
  - `learning_path` - 学习路径规划（至少3个阶段）
  - `learning_methods` - 学习方法建议
  - `related_technologies` - 技术关联分析

#### test_interview.docx
- **类型**：面试题文档
- **内容**：技术面试题目（如Java面试题、Python面试题等）
- **预期结果**：
  - `summary` - 内容总结（key_points, question_types, difficulty, total_questions）
  - `generated_questions` - 生成的问题列表（至少3个问题）
  - `extracted_answers` - 提取的答案列表

#### test_architecture.md
- **类型**：架构文档
- **内容**：系统架构/搭建文档（如Spring Boot搭建、Docker部署等）
- **预期结果**：
  - `config_steps` - 配置步骤列表（至少5个步骤）
  - `components` - 组件识别列表（至少3个组件）
  - `architecture_view` - 架构视图（可能包含Mermaid代码）
  - `plain_explanation` - 白话解释
  - `checklist` - 检查清单
  - `related_technologies` - 技术栈列表

### 文档获取

测试文档可以通过以下方式获取：

1. **使用现有文档**：从项目的 `uploads/` 目录选择合适的文档
2. **创建测试文档**：手动创建符合要求的测试文档
3. **下载示例文档**：从公开资源下载示例文档

**注意**：确保测试文档不包含敏感信息，可以公开使用。

