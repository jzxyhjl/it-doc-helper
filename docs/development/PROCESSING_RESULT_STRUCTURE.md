# 文档处理结果结构说明

## 一、概述

系统支持多视角处理，每个文档可以同时拥有多个视角的处理结果。结果以**多视角输出容器**的形式返回。

### 1.1 多视角输出容器

多视角输出容器包含所有可用视角的结果，结构如下：

```json
{
  "document_id": "uuid-string",
  "views": {
    "learning": {...学习视角结果...},
    "qa": {...问答视角结果...},
    "system": {...系统视角结果...}
  },
  "meta": {
    "enabled_views": ["learning", "system"],
    "primary_view": "learning",
    "confidence": {
      "learning": 0.85,
      "system": 0.65
    },
    "view_count": 2,
    "timestamp": "2025-12-21T12:00:00Z"
  }
}
```

**注意**：不是每个文档都有所有视角，只有检测到特征的视角才会生成结果。

### 1.2 单视角响应格式

获取单个视角的结果时，返回格式如下：

```json
{
  "document_id": "uuid-string",
  "view": "learning",
  "document_type": "technical",
  "result": {
    // 具体的结果数据（见下方各场景说明）
  },
  "processing_time": 120,  // 处理耗时（秒）
  "quality_score": 85,     // 质量分数（0-100）
  "created_at": "2025-12-21T12:00:00Z"
}
```

### 1.2 数据库存储结构

处理结果存储在 `processing_results` 表中：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID | 结果ID |
| `document_id` | UUID | 文档ID（唯一） |
| `document_type` | VARCHAR(50) | 文档类型 |
| `result_data` | JSONB | 处理结果数据（JSON格式） |
| `processing_time` | INTEGER | 处理耗时（秒） |
| `created_at` | TIMESTAMP | 创建时间 |
| `updated_at` | TIMESTAMP | 更新时间 |

---

## 二、技术文档处理结果结构

### 2.1 输出字段

技术文档处理结果包含 **4个主要字段**：

```json
{
  "prerequisites": {...},
  "learning_path": [...],
  "learning_methods": {...},
  "related_technologies": {...}
}
```

### 2.2 详细结构

#### 2.2.1 prerequisites（前置条件）

```json
{
  "prerequisites": {
    "required": ["前置知识1", "前置知识2", ...],
    "recommended": ["推荐知识1", "推荐知识2", ...],
    "confidence": 85,                    // 置信度分数（0-100）
    "confidence_label": "high",            // 置信度标签（high/medium/low）
    "confidence_factors": {                // 置信度因子
      "base_confidence": 85,
      "source_count": 3,
      "content_length": 5000
    },
    "sources": [                           // 来源片段
      {
        "id": 1,
        "text": "原文片段...",
        "position": {"start": 100, "end": 200}
      }
    ]
  }
}
```

#### 2.2.2 learning_path（学习路径）

```json
{
  "learning_path": [
    {
      "stage": 1,                         // 阶段编号
      "title": "阶段标题",
      "content": "阶段内容描述",
      "confidence": 90,                   // 置信度分数
      "confidence_label": "high",
      "sources": [                        // 来源片段
        {
          "id": 2,
          "text": "原文片段...",
          "position": {"start": 300, "end": 400}
        }
      ]
    },
    // ... 更多阶段
  ]
}
```

#### 2.2.3 learning_methods（学习方法）

```json
{
  "learning_methods": {
    "theory": "理论学习方法描述",
    "practice": "实践学习方法描述",
    "confidence": 80,
    "confidence_label": "high",
    "confidence_factors": {...},
    "sources": [...]
  }
}
```

#### 2.2.4 related_technologies（相关技术）

```json
{
  "related_technologies": {
    "technologies": ["Spring Boot", "RocketMQ", "MySQL", ...],  // 最多10个
    "confidence": 75,
    "confidence_label": "medium",
    "confidence_factors": {...},
    "sources": [...]
  }
}
```

### 2.3 特点

- ✅ **完整展示模式**：所有字段都包含置信度和来源信息
- ✅ **4个处理步骤**：前置条件、学习路径、学习方法、技术关联
- ✅ **技术名词清理**：自动清理技术名词中的中文翻译

---

## 三、面试题文档处理结果结构

### 3.1 输出字段

面试题文档处理结果包含 **3个主要字段**：

```json
{
  "summary": {...},
  "generated_questions": [...],
  "extracted_answers": {...}
}
```

### 3.2 详细结构

#### 3.2.1 summary（内容总结）

