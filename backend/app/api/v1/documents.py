"""
文档管理API
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import structlog
import uuid
import os
import time
import json

from app.core.database import get_db, AsyncSessionLocal
from sqlalchemy import select
from app.core.config import settings
from app.models.document import Document
from app.models.processing_task import ProcessingTask
from app.models.processing_result import ProcessingResult
from app.utils.file_utils import save_upload_file
from app.schemas.document import (
    DocumentResponse, 
    DocumentUploadResponse, 
    DocumentProgressResponse,
    DocumentResultResponse,
    SimilarDocumentsResponse,
    SimilarDocumentItem,
    ViewRecommendationResponse,
    MultiViewResultResponse,
    ViewsResultResponse,
    ViewsStatusResponse,
    ViewStatusItem
)
from app.tasks.document_processing import process_document_task
from app.services.view_switcher import ViewSwitcher
from app.services.document_view_classifier import DocumentViewClassifier
from app.services.multi_view_container import MultiViewOutputContainer
from app.services.view_registry import ViewRegistry
from app.models.document_type import DocumentType
from app.models.intermediate_result import DocumentIntermediateResult

logger = structlog.get_logger()
router = APIRouter(prefix="/documents", tags=["documents"])


async def delete_document_and_related_data(
    doc_id: uuid.UUID,
    db: AsyncSession,
    delete_file: bool = True
) -> Optional[Document]:
    """
    删除文档及其所有关联数据（辅助函数）
    
    Args:
        doc_id: 文档ID
        db: 数据库会话
        delete_file: 是否删除文件系统中的文件
    
    Returns:
        被删除的文档对象，如果不存在则返回None
    """
    from sqlalchemy import select
    from app.models.document_type import DocumentType
    from app.models.system_learning_data import SystemLearningData
    
    # 获取文档
    result = await db.execute(select(Document).where(Document.id == doc_id))
    document = result.scalar_one_or_none()
    
    if not document:
        return None
    
    # 删除关联数据（按顺序删除，避免外键约束错误）
    
    # 1. 删除处理结果（可能有多个视角）
    result_query = await db.execute(
        select(ProcessingResult).where(ProcessingResult.document_id == doc_id)
    )
    processing_results = result_query.scalars().all()
    for processing_result in processing_results:
        await db.delete(processing_result)
    
    # 2. 删除处理任务（可能有多个）
    task_query = await db.execute(
        select(ProcessingTask).where(ProcessingTask.document_id == doc_id)
    )
    processing_tasks = task_query.scalars().all()
    for task in processing_tasks:
        await db.delete(task)
    
    # 3. 删除文档类型记录
    doc_type_query = await db.execute(
        select(DocumentType).where(DocumentType.document_id == doc_id)
    )
    doc_types = doc_type_query.scalars().all()
    for doc_type in doc_types:
        await db.delete(doc_type)
    
    # 4. 删除中间结果
    from app.models.intermediate_result import DocumentIntermediateResult
    intermediate_query = await db.execute(
        select(DocumentIntermediateResult).where(DocumentIntermediateResult.document_id == doc_id)
    )
    intermediate_result = intermediate_query.scalar_one_or_none()
    if intermediate_result:
        await db.delete(intermediate_result)
    
    # 5. 删除系统学习数据（可能有多个）
    learning_data_query = await db.execute(
        select(SystemLearningData).where(SystemLearningData.document_id == doc_id)
    )
    learning_data_list = learning_data_query.scalars().all()
    for learning_data in learning_data_list:
        await db.delete(learning_data)
    
    # 提交关联数据删除
    await db.commit()
    
    # 6. 删除文件（如果需要）
    if delete_file and os.path.exists(document.file_path):
        try:
            os.remove(document.file_path)
        except Exception as e:
            logger.warning("删除文件失败", file_path=document.file_path, error=str(e))
    
    # 7. 最后删除文档记录
    await db.delete(document)
    await db.commit()
    
    logger.info("文档及其关联数据删除成功", document_id=str(doc_id), filename=document.filename)
    
    return document


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    views: Optional[str] = Query(None, description="启用的视角列表（逗号分隔，如：learning,system）。如果未指定，系统将自动推荐"),
    db: AsyncSession = Depends(get_db)
):
    """
    上传文档
    
    - 支持格式：PDF、Word、PPT、Markdown、TXT
    - 文件大小限制：15MB
    - 如果上传同名文档，会自动覆盖旧文档
    - views参数：可选，指定要启用的视角（learning/qa/system），多个视角用逗号分隔。如果未指定，系统将根据文档内容自动推荐
    """
    from sqlalchemy import select
    
    # #region agent log
    try:
        log_data = {"location": "documents.py:113", "message": "upload_document entry", "data": {"filename": file.filename, "content_type": file.content_type}, "timestamp": int(time.time() * 1000), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "H"}
        log_path = os.getenv("DEBUG_LOG_PATH", "/app/.cursor/debug.log")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_data, ensure_ascii=False) + "\n")
    except Exception:
        pass  # 忽略日志写入错误，不影响主流程
    # #endregion
    
    try:
        # #region agent log
        try:
            log_data = {"location": "documents.py:127", "message": "Before file validation", "data": {"filename": file.filename}, "timestamp": int(time.time() * 1000), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "I"}
            log_path = os.getenv("DEBUG_LOG_PATH", "/app/.cursor/debug.log")
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_data, ensure_ascii=False) + "\n")
        except Exception:
            pass
        # #endregion
        
        # 验证文件类型
        file_ext = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
        allowed_exts = settings.get_allowed_extensions()
        
        # 特殊处理：.doc 格式提供友好提示
        if file_ext == 'doc':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "系统暂不支持 .doc 格式（旧版 Word 文档）。"
                    "请使用 Microsoft Word 或 LibreOffice 将文件另存为 .docx 格式后重新上传。"
                    f"支持的类型: {', '.join(allowed_exts)}"
                )
            )
        
        if file_ext not in allowed_exts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的文件类型: {file_ext}。支持的类型: {', '.join(allowed_exts)}"
            )
        
        # 检测同名文档
        existing_doc_query = await db.execute(
            select(Document).where(Document.filename == file.filename)
        )
        existing_document = existing_doc_query.scalar_one_or_none()
        
        message = None
        if existing_document:
            # 删除旧文档及其所有关联数据
            logger.info("检测到同名文档，准备覆盖", 
                       old_document_id=str(existing_document.id),
                       filename=file.filename)
            
            deleted_doc = await delete_document_and_related_data(
                doc_id=existing_document.id,
                db=db,
                delete_file=True
            )
            
            if deleted_doc:
                message = f"已覆盖同名文档：{file.filename}"
                logger.info("同名文档已删除", 
                           old_document_id=str(existing_document.id),
                           filename=file.filename)
            else:
                logger.warning("同名文档删除失败，但继续上传", 
                              old_document_id=str(existing_document.id),
                              filename=file.filename)
        
        # #region agent log
        try:
            log_data = {"location": "documents.py:177", "message": "Before reading file content", "data": {"filename": file.filename}, "timestamp": int(time.time() * 1000), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "J"}
            log_path = os.getenv("DEBUG_LOG_PATH", "/app/.cursor/debug.log")
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_data, ensure_ascii=False) + "\n")
        except Exception:
            pass
        # #endregion
        
        # 先读取文件内容以获取大小（不保存）
        file_content = await file.read()
        file_size = len(file_content)
        
        # #region agent log
        try:
            log_data = {"location": "documents.py:180", "message": "After reading file content", "data": {"filename": file.filename, "file_size": file_size}, "timestamp": int(time.time() * 1000), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "K"}
            log_path = os.getenv("DEBUG_LOG_PATH", "/app/.cursor/debug.log")
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_data, ensure_ascii=False) + "\n")
        except Exception:
            pass
        # #endregion
        
        # 验证文件大小
        from app.services.document_size_validator import DocumentSizeValidator
        try:
            size_validation = DocumentSizeValidator.validate_file_size(file_size)
            warnings = size_validation.get("warnings", [])
            if warnings:
                logger.warning("文件大小警告", filename=file.filename, warnings=warnings)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        
        # 重置文件指针，准备保存
        await file.seek(0)
        
        # 保存文件
        file_path, _ = await save_upload_file(
            file=file,
            upload_dir=settings.UPLOAD_DIR,
            max_size=settings.UPLOAD_MAX_SIZE,
            allowed_extensions=settings.get_allowed_extensions()
        )
        
        # 创建文档记录
        document = Document(
            filename=file.filename,
            file_path=file_path,
            file_size=file_size,
            file_type=file_ext,
            status="pending"
        )
        
        db.add(document)
        await db.commit()
        await db.refresh(document)
        
        # 解析和验证views参数
        enabled_views = None
        if views:
            try:
                # 解析views参数（逗号分隔）
                view_list = [v.strip().lower() for v in views.split(',') if v.strip()]
                
                # 验证view是否已注册
                registered_views = ViewRegistry.list_views()
                invalid_views = [v for v in view_list if v not in registered_views]
                if invalid_views:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"无效的视角: {', '.join(invalid_views)}。已注册的视角: {', '.join(registered_views)}"
                    )
                
                enabled_views = view_list
                logger.info("用户指定了视角", document_id=str(document.id), enabled_views=enabled_views)
            except HTTPException:
                raise  # 重新抛出HTTPException
            except Exception as e:
                logger.error("解析views参数失败", error=str(e), views=views)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"解析views参数失败: {str(e)}"
                )
        
        # 创建处理任务
        task = ProcessingTask(
            document_id=document.id,
            task_type="process",
            status="pending",
            progress=0
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        
        # 异步启动处理任务（传递enabled_views参数）
        process_document_task.delay(str(document.id), str(task.id), enabled_views=enabled_views)
        
        logger.info("文档上传成功，任务已启动", 
                   document_id=str(document.id), 
                   task_id=str(task.id),
                   filename=file.filename,
                   is_overwrite=existing_document is not None)
        
        return DocumentUploadResponse(
            document_id=str(document.id),
            task_id=str(task.id),
            filename=document.filename,
            file_size=document.file_size,
            file_type=document.file_type,
            status=document.status,
            upload_time=document.upload_time,
            message=message
        )
        
    except HTTPException:
        raise  # 重新抛出HTTPException，不要被Exception捕获
    except ValueError as e:
        logger.error("文件验证失败", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # #region agent log
        try:
            import traceback
            log_data = {"location": "documents.py:255", "message": "Exception caught", "data": {"error": str(e), "error_type": type(e).__name__, "traceback": traceback.format_exc()[:500]}, "timestamp": int(time.time() * 1000), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "L"}
            log_path = os.getenv("DEBUG_LOG_PATH", "/app/.cursor/debug.log")
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_data, ensure_ascii=False) + "\n")
        except Exception:
            pass
        # #endregion
        logger.error("文档上传失败", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文档上传失败: {str(e)}"
        )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取文档信息"""
    from uuid import UUID
    
    try:
        doc_id = UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的文档ID格式"
        )
    
    from sqlalchemy import select
    result = await db.execute(select(Document).where(Document.id == doc_id))
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在"
        )
    
    return DocumentResponse(
        document_id=str(document.id),
        filename=document.filename,
        file_size=document.file_size,
        file_type=document.file_type,
        status=document.status,
        upload_time=document.upload_time,
        created_at=document.created_at,
        updated_at=document.updated_at
    )


