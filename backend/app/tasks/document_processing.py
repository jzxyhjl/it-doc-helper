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
from app.services.document_classifier import DocumentClassifier
from app.services.interview_processor import InterviewProcessor
from app.services.technical_processor import TechnicalProcessor
from app.services.architecture_processor import ArchitectureProcessor
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
                
                # 步骤1: 提取文档内容 (0-20%)
                await update_progress(task_id, 10, "提取文档内容中...", "running")
                try:
                    content = await DocumentExtractor.extract(document.file_path, document.file_type)
                    document.content_extracted = content
                    await db.commit()
                    await update_progress(task_id, 20, "内容提取完成", "running")
                    logger.info("文档内容提取完成", document_id=document_id, content_length=len(content))
                except Exception as e:
                    logger.error("内容提取失败", document_id=document_id, error=str(e))
                    document.status = "failed"
                    await db.commit()
                    await update_progress(task_id, 0, f"内容提取失败: {str(e)}", "failed")
                    return
                
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
                    
                    # 调用处理器
                    if detected_type == "architecture":
                        # 架构文档处理需要进度回调
                        async def progress_callback(progress, stage):
                            await update_progress(task_id, progress, stage, "running")
                        result_data = await processor.process(content, progress_callback=progress_callback)
                    else:
                        result_data = await processor.process(content)
                    await update_progress(task_id, 80, "AI处理完成", "running")
                    
                except Exception as e:
                    logger.error("文档处理失败", document_id=document_id, error=str(e))
                    document.status = "failed"
                    await db.commit()
                    # 截断错误消息
                    error_msg = str(e)[:80]
                    await update_progress(task_id, 0, f"处理失败: {error_msg}", "failed")
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
                        # 生成文档向量（异步，不阻塞主流程）
                        embedding = None
                        try:
                            from app.services.embedding_service import get_embedding_service
                            embedding_service = get_embedding_service()
                            embedding = await embedding_service.generate_embedding(content)
                            if embedding:
                                logger.info("文档向量生成成功", document_id=document_id)
                            else:
                                logger.warning("文档向量生成失败，但继续处理", document_id=document_id)
                        except Exception as e:
                            logger.warning("向量生成异常，但继续处理", error=str(e), document_id=document_id)
                        
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

