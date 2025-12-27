"""
文档视角分类器（主次视角识别）
"""
from typing import Optional, Dict, Any, List
import re
import hashlib
import json
import structlog

logger = structlog.get_logger()


class DocumentViewClassifier:
    """
    文档视角分类器（重构后的命名）
    
    核心逻辑：
    - 主类型 → 默认 view
    - 次特征 → 可选 view
    - 例如：判断为技术文档 → 默认 learning view → 如果组件关键词多，再加 system view
    """
    
    @staticmethod
    def detect_qa_structure(content: str) -> float:
        """
        检测 Q&A 结构特征
        
        特征：
        - 问题-答案对（问号+答案）
        - 选择题格式（A/B/C/D选项）
        - 常见问题关键词
        
        Returns:
            得分 0.0-1.0
        """
        score = 0.0
        content_lower = content.lower()
        
        # 检测问题-答案对
        qa_patterns = [
            r'[？?].*?[答案|Answer|answer]',
            r'问题\d+[:：].*?答案\d+[:：]',
            r'Q\d+[:：].*?A\d+[:：]',
        ]
        qa_matches = sum(1 for pattern in qa_patterns if re.search(pattern, content))
        score += min(qa_matches * 0.2, 0.6)
        
        # 检测选择题格式
        choice_patterns = [
            r'[A-D][\.、]',
            r'[①②③④]',
            r'\([A-D]\)',
        ]
        choice_matches = sum(1 for pattern in choice_patterns if re.search(pattern, content))
        score += min(choice_matches * 0.1, 0.4)
        
        # 检测问题关键词
        question_keywords = [
            '问题', '题目', '试题', '问', '答案', '解析',
            'question', 'answer', 'solution', 'explanation'
        ]
        keyword_count = sum(1 for keyword in question_keywords if keyword in content_lower)
        score += min(keyword_count * 0.05, 0.3)
        
        return min(score, 1.0)
    
    @staticmethod
    def detect_component_relationships(content: str) -> float:
        """
        检测系统组件关系特征
        
        特征：
        - 组件、模块、服务等关键词
        - 依赖关系描述
        - 架构图、拓扑图相关
        
        Returns:
            得分 0.0-1.0
        """
        score = 0.0
        content_lower = content.lower()
        
        # 组件关系关键词
        component_keywords = [
            '组件', '模块', '服务', '微服务', '组件间', '模块间',
            'component', 'module', 'service', 'microservice',
            '依赖', '依赖关系', '依赖图', 'dependency',
            '架构', '架构图', '拓扑', 'topology', 'architecture'
        ]
        keyword_count = sum(1 for keyword in component_keywords if keyword in content_lower)
        score += min(keyword_count * 0.15, 0.7)
        
        # 检测架构描述模式
        arch_patterns = [
            r'[组件|模块|服务].*?[连接|通信|调用]',
            r'[架构|设计].*?[包含|包括]',
        ]
        arch_matches = sum(1 for pattern in arch_patterns if re.search(pattern, content))
        score += min(arch_matches * 0.15, 0.3)
        
        return min(score, 1.0)
    
    @staticmethod
    def detect_usage_flow(content: str) -> float:
        """
        检测使用流程特征
        
        特征：
        - 步骤、流程、操作序列
        - 教程、指南、入门相关
        - 安装、配置、使用说明
        
        Returns:
            得分 0.0-1.0
        """
        score = 0.0
        content_lower = content.lower()
        
        # 流程关键词
        flow_keywords = [
            '步骤', '流程', '操作', '教程', '指南', '入门',
            'step', 'process', 'tutorial', 'guide', 'getting started',
            '安装', '配置', '使用', '使用说明',
            'install', 'setup', 'configuration', 'usage'
        ]
        keyword_count = sum(1 for keyword in flow_keywords if keyword in content_lower)
        score += min(keyword_count * 0.12, 0.6)
        
        # 检测步骤序列
        step_patterns = [
            r'步骤\d+[:：]',
            r'第[一二三四五六七八九十\d]+步',
            r'Step \d+[:：]',
        ]
        step_matches = sum(1 for pattern in step_patterns if re.search(pattern, content))
        score += min(step_matches * 0.1, 0.4)
        
        return min(score, 1.0)
    
    @staticmethod
    def generate_cache_key_from_scores(
        document_id: str,
        detection_scores: Dict[str, float]
    ) -> str:
        """
        生成缓存key（基于系统检测的特征得分，不基于推荐结果）
        
        难点2解决方案：
        - 缓存key基于系统检测的原始得分
        - 不包含推荐结果（主视角、次视角等）
        - 系统检测才是算力与存储的边界
        
        Args:
            document_id: 文档ID
            detection_scores: 系统检测的特征得分
        
        Returns:
            str: 缓存key
        """
        # 基于检测得分生成key（不包含推荐逻辑）
        score_str = json.dumps(detection_scores, sort_keys=True)
        score_hash = hashlib.md5(score_str.encode()).hexdigest()
        
        return f"doc:{document_id}:detection:{score_hash}"
    
    @staticmethod
    async def recommend_views(
        content: str,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        推荐处理视角（重构后的命名和逻辑）
        
        核心逻辑：
        - 主类型 → 默认 view
        - 次特征 → 可选 view
        - 例如：判断为技术文档 → 默认 learning view → 如果组件关键词多，再加 system view
        
        难点2解决方案：
        - 系统检测的特征得分用于UI和算力分配决策
        - 主视角用于UI初始状态和算力分配，但不影响存储
        - 缓存key基于系统检测的特征得分，不基于推荐结果
        - 系统检测才是算力与存储的边界
        
        Args:
            content: 文档内容
            api_key: AI API密钥（可选）
            api_base: AI API基础URL（可选）
        
        Returns:
            {
                'primary_view': 'learning|qa|system',  # 主视角（用于UI初始状态和算力分配）
                'enabled_views': ['learning', 'system'],  # 启用的视角列表（检测到哪些就生成哪些）
                'detection_scores': {...},  # 系统检测的原始得分（用于缓存key）
                'cache_key': '...',  # 基于检测得分生成的缓存key
                'method': 'rule|ai|hybrid',
                'type_mapping': 'technical',  # 向后兼容：主类型
                'secondary_types': ['architecture']  # 向后兼容：次类型
            }
        """
        # 1. 系统检测特征得分（这是算力与存储的边界）
        detection_scores = {
            'qa': DocumentViewClassifier.detect_qa_structure(content),
            'system': DocumentViewClassifier.detect_component_relationships(content),
            'learning': DocumentViewClassifier.detect_usage_flow(content)
        }
        
        # 2. 生成缓存key（基于检测得分，不基于推荐）- 难点2解决方案
        # 注意：这里需要document_id，但在这个方法中我们没有，所以先不生成
        # 在实际使用时，会在调用处传入document_id后生成cache_key
        
        # 3. 确定主类型（向后兼容）
        # 映射关系：technical → learning, interview → qa, architecture → system
        type_scores = {
            'technical': detection_scores['learning'],
            'interview': detection_scores['qa'],
            'architecture': detection_scores['system']
        }
        primary_type = max(type_scores, key=type_scores.get)
        
        # 4. 主类型 → 默认 view（用于UI和算力分配）
        type_to_view = {
            'technical': 'learning',
            'interview': 'qa',
            'architecture': 'system'
        }
        primary_view = type_to_view[primary_type]
        
        # 5. 次特征 → 可选 view（检测到哪些就生成哪些）
        enabled_views = [primary_view]  # 至少包含主视角
        
        # 如果其他视角得分 >= 0.3，也启用
        view_threshold = 0.3
        for view, score in detection_scores.items():
            if view != primary_view and score >= view_threshold:
                enabled_views.append(view)
        
        # 6. 如果主视角置信度低，使用AI（可选）
        if detection_scores[primary_view] < 0.5 and api_key:
            ai_result = await DocumentViewClassifier.ai_recommend_views(
                content, api_key, api_base
            )
            if ai_result:
                return ai_result
        
        # 7. 返回推荐结果
        return {
            'primary_view': primary_view,  # 用于UI初始状态和算力分配
            'enabled_views': enabled_views,  # 用于算力分配
            'detection_scores': detection_scores,  # 系统检测的原始得分（用于缓存key）
            'method': 'rule',
            'type_mapping': primary_type,  # 向后兼容
            'secondary_types': [
                t for t, s in type_scores.items() 
                if t != primary_type and s >= view_threshold
            ]
        }
    
    @staticmethod
    async def ai_recommend_views(
        content: str,
        api_key: str,
        api_base: str
    ) -> Optional[Dict[str, Any]]:
        """
        使用AI推荐视角（重构后的命名）
        
        Args:
            content: 文档内容
            api_key: AI API密钥
            api_base: AI API基础URL
        
        Returns:
            推荐结果，格式与recommend_views一致
        """
        # TODO: 实现AI推荐逻辑
        # 这里可以调用DeepSeek API进行更精确的视角识别
        logger.info("AI推荐视角（待实现）", content_length=len(content))
        return None

