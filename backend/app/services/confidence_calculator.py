"""
可信度计算服务
计算AI处理结果的可信度分数和标签
"""
import re
from typing import Dict, List, Optional
import structlog

logger = structlog.get_logger()


class ConfidenceCalculator:
    """可信度计算器"""
    
    # 权重配置
    WEIGHT_RETRIEVAL_STRENGTH = 0.3  # 检索命中强度
    WEIGHT_SIMILARITY = 0.2           # top-k相似度
    WEIGHT_CONCENTRATION = 0.2       # 来源集中度
    WEIGHT_CONSISTENCY = 0.3          # 内容一致性
    
    # 降分规则
    PENALTY_OUT_OF_SCOPE = -20       # 超出文档内容
    PENALTY_NONEXISTENT_CONCEPT = -15 # 不存在概念
    PENALTY_CONTRADICTION = -10      # 自相矛盾
    PENALTY_UNSTABLE = -10            # 结果不稳定
    
    # 可信度标签阈值
    THRESHOLD_HIGH = 75
    THRESHOLD_MEDIUM = 40
    
    @staticmethod
    def calculate_confidence(
        base_confidence: float,
        source_ids: List[int],
        segments: List[Dict],
        similarity_scores: Optional[List[float]] = None,
        content: str = "",
        ai_response: str = ""
    ) -> Dict:
        """
        计算最终可信度
        
        Args:
            base_confidence: AI返回的基础可信度（0-100）
            source_ids: 来源段落ID列表
            segments: 所有段落列表
            similarity_scores: 相似度分数列表（可选）
            content: 原始文档内容（用于一致性检查）
            ai_response: AI返回的响应内容（用于一致性检查）
            
        Returns:
            {
                "score": 85,
                "label": "高",
                "factors": {
                    "base": 80,
                    "retrieval_strength": 0.9,
                    "similarity": 0.85,
                    "concentration": 0.8,
                    "consistency": 0.9
                }
            }
        """
        try:
            # 确保基础可信度在有效范围内
            base_confidence = max(0, min(100, base_confidence))
            
            # 1. 计算检索命中强度（带异常处理）
            try:
                retrieval_strength = ConfidenceCalculator._calculate_retrieval_strength(
                    source_ids, segments
                )
            except Exception as e:
                logger.warning("检索命中强度计算失败，使用默认值", error=str(e))
                retrieval_strength = 0.5  # 默认中等强度
            
            # 2. 计算top-k相似度（带异常处理）
            try:
                similarity = ConfidenceCalculator._calculate_similarity(
                    similarity_scores
                )
            except Exception as e:
                logger.warning("相似度计算失败，使用默认值", error=str(e))
                similarity = 0.5  # 默认中等相似度
            
            # 3. 计算来源集中度（带异常处理）
            try:
                concentration = ConfidenceCalculator._calculate_concentration(
                    source_ids, segments
                )
            except Exception as e:
                logger.warning("来源集中度计算失败，使用默认值", error=str(e))
                concentration = 0.5  # 默认中等集中度
            
            # 4. 计算内容一致性（带异常处理）
            try:
                consistency = ConfidenceCalculator._calculate_consistency(
                    source_ids, segments, content, ai_response
                )
            except Exception as e:
                logger.warning("内容一致性检查失败，跳过检查", error=str(e))
                consistency = 1.0  # 跳过检查，不降分
            
            # 5. 加权计算
            weighted_score = (
                base_confidence * 0.4 +  # 基础分数占40%
                retrieval_strength * 100 * ConfidenceCalculator.WEIGHT_RETRIEVAL_STRENGTH +
                similarity * 100 * ConfidenceCalculator.WEIGHT_SIMILARITY +
                concentration * 100 * ConfidenceCalculator.WEIGHT_CONCENTRATION +
                consistency * 100 * ConfidenceCalculator.WEIGHT_CONSISTENCY
            )
            
            # 6. 应用降分规则（带异常处理）
            try:
                final_score = ConfidenceCalculator._apply_penalties(
                    weighted_score, content, ai_response
                )
            except Exception as e:
                logger.warning("降分规则应用失败，使用加权分数", error=str(e))
                final_score = weighted_score  # 使用加权分数，不应用降分
            
            # 确保分数在有效范围内
            final_score = max(0, min(100, final_score))
            
            # 7. 转换为标签
            label = ConfidenceCalculator._score_to_label(final_score)
            
            return {
                "score": round(final_score, 1),
                "label": label,
                "factors": {
                    "base": round(base_confidence, 1),
                    "retrieval_strength": round(retrieval_strength, 2),
                    "similarity": round(similarity, 2),
                    "concentration": round(concentration, 2),
                    "consistency": round(consistency, 2)
                }
            }
            
        except Exception as e:
            logger.error("可信度计算失败，使用基础分数", error=str(e))
            # 兜底：使用基础分数
            return {
                "score": round(max(0, min(100, base_confidence)), 1),
                "label": ConfidenceCalculator._score_to_label(base_confidence),
                "factors": {
                    "base": round(base_confidence, 1),
                    "retrieval_strength": 0.5,
                    "similarity": 0.5,
                    "concentration": 0.5,
                    "consistency": 0.5
                }
            }
    
    @staticmethod
    def _calculate_retrieval_strength(
        source_ids: List[int],
        segments: List[Dict]
    ) -> float:
        """
        计算检索命中强度
        
        基于来源段落的数量和质量
        """
        if not source_ids or not segments:
            return 0.0
        
        # 验证source_ids有效性
        valid_ids = [sid for sid in source_ids if 1 <= sid <= len(segments)]
        
        if not valid_ids:
            return 0.0
        
        # 计算有效来源的比例
        valid_ratio = len(valid_ids) / len(source_ids) if source_ids else 0.0
        
        # 计算来源段落的平均长度（长度越长，质量可能越高）
        source_segments = [seg for seg in segments if seg["id"] in valid_ids]
        if source_segments:
            avg_length = sum(seg["length"] for seg in source_segments) / len(source_segments)
            # 归一化长度分数（假设平均段落长度200字符）
            length_score = min(1.0, avg_length / 200.0)
        else:
            length_score = 0.0
        
        # 综合分数
        strength = (valid_ratio * 0.6 + length_score * 0.4)
        
        return min(1.0, max(0.0, strength))
    
    @staticmethod
    def _calculate_similarity(similarity_scores: Optional[List[float]]) -> float:
        """
        计算top-k相似度
        
        基于与相似文档的相似度分数
        """
        if not similarity_scores:
            return 0.5  # 默认中等相似度
        
        # 计算平均相似度
        avg_similarity = sum(similarity_scores) / len(similarity_scores)
        
        return min(1.0, max(0.0, avg_similarity))
    
    @staticmethod
    def _calculate_concentration(
        source_ids: List[int],
        segments: List[Dict]
    ) -> float:
        """
        计算来源集中度
        
        检查来源是否集中在少数段落
        """
        if not source_ids or not segments:
            return 0.5
        
        # 计算来源段落的分布
        unique_segments = len(set(source_ids))
        total_segments = len(segments)
        
        if total_segments == 0:
            return 0.5
        
        # 集中度：使用的段落数 / 总段落数
        # 值越小（集中在少数段落），集中度越高
        concentration_ratio = unique_segments / total_segments
        
        # 转换为集中度分数（0-1，值越大表示越集中）
        # 如果集中在20%的段落内，认为集中度高
        if concentration_ratio <= 0.2:
            concentration_score = 1.0
        elif concentration_ratio <= 0.5:
            concentration_score = 0.8
        elif concentration_ratio <= 0.8:
            concentration_score = 0.6
        else:
            concentration_score = 0.4
        
        return concentration_score
    
    @staticmethod
    def _calculate_consistency(
        source_ids: List[int],
        segments: List[Dict],
        content: str,
        ai_response: str
    ) -> float:
        """
        计算内容一致性
        
        检查AI回答是否与文档内容一致
        """
        if not content or not ai_response:
            return 0.5  # 默认中等一致性
        
        consistency_score = 1.0
        
        # 1. 检查是否超出文档内容
        # 简单检查：AI响应中的关键词是否在文档中出现
        ai_words = set(re.findall(r'\w+', ai_response.lower()))
        content_words = set(re.findall(r'\w+', content.lower()))
        
        # 计算关键词重叠率
        if ai_words:
            overlap_ratio = len(ai_words & content_words) / len(ai_words)
            # 如果重叠率低于50%，可能超出文档内容
            if overlap_ratio < 0.5:
                consistency_score -= 0.2
        
        # 2. 检查来源段落与AI响应的相关性
        if source_ids and segments:
            source_texts = [
                seg["text"] for seg in segments 
                if seg["id"] in source_ids
            ]
            source_content = " ".join(source_texts).lower()
            
            # 计算AI响应与来源段落的相关性
            ai_keywords = set(re.findall(r'\w+', ai_response.lower()))
            source_keywords = set(re.findall(r'\w+', source_content))
            
            if ai_keywords:
                relevance_ratio = len(ai_keywords & source_keywords) / len(ai_keywords)
                consistency_score = consistency_score * 0.5 + relevance_ratio * 0.5
        
        return min(1.0, max(0.0, consistency_score))
    
    @staticmethod
    def _apply_penalties(
        score: float,
        content: str,
        ai_response: str
    ) -> float:
        """
        应用降分规则
        
        检查是否存在超出文档、不存在概念、自相矛盾等情况
        """
        final_score = score
        
        if not content or not ai_response:
            return final_score
        
        # 1. 检查超出文档内容（简单实现）
        # 提取文档中的技术术语和关键词
        content_terms = set(re.findall(r'[A-Z][a-z]+|[a-z]+', content))
        ai_terms = set(re.findall(r'[A-Z][a-z]+|[a-z]+', ai_response))
        
        # 如果AI响应中有大量文档中不存在的术语，可能超出文档
        if content_terms:
            unknown_ratio = len(ai_terms - content_terms) / len(ai_terms) if ai_terms else 0
            if unknown_ratio > 0.3:  # 超过30%的术语不在文档中
                final_score += ConfidenceCalculator.PENALTY_OUT_OF_SCOPE
        
        # 2. 检查自相矛盾（简单实现：检查否定词）
        # 这里只是示例，实际需要更复杂的逻辑
        negation_pattern = r'\b(不|非|无|没有|错误|失败)\b'
        if len(re.findall(negation_pattern, ai_response)) > 3:
            # 如果否定词过多，可能存在矛盾
            final_score += ConfidenceCalculator.PENALTY_CONTRADICTION * 0.5
        
        return final_score
    
    @staticmethod
    def _score_to_label(score: float) -> str:
        """
        将分数转换为标签
        
        Args:
            score: 可信度分数（0-100）
            
        Returns:
            "高" | "中" | "低"
        """
        if score >= ConfidenceCalculator.THRESHOLD_HIGH:
            return "高"
        elif score >= ConfidenceCalculator.THRESHOLD_MEDIUM:
            return "中"
        else:
            return "低"
    
    @staticmethod
    def normalize_confidence(confidence: Optional[float]) -> float:
        """
        规范化可信度分数
        
        确保分数在0-100范围内，如果缺失则返回默认值
        """
        if confidence is None:
            return 50.0  # 默认中等可信度
        
        return max(0.0, min(100.0, float(confidence)))

