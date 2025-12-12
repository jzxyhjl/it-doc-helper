"""
架构分析服务
- 从架构师视角分析技术栈
- 提取架构层次和上下游关系
"""
from typing import Dict, List, Optional
import structlog
import re
from app.utils.tech_name_utils import clean_tech_name

from app.services.ai_service import get_ai_service

logger = structlog.get_logger()


class ArchitectureAnalyzer:
    """架构分析器"""
    
    # 架构层次定义
    ARCHITECTURE_LAYERS = {
        'application': {'name': '应用层', 'color': '#3B82F6', 'order': 1},
        'middleware': {'name': '中间件层', 'color': '#10B981', 'order': 2},
        'framework': {'name': '框架层', 'color': '#F59E0B', 'order': 3},
        'infrastructure': {'name': '基础设施层', 'color': '#8B5CF6', 'order': 4},
        'database': {'name': '数据层', 'color': '#EF4444', 'order': 5},
        'other': {'name': '其他', 'color': '#6B7280', 'order': 6}
    }
    
    @staticmethod
    async def analyze_architecture(
        content: str,
        components: Optional[List[Dict]] = None,
        related_technologies: Optional[List[str]] = None
    ) -> Dict:
        """
        从架构师视角分析技术栈
        
        Args:
            content: 文档内容
            components: 组件列表（可选）
            related_technologies: 相关技术列表（可选）
        
        Returns:
            架构分析结果，包含：
            - technologies: 技术列表（带层次信息）
            - relationships: 上下游关系
            - layers: 架构层次
        """
        ai_service = get_ai_service()
        
        content_preview = content[:4000] if len(content) > 4000 else content
        components_info = ""
        if components:
            components_info = "\n".join([
                f"- {c.get('name', '')}: {c.get('description', '')}" 
                for c in components[:10]
            ])
        
        techs_info = ""
        if related_technologies:
            techs_info = ", ".join(related_technologies[:20])
        
        prompt = f"""请从架构师的视角，分析以下文档中的技术栈架构。

文档内容：
{content_preview}

已识别组件：
{components_info if components_info else "无"}

已识别技术：
{techs_info if techs_info else "无"}

请返回JSON格式，包含以下内容：
{{
  "technologies": [
    {{
      "name": "技术名称",
      "layer": "application|middleware|framework|infrastructure|database|other",
      "description": "技术描述",
      "position": "在架构中的位置和作用"
    }},
    ...
  ],
  "relationships": [
    {{
      "from": "上游技术名称",
      "to": "下游技术名称",
      "type": "dependency|call|dataflow|integration",
      "description": "关系描述",
      "strength": 0.0-1.0
    }},
    ...
  ],
  "summary": "整体架构总结（1-2句话）"
}}

要求：
1. 技术分层：
   - application: 业务应用层（如 Spring Boot 应用、业务服务）
   - middleware: 中间件层（如消息队列、缓存、API网关）
   - framework: 框架层（如 Spring、Spring Boot、Spring Cloud）
   - infrastructure: 基础设施层（如 Docker、Kubernetes、CI/CD）
   - database: 数据层（如 MySQL、Redis、MongoDB）
   - other: 其他

2. 上下游关系：
   - dependency: 依赖关系（如 Spring Boot 依赖 Spring）
   - call: 调用关系（如应用调用消息队列）
   - dataflow: 数据流（如应用 -> 消息队列 -> 数据库）
   - integration: 集成关系（如 Spring Cloud Stream 集成 RocketMQ）

3. 技术名称要求：
   - 必须使用标准的英文技术名称（如 "Spring Boot"、"RocketMQ"、"MySQL"）
   - 不要翻译技术名词，不要添加中文翻译（如不要写成 "Spring Boot（春波特）"）
   - 只使用英文原名，保持技术名词的原始形式

4. 只返回JSON，不要其他内容。"""
        
        system_prompt = """你是一个资深的技术架构师，擅长分析技术栈的架构层次和上下游关系。
请从实际开发场景和架构设计的角度，准确识别技术之间的层次关系和依赖关系。"""
        
        try:
            result = await ai_service.generate_json(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3
            )
            
            if not isinstance(result, dict):
                logger.warning("AI返回格式不正确，使用默认分析")
                return ArchitectureAnalyzer._default_analysis(content, components, related_technologies)
            
            # 验证和清理数据
            technologies = result.get('technologies', [])
            relationships = result.get('relationships', [])
            summary = result.get('summary', '')
            
            # 验证技术列表
            validated_techs = []
            for tech in technologies:
                if isinstance(tech, dict) and 'name' in tech:
                    layer = tech.get('layer', 'other')
                    if layer not in ArchitectureAnalyzer.ARCHITECTURE_LAYERS:
                        layer = 'other'
                    
                    # 清理技术名称：移除中文翻译（如 "Spring Boot（春波特）" -> "Spring Boot"）
                    tech_name = clean_tech_name(tech.get('name', ''))
                    
                    validated_techs.append({
                        'name': tech_name,
                        'layer': layer,
                        'description': tech.get('description', '').strip(),
                        'position': tech.get('position', '').strip()
                    })
            
            # 验证关系列表
            validated_rels = []
            for rel in relationships:
                if isinstance(rel, dict) and 'from' in rel and 'to' in rel:
                    # 清理技术名称：移除中文翻译
                    from_tech = clean_tech_name(rel.get('from', ''))
                    to_tech = clean_tech_name(rel.get('to', ''))
                    
                    validated_rels.append({
                        'from': from_tech,
                        'to': to_tech,
                        'type': rel.get('type', 'integration'),
                        'description': rel.get('description', '').strip(),
                        'strength': min(1.0, max(0.0, float(rel.get('strength', 0.5))))
                    })
            
            return {
                'technologies': validated_techs,
                'relationships': validated_rels,
                'summary': summary.strip()
            }
            
        except Exception as e:
            logger.error("架构分析失败，使用默认分析", error=str(e))
            return ArchitectureAnalyzer._default_analysis(content, components, related_technologies)
    
    @staticmethod
    def _default_analysis(
        content: str,
        components: Optional[List[Dict]] = None,
        related_technologies: Optional[List[str]] = None
    ) -> Dict:
        """默认分析（当AI分析失败时使用）"""
        from app.services.tech_relationship_service import get_tech_relationship_service
        
        techs = related_technologies or []
        if not techs and components:
            from app.services.entity_extractor import EntityExtractor
            for comp in components:
                if isinstance(comp, dict) and 'name' in comp:
                    techs.extend(EntityExtractor._extract_tech_from_text(comp['name']))
        
        relationship_service = get_tech_relationship_service()
        
        technologies = []
        relationships = []
        
        for tech in techs[:20]:
            # 根据技术名称推断层次
            layer = ArchitectureAnalyzer._infer_layer(tech)
            technologies.append({
                'name': tech,
                'layer': layer,
                'description': '',
                'position': ''
            })
        
        # 生成基本关系
        for i, tech1 in enumerate(techs):
            for j, tech2 in enumerate(techs):
                if i >= j:
                    continue
                strength = relationship_service.get_relationship_strength_sync(tech1, tech2)
                if strength >= 0.3:
                    # 推断关系类型
                    rel_type = ArchitectureAnalyzer._infer_relationship_type(tech1, tech2, strength)
                    relationships.append({
                        'from': tech1,
                        'to': tech2,
                        'type': rel_type,
                        'description': '',
                        'strength': strength
                    })
        
        return {
            'technologies': technologies,
            'relationships': relationships,
            'summary': '技术栈架构分析'
        }
    
    @staticmethod
    def _infer_layer(tech: str) -> str:
        """根据技术名称推断架构层次"""
        tech_lower = tech.lower()
        
        # 应用层
        if any(x in tech_lower for x in ['app', 'application', 'service', '业务']):
            return 'application'
        
        # 框架层
        if any(x in tech_lower for x in ['spring', 'framework', 'boot', 'cloud']):
            return 'framework'
        
        # 中间件层
        if any(x in tech_lower for x in ['mq', 'kafka', 'rabbit', 'redis', 'cache', 'gateway']):
            return 'middleware'
        
        # 数据层
        if any(x in tech_lower for x in ['mysql', 'postgres', 'mongo', 'database', 'db']):
            return 'database'
        
        # 基础设施层
        if any(x in tech_lower for x in ['docker', 'kubernetes', 'k8s', 'ci/cd', 'jenkins']):
            return 'infrastructure'
        
        return 'other'
    
    @staticmethod
    def _infer_relationship_type(tech1: str, tech2: str, strength: float) -> str:
        """推断关系类型"""
        tech1_lower = tech1.lower()
        tech2_lower = tech2.lower()
        
        # 依赖关系
        if any(x in tech1_lower for x in ['spring', 'boot']) and any(x in tech2_lower for x in ['spring']):
            return 'dependency'
        
        # 数据流
        if any(x in tech1_lower for x in ['app', 'service']) and any(x in tech2_lower for x in ['mq', 'kafka', 'database']):
            return 'dataflow'
        
        # 调用关系
        if strength >= 0.7:
            return 'call'
        
        return 'integration'


def get_architecture_analyzer() -> ArchitectureAnalyzer:
    """获取架构分析器实例（单例模式）"""
    return ArchitectureAnalyzer()

