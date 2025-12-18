# 技术方案设计 - 可信度估计与来源片段引用

## 一、架构设计

### 1.1 整体架构（更新）

```
文档处理流程
├── 文档内容提取
├── 文本预处理（新增）
│   ├── 格式统一
│   ├── 文本清洗
│   └── 噪声过滤
├── 文档段落切分（新增）
│   └── 生成段落索引和片段映射
├── 文档类型识别
├── AI处理（增强）
│   ├── 传入段落索引
│   ├── 要求返回source_ids
│   └── 要求返回confidence
├── 可信度计算（新增）
│   ├── 基础可信度（AI返回）
│   ├── 加权因子计算
│   └── 最终可信度分数
└── 结果存储（增强）
    ├── 可信度信息
    └── 来源片段信息
```

### 1.2 核心组件

1. **文本预处理服务** (`TextPreprocessor`) - 新增
   - 格式统一（换行符、空格、制表符、编码）
   - 文本清洗（不可见字符、编码错误、标点符号）
   - 噪声过滤（页眉页脚、重复内容、无意义短行）

2. **段落切分服务** (`SourceSegmenter`)
   - 负责将文档内容按段落切分
   - 生成段落索引和映射关系

3. **可信度计算服务** (`ConfidenceCalculator`)
   - 计算基础可信度
   - 应用加权因子
   - 生成最终可信度分数和标签

4. **AI服务增强** (`AIService`)
   - 支持传入段落索引
   - 要求AI返回source_ids和confidence

5. **处理器增强** (`XXXProcessor`)
   - 集成文本预处理
   - 集成段落切分
   - 集成可信度计算
   - 更新prompt要求返回来源和可信度

## 二、技术选型

### 2.1 段落切分算法

- **主粒度**：按空行和Markdown block切分
- **超长段落处理**：使用滑动窗口找到最强连续子段
- **实现方式**：Python正则表达式 + 文本分析

### 2.2 可信度计算

- **基础分数**：AI返回的confidence（0-100）
- **加权因子**：
  - 检索命中强度（0.3权重）
  - top-k相似度（0.2权重）
  - 来源集中度（0.2权重）
  - 内容一致性（0.3权重）
- **降分规则**：
  - 超出文档内容：-20分
  - 不存在概念：-15分
  - 自相矛盾：-10分
  - 结果不稳定：-10分

### 2.3 数据存储

- **存储位置**：`ProcessingResult.result_data` (JSON)
- **数据结构**：
```json
{
  "prerequisites": {
    "required": [...],
    "confidence": 85,
    "confidence_label": "高",
    "sources": [
      {
        "id": 1,
        "text": "原文片段...",
        "position": 0
      }
    ]
  }
}
```

## 三、数据库设计

### 3.1 无需新增表

- 所有信息存储在现有的 `ProcessingResult.result_data` JSON字段中
- 保持向后兼容，不影响现有数据

## 四、接口设计

### 4.1 后端接口

- **无需新增接口**
- 现有接口 `GET /api/v1/documents/{document_id}/result` 返回增强后的数据

### 4.2 前端接口

- **无需修改API调用**
- 前端组件需要适配新的数据结构

## 五、实现细节

### 5.1 段落切分实现

```python
class SourceSegmenter:
    @staticmethod
    def segment_content(content: str) -> List[Dict]:
        """
        切分文档内容为段落
        
        Returns:
            [
                {
                    "id": 1,
                    "text": "段落内容",
                    "position": 0,
                    "length": 100
                },
                ...
            ]
        """
        # 1. 按空行切分
        # 2. 识别Markdown block
        # 3. 处理超长段落（滑动窗口找最强子段）
        pass
```

### 5.2 可信度计算实现

```python
class ConfidenceCalculator:
    @staticmethod
    def calculate_confidence(
        base_confidence: float,
        source_ids: List[int],
        segments: List[Dict],
        similarity_scores: List[float],
        content: str,
        ai_response: str
    ) -> Dict:
        """
        计算最终可信度
        
        Returns:
            {
                "score": 85,
                "label": "高",
                "factors": {
                    "base": 80,
                    "retrieval_strength": 0.9,
                    "similarity": 0.85,
                    "concentration": 0.8,
                    "consistency": 0.9
                }
            }
        """
        pass
```

