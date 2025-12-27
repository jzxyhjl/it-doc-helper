"""
向后兼容性处理工具
"""
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.services.view_registry import ViewRegistry
from app.models.processing_result import ProcessingResult
from app.models.document_type import DocumentType
from app.models.document import Document

logger = structlog.get_logger()


class BackwardCompatHelper:
    """
    向后兼容性处理辅助类
    
    用于处理历史数据和旧API调用
    """
    
    @staticmethod
    def get_view_from_type(document_type: str) -> str:
        """
        从类型推断视角（向后兼容）
        
        Args:
            document_type: 文档类型（technical/interview/architecture）
        
        Returns:
            视角名称（learning/qa/system）
        """
        return ViewRegistry.get_view_from_type(document_type)
    
    @staticmethod
    def enrich_result_with_views(result: Dict[str, Any]) -> Dict[str, Any]:
        """
        为结果添加视角信息（向后兼容）
        
        如果结果缺少view字段，从document_type推断
        
        Args:
            result: 处理结果字典
        
        Returns:
            添加了视角信息的结果字典
        """
        if not result.get('view') and result.get('document_type'):
            result['view'] = BackwardCompatHelper.get_view_from_type(result['document_type'])
            result['primary_view'] = result['view']
            result['enabled_views'] = [result['view']]
        return result
    
    @staticmethod
    async def migrate_processing_result(
        document_id: str,
        db: AsyncSession
    ) -> bool:
        """
        为历史处理结果填充view字段
        
        Args:
            document_id: 文档ID
            db: 数据库会话
        
        Returns:
            是否迁移成功
        
        注意：此函数不自动commit，由调用者负责事务管理
        """
        try:
            # 查询缺少view字段的处理结果
            result_query = await db.execute(
                select(ProcessingResult)
                .where(ProcessingResult.document_id == document_id)
                .where(ProcessingResult.view.is_(None))
            )
            results = result_query.scalars().all()
            
            if not results:
                return True  # 没有需要迁移的数据
            
            # 查询文档类型
            doc_type_query = await db.execute(
                select(DocumentType)
                .where(DocumentType.document_id == document_id)
            )
            doc_type = doc_type_query.scalar_one_or_none()
            
            # 为每个结果填充view字段
            for result in results:
                if doc_type and doc_type.primary_view:
                    # 使用主视角
                    result.view = doc_type.primary_view
                    result.is_primary = True
                elif result.document_type:
                    # 从document_type推断
                    result.view = BackwardCompatHelper.get_view_from_type(result.document_type)
                    result.is_primary = True
                else:
                    # 默认使用learning视角
                    result.view = 'learning'
                    result.is_primary = True
            
            # 不自动commit，由调用者负责
            logger.info("处理结果迁移完成", document_id=document_id, migrated_count=len(results))
            return True
        except Exception as e:
            logger.error("处理结果迁移失败", document_id=document_id, error=str(e))
            return False
    
    @staticmethod
    async def migrate_document_type(
        document_id: str,
        db: AsyncSession
    ) -> bool:
        """
        为历史文档类型填充视角字段
        
        Args:
            document_id: 文档ID
            db: 数据库会话
        
        Returns:
            是否迁移成功
        
        注意：此函数不自动commit，由调用者负责事务管理
        """
        try:
            # 查询缺少视角字段的文档类型
            doc_type_query = await db.execute(
                select(DocumentType)
                .where(DocumentType.document_id == document_id)
                .where(
                    (DocumentType.primary_view.is_(None)) |
                    (DocumentType.enabled_views.is_(None))
                )
            )
            doc_type = doc_type_query.scalar_one_or_none()
            
            if not doc_type:
                return True  # 没有需要迁移的数据
            
            # 从detected_type推断视角
            if not doc_type.primary_view and doc_type.detected_type:
                doc_type.primary_view = BackwardCompatHelper.get_view_from_type(doc_type.detected_type)
            
            if not doc_type.enabled_views:
                if doc_type.primary_view:
                    doc_type.enabled_views = [doc_type.primary_view]
                elif doc_type.detected_type:
                    view = BackwardCompatHelper.get_view_from_type(doc_type.detected_type)
                    doc_type.enabled_views = [view]
                else:
                    doc_type.enabled_views = ['learning']
            
            # 不自动commit，由调用者负责
            logger.info("文档类型迁移完成", document_id=document_id)
            return True
        except Exception as e:
            logger.error("文档类型迁移失败", document_id=document_id, error=str(e))
            return False
    
    @staticmethod
    async def create_multi_view_container_for_legacy(
        document_id: str,
        db: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """
        为历史结果创建多视角容器（向后兼容）
        
        Args:
            document_id: 文档ID
            db: 数据库会话
        
        Returns:
            多视角容器字典，如果无法创建则返回None
        """
        try:
            # 查询所有处理结果
            results_query = await db.execute(
                select(ProcessingResult)
                .where(ProcessingResult.document_id == document_id)
            )
            results = results_query.scalars().all()
            
            if not results:
                return None
            
            # 查询文档类型
            doc_type_query = await db.execute(
                select(DocumentType)
                .where(DocumentType.document_id == document_id)
            )
            doc_type = doc_type_query.scalar_one_or_none()
            
            # 构建多视角容器
            views = {}
            enabled_views = []
            primary_view = None
            
            for result in results:
                # 确保有view字段
                if not result.view and result.document_type:
                    result.view = BackwardCompatHelper.get_view_from_type(result.document_type)
                
                if result.view:
                    views[result.view] = result.result_data
                    enabled_views.append(result.view)
                    
                    if result.is_primary:
                        primary_view = result.view
            
            # 如果没有主视角，使用第一个
            if not primary_view and enabled_views:
                primary_view = enabled_views[0]
            
            # 如果没有主视角，从文档类型推断
            if not primary_view and doc_type:
                if doc_type.primary_view:
                    primary_view = doc_type.primary_view
                elif doc_type.detected_type:
                    primary_view = BackwardCompatHelper.get_view_from_type(doc_type.detected_type)
            
            if not primary_view:
                primary_view = 'learning'
            
            return {
                'views': views,
                'meta': {
                    'enabled_views': list(set(enabled_views)) if enabled_views else [primary_view],
                    'primary_view': primary_view,
                    'confidence': doc_type.detection_scores if doc_type and doc_type.detection_scores else {}
                }
            }
        except Exception as e:
            logger.error("创建多视角容器失败", document_id=document_id, error=str(e))
            return None
    
    @staticmethod
    def convert_old_api_params(params: Dict[str, Any]) -> Dict[str, Any]:
        """
        转换旧API参数为新格式
        
        Args:
            params: 旧API参数
        
        Returns:
            新API参数
        """
        new_params = params.copy()
        
        # 如果使用旧的document_type参数，转换为views
        if 'document_type' in new_params:
            old_type = new_params.pop('document_type')
            # 如果还没有views参数，则从document_type转换
            if 'views' not in new_params:
                view = BackwardCompatHelper.get_view_from_type(old_type)
                new_params['views'] = view
            # 如果已有views参数，则保留views，移除document_type（已pop）
        
        return new_params

