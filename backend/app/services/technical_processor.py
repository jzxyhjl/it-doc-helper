"""
IT技术文档处理服务
- 前置条件分析
- 学习路径规划
- 学习方法建议
"""
from typing import Dict, List
import structlog

from app.services.ai_service import get_ai_service
from app.utils.tech_name_utils import clean_tech_name

logger = structlog.get_logger()


class TechnicalProcessor:
    """IT技术文档处理器"""
    
    @staticmethod
    async def process(content: str) -> Dict:
        """
        处理IT技术文档
        
        Args:
            content: 文档内容
        
        Returns:
            处理结果字典
        """
        logger.info("开始处理IT技术文档", content_length=len(content))
        
        # 1. 前置条件分析
        prerequisites = await TechnicalProcessor._analyze_prerequisites(content)
        
        # 2. 学习路径规划
        learning_path = await TechnicalProcessor._plan_learning_path(content, prerequisites)
        
        # 3. 学习方法建议
        learning_methods = await TechnicalProcessor._suggest_learning_methods(content)
        
        # 4. 技术关联分析
        related_technologies = await TechnicalProcessor._analyze_related_technologies(content)
        
        result = {
            "prerequisites": prerequisites,
            "learning_path": learning_path,
            "learning_methods": learning_methods,
            "related_technologies": related_technologies
        }
        
        logger.info("IT技术文档处理完成", 
                   prerequisites_count=len(prerequisites.get("required", [])),
                   stages=len(learning_path))
        
        return result
    
    @staticmethod
    async def _analyze_prerequisites(content: str) -> Dict:
        """分析前置条件"""
        ai_service = get_ai_service()
        
        content_preview = content[:3000] if len(content) > 3000 else content
        
        prompt = f"""请分析以下IT技术文档，识别学习该技术需要的前置知识。

文档内容：
{content_preview}

请返回JSON格式：
{{
  "required": ["必须掌握的基础知识1", "必须掌握的基础知识2", ...],  // 必须掌握
  "recommended": ["推荐掌握的基础知识1", ...]  // 推荐掌握
}}

要求：
1. 如果前置知识是技术名词（如 Spring Boot、RocketMQ、MySQL），必须使用标准的英文技术名称
2. 不要翻译技术名词，不要添加中文翻译（如不要写成 "Spring Boot（春波特）"）
3. 只使用英文原名，保持技术名词的原始形式

请从架构师或讲师的角度，准确识别学习该技术的前置条件。"""
        
        system_prompt = "你是一个资深的技术架构师和讲师，擅长分析技术学习的前置条件。"
        
        try:
            prerequisites = await ai_service.generate_json(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3
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
            
            return prerequisites
            
        except Exception as e:
            logger.error("前置条件分析失败", error=str(e))
            return {
                "required": [],
                "recommended": []
            }
    
    @staticmethod
    async def _plan_learning_path(content: str, prerequisites: Dict) -> List[Dict]:
        """规划学习路径"""
        ai_service = get_ai_service()
        
        content_preview = content[:3000] if len(content) > 3000 else content
        required = prerequisites.get("required", [])
        
        prompt = f"""基于以下IT技术文档，制定一个循序渐进的学习路径。

文档内容：
{content_preview}

前置知识：{', '.join(required) if required else '无特殊要求'}

请返回JSON格式的数组，包含至少3个学习阶段：
[
  {{
    "stage": 1,
    "title": "阶段标题",
    "content": "阶段学习内容描述，包括需要掌握的知识点和实践建议"
  }},
  ...
]

学习路径应该：
1. 从基础到进阶，循序渐进
2. 每个阶段有明确的学习目标
3. 包含理论学习与实践建议
4. 从架构师或讲师的角度提供专业建议"""
        
        system_prompt = "你是一个资深的技术架构师和讲师，擅长设计技术学习路径。"
        
        try:
            learning_path = await ai_service.generate_json(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.5
            )
            
            # 确保返回列表格式
            if isinstance(learning_path, dict):
                learning_path = [learning_path]
            elif not isinstance(learning_path, list):
                learning_path = []
            
            # 验证和格式化
            validated_path = []
            for stage in learning_path[:6]:  # 最多6个阶段
                if isinstance(stage, dict):
                    validated_path.append({
                        "stage": stage.get("stage", len(validated_path) + 1),
                        "title": stage.get("title", ""),
                        "content": stage.get("content", "")
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
    async def _suggest_learning_methods(content: str) -> Dict:
        """建议学习方法"""
        ai_service = get_ai_service()
        
        content_preview = content[:2000] if len(content) > 2000 else content
        
        prompt = f"""基于以下IT技术文档，从架构师或讲师的角度，提供学习方法建议。

文档内容：
{content_preview}

请返回JSON格式：
{{
  "theory": "理论学习建议，包括如何理解概念、阅读文档等",
  "practice": "实践建议，包括动手实践、项目练习等"
}}"""
        
        system_prompt = "你是一个资深的技术架构师和讲师，擅长提供技术学习方法建议。"
        
        try:
            methods = await ai_service.generate_json(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.6
            )
            
            # 验证和补充
            if "theory" not in methods:
                methods["theory"] = "建议先理解基本概念，再深入学习。"
            if "practice" not in methods:
                methods["practice"] = "建议通过实际项目练习，加深理解。"
            
            return methods
            
        except Exception as e:
            logger.error("学习方法建议失败", error=str(e))
            return {
                "theory": "建议先理解基本概念，再深入学习。",
                "practice": "建议通过实际项目练习，加深理解。"
            }
    
    @staticmethod
    async def _analyze_related_technologies(content: str) -> List[str]:
        """分析相关技术"""
        ai_service = get_ai_service()
        
        content_preview = content[:2000] if len(content) > 2000 else content
        
        prompt = f"""请从以下IT技术文档中，识别与该技术相关的其他技术。

文档内容：
{content_preview}

请返回JSON格式的数组：
["相关技术1", "相关技术2", ...]

要求：
1. 必须使用标准的英文技术名称（如 "Spring Boot"、"RocketMQ"、"MySQL"）
2. 不要翻译技术名词，不要添加中文翻译（如不要写成 "Spring Boot（春波特）"）
3. 只使用英文原名，保持技术名词的原始形式

如果没有相关技术，返回空数组 []。"""
        
        system_prompt = "你是一个技术专家，擅长识别技术之间的关联关系。必须使用标准的英文技术名称，不要翻译技术名词。"
        
        try:
            technologies = await ai_service.generate_json(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.4
            )
            
            # 确保返回列表格式，并清理技术名词
            if isinstance(technologies, list):
                # 清理技术名词，移除中文翻译
                cleaned_techs = []
                for tech in technologies:
                    if isinstance(tech, str) and tech.strip():
                        tech_clean = clean_tech_name(tech)
                        if tech_clean and 2 <= len(tech_clean) <= 50:
                            cleaned_techs.append(tech_clean)
                return cleaned_techs[:10]  # 限制数量
            elif isinstance(technologies, dict) and "technologies" in technologies:
                techs = technologies["technologies"]
                if isinstance(techs, list):
                    cleaned_techs = []
                    for tech in techs:
                        if isinstance(tech, str) and tech.strip():
                            tech_clean = clean_tech_name(tech)
                            if tech_clean and 2 <= len(tech_clean) <= 50:
                                cleaned_techs.append(tech_clean)
                    return cleaned_techs[:10]
            return []
                
        except Exception as e:
            logger.error("技术关联分析失败", error=str(e))
            return []

