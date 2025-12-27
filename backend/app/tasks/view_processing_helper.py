"""
视角处理辅助函数
用于主次视角优先级处理逻辑
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.services.view_registry import ViewRegistry
from app.services.intermediate_results_service import IntermediateResultsService
from app.services.multi_view_container import MultiViewOutputContainer
from app.models.processing_result import ProcessingResult
from app.models.document_type import DocumentType
from app.core.database import AsyncSessionLocal
from app.core.config import settings

logger = structlog.get_logger()


async def _save_incremental_result(
    document_id: str,
    view: str,
    partial_result: Dict,
    db: AsyncSession,
    type_mapping: str,
    is_primary: bool
):
    """
    增量保存部分结果到数据库
    
    Args:
        document_id: 文档ID
        view: 视角名称
        partial_result: 部分结果（字典）
        db: 数据库会话
        type_mapping: 文档类型映射
        is_primary: 是否为主视角
    """
    from uuid import UUID
    from sqlalchemy import select
    
    try:
        doc_uuid = UUID(document_id) if isinstance(document_id, str) else document_id
        
        # 查询或创建 ProcessingResult 记录
        result_query = await db.execute(
            select(ProcessingResult)
            .where(ProcessingResult.document_id == doc_uuid)
            .where(ProcessingResult.view == view)
        )
        existing_result = result_query.scalar_one_or_none()
        
        if existing_result:
            # 更新现有记录：合并部分结果
            current_data = existing_result.result_data or {}
            # 合并新数据到现有数据
            current_data.update(partial_result)
            existing_result.result_data = current_data
            await db.commit()
            logger.debug(
                "增量保存成功（更新）",
                document_id=document_id,
                view=view,
                new_keys=list(partial_result.keys())
            )
        else:
            # 创建新记录
            new_result = ProcessingResult(
                document_id=doc_uuid,
                view=view,
                document_type=type_mapping,
                result_data=partial_result,
                is_primary=is_primary,
                processing_time=None  # 处理中，暂时不设置
            )
            db.add(new_result)
            await db.commit()
            logger.debug(
                "增量保存成功（新建）",
                document_id=document_id,
                view=view,
                keys=list(partial_result.keys())
            )
    except Exception as e:
        logger.error(
            "增量保存失败",
            document_id=document_id,
            view=view,
            error=str(e)
        )
        await db.rollback()
        # 不抛出异常，允许继续处理


async def process_view_independently(
    document_id: str,
    view: str,
    content: str,
    segments: List[Dict],
    is_primary: bool,
    db: Optional[AsyncSession] = None,  # 改为可选，如果为None则创建新session
    progress_callback: Optional[callable] = None,
    incremental_save: bool = True,  # 是否启用增量保存
    stream_callback: Optional[callable] = None,  # 流式内容回调函数
    task_id: Optional[str] = None  # 新增：用于流式生成
) -> Optional[Dict]:
    """
    独立处理单个view，不影响其他view
    
    难点1解决方案：
    - 使用独立的数据库事务
    - 失败不影响其他view
    - 成功立即提交，确保稳定性
    
    Args:
        document_id: 文档ID
        view: 视角名称
        content: 预处理后的内容
        segments: 段落切分结果
        is_primary: 是否为主视角
        db: 数据库会话（可选，如果为None则创建新session）
        progress_callback: 进度回调函数
    
    Returns:
        处理结果，如果失败则返回None
    """
    # 如果db为None，创建新的独立session
    use_own_session = db is None
    if use_own_session:
        db = AsyncSessionLocal()
    
    try:
        # 获取处理器
        processor_class = ViewRegistry.get_processor(view)
        processor = processor_class()
        
        # 处理文档
        start_time = datetime.now()
        
        # 构建流式回调函数（如果提供task_id）
        def stream_cb(data: dict):
            """流式回调：推送内容到Redis"""
            if task_id:
                import redis
                import json
                r = redis.from_url(settings.REDIS_URL)
                stream_data = {
                    'view': view,
                    'module': data.get('module', 'unknown'),
                    'chunk': data.get('chunk', '')
                }
                r.publish(
                    f"task_progress:{task_id}",
                    json.dumps({
                        'type': 'stream',
                        'stream': stream_data
                    }, ensure_ascii=False)
                )
        
        # 如果是架构文档且需要进度回调
        type_mapping = ViewRegistry.get_type_mapping(view)
        if type_mapping == 'architecture' and progress_callback:
            result_data = await processor.process(content, progress_callback=progress_callback, stream_callback=stream_cb if task_id else None)
        else:
            result_data = await processor.process(content, stream_callback=stream_cb if task_id else None)
        
        processing_time = int((datetime.now() - start_time).total_seconds())
        
        # 验证结果数据不为空
        if not result_data:
            logger.warning(
                f"View处理结果为空: {view}",
                document_id=document_id,
                is_primary=is_primary
            )
            result_data = {}  # 使用空字典而不是None
        
        # 独立保存该view的结果
        view_result = ProcessingResult(
            document_id=document_id,
            view=view,
            document_type=type_mapping,
            result_data=result_data,  # 保持原生结构
            is_primary=is_primary,
            processing_time=processing_time
        )
        db.add(view_result)
        await db.commit()  # 立即提交，确保该view结果稳定
        
        logger.info(
            "View处理完成",
            document_id=document_id,
            view=view,
            is_primary=is_primary,
            processing_time=processing_time,
            result_keys=list(result_data.keys()) if isinstance(result_data, dict) else "non-dict"
        )
        
        return {
            'view': view,
            'result': result_data,
            'processing_time': processing_time
        }
        
    except Exception as e:
        logger.error(
            f"View处理失败: {view}",
            document_id=document_id,
            error=str(e),
            is_primary=is_primary,
            error_type=type(e).__name__
        )
        # 失败不影响其他view，继续处理
        if use_own_session:
            await db.rollback()
        else:
            try:
                await db.rollback()
            except Exception:
                pass  # 如果rollback也失败，忽略
        return None
    finally:
        # 如果使用了独立的session，关闭它
        if use_own_session:
            await db.close()


async def process_views_with_priority(
    document_id: str,
    primary_view: str,
    enabled_views: List[str],
    content: str,
    segments: List[Dict],
    detection_scores: Dict[str, float],
    db: AsyncSession,
    progress_callback: Optional[callable] = None,
    task_id: Optional[str] = None  # 新增：用于流式生成
) -> Dict[str, Any]:
    """
    处理多个视角（主次视角优先级策略）
    
    难点4解决方案：
    - Primary View：同步处理，优先保证，快速返回
    - Secondary View：异步处理，可以后补，不影响主视角
    
    Args:
        document_id: 文档ID
        primary_view: 主视角
        enabled_views: 启用的视角列表
        content: 预处理后的内容
        segments: 段落切分结果
        detection_scores: 系统检测的特征得分
        db: 数据库会话
        progress_callback: 进度回调函数
    
    Returns:
        {
            'results': {view: result_data},
            'processing_status': {view: status},
            'primary_view': primary_view,
            'primary_view_ready': bool,
            'secondary_views_ready': [view, ...]
        }
    """
    results = {}
    processing_status = {}
    
    # 1. 优先处理主视角（同步，必须快速返回）
    if primary_view in enabled_views:
        primary_result = await process_view_independently(
            document_id=document_id,
            view=primary_view,
            content=content,
            segments=segments,
            is_primary=True,
            db=db,
            progress_callback=progress_callback,
            stream_callback=None,
            task_id=task_id
        )
        
        if primary_result:
            results[primary_view] = primary_result['result']
            processing_status[primary_view] = {
                'status': 'completed',
                'processing_time': primary_result['processing_time'],
                'ready': True
            }
        else:
            processing_status[primary_view] = {
                'status': 'failed',
                'ready': False
            }
    
    # 2. 次视角滞后异步处理（创建后台任务，不阻塞主任务）
    secondary_views = [v for v in enabled_views if v != primary_view]
    
    # 为次视角创建后台任务（不立即处理）
    if secondary_views:
        from app.tasks.document_processing import process_secondary_views_task
        import json
        
        # 将segments序列化为JSON（Celery任务需要可序列化的参数）
        segments_json = json.dumps(segments) if segments else "[]"
        
        # 创建后台任务处理次视角（延迟执行，不阻塞主任务）
        try:
            # 使用apply_async创建异步任务，不等待结果
            process_secondary_views_task.apply_async(
                args=[document_id, secondary_views, content, segments_json, task_id],
                countdown=5  # 延迟5秒后开始处理，确保主视角任务已返回
            )
            logger.info(
                "已创建次视角后台处理任务",
                document_id=document_id,
                secondary_views=secondary_views,
                task_id=task_id
            )
        except Exception as e:
            logger.error(
                "创建次视角后台任务失败",
                document_id=document_id,
                error=str(e)
            )
        
        # 标记次视角为"处理中"状态
        for view in secondary_views:
            processing_status[view] = {
                'status': 'processing',  # 标记为处理中
                'ready': False
            }
            # 不设置results，让前端知道这些视角还在处理中
    
    # 3. 创建多视角输出容器
    container = MultiViewOutputContainer.create_container(
        views=results,
        enabled_views=enabled_views,
        confidence=detection_scores,
        primary_view=primary_view
    )
    
    return {
        'results': results,
        'processing_status': processing_status,
        'container': container,
        'primary_view': primary_view,
        'primary_view_ready': processing_status.get(primary_view, {}).get('ready', False),
        'secondary_views_ready': [
            view for view, status in processing_status.items()
            if view != primary_view and status.get('ready', False)
        ]
    }

