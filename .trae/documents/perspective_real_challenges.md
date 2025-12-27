# 基于视角的文档分类系统 - 真实难点与解决方案

## 一、真实难点概述

本次重构面临4个真实难点，这些是架构设计的核心挑战，需要在技术方案中明确解决。

---

## 难点1：多视角独立性

### 问题描述

**不再假设"一次处理只有一个真结果"**，一个view的生成/更新，不能影响其他view的稳定性。

### 核心挑战

- 多个view可能同时处理，需要保证独立性
- 一个view失败不应影响其他view
- 一个view更新不应影响其他view的稳定性
- 需要支持view的增量更新

### 解决方案

#### 1.1 独立存储策略

```python
# 每个view独立存储，互不影响
class ProcessingResult(Base):
    __tablename__ = "processing_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"))
    view = Column(String(50), nullable=False)  # learning/qa/system
    result_data = Column(JSONB, nullable=False)  # 该view的结果（独立存储）
    processing_time = Column(Integer, nullable=True)
    is_primary = Column(Boolean, default=False)  # 是否为主视角
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)
    
    # 唯一约束：一个文档的同一个view只能有一条记录
    __table_args__ = (
        UniqueConstraint('document_id', 'view', name='uq_processing_result_document_view'),
    )
```

#### 1.2 独立处理任务

```python
# 每个view使用独立的处理任务，避免相互干扰
async def process_view_independently(
    document_id: str,
    view: str,
    intermediate_results: DocumentIntermediateResult,
    db: AsyncSession
):
    """
    独立处理单个view，不影响其他view
    
    关键点：
    - 使用独立的数据库事务
    - 失败不影响其他view
    - 成功立即提交，确保稳定性
    """
    try:
        processor = ViewRegistry.get_processor(view)
        result_data = await processor.process(
            content=intermediate_results.preprocessed_content,
            segments=intermediate_results.segments,
            # 其他参数...
        )
        
        # 独立保存该view的结果
        view_result = ProcessingResult(
            document_id=document_id,
            view=view,
            result_data=result_data,
            is_primary=(view == primary_view)
        )
        db.add(view_result)
        await db.commit()  # 立即提交，确保该view结果稳定
        
        return result_data
        
    except Exception as e:
        logger.error(f"View处理失败: {view}", 
                    document_id=document_id, 
                    error=str(e))
        # 失败不影响其他view，继续处理
        return None
```

#### 1.3 增量更新机制

```python
# 支持view的增量更新，不影响其他view
async def update_view_result(
    document_id: str,
    view: str,
    new_result: Dict,
    db: AsyncSession
):
    """
    更新单个view的结果，不影响其他view
    
    关键点：
    - 只更新指定view的结果
    - 不影响容器中其他view
    - 更新后立即提交
    """
    # 查询现有结果
    existing = await db.execute(
        select(ProcessingResult)
        .where(ProcessingResult.document_id == document_id)
        .where(ProcessingResult.view == view)
    )
    result = existing.scalar_one_or_none()
    
    if result:
        # 更新现有结果（只更新该view）
        result.result_data = new_result
        result.updated_at = datetime.now()
    else:
        # 创建新结果
        result = ProcessingResult(
            document_id=document_id,
            view=view,
            result_data=new_result
        )
        db.add(result)
    
    await db.commit()  # 立即提交，确保更新稳定
    
    # 更新容器meta（不影响其他view的数据）
    await update_container_meta(document_id, db)
```

---

## 难点2：特征强弱作为决策依据

### 问题描述

把"文档特征强弱"变成UI和算力分配的决策依据，**主视角 ≠ 用户最终视角**，系统推荐不应该参与缓存key，**系统检测才是算力与存储的边界**。

### 核心挑战

- 主视角用于UI初始状态和算力分配，但不应该影响存储
- 缓存key应该基于系统检测的特征得分，不基于推荐结果
- 用户可以选择任意视角，不受主视角限制
- 系统检测的特征得分是算力与存储的边界

### 解决方案

#### 2.1 缓存key生成策略

