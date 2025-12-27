"""
面试题文档处理服务
- 内容总结
- 问题生成
- 答案提取
"""
from typing import Dict, List, Optional
import structlog
import json

from app.services.ai_service import get_ai_service
from app.services.source_segmenter import SourceSegmenter
from app.services.confidence_calculator import ConfidenceCalculator

logger = structlog.get_logger()


class InterviewProcessor:
    """面试题文档处理器"""
    
    @staticmethod
    async def process(content: str, stream_callback: Optional[callable] = None) -> Dict:
        """
        处理面试题文档
        
        Args:
            content: 文档内容
        
        Returns:
            处理结果字典
        """
        logger.info("开始处理面试题文档", content_length=len(content))
        
        # 0. 段落切分（带异常处理）
        try:
            segments = SourceSegmenter.segment_content(content, timeout=5.0)
            logger.info("段落切分完成", segments_count=len(segments), content_length=len(content))
            # 如果段落切分返回空列表，使用兜底策略
            if not segments:
                logger.warning("段落切分返回空列表，使用兜底策略")
                segments = SourceSegmenter._fallback_segment(content)
                logger.info("兜底策略完成", segments_count=len(segments))
        except Exception as e:
            logger.error("段落切分失败，使用兜底策略", error=str(e))
            segments = SourceSegmenter._fallback_segment(content)  # 使用兜底策略而不是空列表
        
        # 1. 内容总结（带异常处理）
        try:
            summary = await InterviewProcessor._extract_summary(content, segments)
        except Exception as e:
            logger.error("内容总结失败，使用默认值", error=str(e))
            summary = {
                "key_points": [],
                "question_types": {},
                "difficulty": {},
                "total_questions": 0
            }
        
        # 2. 问题生成（带异常处理）
        try:
            generated_questions = await InterviewProcessor._generate_questions(content, segments, summary)
        except Exception as e:
            logger.error("问题生成失败，使用默认值", error=str(e))
            generated_questions = []
        
        # 3. 答案提取（带异常处理）
        try:
            extracted_answers = await InterviewProcessor._extract_answers(content, segments)
        except Exception as e:
            logger.error("答案提取失败，使用默认值", error=str(e))
            extracted_answers = {
                "answers": [],
                "confidence": None,
                "confidence_label": None,
                "sources": []
            }
        
        result = {
            "summary": summary,
            "generated_questions": generated_questions,
            "extracted_answers": extracted_answers
        }
        
        logger.info("面试题文档处理完成", 
                   key_points=len(summary.get("key_points", [])),
                   questions=len(generated_questions))
        
        return result
    
    @staticmethod
    async def _extract_summary(content: str, segments: List[Dict]) -> Dict:
        """提取内容总结"""
        ai_service = get_ai_service()
        
        prompt = """请分析以下面试题文档，提取关键信息并总结。

请返回JSON格式，包含以下字段：
{
  "key_points": ["知识点1", "知识点2", ...],  // 关键知识点列表
  "question_types": {"选择题": 数量, "问答题": 数量, ...},  // 题型分布
  "difficulty": {"简单": 数量, "中等": 数量, "困难": 数量},  // 难度分布
  "total_questions": 总题目数,  // 题目总数
  "source_ids": [1, 2, 3],  // 引用的段落编号（可选）
  "confidence": 85  // 可信度分数(0-100)（可选）
}"""
        
        system_prompt = "你是一个面试题分析专家，擅长总结和分类技术面试题目。"
        
        try:
            summary = await ai_service.generate_with_sources(
                prompt=prompt,
                segments=segments,
                system_prompt=system_prompt,
                temperature=0.3,
                require_confidence=False  # 弱展示，不强制要求
            )
            
            # 验证和补充数据
            if "key_points" not in summary:
                summary["key_points"] = []
            if "question_types" not in summary:
                summary["question_types"] = {}
            if "difficulty" not in summary:
                summary["difficulty"] = {}
            if "total_questions" not in summary:
                summary["total_questions"] = 0
            
            # 弱展示：如果AI返回了可信度和来源，则计算并添加
            if "confidence" in summary or "source_ids" in summary:
                base_confidence = ConfidenceCalculator.normalize_confidence(
                    summary.get("confidence")
                )
                source_ids = summary.get("source_ids", [])
                
                confidence_result = ConfidenceCalculator.calculate_confidence(
                    base_confidence=base_confidence,
                    source_ids=source_ids,
                    segments=segments,
                    content=content,
                    ai_response=str(summary)
                )
                
                summary["confidence"] = confidence_result["score"]
                summary["confidence_label"] = confidence_result["label"]
                
                # 添加来源片段（弱展示）
                if source_ids:
                    source_segments = SourceSegmenter.get_segments_by_ids(segments, source_ids)
                    summary["sources"] = [
                        {
                            "id": seg["id"],
                            "text": seg["text"][:200] + "..." if len(seg["text"]) > 200 else seg["text"],  # 截断显示
                            "position": seg["position"]
                        }
                        for seg in source_segments
                    ]
                else:
                    summary["sources"] = []
            
            return summary
            
        except Exception as e:
            logger.error("内容总结失败", error=str(e))
            # 返回默认结构
            return {
                "key_points": [],
                "question_types": {},
                "difficulty": {},
                "total_questions": 0
            }
    
    @staticmethod
    async def _generate_questions(content: str, segments: List[Dict], summary: Dict) -> List[Dict]:
        """生成新问题"""
        ai_service = get_ai_service()
        
        key_points = summary.get("key_points", [])[:5]  # 取前5个知识点
        
        prompt = f"""基于以下面试题文档，生成3-5个新的相关问题。

关键知识点：{', '.join(key_points) if key_points else '无'}

请返回JSON格式的数组，每个问题包含：
{{
  "question": "问题内容",
  "hint": "提示或考察点",
  "source_ids": [1, 2, 3],  // 引用的段落编号（可选）
  "confidence": 85  // 可信度分数(0-100)（可选）
}}

生成的问题应该：
1. 与原文档相关但不同
2. 覆盖关键知识点
3. 难度适中
4. 具有实际考察价值"""
        
        system_prompt = "你是一个技术面试官，擅长设计高质量的技术面试题目。"
        
        try:
            questions = await ai_service.generate_with_sources(
                prompt=prompt,
                segments=segments,
                system_prompt=system_prompt,
                temperature=0.7,
                require_confidence=False  # 弱展示，不强制要求
            )
            
            # 确保返回列表格式
            if isinstance(questions, dict):
                questions = [questions]
            elif not isinstance(questions, list):
                questions = []
            
            # 限制数量
            questions = questions[:5]
            
            # 验证格式，添加可信度和来源（弱展示）
            validated_questions = []
            for q in questions:
                if isinstance(q, dict) and "question" in q:
                    question_item = {
                        "question": q.get("question", ""),
                        "hint": q.get("hint", "")
                    }
                    
                    # 弱展示：如果AI返回了可信度和来源，则添加
                    if "confidence" in q or "source_ids" in q:
                        base_confidence = ConfidenceCalculator.normalize_confidence(
                            q.get("confidence")
                        )
                        source_ids = q.get("source_ids", [])
                        
                        confidence_result = ConfidenceCalculator.calculate_confidence(
                            base_confidence=base_confidence,
                            source_ids=source_ids,
                            segments=segments,
                            content=content,
                            ai_response=str(q)
                        )
                        
                        question_item["confidence"] = confidence_result["score"]
                        question_item["confidence_label"] = confidence_result["label"]
                        
                        # 添加来源片段（弱展示，截断显示）
                        if source_ids:
                            source_segments = SourceSegmenter.get_segments_by_ids(segments, source_ids)
                            question_item["sources"] = [
                                {
                                    "id": seg["id"],
                                    "text": seg["text"][:200] + "..." if len(seg["text"]) > 200 else seg["text"],
                                    "position": seg["position"]
                                }
                                for seg in source_segments
                            ]
                        else:
                            question_item["sources"] = []
                    
                    validated_questions.append(question_item)
            
            return validated_questions
            
        except Exception as e:
            logger.error("问题生成失败", error=str(e))
            return []
    
    @staticmethod
    async def _extract_answers(content: str, segments: List[Dict]) -> List[Dict]:
        """提取答案"""
        ai_service = get_ai_service()
        
        prompt = """请从以下面试题文档中提取所有答案。

请返回JSON格式：
{
  "answers": ["答案1", "答案2", ...],
  "source_ids": [1, 2, 3],  // 引用的段落编号（可选）
  "confidence": 85  // 可信度分数(0-100)（可选）
}

如果没有找到答案，answers返回空数组 []。"""
        
        system_prompt = "你是一个文档分析专家，擅长从文档中提取结构化信息。"
        
        try:
            result = await ai_service.generate_with_sources(
                prompt=prompt,
                segments=segments,
                system_prompt=system_prompt,
                temperature=0.3,
                require_confidence=False  # 弱展示，不强制要求
            )
            
            # 提取answers列表
            if isinstance(result, dict) and "answers" in result:
                answers = result["answers"]
            elif isinstance(result, list):
                answers = result
            else:
                answers = []
            
            # 限制数量并转换为带可信度的格式
            answers_list = answers[:20]
            
            # 弱展示：如果AI返回了可信度和来源，则添加
            if isinstance(result, dict) and ("confidence" in result or "source_ids" in result):
                base_confidence = ConfidenceCalculator.normalize_confidence(
                    result.get("confidence")
                )
                source_ids = result.get("source_ids", [])
                
                confidence_result = ConfidenceCalculator.calculate_confidence(
                    base_confidence=base_confidence,
                    source_ids=source_ids,
                    segments=segments,
                    content=content,
                    ai_response=str(answers_list)
                )
                
                return {
                    "answers": answers_list,
                    "confidence": confidence_result["score"],
                    "confidence_label": confidence_result["label"],
                    "sources": [
                        {
                            "id": seg["id"],
                            "text": seg["text"][:200] + "..." if len(seg["text"]) > 200 else seg["text"],
                            "position": seg["position"]
                        }
                        for seg in SourceSegmenter.get_segments_by_ids(segments, source_ids)
                    ] if source_ids else []
                }
            else:
                # 兼容旧格式
                return {
                    "answers": answers_list,
                    "confidence": None,
                    "confidence_label": None,
                    "sources": []
                }
                
        except Exception as e:
            logger.error("答案提取失败", error=str(e))
            return {
                "answers": [],
                "confidence": None,
                "confidence_label": None,
                "sources": []
            }

