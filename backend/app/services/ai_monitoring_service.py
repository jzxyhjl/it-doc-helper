"""
AI监控服务 - 收集和存储AI调用指标、结果质量、一致性数据
"""
from typing import Optional, Dict, List
from datetime import datetime
import hashlib
import json
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.ai_monitoring import AICallMetrics, AIResultQuality, AIResultConsistency
from app.core.database import AsyncSessionLocal

logger = structlog.get_logger()


class AIMonitoringService:
    """AI监控服务"""
    
    def __init__(self):
        """初始化监控服务"""
        self.enabled = settings.ENABLE_AI_MONITORING
        if self.enabled:
            logger.info("AI监控服务已启用")
        else:
            logger.debug("AI监控服务已禁用")
    
    async def record_call_metrics(
        self,
        document_id: Optional[str],
        call_type: str,
        model: str,
        status: str,
        response_time_ms: Optional[int] = None,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        retry_count: int = 0
    ) -> None:
        """
        记录AI调用指标
        
        Args:
            document_id: 文档ID
            call_type: 调用类型
            model: 模型名称
            status: 状态
            response_time_ms: 响应时间（毫秒）
            error_type: 错误类型
            error_message: 错误信息
            retry_count: 重试次数
        """
        if not self.enabled:
            return
        
        try:
            db = AsyncSessionLocal()
            try:
                import uuid
                doc_uuid = uuid.UUID(document_id) if document_id else None
                
                metrics = AICallMetrics(
                    document_id=doc_uuid,
                    call_type=call_type,
                    model=model,
                    status=status,
                    response_time_ms=response_time_ms,
                    error_type=error_type,
                    error_message=error_message[:500] if error_message else None,  # 限制长度
                    retry_count=retry_count
                )
                
                db.add(metrics)
                await db.commit()
                logger.debug("AI调用指标已记录", 
                           document_id=document_id,
                           call_type=call_type,
                           status=status)
            finally:
                await db.close()
        except Exception as e:
            logger.error("记录AI调用指标失败", 
                        error=str(e),
                        document_id=document_id)
    
    async def record_result_quality(
        self,
        document_id: str,
        document_type: str,
        result_data: Dict
    ) -> None:
        """
        记录AI结果质量
        
        Args:
            document_id: 文档ID
            document_type: 文档类型
            result_data: 结果数据字典
        """
        if not self.enabled:
            return
        
        try:
            # 计算质量指标
            quality_metrics = self._calculate_quality_metrics(result_data)
            
            db = AsyncSessionLocal()
            try:
                import uuid
                doc_uuid = uuid.UUID(document_id)
                
                quality = AIResultQuality(
                    document_id=doc_uuid,
                    document_type=document_type,
                    **quality_metrics
                )
                
                db.add(quality)
                await db.commit()
                logger.debug("AI结果质量已记录", 
                           document_id=document_id,
                           quality_score=quality_metrics.get('quality_score'))
            finally:
                await db.close()
        except Exception as e:
            logger.error("记录AI结果质量失败", 
                        error=str(e),
                        document_id=document_id)
    
    def _calculate_quality_metrics(self, result_data: Dict) -> Dict:
        """
        计算质量指标
        
        Args:
            result_data: 结果数据字典
            
        Returns:
            质量指标字典
        """
        metrics = {
            "field_completeness": 0.0,
            "confidence_avg": 0.0,
            "confidence_min": 100.0,
            "confidence_max": 0.0,
            "sources_count": 0,
            "sources_completeness": 0.0,
            "quality_score": 0.0
        }
        
        # 收集所有置信度值
        confidences = []
        sources_counts = []
        fields_with_confidence = 0
        total_fields = 0
        
        def extract_metrics(obj, path=""):
            """递归提取指标"""
            nonlocal confidences, sources_counts, fields_with_confidence, total_fields
            
            if isinstance(obj, dict):
                total_fields += 1
                
                # 检查置信度
                if "confidence" in obj:
                    conf = obj["confidence"]
                    if isinstance(conf, (int, float)) and 0 <= conf <= 100:
                        confidences.append(conf)
                        fields_with_confidence += 1
                
                # 检查来源
                if "sources" in obj:
                    sources = obj["sources"]
                    if isinstance(sources, list):
                        sources_counts.append(len(sources))
                
                # 递归处理
                for key, value in obj.items():
                    extract_metrics(value, f"{path}.{key}" if path else key)
            
            elif isinstance(obj, list):
                for item in obj:
                    extract_metrics(item, path)
        
        extract_metrics(result_data)
        
        # 计算指标
        if confidences:
            metrics["confidence_avg"] = sum(confidences) / len(confidences)
            metrics["confidence_min"] = min(confidences)
            metrics["confidence_max"] = max(confidences)
        
        if sources_counts:
            metrics["sources_count"] = sum(sources_counts)
            # 来源完整性：有来源的字段占比
            metrics["sources_completeness"] = len(sources_counts) / max(total_fields, 1)
        
        # 字段完整性：有置信度的字段占比
        metrics["field_completeness"] = fields_with_confidence / max(total_fields, 1)
        
        # 综合质量分数（加权平均）
        quality_score = (
            metrics["field_completeness"] * 0.3 +
            (metrics["confidence_avg"] / 100.0) * 0.4 +
            metrics["sources_completeness"] * 0.3
        ) * 100
        
        metrics["quality_score"] = round(quality_score, 2)
        
        return metrics
    
    async def record_result_consistency(
        self,
        document_id: str,
        test_run_id: str,
        result_data: Dict
    ) -> None:
        """
        记录AI结果一致性（用于回归测试）
        
        Args:
            document_id: 文档ID
            test_run_id: 测试运行ID
            result_data: 结果数据字典
        """
        if not self.enabled:
            return
        
        try:
            db = AsyncSessionLocal()
            try:
                import uuid
                doc_uuid = uuid.UUID(document_id)
                
                # 提取关键字段的哈希值
                consistency_records = []
                
                def extract_fields(obj, field_path=""):
                    """递归提取字段"""
                    if isinstance(obj, dict):
                        # 提取置信度字段
                        if "confidence" in obj:
                            conf = obj["confidence"]
                            field_hash = hashlib.sha256(
                                json.dumps({field_path: conf}, sort_keys=True).encode()
                            ).hexdigest()
                            
                            consistency_records.append(
                                AIResultConsistency(
                                    document_id=doc_uuid,
                                    test_run_id=test_run_id,
                                    field_name=field_path or "root",
                                    field_value_hash=field_hash,
                                    confidence_diff=None  # 需要与基准对比才能计算
                                )
                            )
                        
                        # 递归处理
                        for key, value in obj.items():
                            new_path = f"{field_path}.{key}" if field_path else key
                            extract_fields(value, new_path)
                    
                    elif isinstance(obj, list):
                        for i, item in enumerate(obj):
                            extract_fields(item, f"{field_path}[{i}]")
                
                extract_fields(result_data)
                
                if consistency_records:
                    db.add_all(consistency_records)
                    await db.commit()
                    logger.debug("AI结果一致性已记录", 
                               document_id=document_id,
                               test_run_id=test_run_id,
                               records_count=len(consistency_records))
            finally:
                await db.close()
        except Exception as e:
            logger.error("记录AI结果一致性失败", 
                        error=str(e),
                        document_id=document_id)
    
    @staticmethod
    def get_instance() -> 'AIMonitoringService':
        """获取监控服务实例（单例模式）"""
        if not hasattr(AIMonitoringService, '_instance'):
            AIMonitoringService._instance = AIMonitoringService()
        return AIMonitoringService._instance

