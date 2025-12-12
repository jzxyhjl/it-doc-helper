"""
技术栈关联关系服务
- 定义技术之间的实际关联关系（基于架构师/开发者的视角）
- 提供技术栈组合知识库
"""
from typing import Dict, List, Tuple, Set
import structlog

logger = structlog.get_logger()


class TechRelationshipService:
    """技术栈关联关系服务"""
    
    # 技术栈关联关系定义（基于实际开发场景）
    TECH_RELATIONSHIPS: Dict[str, List[Tuple[str, float]]] = {
        # 编程语言 -> 常用框架/工具
        'Java': [
            ('Spring', 0.9), ('Spring Boot', 0.9), ('Maven', 0.8), ('Gradle', 0.7),
            ('Hibernate', 0.7), ('MyBatis', 0.6), ('Tomcat', 0.7), ('Jetty', 0.5),
            ('MySQL', 0.6), ('PostgreSQL', 0.5), ('Redis', 0.6), ('Kafka', 0.5)
        ],
        'JavaScript': [
            ('Node.js', 0.9), ('React', 0.8), ('Vue', 0.7), ('Angular', 0.6),
            ('Express', 0.8), ('NPM', 0.9), ('Webpack', 0.7), ('TypeScript', 0.7),
            ('MongoDB', 0.6), ('Redis', 0.5), ('Docker', 0.6)
        ],
        'TypeScript': [
            ('React', 0.8), ('Vue', 0.7), ('Angular', 0.8), ('Node.js', 0.8),
            ('NestJS', 0.7), ('Express', 0.6)
        ],
        'Python': [
            ('Django', 0.8), ('Flask', 0.7), ('FastAPI', 0.7), ('Pandas', 0.6),
            ('NumPy', 0.6), ('TensorFlow', 0.5), ('PyTorch', 0.5), ('PostgreSQL', 0.5),
            ('Redis', 0.5), ('Celery', 0.6), ('Docker', 0.6)
        ],
        'Go': [
            ('Gin', 0.7), ('Echo', 0.6), ('GORM', 0.6), ('Docker', 0.7),
            ('Kubernetes', 0.6), ('gRPC', 0.6), ('PostgreSQL', 0.5), ('Redis', 0.5)
        ],
        'C++': [
            ('CMake', 0.7), ('Boost', 0.6), ('Qt', 0.5), ('OpenCV', 0.5),
            ('Docker', 0.4)
        ],
        'C#': [
            ('.NET', 0.9), ('ASP.NET', 0.8), ('Entity Framework', 0.7),
            ('SQL Server', 0.6), ('Azure', 0.6)
        ],
        'Rust': [
            ('Cargo', 0.9), ('Tokio', 0.7), ('Actix', 0.6), ('Docker', 0.5)
        ],
        'PHP': [
            ('Laravel', 0.8), ('Symfony', 0.6), ('Composer', 0.8), ('MySQL', 0.7)
        ],
        
        # 框架 -> 相关技术
        'Spring': [
            ('Java', 0.9), ('Spring Boot', 0.9), ('Maven', 0.8), ('MySQL', 0.6),
            ('PostgreSQL', 0.5), ('Redis', 0.6), ('Docker', 0.6)
        ],
        'Spring Boot': [
            ('Java', 0.9), ('Spring', 0.9), ('Maven', 0.8), ('MySQL', 0.6),
            ('PostgreSQL', 0.5), ('Redis', 0.6), ('Docker', 0.7),
            ('RocketMQ', 0.7), ('Kafka', 0.6), ('Spring Cloud Stream', 0.8)
        ],
        'Spring Cloud Stream': [
            ('Spring Boot', 0.8), ('Spring', 0.8), ('Java', 0.8),
            ('RocketMQ', 0.9), ('Kafka', 0.8), ('RabbitMQ', 0.7)
        ],
        'React': [
            ('JavaScript', 0.8), ('TypeScript', 0.7), ('Node.js', 0.7),
            ('Webpack', 0.7), ('NPM', 0.8), ('Redux', 0.6), ('Docker', 0.5)
        ],
        'Vue': [
            ('JavaScript', 0.7), ('TypeScript', 0.6), ('Node.js', 0.6),
            ('Webpack', 0.6), ('NPM', 0.7)
        ],
        'Angular': [
            ('TypeScript', 0.8), ('Node.js', 0.7), ('NPM', 0.7), ('RxJS', 0.6)
        ],
        'Django': [
            ('Python', 0.8), ('PostgreSQL', 0.6), ('Redis', 0.5), ('Celery', 0.6),
            ('Docker', 0.6)
        ],
        'Flask': [
            ('Python', 0.7), ('PostgreSQL', 0.5), ('Redis', 0.5), ('Docker', 0.5)
        ],
        'FastAPI': [
            ('Python', 0.7), ('PostgreSQL', 0.5), ('Redis', 0.5), ('Docker', 0.6)
        ],
        'Node.js': [
            ('JavaScript', 0.9), ('TypeScript', 0.7), ('Express', 0.8),
            ('NPM', 0.9), ('MongoDB', 0.6), ('Redis', 0.6), ('Docker', 0.7)
        ],
        'Express': [
            ('Node.js', 0.8), ('JavaScript', 0.8), ('MongoDB', 0.6), ('Redis', 0.5)
        ],
        
        # 消息队列 -> 相关技术
        'RocketMQ': [
            ('Spring Boot', 0.7), ('Spring Cloud Stream', 0.9), ('Java', 0.7),
            ('Spring', 0.7), ('Docker', 0.6), ('Kubernetes', 0.5)
        ],
        'Kafka': [
            ('Spring Boot', 0.6), ('Java', 0.6), ('Docker', 0.6),
            ('Kubernetes', 0.6), ('Spring Cloud Stream', 0.8)
        ],
        'RabbitMQ': [
            ('Spring Boot', 0.6), ('Java', 0.6), ('Python', 0.5),
            ('Docker', 0.5)
        ],
        'MQ': [
            ('RocketMQ', 0.8), ('Kafka', 0.7), ('RabbitMQ', 0.7),
            ('Spring Boot', 0.6), ('Java', 0.6)
        ],
        
        # 数据库 -> 相关技术
        'MySQL': [
            ('Java', 0.6), ('Spring', 0.6), ('PHP', 0.7), ('Python', 0.5),
            ('Docker', 0.5)
        ],
        'PostgreSQL': [
            ('Python', 0.5), ('Django', 0.6), ('Java', 0.5), ('Go', 0.5),
            ('Docker', 0.5)
        ],
        'MongoDB': [
            ('Node.js', 0.6), ('JavaScript', 0.6), ('Express', 0.6), ('Docker', 0.5)
        ],
        'Redis': [
            ('Java', 0.6), ('Spring', 0.6), ('Python', 0.5), ('Node.js', 0.6),
            ('Docker', 0.5)
        ],
        
        # 工具和平台
        'Docker': [
            ('Kubernetes', 0.7), ('Java', 0.6), ('Python', 0.6), ('Node.js', 0.7),
            ('Go', 0.7), ('MySQL', 0.5), ('PostgreSQL', 0.5), ('Redis', 0.5)
        ],
        'Kubernetes': [
            ('Docker', 0.7), ('Go', 0.6), ('Java', 0.5), ('Python', 0.5)
        ],
        'Git': [
            ('GitHub', 0.7), ('GitLab', 0.6), ('Jenkins', 0.5), ('CI/CD', 0.6)
        ],
        'Jenkins': [
            ('CI/CD', 0.8), ('Docker', 0.6), ('Git', 0.5), ('Kubernetes', 0.5)
        ],
        'AWS': [
            ('Docker', 0.6), ('Kubernetes', 0.5), ('MySQL', 0.4), ('Redis', 0.4)
        ],
        'Azure': [
            ('.NET', 0.6), ('C#', 0.6), ('Docker', 0.5), ('Kubernetes', 0.4)
        ],
    }
    
    # 技术栈组合（常见的技术栈）
    TECH_STACKS: List[Dict[str, any]] = [
        {
            'name': 'Java Spring Boot 全栈',
            'technologies': ['Java', 'Spring Boot', 'Spring', 'Maven', 'MySQL', 'Redis', 'Docker'],
            'weight': 0.9
        },
        {
            'name': 'Node.js 全栈',
            'technologies': ['Node.js', 'JavaScript', 'Express', 'MongoDB', 'Redis', 'Docker'],
            'weight': 0.9
        },
        {
            'name': 'React 前端',
            'technologies': ['React', 'JavaScript', 'TypeScript', 'Node.js', 'Webpack', 'NPM'],
            'weight': 0.9
        },
        {
            'name': 'Python Django 全栈',
            'technologies': ['Python', 'Django', 'PostgreSQL', 'Redis', 'Celery', 'Docker'],
            'weight': 0.9
        },
        {
            'name': 'Go 微服务',
            'technologies': ['Go', 'Gin', 'PostgreSQL', 'Redis', 'Docker', 'Kubernetes', 'gRPC'],
            'weight': 0.8
        },
        {
            'name': 'Vue 前端',
            'technologies': ['Vue', 'JavaScript', 'TypeScript', 'Node.js', 'Webpack', 'NPM'],
            'weight': 0.8
        },
    ]
    
    @staticmethod
    async def get_relationship_strength(tech1: str, tech2: str, use_ai: bool = False) -> float:
        """
        获取两个技术之间的关联强度
        
        Args:
            tech1: 技术1
            tech2: 技术2
            use_ai: 是否使用AI获取最新关联关系（默认False，使用静态定义）
            
        Returns:
            关联强度 (0.0 - 1.0)
        """
        # 如果启用AI，尝试从AI获取
        if use_ai:
            try:
                from app.services.tech_relationship_updater import get_tech_relationship_updater
                updater = get_tech_relationship_updater()
                relationships = await updater.get_updated_relationships(tech1)
                for related_tech, strength in relationships:
                    if related_tech.lower() == tech2.lower():
                        return strength
            except Exception as e:
                logger.warning("AI获取关联关系失败，使用静态定义", tech1=tech1, tech2=tech2, error=str(e))
        
        # 检查直接关联（静态定义）
        if tech1 in TechRelationshipService.TECH_RELATIONSHIPS:
            for related_tech, strength in TechRelationshipService.TECH_RELATIONSHIPS[tech1]:
                if related_tech.lower() == tech2.lower():
                    return strength
        
        # 检查反向关联
        if tech2 in TechRelationshipService.TECH_RELATIONSHIPS:
            for related_tech, strength in TechRelationshipService.TECH_RELATIONSHIPS[tech2]:
                if related_tech.lower() == tech1.lower():
                    return strength
        
        # 检查技术栈组合
        for stack in TechRelationshipService.TECH_STACKS:
            techs = [t.lower() for t in stack['technologies']]
            if tech1.lower() in techs and tech2.lower() in techs:
                # 在同一个技术栈中，给予基础关联强度
                return stack['weight'] * 0.6
        
        # 默认：同类技术有弱关联
        tech1_type = TechRelationshipService._get_tech_type(tech1)
        tech2_type = TechRelationshipService._get_tech_type(tech2)
        
        if tech1_type == tech2_type and tech1_type != 'other':
            return 0.3  # 同类技术有弱关联
        
        return 0.0  # 无关联
    
    @staticmethod
    def get_relationship_strength_sync(tech1: str, tech2: str) -> float:
        """
        同步版本：获取两个技术之间的关联强度（不使用AI）
        
        Args:
            tech1: 技术1
            tech2: 技术2
            
        Returns:
            关联强度 (0.0 - 1.0)
        """
        # 检查直接关联
        if tech1 in TechRelationshipService.TECH_RELATIONSHIPS:
            for related_tech, strength in TechRelationshipService.TECH_RELATIONSHIPS[tech1]:
                if related_tech.lower() == tech2.lower():
                    return strength
        
        # 检查反向关联
        if tech2 in TechRelationshipService.TECH_RELATIONSHIPS:
            for related_tech, strength in TechRelationshipService.TECH_RELATIONSHIPS[tech2]:
                if related_tech.lower() == tech1.lower():
                    return strength
        
        # 检查技术栈组合
        for stack in TechRelationshipService.TECH_STACKS:
            techs = [t.lower() for t in stack['technologies']]
            if tech1.lower() in techs and tech2.lower() in techs:
                return stack['weight'] * 0.6
        
        # 默认：同类技术有弱关联
        tech1_type = TechRelationshipService._get_tech_type(tech1)
        tech2_type = TechRelationshipService._get_tech_type(tech2)
        
        if tech1_type == tech2_type and tech1_type != 'other':
            return 0.3
        
        return 0.0
    
    @staticmethod
    def _get_tech_type(tech: str) -> str:
        """获取技术类型"""
        tech_lower = tech.lower()
        
        # 编程语言
        if tech_lower in ['java', 'javascript', 'typescript', 'python', 'go', 'rust', 'c++', 'c#', 'php', 'ruby', 'swift', 'kotlin']:
            return 'language'
        
        # 框架
        elif tech_lower in ['react', 'vue', 'angular', 'django', 'flask', 'spring', 'express', 'fastapi', 'laravel', 'gin', 'echo']:
            return 'framework'
        
        # 数据库
        elif tech_lower in ['mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch', 'sqlite', 'oracle']:
            return 'database'
        
        # 工具和平台
        elif tech_lower in ['docker', 'kubernetes', 'git', 'jenkins', 'aws', 'azure', 'gcp', 'nginx', 'apache']:
            return 'tool'
        
        return 'other'
    
    @staticmethod
    def get_related_technologies(tech: str, limit: int = 10) -> List[Tuple[str, float]]:
        """
        获取与指定技术相关的技术列表
        
        Args:
            tech: 技术名称
            limit: 返回数量限制
            
        Returns:
            [(技术名称, 关联强度), ...]
        """
        relationships = []
        
        # 从直接关联中获取
        if tech in TechRelationshipService.TECH_RELATIONSHIPS:
            relationships.extend(TechRelationshipService.TECH_RELATIONSHIPS[tech])
        
        # 从反向关联中获取
        for related_tech, related_list in TechRelationshipService.TECH_RELATIONSHIPS.items():
            for rt, strength in related_list:
                if rt.lower() == tech.lower():
                    relationships.append((related_tech, strength))
        
        # 去重并排序
        tech_strength_map = {}
        for rt, strength in relationships:
            rt_lower = rt.lower()
            if rt_lower not in tech_strength_map or strength > tech_strength_map[rt_lower][1]:
                tech_strength_map[rt_lower] = (rt, strength)
        
        result = sorted(tech_strength_map.values(), key=lambda x: x[1], reverse=True)
        return result[:limit]


def get_tech_relationship_service() -> TechRelationshipService:
    """获取技术关联关系服务实例（单例模式）"""
    return TechRelationshipService()

