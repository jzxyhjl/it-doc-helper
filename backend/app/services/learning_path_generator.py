"""
学习路径生成服务
- 基于文档类型生成学习路径建议
- 生成文字描述的学习路径
"""
from typing import Dict, List, Optional
from datetime import datetime
import structlog

logger = structlog.get_logger()


class LearningPathGenerator:
    """学习路径生成器"""
    
    @staticmethod
    async def generate_learning_path(db) -> Dict:
        """
        生成学习路径
        
        Args:
            db: 数据库会话
        
        Returns:
            学习路径字典
        """
        from sqlalchemy import select, func
        from app.models.system_learning_data import SystemLearningData
        
        logger.info("开始生成学习路径")
        
        try:
            # 1. 统计文档类型分布
            type_distribution = await LearningPathGenerator._get_type_distribution(db)
            
            # 2. 生成学习路径建议
            learning_path = LearningPathGenerator._generate_path_suggestions(type_distribution)
            
            # 3. 生成学习建议
            recommendations = LearningPathGenerator._generate_recommendations(type_distribution)
            
            result = {
                "type_distribution": type_distribution,
                "learning_path": learning_path,
                "recommendations": recommendations,
                "generated_at": datetime.now().isoformat()
            }
            
            logger.info("学习路径生成完成")
            return result
            
        except Exception as e:
            logger.error("学习路径生成失败", error=str(e))
            return {
                "error": str(e),
                "generated_at": datetime.now().isoformat()
            }
    
    @staticmethod
    async def _get_type_distribution(db) -> Dict:
        """获取文档类型分布"""
        from sqlalchemy import select, func
        from app.models.system_learning_data import SystemLearningData
        
        result = await db.execute(
            select(
                SystemLearningData.document_type,
                func.count(SystemLearningData.id).label('count')
            )
            .group_by(SystemLearningData.document_type)
            .order_by(func.count(SystemLearningData.id).desc())
        )
        
        type_stats = result.fetchall()
        total = sum(stat.count for stat in type_stats)
        
        return {
            "total_documents": total,
            "distribution": [
                {
                    "type": stat.document_type,
                    "count": stat.count,
                    "percentage": round((stat.count / total * 100), 2) if total > 0 else 0
                }
                for stat in type_stats
            ]
        }
    
    @staticmethod
    def _generate_path_suggestions(type_distribution: Dict) -> List[Dict]:
        """生成学习路径建议"""
        distribution = type_distribution.get("distribution", [])
        total = type_distribution.get("total_documents", 0)
        
        if total == 0:
            return [
                {
                    "stage": 1,
                    "title": "开始学习",
                    "description": "上传您的第一份文档，开始您的学习之旅",
                    "suggested_type": "technical"
                }
            ]
        
        # 根据文档类型分布生成学习路径
        path = []
        stage = 1
        
        # 如果有技术文档，建议先学习技术文档
        technical_docs = next((d for d in distribution if d["type"] == "technical"), None)
        if technical_docs and technical_docs["count"] > 0:
            path.append({
                "stage": stage,
                "title": "技术文档学习",
                "description": f"您已上传{technical_docs['count']}份技术文档，建议系统学习技术知识，建立扎实的基础",
                "suggested_type": "technical",
                "current_count": technical_docs["count"]
            })
            stage += 1
        
        # 如果有面试题，建议学习面试题
        interview_docs = next((d for d in distribution if d["type"] == "interview"), None)
        if interview_docs and interview_docs["count"] > 0:
            path.append({
                "stage": stage,
                "title": "面试准备",
                "description": f"您已上传{interview_docs['count']}份面试题文档，建议系统复习和练习，提升面试能力",
                "suggested_type": "interview",
                "current_count": interview_docs["count"]
            })
            stage += 1
        
        # 如果有架构文档，建议学习架构
        architecture_docs = next((d for d in distribution if d["type"] == "architecture"), None)
        if architecture_docs and architecture_docs["count"] > 0:
            path.append({
                "stage": stage,
                "title": "架构设计学习",
                "description": f"您已上传{architecture_docs['count']}份架构文档，建议深入学习系统架构和设计模式",
                "suggested_type": "architecture",
                "current_count": architecture_docs["count"]
            })
            stage += 1
        
        # 如果没有特定类型，提供通用建议
        if not path:
            path.append({
                "stage": 1,
                "title": "多样化学习",
                "description": "建议上传不同类型文档，建立全面的知识体系",
                "suggested_type": None
            })
        
        return path
    
    @staticmethod
    def _generate_recommendations(type_distribution: Dict) -> List[str]:
        """生成学习建议"""
        recommendations = []
        distribution = type_distribution.get("distribution", [])
        total = type_distribution.get("total_documents", 0)
        
        if total == 0:
            recommendations.append("开始上传文档，系统将为您生成个性化的学习路径")
            return recommendations
        
        # 检查是否有单一类型占主导
        if len(distribution) == 1:
            doc_type = distribution[0]["type"]
            type_labels = {
                "technical": "技术文档",
                "interview": "面试题",
                "architecture": "架构文档"
            }
            recommendations.append(
                f"您目前主要学习{type_labels.get(doc_type, doc_type)}，"
                f"建议尝试上传其他类型的文档，建立更全面的知识体系"
            )
        elif len(distribution) >= 3:
            recommendations.append("您的学习内容多样化，很好！继续保持这种学习方式")
        
        # 检查文档数量
        if total < 5:
            recommendations.append("建议上传更多文档，系统可以为您提供更精准的学习建议")
        elif total >= 10:
            recommendations.append("您已上传大量文档，建议定期回顾历史文档，巩固学习成果")
        
        return recommendations


def get_learning_path_generator() -> LearningPathGenerator:
    """获取学习路径生成器实例（单例模式）"""
    return LearningPathGenerator()