@router.get("/{document_id}/progress", response_model=DocumentProgressResponse)
async def get_document_progress(
    document_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取文档处理进度"""
    from uuid import UUID
    from sqlalchemy import select
    
    try:
        doc_id = UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的文档ID格式"
        )
    
    # 获取最新的处理任务
    result = await db.execute(
        select(ProcessingTask)
        .where(ProcessingTask.document_id == doc_id)
        .order_by(ProcessingTask.created_at.desc())
        .limit(1)
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="处理任务不存在"
        )
    
    # 获取视角信息（如果已检测）
    enabled_views = None
    primary_view = None
    doc_type_result = await db.execute(
        select(DocumentType)
        .where(DocumentType.document_id == doc_id)
    )
    doc_type = doc_type_result.scalar_one_or_none()
    if doc_type:
        enabled_views = doc_type.enabled_views or []
        primary_view = doc_type.primary_view
    
    return DocumentProgressResponse(
        document_id=document_id,
        progress=task.progress,
        current_stage=task.current_stage,
        status=task.status,
        enabled_views=enabled_views,
        primary_view=primary_view,
        task_id=str(task.id)  # 添加task_id用于WebSocket连接
    )


@router.post("/{document_id}/review")
async def review_document_result(
    document_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    审核文档处理结果的内容质量
    
    使用 DeepSeek AI 审核生成结果的语言描述是否完整、有逻辑，不是胡言乱语。
    返回详细的审核报告，包括评分、问题列表和改进建议。
    """
    from uuid import UUID
    from app.services.content_reviewer import get_content_reviewer
    
    try:
        doc_id = UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的文档ID格式"
        )
    
    # 获取处理结果
    result = await db.execute(
        select(ProcessingResult)
        .where(ProcessingResult.document_id == doc_id)
    )
    processing_result = result.scalar_one_or_none()
    
    if not processing_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="处理结果不存在"
        )
    
    # 审核内容
    reviewer = get_content_reviewer()
    
    # 根据文档类型选择审核方法（使用ViewRegistry获取类型映射，保持向后兼容）
    document_type = processing_result.document_type
    # 兼容处理：如果document_type是view名称，转换为类型
    if document_type in ViewRegistry.TYPE_TO_VIEW_MAP.values():
        document_type = ViewRegistry.get_type_mapping(document_type)
    
    if document_type == "architecture":
        review_result = await reviewer.review_architecture_result(processing_result.result_data)
    elif document_type == "technical":
        review_result = await reviewer.review_technical_result(processing_result.result_data)
    elif document_type == "interview":
        review_result = await reviewer.review_interview_result(processing_result.result_data)
    else:
        # 默认使用架构文档的审核逻辑
        review_result = await reviewer.review_architecture_result(processing_result.result_data)
    
    return review_result


