"""
处理模式学习分析服务
- 文档类型识别准确率统计
- 处理耗时分析
- 常见错误模式识别
- 优化建议生成
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger()


class LearningAnalyzer:
    """学习分析器"""
    
    @staticmethod
    async def analyze_processing_patterns(db: any) -> Dict:
        """
        分析处理模式
        
        Args:
            db: 数据库会话
        
        Returns:
            分析结果字典
        """
        from sqlalchemy import select, func, and_
        from app.models.system_learning_data import SystemLearningData
        from app.models.processing_task import ProcessingTask
        from app.models.document_type import DocumentType
        
        logger.info("开始分析处理模式")
        
        try:
            # 1. 文档类型识别准确率统计
            type_accuracy = await LearningAnalyzer._analyze_type_accuracy(db)
            
            # 2. 处理耗时分析
            processing_time_analysis = await LearningAnalyzer._analyze_processing_time(db)
            
            # 3. 常见错误模式识别
            error_patterns = await LearningAnalyzer._analyze_error_patterns(db)
            
            # 4. 生成优化建议
            suggestions = LearningAnalyzer._generate_suggestions(
                type_accuracy,
                processing_time_analysis,
                error_patterns
            )
            
            result = {
                "type_accuracy": type_accuracy,
                "processing_time_analysis": processing_time_analysis,
                "error_patterns": error_patterns,
                "suggestions": suggestions,
                "analyzed_at": datetime.now().isoformat()
            }
            
            logger.info("处理模式分析完成")
            return result
            
        except Exception as e:
            logger.error("处理模式分析失败", error=str(e))
            return {
                "error": str(e),
                "analyzed_at": datetime.now().isoformat()
            }
    
    @staticmethod
    async def _analyze_type_accuracy(db) -> Dict:
        """分析文档类型识别准确率"""
        from sqlalchemy import select, func
        from app.models.document_type import DocumentType
        
        # 统计各类型的识别次数和置信度
        result = await db.execute(
            select(
                DocumentType.detected_type,
                func.count(DocumentType.id).label('count'),
                func.avg(DocumentType.confidence).label('avg_confidence'),
                func.min(DocumentType.confidence).label('min_confidence'),
                func.max(DocumentType.confidence).label('max_confidence')
            )
            .group_by(DocumentType.detected_type)
        )
        
        type_stats = result.fetchall()
        
        total = sum(stat.count for stat in type_stats)
        avg_confidence = sum(stat.avg_confidence or 0 for stat in type_stats) / len(type_stats) if type_stats else 0
        
        return {
            "total_documents": total,
            "average_confidence": round(avg_confidence, 3) if avg_confidence else 0,
            "type_distribution": [
                {
                    "type": stat.detected_type,
                    "count": stat.count,
                    "percentage": round((stat.count / total * 100), 2) if total > 0 else 0,
                    "avg_confidence": round(float(stat.avg_confidence or 0), 3),
                    "min_confidence": round(float(stat.min_confidence or 0), 3),
                    "max_confidence": round(float(stat.max_confidence or 0), 3)
                }
                for stat in type_stats
            ]
        }
    
    @staticmethod
    async def _analyze_processing_time(db) -> Dict:
        """分析处理耗时"""
        from sqlalchemy import select, func, case
        from app.models.system_learning_data import SystemLearningData
        
        # 统计各类型的平均处理时间
        result = await db.execute(
            select(
                SystemLearningData.document_type,
                func.count(SystemLearningData.id).label('count'),
                func.avg(SystemLearningData.processing_time).label('avg_time'),
                func.min(SystemLearningData.processing_time).label('min_time'),
                func.max(SystemLearningData.processing_time).label('max_time')
            )
            .where(SystemLearningData.processing_time.isnot(None))
            .group_by(SystemLearningData.document_type)
        )
        
        time_stats = result.fetchall()
        
        # 计算总体统计
        all_times_result = await db.execute(
            select(
                func.avg(SystemLearningData.processing_time).label('avg_time'),
                func.min(SystemLearningData.processing_time).label('min_time'),
                func.max(SystemLearningData.processing_time).label('max_time')
            )
            .where(SystemLearningData.processing_time.isnot(None))
        )
        overall = all_times_result.fetchone()
        
        return {
            "overall": {
                "average_time": round(float(overall.avg_time or 0), 2) if overall else 0,
                "min_time": int(overall.min_time or 0) if overall else 0,
                "max_time": int(overall.max_time or 0) if overall else 0
            },
            "by_type": [
                {
                    "type": stat.document_type,
                    "count": stat.count,
                    "avg_time": round(float(stat.avg_time or 0), 2),
                    "min_time": int(stat.min_time or 0),
                    "max_time": int(stat.max_time or 0)
                }
                for stat in time_stats
            ]
        }
    
    @staticmethod
    async def _analyze_error_patterns(db) -> Dict:
        """分析常见错误模式"""
        from sqlalchemy import select, func
        from app.models.processing_task import ProcessingTask
        
        # 统计失败任务
        failed_tasks_result = await db.execute(
            select(
                ProcessingTask.current_stage,
                func.count(ProcessingTask.id).label('count')
            )
            .where(ProcessingTask.status == 'failed')
            .group_by(ProcessingTask.current_stage)
            .order_by(func.count(ProcessingTask.id).desc())
            .limit(10)
        )
        
        failed_patterns = failed_tasks_result.fetchall()
        
        # 统计总失败数
        total_failed_result = await db.execute(
            select(func.count(ProcessingTask.id))
            .where(ProcessingTask.status == 'failed')
        )
        total_failed = total_failed_result.scalar_one() or 0
        
        # 统计总任务数
        total_tasks_result = await db.execute(
            select(func.count(ProcessingTask.id))
        )
        total_tasks = total_tasks_result.scalar_one() or 0
        
        failure_rate = (total_failed / total_tasks * 100) if total_tasks > 0 else 0
        
        return {
            "total_tasks": total_tasks,
            "total_failed": total_failed,
            "failure_rate": round(failure_rate, 2),
            "common_failure_stages": [
                {
                    "stage": pattern.current_stage or "未知",
                    "count": pattern.count,
                    "percentage": round((pattern.count / total_failed * 100), 2) if total_failed > 0 else 0
                }
                for pattern in failed_patterns
            ]
        }
    
    @staticmethod
    def _generate_suggestions(
        type_accuracy: Dict,
        processing_time_analysis: Dict,
        error_patterns: Dict
    ) -> List[str]:
        """生成优化建议"""
        suggestions = []
        
        # 基于类型识别准确率的建议
        if type_accuracy.get("average_confidence", 0) < 0.7:
            suggestions.append("文档类型识别置信度较低，建议优化类型识别算法或增加训练数据")
        
        # 基于处理耗时的建议
        overall_time = processing_time_analysis.get("overall", {})
        avg_time = overall_time.get("average_time", 0)
        if avg_time > 120:  # 超过2分钟
            suggestions.append(f"平均处理时间较长（{avg_time}秒），建议优化处理流程或增加并发处理能力")
        
        # 基于错误模式的建议
        failure_rate = error_patterns.get("failure_rate", 0)
        if failure_rate > 10:  # 失败率超过10%
            suggestions.append(f"处理失败率较高（{failure_rate}%），建议检查错误日志并优化错误处理机制")
        
        # 检查是否有特定类型的处理时间异常
        for type_stat in processing_time_analysis.get("by_type", []):
            if type_stat.get("avg_time", 0) > 180:  # 超过3分钟
                suggestions.append(
                    f"{type_stat['type']}类型文档处理时间较长（平均{type_stat['avg_time']}秒），"
                    f"建议针对该类型优化处理逻辑"
                )
        
        if not suggestions:
            suggestions.append("系统运行良好，暂无优化建议")
        
        return suggestions


def get_learning_analyzer() -> LearningAnalyzer:
    """获取学习分析器实例（单例模式）"""
    return LearningAnalyzer()

