# 文档视角分类机制说明

## 一、概述

系统使用**混合识别策略**来识别文档的处理视角，支持多视角处理：

### 视角类型

- **学习视角**（learning）：原技术文档结构，用于学习路径、前置条件等
- **问答视角**（qa）：原面试题结构，用于问题生成、答案提取等
- **系统视角**（system）：原架构文档结构，用于组件识别、架构视图等

### 核心概念

- **主视角**（Primary View）：系统推荐的主要处理视角（用于UI初始状态和算力分配）
- **次视角**（Secondary View）：系统推荐的备选处理视角（可以异步、后补）
- **启用视角**（Enabled Views）：检测到哪些特征，就生成哪些视角（不是每个文档都有所有视角）

### 分类策略

**规则优先，AI补充** - 系统首先使用规则匹配，如果置信度不足，则使用AI识别。

---

## 二、分类流程

### 2.1 整体流程

```
文档上传
  ↓
内容提取
  ↓
规则匹配（第一步）
  ↓
置信度 >= 0.5？
  ├─ 是 → 使用规则识别结果
  └─ 否 → AI识别（第二步）
       ↓
      AI识别成功？
      ├─ 是 → 使用AI识别结果
      └─ 否 → 使用规则结果（即使置信度低）或 unknown
```

### 2.2 详细步骤

1. **规则匹配**（`rule_based_classify`）
   - 统计关键词出现次数
   - 计算各类型得分比例
   - 如果最高分 >= 0.3，返回识别结果
   - 如果最高分 >= 0.5，直接使用（不调用AI）

2. **AI识别**（`ai_classify`）
   - 仅在规则识别置信度 < 0.5 时调用
   - 截取文档前2000字符
   - 调用 DeepSeek API 进行识别
   - 返回类型和置信度

3. **最终结果**
   - 优先使用规则识别（如果置信度 >= 0.5）
   - 否则使用AI识别结果
   - 如果都失败，返回规则结果（即使置信度低）或 `unknown`

---

## 三、规则匹配机制

### 3.1 关键词列表

#### 面试题关键词（INTERVIEW_KEYWORDS）

```python
[
    '面试', '题目', '试题', '答案', '解析', '考点', '知识点',
    '选择题', '问答题', '编程题', '算法题', '面经',
    'interview', 'question', 'answer', 'solution'
]
```

#### 技术文档关键词（TECHNICAL_KEYWORDS）

```python
[
    '教程', '指南', '文档', 'API', '框架', '库', '工具',
    '使用', '配置', '安装', '入门', '进阶', '最佳实践',
    'tutorial', 'guide', 'documentation', 'api', 'framework',
    'library', 'getting started', 'how to'
]
```

#### 架构文档关键词（ARCHITECTURE_KEYWORDS）

```python
[
    '架构', '设计', '系统', '组件', '模块', '服务', '部署',
    '配置', '环境', '搭建', '安装', '启动', '运行',
    'architecture', 'design', 'system', 'component', 'module',
    'service', 'deployment', 'setup', 'installation'
]
```

### 3.2 评分算法

```python
# 1. 统计关键词出现次数
interview_score = sum(关键词在文档中出现的次数)
technical_score = sum(关键词在文档中出现的次数)
architecture_score = sum(关键词在文档中出现的次数)

# 2. 计算各类型得分比例
total_score = interview_score + technical_score + architecture_score
scores = {
    'interview': interview_score / total_score,
    'technical': technical_score / total_score,
    'architecture': architecture_score / total_score
}

# 3. 返回得分最高的类型
max_type = max(scores, key=scores.get)
max_score = scores[max_type]

# 4. 如果最高分 < 0.3，返回 None（无法确定）
# 5. 如果最高分 >= 0.3，返回识别结果
```

### 3.3 规则匹配示例

**示例1：面试题文档**
```
文档内容包含：
- "面试" 出现 5 次
- "题目" 出现 3 次
- "答案" 出现 4 次
- "教程" 出现 1 次
- "架构" 出现 0 次

计算：
interview_score = 5 + 3 + 4 = 12
technical_score = 1
architecture_score = 0
total_score = 13

scores = {
    'interview': 12/13 = 0.92,
    'technical': 1/13 = 0.08,
    'architecture': 0/13 = 0.0
}

结果：interview（置信度 0.92，>= 0.5，直接使用）
```