```python
def generate_cache_key(
    document_id: str,
    detection_scores: Dict[str, float]
) -> str:
    """
    生成缓存key（基于系统检测的特征得分，不基于推荐结果）
    
    关键点：
    - 缓存key基于系统检测的原始得分
    - 不包含推荐结果（主视角、次视角等）
    - 系统检测才是算力与存储的边界
    """
    # 基于特征得分生成key（不包含推荐逻辑）
    score_hash = hashlib.md5(
        json.dumps(detection_scores, sort_keys=True).encode()
    ).hexdigest()
    
    return f"doc:{document_id}:scores:{score_hash}"

# 示例
detection_scores = {
    'qa': 0.75,
    'system': 0.65,
    'learning': 0.85
}
cache_key = generate_cache_key(document_id, detection_scores)
# 结果：doc:xxx:scores:abc123...
# 注意：不包含primary_view、enabled_views等推荐结果
```

#### 2.2 主视角用于UI和算力分配

```python
async def recommend_views(
    content: str,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None
) -> Dict[str, Any]:
    """
    推荐处理视角
    
    关键点：
    - 主视角用于UI初始状态和算力分配
    - 不用于存储决策
    - 用户可以选择任意视角
    """
    # 1. 系统检测特征得分（这是算力与存储的边界）
    detection_scores = {
        'qa': detect_qa_structure(content),
        'system': detect_component_relationships(content),
        'learning': detect_usage_flow(content)
    }
    
    # 2. 生成缓存key（基于检测得分，不基于推荐）
    cache_key = generate_cache_key(document_id, detection_scores)
    
    # 3. 推荐主视角（用于UI和算力分配，不影响存储）
    primary_view = max(detection_scores, key=detection_scores.get)
    enabled_views = [
        view for view, score in detection_scores.items()
        if score >= 0.3
    ]
    
    return {
        'primary_view': primary_view,  # 用于UI初始状态
        'enabled_views': enabled_views,  # 用于算力分配
        'detection_scores': detection_scores,  # 系统检测的原始得分
        'cache_key': cache_key,  # 基于检测得分，不基于推荐
        'method': 'rule|ai|hybrid'
    }
```

#### 2.3 用户视角选择不受主视角限制

```python
@router.get("/{document_id}/result")
async def get_document_result(
    document_id: str,
    view: Optional[str] = Query(None, description="用户选择的视角"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取文档处理结果
    
    关键点：
    - 用户可以选择任意视角，不受主视角限制
    - 主视角只是推荐，不是限制
    """
    # 用户选择的视角（可能不是主视角）
    requested_view = view or get_default_view(document_id, db)
    
    # 查询或生成该view的结果
    result = await get_or_generate_view_result(
        document_id=document_id,
        view=requested_view,  # 用户选择的视角
        db=db
    )
    
    return {
        'document_id': document_id,
        'view': requested_view,  # 用户最终视角（可能不是主视角）
        'result': result
    }
```

---

## 难点3：中间结果视角无关

### 问题描述

**切换视角 ≠ 重新理解世界**，切换视角 = 对同一理解的再组织，**中间结果必须是视角无关的**。

### 核心挑战

- 中间结果不能包含任何视角相关的信息
- 所有视角共享同一份中间结果
- 切换视角时复用中间结果，仅重新组织AI处理

### 解决方案

#### 3.1 中间结果存储（视角无关）

```python
class DocumentIntermediateResult(Base):
    """文档中间结果表（视角无关）"""
    __tablename__ = "document_intermediate_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), unique=True)
    
    # 视角无关的中间结果
    content = Column(Text, nullable=False)  # 原始内容（视角无关）
    preprocessed_content = Column(Text, nullable=True)  # 预处理后内容（视角无关）
    segments = Column(JSONB, nullable=True)  # 段落切分结果（视角无关）
    metadata = Column(JSONB, nullable=True)  # 元数据（视角无关）
    
    # 注意：不包含任何视角相关的处理结果
    # 视角相关的处理结果存储在 processing_results 表中
    
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)
```

#### 3.2 切换视角逻辑（复用中间结果）