@router.post("/{document_id}/recommend-views", response_model=ViewRecommendationResponse)
async def recommend_views(
    document_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    推荐文档处理视角（主次视角）
    
    返回：
    - primary_view: 主视角（用于UI初始状态和算力分配）
    - enabled_views: 启用的视角列表
    - detection_scores: 系统检测的特征得分（用于缓存key）
    - cache_key: 基于检测得分生成的缓存key
    - type_mapping: 向后兼容的类型映射
    - method: 推荐方法（rule/ai/user_specified）
    """
    from uuid import UUID
    
    try:
        doc_id = UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的文档ID格式"
        )
    
    # 1. 获取文档内容（或中间结果）
    intermediate = await db.execute(
        select(DocumentIntermediateResult)
        .where(DocumentIntermediateResult.document_id == doc_id)
    )
    intermediate_result = intermediate.scalar_one_or_none()
    
    if not intermediate_result:
        # 如果没有中间结果，尝试从文档获取内容
        doc_query = await db.execute(
            select(Document).where(Document.id == doc_id)
        )
        document = doc_query.scalar_one_or_none()
        
        if not document or not document.content_extracted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文档内容不存在，请先完成文档处理"
            )
        content = document.content_extracted
    else:
        content = intermediate_result.preprocessed_content or intermediate_result.content
    
    # 2. 系统检测特征得分（这是算力与存储的边界）- 难点2解决方案
    detection_scores = {
        'qa': DocumentViewClassifier.detect_qa_structure(content),
        'system': DocumentViewClassifier.detect_component_relationships(content),
        'learning': DocumentViewClassifier.detect_usage_flow(content)
    }
    
    # 3. 调用视角识别器推荐主次视角
    recommendation = await DocumentViewClassifier.recommend_views(
        content=content,
        api_key=settings.DEEPSEEK_API_KEY,
        api_base=settings.DEEPSEEK_API_BASE
    )
    
    # 4. 生成缓存key（基于检测得分，不基于推荐）- 难点2解决方案
    cache_key = DocumentViewClassifier.generate_cache_key_from_scores(
        document_id, detection_scores
    )
    
    # 5. 返回推荐结果（包含检测得分和缓存key）
    return ViewRecommendationResponse(
        primary_view=recommendation['primary_view'],
        enabled_views=recommendation['enabled_views'],
        detection_scores=detection_scores,  # 使用系统检测的得分，不是推荐结果中的
        cache_key=cache_key,
        type_mapping=recommendation.get('type_mapping'),
        method=recommendation.get('method', 'rule')
    )


@router.post("/{document_id}/switch-view")
async def switch_view(
    document_id: str,
    view: str = Query(..., description="目标视角（learning/qa/system）"),
    db: AsyncSession = Depends(get_db)
):
    """
    快速切换视角（复用中间结果）
    
    难点3解决方案：
    - 复用视角无关的中间结果
    - 仅重新组织AI处理
    - 5秒内完成
    
    Args:
        document_id: 文档ID
        view: 目标视角（learning/qa/system）
    """
    from uuid import UUID
    
    try:
        doc_id = UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的文档ID格式"
        )
    
    # 1. 验证view参数
    if view not in ViewRegistry.list_views():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的视角: {view}。支持的视角: {ViewRegistry.list_views()}"
        )
    
    # 2. 调用快速切换逻辑
    try:
        result = await ViewSwitcher.switch_view(
            document_id=doc_id,
            target_view=view,
            db=db
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("切换视角失败", document_id=document_id, view=view, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"切换视角失败: {str(e)}"
        )


@router.get("/{document_id}/views/status", response_model=ViewsStatusResponse)
async def get_views_status(
    document_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    获取各视角的处理状态（难点4解决方案）
    
    用于UI层轮询，显示"正在生成..."状态
    
    返回：
    - views_status: 各视角的状态（completed/processing/pending/failed）
    - primary_view: 主视角
    - enabled_views: 启用的视角列表
    """
    from uuid import UUID
    
    try:
        doc_id = UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的文档ID格式"
        )
    
    # 1. 查询所有view的处理状态
    results_query = await db.execute(
        select(ProcessingResult)
        .where(ProcessingResult.document_id == doc_id)
    )
    view_results = results_query.scalars().all()
    
    # 2. 构建已完成的view状态
    statuses = {}
    for result in view_results:
        # 检查结果是否有内容（非空且不是空字典）
        has_content = False
        if result.result_data:
            if isinstance(result.result_data, dict):
                # 检查字典是否有非空值
                has_content = len(result.result_data) > 0 and any(
                    v is not None and v != "" and (not isinstance(v, (list, dict)) or len(v) > 0)
                    for v in result.result_data.values()
                )
            else:
                # 非字典类型，只要有值就认为有内容
                has_content = True
        
        statuses[result.view] = ViewStatusItem(
            view=result.view,
            status='completed',
            ready=True,
            processing_time=result.processing_time,
            is_primary=result.is_primary,
            has_content=has_content
        )
    
    # 3. 查询推荐信息，确定哪些view应该存在
    doc_type_query = await db.execute(
        select(DocumentType)
        .where(DocumentType.document_id == doc_id)
    )
    doc_type = doc_type_query.scalar_one_or_none()
    
    enabled_views = []
    primary_view = None
    if doc_type:
        enabled_views = doc_type.enabled_views or []
        primary_view = doc_type.primary_view
    
    # 4. 检查处理任务状态，确定正在处理的view
    task_query = await db.execute(
        select(ProcessingTask)
        .where(ProcessingTask.document_id == doc_id)
        .where(ProcessingTask.status.in_(['pending', 'running']))
        .order_by(ProcessingTask.created_at.desc())
        .limit(1)
    )
    active_task = task_query.scalar_one_or_none()
    
    # 5. 标记未完成的view
    for view in enabled_views:
        if view not in statuses:
            # 如果有活跃的处理任务，标记为processing，否则标记为pending
            task_status = 'processing' if active_task and active_task.status == 'running' else 'pending'
            statuses[view] = ViewStatusItem(
                view=view,
                status=task_status,
                ready=False,
                processing_time=None,
                is_primary=(view == primary_view),
                has_content=False  # 未完成时肯定没有内容
            )
    
    # 6. 返回状态响应
    return ViewsStatusResponse(
        document_id=document_id,
        views_status={k: v for k, v in statuses.items()},
        primary_view=primary_view,
        enabled_views=enabled_views
    )