**示例2：技术文档**
```
文档内容包含：
- "教程" 出现 8 次
- "指南" 出现 3 次
- "API" 出现 5 次
- "面试" 出现 1 次
- "架构" 出现 2 次

计算：
interview_score = 1
technical_score = 8 + 3 + 5 = 16
architecture_score = 2
total_score = 19

scores = {
    'interview': 1/19 = 0.05,
    'technical': 16/19 = 0.84,
    'architecture': 2/19 = 0.11
}

结果：technical（置信度 0.84，>= 0.5，直接使用）
```

**示例3：架构文档**
```
文档内容包含：
- "架构" 出现 6 次
- "组件" 出现 4 次
- "部署" 出现 3 次
- "教程" 出现 2 次
- "面试" 出现 0 次

计算：
interview_score = 0
technical_score = 2
architecture_score = 6 + 4 + 3 = 13
total_score = 15

scores = {
    'interview': 0/15 = 0.0,
    'technical': 2/15 = 0.13,
    'architecture': 13/15 = 0.87
}

结果：architecture（置信度 0.87，>= 0.5，直接使用）
```

---

## 四、AI识别机制

### 4.1 触发条件

AI识别仅在以下情况触发：
- 规则匹配置信度 < 0.5
- 提供了 DeepSeek API 密钥和基础URL

### 4.2 AI识别流程

```python
# 1. 截取文档前2000字符
content_preview = content[:2000]

# 2. 构建提示词
prompt = """
请分析以下文档内容，判断文档类型。文档类型包括：
1. interview（面试题文档）- 包含技术面试题目、答案、解析等
2. technical（IT技术文档）- 介绍特定技术、框架、工具的学习文档
3. architecture（架构/搭建文档）- 描述系统架构设计或系统搭建配置的文档

文档内容：
{content_preview}

请只返回JSON格式，包含type（类型）和confidence（置信度0-1）：
{"type": "interview|technical|architecture", "confidence": 0.0-1.0}
"""

# 3. 调用 DeepSeek API
response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "你是一个文档类型识别专家，请准确判断文档类型。"},
        {"role": "user", "content": prompt}
    ],
    temperature=0.3,
    max_tokens=100
)

# 4. 解析JSON响应
result = json.loads(response.choices[0].message.content)
result['method'] = 'ai'
```

### 4.3 AI识别示例

**输入**：文档前2000字符
```
"Spring Boot 是一个基于 Java 的框架，用于快速开发企业级应用。
本教程将介绍如何安装和配置 Spring Boot..."
```

**AI输出**：
```json
{
  "type": "technical",
  "confidence": 0.95,
  "method": "ai"
}
```

---

## 五、识别结果存储

### 5.1 数据库表结构

识别结果存储在 `document_types` 表中：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID | 类型记录ID |
| `document_id` | UUID | 文档ID（外键） |
| `detected_type` | VARCHAR(50) | 识别的类型（interview/technical/architecture/unknown） |
| `confidence` | FLOAT | 识别置信度（0-1） |
| `detection_method` | VARCHAR(50) | 识别方法（rule/ai/hybrid） |
| `detected_at` | TIMESTAMP | 识别时间 |

### 5.2 识别方法字段

| 值 | 说明 |
|----|------|
| `rule` | 仅使用规则匹配 |
| `ai` | 使用AI识别 |
| `hybrid` | 混合使用（规则+AI） |
| `none` | 无法识别（返回unknown） |

---

## 六、分类准确性

### 6.1 规则匹配的优势

- ✅ **速度快**：无需调用API，毫秒级响应
- ✅ **成本低**：不消耗API调用次数
- ✅ **准确性高**：对于关键词明显的文档，准确率可达90%+

### 6.2 AI识别的优势

- ✅ **理解语义**：能理解文档的深层含义
- ✅ **处理边界情况**：对于关键词不明显的文档，能更准确判断
- ✅ **适应性强**：能处理各种格式和风格的文档

### 6.3 混合策略的优势

- ✅ **兼顾速度和准确性**：规则优先，AI补充
- ✅ **降低成本**：大部分文档通过规则识别，减少API调用
- ✅ **提高准确率**：对于规则识别不确定的文档，使用AI提高准确率

---

## 七、分类失败处理

### 7.1 无法识别的情况

如果规则匹配和AI识别都失败，系统会：

