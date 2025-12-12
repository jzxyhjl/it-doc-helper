"""
文档类型识别服务
结合规则匹配和AI判断
"""
from typing import Optional, Dict
import structlog
import re
import json

logger = structlog.get_logger()


class DocumentClassifier:
    """文档类型分类器"""
    
    # 面试题关键词
    INTERVIEW_KEYWORDS = [
        '面试', '题目', '试题', '答案', '解析', '考点', '知识点',
        '选择题', '问答题', '编程题', '算法题', '面经',
        'interview', 'question', 'answer', 'solution'
    ]
    
    # 技术文档关键词
    TECHNICAL_KEYWORDS = [
        '教程', '指南', '文档', 'API', '框架', '库', '工具',
        '使用', '配置', '安装', '入门', '进阶', '最佳实践',
        'tutorial', 'guide', 'documentation', 'api', 'framework',
        'library', 'getting started', 'how to'
    ]
    
    # 架构文档关键词
    ARCHITECTURE_KEYWORDS = [
        '架构', '设计', '系统', '组件', '模块', '服务', '部署',
        '配置', '环境', '搭建', '安装', '启动', '运行',
        'architecture', 'design', 'system', 'component', 'module',
        'service', 'deployment', 'setup', 'installation'
    ]
    
    @staticmethod
    def rule_based_classify(content: str) -> Optional[Dict[str, float]]:
        """
        基于规则的文档类型识别
        
        Returns:
            Dict with type and confidence, or None if cannot determine
        """
        content_lower = content.lower()
        
        # 统计关键词出现次数
        interview_score = sum(1 for keyword in DocumentClassifier.INTERVIEW_KEYWORDS 
                              if keyword in content_lower)
        technical_score = sum(1 for keyword in DocumentClassifier.TECHNICAL_KEYWORDS 
                             if keyword in content_lower)
        architecture_score = sum(1 for keyword in DocumentClassifier.ARCHITECTURE_KEYWORDS 
                                if keyword in content_lower)
        
        # 计算置信度
        total_score = interview_score + technical_score + architecture_score
        if total_score == 0:
            return None
        
        scores = {
            'interview': interview_score / total_score,
            'technical': technical_score / total_score,
            'architecture': architecture_score / total_score
        }
        
        # 返回得分最高的类型
        max_type = max(scores, key=scores.get)
        max_score = scores[max_type]
        
        # 如果最高分太低，返回None
        if max_score < 0.3:
            return None
        
        return {
            'type': max_type,
            'confidence': max_score,
            'method': 'rule'
        }
    
    @staticmethod
    async def ai_classify(content: str, api_key: str, api_base: str) -> Optional[Dict[str, float]]:
        """
        使用AI进行文档类型识别
        
        Args:
            content: 文档内容（截取前2000字符）
            api_key: DeepSeek API密钥
            api_base: DeepSeek API基础URL
        
        Returns:
            Dict with type and confidence, or None if failed
        """
        try:
            from openai import OpenAI
            
            # 截取内容（避免过长）
            content_preview = content[:2000] if len(content) > 2000 else content
            
            client = OpenAI(
                api_key=api_key,
                base_url=api_base
            )
            
            prompt = f"""请分析以下文档内容，判断文档类型。文档类型包括：
1. interview（面试题文档）- 包含技术面试题目、答案、解析等
2. technical（IT技术文档）- 介绍特定技术、框架、工具的学习文档
3. architecture（架构/搭建文档）- 描述系统架构设计或系统搭建配置的文档

文档内容：
{content_preview}

请只返回JSON格式，包含type（类型）和confidence（置信度0-1）：
{{"type": "interview|technical|architecture", "confidence": 0.0-1.0}}"""
            
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是一个文档类型识别专家，请准确判断文档类型。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=100
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # 解析JSON响应
            # 尝试提取JSON
            json_match = re.search(r'\{[^}]+\}', result_text)
            if json_match:
                result = json.loads(json_match.group())
                result['method'] = 'ai'
                return result
            else:
                logger.warning("AI返回格式不正确", response=result_text)
                return None
                
        except Exception as e:
            logger.error("AI识别失败", error=str(e))
            return None
    
    @staticmethod
    async def classify(
        content: str,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None
    ) -> Dict[str, any]:
        """
        混合识别策略：规则优先，AI补充
        
        Args:
            content: 文档内容
            api_key: DeepSeek API密钥（可选）
            api_base: DeepSeek API基础URL（可选）
        
        Returns:
            Dict包含: type, confidence, method
        """
        # 首先尝试规则匹配
        rule_result = DocumentClassifier.rule_based_classify(content)
        
        if rule_result and rule_result['confidence'] >= 0.5:
            logger.info("规则识别成功", type=rule_result['type'], confidence=rule_result['confidence'])
            return rule_result
        
        # 如果规则识别置信度低，使用AI
        if api_key and api_base:
            ai_result = await DocumentClassifier.ai_classify(content, api_key, api_base)
            if ai_result:
                logger.info("AI识别成功", type=ai_result['type'], confidence=ai_result['confidence'])
                return ai_result
        
        # 如果都失败，返回规则结果（即使置信度低）或unknown
        if rule_result:
            logger.info("使用规则识别结果（置信度较低）", type=rule_result['type'], confidence=rule_result['confidence'])
            return rule_result
        
        logger.warning("无法识别文档类型，返回unknown")
        return {
            'type': 'unknown',
            'confidence': 0.0,
            'method': 'none'
        }

