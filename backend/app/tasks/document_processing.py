"""
文档处理任务
异步处理文档：提取内容、识别类型、处理文档
"""
import asyncio
from datetime import datetime
from uuid import UUID
from typing import Optional
import structlog

from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.core.config import settings
from app.models.document import Document
from app.models.document_type import DocumentType
from app.models.processing_result import ProcessingResult
from app.models.processing_task import ProcessingTask
from app.models.system_learning_data import SystemLearningData
from app.services.document_extractor import DocumentExtractor
from app.services.text_preprocessor import TextPreprocessor
from app.services.document_classifier import DocumentClassifier
from app.services.document_view_classifier import DocumentViewClassifier
from app.services.interview_processor import InterviewProcessor
from app.services.technical_processor import TechnicalProcessor
from app.services.architecture_processor import ArchitectureProcessor
from app.services.intermediate_results_service import IntermediateResultsService
from app.services.source_segmenter import SourceSegmenter
from app.services.view_registry import ViewRegistry
from app.tasks.view_processing_helper import process_views_with_priority, process_view_independently
from app.utils.processing_exception import (
    ProcessingException,
    ProcessingStatus,
    ErrorType,
    UserActionMapper
)
from app.services.document_size_validator import DocumentSizeValidator
from app.models.intermediate_result import DocumentIntermediateResult
from sqlalchemy import select

logger = structlog.get_logger()


async def update_progress(
    task_id: str, 
    progress: int, 
    stage: str, 
    status: str = "running",
    enabled_views: Optional[list] = None,
    primary_view: Optional[str] = None,
    stream_data: Optional[dict] = None
):
    """更新任务进度（异步函数）
    
    Args:
        task_id: 任务ID
        progress: 进度百分比
        stage: 当前阶段描述
        status: 任务状态
        enabled_views: 启用的视角列表（可选）
        primary_view: 主视角（可选）
    """
    # 创建新的独立session，避免并发冲突
    db = AsyncSessionLocal()
    try:
        task_uuid = UUID(task_id)
        result = await db.execute(
            select(ProcessingTask).where(ProcessingTask.id == task_uuid)
        )
        task = result.scalar_one_or_none()
        
        if task:
            task.progress = progress
            task.current_stage = stage
            task.status = status
            await db.commit()
            
            # 发布进度更新到Redis（供WebSocket使用）
            import redis
            import json
            r = redis.from_url(settings.REDIS_URL)
            progress_data = {
                "progress": progress,
                "stage": stage,
                "status": status
            }
            # 如果提供了视角信息，添加到进度数据中
            if enabled_views is not None:
                progress_data["enabled_views"] = enabled_views
            if primary_view is not None:
                progress_data["primary_view"] = primary_view
            if stream_data is not None:
                progress_data["stream"] = stream_data
            
            r.publish(
                f"task_progress:{task_id}",
                json.dumps(progress_data, ensure_ascii=False)
            )
    except Exception as e:
        logger.error("更新进度失败", task_id=task_id, error=str(e))
        await db.rollback()
    finally:
        await db.close()