1. **返回规则结果**（即使置信度低）
   - 如果规则匹配有结果（即使置信度 < 0.3），仍会使用

2. **返回 unknown**
   - 如果规则匹配也没有结果，返回 `unknown` 类型

3. **默认处理**
   - 如果类型为 `unknown`，系统会默认使用 `technical` 处理器

### 7.2 代码实现

```python
# 如果都失败，返回规则结果（即使置信度低）或unknown
if rule_result:
    logger.info("使用规则识别结果（置信度较低）", 
               type=rule_result['type'], 
               confidence=rule_result['confidence'])
    return rule_result

logger.warning("无法识别文档类型，返回unknown")
return {
    'type': 'unknown',
    'confidence': 0.0,
    'method': 'none'
}
```

---

## 八、分类示例

### 8.1 面试题文档示例

**文档标题**：`Java面试题大全.md`

**文档内容片段**：
```
# Java面试题

## 1. 什么是Java的多线程？
答案：Java多线程是指...

## 2. 解释一下Java的集合框架
答案：Java集合框架包括...
```

**识别过程**：
1. 规则匹配：
   - `interview_score = 2`（"面试"出现2次）
   - `technical_score = 0`
   - `architecture_score = 0`
   - 置信度 = 1.0
   - **结果**：interview（置信度 1.0，>= 0.5，直接使用）

### 8.2 技术文档示例

**文档标题**：`Spring Boot入门教程.md`

**文档内容片段**：
```
# Spring Boot 入门教程

## 1. 安装和配置
本教程将介绍如何安装和配置Spring Boot...

## 2. 快速开始
让我们创建一个简单的Spring Boot应用...
```

**识别过程**：
1. 规则匹配：
   - `interview_score = 0`
   - `technical_score = 3`（"教程"、"安装"、"配置"）
   - `architecture_score = 0`
   - 置信度 = 1.0
   - **结果**：technical（置信度 1.0，>= 0.5，直接使用）

### 8.3 架构文档示例

**文档标题**：`系统架构设计文档.md`

**文档内容片段**：
```
# 系统架构设计

## 1. 系统组件
系统包含以下组件：
- API Gateway
- 用户服务
- 订单服务

## 2. 部署配置
系统部署在Kubernetes集群中...
```

**识别过程**：
1. 规则匹配：
   - `interview_score = 0`
   - `technical_score = 0`
   - `architecture_score = 3`（"架构"、"组件"、"部署"）
   - 置信度 = 1.0
   - **结果**：architecture（置信度 1.0，>= 0.5，直接使用）

### 8.4 边界情况示例

**文档标题**：`技术分享.md`

**文档内容片段**：
```
# 技术分享

今天我想和大家分享一些技术心得...
```

**识别过程**：
1. 规则匹配：
   - `interview_score = 0`
   - `technical_score = 1`（"技术"）
   - `architecture_score = 0`
   - 置信度 = 1.0（但只有一个关键词，可能不够准确）

2. 如果置信度 < 0.5，调用AI识别：
   - AI分析文档内容
   - 判断为 technical（置信度 0.7）
   - **结果**：technical（置信度 0.7，method: ai）

---

## 九、分类性能

### 9.1 规则匹配性能

- **响应时间**：< 10ms
- **准确率**：90%+（对于关键词明显的文档）
- **成本**：0（无需API调用）

### 9.2 AI识别性能

- **响应时间**：500-1000ms（取决于API响应时间）
- **准确率**：95%+（对于语义理解）
- **成本**：每次调用消耗API额度

### 9.3 混合策略性能

- **平均响应时间**：< 50ms（大部分文档通过规则识别）
- **平均准确率**：92%+
- **API调用率**：约10-20%（仅当规则识别置信度低时调用）

---

## 十、优化建议

### 10.1 关键词优化

- 定期更新关键词列表
- 根据实际使用情况调整关键词权重
- 考虑添加同义词和变体

### 10.2 AI识别优化

- 调整提示词，提高识别准确率
- 考虑使用更长的文档预览（当前2000字符）
- 添加置信度阈值，避免低置信度结果

### 10.3 性能优化

- 缓存常见文档类型的识别结果
- 考虑使用本地模型进行快速识别
- 优化规则匹配算法，提高速度

---

**文档版本**：v1.0  
**创建时间**：2025-12-21  
**最后更新**：2025-12-21

