"""
技术实体提取服务
- 从文档内容中提取IT技术名词
- 支持多种提取方式
"""
from typing import List, Set, Dict
import structlog
import re
from app.utils.tech_name_utils import clean_tech_name

logger = structlog.get_logger()


class EntityExtractor:
    """技术实体提取器"""
    
    # 常见IT技术名词（用于增强提取）
    COMMON_TECH_TERMS = {
        # 编程语言
        'Python', 'Java', 'JavaScript', 'TypeScript', 'Go', 'Rust', 'C++', 'C#', 'PHP', 'Ruby', 'Swift', 'Kotlin',
        # 框架
        'React', 'Vue', 'Angular', 'Django', 'Flask', 'Spring', 'Spring Boot', 'Spring Cloud', 'Spring Cloud Stream', 
        'Express', 'FastAPI', 'Laravel', 'Gin', 'Echo', 'NestJS', 'Next.js', 'Nuxt.js',
        # 消息队列
        'RocketMQ', 'Kafka', 'RabbitMQ', 'ActiveMQ', 'MQ', 'Apache RocketMQ',
        # 数据库
        'MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Elasticsearch', 'SQLite', 'Oracle', 'Cassandra', 'InfluxDB',
        # 工具和平台
        'Docker', 'Kubernetes', 'Git', 'Jenkins', 'CI/CD', 'AWS', 'Azure', 'GCP', 'Maven', 'Gradle',
        # 技术栈
        'Node.js', 'Nginx', 'Apache', 'Linux', 'Windows', 'macOS', 'Tomcat', 'Jetty',
        # 其他
        'REST', 'GraphQL', 'gRPC', 'WebSocket', 'HTTP', 'HTTPS', 'TCP', 'UDP',
        # Spring 生态
        'Spring Messaging', 'Spring Framework', 'Hibernate', 'MyBatis', 'JPA'
    }
    
    @staticmethod
    async def extract_technologies_from_result(processing_result: Dict) -> List[str]:
        """
        从处理结果中提取技术名词
        
        Args:
            processing_result: 文档处理结果字典
        
        Returns:
            技术名词列表
        """
        technologies = set()
        
        # 1. 从技术文档的 related_technologies 字段提取
        if isinstance(processing_result, dict):
            if 'related_technologies' in processing_result:
                techs = processing_result['related_technologies']
                if isinstance(techs, list):
                    # 清理技术名词，移除中文翻译
                    for t in techs:
                        if t and isinstance(t, str):
                            tech_clean = clean_tech_name(t.strip())
                            if tech_clean:
                                technologies.add(tech_clean)
            
            # 2. 从架构文档的 components 字段提取组件名称和技术名词
            if 'components' in processing_result:
                components = processing_result['components']
                if isinstance(components, list):
                    for comp in components:
                        if isinstance(comp, dict):
                            # 提取组件名称
                            if 'name' in comp:
                                name = comp['name'].strip()
                                if name:
                                    # 清理技术名词，移除中文翻译
                                    name_clean = clean_tech_name(name)
                                    if name_clean:
                                        technologies.add(name_clean)
                                        # 从组件名称中提取技术名词（如 "Spring Boot 业务应用" -> "Spring Boot"）
                                        extracted = EntityExtractor._extract_tech_from_text(name_clean)
                                        technologies.update(extracted)
                            
                            # 提取组件描述中的技术名词
                            if 'description' in comp:
                                desc = comp.get('description', '')
                                if isinstance(desc, str):
                                    extracted = EntityExtractor._extract_tech_from_text(desc)
                                    technologies.update(extracted)
                            
                            # 提取依赖中的技术名词
                            if 'dependencies' in comp:
                                deps = comp.get('dependencies', [])
                                if isinstance(deps, list):
                                    for dep in deps:
                                        if isinstance(dep, str):
                                            # 清理技术名词，移除中文翻译
                                            dep_clean = clean_tech_name(dep.strip())
                                            if dep_clean:
                                                technologies.add(dep_clean)
                                                extracted = EntityExtractor._extract_tech_from_text(dep_clean)
                                                technologies.update(extracted)
            
            # 3. 从前置条件中提取技术名词
            if 'prerequisites' in processing_result:
                prereqs = processing_result['prerequisites']
                if isinstance(prereqs, dict):
                    for key in ['required', 'recommended']:
                        if key in prereqs and isinstance(prereqs[key], list):
                            for item in prereqs[key]:
                                if isinstance(item, str):
                                    # 尝试提取技术名词
                                    extracted = EntityExtractor._extract_tech_from_text(item)
                                    technologies.update(extracted)
        
        return list(technologies)
    
    @staticmethod
    async def extract_technologies_from_content(content: str) -> List[str]:
        """
        从文档内容中提取技术名词（使用AI）
        
        Args:
            content: 文档内容
        
        Returns:
            技术名词列表
        """
        from app.services.ai_service import get_ai_service
        
        try:
            ai_service = get_ai_service()
            content_preview = content[:2000] if len(content) > 2000 else content
            
            prompt = f"""请从以下文档内容中，提取所有提到的IT技术名词、框架、工具、平台等。

文档内容：
{content_preview}

请返回JSON格式的数组，包含所有提取到的技术名词：
["技术名词1", "技术名词2", ...]

要求：
1. 只提取IT相关的技术名词（编程语言、框架、工具、平台、数据库等）
2. 去除重复项
3. 使用标准的技术名称（如 "Python" 而不是 "python"）
4. 必须使用英文原名，不要翻译技术名词（如 "Spring Boot" 而不是 "Spring Boot（春波特）"）
5. 如果没有技术名词，返回空数组 []

只返回JSON数组，不要其他内容。"""
            
            system_prompt = "你是一个技术专家，擅长识别和提取IT技术名词。"
            
            try:
                result = await ai_service.generate_json(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=0.3
                )
                
                if isinstance(result, list):
                    # 清理和验证技术名词
                    technologies = []
                    for tech in result:
                        if isinstance(tech, str) and tech.strip():
                            tech_clean = clean_tech_name(tech)
                            # 过滤掉太短或太长的词
                            if 2 <= len(tech_clean) <= 50:
                                technologies.append(tech_clean)
                    return technologies
                elif isinstance(result, dict) and 'technologies' in result:
                    return result['technologies']
                else:
                    return []
                    
            except Exception as e:
                logger.warning("AI提取技术名词失败，使用规则提取", error=str(e))
                return EntityExtractor._extract_tech_from_text(content)
                
        except Exception as e:
            logger.warning("技术名词提取失败，使用规则提取", error=str(e))
            return EntityExtractor._extract_tech_from_text(content)
    
    @staticmethod
    def _extract_tech_from_text(text: str) -> List[str]:
        """使用规则从文本中提取技术名词"""
        technologies = set()
        text_upper = text.upper()
        
        # 检查常见技术名词（优先匹配完整名称，如 "Spring Boot" 优先于 "Spring"）
        # 按长度排序，先匹配长的技术名词
        sorted_techs = sorted(EntityExtractor.COMMON_TECH_TERMS, key=len, reverse=True)
        for tech in sorted_techs:
            # 使用单词边界匹配
            pattern = r'\b' + re.escape(tech) + r'\b'
            if re.search(pattern, text, re.IGNORECASE):
                technologies.add(tech)
        
        # 提取复合技术名词（如 "Spring Boot", "Spring Cloud Stream", "RocketMQ"）
        # 匹配：大写字母开头，可能包含空格或连字符，后跟字母数字
        compound_patterns = [
            r'\b[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)+\b',  # Spring Boot, Spring Cloud Stream
            r'\b[A-Z][A-Za-z]+[A-Z][A-Za-z]+\b',  # RocketMQ, NodeJS
        ]
        for pattern in compound_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                # 检查是否已经是已知技术名词
                if match in EntityExtractor.COMMON_TECH_TERMS:
                    technologies.add(match)
                # 检查是否包含已知技术名词（如 "Spring Boot 业务应用" -> "Spring Boot"）
                for tech in sorted_techs:
                    if tech.lower() in match.lower():
                        technologies.add(tech)
                        break
        
        # 提取大写字母开头的技术名词（如 Python, Docker）
        # 匹配：大写字母开头，后跟字母数字，长度2-30
        tech_pattern = r'\b[A-Z][A-Za-z0-9]{1,29}\b'
        matches = re.findall(tech_pattern, text)
        for match in matches:
            # 过滤掉常见的非技术词
            if match not in ['The', 'This', 'That', 'There', 'These', 'Those', 'When', 'Where', 'What', 'Which', 'Who', 'How']:
                # 过滤掉已经匹配的复合技术名词的一部分
                is_part_of_compound = False
                for tech in technologies:
                    if match in tech and match != tech:
                        is_part_of_compound = True
                        break
                if not is_part_of_compound and len(match) >= 2:
                    technologies.add(match)
        
        return list(technologies)


def get_entity_extractor() -> EntityExtractor:
    """获取实体提取器实例（单例模式）"""
    return EntityExtractor()

