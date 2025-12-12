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
    db: AsyncSession = Depends(get_db)
):
    """获取处理历史记录列表"""
    try:
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
        
        # 获取处理结果信息
        items = []
        for doc in documents:
            # 查询处理结果
            result_query = select(ProcessingResult).where(
                ProcessingResult.document_id == doc.id
            )
            result = await db.execute(result_query)
            processing_result = result.scalar_one_or_none()
            
            items.append(DocumentHistoryItem(
                document_id=str(doc.id),
                filename=doc.filename,
                file_type=doc.file_type,
                document_type=processing_result.document_type if processing_result else None,
                status=doc.status,
                upload_time=doc.upload_time,
                processing_time=processing_result.processing_time if processing_result else None
            ))
        
        return DocumentHistoryResponse(
            total=total,
            page=page,
            page_size=page_size,
            items=items
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("获取历史记录失败", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"获取历史记录失败: {str(e)}"
        )

