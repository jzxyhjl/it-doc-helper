"""
流式生成API
支持Server-Sent Events (SSE)推送流式内容
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, AsyncGenerator
import structlog
import json
import asyncio

from app.core.database import get_db
from app.models.processing_result import ProcessingResult
from app.models.document_type import DocumentType
from app.services.ai_service import get_ai_service
from app.services.view_registry import ViewRegistry

logger = structlog.get_logger()
router = APIRouter(prefix="/streaming", tags=["streaming"])


@router.get("/{document_id}/generate-text")
async def stream_text_generation(
    document_id: str,
    prompt: str = Query(..., description="提示词"),
    system_prompt: Optional[str] = Query(None, description="系统提示词"),
    view: Optional[str] = Query(None, description="视角名称（可选）"),
    db: AsyncSession = Depends(get_db)
):
    """
    流式生成文本（SSE）
    
    用于实时推送AI生成的文本内容，类似deepseek-chat的逐字输出
    
    Args:
        document_id: 文档ID
        prompt: 用户提示词
        system_prompt: 系统提示词（可选）
        view: 视角名称（可选，用于上下文）
    
    Returns:
        Server-Sent Events流
    """
    from uuid import UUID
    
    try:
        doc_id = UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="无效的文档ID格式"
        )
    
    async def generate_stream() -> AsyncGenerator[str, None]:
        """生成SSE流"""
        try:
            # 获取AI服务
            ai_service = get_ai_service()
            
            # 构建消息
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            # 发送开始事件
            yield f"data: {json.dumps({'type': 'start'})}\n\n"
            
            # 流式生成文本
            full_content = ""
            async for chunk in ai_service.chat_completion_stream(
                messages=messages,
                model="deepseek-chat",
                temperature=0.7,
                document_id=document_id
            ):
                full_content += chunk
                # 发送文本块
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
            
            # 发送完成事件
            yield f"data: {json.dumps({'type': 'done', 'full_content': full_content})}\n\n"
            
        except Exception as e:
            logger.error("流式生成失败", document_id=document_id, error=str(e))
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # 禁用Nginx缓冲
        }
    )

