"""
面试题文档处理服务
- 内容总结
- 问题生成
- 答案提取
"""
from typing import Dict, List
import structlog
import json

from app.services.ai_service import get_ai_service

logger = structlog.get_logger()


class InterviewProcessor:
    """面试题文档处理器"""
    
    @staticmethod
    async def process(content: str) -> Dict:
        """
        处理面试题文档
        
        Args:
            content: 文档内容
        
        Returns:
            处理结果字典
        """
        logger.info("开始处理面试题文档", content_length=len(content))
        
        # 1. 内容总结
        summary = await InterviewProcessor._extract_summary(content)
        
        # 2. 问题生成
        generated_questions = await InterviewProcessor._generate_questions(content, summary)
        
        # 3. 答案提取
        extracted_answers = await InterviewProcessor._extract_answers(content)
        
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
    async def _extract_summary(content: str) -> Dict:
        """提取内容总结"""
        ai_service = get_ai_service()
        
        # 截取内容（避免过长）
        content_preview = content[:3000] if len(content) > 3000 else content
        
        prompt = f"""请分析以下面试题文档，提取关键信息并总结。

文档内容：
{content_preview}

请返回JSON格式，包含以下字段：
{{
  "key_points": ["知识点1", "知识点2", ...],  // 关键知识点列表
  "question_types": {{"选择题": 数量, "问答题": 数量, ...}},  // 题型分布
  "difficulty": {{"简单": 数量, "中等": 数量, "困难": 数量}},  // 难度分布
  "total_questions": 总题目数  // 题目总数
}}"""
        
        system_prompt = "你是一个面试题分析专家，擅长总结和分类技术面试题目。"
        
        try:
            summary = await ai_service.generate_json(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3
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
    async def _generate_questions(content: str, summary: Dict) -> List[Dict]:
        """生成新问题"""
        ai_service = get_ai_service()
        
        # 截取内容
        content_preview = content[:3000] if len(content) > 3000 else content
        key_points = summary.get("key_points", [])[:5]  # 取前5个知识点
        
        prompt = f"""基于以下面试题文档，生成3-5个新的相关问题。

原文档内容：
{content_preview}

关键知识点：{', '.join(key_points) if key_points else '无'}

请返回JSON格式的数组，每个问题包含：
{{
  "question": "问题内容",
  "hint": "提示或考察点"
}}

生成的问题应该：
1. 与原文档相关但不同
2. 覆盖关键知识点
3. 难度适中
4. 具有实际考察价值"""
        
        system_prompt = "你是一个技术面试官，擅长设计高质量的技术面试题目。"
        
        try:
            questions = await ai_service.generate_json(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.7
            )
            
            # 确保返回列表格式
            if isinstance(questions, dict):
                questions = [questions]
            elif not isinstance(questions, list):
                questions = []
            
            # 限制数量
            questions = questions[:5]
            
            # 验证格式
            validated_questions = []
            for q in questions:
                if isinstance(q, dict) and "question" in q:
                    validated_questions.append({
                        "question": q.get("question", ""),
                        "hint": q.get("hint", "")
                    })
            
            return validated_questions
            
        except Exception as e:
            logger.error("问题生成失败", error=str(e))
            return []
    
    @staticmethod
    async def _extract_answers(content: str) -> List[str]:
        """提取答案"""
        ai_service = get_ai_service()
        
        # 截取内容
        content_preview = content[:3000] if len(content) > 3000 else content
        
        prompt = f"""请从以下面试题文档中提取所有答案。

文档内容：
{content_preview}

请返回JSON格式的数组，包含所有找到的答案：
["答案1", "答案2", ...]

如果没有找到答案，返回空数组 []。"""
        
        system_prompt = "你是一个文档分析专家，擅长从文档中提取结构化信息。"
        
        try:
            answers = await ai_service.generate_json(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3
            )
            
            # 确保返回列表格式
            if isinstance(answers, list):
                return answers[:20]  # 限制数量
            elif isinstance(answers, dict) and "answers" in answers:
                return answers["answers"][:20]
            else:
                return []
                
        except Exception as e:
            logger.error("答案提取失败", error=str(e))
            return []