```json
{
  "summary": {
    "key_points": ["知识点1", "知识点2", ...],
    "question_types": {
      "选择题": 10,
      "问答题": 5,
      "编程题": 3
    },
    "difficulty": {
      "简单": 5,
      "中等": 8,
      "困难": 2
    },
    "total_questions": 15,
    "confidence": 85,                    // 可选（弱展示）
    "confidence_label": "high",           // 可选
    "sources": [...]                      // 可选
  }
}
```

#### 3.2.2 generated_questions（生成的问题）

```json
{
  "generated_questions": [
    {
      "question": "问题内容",
      "answer": "答案内容",
      "hint": "提示信息",                 // 可选
      "difficulty": "medium",             // 可选
      "confidence": 80,                   // 可选（弱展示）
      "confidence_label": "high",         // 可选
      "sources": [...]                    // 可选
    },
    // ... 更多问题
  ]
}
```

#### 3.2.3 extracted_answers（提取的答案）

```json
{
  "extracted_answers": {
    "answers": ["答案1", "答案2", ...],   // 最多20个
    "confidence": 75,                     // 可选（弱展示）
    "confidence_label": "medium",         // 可选
    "sources": [...]                      // 可选
  }
}
```

### 3.3 特点

- ⚠️ **弱展示模式**：置信度和来源字段可选，不强制要求
- ✅ **3个处理步骤**：内容总结、问题生成、答案提取
- ✅ **灵活验证**：如果AI返回了置信度，则验证；否则不强制

---

## 四、架构文档处理结果结构

### 4.1 输出字段

架构文档处理结果包含 **6个主要字段**：

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

### 4.2 详细结构

#### 4.2.1 config_steps（配置步骤）

```json
{
  "config_steps": [
    {
      "step": 1,
      "description": "配置步骤描述",
      "confidence": 85,                   // 可选（弱展示）
      "confidence_label": "high",         // 可选
      "sources": [...]                    // 可选
    },
    // ... 更多步骤
  ]
}
```

#### 4.2.2 components（组件识别）

```json
{
  "components": [
    {
      "name": "组件名称",
      "description": "组件描述",
      "type": "service|database|queue|...",  // 可选
      "confidence": 90,                   // 可选（弱展示）
      "confidence_label": "high",         // 可选
      "sources": [...]                    // 可选
    },
    // ... 更多组件
  ]
}
```

#### 4.2.3 architecture_view（架构视图）

```json
{
  "architecture_view": "架构视图文本（可能包含Mermaid代码）",
  "confidence": 80,                       // 可选（弱展示）
  "confidence_label": "high",             // 可选
  "sources": [...]                        // 可选
}
```

#### 4.2.4 plain_explanation（白话串讲）

```json
{
  "plain_explanation": "白话串讲文本",
  "confidence": 75,                       // 可选（弱展示）
  "confidence_label": "medium",           // 可选
  "sources": [...]                        // 可选
}
```

#### 4.2.5 checklist（检查清单）

```json
{
  "checklist": {
    "items": ["检查项1", "检查项2", ...],  // 最多20个
    "confidence": 85,                     // 可选（弱展示）
    "confidence_label": "high",           // 可选
    "sources": [...]                      // 可选
  }
}
```

#### 4.2.6 related_technologies（相关技术）

```json
{
  "related_technologies": {
    "technologies": ["Java", "Spring Boot", "MySQL", ...],  // 最多20个
    "confidence": 80,                     // 可选（弱展示）
    "confidence_label": "high",           // 可选
    "sources": [...]                      // 可选
  }
}
```

### 4.3 特点

- ⚠️ **弱展示模式**：置信度和来源字段可选
- ✅ **6个处理步骤**：最复杂的处理流程
- ✅ **进度回调机制**：处理过程中会更新进度（5个步骤）
- ✅ **长文本处理**：自动截断超长内容（前15000字符 + 后5000字符）

---

## 五、置信度和来源字段说明

### 5.1 置信度字段

所有场景都支持置信度字段，但展示模式不同：

| 字段 | 类型 | 说明 |
|------|------|------|
| `confidence` | Integer | 置信度分数（0-100） |
| `confidence_label` | String | 置信度标签（high/medium/low） |
| `confidence_factors` | Object | 置信度因子（可选） |

**置信度标签规则**：
- `high`: 80-100
- `medium`: 50-79
- `low`: 0-49

### 5.2 来源字段

所有场景都支持来源字段：

```json
{
  "sources": [
    {
      "id": 1,                           // 段落ID
      "text": "原文片段（最多200字符）",
      "position": {
        "start": 100,                     // 起始位置
        "end": 200                        // 结束位置
      }
    }
  ]
}
```

### 5.3 展示模式对比

| 场景 | 展示模式 | 说明 |
|------|---------|------|
| 技术文档 | **完整展示** | 所有字段都包含置信度和来源 |
| 面试题 | **弱展示** | 置信度和来源可选，不强制 |
| 架构文档 | **弱展示** | 置信度和来源可选，不强制 |

