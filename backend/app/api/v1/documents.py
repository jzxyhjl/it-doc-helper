"""
文档管理API
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
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
    SimilarDocumentItem
)
from app.tasks.document_processing import process_document_task

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
    
    # 1. 删除处理结果
    result_query = await db.execute(
        select(ProcessingResult).where(ProcessingResult.document_id == doc_id)
    )
    processing_result = result_query.scalar_one_or_none()
    if processing_result:
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
    
    # 4. 删除系统学习数据（可能有多个）
    learning_data_query = await db.execute(
        select(SystemLearningData).where(SystemLearningData.document_id == doc_id)
    )
    learning_data_list = learning_data_query.scalars().all()
    for learning_data in learning_data_list:
        await db.delete(learning_data)
    
    # 提交关联数据删除
    await db.commit()
    
    # 5. 删除文件（如果需要）
    if delete_file and os.path.exists(document.file_path):
        try:
            os.remove(document.file_path)
        except Exception as e:
            logger.warning("删除文件失败", file_path=document.file_path, error=str(e))
    
    # 6. 最后删除文档记录
    await db.delete(document)
    await db.commit()
    
    logger.info("文档及其关联数据删除成功", document_id=str(doc_id), filename=document.filename)
    
    return document


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    上传文档
    
    - 支持格式：PDF、Word、PPT、Markdown、TXT
    - 文件大小限制：30MB
    - 如果上传同名文档，会自动覆盖旧文档
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
        
        # 异步启动处理任务
        process_document_task.delay(str(document.id), str(task.id))
        
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
    
    return DocumentProgressResponse(
        document_id=document_id,
        progress=task.progress,
        current_stage=task.current_stage,
        status=task.status
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
    
    # 根据文档类型选择审核方法
    if processing_result.document_type == "architecture":
        review_result = await reviewer.review_architecture_result(processing_result.result_data)
    elif processing_result.document_type == "technical":
        review_result = await reviewer.review_technical_result(processing_result.result_data)
    elif processing_result.document_type == "interview":
        review_result = await reviewer.review_interview_result(processing_result.result_data)
    else:
        # 默认使用架构文档的审核逻辑
        review_result = await reviewer.review_architecture_result(processing_result.result_data)
    
    return review_result


@router.get("/{document_id}/result")
async def get_document_result(
    document_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取文档处理结果"""
    from uuid import UUID
    from sqlalchemy import select
    from app.schemas.document import DocumentResultResponse
    
    try:
        doc_id = UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的文档ID格式"
        )
    
    result = await db.execute(
        select(ProcessingResult).where(ProcessingResult.document_id == doc_id)
    )
    processing_result = result.scalar_one_or_none()
    
    if not processing_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="处理结果不存在，文档可能还在处理中"
        )
    
    # 获取质量分数
    from app.models.system_learning_data import SystemLearningData
    learning_result = await db.execute(
        select(SystemLearningData)
        .where(SystemLearningData.document_id == doc_id)
        .limit(1)
    )
    learning_data = learning_result.scalar_one_or_none()
    quality_score = learning_data.quality_score if learning_data else None
    
    # 清理处理结果中的技术名词翻译
    from app.utils.result_cleaner import clean_processing_result
    cleaned_result = clean_processing_result(processing_result.result_data) if processing_result.result_data else None
    
    return DocumentResultResponse(
        document_id=document_id,
        document_type=processing_result.document_type,
        result=cleaned_result,
        processing_time=processing_result.processing_time,
        quality_score=quality_score,
        created_at=processing_result.created_at
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
