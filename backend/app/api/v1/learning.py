"""
学习相关API
- 学习路径跟踪
- 学习数据分析
- 处理模式学习
"""
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime
import structlog

from app.core.database import get_db
from app.services.learning_path_generator import get_learning_path_generator
from app.services.learning_analyzer import get_learning_analyzer
from app.services.recommendation_service import get_recommendation_service
from app.services.knowledge_graph_builder import get_knowledge_graph_builder
from app.services.tech_relationship_updater import get_tech_relationship_updater

logger = structlog.get_logger()
router = APIRouter(prefix="/learning", tags=["learning"])


@router.get("/path")
async def get_learning_path(
    db: AsyncSession = Depends(get_db)
):
    """
    获取学习路径
    
    返回基于用户上传文档类型的学习路径建议
    """
    try:
        generator = get_learning_path_generator()
        path_data = await generator.generate_learning_path(db)
        
        return path_data
        
    except Exception as e:
        logger.error("获取学习路径失败", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取学习路径失败: {str(e)}"
        )


@router.get("/statistics")
async def get_learning_statistics(
    db: AsyncSession = Depends(get_db)
):
    """
    获取学习统计数据
    
    返回处理文档总数、各类型文档数量分布、最近一段时间的处理趋势
    """
    from sqlalchemy import select, func
    from datetime import datetime, timedelta
    from app.models.document import Document
    from app.models.processing_result import ProcessingResult
    from app.models.system_learning_data import SystemLearningData
    
    try:
        # 1. 处理文档总数
        total_docs_result = await db.execute(
            select(func.count(Document.id))
        )
        total_documents = total_docs_result.scalar_one() or 0
        
        # 2. 各类型文档数量分布
        type_distribution_result = await db.execute(
            select(
                ProcessingResult.document_type,
                func.count(ProcessingResult.id).label('count')
            )
            .group_by(ProcessingResult.document_type)
        )
        type_distribution = [
            {
                "type": stat.document_type,
                "count": stat.count
            }
            for stat in type_distribution_result.fetchall()
        ]
        
        # 3. 最近一段时间的处理趋势（最近7天）
        seven_days_ago = datetime.now() - timedelta(days=7)
        recent_trend_result = await db.execute(
            select(
                func.date(Document.upload_time).label('date'),
                func.count(Document.id).label('count')
            )
            .where(Document.upload_time >= seven_days_ago)
            .group_by(func.date(Document.upload_time))
            .order_by(func.date(Document.upload_time))
        )
        recent_trend = [
            {
                "date": stat.date.isoformat() if stat.date else None,
                "count": stat.count
            }
            for stat in recent_trend_result.fetchall()
        ]
        
        # 4. 处理状态统计
        status_stats_result = await db.execute(
            select(
                Document.status,
                func.count(Document.id).label('count')
            )
            .group_by(Document.status)
        )
        status_statistics = [
            {
                "status": stat.status,
                "count": stat.count
            }
            for stat in status_stats_result.fetchall()
        ]
        
        # 5. 平均质量分数
        quality_stats_result = await db.execute(
            select(
                func.avg(SystemLearningData.quality_score).label('avg_quality'),
                func.count(SystemLearningData.id).label('total_with_quality')
            )
            .where(SystemLearningData.quality_score.isnot(None))
        )
        quality_stat = quality_stats_result.fetchone()
        
        return {
            "total_documents": total_documents,
            "type_distribution": type_distribution,
            "recent_trend": recent_trend,
            "status_statistics": status_statistics,
            "quality_statistics": {
                "average_quality_score": round(float(quality_stat.avg_quality or 0), 2) if quality_stat else None,
                "total_with_quality": quality_stat.total_with_quality if quality_stat else 0
            },
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error("获取学习统计失败", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取学习统计失败: {str(e)}"
        )


@router.get("/patterns")
async def get_processing_patterns(
    db: AsyncSession = Depends(get_db)
):
    """
    获取处理模式分析
    
    返回文档类型识别准确率、处理耗时分析、常见错误模式、优化建议
    """
    try:
        analyzer = get_learning_analyzer()
        patterns = await analyzer.analyze_processing_patterns(db)
        
        return patterns
        
    except Exception as e:
        logger.error("获取处理模式失败", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取处理模式失败: {str(e)}"
        )


@router.get("/recommendations")
async def get_recommendations(
    document_id: Optional[str] = None,
    limit: int = 10,
    document_type: Optional[str] = None,
    min_quality_score: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    获取智能推荐文档
    
    参数:
    - document_id: 当前文档ID（可选，用于基于当前文档推荐）
    - limit: 推荐数量（默认10）
    - document_type: 文档类型过滤（可选）
    - min_quality_score: 最低质量分数（可选，0-100）
    
    返回推荐文档列表，包含推荐分数和推荐理由
    """
    from app.schemas.document import RecommendationsResponse
    
    try:
        service = get_recommendation_service()
        recommendations = await service.recommend_documents(
            db=db,
            document_id=document_id,
            limit=limit,
            document_type=document_type,
            min_quality_score=min_quality_score
        )
        
        return recommendations
        
    except Exception as e:
        logger.error("获取推荐失败", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取推荐失败: {str(e)}"
        )


@router.get("/knowledge-graph")
async def get_knowledge_graph(
    similarity_threshold: float = 0.3,
    max_nodes: int = 50,
    document_type: Optional[str] = None,
    document_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    获取知识图谱数据
    
    参数:
    - similarity_threshold: 关联度阈值（0-1，默认0.3）
    - max_nodes: 最大节点数（默认50）
    - document_type: 文档类型过滤（可选）
    - document_id: 文档ID（可选，如果提供则只显示该文档中的技术名词及其关联关系）
    
    返回知识图谱数据，包含节点和边
    """
    try:
        builder = get_knowledge_graph_builder()
        graph_data = await builder.build_graph(
            db=db,
            similarity_threshold=similarity_threshold,
            max_nodes=max_nodes,
            document_type=document_type,
            document_id=document_id
        )
        
        return graph_data
        
    except Exception as e:
        logger.error("获取知识图谱失败", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取知识图谱失败: {str(e)}"
        )


@router.post("/tech-relationships/update")
async def update_tech_relationships(
    tech: Optional[str] = None,
    techs: Optional[List[str]] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    更新技术栈关联关系（通过 AI）
    
    参数:
    - tech: 单个技术名称（可选）
    - techs: 多个技术名称列表（可选）
    
    如果都不提供，则更新所有常见技术
    
    返回更新结果
    """
    try:
        updater = get_tech_relationship_updater()
        
        if tech:
            # 更新单个技术
            result = await updater.update_relationship_for_tech(tech)
            return {
                "message": f"技术 {tech} 的关联关系已更新",
                "updated": result,
                "updated_at": datetime.now().isoformat()
            }
        elif techs:
            # 批量更新
            result = await updater.batch_update_relationships(techs)
            return {
                "message": f"已更新 {len(result)} 个技术的关联关系",
                "updated": result,
                "updated_at": datetime.now().isoformat()
            }
        else:
            # 更新所有常见技术
            from app.services.tech_relationship_service import TechRelationshipService
            all_techs = list(TechRelationshipService.TECH_RELATIONSHIPS.keys())
            result = await updater.batch_update_relationships(all_techs[:20])  # 限制一次最多20个
            return {
                "message": f"已更新 {len(result)} 个技术的关联关系",
                "updated": result,
                "updated_at": datetime.now().isoformat(),
                "note": "一次最多更新20个技术，如需更新更多请分批调用"
            }
        
    except Exception as e:
        logger.error("更新技术关联关系失败", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新技术关联关系失败: {str(e)}"
        )


@router.get("/tech-relationships/{tech}")
async def get_tech_relationships(
    tech: str,
    use_ai: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """
    获取指定技术的关联关系
    
    参数:
    - tech: 技术名称
    - use_ai: 是否使用AI获取最新关联关系（默认False，使用静态定义）
    
    返回该技术的关联关系列表
    """
    try:
        from app.services.tech_relationship_service import TechRelationshipService
        
        if use_ai:
            updater = get_tech_relationship_updater()
            relationships = await updater.get_updated_relationships(tech)
        else:
            relationships = TechRelationshipService.get_related_technologies(tech, limit=15)
        
        return {
            "tech": tech,
            "relationships": [
                {"technology": rel[0], "strength": rel[1]} 
                for rel in relationships
            ],
            "count": len(relationships),
            "source": "ai" if use_ai else "static",
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error("获取技术关联关系失败", tech=tech, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取技术关联关系失败: {str(e)}"
        )


