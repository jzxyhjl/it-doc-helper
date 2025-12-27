# 多视角API接口文档

## 一、概述

系统支持多视角文档处理，允许用户根据文档内容特征选择不同的处理视角。每个文档可以同时拥有多个视角的处理结果。

### 视角类型

- **learning**（学习视角）：原技术文档结构，用于学习路径、前置条件等
- **qa**（问答视角）：原面试题结构，用于问题生成、答案提取等
- **system**（系统视角）：原架构文档结构，用于组件识别、架构视图等

---

## 二、API接口

### 2.1 上传文档（支持指定视角）

**接口**：`POST /api/v1/documents/upload`

**描述**：上传文档并指定要处理的视角

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | File | 是 | 文档文件 |
| `views` | String | 否 | 要处理的视角，多个视角用逗号分隔（如：`learning,system`）。如果不指定，系统会自动推荐 |

**请求示例**：

```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@document.pdf" \
  -F "views=learning,system"
```

**响应示例**：

```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "document.pdf",
  "status": "pending",
  "message": "文档上传成功，正在处理..."
}
```

---

### 2.2 推荐视角

**接口**：`POST /api/v1/documents/{document_id}/recommend-views`

**描述**：获取系统推荐的视角（主视角和次视角）

**路径参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `document_id` | String | 文档ID |

**响应示例**：

```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "primary_view": "learning",
  "enabled_views": ["learning", "system"],
  "detection_scores": {
    "learning": 0.85,
    "qa": 0.15,
    "system": 0.65
  },
  "cache_key": "doc:550e8400-e29b-41d4-a716-446655440000:detection:learning:0.85,qa:0.15,system:0.65",
  "type_mapping": {
    "technical": "learning",
    "interview": "qa",
    "architecture": "system"
  },
  "method": "rule"
}
```

**字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `primary_view` | String | 主视角（系统推荐的主要处理视角） |
| `enabled_views` | Array | 启用的视角列表（检测到哪些特征就生成哪些视角） |
| `detection_scores` | Object | 各视角的检测得分（0-1） |
| `cache_key` | String | 缓存key（基于检测得分生成，用于快速切换视角） |
| `type_mapping` | Object | 类型到视角的映射（向后兼容） |
| `method` | String | 检测方法（rule/ai） |

---

### 2.3 获取处理结果（单视角）

**接口**：`GET /api/v1/documents/{document_id}/result?view={view}`

**描述**：获取指定视角的处理结果

**路径参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `document_id` | String | 文档ID |

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `view` | String | 否 | 视角名称（learning/qa/system）。如果不指定，返回多视角容器 |

**响应示例**（learning视角）：

```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "view": "learning",
  "document_type": "technical",
  "result": {
    "prerequisites": {...},
    "learning_path": [...],
    "learning_methods": {...},
    "related_technologies": {...}
  },
  "processing_time": 120,
  "quality_score": 85,
  "created_at": "2025-12-21T12:00:00Z"
}
```

---

### 2.4 获取处理结果（多视角）

**接口**：`GET /api/v1/documents/{document_id}/result?views={view1,view2}`

**描述**：获取多个视角的处理结果

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `views` | String | 否 | 视角名称，多个视角用逗号分隔（如：`learning,system`）。如果不指定，返回所有可用视角 |

**响应示例**：

```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "requested_views": ["learning", "system"],
  "results": {
    "learning": {
      "prerequisites": {...},
      "learning_path": [...],
      "learning_methods": {...},
      "related_technologies": {...}
    },
    "system": {
      "components": [...],
      "architecture_view": {...},
      "config_steps": [...],
      "plain_explanation": "..."
    }
  }
}
```

---

### 2.5 获取处理结果（所有视角）

**接口**：`GET /api/v1/documents/{document_id}/result`

**描述**：获取所有可用视角的处理结果（多视角输出容器）

**响应示例**：