### 5.3 AI Prompt增强

在现有prompt基础上增加：
1. 段落索引信息
2. 要求返回source_ids
3. 要求返回confidence

示例：
```
文档内容已按段落编号：
[段落1] 内容...
[段落2] 内容...

请分析并返回JSON，每个结论包含：
- source_ids: [1, 2, 3]  // 引用的段落编号
- confidence: 85  // 可信度分数(0-100)
```

### 5.4 文档大小控制实现

```python
class DocumentSizeValidator:
    """文档大小验证器"""
    
    # 阈值定义
    FILE_SIZE_WARNING = 20 * 1024 * 1024  # 20MB
    FILE_SIZE_MAX = 30 * 1024 * 1024      # 30MB
    CONTENT_LENGTH_WARNING = 300000       # 30万字符
    CONTENT_LENGTH_MAX = 500000           # 50万字符
    PROCESS_TIME_WARNING = 240            # 240秒
    PROCESS_TIME_MAX = 300                # 300秒
    
    @staticmethod
    def estimate_processing_time(content_length: int, doc_type: str) -> int:
        """估算处理时间（秒）"""
        base_time = 30
        content_factor = (content_length / 10000) * 10
        type_factor = {
            "technical": 1.0,
            "interview": 0.8,
            "architecture": 1.2
        }
        return int(base_time + (content_factor * type_factor.get(doc_type, 1.0)))
    
    @staticmethod
    def validate_file_size(file_size: int) -> Dict:
        """验证文件大小"""
        if file_size > DocumentSizeValidator.FILE_SIZE_MAX:
            raise ValueError(
                f"文件大小超过限制: {file_size / 1024 / 1024:.2f}MB > "
                f"{DocumentSizeValidator.FILE_SIZE_MAX / 1024 / 1024}MB"
            )
        
        warnings = []
        if file_size > DocumentSizeValidator.FILE_SIZE_WARNING:
            warnings.append(
                f"文件较大 ({file_size / 1024 / 1024:.2f}MB)，处理时间可能较长"
            )
        
        return {"valid": True, "warnings": warnings}
    
    @staticmethod
    def validate_content_length(content_length: int, doc_type: str = "technical") -> Dict:
        """验证内容长度和处理时间"""
        # 内容长度检查
        if content_length > DocumentSizeValidator.CONTENT_LENGTH_MAX:
            raise ValueError(
                f"文档内容过长: {content_length} 字符，超过限制 "
                f"{DocumentSizeValidator.CONTENT_LENGTH_MAX} 字符。"
                "建议拆分后处理。"
            )
        
        # 处理时间估算
        estimated_time = DocumentSizeValidator.estimate_processing_time(
            content_length, doc_type
        )
        
        if estimated_time > DocumentSizeValidator.PROCESS_TIME_MAX:
            raise ValueError(
                f"文档过大，预计处理时间 {estimated_time} 秒，"
                f"超过最大限制 {DocumentSizeValidator.PROCESS_TIME_MAX} 秒。"
                "建议拆分后处理。"
            )
        
        warnings = []
        if content_length > DocumentSizeValidator.CONTENT_LENGTH_WARNING:
            warnings.append(
                f"文档内容较长 ({content_length} 字符)，处理时间可能较长"
            )
        if estimated_time > DocumentSizeValidator.PROCESS_TIME_WARNING:
            warnings.append(
                f"预计处理时间约 {estimated_time} 秒，请耐心等待"
            )
        
        return {
            "valid": True,
            "estimated_time": estimated_time,
            "warnings": warnings
        }
```

## 六、测试策略

### 6.1 单元测试

- 段落切分算法测试
- 可信度计算测试
- 加权因子计算测试

### 6.2 集成测试

- 完整处理流程测试
- 不同文档类型测试
- 边界情况测试（超长段落、无来源等）

### 6.3 端到端测试

- 前端展示测试
- 可信度标签显示测试
- 来源片段展示测试

## 七、异常处理与兜底逻辑

### 7.1 段落切分异常处理

**异常场景**：
- 文档内容为空
- 切分算法失败
- 超长段落处理失败

**兜底策略**：
```python
def segment_content(content: str) -> List[Dict]:
    try:
        # 正常切分逻辑
        return normal_segment(content)
    except Exception as e:
        logger.warning("段落切分失败，使用兜底策略", error=str(e))
        # 兜底：按固定长度切分（每500字符一段）
        return fallback_segment(content, chunk_size=500)
```

