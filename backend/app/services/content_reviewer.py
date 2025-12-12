"""
内容审核服务
- 审核生成结果的语言描述是否完整、有逻辑
- 使用 DeepSeek AI 进行内容质量审核
"""
from typing import Dict, List, Optional
import structlog
import json

from app.services.ai_service import get_ai_service

logger = structlog.get_logger()


class ContentReviewer:
    """内容审核器"""
    
    @staticmethod
    async def review_architecture_result(result_data: Dict) -> Dict:
        """
        审核架构文档处理结果
        
        Args:
            result_data: 处理结果数据
            
        Returns:
            审核结果，包含：
            - overall_score: 总体评分 (0-100)
            - is_acceptable: 是否可接受
            - issues: 问题列表
            - suggestions: 改进建议
            - detailed_review: 详细审核报告
        """
        ai_service = get_ai_service()
        
        # 提取关键字段
        plain_explanation = result_data.get('plain_explanation', '')
        architecture_view = result_data.get('architecture_view', '')
        config_steps = result_data.get('config_steps', [])
        components = result_data.get('components', [])
        checklist = result_data.get('checklist', [])
        
        # 构建审核提示词
        prompt = f"""请审核以下架构文档处理结果的内容质量。

## 处理结果内容：

### 1. 白话串讲（plain_explanation）：
{plain_explanation[:2000] if len(plain_explanation) > 2000 else plain_explanation}

### 2. 架构视图（architecture_view）：
{architecture_view[:2000] if len(architecture_view) > 2000 else architecture_view}

### 3. 配置步骤（config_steps）：
{json.dumps(config_steps[:5], ensure_ascii=False, indent=2) if config_steps else "无"}

### 4. 组件列表（components）：
{json.dumps(components[:5], ensure_ascii=False, indent=2) if components else "无"}

### 5. 检查清单（checklist）：
{json.dumps(checklist[:5], ensure_ascii=False, indent=2) if checklist else "无"}

## 审核要求：

请从以下维度审核内容质量：

1. **完整性**：
   - 内容是否完整，是否覆盖了文档的主要要点
   - 是否有明显的缺失或遗漏

2. **逻辑性**：
   - 内容是否有逻辑，条理是否清晰
   - 各部分之间是否有合理的关联
   - 是否有前后矛盾或逻辑混乱的地方

3. **准确性**：
   - 技术描述是否准确
   - 是否有明显的错误或误导性信息

4. **可读性**：
   - 语言是否流畅自然
   - 是否有胡言乱语、无意义的重复或混乱的表述
   - 是否符合中文表达习惯

5. **实用性**：
   - 内容是否对用户有帮助
   - 是否提供了有价值的信息

## 输出格式（JSON）：

请以 JSON 格式返回审核结果：

```json
{{
    "overall_score": 85,
    "is_acceptable": true,
    "issues": [
        {{
            "field": "plain_explanation",
            "severity": "medium",
            "description": "问题描述",
            "example": "具体的问题示例"
        }}
    ],
    "suggestions": [
        "改进建议1",
        "改进建议2"
    ],
    "detailed_review": {{
        "plain_explanation": {{
            "score": 80,
            "strengths": ["优点1", "优点2"],
            "weaknesses": ["缺点1", "缺点2"],
            "summary": "总体评价"
        }},
        "architecture_view": {{
            "score": 85,
            "strengths": ["优点1"],
            "weaknesses": ["缺点1"],
            "summary": "总体评价"
        }},
        "config_steps": {{
            "score": 90,
            "strengths": ["优点1"],
            "weaknesses": ["缺点1"],
            "summary": "总体评价"
        }}
    }}
}}
```

**重要**：
- 如果发现内容有明显问题（如胡言乱语、逻辑混乱、严重错误），请将 `is_acceptable` 设为 `false`
- 评分标准：90-100 优秀，80-89 良好，70-79 一般，60-69 较差，<60 不合格
- 请诚实、客观地评价，不要过度宽容
"""
        
        system_prompt = "你是一个专业的技术文档审核专家，擅长评估技术文档的内容质量、逻辑性和可读性。"
        
        try:
            response = await ai_service.generate_json(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3
            )
            
            # 验证响应格式
            if isinstance(response, dict):
                # 确保必要字段存在
                review_result = {
                    "overall_score": response.get("overall_score", 0),
                    "is_acceptable": response.get("is_acceptable", False),
                    "issues": response.get("issues", []),
                    "suggestions": response.get("suggestions", []),
                    "detailed_review": response.get("detailed_review", {})
                }
                
                logger.info("内容审核完成", 
                           overall_score=review_result["overall_score"],
                           is_acceptable=review_result["is_acceptable"],
                           issues_count=len(review_result["issues"]))
                
                return review_result
            else:
                logger.error("AI返回格式错误", response_type=type(response))
                return ContentReviewer._default_review_result()
                
        except Exception as e:
            logger.error("内容审核失败", error=str(e))
            return ContentReviewer._default_review_result()
    
    @staticmethod
    def _default_review_result() -> Dict:
        """默认审核结果（审核失败时返回）"""
        return {
            "overall_score": 0,
            "is_acceptable": False,
            "issues": [{
                "field": "system",
                "severity": "high",
                "description": "审核服务异常，无法完成审核",
                "example": ""
            }],
            "suggestions": ["请检查系统日志或联系管理员"],
            "detailed_review": {}
        }
    
    @staticmethod
    async def review_technical_result(result_data: Dict) -> Dict:
        """
        审核技术文档处理结果
        
        Args:
            result_data: 处理结果数据
            
        Returns:
            审核结果
        """
        # 类似架构文档的审核逻辑，但针对技术文档的字段
        # 暂时复用架构文档的审核逻辑
        return await ContentReviewer.review_architecture_result(result_data)
    
    @staticmethod
    async def review_interview_result(result_data: Dict) -> Dict:
        """
        审核面试文档处理结果
        
        Args:
            result_data: 处理结果数据
            
        Returns:
            审核结果
        """
        # 类似架构文档的审核逻辑，但针对面试文档的字段
        # 暂时复用架构文档的审核逻辑
        return await ContentReviewer.review_architecture_result(result_data)


def get_content_reviewer() -> ContentReviewer:
    """获取内容审核器实例"""
    return ContentReviewer()