```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "views": {
    "learning": {
      "prerequisites": {...},
      "learning_path": [...],
      "learning_methods": {...},
      "related_technologies": {...}
    },
    "system": {
      "components": [...],
      "architecture_view": {...},
      "config_steps": [...],
      "plain_explanation": "..."
    }
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

---

### 2.6 获取视角状态

**接口**：`GET /api/v1/documents/{document_id}/views/status`

**描述**：获取各视角的处理状态（用于UI轮询，显示"正在生成..."状态）

**响应示例**：

```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "views_status": {
    "learning": {
      "view": "learning",
      "status": "completed",
      "ready": true,
      "processing_time": 120,
      "is_primary": true
    },
    "system": {
      "view": "system",
      "status": "processing",
      "ready": false,
      "processing_time": null,
      "is_primary": false
    }
  },
  "primary_view": "learning",
  "enabled_views": ["learning", "system"]
}
```

**状态说明**：

| 状态 | 说明 |
|------|------|
| `pending` | 待处理 |
| `processing` | 正在处理 |
| `completed` | 已完成 |
| `failed` | 处理失败 |

---

### 2.7 切换视角

**接口**：`POST /api/v1/documents/{document_id}/switch-view?view={view}`

**描述**：切换到指定视角（复用中间结果，快速生成）

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `view` | String | 是 | 目标视角名称（learning/qa/system） |

**响应示例**：

```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "view": "system",
  "result": {
    "components": [...],
    "architecture_view": {...},
    "config_steps": [...],
    "plain_explanation": "..."
  },
  "from_cache": false,
  "used_intermediate_results": true,
  "processing_time": 5
}
```

**字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `from_cache` | Boolean | 是否从缓存获取（如果结果已存在） |
| `used_intermediate_results` | Boolean | 是否使用了中间结果（快速切换） |
| `processing_time` | Integer | 处理耗时（秒），快速切换通常 < 5秒 |

---

## 三、错误码

| 错误码 | 说明 |
|--------|------|
| `400` | 请求参数错误（如：无效的视角名称） |
| `404` | 文档不存在 |
| `422` | 文档处理失败 |
| `500` | 服务器内部错误 |

**错误响应示例**：

```json
{
  "detail": "无效的视角名称：invalid_view。支持的视角：learning, qa, system"
}
```

---

## 四、向后兼容性

系统支持向后兼容，旧的API调用仍然可以正常工作：

### 4.1 旧API参数

旧的 `document_type` 参数会自动转换为 `view` 参数：

- `document_type=technical` → `view=learning`
- `document_type=interview` → `view=qa`
- `document_type=architecture` → `view=system`

### 4.2 历史数据

历史数据会自动迁移：

- 缺少 `view` 字段的处理结果会自动填充
- 缺少视角字段的文档类型会自动填充
- 旧格式的结果会自动转换为多视角容器格式

---

## 五、最佳实践

### 5.1 上传文档

1. **不指定视角**：让系统自动推荐（推荐）
   ```bash
   curl -X POST "http://localhost:8000/api/v1/documents/upload" \
     -F "file=@document.pdf"
   ```

2. **指定视角**：明确指定要处理的视角
   ```bash
   curl -X POST "http://localhost:8000/api/v1/documents/upload" \
     -F "file=@document.pdf" \
     -F "views=learning,system"
   ```

### 5.2 获取结果

1. **获取主视角结果**（最快）：
   ```bash
   GET /api/v1/documents/{id}/result?view=learning
   ```

2. **获取所有视角结果**（完整）：
   ```bash
   GET /api/v1/documents/{id}/result
   ```

3. **轮询视角状态**（UI显示进度）：
   ```bash
   GET /api/v1/documents/{id}/views/status
   ```

### 5.3 切换视角

1. **快速切换**（复用中间结果）：
   ```bash
   POST /api/v1/documents/{id}/switch-view?view=system
   ```

2. **检查是否已存在**（避免重复处理）：
   ```bash
   GET /api/v1/documents/{id}/views/status
   ```

---

**文档版本**：v1.0  
**最后更新**：2025-12-21

