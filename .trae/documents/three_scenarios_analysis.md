# 三个核心场景差异分析

## 一、核心功能理解

您说得对，**系统的核心功能确实是"解析文档，并整理内容"**。三个场景都遵循相同的基础流程：
1. 文档内容提取
2. 段落切分
3. 调用DeepSeek API处理
4. 计算置信度和来源
5. 返回结构化结果

## 二、三个场景的具体差异

### 2.1 技术文档处理器 (TechnicalProcessor)

**处理步骤**：
1. 前置条件分析（required/recommended）
2. 学习路径规划（多阶段列表）
3. 学习方法建议（theory/practice）
4. 技术关联分析（technologies列表）

**输出结构**：
```json
{
  "prerequisites": {...},
  "learning_path": [...],
  "learning_methods": {...},
  "related_technologies": {...}
}
```

**特点**：
- 4个主要处理步骤
- 输出结构相对简单
- 所有字段都有置信度和来源（完整展示）

---

### 2.2 面试题文档处理器 (InterviewProcessor)

**处理步骤**：
1. 内容总结（key_points, question_types, difficulty, total_questions）
2. 问题生成（generated_questions列表）
3. 答案提取（answers列表）

**输出结构**：
```json
{
  "summary": {...},
  "generated_questions": [...],
  "extracted_answers": {...}
}
```

**特点**：
- 3个主要处理步骤
- 输出结构中等复杂度
- 部分字段有置信度和来源（弱展示）

---

### 2.3 架构文档处理器 (ArchitectureProcessor)

**处理步骤**：
1. 配置流程提取（config_steps列表）
2. 组件识别（components列表）
3. 全景视图生成（architecture_view文本）
4. 白话串讲（plain_explanation文本）
5. 配置检查清单（checklist）
6. 技术栈提取（related_technologies）

**输出结构**：
```json
{
  "config_steps": [...],
  "components": [...],
  "architecture_view": "...",
  "plain_explanation": "...",
  "checklist": {...},
  "related_technologies": {...}
}
```

**特点**：
- **6个主要处理步骤**（最复杂）
- 输出结构最复杂
- **有进度回调机制**（5个步骤的进度更新）
- 部分字段有置信度和来源（弱展示）

---

## 三、为什么需要分别测试？

### 3.1 不同的AI调用模式

虽然都调用DeepSeek API，但调用模式不同：

| 场景 | AI调用次数 | 调用复杂度 | 特殊处理 |
|------|-----------|-----------|---------|
| 技术文档 | 4次 | 中等 | 技术名词清理 |
| 面试题 | 3次 | 简单 | 弱展示模式 |
| 架构文档 | 6次 | **最复杂** | **进度回调**、长文本截断 |

**架构文档的特殊性**：
- 有进度回调，需要测试回调机制
- 内容可能很长，有特殊截断逻辑（前15000字符 + 后5000字符）
- 处理步骤最多，失败风险最高

### 3.2 不同的输出结构验证

每个场景的输出结构不同，需要验证的字段也不同：

**技术文档需要验证**：
- `prerequisites.required` 和 `prerequisites.recommended` 存在
- `learning_path` 是列表，每个阶段有 `stage`, `title`, `content`
- `learning_methods.theory` 和 `learning_methods.practice` 存在
- `related_technologies.technologies` 是列表

**面试题需要验证**：
- `summary.key_points` 是列表
- `summary.question_types` 是字典
- `generated_questions` 是列表，每个问题有 `question` 和 `answer`
- `extracted_answers.answers` 是列表

**架构文档需要验证**：
- `config_steps` 是列表，每个步骤有 `step`, `description`
- `components` 是列表，每个组件有 `name`, `description`
- `architecture_view` 是字符串（可能包含Mermaid代码）
- `plain_explanation` 是字符串
- `checklist.items` 是列表

### 3.3 不同的错误处理路径

虽然都有异常处理，但失败点不同：

**技术文档**：
- 4个处理步骤，任何一个失败都有默认值
- 相对简单，失败影响较小

**面试题**：
- 3个处理步骤
- 问题生成失败影响较大（核心功能）

**架构文档**：
- **6个处理步骤**，失败点最多
- **进度回调机制**，需要测试回调是否正常
- 任何一个步骤失败都可能影响用户体验

### 3.4 不同的性能特征

| 场景 | 预计处理时间 | API调用次数 | 复杂度 |
|------|------------|-----------|--------|
| 技术文档 | 60-90秒 | 4次 | 中等 |
| 面试题 | 45-70秒 | 3次 | 简单 |
| 架构文档 | **90-120秒** | **6次** | **最复杂** |

架构文档处理时间最长，最容易超时，需要重点测试。

---

## 四、回归测试的优化建议

### 4.1 测试策略调整

基于您的观察，可以优化测试策略：

**方案A：统一测试框架 + 场景差异化验证**

```python
# 统一的测试基础流程
async def test_document_processing_base(document_type: str, expected_fields: List[str]):
    """统一的文档处理测试基础流程"""
    # 1. 上传文档
    # 2. 触发处理
    # 3. 等待完成
    # 4. 验证基础结构（所有场景通用）
    assert result["document_type"] == document_type
    assert "result" in result
    
    # 5. 验证场景特定字段
    for field in expected_fields:
        assert field in result["result"]
    
    # 6. 验证置信度和来源（所有场景通用）
    validate_confidence_and_sources(result["result"])

# 场景特定的测试
async def test_technical_document():
    await test_document_processing_base(
        "technical",
        ["prerequisites", "learning_path", "learning_methods", "related_technologies"]
    )

async def test_interview_document():
    await test_document_processing_base(
        "interview",
        ["summary", "generated_questions", "extracted_answers"]
    )

async def test_architecture_document():
    await test_document_processing_base(
        "architecture",
        ["config_steps", "components", "architecture_view", "plain_explanation", "checklist"]
    )
    # 额外测试：进度回调机制
    await test_progress_callback()
```

**方案B：重点测试架构文档**

既然架构文档最复杂，可以：
- 架构文档：完整测试（6个步骤 + 进度回调）
- 技术文档和面试题：简化测试（只验证核心字段）

### 4.2 测试用例精简

**核心测试点**（所有场景通用）：
1. ✅ 文档能成功处理
2. ✅ 输出结构正确
3. ✅ 置信度和来源字段存在
4. ✅ API调用成功

**场景特定测试点**：
- 技术文档：验证4个主要字段
- 面试题：验证3个主要字段
- 架构文档：验证6个主要字段 + 进度回调

---

## 五、结论

### 5.1 您的观察是正确的

- ✅ 核心功能确实是"解析文档，并整理内容"
- ✅ 三个场景的基础流程相同
- ✅ 都调用相同的AI服务

### 5.2 但仍然需要分别测试

**原因**：
1. **输出结构不同**：需要验证不同的字段
2. **处理复杂度不同**：架构文档最复杂，需要重点测试
3. **特殊机制不同**：架构文档有进度回调，需要单独测试
4. **失败风险不同**：架构文档处理步骤最多，失败风险最高

### 5.3 优化建议

**测试策略**：
- 使用统一的测试基础框架
- 场景特定的验证逻辑
- 重点测试架构文档（最复杂）
- 技术文档和面试题可以简化测试

**测试用例数量**：
- 架构文档：完整测试（6个步骤）
- 技术文档：核心测试（4个字段）
- 面试题：核心测试（3个字段）

这样既能保证测试覆盖，又能提高测试效率。

---

**文档版本**：v1.0
**创建时间**：2025-12-19
**最后更新**：2025-12-19