---

## 六、数据清理说明

### 6.1 技术名词清理

系统会自动清理技术名词中的中文翻译：

**清理前**：
```json
{
  "technologies": ["Spring Boot（春波特）", "RocketMQ（火箭MQ）"]
}
```

**清理后**：
```json
{
  "technologies": ["Spring Boot", "RocketMQ"]
}
```

### 6.2 结果清理

通过 `clean_processing_result()` 函数自动清理：
- 移除技术名词中的中文翻译
- 保持技术名词的原始英文形式
- 递归处理嵌套结构

---

## 七、质量评估

### 7.1 质量分数

系统会根据处理结果计算质量分数（0-100）：

| 场景 | 评估维度 |
|------|---------|
| 技术文档 | 字段完整性、内容质量、置信度 |
| 面试题 | 问题数量、答案质量、总结完整性 |
| 架构文档 | 组件识别、配置步骤、视图完整性 |

### 7.2 质量分数存储

质量分数存储在 `system_learning_data` 表的 `quality_score` 字段中。

---

## 八、示例数据

### 8.1 技术文档示例

```json
{
  "document_id": "123e4567-e89b-12d3-a456-426614174000",
  "document_type": "technical",
  "result": {
    "prerequisites": {
      "required": ["Java基础", "Spring框架"],
      "recommended": ["Maven", "Git"],
      "confidence": 85,
      "confidence_label": "high",
      "sources": [...]
    },
    "learning_path": [
      {
        "stage": 1,
        "title": "基础概念",
        "content": "学习Spring Boot的基本概念...",
        "confidence": 90,
        "sources": [...]
      }
    ],
    "learning_methods": {
      "theory": "阅读官方文档...",
      "practice": "完成实际项目...",
      "confidence": 80,
      "sources": [...]
    },
    "related_technologies": {
      "technologies": ["Spring Boot", "MySQL", "Redis"],
      "confidence": 75,
      "sources": [...]
    }
  },
  "processing_time": 120,
  "quality_score": 85,
  "created_at": "2025-12-21T12:00:00Z"
}
```

### 8.2 面试题文档示例

```json
{
  "document_id": "123e4567-e89b-12d3-a456-426614174001",
  "document_type": "interview",
  "result": {
    "summary": {
      "key_points": ["Java基础", "多线程", "集合框架"],
      "question_types": {"选择题": 10, "问答题": 5},
      "difficulty": {"简单": 5, "中等": 8, "困难": 2},
      "total_questions": 15
    },
    "generated_questions": [
      {
        "question": "什么是Java的多线程？",
        "answer": "Java多线程是指...",
        "confidence": 80
      }
    ],
    "extracted_answers": {
      "answers": ["答案1", "答案2"]
    }
  },
  "processing_time": 90,
  "quality_score": 80,
  "created_at": "2025-12-21T12:00:00Z"
}
```

### 8.3 架构文档示例

```json
{
  "document_id": "123e4567-e89b-12d3-a456-426614174002",
  "document_type": "architecture",
  "result": {
    "config_steps": [
      {
        "step": 1,
        "description": "配置数据库连接",
        "confidence": 85
      }
    ],
    "components": [
      {
        "name": "API Gateway",
        "description": "API网关服务",
        "type": "service",
        "confidence": 90
      }
    ],
    "architecture_view": "```mermaid\ngraph TD\nA[Gateway] --> B[Service]\n```",
    "plain_explanation": "系统架构包括...",
    "checklist": {
      "items": ["检查数据库连接", "检查服务配置"],
      "confidence": 80
    },
    "related_technologies": {
      "technologies": ["Spring Boot", "MySQL", "Redis"],
      "confidence": 75
    }
  },
  "processing_time": 150,
  "quality_score": 85,
  "created_at": "2025-12-21T12:00:00Z"
}
```

---

## 九、字段对比表

| 字段 | 技术文档 | 面试题 | 架构文档 |
|------|---------|--------|---------|
| 主要字段数 | 4 | 3 | 6 |
| 处理步骤数 | 4 | 3 | 6 |
| 置信度展示 | ✅ 完整 | ⚠️ 可选 | ⚠️ 可选 |
| 来源展示 | ✅ 完整 | ⚠️ 可选 | ⚠️ 可选 |
| 进度回调 | ❌ | ❌ | ✅ |
| 技术名词清理 | ✅ | ❌ | ✅ |
| 预计处理时间 | 60-90秒 | 45-70秒 | 90-120秒 |

---

**文档版本**：v1.0  
**创建时间**：2025-12-21  
**最后更新**：2025-12-21

