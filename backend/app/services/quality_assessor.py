"""
处理结果质量评估服务
- 内容完整性检查
- 内容长度检查
- 结构规范性检查
"""
from typing import Dict, Optional
import structlog
from app.services.view_registry import ViewRegistry

logger = structlog.get_logger()


class QualityAssessor:
    """质量评估器"""
    
    @staticmethod
    async def assess_quality(document_type: str, result_data: Dict) -> int:
        """
        评估处理结果质量
        
        Args:
            document_type: 文档类型（interview/technical/architecture）或视角名称（向后兼容）
            result_data: 处理结果数据
        
        Returns:
            质量分数（0-100）
        """
        logger.info("开始评估处理结果质量", document_type=document_type)
        
        try:
            # 兼容处理：如果document_type是view名称，转换为类型
            if document_type in ViewRegistry.TYPE_TO_VIEW_MAP.values():
                document_type = ViewRegistry.get_type_mapping(document_type)
            
            # 根据类型选择评估方法（保持向后兼容的类型判断）
            if document_type == "interview":
                score = await QualityAssessor._assess_interview_quality(result_data)
            elif document_type == "technical":
                score = await QualityAssessor._assess_technical_quality(result_data)
            elif document_type == "architecture":
                score = await QualityAssessor._assess_architecture_quality(result_data)
            else:
                # 未知类型，使用通用评估
                score = await QualityAssessor._assess_generic_quality(result_data)
            
            logger.info("质量评估完成", document_type=document_type, quality_score=score)
            return score
            
        except Exception as e:
            logger.error("质量评估失败", error=str(e), document_type=document_type)
            # 评估失败时返回默认分数50
            return 50
    
    @staticmethod
    async def _assess_interview_quality(result_data: Dict) -> int:
        """
        评估面试题文档处理结果质量
        
        评估规则：
        1. 内容完整性（40分）：是否有summary、generated_questions、extracted_answers
        2. 内容长度（30分）：各字段内容是否足够详细
        3. 结构规范性（30分）：数据格式是否正确
        """
        score = 0
        
        # 1. 内容完整性检查（40分）
        completeness_score = 0
        required_fields = ["summary", "generated_questions", "extracted_answers"]
        for field in required_fields:
            if field in result_data and result_data[field]:
                completeness_score += 13  # 每个字段13分，共40分（约）
        
        # summary字段检查
        if "summary" in result_data and result_data["summary"]:
            summary = result_data["summary"]
            if isinstance(summary, dict):
                if "key_points" in summary and summary["key_points"]:
                    completeness_score += 2
                if "total_questions" in summary and summary["total_questions"] > 0:
                    completeness_score += 2
        completeness_score = min(completeness_score, 40)  # 最多40分
        
        # 2. 内容长度检查（30分）
        length_score = 0
        if "summary" in result_data and result_data["summary"]:
            summary_str = str(result_data["summary"])
            if len(summary_str) > 100:
                length_score += 10
            elif len(summary_str) > 50:
                length_score += 5
        
        if "generated_questions" in result_data and result_data["generated_questions"]:
            questions = result_data["generated_questions"]
            if isinstance(questions, list):
                if len(questions) >= 5:
                    length_score += 10
                elif len(questions) >= 2:
                    length_score += 5
        
        if "extracted_answers" in result_data and result_data["extracted_answers"]:
            answers = result_data["extracted_answers"]
            if isinstance(answers, list):
                if len(answers) >= 3:
                    length_score += 10
                elif len(answers) >= 1:
                    length_score += 5
        
        length_score = min(length_score, 30)  # 最多30分
        
        # 3. 结构规范性检查（30分）
        structure_score = 0
        if "summary" in result_data:
            summary = result_data["summary"]
            if isinstance(summary, dict):
                structure_score += 10
                if "key_points" in summary and isinstance(summary["key_points"], list):
                    structure_score += 5
                if "total_questions" in summary and isinstance(summary["total_questions"], (int, float)):
                    structure_score += 5
        
        if "generated_questions" in result_data:
            questions = result_data["generated_questions"]
            if isinstance(questions, list):
                structure_score += 5
                # 检查问题格式
                if questions and isinstance(questions[0], dict):
                    structure_score += 5
        
        structure_score = min(structure_score, 30)  # 最多30分
        
        score = completeness_score + length_score + structure_score
        return min(score, 100)  # 确保不超过100分
    
    @staticmethod
    async def _assess_technical_quality(result_data: Dict) -> int:
        """
        评估IT技术文档处理结果质量
        
        评估规则：
        1. 内容完整性（40分）：是否有prerequisites、learning_path、learning_methods、related_technologies
        2. 内容长度（30分）：各字段内容是否足够详细
        3. 结构规范性（30分）：数据格式是否正确
        """
        score = 0
        
        # 1. 内容完整性检查（40分）
        completeness_score = 0
        required_fields = ["prerequisites", "learning_path", "learning_methods", "related_technologies"]
        for field in required_fields:
            if field in result_data and result_data[field]:
                completeness_score += 10  # 每个字段10分，共40分
        
        completeness_score = min(completeness_score, 40)  # 最多40分
        
        # 2. 内容长度检查（30分）
        length_score = 0
        
        if "prerequisites" in result_data and result_data["prerequisites"]:
            prereq = result_data["prerequisites"]
            if isinstance(prereq, dict):
                required = prereq.get("required", [])
                if len(required) >= 3:
                    length_score += 10
                elif len(required) >= 1:
                    length_score += 5
        
        if "learning_path" in result_data and result_data["learning_path"]:
            path = result_data["learning_path"]
            if isinstance(path, list):
                if len(path) >= 3:
                    length_score += 10
                elif len(path) >= 1:
                    length_score += 5
        
        if "learning_methods" in result_data and result_data["learning_methods"]:
            methods = result_data["learning_methods"]
            if isinstance(methods, list):
                if len(methods) >= 3:
                    length_score += 10
                elif len(methods) >= 1:
                    length_score += 5
        
        length_score = min(length_score, 30)  # 最多30分
        
        # 3. 结构规范性检查（30分）
        structure_score = 0
        
        if "prerequisites" in result_data and isinstance(result_data["prerequisites"], dict):
            structure_score += 10
        if "learning_path" in result_data and isinstance(result_data["learning_path"], list):
            structure_score += 10
        if "learning_methods" in result_data and isinstance(result_data["learning_methods"], list):
            structure_score += 10
        
        structure_score = min(structure_score, 30)  # 最多30分
        
        score = completeness_score + length_score + structure_score
        return min(score, 100)  # 确保不超过100分
    
    @staticmethod
    async def _assess_architecture_quality(result_data: Dict) -> int:
        """
        评估架构文档处理结果质量
        
        评估规则：
        1. 内容完整性（40分）：是否有config_steps、components、architecture_view、plain_explanation、checklist
        2. 内容长度（30分）：各字段内容是否足够详细
        3. 结构规范性（30分）：数据格式是否正确
        """
        score = 0
        
        # 1. 内容完整性检查（40分）
        completeness_score = 0
        required_fields = ["config_steps", "components", "architecture_view", "plain_explanation", "checklist"]
        for field in required_fields:
            if field in result_data and result_data[field]:
                completeness_score += 8  # 每个字段8分，共40分
        
        completeness_score = min(completeness_score, 40)  # 最多40分
        
        # 2. 内容长度检查（30分）
        length_score = 0
        
        if "config_steps" in result_data and result_data["config_steps"]:
            steps = result_data["config_steps"]
            if isinstance(steps, list):
                if len(steps) >= 5:
                    length_score += 10
                elif len(steps) >= 2:
                    length_score += 5
        
        if "components" in result_data and result_data["components"]:
            components = result_data["components"]
            if isinstance(components, list):
                if len(components) >= 3:
                    length_score += 10
                elif len(components) >= 1:
                    length_score += 5
        
        if "plain_explanation" in result_data and result_data["plain_explanation"]:
            explanation = str(result_data["plain_explanation"])
            if len(explanation) > 200:
                length_score += 10
            elif len(explanation) > 100:
                length_score += 5
        
        length_score = min(length_score, 30)  # 最多30分
        
        # 3. 结构规范性检查（30分）
        structure_score = 0
        
        if "config_steps" in result_data and isinstance(result_data["config_steps"], list):
            structure_score += 10
        if "components" in result_data and isinstance(result_data["components"], list):
            structure_score += 10
        if "architecture_view" in result_data and isinstance(result_data["architecture_view"], (dict, str)):
            structure_score += 10
        
        structure_score = min(structure_score, 30)  # 最多30分
        
        score = completeness_score + length_score + structure_score
        return min(score, 100)  # 确保不超过100分
    
    @staticmethod
    async def _assess_generic_quality(result_data: Dict) -> int:
        """
        通用质量评估（用于未知类型）
        
        评估规则：
        1. 内容完整性（40分）：是否有基本字段
        2. 内容长度（30分）：内容是否足够详细
        3. 结构规范性（30分）：是否为有效JSON
        """
        score = 0
        
        # 1. 内容完整性检查（40分）
        if result_data and isinstance(result_data, dict):
            field_count = len([k for k, v in result_data.items() if v])
            completeness_score = min(field_count * 10, 40)
        else:
            completeness_score = 0
        
        # 2. 内容长度检查（30分）
        result_str = str(result_data)
        if len(result_str) > 500:
            length_score = 30
        elif len(result_str) > 200:
            length_score = 20
        elif len(result_str) > 50:
            length_score = 10
        else:
            length_score = 0
        
        # 3. 结构规范性检查（30分）
        if isinstance(result_data, dict):
            structure_score = 30
        elif isinstance(result_data, list):
            structure_score = 20
        else:
            structure_score = 10
        
        score = completeness_score + length_score + structure_score
        return min(score, 100)  # 确保不超过100分


def get_quality_assessor() -> QualityAssessor:
    """获取质量评估器实例（单例模式）"""
    return QualityAssessor()


