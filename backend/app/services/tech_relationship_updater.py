"""
技术栈关联关系更新服务
- 通过 AI 动态获取最新的技术栈关联关系
- 支持定期更新和按需更新
"""
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import structlog
import json

from app.services.ai_service import get_ai_service
from app.services.tech_relationship_service import TechRelationshipService

logger = structlog.get_logger()


class TechRelationshipUpdater:
    """技术栈关联关系更新器"""
    
    # 缓存时间（天）
    CACHE_DURATION_DAYS = 30
    
    @staticmethod
    async def get_updated_relationships(
        tech: str,
        force_update: bool = False
    ) -> List[Tuple[str, float]]:
        """
        获取指定技术的最新关联关系（通过 AI）
        
        Args:
            tech: 技术名称
            force_update: 是否强制更新（忽略缓存）
        
        Returns:
            [(相关技术, 关联强度), ...]
        """
        from app.models.tech_relationship_cache import TechRelationshipCache
        from sqlalchemy import select
        from app.core.database import get_db
        
        # TODO: 从数据库获取缓存（如果实现了缓存表）
        # 这里先直接调用 AI 获取
        
        try:
            ai_service = get_ai_service()
            
            prompt = f"""请从架构师和开发者的角度，分析以下技术在2024-2025年的实际使用场景和关联关系。

技术名称：{tech}

请返回JSON格式的数组，包含与该技术最相关的其他技术及其关联强度（0.0-1.0）：
[
  {{"technology": "相关技术1", "strength": 0.9, "reason": "关联原因"}},
  {{"technology": "相关技术2", "strength": 0.7, "reason": "关联原因"}},
  ...
]

要求：
1. 只返回IT相关的技术（编程语言、框架、工具、平台、数据库、消息队列等）
2. 关联强度基于实际开发场景中的使用频率和必要性
3. 强度范围：0.0-1.0（0.9+ 强关联，0.7-0.9 中等关联，0.3-0.7 弱关联）
4. 最多返回15个相关技术
5. 使用标准的技术名称（如 "Spring Boot" 而不是 "springboot"）

只返回JSON数组，不要其他内容。"""
            
            system_prompt = """你是一个资深的技术架构师和开发者，熟悉各种技术栈的实际使用场景。
请基于2024-2025年的技术发展趋势和实际项目经验，分析技术之间的关联关系。"""
            
            result = await ai_service.generate_json(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3
            )
            
            relationships = []
            if isinstance(result, list):
                for item in result:
                    if isinstance(item, dict):
                        tech_name = item.get('technology') or item.get('tech') or item.get('name')
                        strength = item.get('strength') or item.get('weight') or item.get('score')
                        if tech_name and strength is not None:
                            try:
                                strength_float = float(strength)
                                if 0.0 <= strength_float <= 1.0:
                                    relationships.append((tech_name, strength_float))
                            except (ValueError, TypeError):
                                continue
            
            logger.info("AI获取技术关联关系成功", 
                       tech=tech, 
                       relationships_count=len(relationships))
            
            return relationships
            
        except Exception as e:
            logger.error("AI获取技术关联关系失败", tech=tech, error=str(e))
            # 失败时返回静态定义
            return TechRelationshipService.get_related_technologies(tech, limit=10)
    
    @staticmethod
    async def update_relationship_for_tech(tech: str) -> Dict[str, List[Tuple[str, float]]]:
        """
        更新指定技术的关联关系
        
        Args:
            tech: 技术名称
        
        Returns:
            更新后的关联关系字典
        """
        relationships = await TechRelationshipUpdater.get_updated_relationships(tech)
        
        # 更新静态定义（临时，实际应该存储到数据库）
        if tech not in TechRelationshipService.TECH_RELATIONSHIPS:
            TechRelationshipService.TECH_RELATIONSHIPS[tech] = []
        
        # 合并AI获取的关系和静态定义
        existing_relationships = {rel[0]: rel[1] for rel in TechRelationshipService.TECH_RELATIONSHIPS[tech]}
        ai_relationships = {rel[0]: rel[1] for rel in relationships}
        
        # 合并：AI结果优先，但保留静态定义中AI没有提到的关系
        merged = {}
        for tech_name, strength in ai_relationships.items():
            merged[tech_name] = strength
        
        # 保留静态定义中强度较高的关系（如果AI没有提到）
        for tech_name, strength in existing_relationships.items():
            if tech_name not in merged and strength >= 0.7:
                merged[tech_name] = strength
        
        # 转换回列表格式
        updated_relationships = [(tech_name, strength) for tech_name, strength in merged.items()]
        updated_relationships.sort(key=lambda x: x[1], reverse=True)
        
        TechRelationshipService.TECH_RELATIONSHIPS[tech] = updated_relationships[:15]
        
        logger.info("技术关联关系更新完成", 
                   tech=tech, 
                   relationships_count=len(updated_relationships))
        
        return {tech: updated_relationships}
    
    @staticmethod
    async def batch_update_relationships(
        techs: List[str],
        use_cache: bool = True
    ) -> Dict[str, List[Tuple[str, float]]]:
        """
        批量更新多个技术的关联关系
        
        Args:
            techs: 技术名称列表
            use_cache: 是否使用缓存
        
        Returns:
            更新后的关联关系字典
        """
        results = {}
        
        for tech in techs:
            try:
                updated = await TechRelationshipUpdater.update_relationship_for_tech(tech)
                results.update(updated)
            except Exception as e:
                logger.error("批量更新技术关联关系失败", tech=tech, error=str(e))
                # 继续处理下一个技术
        
        return results


def get_tech_relationship_updater() -> TechRelationshipUpdater:
    """获取技术关联关系更新器实例（单例模式）"""
    return TechRelationshipUpdater()

