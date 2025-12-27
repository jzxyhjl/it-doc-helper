"""
结果验证器
"""
from typing import Dict, List, Any
import structlog

logger = structlog.get_logger()


def validate_confidence_and_sources(
    result_data: Dict,
    fields: List[str],
    require_confidence: bool = False,
    require_sources: bool = False
) -> Dict[str, bool]:
    """
    验证置信度和来源字段
    
    Args:
        result_data: 结果数据字典
        fields: 需要验证的字段列表
        require_confidence: 是否强制要求置信度字段
        require_sources: 是否强制要求来源字段
        
    Returns:
        验证结果字典 {field_name: is_valid}
    """
    validation_results = {}
    
    for field in fields:
        field_data = result_data.get(field)
        is_valid = True
        errors = []
        
        if field_data is None:
            is_valid = False
            errors.append(f"字段 {field} 不存在")
        elif isinstance(field_data, dict):
            # 检查置信度字段
            if "confidence" in field_data:
                confidence = field_data["confidence"]
                if not isinstance(confidence, (int, float)):
                    is_valid = False
                    errors.append(f"字段 {field}.confidence 类型错误")
                elif not (0 <= confidence <= 100):
                    is_valid = False
                    errors.append(f"字段 {field}.confidence 值超出范围: {confidence}")
            elif require_confidence:
                is_valid = False
                errors.append(f"字段 {field} 缺少必需的置信度字段")
            
            # 检查来源字段
            if "sources" in field_data:
                sources = field_data["sources"]
                if not isinstance(sources, list):
                    is_valid = False
                    errors.append(f"字段 {field}.sources 类型错误，应为列表")
                else:
                    # 验证来源片段格式
                    for i, source in enumerate(sources):
                        if not isinstance(source, dict):
                            is_valid = False
                            errors.append(f"字段 {field}.sources[{i}] 类型错误，应为字典")
                        elif "content" not in source:
                            is_valid = False
                            errors.append(f"字段 {field}.sources[{i}] 缺少content字段")
            elif require_sources:
                is_valid = False
                errors.append(f"字段 {field} 缺少必需的来源字段")
        
        validation_results[field] = is_valid
        
        if not is_valid:
            logger.warning("字段验证失败", 
                         field=field,
                         errors=errors)
    
    return validation_results


def validate_result_structure(
    result: Dict,
    document_type: str,
    expected_fields: List[str]
) -> Dict[str, Any]:
    """
    验证结果结构
    
    Args:
        result: 处理结果
        document_type: 文档类型
        expected_fields: 期望的字段列表
        
    Returns:
        验证结果字典
    """
    validation_result = {
        "valid": True,
        "errors": [],
        "missing_fields": [],
        "empty_fields": []
    }
    
    # 验证基础结构
    if "document_type" not in result:
        validation_result["valid"] = False
        validation_result["errors"].append("缺少 document_type 字段")
    elif result["document_type"] != document_type:
        validation_result["valid"] = False
        validation_result["errors"].append(
            f"document_type 不匹配: 期望 {document_type}, 实际 {result['document_type']}"
        )
    
    if "result" not in result:
        validation_result["valid"] = False
        validation_result["errors"].append("缺少 result 字段")
        return validation_result
    
    result_data = result["result"]
    
    # 验证期望字段
    for field in expected_fields:
        if field not in result_data:
            validation_result["valid"] = False
            validation_result["missing_fields"].append(field)
        elif result_data[field] is None:
            validation_result["valid"] = False
            validation_result["empty_fields"].append(field)
    
    return validation_result


def validate_field_not_empty(
    result_data: Dict,
    field: str,
    field_type: type = None
) -> bool:
    """
    验证字段不为空
    
    Args:
        result_data: 结果数据字典
        field: 字段名
        field_type: 期望的字段类型（可选）
        
    Returns:
        是否有效
    """
    if field not in result_data:
        return False
    
    value = result_data[field]
    
    if value is None:
        return False
    
    if field_type and not isinstance(value, field_type):
        return False
    
    # 检查列表是否为空
    if isinstance(value, list) and len(value) == 0:
        return False
    
    # 检查字典是否为空
    if isinstance(value, dict) and len(value) == 0:
        return False
    
    # 检查字符串是否为空
    if isinstance(value, str) and len(value.strip()) == 0:
        return False
    
    return True