@router.get("/{document_id}/result")
async def get_document_result(
    document_id: str,
    view: Optional[str] = None,
    views: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    获取文档处理结果（多视角输出容器）
    
    关键点：
    - 用户可以选择任意视角，不受主视角限制（难点2）
    - 从容器中提取指定view的结果
    - 保持各view的原生结构
    
    Args:
        document_id: 文档ID
        view: 指定视角（可选，返回该视角的结果）
        views: 指定多个视角（可选，逗号分隔，返回多个视角的结果）
    """
    from uuid import UUID
    from sqlalchemy import select
    from app.schemas.document import DocumentResultResponse
    from fastapi import Query
    
    try:
        doc_id = UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的文档ID格式"
        )
    
    # 1. 查询多视角输出容器（从主视角结果中获取）
    doc_type_query = await db.execute(
        select(DocumentType)
        .where(DocumentType.document_id == doc_id)
    )
    doc_type = doc_type_query.scalar_one_or_none()
    
    # 向后兼容：如果缺少视角字段，尝试迁移
    if doc_type and (not doc_type.primary_view or not doc_type.enabled_views):
        from app.utils.backward_compat import BackwardCompatHelper
        await BackwardCompatHelper.migrate_document_type(document_id, db)
        await db.commit()  # 迁移后需要commit
        # 重新查询
        doc_type_query = await db.execute(
            select(DocumentType)
            .where(DocumentType.document_id == doc_id)
        )
        doc_type = doc_type_query.scalar_one_or_none()
    
    primary_view = None
    if doc_type and doc_type.primary_view:
        primary_view = doc_type.primary_view
    elif doc_type and doc_type.detected_type:
        # 向后兼容：从detected_type推断
        from app.utils.backward_compat import BackwardCompatHelper
        primary_view = BackwardCompatHelper.get_view_from_type(doc_type.detected_type)
    
    # 查询主视角结果（可能包含容器）
    if primary_view:
        primary_result_query = await db.execute(
            select(ProcessingResult)
            .where(ProcessingResult.document_id == doc_id)
            .where(ProcessingResult.view == primary_view)
        )
        primary_result = primary_result_query.scalar_one_or_none()
    else:
        primary_result = None
    
    # 2. 如果指定了view或views，从对应的结果中提取（用户可以选择任意视角，不受主视角限制 - 难点2）
    if views:
        # 指定多个views
        requested_views = [v.strip().lower() for v in views.split(',') if v.strip()]
        
        # 验证view是否已注册
        registered_views = ViewRegistry.list_views()
        invalid_views = [v for v in requested_views if v not in registered_views]
        if invalid_views:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的视角: {', '.join(invalid_views)}。支持的视角: {', '.join(registered_views)}"
            )
        
        results = {}
        for v in requested_views:
            view_result_query = await db.execute(
                select(ProcessingResult)
                .where(ProcessingResult.document_id == doc_id)
                .where(ProcessingResult.view == v)
            )
            view_result = view_result_query.scalar_one_or_none()
            
            if view_result:
                # 清理处理结果
                from app.utils.result_cleaner import clean_processing_result
                cleaned_result = clean_processing_result(view_result.result_data) if view_result.result_data else None
                results[v] = cleaned_result
        
        return ViewsResultResponse(
            document_id=document_id,
            requested_views=requested_views,
            results=results  # 保持原生结构
        )
    elif view:
        # 指定单个view
        if view not in ViewRegistry.list_views():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的视角: {view}。支持的视角: {ViewRegistry.list_views()}"
            )
        
        view_result_query = await db.execute(
            select(ProcessingResult)
            .where(ProcessingResult.document_id == doc_id)
            .where(ProcessingResult.view == view)
        )
        view_result = view_result_query.scalar_one_or_none()
        
        if not view_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"视角 {view} 的结果不存在，文档可能还在处理中"
            )
        
        # 清理处理结果
        from app.utils.result_cleaner import clean_processing_result
        cleaned_result = clean_processing_result(view_result.result_data) if view_result.result_data else None
        
        # 获取质量分数
        from app.models.system_learning_data import SystemLearningData
        learning_result = await db.execute(
            select(SystemLearningData)
            .where(SystemLearningData.document_id == doc_id)
            .limit(1)
        )
        learning_data = learning_result.scalar_one_or_none()
        quality_score = learning_data.quality_score if learning_data else None
        
        return DocumentResultResponse(
            document_id=document_id,
            document_type=view_result.document_type,
            result=cleaned_result,
            processing_time=view_result.processing_time,
            quality_score=quality_score,
            created_at=view_result.created_at
        )
    else:
        # 3. 如果不指定，返回完整多视角输出容器
        # 查询所有view的结果
        all_results_query = await db.execute(
            select(ProcessingResult)
            .where(ProcessingResult.document_id == doc_id)
        )
        all_view_results = all_results_query.scalars().all()
        
        # 向后兼容：如果结果缺少view字段，尝试迁移
        if all_view_results and any(r.view is None for r in all_view_results):
            from app.utils.backward_compat import BackwardCompatHelper
            await BackwardCompatHelper.migrate_processing_result(document_id, db)
            await db.commit()  # 迁移后需要commit
            # 重新查询
            all_results_query = await db.execute(
                select(ProcessingResult)
                .where(ProcessingResult.document_id == doc_id)
            )
            all_view_results = all_results_query.scalars().all()
        
        if not all_view_results:
            # 向后兼容：尝试为历史数据创建多视角容器
            from app.utils.backward_compat import BackwardCompatHelper
            container = await BackwardCompatHelper.create_multi_view_container_for_legacy(document_id, db)
            if container:
                return MultiViewResultResponse(
                    document_id=document_id,
                    views=container['views'],
                    meta=container['meta']
                )
            
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="处理结果不存在，文档可能还在处理中"
            )
        
        # 构建多视角容器
        views_data = {}
        for view_result in all_view_results:
            # 确保有view字段（向后兼容）
            if not view_result.view and view_result.document_type:
                from app.utils.backward_compat import BackwardCompatHelper
                view_result.view = BackwardCompatHelper.get_view_from_type(view_result.document_type)
            
            # 清理处理结果
            from app.utils.result_cleaner import clean_processing_result
            cleaned_result = clean_processing_result(view_result.result_data) if view_result.result_data else None
            views_data[view_result.view] = cleaned_result
        
        # 获取元数据
        enabled_views = doc_type.enabled_views if doc_type and doc_type.enabled_views else list(views_data.keys())
        detection_scores = doc_type.detection_scores if doc_type and doc_type.detection_scores else {}
        
        # 创建多视角输出容器
        container = MultiViewOutputContainer.create_container(
            views=views_data,
            enabled_views=enabled_views,
            confidence=detection_scores,
            primary_view=primary_view
        )
        
        return MultiViewResultResponse(
            document_id=document_id,
            views=container['views'],
            meta=container['meta']
        )


@router.get("/{document_id}/export")
async def export_document_result(
    document_id: str,
    view: Optional[str] = Query(None, description="视角名称（learning/qa/system），默认使用主视角"),
    format: str = Query("markdown", description="导出格式（目前仅支持markdown）"),
    db: AsyncSession = Depends(get_db)
):
    """
    导出文档处理结果为Markdown格式
    
    Args:
        document_id: 文档ID
        view: 视角名称（可选，默认使用主视角）
        format: 导出格式（目前仅支持markdown）
    
    Returns:
        Markdown格式的文本内容
    """
    from uuid import UUID
    from sqlalchemy import select
    from fastapi.responses import Response
    from app.services.result_exporter import ResultExporter
    from app.models.document_type import DocumentType
    
    try:
        doc_id = UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的文档ID格式"
        )
    
    # 获取文档信息
    doc_query = await db.execute(
        select(Document)
        .where(Document.id == doc_id)
    )
    document = doc_query.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在"
        )
    
    # 确定要导出的视角
    target_view = view
    if not target_view:
        # 获取主视角
        doc_type_query = await db.execute(
            select(DocumentType)
            .where(DocumentType.document_id == doc_id)
        )
        doc_type = doc_type_query.scalar_one_or_none()
        if doc_type and doc_type.primary_view:
            target_view = doc_type.primary_view
        else:
            # 如果没有主视角，使用第一个可用的视角
            result_query = await db.execute(
                select(ProcessingResult)
                .where(ProcessingResult.document_id == doc_id)
                .limit(1)
            )
            first_result = result_query.scalar_one_or_none()
            if first_result:
                target_view = first_result.view
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="处理结果不存在"
                )
    
    # 获取处理结果
    result_query = await db.execute(
        select(ProcessingResult)
        .where(ProcessingResult.document_id == doc_id)
        .where(ProcessingResult.view == target_view)
    )
    processing_result = result_query.scalar_one_or_none()
    
    if not processing_result or not processing_result.result_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"视角 '{target_view}' 的处理结果不存在"
        )
    
    # 导出为Markdown
    if format.lower() == "markdown":
        markdown_content = ResultExporter.export_to_markdown(
            result_data=processing_result.result_data,
            view=target_view,
            document_name=document.filename,
            document_id=document_id
        )
        
        # 返回Markdown文件
        return Response(
            content=markdown_content,
            media_type="text/markdown; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{document.filename or "result"}_{target_view}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md"'
            }
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的导出格式: {format}。目前仅支持 'markdown'"
        )


@router.get("/{document_id}/similar", response_model=SimilarDocumentsResponse)
async def get_similar_documents(
    document_id: str,
    limit: int = 5,
    threshold: Optional[float] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    获取相似文档列表
    
    - 基于向量相似度搜索相似文档
    - 使用pgvector的余弦相似度搜索
    - 返回Top-K相似文档（默认5个）
    - 可选相似度阈值过滤
    """
    from uuid import UUID
    from sqlalchemy import select, text
    from app.models.system_learning_data import SystemLearningData
    from app.models.document import Document
    
    try:
        doc_id = UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的文档ID格式"
        )
    
    # 验证参数
    if limit < 1 or limit > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="limit参数必须在1-20之间"
        )
    
    if threshold is not None and (threshold < 0.0 or threshold > 1.0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="threshold参数必须在0.0-1.0之间"
        )
    
    # 1. 获取目标文档的向量
    target_query = await db.execute(
        select(SystemLearningData)
        .where(SystemLearningData.document_id == doc_id)
        .where(SystemLearningData.embedding.isnot(None))
    )
    target_data = target_query.scalar_one_or_none()
    
    if not target_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在或尚未生成向量，无法搜索相似文档"
        )
    
    # 检查向量是否存在（pgvector返回的是数组，不能直接用于布尔判断）
    if target_data.embedding is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档向量不存在，无法搜索相似文档"
        )
    
    # 2. 使用pgvector的余弦相似度搜索
    # SQL: SELECT document_id, 1 - (embedding <=> $1) as similarity
    #      FROM system_learning_data
    #      WHERE document_id != $2 AND embedding IS NOT NULL
    #      ORDER BY embedding <=> $1
    #      LIMIT $3
    
    # 构建查询
    # 注意：pgvector的 <=> 操作符返回余弦距离（0-2），需要转换为相似度（0-1）
    # 相似度 = 1 - (距离 / 2) 或直接使用 1 - (embedding <=> target_embedding)
    # 但更准确的是：相似度 = 1 - (embedding <=> target_embedding) / 2
    
    # 使用原始SQL查询以利用pgvector的索引
    # 将向量转换为字符串格式（PostgreSQL数组格式）
    import numpy as np
    if isinstance(target_data.embedding, np.ndarray):
        target_embedding_list = target_data.embedding.tolist()
    else:
        target_embedding_list = list(target_data.embedding) if hasattr(target_data.embedding, '__iter__') else target_data.embedding
    
    # 转换为PostgreSQL数组格式的字符串: '[0.1, 0.2, ...]'
    target_embedding_str = '[' + ','.join(map(str, target_embedding_list)) + ']'
    
    # 使用CAST将字符串转换为vector类型
    query = text("""
        SELECT 
            sld.document_id,
            1 - (sld.embedding <=> CAST(:target_embedding AS vector)) as similarity,
            sld.content_summary,
            sld.document_type
        FROM system_learning_data sld
        WHERE sld.document_id != :target_document_id
          AND sld.embedding IS NOT NULL
        ORDER BY sld.embedding <=> CAST(:target_embedding AS vector)
        LIMIT :limit
    """)
    
    # 执行查询
    result = await db.execute(
        query,
        {
            "target_embedding": target_embedding_str,
            "target_document_id": doc_id,
            "limit": limit
        }
    )
    
    similar_records = result.fetchall()
    
    # 3. 应用相似度阈值过滤（如果指定）
    filtered_records = []
    for record in similar_records:
        similarity = float(record.similarity)
        if threshold is None or similarity >= threshold:
            filtered_records.append(record)
    
    # 4. 获取文档详细信息
    similar_items = []
    for record in filtered_records:
        doc_query = await db.execute(
            select(Document).where(Document.id == record.document_id)
        )
        document = doc_query.scalar_one_or_none()
        
        if document:
            similar_items.append(SimilarDocumentItem(
                document_id=str(record.document_id),
                filename=document.filename,
                file_type=document.file_type,
                document_type=record.document_type,
                similarity=float(record.similarity),
                content_summary=record.content_summary[:200] if record.content_summary else None,
                upload_time=document.upload_time
            ))
    
    logger.info("相似文档搜索完成",
               document_id=document_id,
               total_found=len(similar_records),
               filtered_count=len(similar_items),
               limit=limit,
               threshold=threshold)
    
    return SimilarDocumentsResponse(
        document_id=document_id,
        total=len(similar_items),
        limit=limit,
        threshold=threshold,
        items=similar_items
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(get_db)
):
    """删除文档"""
    from uuid import UUID
    
    try:
        doc_id = UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的文档ID格式"
        )
    
    # 使用辅助函数删除文档及其关联数据
    deleted_doc = await delete_document_and_related_data(
        doc_id=doc_id,
        db=db,
        delete_file=True
    )
    
    if not deleted_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在"
        )
    
    return None