### 7.2 AI返回格式异常处理

**异常场景**：
- JSON格式不正确
- 缺少source_ids字段
- 缺少confidence字段
- source_ids超出范围
- confidence超出范围

**兜底策略**：
```python
def parse_ai_response(response: str, segments: List[Dict]) -> Dict:
    try:
        result = json.loads(response)
    except:
        # 尝试提取JSON
        result = extract_json_from_text(response)
    
    # 验证和修正
    if "source_ids" not in result:
        result["source_ids"] = []
    else:
        # 过滤无效ID
        max_id = len(segments)
        result["source_ids"] = [id for id in result["source_ids"] 
                                if 1 <= id <= max_id]
    
    if "confidence" not in result:
        result["confidence"] = 50  # 默认中等可信度
    else:
        # 修正范围
        result["confidence"] = max(0, min(100, result["confidence"]))
    
    return result
```

### 7.3 可信度计算异常处理

**异常场景**：
- 相似度计算失败
- 来源集中度计算失败
- 内容一致性检查失败
- 计算超时

**兜底策略**：
```python
def calculate_confidence(...) -> Dict:
    try:
        # 正常计算流程
        factors = {
            "retrieval_strength": calculate_retrieval_strength(...),
            "similarity": calculate_similarity(...),
            "concentration": calculate_concentration(...),
            "consistency": check_consistency(...)
        }
    except Exception as e:
        logger.warning("可信度计算异常，使用基础分数", error=str(e))
        # 兜底：使用AI返回的基础可信度
        return {
            "score": base_confidence,
            "label": get_confidence_label(base_confidence),
            "factors": {"base": base_confidence}
        }
```

### 7.4 性能异常处理

**异常场景**：
- 段落切分耗时过长（>5秒）
- 可信度计算耗时过长（>3秒）
- 处理超时风险

**兜底策略**：
```python
import asyncio

async def segment_with_timeout(content: str, timeout=5):
    try:
        return await asyncio.wait_for(
            segment_content(content),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        logger.warning("段落切分超时，使用快速模式")
        return fast_segment(content)  # 简化切分
```

### 7.5 前端展示异常处理

**异常场景**：
- 缺少可信度信息
- 缺少来源片段信息
- 来源片段ID无效
- 可信度标签无法解析

**兜底策略**：
```typescript
// 前端组件
function renderConfidence(confidence?: number, label?: string) {
  if (!confidence && !label) {
    return null; // 不显示，不报错
  }
  
  const displayLabel = label || getLabelFromScore(confidence || 50);
  return <ConfidenceBadge label={displayLabel} />;
}

function renderSources(sources?: Array<{id: number, text: string}>) {
  if (!sources || sources.length === 0) {
    return null; // 不显示，不报错
  }
  
  // 过滤无效片段
  const validSources = sources.filter(s => s.id && s.text);
  return <SourceList sources={validSources} />;
}
```

### 7.6 日志和监控

**日志策略**：
- 所有异常记录ERROR级别日志
- 使用兜底逻辑记录WARNING级别日志
- 包含完整的上下文信息（document_id, task_id等）

**监控指标**：
- 异常频率统计
- 兜底逻辑使用频率
- 性能指标（切分耗时、计算耗时）

## 八、安全性

### 8.1 数据验证

- 验证source_ids有效性
- 验证confidence范围（0-100）
- 防止XSS攻击（前端转义）
- 输入内容长度限制

### 8.2 性能优化

- 段落切分缓存
- 相似度计算优化
- 批量处理优化
- 超时保护机制

## 九、向后兼容

### 9.1 数据兼容

- 旧数据不包含可信度和来源信息，前端需要兼容处理
- 新数据包含完整信息，前端优先展示
- 兜底逻辑确保旧数据正常显示

### 9.2 API兼容

- 现有API接口保持不变
- 返回数据结构向后兼容（新增字段可选）
- 异常情况下返回默认值，不破坏现有结构

## 十、失败策略设计

### 10.1 失败状态定义

系统定义以下明确的失败状态：

1. **failed** - 处理失败
   - AI调用失败
   - 文档无法提取
   - 结果格式无法解析
   - 关键步骤失败