```python
async def switch_view(
    document_id: str,
    target_view: str,
    db: AsyncSession
) -> Dict:
    """
    切换视角（对同一理解的再组织）
    
    关键点：
    - 切换视角 ≠ 重新理解世界
    - 切换视角 = 对同一理解的再组织
    - 复用视角无关的中间结果
    """
    # 1. 获取视角无关的中间结果
    intermediate = await get_intermediate_results(document_id, db)
    
    if not intermediate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="中间结果不存在，需要重新处理文档"
        )
    
    # 2. 复用中间结果（视角无关）
    content = intermediate.preprocessed_content or intermediate.content
    segments = intermediate.segments or []
    
    # 3. 仅重新组织AI处理（根据新视角）
    processor = ViewRegistry.get_processor(target_view)
    result_data = await processor.process(
        content=content,  # 复用视角无关的内容
        segments=segments,  # 复用视角无关的段落
        # 其他参数...
    )
    
    # 4. 保存新视角的结果（不影响中间结果）
    view_result = ProcessingResult(
        document_id=document_id,
        view=target_view,
        result_data=result_data
    )
    db.add(view_result)
    await db.commit()
    
    return {
        'view': target_view,
        'result': result_data,
        'used_intermediate_results': True  # 标记使用了中间结果
    }
```

---

## 难点4：主次视角优先级

### 问题描述

**LLM 并行 ≠ 用户价值并行**，Primary View：必须快、稳定、可预测，Secondary View：可以慢、可以异步、可以后补。UI层是：主视角先出结果，次视角显示「正在生成…」。

### 核心挑战

- Primary View必须优先保证，快速返回
- Secondary View可以异步处理，不影响主视角
- UI层需要区分主次视角的显示状态
- 需要支持主视角先显示，次视角后补

### 解决方案

#### 4.1 主次视角处理策略

```python
async def process_views_with_priority(
    document_id: str,
    primary_view: str,
    secondary_views: List[str],
    intermediate_results: DocumentIntermediateResult,
    db: AsyncSession
) -> Dict:
    """
    处理多个视角（主次视角优先级策略）
    
    关键点：
    - Primary View：同步处理，优先保证，快速返回
    - Secondary View：异步处理，可以后补，不影响主视角
    """
    results = {}
    processing_status = {}
    
    # 1. 优先处理主视角（同步，必须快速返回）
    primary_start = datetime.now()
    try:
        primary_processor = ViewRegistry.get_processor(primary_view)
        primary_result = await primary_processor.process(
            content=intermediate_results.preprocessed_content,
            segments=intermediate_results.segments,
            # 其他参数...
        )
        primary_time = (datetime.now() - primary_start).total_seconds()
        
        # 立即保存主视角结果
        await save_view_result(
            document_id=document_id,
            view=primary_view,
            result=primary_result,
            is_primary=True,
            db=db
        )
        
        results[primary_view] = primary_result
        processing_status[primary_view] = {
            'status': 'completed',
            'processing_time': primary_time,
            'ready': True
        }
        
        logger.info("主视角处理完成", 
                  document_id=document_id,
                  view=primary_view,
                  time=primary_time)
        
    except Exception as e:
        logger.error(f"主视角处理失败: {primary_view}", 
                    document_id=document_id, 
                    error=str(e))
        processing_status[primary_view] = {
            'status': 'failed',
            'error': str(e),
            'ready': False
        }
    
    # 2. 异步处理次视角（可以慢、可以后补）
    async def process_secondary_view(view: str):
        """异步处理次视角"""
        try:
            start_time = datetime.now()
            processor = ViewRegistry.get_processor(view)
            result = await processor.process(
                content=intermediate_results.preprocessed_content,
                segments=intermediate_results.segments,
                # 其他参数...
            )
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # 保存次视角结果
            await save_view_result(
                document_id=document_id,
                view=view,
                result=result,
                is_primary=False,
                db=db
            )
            
            return {
                'view': view,
                'result': result,
                'status': 'completed',
                'processing_time': processing_time,
                'ready': True
            }
            
        except Exception as e:
            logger.error(f"次视角处理失败: {view}", 
                        document_id=document_id, 
                        error=str(e))
            return {
                'view': view,
                'status': 'failed',
                'error': str(e),
                'ready': False
            }
    
    # 并行处理次视角（不影响主视角）
    if secondary_views:
        secondary_tasks = [
            process_secondary_view(view) 
            for view in secondary_views
        ]
        secondary_results = await asyncio.gather(
            *secondary_tasks, 
            return_exceptions=True
        )
        
        for result in secondary_results:
            if result and not isinstance(result, Exception):
                results[result['view']] = result.get('result')
                processing_status[result['view']] = {
                    'status': result['status'],
                    'processing_time': result.get('processing_time'),
                    'ready': result.get('ready', False)
                }
    
    # 3. 返回处理结果（包含状态信息）
    return {
        'document_id': document_id,
        'results': results,
        'processing_status': processing_status,
        'primary_view': primary_view,
        'primary_view_ready': processing_status.get(primary_view, {}).get('ready', False),
        'secondary_views_ready': [
            view for view, status in processing_status.items()
            if view != primary_view and status.get('ready', False)
        ]
    }
```

