"""
视角切换服务（复用中间结果）
"""
from typing import Dict, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.services.view_registry import ViewRegistry
from app.services.intermediate_results_service import IntermediateResultsService
from app.models.processing_result import ProcessingResult
from app.models.intermediate_result import DocumentIntermediateResult

logger = structlog.get_logger()


class ViewSwitcher:
    """
    视角切换服务
    
    难点3解决方案：
    - 切换视角 ≠ 重新理解世界
    - 切换视角 = 对同一理解的再组织
    - 复用视角无关的中间结果
    """
    
    @staticmethod
    async def switch_view(
        document_id: str,
        target_view: str,
        db: AsyncSession
    ) -> Dict:
        """
        快速切换视角（对同一理解的再组织）
        
        流程：
        1. 检查中间结果是否存在
        2. 如果存在，复用中间结果
        3. 仅重新组织AI处理（根据新视角）
        4. 返回结果（5秒内完成）
        
        Args:
            document_id: 文档ID
            target_view: 目标视角
        
        Returns:
            {
                'view': target_view,
                'result': result_data,
                'processing_time': elapsed_time,
                'used_intermediate_results': True
            }
        
        Raises:
            HTTPException: 如果中间结果不存在或视角无效
        """
        start_time = datetime.now()
        
        # 1. 验证视角是否已注册
        if target_view not in ViewRegistry.list_views():
            raise ValueError(f"无效的视角: {target_view}。支持的视角: {ViewRegistry.list_views()}")
        
        # 2. 检查目标视角的结果是否已存在
        existing_result_query = await db.execute(
            select(ProcessingResult)
            .where(ProcessingResult.document_id == document_id)
            .where(ProcessingResult.view == target_view)
        )
        existing_result = existing_result_query.scalar_one_or_none()
        
        if existing_result:
            # 如果结果已存在，直接返回
            elapsed_time = (datetime.now() - start_time).total_seconds()
            logger.info(
                "视角结果已存在，直接返回",
                document_id=document_id,
                view=target_view,
                elapsed_time=elapsed_time
            )
            return {
                'view': target_view,
                'result': existing_result.result_data,
                'processing_time': elapsed_time,
                'used_intermediate_results': False,
                'from_cache': True
            }
        
        # 3. 获取视角无关的中间结果（优先从缓存获取）
        from app.services.cache_service import CacheService
        from app.services.document_view_classifier import DocumentViewClassifier
        
        # 3.1 尝试从缓存获取中间结果（基于cache_key）
        # 首先需要获取document_types中的detection_scores来生成cache_key
        from app.models.document_type import DocumentType
        doc_type_query = await db.execute(
            select(DocumentType)
            .where(DocumentType.document_id == document_id)
        )
        doc_type = doc_type_query.scalar_one_or_none()
        
        content = None
        segments = []
        cached = False
        
        if doc_type and doc_type.detection_scores:
            # 生成cache_key
            cache_key = DocumentViewClassifier.generate_cache_key_from_scores(
                str(document_id), doc_type.detection_scores
            )
            # 尝试从缓存获取
            cached_intermediate = CacheService.get_intermediate_results(cache_key)
            if cached_intermediate:
                logger.info("从缓存获取中间结果", document_id=document_id, cache_key=cache_key)
                # 使用缓存的数据
                content = cached_intermediate.get('preprocessed_content') or cached_intermediate.get('content')
                segments = cached_intermediate.get('segments', [])
                cached = True
        
        # 3.2 如果缓存中没有，从数据库获取
        if not cached:
            intermediate = await IntermediateResultsService.get_intermediate_results(document_id, db)
            
            if not intermediate:
                raise ValueError(
                    "中间结果不存在，需要重新处理文档。"
                    "请先完成文档的初始处理。"
                )
            
            # 4. 复用中间结果（视角无关）
            content = intermediate.preprocessed_content or intermediate.content
            segments = intermediate.segments or []
        
        # 5. 仅重新组织AI处理（根据新视角）
        processor_class = ViewRegistry.get_processor(target_view)
        processor = processor_class()
        
        # 处理文档（复用中间结果）
        processing_start = datetime.now()
        type_mapping = ViewRegistry.get_type_mapping(target_view)
        
        # 如果是架构文档，可能需要进度回调（但切换时不需要）
        if type_mapping == 'architecture':
            result_data = await processor.process(content, progress_callback=None)
        else:
            result_data = await processor.process(content)
        
        processing_time = int((datetime.now() - processing_start).total_seconds())
        
        # 6. 保存新视角的结果（难点1：独立存储，不影响其他view）
        view_result = ProcessingResult(
            document_id=document_id,
            view=target_view,
            document_type=type_mapping,
            result_data=result_data,  # 保持原生结构
            is_primary=False,  # 切换的视角不是主视角
            processing_time=processing_time
        )
        db.add(view_result)
        await db.commit()  # 立即提交，确保该view结果稳定
        
        elapsed_time = (datetime.now() - start_time).total_seconds()
        
        # 7. 检查是否超过5秒
        if elapsed_time > 5:
            logger.warning(
                "视角切换耗时超过5秒",
                document_id=document_id,
                view=target_view,
                elapsed_time=elapsed_time,
                processing_time=processing_time
            )
        else:
            logger.info(
                "视角切换完成",
                document_id=document_id,
                view=target_view,
                elapsed_time=elapsed_time,
                processing_time=processing_time
            )
        
        return {
            'view': target_view,
            'result': result_data,
            'processing_time': elapsed_time,
            'used_intermediate_results': True,
            'from_cache': False
        }