2. **timeout** - 处理超时
   - 超过最大处理时间（默认300秒）
   - 单个步骤超时

3. **low_quality** - 结果质量过低
   - 可信度<20且无有效来源
   - 结果明显不合理

4. **unknown** - 无法确定类型
   - 文档类型识别失败
   - 置信度过低

### 10.2 失败处理流程

```
处理流程
├── 步骤0: 文档大小验证（上传阶段）
│   ├── 文件大小检查 → 超过30MB拒绝
│   ├── 内容提取
│   ├── 内容长度检查 → 超过50万字符拒绝
│   ├── 处理时间估算 → 超过300秒拒绝
│   └── 验证通过 → 继续
├── 步骤1: 内容提取
│   ├── 成功 → 继续
│   └── 失败 → 标记failed，停止处理，返回错误信息
├── 步骤1.5: 文本预处理（新增）
│   ├── 格式统一 → 统一换行符、空格、制表符、编码
│   ├── 文本清洗 → 去除不可见字符、修复编码错误
│   ├── 噪声过滤 → 去除页眉页脚、重复内容、无意义短行
│   ├── 成功 → 继续（使用清洗后的内容）
│   └── 失败 → 使用原始内容继续，记录警告日志
├── 步骤2: 类型识别
│   ├── 成功 → 继续
│   └── 失败 → 标记unknown，继续处理（使用默认类型）
├── 步骤3: AI处理
│   ├── 成功 → 继续
│   ├── 超时 → 标记timeout，停止处理，返回超时信息
│   └── 失败 → 标记failed，停止处理，返回错误信息
└── 步骤4: 结果验证
    ├── 有效 → 保存结果
    ├── 质量过低 → 标记low_quality，保存结果并提示
    └── 无效 → 标记failed，不保存结果，返回错误信息
```

### 10.3 错误信息结构

```python
class ProcessingException(Exception):
    """处理异常类"""
    def __init__(
        self,
        status: str,  # "failed" | "timeout" | "low_quality"
        error_type: str,  # "ai_call_failed" | "timeout" | "invalid_file" | "parse_error"
        error_message: str,
        error_details: Dict,
        user_actions: List[Dict]
    ):
        self.status = status
        self.error_type = error_type
        self.error_message = error_message
        self.error_details = error_details
        self.user_actions = user_actions

# 错误信息结构
{
    "status": "failed",
    "error_type": "ai_call_failed",
    "error_message": "AI服务调用失败：网络连接超时",
    "error_details": {
        "step": "AI处理",
        "reason": "网络连接超时",
        "completed_steps": ["提取内容", "类型识别"],
        "failed_step": "AI处理"
    },
    "user_actions": [
        {
            "action": "retry",
            "label": "重试处理",
            "description": "重新处理当前文档"
        },
        {
            "action": "check_config",
            "label": "检查配置",
            "description": "请检查API密钥配置和网络连接"
        }
    ]
}
```

### 10.4 防止"胡乱返回"机制

**关键原则**：
1. **立即停止**：关键步骤失败时立即停止，不继续处理
2. **明确状态**：使用明确的失败状态，不使用模糊的"completed"状态
3. **不填充猜测值**：关键数据缺失时不使用默认值填充
4. **结果验证**：保存前验证结果有效性，无效结果不保存
5. **质量检查**：结果质量过低时明确标记，不隐藏问题

**实现示例**：
```python
# ❌ 错误示例：胡乱返回
if ai_result is None:
    result = {"prerequisites": []}  # 不应该返回空结果
    return result

# ✅ 正确示例：明确失败
if ai_result is None:
    raise ProcessingException(
        status="failed",
        error_type="ai_call_failed",
        error_message="AI服务调用失败",
        error_details={
            "step": "AI处理",
            "reason": "AI返回结果为空"
        },
        user_actions=[
            {"action": "retry", "label": "重试处理"}
        ]
    )
```

### 10.5 文档大小控制策略

**控制层级**：

1. **上传阶段控制**
   - 文件大小限制：30MB（硬限制）
   - 内容长度估算：提取后根据字符数估算
   - 处理时间估算：基于内容长度和文档类型