#### 4.2 UI层状态管理

```typescript
// 前端状态管理
interface ViewProcessingStatus {
  view: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  result?: any
  error?: string
}

const ResultPage = () => {
  const [primaryView, setPrimaryView] = useState<string>('')
  const [viewStatuses, setViewStatuses] = useState<Map<string, ViewProcessingStatus>>(new Map())
  
  useEffect(() => {
    // 1. 获取主视角结果（优先显示）
    fetchPrimaryViewResult().then(result => {
      setPrimaryView(result.view)
      setViewStatuses(prev => {
        const next = new Map(prev)
        next.set(result.view, {
          view: result.view,
          status: 'completed',
          result: result.result
        })
        return next
      })
    })
    
    // 2. 轮询次视角状态（显示"正在生成..."）
    const interval = setInterval(() => {
      fetchViewStatuses().then(statuses => {
        setViewStatuses(prev => {
          const next = new Map(prev)
          statuses.forEach(status => {
            if (status.view !== primaryView) {
              next.set(status.view, status)
            }
          })
          return next
        })
      })
    }, 2000)  // 每2秒轮询一次
    
    return () => clearInterval(interval)
  }, [primaryView])
  
  return (
    <div>
      {/* 主视角：立即显示结果 */}
      {primaryView && viewStatuses.get(primaryView)?.status === 'completed' && (
        <ViewResult 
          view={primaryView} 
          result={viewStatuses.get(primaryView)?.result} 
        />
      )}
      
      {/* 次视角：显示"正在生成..." */}
      {secondaryViews.map(view => {
        const status = viewStatuses.get(view)
        if (status?.status === 'processing' || status?.status === 'pending') {
          return (
            <div key={view}>
              <ViewPlaceholder view={view} message="正在生成..." />
            </div>
          )
        } else if (status?.status === 'completed') {
          return (
            <ViewResult key={view} view={view} result={status.result} />
          )
        }
        return null
      })}
    </div>
  )
}
```

#### 4.3 API状态接口

```python
@router.get("/{document_id}/views/status")
async def get_views_status(
    document_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    获取各视角的处理状态
    
    用于UI层轮询，显示"正在生成..."状态
    """
    # 查询所有view的处理状态
    results = await db.execute(
        select(ProcessingResult)
        .where(ProcessingResult.document_id == document_id)
    )
    view_results = results.scalars().all()
    
    statuses = {}
    for result in view_results:
        statuses[result.view] = {
            'view': result.view,
            'status': 'completed',
            'ready': True,
            'processing_time': result.processing_time
        }
    
    # 查询推荐信息，确定哪些view应该存在
    doc_type = await get_document_type(document_id, db)
    enabled_views = doc_type.enabled_views or []
    
    # 标记未完成的view
    for view in enabled_views:
        if view not in statuses:
            statuses[view] = {
                'view': view,
                'status': 'processing',  # 或 'pending'
                'ready': False
            }
    
    return {
        'document_id': document_id,
        'views_status': statuses,
        'primary_view': doc_type.primary_view,
        'enabled_views': enabled_views
    }
```

---

## 五、综合解决方案

### 5.1 数据库设计

