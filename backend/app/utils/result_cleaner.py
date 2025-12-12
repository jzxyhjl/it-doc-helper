"""
处理结果清理工具
- 清理处理结果中的技术名词翻译
- 递归清理所有可能包含技术名词的字段
"""
from typing import Any, Dict, List
from app.utils.tech_name_utils import clean_tech_name


def clean_processing_result(result: Any) -> Any:
    """
    递归清理处理结果中的技术名词翻译
    
    Args:
        result: 处理结果（可能是dict、list、str等）
        
    Returns:
        清理后的处理结果
    """
    if isinstance(result, dict):
        cleaned = {}
        for key, value in result.items():
            # 对于可能包含技术名词的字段，进行清理
            if key in ['related_technologies', 'required', 'recommended']:
                if isinstance(value, list):
                    cleaned[key] = [clean_tech_name(item) if isinstance(item, str) else clean_processing_result(item) for item in value]
                else:
                    cleaned[key] = clean_processing_result(value)
            elif key in ['prerequisites']:
                # prerequisites 是嵌套结构，需要递归清理
                cleaned[key] = clean_processing_result(value)
            elif key in ['learning_path']:
                # learning_path 是列表，每个元素可能包含技术名词
                if isinstance(value, list):
                    cleaned[key] = [clean_processing_result(item) for item in value]
                else:
                    cleaned[key] = clean_processing_result(value)
            elif key in ['components']:
                # components 是列表，每个组件可能有技术名词
                if isinstance(value, list):
                    cleaned[key] = [clean_processing_result(item) for item in value]
                else:
                    cleaned[key] = clean_processing_result(value)
            elif key in ['plain_explanation', 'architecture_view']:
                # 清理白话串讲和架构视图中的格式错误（如单独的右括号）
                if isinstance(value, str):
                    from app.services.architecture_processor import ArchitectureProcessor
                    cleaned[key] = ArchitectureProcessor._clean_explanation_text(value)
                else:
                    cleaned[key] = clean_processing_result(value)
            else:
                cleaned[key] = clean_processing_result(value)
        return cleaned
    elif isinstance(result, list):
        return [clean_processing_result(item) for item in result]
    elif isinstance(result, str):
        # 对于字符串，检查是否可能是技术名词（包含括号和中文）
        # 如果包含中文括号和中文内容，尝试清理
        if '（' in result or '(' in result:
            # 检查是否包含中文内容
            import re
            if re.search(r'[\uff08(（][\u4e00-\u9fa5]+', result):
                return clean_tech_name(result)
        return result
    else:
        return result

