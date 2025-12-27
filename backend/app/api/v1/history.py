"""
历史记录API
"""
from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from datetime import datetime
from typing import Optional
import structlog

from app.core.database import get_db
from app.models.document import Document
from app.models.processing_result import ProcessingResult
from app.schemas.document import DocumentHistoryResponse, DocumentHistoryItem

logger = structlog.get_logger()
router = APIRouter(prefix="/documents", tags=["history"])


@router.get("/history", response_model=DocumentHistoryResponse)
async def get_document_history(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    document_type: Optional[str] = Query(None, description="文档类型筛选"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    search: Optional[str] = Query(None, description="文件名模糊搜索"),
    db: AsyncSession = Depends(get_db)
):
    """获取处理历史记录列表"""
    import asyncio
    try:
        # 设置查询超时，避免被其他操作阻塞
        try:
            result = await asyncio.wait_for(
                _fetch_history_data(page, page_size, document_type, start_date, end_date, search, db),
                timeout=10.0  # 10秒超时
            )
            return result
        except asyncio.TimeoutError:
            logger.error("历史记录查询超时", page=page, page_size=page_size)
            raise HTTPException(
                status_code=500,
                detail="查询超时，请稍后重试"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("获取历史记录失败", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"获取历史记录失败: {str(e)}"
        )


async def _fetch_history_data(
    page: int,
    page_size: int,
    document_type: Optional[str],
    start_date: Optional[str],
    end_date: Optional[str],
    search: Optional[str],
    db: AsyncSession
) -> DocumentHistoryResponse:
    """获取历史记录数据（内部函数）"""
    # 构建查询条件
    conditions = []
        
    if document_type:
        # 需要通过processing_results关联查询
        subquery = select(ProcessingResult.document_id).where(
            ProcessingResult.document_type == document_type
        )
        conditions.append(Document.id.in_(subquery))
    
    if start_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            conditions.append(Document.upload_time >= start)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="开始日期格式错误，请使用 YYYY-MM-DD 格式"
            )
    
    if end_date:
        try:
            end = datetime.strptime(end_date, "%Y-%m-%d")
            # 包含整天
            from datetime import timedelta
            end = end + timedelta(days=1)
            conditions.append(Document.upload_time < end)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="结束日期格式错误，请使用 YYYY-MM-DD 格式"
            )
    
    if search:
        # 文件名模糊搜索
        conditions.append(Document.filename.ilike(f"%{search}%"))
    
    # 查询总数
    count_query = select(func.count(Document.id))
    if conditions:
        count_query = count_query.where(and_(*conditions))
    
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()
    
    # 查询列表
    query = select(Document).order_by(Document.upload_time.desc())
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    documents = result.scalars().all()
    
    # 获取处理结果信息（批量查询，避免N+1问题）
    doc_ids = [doc.id for doc in documents]
    items = []
    
    if doc_ids:
        # 批量查询所有文档的处理结果（优先主视角）
        results_query = select(ProcessingResult).where(
            ProcessingResult.document_id.in_(doc_ids)
        ).order_by(
            ProcessingResult.document_id,
            ProcessingResult.is_primary.desc()  # 主视角优先
        )
        results = await db.execute(results_query)
        processing_results = results.scalars().all()
        
        # 构建文档ID到处理结果的映射（每个文档只取第一个，优先主视角）
        doc_result_map = {}
        for pr in processing_results:
            if pr.document_id not in doc_result_map:
                doc_result_map[pr.document_id] = pr
        
        # 构建历史记录项
        for doc in documents:
            processing_result = doc_result_map.get(doc.id)
            items.append(DocumentHistoryItem(
                document_id=str(doc.id),
                filename=doc.filename,
                file_type=doc.file_type,
                document_type=processing_result.document_type if processing_result else None,
                status=doc.status,
                upload_time=doc.upload_time,
                processing_time=processing_result.processing_time if processing_result else None
            ))
    else:
        # 如果没有文档，返回空列表
        items = []
    
    return DocumentHistoryResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items
    )