```python
# 1. 中间结果表（视角无关）
class DocumentIntermediateResult(Base):
    """视角无关的中间结果"""
    document_id = Column(UUID, unique=True)
    content = Column(Text)  # 视角无关
    preprocessed_content = Column(Text)  # 视角无关
    segments = Column(JSONB)  # 视角无关
    metadata = Column(JSONB)  # 视角无关

# 2. 处理结果表（每个view独立存储）
class ProcessingResult(Base):
    """每个view的处理结果（独立存储）"""
    document_id = Column(UUID)
    view = Column(String(50))  # learning/qa/system
    result_data = Column(JSONB)  # 该view的结果
    is_primary = Column(Boolean)  # 是否为主视角
    processing_time = Column(Integer)
    
    # 唯一约束：一个文档的同一个view只能有一条记录
    __table_args__ = (
        UniqueConstraint('document_id', 'view', name='uq_result_doc_view'),
    )
```

### 5.2 处理流程

```python
async def process_document_with_views(
    document_id: str,
    enabled_views: List[str],
    primary_view: str,
    db: AsyncSession
):
    """
    处理文档（主次视角优先级策略）
    
    流程：
    1. 保存视角无关的中间结果
    2. 优先处理主视角（同步，快速返回）
    3. 异步处理次视角（可以慢、可以后补）
    4. 每个view独立存储，互不影响
    """
    # 1. 提取和预处理（视角无关）
    intermediate = await extract_and_preprocess(document_id, db)
    
    # 2. 保存中间结果（视角无关）
    await save_intermediate_results(document_id, intermediate, db)
    
    # 3. 处理主视角（同步，优先保证）
    primary_result = await process_view(
        document_id=document_id,
        view=primary_view,
        intermediate=intermediate,
        db=db
    )
    await save_view_result(
        document_id=document_id,
        view=primary_view,
        result=primary_result,
        is_primary=True,
        db=db
    )
    
    # 4. 异步处理次视角（可以慢、可以后补）
    secondary_views = [v for v in enabled_views if v != primary_view]
    if secondary_views:
        asyncio.create_task(
            process_secondary_views_async(
                document_id=document_id,
                views=secondary_views,
                intermediate=intermediate,
                db=db
            )
        )
    
    # 5. 立即返回主视角结果
    return {
        'document_id': document_id,
        'primary_view': primary_view,
        'primary_result': primary_result,
        'primary_ready': True,
        'secondary_views': secondary_views,
        'secondary_ready': False  # 次视角还在处理中
    }
```

### 5.3 缓存策略

```python
def get_cache_key(document_id: str, detection_scores: Dict) -> str:
    """
    生成缓存key（基于系统检测，不基于推荐）
    
    关键点：
    - 缓存key基于系统检测的特征得分
    - 不包含推荐结果（主视角、次视角等）
    - 系统检测才是算力与存储的边界
    """
    # 基于检测得分生成key
    score_str = json.dumps(detection_scores, sort_keys=True)
    score_hash = hashlib.md5(score_str.encode()).hexdigest()
    return f"doc:{document_id}:detection:{score_hash}"

# 使用示例
detection_scores = {
    'learning': 0.85,
    'system': 0.65,
    'qa': 0.15
}
cache_key = get_cache_key(document_id, detection_scores)
# 结果：doc:xxx:detection:abc123...
# 注意：不包含primary_view、enabled_views等推荐结果
```

---

## 六、实施要点

### 6.1 难点1：多视角独立性
- ✅ 每个view独立存储（UniqueConstraint on document_id + view）
- ✅ 独立处理任务，失败不影响其他view
- ✅ 增量更新机制，只更新指定view

### 6.2 难点2：特征强弱作为决策依据
- ✅ 缓存key基于系统检测的特征得分
- ✅ 主视角用于UI和算力分配，不影响存储
- ✅ 用户可以选择任意视角，不受主视角限制

### 6.3 难点3：中间结果视角无关
- ✅ 中间结果不包含任何视角相关信息
- ✅ 所有视角共享同一份中间结果
- ✅ 切换视角时复用中间结果，仅重新组织AI处理

### 6.4 难点4：主次视角优先级
- ✅ Primary View：同步处理，优先保证，快速返回
- ✅ Secondary View：异步处理，可以后补，不影响主视角
- ✅ UI层：主视角先显示结果，次视角显示"正在生成..."

---

**文档版本**：v1.0  
**创建时间**：2025-12-21  
**核心价值**：解决4个真实难点，确保架构设计的正确性和可实施性