@celery_app.task(bind=True, name="app.tasks.document_processing.process_document")
def process_document_task(self, document_id: str, task_id: str, enabled_views: Optional[list] = None):
    """
    文档处理任务
    
    Args:
        document_id: 文档ID
        task_id: 处理任务ID
    """
    import asyncio
    import nest_asyncio
    import json
    import os
    
    # #region agent log
    try:
        log_data = {
            "location": "document_processing.py:75",
            "message": "process_document_task entry",
            "data": {
                "document_id": document_id,
                "task_id": task_id,
                "enabled_views": enabled_views,
                "enabled_views_type": str(type(enabled_views)),
                "enabled_views_is_none": enabled_views is None
            },
            "timestamp": int(datetime.now().timestamp() * 1000),
            "sessionId": "debug-session",
            "runId": "run1",
            "hypothesisId": "A"
        }
        log_path = os.getenv("DEBUG_LOG_PATH", "/app/.cursor/debug.log")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_data, ensure_ascii=False) + "\n")
    except Exception:
        pass
    # #endregion
    
    # 允许嵌套事件循环（解决Celery中的asyncio问题）
    nest_asyncio.apply()
    
    # 在定义_process函数之前，先捕获enabled_views的值到局部变量
    # 这样_process函数就可以通过闭包访问这个值，而不会触发UnboundLocalError
    _captured_enabled_views = enabled_views if enabled_views is not None else []
    
    async def _process():
        # 创建新的独立session
        db = AsyncSessionLocal()
        # 使用捕获的值初始化局部变量
        current_enabled_views = _captured_enabled_views.copy() if _captured_enabled_views else []
        try:
            # #region agent log
            try:
                log_data = {
                    "location": "document_processing.py:127",
                    "message": "_process entry",
                    "data": {
                        "document_id": document_id,
                        "current_enabled_views": current_enabled_views,
                        "current_enabled_views_type": str(type(current_enabled_views)),
                        "current_enabled_views_is_none": current_enabled_views is None,
                        "_captured_enabled_views": _captured_enabled_views
                    },
                    "timestamp": int(datetime.now().timestamp() * 1000),
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "A"
                }
                log_path = os.getenv("DEBUG_LOG_PATH", "/app/.cursor/debug.log")
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(log_data, ensure_ascii=False) + "\n")
            except Exception:
                pass
            # #endregion
            try:
                doc_uuid = UUID(document_id)
                task_uuid = UUID(task_id)
                
                # 获取文档
                result = await db.execute(
                    select(Document).where(Document.id == doc_uuid)
                )
                document = result.scalar_one_or_none()
                
                if not document:
                    logger.error("文档不存在", document_id=document_id)
                    update_progress(task_id, 0, "错误：文档不存在", "failed")
                    return
                
                # 更新文档状态
                document.status = "processing"
                await db.commit()
                
                logger.info("开始处理文档", document_id=document_id, filename=document.filename)
                
                # 步骤1: 提取文档内容 (0-15%)
                await update_progress(task_id, 10, "提取文档内容中...", "running")
                try:
                    # 定义进度回调（仅PDF支持）
                    last_progress_update = [0]  # 使用列表避免闭包问题
                    
                    async def extraction_progress(current: int, total: int):
                        """提取进度回调（异步函数，用于更新进度）"""
                        if total > 0 and current > last_progress_update[0]:
                            progress_pct = int(10 + (current / total) * 5)  # 10-15%
                            await update_progress(
                                task_id, 
                                progress_pct, 
                                f"提取文档内容中... ({current}/{total} 页)", 
                                "running"
                            )
                            last_progress_update[0] = current
                    
                    # 根据文件大小动态调整超时
                    file_size_mb = document.file_size / (1024 * 1024)
                    extraction_timeout = 120  # 默认2分钟
                    if file_size_mb > 20:
                        extraction_timeout = 180  # 大文件3分钟
                    elif file_size_mb > 10:
                        extraction_timeout = 150  # 中等文件2.5分钟
                    
                    # 对于PDF，使用进度回调；其他类型不使用
                    progress_cb = extraction_progress if document.file_type.lower() == 'pdf' else None
                    
                    content = await DocumentExtractor.extract(
                        document.file_path, 
                        document.file_type,
                        timeout=extraction_timeout,
                        progress_callback=progress_cb
                    )
                    document.content_extracted = content
                    await db.commit()
                    await update_progress(task_id, 15, "内容提取完成", "running")
                    logger.info(
                        "文档内容提取完成",
                        document_id=document_id,
                        content_length=len(content),
                        file_size_mb=file_size_mb,
                        timeout_used=extraction_timeout
                    )
                    
                    # 验证内容长度和处理时间（在提取后）
                    from app.services.document_size_validator import DocumentSizeValidator
                    from app.services.view_registry import ViewRegistry
                    try:
                        # 先尝试识别文档类型（如果已识别）
                        # 使用ViewRegistry获取默认类型（向后兼容）
                        detected_type = ViewRegistry.get_type_mapping('learning')  # 默认类型：technical，后续会被实际识别结果覆盖
                        content_validation = DocumentSizeValidator.validate_content_length(
                            len(content), detected_type
                        )
                        warnings = content_validation.get("warnings", [])
                        estimated_time = content_validation.get("estimated_time")
                        if warnings:
                            logger.warning(
                                "文档内容长度警告",
                                document_id=document_id,
                                content_length=len(content),
                                estimated_time=estimated_time,
                                warnings=warnings
                            )
                    except ValueError as e:
                        # 内容过长或处理时间过长，拒绝处理
                        logger.error(
                            "文档内容验证失败",
                            document_id=document_id,
                            content_length=len(content),
                            error=str(e)
                        )
                        document.status = "failed"
                        await db.commit()
                        await update_progress(
                            task_id, 
                            0, 
                            f"文档过大: {str(e)}", 
                            "failed"
                        )
                        return
                except FileNotFoundError as e:
                    # 文件不存在
                    error = ProcessingException(
                        status=ProcessingStatus.FAILED,
                        error_type=ErrorType.INVALID_FILE,
                        error_message=f"文件不存在: {str(e)}",
                        error_details={
                            "step": "内容提取",
                            "reason": "文件不存在或已被删除"
                        },
                        user_actions=UserActionMapper.get_actions_for_error(
                            ErrorType.INVALID_FILE, {}
                        )
                    )
                    logger.error("内容提取失败：文件不存在", document_id=document_id, error=str(e))
                    document.status = "failed"
                    await db.commit()
                    await update_progress(task_id, 0, error.error_message, "failed")
                    return
                except ValueError as e:
                    # 文件格式不支持或内容为空
                    error_msg = str(e)
                    if "不支持" in error_msg or "格式" in error_msg:
                        error = ProcessingException(
                            status=ProcessingStatus.FAILED,
                            error_type=ErrorType.UNSUPPORTED_FORMAT,
                            error_message=error_msg,
                            error_details={
                                "step": "内容提取",
                                "reason": "文件格式不支持"
                            },
                            user_actions=UserActionMapper.get_actions_for_error(
                                ErrorType.UNSUPPORTED_FORMAT,
                                {"supported_formats": "PDF, Word, PPT, Markdown, TXT"}
                            )
                        )
                    elif "内容过少" in error_msg or len(content) < 50:
                        error = ProcessingException(
                            status=ProcessingStatus.FAILED,
                            error_type=ErrorType.CONTENT_TOO_SHORT,
                            error_message="文档内容过少，无法处理",
                            error_details={
                                "step": "内容提取",
                                "reason": f"内容长度: {len(content) if 'content' in locals() else 0} 字符"
                            },
                            user_actions=UserActionMapper.get_actions_for_error(
                                ErrorType.CONTENT_TOO_SHORT, {}
                            )
                        )
                    else:
                        error = ProcessingException(
                            status=ProcessingStatus.FAILED,
                            error_type=ErrorType.INVALID_FILE,
                            error_message=error_msg,
                            error_details={
                                "step": "内容提取",
                                "reason": str(e)
                            },
                            user_actions=UserActionMapper.get_actions_for_error(
                                ErrorType.INVALID_FILE, {}
                            )
                        )
                    logger.error("内容提取失败", document_id=document_id, error=str(e))
                    document.status = "failed"
                    await db.commit()
                    await update_progress(task_id, 0, error.error_message, "failed")
                    return
                except Exception as e:
                    # 其他异常
                    error = ProcessingException(
                        status=ProcessingStatus.FAILED,
                        error_type=ErrorType.INVALID_FILE,
                        error_message=f"内容提取失败: {str(e)[:100]}",
                        error_details={
                            "step": "内容提取",
                            "reason": str(e),
                            "error_type": type(e).__name__
                        },
                        user_actions=UserActionMapper.get_actions_for_error(
                            ErrorType.INVALID_FILE, {}
                        )
                    )
                    logger.error("内容提取失败", document_id=document_id, error=str(e), error_type=type(e).__name__)
                    document.status = "failed"
                    await db.commit()
                    await update_progress(task_id, 0, error.error_message, "failed")
                    return
                
                # 步骤1.5: 文本预处理 (15-20%)
                await update_progress(task_id, 18, "文本预处理中...", "running")
                preprocessed_content = content
                try:
                    preprocess_result = await TextPreprocessor.preprocess(
                        content=content,
                        file_type=document.file_type,
                        timeout=10.0
                    )
                    preprocessed_content = preprocess_result["cleaned_content"]
                    preprocess_stats = preprocess_result["stats"]
                    
                    logger.info(
                        "文本预处理完成",
                        document_id=document_id,
                        original_length=preprocess_stats["original_length"],
                        cleaned_length=preprocess_stats["cleaned_length"],
                        removed_chars=preprocess_stats["removed_chars"],
                        removed_paragraphs=preprocess_stats["removed_paragraphs"]
                    )
                    await update_progress(task_id, 20, "文本预处理完成", "running")
                except Exception as e:
                    # 预处理失败时使用原始内容继续，记录警告
                    logger.warning(
                        "文本预处理失败，使用原始内容继续",
                        document_id=document_id,
                        error=str(e)
                    )
                    # 不中断处理流程，继续使用原始content
                    await update_progress(task_id, 20, "文本预处理跳过", "running")
                
                # 步骤1.6: 段落切分（视角无关）
                await update_progress(task_id, 22, "段落切分中...", "running")
                segments = []
                try:
                    from app.services.source_segmenter import SourceSegmenter
                    segments = SourceSegmenter.segment_content(preprocessed_content, timeout=5.0)
                    logger.info("段落切分完成", document_id=document_id, segments_count=len(segments))
                except Exception as e:
                    logger.warning("段落切分失败，使用空列表", document_id=document_id, error=str(e))
                    segments = []
                
                # 步骤1.7: 保存中间结果（视角无关）- 难点3解决方案
                await update_progress(task_id, 25, "保存中间结果...", "running")
                try:
                    await IntermediateResultsService.save_intermediate_results(
                        document_id=doc_uuid,
                        content=content,  # 原始内容（视角无关）
                        preprocessed_content=preprocessed_content,  # 预处理后内容（视角无关）
                        segments=segments,  # 段落切分结果（视角无关）
                        metadata={
                            'file_type': document.file_type,
                            'file_size': document.file_size,
                            'filename': document.filename
                        },
                        db=db
                    )
                    logger.info("中间结果保存完成", document_id=document_id)
                except Exception as e:
                    logger.warning("保存中间结果失败，继续处理", document_id=document_id, error=str(e))
                    # 不中断处理流程
                
                # 使用预处理后的内容继续
                content = preprocessed_content
                
                # 步骤2: 识别文档类型和推荐视角 (25-40%)
                await update_progress(task_id, 30, "识别文档类型和视角中...", "running")
                detected_type = "unknown"
                primary_view = "learning"
                # #region agent log
                try:
                    log_data = {
                        "location": "document_processing.py:373",
                        "message": "step2 before init enabled_views",
                        "data": {
                            "document_id": document_id,
                            "current_enabled_views": current_enabled_views,
                            "current_enabled_views_type": str(type(current_enabled_views)),
                            "current_enabled_views_is_none": current_enabled_views is None,
                            "_captured_enabled_views": _captured_enabled_views
                        },
                        "timestamp": int(datetime.now().timestamp() * 1000),
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "B"
                    }
                    log_path = os.getenv("DEBUG_LOG_PATH", "/app/.cursor/debug.log")
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps(log_data, ensure_ascii=False) + "\n")
                except Exception:
                    pass
                # #endregion
                # 初始化enabled_views，使用捕获的值避免UnboundLocalError
                enabled_views = current_enabled_views.copy() if current_enabled_views else []
                # 确保enabled_views是列表类型
                if not isinstance(enabled_views, list):
                    enabled_views = []
                user_specified_views = enabled_views.copy() if enabled_views else []  # 保存用户指定的views
                # #region agent log
                try:
                    log_data = {
                        "location": "document_processing.py:323",
                        "message": "step2 after init enabled_views",
                        "data": {
                            "document_id": document_id,
                            "enabled_views": enabled_views,
                            "enabled_views_type": str(type(enabled_views)),
                            "enabled_views_len": len(enabled_views) if isinstance(enabled_views, list) else None,
                            "user_specified_views": user_specified_views
                        },
                        "timestamp": int(datetime.now().timestamp() * 1000),
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "B"
                    }
                    log_path = os.getenv("DEBUG_LOG_PATH", "/app/.cursor/debug.log")
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps(log_data, ensure_ascii=False) + "\n")
                except Exception:
                    pass
                # #endregion
                detection_scores = {}
                cache_key = None
                confidence = 0.0
                method = 'unknown'
                
                try:
                    # 2.1 系统检测特征得分（这是算力与存储的边界）- 难点2解决方案
                    detection_scores = {
                        'qa': DocumentViewClassifier.detect_qa_structure(content),
                        'system': DocumentViewClassifier.detect_component_relationships(content),
                        'learning': DocumentViewClassifier.detect_usage_flow(content)
                    }
                    
                    # 2.2 生成缓存key（基于检测得分，不基于推荐）- 难点2解决方案
                    cache_key = DocumentViewClassifier.generate_cache_key_from_scores(
                        str(doc_uuid), detection_scores
                    )
                    
                    # 2.2.1 尝试从缓存获取检测结果（可选优化）
                    from app.services.cache_service import CacheService
                    cached_detection = CacheService.get_detection_result(cache_key)
                    if cached_detection:
                        logger.info("从缓存获取检测结果", document_id=document_id, cache_key=cache_key)
                        # 如果缓存中有相同的检测得分，可以复用（但这里我们仍然需要重新推荐，因为推荐可能变化）
                    
                    # 2.2.2 保存检测结果到缓存（用于后续查询）
                    CacheService.set_detection_result(
                        cache_key,
                        {
                            'detection_scores': detection_scores,
                            'document_id': str(doc_uuid)
                        }
                    )
                    
                    # 2.2.3 缓存中间结果（用于快速切换视角）
                    # 获取之前保存的中间结果并缓存
                    try:
                        intermediate_result = await IntermediateResultsService.get_intermediate_results(
                            document_id=doc_uuid,
                            db=db
                        )
                        if intermediate_result:
                            CacheService.set_intermediate_results(
                                cache_key,
                                {
                                    'content': intermediate_result.content,
                                    'preprocessed_content': intermediate_result.preprocessed_content,
                                    'segments': intermediate_result.segments,
                                    'metadata_json': intermediate_result.metadata_json
                                }
                            )
                            logger.info("中间结果已缓存", document_id=document_id, cache_key=cache_key)
                    except Exception as e:
                        logger.warning("缓存中间结果失败", document_id=document_id, error=str(e))
                        # 不中断处理流程
                    
                    # 2.3 推荐主次视角（用于UI和算力分配，不影响存储）
                    if user_specified_views:
                        # 用户指定了views，使用指定的views
                        # 根据detection_scores确定primary_view（从用户指定的views中选择得分最高的）
                        view_scores = {v: detection_scores.get(v, 0.0) for v in user_specified_views}
                        primary_view = max(view_scores, key=view_scores.get) if view_scores else user_specified_views[0]
                        enabled_views = user_specified_views
                        # 根据primary_view确定detected_type（向后兼容）
                        detected_type = ViewRegistry.get_type_mapping(primary_view)
                        confidence = detection_scores.get(primary_view, 0.0)
                        method = 'user_specified'
                        logger.info(
                            "使用用户指定的视角",
                            document_id=document_id,
                            enabled_views=enabled_views,
                            primary_view=primary_view,
                            detection_scores=detection_scores
                        )
                    else:
                        # 未指定views，自动推荐
                        try:
                            view_recommendation = await DocumentViewClassifier.recommend_views(
                                content=content,
                                api_key=settings.DEEPSEEK_API_KEY,
                                api_base=settings.DEEPSEEK_API_BASE
                            )
                            primary_view = view_recommendation['primary_view']
                            enabled_views = view_recommendation['enabled_views']
                            detected_type = view_recommendation['type_mapping']
                            confidence = detection_scores.get(primary_view, 0.0)
                            method = view_recommendation.get('method', 'rule')
                        except Exception as e:
                            # 如果推荐失败，使用默认值
                            logger.warning("视角推荐失败，使用默认值", document_id=document_id, error=str(e))
                            primary_view = "learning"
                            enabled_views = [primary_view]
                            detected_type = ViewRegistry.get_type_mapping(primary_view)
                            confidence = detection_scores.get(primary_view, 0.0)
                            method = 'default_fallback'
                    
                    # 2.4 根据识别的文档类型，重新验证处理时间
                    try:
                        content_validation = DocumentSizeValidator.validate_content_length(
                            len(content), detected_type
                        )
                        estimated_time = content_validation.get("estimated_time")
                        warnings = content_validation.get("warnings", [])
                        logger.info(
                            "文档处理时间估算",
                            document_id=document_id,
                            doc_type=detected_type,
                            primary_view=primary_view,
                            enabled_views=enabled_views,
                            content_length=len(content),
                            estimated_time=estimated_time,
                            warnings=warnings
                        )
                    except ValueError as e:
                        logger.error(
                            "文档处理时间验证失败",
                            document_id=document_id,
                            doc_type=detected_type,
                            content_length=len(content),
                            error=str(e)
                        )
                        document.status = "failed"
                        await db.commit()
                        await update_progress(
                            task_id,
                            0,
                            f"文档过大: {str(e)}",
                            "failed"
                        )
                        return
                    
                    # 2.5 保存类型识别结果（包含视角信息）
                    doc_type = DocumentType(
                        document_id=doc_uuid,
                        detected_type=detected_type,
                        primary_view=primary_view,
                        enabled_views=enabled_views,
                        detection_scores=detection_scores,  # 保存检测得分（用于缓存key）
                        confidence=confidence,
                        detection_method=method
                    )
                    db.add(doc_type)
                    await db.commit()
                    
                    # 视角检测完成后，立即更新进度（包含视角信息）
                    await update_progress(
                        task_id, 
                        40, 
                        f"文档类型: {detected_type}, 主视角: {primary_view}", 
                        "running",
                        enabled_views=enabled_views,
                        primary_view=primary_view
                    )
                    logger.info(
                        "文档类型和视角识别完成",
                        document_id=document_id,
                        type=detected_type,
                        primary_view=primary_view,
                        enabled_views=enabled_views,
                        confidence=confidence
                    )
                except Exception as e:
                    logger.error("类型和视角识别失败", document_id=document_id, error=str(e))
                    # #region agent log
                    try:
                        log_data = {
                            "location": "document_processing.py:527",
                            "message": "step2 exception handler",
                            "data": {
                                "document_id": document_id,
                                "error": str(e),
                                "error_type": type(e).__name__,
                                "enabled_views_in_locals": "enabled_views" in locals(),
                                "enabled_views": enabled_views if "enabled_views" in locals() else "NOT_IN_LOCALS"
                            },
                            "timestamp": int(datetime.now().timestamp() * 1000),
                            "sessionId": "debug-session",
                            "runId": "run1",
                            "hypothesisId": "C"
                        }
                        log_path = os.getenv("DEBUG_LOG_PATH", "/app/.cursor/debug.log")
                        with open(log_path, "a", encoding="utf-8") as f:
                            f.write(json.dumps(log_data, ensure_ascii=False) + "\n")
                    except Exception:
                        pass
                    # #endregion
                    # 使用默认值继续处理（使用ViewRegistry获取默认映射）
                    from app.services.view_registry import ViewRegistry
                    primary_view = "learning"  # 默认视角
                    detected_type = ViewRegistry.get_type_mapping(primary_view)  # 默认类型：technical
                    enabled_views = [primary_view]  # 确保enabled_views被赋值
                    detection_scores = {'learning': 1.0}
                    # #region agent log
                    try:
                        log_data = {
                            "location": "document_processing.py:483",
                            "message": "step2 exception handler after set enabled_views",
                            "data": {
                                "document_id": document_id,
                                "enabled_views": enabled_views,
                                "enabled_views_type": str(type(enabled_views))
                            },
                            "timestamp": int(datetime.now().timestamp() * 1000),
                            "sessionId": "debug-session",
                            "runId": "run1",
                            "hypothesisId": "C"
                        }
                        log_path = os.getenv("DEBUG_LOG_PATH", "/app/.cursor/debug.log")
                        with open(log_path, "a", encoding="utf-8") as f:
                            f.write(json.dumps(log_data, ensure_ascii=False) + "\n")
                    except Exception:
                        pass
                    # #endregion
                
                # 步骤3: 多视角处理文档 (40-90%) - 难点4解决方案
                await update_progress(task_id, 50, "AI处理文档中（多视角）...", "running")
                # #region agent log
                try:
                    log_data = {
                        "location": "document_processing.py:486",
                        "message": "step3 before process_views_with_priority",
                        "data": {
                            "document_id": document_id,
                            "enabled_views": enabled_views,
                            "enabled_views_type": str(type(enabled_views)),
                            "enabled_views_in_locals": "enabled_views" in locals(),
                            "primary_view": primary_view
                        },
                        "timestamp": int(datetime.now().timestamp() * 1000),
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "D"
                    }
                    log_path = os.getenv("DEBUG_LOG_PATH", "/app/.cursor/debug.log")
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps(log_data, ensure_ascii=False) + "\n")
                except Exception:
                    pass
                # #endregion
                start_time = datetime.now()
                # 根据视角数量动态调整超时时间（流式生成和多个视角会增加处理时间）
                view_count = len(enabled_views) if enabled_views else 1
                base_timeout = 1200  # 基础超时：20分钟
                timeout_per_view = 300  # 每个额外视角增加5分钟
                PROCESSING_TIMEOUT = base_timeout + (view_count - 1) * timeout_per_view
                # 但不超过Celery软超时（1500秒=25分钟）
                PROCESSING_TIMEOUT = min(PROCESSING_TIMEOUT, 1500)
                
                # 创建流式内容回调函数（用于推送AI生成的内容）
                def stream_content_callback(chunk: str, view: str, field: str = None):
                    """推送流式内容到Redis，供前端实时显示"""
                    try:
                        import redis
                        import json
                        r = redis.from_url(settings.REDIS_URL)
                        stream_data = {
                            "type": "stream_content",
                            "view": view,
                            "chunk": chunk,
                            "field": field  # 可选：标识是哪个字段（如prerequisites, learning_path等）
                        }
                        r.publish(
                            f"task_stream:{task_id}:{view}",
                            json.dumps(stream_data, ensure_ascii=False)
                        )
                    except Exception as e:
                        logger.warning("推送流式内容失败", error=str(e))
                
                # 创建进度回调函数（用于主视角）
                async def progress_callback(progress, stage):
                    # 检查超时
                    elapsed = (datetime.now() - start_time).total_seconds()
                    if elapsed > PROCESSING_TIMEOUT:
                        raise ProcessingException(
                            status=ProcessingStatus.TIMEOUT,
                            error_type=ErrorType.TIMEOUT,
                            error_message=f"处理超时（超过{PROCESSING_TIMEOUT}秒）",
                            error_details={
                                "step": "AI处理",
                                "elapsed_time": elapsed,
                                "timeout": PROCESSING_TIMEOUT
                            },
                            user_actions=UserActionMapper.get_actions_for_error(
                                ErrorType.TIMEOUT, {}
                            )
                        )
                    # 将进度映射到50-80%范围（主视角处理）
                    mapped_progress = 50 + int(progress * 0.3)
                    await update_progress(task_id, mapped_progress, stage, "running")
                
                try:
                    # 使用多视角处理逻辑（主次视角优先级策略）
                    view_processing_result = await process_views_with_priority(
                        document_id=doc_uuid,
                        primary_view=primary_view,
                        enabled_views=enabled_views,
                        content=content,
                        segments=segments,
                        detection_scores=detection_scores,
                        db=db,
                        progress_callback=progress_callback,
                        task_id=task_id  # 传递task_id用于流式生成
                    )
                    
                    results = view_processing_result['results']
                    processing_status = view_processing_result['processing_status']
                    container = view_processing_result['container']
                    primary_view_ready = view_processing_result['primary_view_ready']
                    secondary_views_ready = view_processing_result['secondary_views_ready']
                    
                    # 检查处理时间
                    elapsed = (datetime.now() - start_time).total_seconds()
                    if elapsed > PROCESSING_TIMEOUT:
                        raise ProcessingException(
                            status=ProcessingStatus.TIMEOUT,
                            error_type=ErrorType.TIMEOUT,
                            error_message=f"处理超时（超过{PROCESSING_TIMEOUT}秒）",
                            error_details={
                                "step": "AI处理",
                                "elapsed_time": elapsed,
                                "timeout": PROCESSING_TIMEOUT
                            },
                            user_actions=UserActionMapper.get_actions_for_error(
                                ErrorType.TIMEOUT, {}
                            )
                        )
                    
                    # 主视角必须成功
                    if not primary_view_ready:
                        raise ProcessingException(
                            status=ProcessingStatus.FAILED,
                            error_type=ErrorType.AI_CALL_FAILED,
                            error_message="主视角处理失败",
                            error_details={
                                "step": "AI处理",
                                "primary_view": primary_view
                            },
                            user_actions=UserActionMapper.get_actions_for_error(
                                ErrorType.AI_CALL_FAILED, {}
                            )
                        )
                    
                    # 使用主视角的结果作为主要结果（向后兼容）
                    result_data = results.get(primary_view, {})
                    
                    # 更新进度：主视角已完成，次视角正在后台处理
                    secondary_views_count = len([v for v in enabled_views if v != primary_view])
                    if secondary_views_count > 0:
                        await update_progress(
                            task_id, 
                            80, 
                            f"主视角 {primary_view} 生成完成，其他视角正在后台异步生成...", 
                            "running"
                        )
                    else:
                        await update_progress(
                            task_id, 
                            90, 
                            f"AI处理完成（主视角: {primary_view}）", 
                            "running"
                        )
                    
                except ProcessingException as e:
                    # 明确的处理异常
                    logger.error(
                        "文档处理失败（明确异常）",
                        document_id=document_id,
                        status=e.status.value,
                        error_type=e.error_type.value,
                        error_message=e.error_message
                    )
                    document.status = e.status.value
                    await db.commit()
                    await update_progress(task_id, 0, e.error_message, e.status.value)
                    return
                except asyncio.TimeoutError:
                    # 异步超时
                    error = ProcessingException(
                        status=ProcessingStatus.TIMEOUT,
                        error_type=ErrorType.TIMEOUT,
                        error_message=f"处理超时（超过{PROCESSING_TIMEOUT}秒）",
                        error_details={
                            "step": "AI处理",
                            "timeout": PROCESSING_TIMEOUT
                        },
                        user_actions=UserActionMapper.get_actions_for_error(
                            ErrorType.TIMEOUT, {}
                        )
                    )
                    logger.error("文档处理超时", document_id=document_id)
                    document.status = "timeout"
                    await db.commit()
                    await update_progress(task_id, 0, error.error_message, "timeout")
                    return
                except Exception as e:
                    # 其他异常（可能是AI调用失败）
                    error_msg = str(e)
                    error_type = ErrorType.AI_CALL_FAILED
                    if "API" in error_msg or "api" in error_msg or "key" in error_msg.lower():
                        error_type = ErrorType.AI_CALL_FAILED
                    elif "timeout" in error_msg.lower() or "超时" in error_msg:
                        error_type = ErrorType.TIMEOUT
                    
                    error = ProcessingException(
                        status=ProcessingStatus.FAILED,
                        error_type=error_type,
                        error_message=f"AI处理失败: {error_msg[:100]}",
                        error_details={
                            "step": "AI处理",
                            "reason": error_msg,
                            "error_type": type(e).__name__
                        },
                        user_actions=UserActionMapper.get_actions_for_error(
                            error_type, {}
                        )
                    )
                    logger.error(
                        "文档处理失败",
                        document_id=document_id,
                        error=str(e),
                        error_type=type(e).__name__
                    )
                    document.status = "failed"
                    await db.commit()
                    await update_progress(task_id, 0, error.error_message, "failed")
                    return
                
                # 步骤4: 保存处理结果 (90-100%) - 难点1解决方案：每个view独立存储
                await update_progress(task_id, 90, "保存处理结果...", "running")
                try:
                    end_time = datetime.now()
                    processing_time = int((end_time - start_time).total_seconds())
                    
                    # 注意：每个view的结果已经在process_views_with_priority中独立保存
                    # 这里只需要确保主视角结果存在（用于向后兼容）
                    # 如果主视角结果不存在，创建一个（使用容器）
                    primary_result_query = await db.execute(
                        select(ProcessingResult)
                        .where(ProcessingResult.document_id == doc_uuid)
                        .where(ProcessingResult.view == primary_view)
                    )
                    primary_result = primary_result_query.scalar_one_or_none()
                    
                    # 注意：每个view的结果已经在process_views_with_priority中独立保存
                    # 这里不需要再次保存，只需要确保主视角结果存在即可
                    # 如果主视角结果不存在（理论上不应该发生），记录警告
                    if not primary_result:
                        logger.warning(
                            "主视角结果不存在，但应该已在process_views_with_priority中保存",
                            document_id=document_id,
                            primary_view=primary_view
                        )
                        # 如果确实不存在，创建一个（使用主视角结果）
                        primary_result = ProcessingResult(
                            document_id=doc_uuid,
                            view=primary_view,
                            document_type=detected_type,
                            result_data=result_data,  # 使用主视角结果
                            is_primary=True,
                            processing_time=processing_time
                        )
                        db.add(primary_result)
                        await db.commit()
                    
                    # 更新文档状态
                    document.status = "completed"
                    
                    # 更新任务状态
                    result = await db.execute(
                        select(ProcessingTask).where(ProcessingTask.id == task_uuid)
                    )
                    task = result.scalar_one_or_none()
                    if task:
                        task.status = "completed"
                        task.progress = 100
                        task.current_stage = "处理完成"
                        task.completed_at = end_time
                    
                    # 记录AI结果质量（监控）
                    from app.services.ai_monitoring_service import AIMonitoringService
                    monitoring_service = AIMonitoringService.get_instance()
                    if monitoring_service.enabled:
                        try:
                            await monitoring_service.record_result_quality(
                                document_id=document_id,
                                document_type=detected_type,
                                result_data=result_data
                            )
                            logger.debug("AI结果质量已记录", document_id=document_id)
                        except Exception as e:
                            logger.warning("记录AI结果质量失败", 
                                         error=str(e),
                                         document_id=document_id)
                    
                    # 先提交结果，确保用户能立即看到
                    await db.commit()
                    
                    # 保存系统学习数据（基础版）- 模型预热 + 同步生成
                    try:
                        # 评估处理结果质量（快速评估，设置超时避免卡死）
                        quality_score = None
                        try:
                            from app.services.quality_assessor import get_quality_assessor
                            quality_assessor = get_quality_assessor()
                            # 设置超时，避免卡死
                            quality_score = await asyncio.wait_for(
                                quality_assessor.assess_quality(detected_type, result_data),
                                timeout=10.0  # 10秒超时
                            )
                            logger.info("质量评估完成", document_id=document_id, quality_score=quality_score)
                        except asyncio.TimeoutError:
                            logger.warning("质量评估超时，跳过", document_id=document_id)
                        except Exception as e:
                            logger.warning("质量评估异常，但继续处理", error=str(e), document_id=document_id)
                        
                        # 生成文档向量（同步生成，但设置超时避免卡死）
                        embedding = None
                        try:
                            from app.services.embedding_service import get_embedding_service
                            embedding_service = get_embedding_service()
                            
                            # 设置向量生成超时（30秒），避免首次加载模型时卡死
                            # 如果模型已预热，生成向量很快（0.5-5秒）
                            try:
                                embedding = await asyncio.wait_for(
                                    embedding_service.generate_embedding(content),
                                    timeout=30.0  # 30秒超时（首次加载模型可能需要时间）
                                )
                                if embedding:
                                    logger.info("文档向量生成成功", document_id=document_id)
                                else:
                                    logger.warning("文档向量生成失败，但继续处理", document_id=document_id)
                            except asyncio.TimeoutError:
                                logger.warning("向量生成超时（30秒），跳过向量生成，继续处理", document_id=document_id)
                            except Exception as e:
                                logger.warning("向量生成异常，但继续处理", error=str(e), document_id=document_id)
                        except Exception as e:
                            logger.warning("向量生成服务初始化失败，但继续处理", error=str(e), document_id=document_id)
                        
                        # 保存学习数据（包含向量，如果生成成功）
                        learning_data = SystemLearningData(
                            document_id=doc_uuid,
                            content_summary=content[:500] if len(content) > 500 else content,
                            embedding=embedding,  # 包含向量（如果生成成功）
                            document_type=detected_type,
                            processing_result_summary=str(result_data)[:500] if result_data else None,
                            processing_time=processing_time,
                            quality_score=quality_score
                        )
                        # 使用新session保存学习数据
                        learning_db = AsyncSessionLocal()
                        try:
                            learning_db.add(learning_data)
                            await learning_db.commit()
                            if embedding:
                                logger.info("学习数据已保存（包含向量）", document_id=document_id)
                            else:
                                logger.info("学习数据已保存（向量未生成）", document_id=document_id)
                        finally:
                            await learning_db.close()
                    except Exception as e:
                        logger.warning("保存学习数据失败", error=str(e), document_id=document_id)
                    
                    await update_progress(task_id, 100, "处理完成", "completed")
                    logger.info("文档处理完成", 
                               document_id=document_id,
                               type=detected_type,
                               processing_time=processing_time)
                    
                except Exception as e:
                    logger.error("保存结果失败", document_id=document_id, error=str(e))
                    document.status = "failed"
                    await db.commit()
                    # 截断错误消息
                    error_msg = str(e)[:80]
                    await update_progress(task_id, 0, f"保存失败: {error_msg}", "failed")
                    
            except Exception as e:
                logger.error("文档处理任务异常", document_id=document_id, error=str(e))
                # #region agent log
                try:
                    # 在异常处理中，enabled_views可能未定义，使用current_enabled_views
                    log_data = {
                        "location": "document_processing.py:821",
                        "message": "outer exception handler",
                        "data": {
                            "document_id": document_id,
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "enabled_views_in_locals": "enabled_views" in locals(),
                            "enabled_views": enabled_views if "enabled_views" in locals() else "NOT_IN_LOCALS",
                            "current_enabled_views": current_enabled_views if "current_enabled_views" in locals() else "NOT_IN_LOCALS",
                            "_captured_enabled_views": _captured_enabled_views if "_captured_enabled_views" in locals() else "NOT_IN_LOCALS"
                        },
                        "timestamp": int(datetime.now().timestamp() * 1000),
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "E"
                    }
                    log_path = os.getenv("DEBUG_LOG_PATH", "/app/.cursor/debug.log")
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps(log_data, ensure_ascii=False) + "\n")
                except Exception as log_err:
                    # 如果日志写入失败，尝试记录到标准日志
                    logger.error("写入调试日志失败", error=str(log_err))
                # #endregion
                try:
                    # 截断错误消息
                    error_msg = str(e)[:80]
                    await update_progress(task_id, 0, f"任务异常: {error_msg}", "failed")
                except:
                    pass  # 如果更新进度也失败，忽略
        finally:
            await db.close()
    
    # 运行异步处理
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    loop.run_until_complete(_process())


