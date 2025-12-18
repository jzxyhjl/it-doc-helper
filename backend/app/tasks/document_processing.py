"""
文档处理任务
异步处理文档：提取内容、识别类型、处理文档
"""
import asyncio
from datetime import datetime
from uuid import UUID
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
from app.services.interview_processor import InterviewProcessor
from app.services.technical_processor import TechnicalProcessor
from app.services.architecture_processor import ArchitectureProcessor
from app.utils.processing_exception import (
    ProcessingException,
    ProcessingStatus,
    ErrorType,
    UserActionMapper
)
from app.services.document_size_validator import DocumentSizeValidator
from sqlalchemy import select

logger = structlog.get_logger()


async def update_progress(task_id: str, progress: int, stage: str, status: str = "running"):
    """更新任务进度（异步函数）"""
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
            r = redis.from_url(settings.REDIS_URL)
            r.publish(
                f"task_progress:{task_id}",
                f'{{"progress": {progress}, "stage": "{stage}", "status": "{status}"}}'
            )
    except Exception as e:
        logger.error("更新进度失败", task_id=task_id, error=str(e))
        await db.rollback()
    finally:
        await db.close()


@celery_app.task(bind=True, name="app.tasks.document_processing.process_document")
def process_document_task(self, document_id: str, task_id: str):
    """
    文档处理任务
    
    Args:
        document_id: 文档ID
        task_id: 处理任务ID
    """
    import asyncio
    import nest_asyncio
    
    # 允许嵌套事件循环（解决Celery中的asyncio问题）
    nest_asyncio.apply()
    
    async def _process():
        # 创建新的独立session
        db = AsyncSessionLocal()
        try:
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
                    content = await DocumentExtractor.extract(document.file_path, document.file_type)
                    document.content_extracted = content
                    await db.commit()
                    await update_progress(task_id, 15, "内容提取完成", "running")
                    logger.info("文档内容提取完成", document_id=document_id, content_length=len(content))
                    
                    # 验证内容长度和处理时间（在提取后）
                    from app.services.document_size_validator import DocumentSizeValidator
                    try:
                        # 先尝试识别文档类型（如果已识别）
                        detected_type = "technical"  # 默认类型，后续会被实际识别结果覆盖
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
                try:
                    preprocess_result = await TextPreprocessor.preprocess(
                        content=content,
                        file_type=document.file_type,
                        timeout=10.0
                    )
                    content = preprocess_result["cleaned_content"]
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
                
                # 步骤2: 识别文档类型 (20-40%)
                await update_progress(task_id, 30, "识别文档类型中...", "running")
                try:
                    classification = await DocumentClassifier.classify(
                        content=content,
                        api_key=settings.DEEPSEEK_API_KEY,
                        api_base=settings.DEEPSEEK_API_BASE
                    )
                    
                    detected_type = classification['type']
                    confidence = classification.get('confidence', 0.0)
                    method = classification.get('method', 'unknown')
                    
                    # 根据识别的文档类型，重新验证处理时间
                    from app.services.document_size_validator import DocumentSizeValidator
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
                            content_length=len(content),
                            estimated_time=estimated_time,
                            warnings=warnings
                        )
                    except ValueError as e:
                        # 如果重新验证失败（可能因为类型不同导致时间估算不同），拒绝处理
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
                    
                    # 保存类型识别结果
                    doc_type = DocumentType(
                        document_id=doc_uuid,
                        detected_type=detected_type,
                        confidence=confidence,
                        detection_method=method
                    )
                    db.add(doc_type)
                    await db.commit()
                    
                    await update_progress(task_id, 40, f"文档类型: {detected_type}", "running")
                    logger.info("文档类型识别完成", 
                               document_id=document_id, 
                               type=detected_type, 
                               confidence=confidence)
                except Exception as e:
                    logger.error("类型识别失败", document_id=document_id, error=str(e))
                    detected_type = "unknown"
                    # 继续处理，使用unknown类型
                
                # 步骤3: 根据类型处理文档 (40-90%)
                await update_progress(task_id, 50, "AI处理文档中...", "running")
                start_time = datetime.now()
                PROCESSING_TIMEOUT = 600  # 10分钟超时
                
                try:
                    if detected_type == "interview":
                        processor = InterviewProcessor
                        await update_progress(task_id, 60, "处理面试题文档...", "running")
                    elif detected_type == "technical":
                        processor = TechnicalProcessor
                        await update_progress(task_id, 60, "处理技术文档...", "running")
                    elif detected_type == "architecture":
                        processor = ArchitectureProcessor
                        # 创建进度回调函数
                        async def progress_callback(progress, stage):
                            await update_progress(task_id, progress, stage, "running")
                        await update_progress(task_id, 60, "处理架构文档（步骤1/5：提取配置流程）...", "running")
                    else:
                        # 未知类型，尝试自动判断
                        logger.warning("文档类型未知，尝试自动判断", document_id=document_id)
                        # 默认使用技术文档处理器
                        processor = TechnicalProcessor
                        detected_type = "technical"
                        await update_progress(task_id, 60, "自动判断为技术文档...", "running")
                    
                    # 调用处理器（带超时检测）
                    if detected_type == "architecture":
                        # 架构文档处理需要进度回调
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
                            await update_progress(task_id, progress, stage, "running")
                        result_data = await processor.process(content, progress_callback=progress_callback)
                    else:
                        result_data = await processor.process(content)
                    
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
                    
                    await update_progress(task_id, 80, "AI处理完成", "running")
                    
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
                
                # 步骤4: 保存处理结果 (90-100%)
                await update_progress(task_id, 90, "保存处理结果...", "running")
                try:
                    end_time = datetime.now()
                    processing_time = int((end_time - start_time).total_seconds())
                    
                    # 保存处理结果
                    processing_result = ProcessingResult(
                        document_id=doc_uuid,
                        document_type=detected_type,
                        result_data=result_data,
                        processing_time=processing_time
                    )
                    db.add(processing_result)
                    
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
                    
                    # 保存系统学习数据（基础版）
                    try:
                        # 生成文档向量（异步，不阻塞主流程，设置超时避免卡死）
                        embedding = None
                        try:
                            import asyncio
                            from app.services.embedding_service import get_embedding_service
                            embedding_service = get_embedding_service()
                            
                            # 设置向量生成超时（60秒），避免卡死整个任务
                            try:
                                embedding = await asyncio.wait_for(
                                    embedding_service.generate_embedding(content),
                                    timeout=60.0  # 60秒超时
                                )
                                if embedding:
                                    logger.info("文档向量生成成功", document_id=document_id)
                                else:
                                    logger.warning("文档向量生成失败，但继续处理", document_id=document_id)
                            except asyncio.TimeoutError:
                                logger.warning("向量生成超时（60秒），跳过向量生成，继续处理", document_id=document_id)
                            except Exception as e:
                                logger.warning("向量生成异常，但继续处理", error=str(e), document_id=document_id)
                        except Exception as e:
                            logger.warning("向量生成服务初始化失败，但继续处理", error=str(e), document_id=document_id)
                        
                        # 评估处理结果质量
                        quality_score = None
                        try:
                            from app.services.quality_assessor import get_quality_assessor
                            quality_assessor = get_quality_assessor()
                            quality_score = await quality_assessor.assess_quality(detected_type, result_data)
                            logger.info("质量评估完成", document_id=document_id, quality_score=quality_score)
                        except Exception as e:
                            logger.warning("质量评估异常，但继续处理", error=str(e), document_id=document_id)
                        
                        learning_data = SystemLearningData(
                            document_id=doc_uuid,
                            content_summary=content[:500] if len(content) > 500 else content,
                            embedding=embedding,  # 添加向量字段
                            document_type=detected_type,
                            processing_result_summary=str(result_data)[:500] if result_data else None,
                            processing_time=processing_time,
                            quality_score=quality_score  # 添加质量分数
                        )
                        db.add(learning_data)
                    except Exception as e:
                        logger.warning("保存学习数据失败", error=str(e))
                    
                    await db.commit()
                    
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

