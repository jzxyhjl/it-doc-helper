"""
IT技术文档处理服务
- 前置条件分析
- 学习路径规划
- 学习方法建议
"""
from typing import Dict, List, Optional
import structlog

from app.services.ai_service import get_ai_service
from app.services.source_segmenter import SourceSegmenter
from app.services.confidence_calculator import ConfidenceCalculator
from app.utils.tech_name_utils import clean_tech_name

logger = structlog.get_logger()


class TechnicalProcessor:
    """IT技术文档处理器"""
    
    @staticmethod
    async def process(content: str, stream_callback: Optional[callable] = None) -> Dict:
        """
        处理IT技术文档
        
        Args:
            content: 文档内容
        
        Returns:
            处理结果字典
        """
        logger.info("开始处理IT技术文档", content_length=len(content))
        
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
        
        # 1. 前置条件分析（带异常处理）
        try:
            prerequisites = await TechnicalProcessor._analyze_prerequisites(content, segments)
        except Exception as e:
            logger.error("前置条件分析失败，使用默认值", error=str(e))
            prerequisites = {
                "required": [],
                "recommended": [],
                "confidence": 50.0,
                "confidence_label": "中",
                "sources": []
            }
        
        # 2. 学习路径规划（带异常处理）
        try:
            learning_path = await TechnicalProcessor._plan_learning_path(content, segments, prerequisites)
        except Exception as e:
            logger.error("学习路径规划失败，使用默认值", error=str(e))
            learning_path = [
                {"stage": 1, "title": "基础阶段", "content": "学习基础知识", "confidence": 50.0, "confidence_label": "中", "sources": []},
                {"stage": 2, "title": "进阶阶段", "content": "深入学习", "confidence": 50.0, "confidence_label": "中", "sources": []},
                {"stage": 3, "title": "实践阶段", "content": "实际应用", "confidence": 50.0, "confidence_label": "中", "sources": []}
            ]
        
        # 3. 学习方法建议（带异常处理）
        try:
            learning_methods = await TechnicalProcessor._suggest_learning_methods(content, segments)
        except Exception as e:
            logger.error("学习方法建议失败，使用默认值", error=str(e))
            learning_methods = {
                "theory": "建议先理解基本概念，再深入学习。",
                "practice": "建议通过实际项目练习，加深理解。",
                "confidence": 50.0,
                "confidence_label": "中",
                "sources": []
            }
        
        # 4. 技术关联分析（带异常处理）
        try:
            related_tech_result = await TechnicalProcessor._analyze_related_technologies(content, segments)
        except Exception as e:
            logger.error("技术关联分析失败，使用默认值", error=str(e))
            related_tech_result = {
                "technologies": [],
                "confidence": 50.0,
                "confidence_label": "中",
                "sources": []
            }
        
        result = {
            "prerequisites": prerequisites,
            "learning_path": learning_path,
            "learning_methods": learning_methods,
            "related_technologies": related_tech_result
        }
        
        logger.info("IT技术文档处理完成", 
                   prerequisites_count=len(prerequisites.get("required", [])),
                   stages=len(learning_path))
        
        return result
    
    @staticmethod
    async def _analyze_prerequisites(content: str, segments: List[Dict]) -> Dict:
        """分析前置条件"""
        ai_service = get_ai_service()
        
        prompt = """请分析以下IT技术文档，识别学习该技术需要的前置知识。

请返回JSON格式：
{
  "required": ["必须掌握的基础知识1", "必须掌握的基础知识2", ...],  // 必须掌握
  "recommended": ["推荐掌握的基础知识1", ...],  // 推荐掌握
  "source_ids": [1, 2, 3],  // 引用的段落编号
  "confidence": 85  // 可信度分数(0-100)
}

要求：
1. 如果前置知识是技术名词（如 Spring Boot、RocketMQ、MySQL），必须使用标准的英文技术名称
2. 不要翻译技术名词，不要添加中文翻译（如不要写成 "Spring Boot（春波特）"）
3. 只使用英文原名，保持技术名词的原始形式
4. 必须返回source_ids和confidence字段

请从架构师或讲师的角度，准确识别学习该技术的前置条件。"""
        
        system_prompt = "你是一个资深的技术架构师和讲师，擅长分析技术学习的前置条件。"
        
        try:
            prerequisites = await ai_service.generate_with_sources(
                prompt=prompt,
                segments=segments,
                system_prompt=system_prompt,
                temperature=0.3,
                require_confidence=True
            )
            
            # 验证和补充，并清理技术名词
            if "required" not in prerequisites:
                prerequisites["required"] = []
            else:
                # 清理前置条件中的技术名词
                cleaned_required = []
                for item in prerequisites.get("required", []):
                    if isinstance(item, str):
                        cleaned = clean_tech_name(item)
                        if cleaned:
                            cleaned_required.append(cleaned)
                prerequisites["required"] = cleaned_required
            
            if "recommended" not in prerequisites:
                prerequisites["recommended"] = []
            else:
                # 清理推荐前置条件中的技术名词
                cleaned_recommended = []
                for item in prerequisites.get("recommended", []):
                    if isinstance(item, str):
                        cleaned = clean_tech_name(item)
                        if cleaned:
                            cleaned_recommended.append(cleaned)
                prerequisites["recommended"] = cleaned_recommended
            
            # 计算可信度
            base_confidence = ConfidenceCalculator.normalize_confidence(
                prerequisites.get("confidence")
            )
            source_ids = prerequisites.get("source_ids", [])
            
            confidence_result = ConfidenceCalculator.calculate_confidence(
                base_confidence=base_confidence,
                source_ids=source_ids,
                segments=segments,
                content=content,
                ai_response=str(prerequisites)
            )
            
            # 添加可信度和来源信息
            prerequisites["confidence"] = confidence_result["score"]
            prerequisites["confidence_label"] = confidence_result["label"]
            prerequisites["confidence_factors"] = confidence_result["factors"]
            
            # 添加来源片段
            if source_ids:
                source_segments = SourceSegmenter.get_segments_by_ids(segments, source_ids)
                prerequisites["sources"] = [
                    {
                        "id": seg["id"],
                        "text": seg["text"],
                        "position": seg["position"]
                    }
                    for seg in source_segments
                ]
            else:
                prerequisites["sources"] = []
            
            return prerequisites
            
        except Exception as e:
            logger.error("前置条件分析失败", error=str(e))
            return {
                "required": [],
                "recommended": []
            }
    
    @staticmethod
    async def _plan_learning_path(content: str, segments: List[Dict], prerequisites: Dict) -> List[Dict]:
        """规划学习路径"""
        ai_service = get_ai_service()
        
        required = prerequisites.get("required", [])
        
        prompt = f"""基于以下IT技术文档，制定一个循序渐进的学习路径。

前置知识：{', '.join(required) if required else '无特殊要求'}

请返回JSON格式的数组，包含至少3个学习阶段，每个阶段必须包含：
[
  {{
    "stage": 1,
    "title": "阶段标题",
    "content": "阶段学习内容描述，包括需要掌握的知识点和实践建议",
    "source_ids": [1, 2, 3],  // 引用的段落编号
    "confidence": 85  // 可信度分数(0-100)
  }},
  ...
]

学习路径应该：
1. 从基础到进阶，循序渐进
2. 每个阶段有明确的学习目标
3. 包含理论学习与实践建议
4. 从架构师或讲师的角度提供专业建议
5. 每个阶段必须返回source_ids和confidence字段"""
        
        system_prompt = "你是一个资深的技术架构师和讲师，擅长设计技术学习路径。"
        
        try:
            # 使用generate_json而不是generate_with_sources，因为需要返回数组
            learning_path = await ai_service.generate_json(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.5,
                require_sources=True,
                require_confidence=True
            )
            
            # 确保返回列表格式
            if isinstance(learning_path, dict):
                learning_path = [learning_path]
            elif not isinstance(learning_path, list):
                learning_path = []
            
            # 处理每个阶段，添加可信度和来源信息
            for stage in learning_path:
                if not isinstance(stage, dict):
                    continue
                # 确保有source_ids和confidence
                if "source_ids" not in stage:
                    stage["source_ids"] = []
                if "confidence" not in stage:
                    stage["confidence"] = 50
            
            # 验证和格式化，添加可信度和来源信息
            validated_path = []
            for stage in learning_path[:6]:  # 最多6个阶段
                if isinstance(stage, dict):
                    base_confidence = ConfidenceCalculator.normalize_confidence(
                        stage.get("confidence")
                    )
                    source_ids = stage.get("source_ids", [])
                    
                    # 计算可信度
                    confidence_result = ConfidenceCalculator.calculate_confidence(
                        base_confidence=base_confidence,
                        source_ids=source_ids,
                        segments=segments,
                        content=content,
                        ai_response=str(stage)
                    )
                    
                    # 获取来源片段
                    source_segments = []
                    if source_ids:
                        source_segments = SourceSegmenter.get_segments_by_ids(segments, source_ids)
                    
                    validated_path.append({
                        "stage": stage.get("stage", len(validated_path) + 1),
                        "title": stage.get("title", ""),
                        "content": stage.get("content", ""),
                        "confidence": confidence_result["score"],
                        "confidence_label": confidence_result["label"],
                        "confidence_factors": confidence_result["factors"],
                        "sources": [
                            {
                                "id": seg["id"],
                                "text": seg["text"],
                                "position": seg["position"]
                            }
                            for seg in source_segments
                        ]
                    })
            
            # 确保至少3个阶段
            if len(validated_path) < 3:
                # 补充默认阶段
                while len(validated_path) < 3:
                    validated_path.append({
                        "stage": len(validated_path) + 1,
                        "title": f"阶段{len(validated_path) + 1}",
                        "content": "待补充"
                    })
            
            return validated_path
            
        except Exception as e:
            logger.error("学习路径规划失败", error=str(e))
            return [
                {"stage": 1, "title": "基础阶段", "content": "学习基础知识"},
                {"stage": 2, "title": "进阶阶段", "content": "深入学习"},
                {"stage": 3, "title": "实践阶段", "content": "实际应用"}
            ]
    
    @staticmethod
    async def _suggest_learning_methods(content: str, segments: List[Dict]) -> Dict:
        """建议学习方法"""
        ai_service = get_ai_service()
        
        prompt = """基于以下IT技术文档，从架构师或讲师的角度，提供学习方法建议。

请返回JSON格式：
{
  "theory": "理论学习建议，包括如何理解概念、阅读文档等",
  "practice": "实践建议，包括动手实践、项目练习等",
  "source_ids": [1, 2, 3],  // 引用的段落编号
  "confidence": 85  // 可信度分数(0-100)
}

必须返回source_ids和confidence字段。"""
        
        system_prompt = "你是一个资深的技术架构师和讲师，擅长提供技术学习方法建议。"
        
        try:
            methods = await ai_service.generate_with_sources(
                prompt=prompt,
                segments=segments,
                system_prompt=system_prompt,
                temperature=0.6,
                require_confidence=True
            )
            
            # 验证和补充
            if "theory" not in methods:
                methods["theory"] = "建议先理解基本概念，再深入学习。"
            if "practice" not in methods:
                methods["practice"] = "建议通过实际项目练习，加深理解。"
            
            # 计算可信度
            base_confidence = ConfidenceCalculator.normalize_confidence(
                methods.get("confidence")
            )
            source_ids = methods.get("source_ids", [])
            
            confidence_result = ConfidenceCalculator.calculate_confidence(
                base_confidence=base_confidence,
                source_ids=source_ids,
                segments=segments,
                content=content,
                ai_response=str(methods)
            )
            
            # 添加可信度和来源信息
            methods["confidence"] = confidence_result["score"]
            methods["confidence_label"] = confidence_result["label"]
            methods["confidence_factors"] = confidence_result["factors"]
            
            # 添加来源片段
            if source_ids:
                source_segments = SourceSegmenter.get_segments_by_ids(segments, source_ids)
                methods["sources"] = [
                    {
                        "id": seg["id"],
                        "text": seg["text"],
                        "position": seg["position"]
                    }
                    for seg in source_segments
                ]
            else:
                methods["sources"] = []
            
            return methods
            
        except Exception as e:
            logger.error("学习方法建议失败", error=str(e))
            return {
                "theory": "建议先理解基本概念，再深入学习。",
                "practice": "建议通过实际项目练习，加深理解。"
            }
    
    @staticmethod
    async def _analyze_related_technologies(content: str, segments: List[Dict]) -> List[Dict]:
        """分析相关技术"""
        ai_service = get_ai_service()
        
        prompt = """请从以下IT技术文档中，识别与该技术相关的其他技术。

请返回JSON格式：
{
  "technologies": ["相关技术1", "相关技术2", ...],
  "source_ids": [1, 2, 3],  // 引用的段落编号
  "confidence": 85  // 可信度分数(0-100)
}

要求：
1. 必须使用标准的英文技术名称（如 "Spring Boot"、"RocketMQ"、"MySQL"）
2. 不要翻译技术名词，不要添加中文翻译（如不要写成 "Spring Boot（春波特）"）
3. 只使用英文原名，保持技术名词的原始形式
4. 必须返回source_ids和confidence字段

如果没有相关技术，technologies返回空数组 []。"""
        
        system_prompt = "你是一个技术专家，擅长识别技术之间的关联关系。必须使用标准的英文技术名称，不要翻译技术名词。"
        
        try:
            result = await ai_service.generate_with_sources(
                prompt=prompt,
                segments=segments,
                system_prompt=system_prompt,
                temperature=0.4,
                require_confidence=True
            )
            
            # 提取technologies列表
            if isinstance(result, dict) and "technologies" in result:
                technologies = result["technologies"]
            elif isinstance(result, list):
                technologies = result
            else:
                technologies = []
            
            # 清理技术名词，移除中文翻译
            cleaned_techs = []
            for tech in technologies:
                if isinstance(tech, str) and tech.strip():
                    tech_clean = clean_tech_name(tech)
                    if tech_clean and 2 <= len(tech_clean) <= 50:
                        cleaned_techs.append(tech_clean)
            
            # 计算可信度
            base_confidence = ConfidenceCalculator.normalize_confidence(
                result.get("confidence") if isinstance(result, dict) else None
            )
            source_ids = result.get("source_ids", []) if isinstance(result, dict) else []
            
            confidence_result = ConfidenceCalculator.calculate_confidence(
                base_confidence=base_confidence,
                source_ids=source_ids,
                segments=segments,
                content=content,
                ai_response=str(cleaned_techs)
            )
            
            # 获取来源片段
            source_segments = []
            if source_ids:
                source_segments = SourceSegmenter.get_segments_by_ids(segments, source_ids)
            
            # 返回带可信度和来源信息的结果
            return {
                "technologies": cleaned_techs[:10],  # 限制数量
                "confidence": confidence_result["score"],
                "confidence_label": confidence_result["label"],
                "confidence_factors": confidence_result["factors"],
                "sources": [
                    {
                        "id": seg["id"],
                        "text": seg["text"],
                        "position": seg["position"]
                    }
                    for seg in source_segments
                ]
            }
                
        except Exception as e:
            logger.error("技术关联分析失败", error=str(e))
            return []