@celery_app.task(bind=True, name="app.tasks.document_processing.process_secondary_views")
def process_secondary_views_task(
    self, 
    document_id: str, 
    secondary_views: list, 
    content: str, 
    segments_json: str,
    task_id: Optional[str] = None
):
    """
    异步处理次视角的后台任务
    
    在主视角处理完成后，滞后处理次视角，不阻塞主任务返回
    
    Args:
        document_id: 文档ID
        secondary_views: 次视角列表
        content: 预处理后的内容
        segments_json: 段落切分结果的JSON字符串
        task_id: 主任务ID（用于进度更新和流式生成）
    """
    import json
    import nest_asyncio
    
    # 允许嵌套事件循环
    nest_asyncio.apply()
    
    async def _process():
        db = AsyncSessionLocal()
        try:
            # 解析segments
            segments = json.loads(segments_json) if segments_json else []
            
            # 更新进度：开始处理次视角
            if task_id:
                await update_progress(
                    task_id, 
                    85, 
                    f"正在异步生成其他视角（{', '.join(secondary_views)}）...", 
                    "running"
                )
            
            # 逐个处理次视角（使用独立的session）
            for view in secondary_views:
                try:
                    logger.info(
                        "开始处理次视角",
                        document_id=document_id,
                        view=view,
                        task_id=task_id
                    )
                    
                    # 处理单个次视角
                    result = await process_view_independently(
                        document_id=document_id,
                        view=view,
                        content=content,
                        segments=segments,
                        is_primary=False,
                        db=None,  # 创建独立session
                        progress_callback=None,
                        task_id=task_id  # 传递task_id用于流式生成
                    )
                    
                    if result:
                        logger.info(
                            "次视角处理完成",
                            document_id=document_id,
                            view=view,
                            processing_time=result.get('processing_time')
                        )
                        
                        # 更新进度（可选）
                        if task_id:
                            await update_progress(
                                task_id,
                                90,
                                f"视角 {view} 生成完成",
                                "running"
                            )
                    else:
                        logger.warning(
                            "次视角处理失败",
                            document_id=document_id,
                            view=view
                        )
                        
                except Exception as e:
                    logger.error(
                        "次视角处理异常",
                        document_id=document_id,
                        view=view,
                        error=str(e),
                        error_type=type(e).__name__
                    )
                    # 继续处理其他次视角，不中断
            
            # 所有次视角处理完成
            if task_id:
                await update_progress(
                    task_id,
                    95,
                    "所有视角生成完成",
                    "running"
                )
            
            logger.info(
                "次视角后台处理任务完成",
                document_id=document_id,
                secondary_views=secondary_views
            )
            
        except Exception as e:
            logger.error(
                "次视角后台处理任务异常",
                document_id=document_id,
                error=str(e),
                error_type=type(e).__name__
            )
        finally:
            await db.close()
    
    # 运行异步处理
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    loop.run_until_complete(_process())

