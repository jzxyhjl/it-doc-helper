"""
中间结果存储服务（视角无关）
"""
from typing import Optional, Dict, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.models.intermediate_result import DocumentIntermediateResult

logger = structlog.get_logger()


class IntermediateResultsService:
    """
    中间结果存储服务
    
    难点3解决方案：
    - 中间结果不包含任何视角相关的信息
    - 所有视角共享同一份中间结果
    - 切换视角时复用中间结果，仅重新组织AI处理
    """
    
    @staticmethod
    async def save_intermediate_results(
        document_id: str,
        content: str,
        preprocessed_content: Optional[str] = None,
        segments: Optional[List[Dict]] = None,
        metadata: Optional[Dict] = None,
        db: AsyncSession = None
    ) -> DocumentIntermediateResult:
        """
        保存中间结果（视角无关）
        
        Args:
            document_id: 文档ID
            content: 原始内容（视角无关）
            preprocessed_content: 预处理后的内容（视角无关）
            segments: 段落切分结果（视角无关）
            metadata: 元数据（视角无关）
            db: 数据库会话
        
        Returns:
            DocumentIntermediateResult: 保存的中间结果对象
        
        关键点：
        - 中间结果不包含任何视角相关的信息
        - 所有视角共享同一份中间结果
        - 切换视角时复用这些中间结果，仅重新组织AI处理
        """
        # 检查是否已存在中间结果
        existing_query = await db.execute(
            select(DocumentIntermediateResult)
            .where(DocumentIntermediateResult.document_id == document_id)
        )
        existing = existing_query.scalar_one_or_none()
        
        if existing:
            # 更新现有中间结果
            existing.content = content
            existing.preprocessed_content = preprocessed_content
            existing.segments = segments
            existing.metadata = metadata
            await db.flush()  # 使用flush而不是commit，避免关闭事务
            await db.refresh(existing)
            logger.info("更新中间结果", document_id=document_id)
            return existing
        else:
            # 创建新中间结果
            intermediate_result = DocumentIntermediateResult(
                document_id=document_id,
                content=content,  # 原始内容（视角无关）
                preprocessed_content=preprocessed_content,  # 预处理后内容（视角无关）
                segments=segments,  # 段落切分结果（视角无关）
                metadata=metadata  # 元数据（视角无关）
            )
            db.add(intermediate_result)
            await db.flush()  # 使用flush而不是commit，避免关闭事务
            await db.refresh(intermediate_result)
            logger.info("保存中间结果", document_id=document_id)
            return intermediate_result
    
    @staticmethod
    async def get_intermediate_results(
        document_id: str,
        db: AsyncSession
    ) -> Optional[DocumentIntermediateResult]:
        """
        获取中间结果（视角无关）
        
        Args:
            document_id: 文档ID
            db: 数据库会话
        
        Returns:
            DocumentIntermediateResult: 中间结果对象，如果不存在则返回None
        """
        query = await db.execute(
            select(DocumentIntermediateResult)
            .where(DocumentIntermediateResult.document_id == document_id)
        )
        return query.scalar_one_or_none()
    
    @staticmethod
    async def has_intermediate_results(
        document_id: str,
        db: AsyncSession
    ) -> bool:
        """
        检查是否存在中间结果
        
        Args:
            document_id: 文档ID
            db: 数据库会话
        
        Returns:
            bool: 如果存在中间结果返回True，否则返回False
        """
        result = await IntermediateResultsService.get_intermediate_results(document_id, db)
        return result is not None
    
    @staticmethod
    async def delete_intermediate_results(
        document_id: str,
        db: AsyncSession
    ) -> bool:
        """
        删除中间结果
        
        Args:
            document_id: 文档ID
            db: 数据库会话
        
        Returns:
            bool: 如果删除成功返回True，否则返回False
        """
        query = await db.execute(
            select(DocumentIntermediateResult)
            .where(DocumentIntermediateResult.document_id == document_id)
        )
        result = query.scalar_one_or_none()
        
        if result:
            await db.delete(result)
            await db.flush()  # 使用flush而不是commit，避免关闭事务
            logger.info("删除中间结果", document_id=document_id)
            return True
        else:
            logger.warning("中间结果不存在", document_id=document_id)
            return False

