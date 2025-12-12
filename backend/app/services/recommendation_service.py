"""
智能推荐服务
- 基于向量相似度的增强推荐
- 结合文档类型、质量分数等元数据
- 支持个性化推荐策略
"""
from typing import Dict, List, Optional
from datetime import datetime
import structlog

logger = structlog.get_logger()


class RecommendationService:
    """智能推荐服务"""
    
    @staticmethod
    async def recommend_documents(
        db,
        document_id: Optional[str] = None,
        limit: int = 10,
        document_type: Optional[str] = None,
        min_quality_score: Optional[int] = None
    ) -> Dict:
        """
        推荐文档
        
        Args:
            db: 数据库会话
            document_id: 当前文档ID（可选，用于基于当前文档推荐）
            limit: 推荐数量
            document_type: 文档类型过滤（可选）
            min_quality_score: 最低质量分数（可选）
        
        Returns:
            推荐结果字典
        """
        from sqlalchemy import select, text, func
        from app.models.system_learning_data import SystemLearningData
        from app.models.document import Document
        
        logger.info("开始生成推荐", document_id=document_id, limit=limit)
        
        try:
            if document_id:
                # 只使用书籍推荐，不推荐本地文档
                book_recommendations = await RecommendationService._recommend_books(
                    db, document_id, limit
                )
                
                # 处理书籍推荐结果
                if isinstance(book_recommendations, Exception):
                    logger.warning("书籍推荐失败", error=str(book_recommendations))
                    recommendations = []
                else:
                    recommendations = book_recommendations or []
                
                logger.info("书籍推荐完成", 
                           books=len(recommendations),
                           total=len(recommendations))
            else:
                # 通用推荐（基于质量分数和类型）
                recommendations = await RecommendationService._recommend_general(
                    db, limit, document_type, min_quality_score
                )
            
            # 按推荐度（recommendation_score）降序排序，确保推荐度高的排在前面
            if recommendations:
                recommendations.sort(key=lambda x: x.get("recommendation_score", 0), reverse=True)
            
            result = {
                "recommendations": recommendations,
                "total": len(recommendations),
                "generated_at": datetime.now().isoformat()
            }
            
            logger.info("推荐生成完成", total=len(recommendations), 
                       local=len([r for r in recommendations if not r.get('is_book', False)]),
                       books=len([r for r in recommendations if r.get('is_book', False)]))
            return result
            
        except Exception as e:
            logger.error("推荐生成失败", error=str(e))
            return {
                "recommendations": [],
                "total": 0,
                "error": str(e),
                "generated_at": datetime.now().isoformat()
            }
    
    @staticmethod
    async def _recommend_by_document(
        db,
        document_id: str,
        limit: int,
        document_type: Optional[str],
        min_quality_score: Optional[int]
    ) -> List[Dict]:
        """基于当前文档的推荐（增强版）"""
        from uuid import UUID
        from sqlalchemy import select, text
        from app.models.system_learning_data import SystemLearningData
        from app.models.document import Document
        
        try:
            doc_id = UUID(document_id)
        except ValueError:
            logger.warning("无效的文档ID", document_id=document_id)
            return []
        
        # 1. 获取目标文档的向量和元数据
        target_query = await db.execute(
            select(SystemLearningData)
            .where(SystemLearningData.document_id == doc_id)
            .where(SystemLearningData.embedding.isnot(None))
        )
        target_data = target_query.scalar_one_or_none()
        
        if not target_data or target_data.embedding is None:
            logger.warning("文档向量不存在", document_id=document_id)
            return []
        
        # 2. 构建相似度搜索查询（增强版）
        # 考虑因素：
        # - 向量相似度（权重：50%）
        # - 文档类型匹配（权重：20%）
        # - 质量分数（权重：20%）
        # - 时间新鲜度（权重：10%）
        
        import numpy as np
        if isinstance(target_data.embedding, np.ndarray):
            target_embedding_list = target_data.embedding.tolist()
        else:
            target_embedding_list = list(target_data.embedding) if hasattr(target_data.embedding, '__iter__') else target_data.embedding
        
        target_embedding_str = '[' + ','.join(map(str, target_embedding_list)) + ']'
        
        # 构建SQL查询，综合多个因素计算推荐分数
        # 构建动态WHERE条件，避免None参数的类型问题
        where_conditions = [
            "sld.document_id != :target_document_id",
            "sld.embedding IS NOT NULL",
            "d.status = 'completed'"
        ]
        
        params = {
            "target_embedding": target_embedding_str,
            "target_document_id": doc_id,
            "target_type": target_data.document_type or "",
            "limit": limit * 10  # 多取一些，因为要过滤掉相似度<70%的
        }
        
        # 添加可选的过滤条件
        if document_type:
            where_conditions.append("sld.document_type = :document_type")
            params["document_type"] = document_type
        
        if min_quality_score is not None:
            where_conditions.append("sld.quality_score >= :min_quality_score")
            params["min_quality_score"] = min_quality_score
        
        where_clause = " AND ".join(where_conditions)
        
        query = text(f"""
            SELECT 
                sld.document_id,
                sld.content_summary,
                sld.document_type,
                sld.quality_score,
                sld.processing_time,
                d.filename,
                d.file_type,
                d.upload_time,
                -- 向量相似度分数（0-1）
                1 - (sld.embedding <=> CAST(:target_embedding AS vector)) as similarity_score,
                -- 类型匹配分数（相同类型=1，不同类型=0.5）
                CASE 
                    WHEN sld.document_type = :target_type THEN 1.0
                    ELSE 0.5
                END as type_score,
                -- 质量分数归一化（0-100 -> 0-1）
                COALESCE(sld.quality_score / 100.0, 0.5) as quality_score_normalized,
                -- 时间新鲜度（越新分数越高，基于upload_time）
                CASE 
                    WHEN d.upload_time > NOW() - INTERVAL '7 days' THEN 1.0
                    WHEN d.upload_time > NOW() - INTERVAL '30 days' THEN 0.8
                    WHEN d.upload_time > NOW() - INTERVAL '90 days' THEN 0.6
                    ELSE 0.4
                END as freshness_score
            FROM system_learning_data sld
            JOIN documents d ON sld.document_id = d.id
            WHERE {where_clause}
            ORDER BY 
                -- 综合推荐分数（加权平均）
                (0.5 * (1 - (sld.embedding <=> CAST(:target_embedding AS vector))) +
                 0.2 * CASE WHEN sld.document_type = :target_type THEN 1.0 ELSE 0.5 END +
                 0.2 * COALESCE(sld.quality_score / 100.0, 0.5) +
                 0.1 * CASE 
                     WHEN d.upload_time > NOW() - INTERVAL '7 days' THEN 1.0
                     WHEN d.upload_time > NOW() - INTERVAL '30 days' THEN 0.8
                     WHEN d.upload_time > NOW() - INTERVAL '90 days' THEN 0.6
                     ELSE 0.4
                 END) DESC
            LIMIT :limit
        """)
        
        # 执行查询
        result = await db.execute(query, params)
        
        records = result.fetchall()
        
        # 3. 构建推荐结果
        recommendations = []
        filtered_count = 0
        
        # 先计算所有记录的综合分数
        candidate_recommendations = []
        for record in records:
            similarity = float(record.similarity_score)
            type_match = float(record.type_score)
            quality = float(record.quality_score_normalized)
            freshness = float(record.freshness_score)
            
            # 加权综合分数（相似度权重提高到70%）
            recommendation_score = (
                0.7 * similarity +
                0.15 * type_match +
                0.1 * quality +
                0.05 * freshness
            )
            
            candidate_recommendations.append({
                "record": record,
                "similarity": similarity,
                "recommendation_score": recommendation_score,
                "type_match": type_match,
                "quality": quality,
                "freshness": freshness
            })
        
        # 按综合推荐分数排序
        candidate_recommendations.sort(key=lambda x: x["recommendation_score"], reverse=True)
        
        # 如果最高相似度<70%，使用综合推荐分数>=70%作为阈值
        # 否则使用相似度>=70%作为阈值
        max_similarity = max([c["similarity"] for c in candidate_recommendations]) if candidate_recommendations else 0
        use_composite_threshold = max_similarity < 0.7
        
        if use_composite_threshold:
            max_composite_score = max([c["recommendation_score"] for c in candidate_recommendations]) if candidate_recommendations else 0
            logger.info("最高相似度<70%，使用综合推荐分数作为阈值", max_similarity=max_similarity, max_composite_score=max_composite_score)
            threshold_type = "composite_score"
            # 动态调整阈值：如果最高综合分数<70%，逐步降低阈值，确保至少有一些推荐
            if max_composite_score >= 0.7:
                threshold = 0.7
            elif max_composite_score >= 0.6:
                threshold = 0.6
            elif max_composite_score >= 0.5:
                threshold = 0.5
            else:
                # 如果最高分数<50%，至少返回前几个候选（即使分数较低）
                threshold = max_composite_score * 0.8 if max_composite_score > 0 else 0.3
                logger.info("最高综合分数<50%，使用动态阈值", max_composite_score=max_composite_score, threshold=threshold)
        else:
            threshold = 0.7
            threshold_type = "similarity"
        
        # 筛选推荐
        for candidate in candidate_recommendations:
            if threshold_type == "similarity":
                if candidate["similarity"] < threshold:
                    filtered_count += 1
                    continue
            else:  # composite_score
                if candidate["recommendation_score"] < threshold:
                    filtered_count += 1
                    continue
            
            record = candidate["record"]
            similarity = candidate["similarity"]
            recommendation_score = candidate["recommendation_score"]
            type_match = candidate["type_match"]
            quality = candidate["quality"]
            freshness = candidate["freshness"]
            
            recommendations.append({
                "document_id": str(record.document_id),
                "filename": record.filename,
                "file_type": record.file_type,
                "document_type": record.document_type,
                "content_summary": record.content_summary,
                "quality_score": record.quality_score,
                "upload_time": record.upload_time.isoformat() if record.upload_time else None,
                "similarity": similarity,
                "recommendation_score": round(recommendation_score, 3),
                "reasons": RecommendationService._generate_recommendation_reasons(
                    similarity, type_match, quality, freshness
                )
            })
        
        # 按推荐分数排序并限制数量（已经在上面排序过了）
        logger.info("推荐结果统计", 
                   total_records=len(records),
                   filtered_low_similarity=filtered_count,
                   final_recommendations=len(recommendations),
                   limit=limit,
                   threshold_type=threshold_type if 'threshold_type' in locals() else "similarity",
                   max_similarity=max_similarity,
                   min_similarity=min([c["similarity"] for c in candidate_recommendations]) if candidate_recommendations else 0)
        return recommendations[:limit]
    
    @staticmethod
    async def _recommend_general(
        db,
        limit: int,
        document_type: Optional[str],
        min_quality_score: Optional[int]
    ) -> List[Dict]:
        """通用推荐（基于质量分数和类型）"""
        from sqlalchemy import select, func
        from app.models.system_learning_data import SystemLearningData
        from app.models.document import Document
        
        # 构建查询：优先推荐高质量、新上传的文档
        query = select(
            SystemLearningData.document_id,
            SystemLearningData.content_summary,
            SystemLearningData.document_type,
            SystemLearningData.quality_score,
            Document.filename,
            Document.file_type,
            Document.upload_time
        ).join(
            Document, SystemLearningData.document_id == Document.id
        ).where(
            Document.status == 'completed'
        )
        
        if document_type:
            query = query.where(SystemLearningData.document_type == document_type)
        
        if min_quality_score is not None:
            query = query.where(SystemLearningData.quality_score >= min_quality_score)
        
        query = query.order_by(
            SystemLearningData.quality_score.desc().nulls_last(),
            Document.upload_time.desc()
        ).limit(limit)
        
        result = await db.execute(query)
        records = result.fetchall()
        
        recommendations = []
        for record in records:
            recommendations.append({
                "document_id": str(record.document_id),
                "filename": record.filename,
                "file_type": record.file_type,
                "document_type": record.document_type,
                "content_summary": record.content_summary,
                "quality_score": record.quality_score,
                "upload_time": record.upload_time.isoformat() if record.upload_time else None,
                "recommendation_score": round((record.quality_score or 50) / 100.0, 3),
                "reasons": ["高质量文档", "最新上传"] if record.quality_score and record.quality_score >= 80 else ["最新上传"]
            })
        
        return recommendations
    
    @staticmethod
    def _generate_recommendation_reasons(
        similarity: float,
        type_match: float,
        quality: float,
        freshness: float
    ) -> List[str]:
        """生成推荐理由"""
        reasons = []
        
        if similarity >= 0.8:
            reasons.append("内容高度相似")
        elif similarity >= 0.6:
            reasons.append("内容相关")
        
        if type_match >= 0.9:
            reasons.append("同类型文档")
        
        if quality >= 0.8:
            reasons.append("高质量内容")
        elif quality >= 0.6:
            reasons.append("质量良好")
        
        if freshness >= 0.9:
            reasons.append("最新上传")
        
        if not reasons:
            reasons.append("系统推荐")
        
        return reasons
    
    @staticmethod
    async def _recommend_books(
        db,
        document_id: str,
        limit: int
    ) -> List[Dict]:
        """推荐相关书籍（基于文档内容）"""
        from sqlalchemy import select
        from app.models.system_learning_data import SystemLearningData
        from app.services.ai_service import get_ai_service
        from app.core.database import AsyncSessionLocal
        from uuid import UUID
        
        # 使用独立的数据库会话，避免并发冲突
        book_db = AsyncSessionLocal()
        try:
            # 1. 获取文档信息
            doc_id = UUID(document_id) if isinstance(document_id, str) else document_id
            query = await book_db.execute(
                select(SystemLearningData)
                .where(SystemLearningData.document_id == doc_id)
            )
            doc_data = query.scalar_one_or_none()
            
            if not doc_data:
                return []
            
            # 处理content_summary：可能是字符串或对象
            content_summary = doc_data.content_summary
            if hasattr(content_summary, 'content_summary'):
                content_summary = content_summary.content_summary
            elif not isinstance(content_summary, str):
                content_summary = str(content_summary) if content_summary else ""
            
            content_preview = content_summary[:2000] if content_summary else ""
            doc_type = doc_data.document_type or "technical"
            
            # 2. 使用AI推荐相关书籍
            ai_service = get_ai_service()
            
            type_labels = {
                "interview": "面试题",
                "technical": "技术文档",
                "architecture": "架构文档"
            }
            type_label = type_labels.get(doc_type, "技术")
            
            prompt = f"""请基于以下{type_label}文档内容，推荐3-5本相关的技术书籍。

文档内容摘要：
{content_preview}

请返回JSON格式的数组，每本书包含：
{{
  "title": "书籍名称（必须是真实存在的书籍）",
  "author": "作者（真实作者姓名）",
  "description": "书籍简介（为什么推荐这本书，必须与文档内容相关）",
  "relevance": 0.8
}}

严格要求：
1. **只推荐真实存在的、可以在网络上查到的技术书籍**
   - 必须是可以购买或下载的真实书籍
   - 不要推荐虚构的书籍
   - 不要推荐不存在的书籍
   - 如果不确定书籍是否存在，不要推荐

2. **书籍必须与文档内容高度相关（相关性>=80%）**
   - 书籍主题必须与文档内容直接相关
   - 不要推荐只是稍微相关或完全不相关的书籍
   - 如果找不到高度相关的书籍，可以返回少于3本，但不要推荐不相关的书籍

3. **优先推荐经典、权威的技术书籍**
   - 优先推荐知名出版社出版的书籍
   - 优先推荐作者是技术专家的书籍
   - 优先推荐有良好评价的书籍

4. **书籍信息必须准确**
   - 书名必须准确
   - 作者姓名必须准确
   - 不要编造书籍信息

5. **如果找不到足够的相关书籍，返回空数组 []**
   - 宁愿不推荐，也不要推荐不相关或虚假的书籍
   - 质量比数量更重要

6. **relevance字段必须是0.8-1.0之间的浮点数**
   - 只有高度相关的书籍才推荐
   - 相关性低于80%的书籍不要推荐

只返回JSON数组，不要其他内容。如果找不到合适的书籍，返回空数组 []。"""
            
            system_prompt = """你是一个严格的技术书籍推荐专家，擅长根据技术文档内容推荐真实、相关、高质量的技术书籍。

你的职责：
1. 只推荐真实存在的技术书籍
2. 确保推荐的书籍与文档内容高度相关（>=80%）
3. 优先推荐经典、权威的技术书籍
4. 如果找不到合适的书籍，宁愿不推荐也不要推荐不相关或虚假的书籍
5. 质量比数量更重要

记住：推荐虚假或不相关的书籍会严重影响用户体验，必须严格把关。"""
            
            try:
                books = await ai_service.generate_json(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=0.3
                )
                
                if not isinstance(books, list):
                    return []
                
                # 转换为推荐格式，严格验证
                recommendations = []
                for book in books:
                    if isinstance(book, dict) and "title" in book:
                        title = book.get("title", "").strip()
                        author = book.get("author", "").strip()
                        description = book.get("description", "").strip()
                        relevance = float(book.get("relevance", 0.0))
                        
                        # 严格验证：只保留相关性>=80%且信息完整的书籍
                        if relevance >= 0.8 and title and author and description:
                            # 验证书籍信息是否合理（避免明显的虚假信息）
                            if len(title) >= 3 and len(author) >= 2 and len(description) >= 10:
                                recommendations.append({
                                    "document_id": None,  # 书籍没有document_id
                                    "filename": title,
                                    "file_type": "book",
                                    "document_type": doc_type,
                                    "content_summary": description,
                                    "quality_score": int(relevance * 100),
                                    "upload_time": None,
                                    "similarity": relevance,
                                    "recommendation_score": round(relevance, 3),
                                    "reasons": [
                                        f"相关性: {int(relevance * 100)}%",
                                        "网络推荐书籍",
                                        f"作者: {author}"
                                    ],
                                    "is_book": True,
                                    "author": author
                                })
                            else:
                                logger.warning("书籍信息不完整，跳过", title=title, author=author, description_len=len(description))
                        else:
                            logger.warning("书籍相关性不足或信息缺失，跳过", 
                                         title=title, relevance=relevance, 
                                         has_author=bool(author), has_description=bool(description))
                
                # 按推荐度（recommendation_score）降序排序
                recommendations.sort(key=lambda x: x["recommendation_score"], reverse=True)
                
                # 返回前limit个推荐
                return recommendations[:limit]
                
            except Exception as e:
                logger.warning("书籍推荐失败", error=str(e))
                return []
        except Exception as e:
            logger.error("书籍推荐生成失败", error=str(e))
            return []
        finally:
            await book_db.close()


def get_recommendation_service() -> RecommendationService:
    """获取推荐服务实例（单例模式）"""
    return RecommendationService()