2. **处理时间估算公式**
   ```python
   # 基础处理时间（秒）
   base_time = 30
   
   # 内容长度因子（每1万字符约增加10秒）
   content_factor = (content_length / 10000) * 10
   
   # 文档类型因子
   type_factor = {
       "technical": 1.0,
       "interview": 0.8,
       "architecture": 1.2
   }
   
   # 估算处理时间
   estimated_time = base_time + (content_factor * type_factor[doc_type])
   ```

3. **大小阈值定义**
   ```python
   # 文件大小阈值
   FILE_SIZE_WARNING = 20 * 1024 * 1024  # 20MB（警告）
   FILE_SIZE_MAX = 30 * 1024 * 1024      # 30MB（拒绝）
   
   # 内容长度阈值
   CONTENT_LENGTH_WARNING = 300000       # 30万字符（警告）
   CONTENT_LENGTH_MAX = 500000           # 50万字符（拒绝）
   
   # 处理时间阈值
   PROCESS_TIME_WARNING = 240             # 240秒（警告）
   PROCESS_TIME_MAX = 300                # 300秒（拒绝）
   ```

4. **控制策略**
   - **拒绝策略**：超过最大阈值，直接拒绝上传
   - **警告策略**：在警告阈值和最大阈值之间，允许上传但给出警告
   - **提前终止**：处理过程中检测到可能超时，提前终止

5. **实现示例**
   ```python
   def validate_document_size(file_size: int, content_length: int, doc_type: str) -> Dict:
       """验证文档大小和处理时间"""
       # 文件大小检查
       if file_size > FILE_SIZE_MAX:
           raise ValueError(f"文件大小超过限制: {file_size} bytes > {FILE_SIZE_MAX} bytes")
       
       # 内容长度检查
       if content_length > CONTENT_LENGTH_MAX:
           raise ValueError(f"文档内容过长: {content_length} 字符，建议拆分后处理")
       
       # 处理时间估算
       estimated_time = estimate_processing_time(content_length, doc_type)
       if estimated_time > PROCESS_TIME_MAX:
           raise ValueError(
               f"文档过大，预计处理时间 {estimated_time} 秒，超过最大限制 {PROCESS_TIME_MAX} 秒。"
               "建议拆分后处理。"
           )
       
       # 警告检查
       warnings = []
       if file_size > FILE_SIZE_WARNING:
           warnings.append("文件较大，处理时间可能较长")
       if content_length > CONTENT_LENGTH_WARNING:
           warnings.append("文档内容较长，处理时间可能较长")
       if estimated_time > PROCESS_TIME_WARNING:
           warnings.append(f"预计处理时间约 {estimated_time} 秒，请耐心等待")
       
       return {
           "valid": True,
           "estimated_time": estimated_time,
           "warnings": warnings
       }
   ```

### 10.6 用户反馈设计

**前端错误展示组件**：
```typescript
interface ErrorDisplay {
  status: "failed" | "timeout" | "low_quality";
  title: string;  // "处理失败" / "处理超时" / "结果质量较低"
  message: string;  // 明确的错误描述
  details?: string;  // 详细错误信息（可展开）
  actions: Array<{
    label: string;
    action: () => void;
    description?: string;
  }>;
}
```

**操作建议映射**：
- AI调用失败 → "请检查网络连接" / "请验证API密钥"
- 任务超时 → "文档过大，建议拆分" / "可以稍后重试"
- 文件无法解析 → "文件可能损坏" / "请检查文件格式"
- 结果质量低 → "结果可能不准确" / "建议重新处理"
- 文档过大 → "建议将文档拆分为多个小文件后分别处理"

## 十一、实施计划

### 11.1 第一阶段：核心功能

1. 实现段落切分服务
2. 实现可信度计算服务
3. 增强AI服务prompt
4. 更新技术文档处理器

### 11.2 第二阶段：扩展功能

1. 更新面试题处理器
2. 更新架构文档处理器
3. 前端技术文档展示

### 11.3 第三阶段：完善功能

1. 前端面试题/架构文档弱展示
2. 优化可信度计算算法
3. 性能优化

### 11.4 第四阶段：失败策略

1. 实现失败状态管理
2. 实现错误信息结构
3. 实现用户反馈机制
4. 前端错误展示组件

---

**文档版本**：v1.1  
**创建时间**：2025-12-12  
**最后更新**：2025-12-12