@router.post("/batch-delete", status_code=status.HTTP_200_OK)
async def batch_delete_documents(
    document_ids: list[str],
    db: AsyncSession = Depends(get_db)
):
    """
    批量删除文档
    
    Args:
        document_ids: 文档ID列表
    
    Returns:
        删除结果统计
    """
    from uuid import UUID
    from pydantic import BaseModel
    
    class BatchDeleteResponse(BaseModel):
        success_count: int
        failed_count: int
        failed_ids: list[str]
    
    success_count = 0
    failed_count = 0
    failed_ids = []
    
    for document_id in document_ids:
        try:
            doc_id = UUID(document_id)
        except ValueError:
            failed_count += 1
            failed_ids.append(document_id)
            logger.warning("无效的文档ID格式", document_id=document_id)
            continue
        
        try:
            deleted_doc = await delete_document_and_related_data(
                doc_id=doc_id,
                db=db,
                delete_file=True
            )
            
            if deleted_doc:
                success_count += 1
            else:
                failed_count += 1
                failed_ids.append(document_id)
                logger.warning("文档不存在", document_id=document_id)
        except Exception as e:
            failed_count += 1
            failed_ids.append(document_id)
            logger.error("删除文档失败", document_id=document_id, error=str(e))
    
    return BatchDeleteResponse(
        success_count=success_count,
        failed_count=failed_count,
        failed_ids=failed_ids
    )
