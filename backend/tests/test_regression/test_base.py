"""
统一的测试基础框架
所有回归测试的基础，提供通用的测试流程和验证逻辑
"""
import pytest
from typing import Dict, List, Optional
from pathlib import Path
import structlog

from tests.utils.test_helpers import (
    upload_test_document,
    get_task_id,
    wait_for_completion,
    monitor_progress
)
from tests.utils.validators import (
    validate_confidence_and_sources,
    validate_result_structure,
    validate_field_not_empty
)

logger = structlog.get_logger()


async def document_processing_base(
    document_type: str,
    expected_fields: List[str],
    test_document: str,
    test_documents_dir: Path,
    test_config: Dict,
    require_confidence: bool = False,
    require_sources: bool = False
) -> Dict:
    """
    统一的文档处理测试基础流程
    
    Args:
        document_type: 文档类型（technical/interview/architecture）
        expected_fields: 期望的输出字段列表
        test_document: 测试文档文件名
        test_documents_dir: 测试文档目录路径
        test_config: 测试配置
        require_confidence: 是否强制要求置信度字段
        require_sources: 是否强制要求来源字段
        
    Returns:
        处理结果字典
        
    Raises:
        AssertionError: 如果测试失败
    """
    base_url = test_config["base_url"]
    api_base = test_config["api_base"]
    timeout = test_config["timeout"]
    
    # 1. 上传测试文档
    test_document_path = test_documents_dir / test_document
    if not test_document_path.exists():
        pytest.skip(f"测试文档不存在: {test_document}")
    
    logger.info("开始上传测试文档", document=test_document, document_type=document_type)
    document_id = await upload_test_document(
        str(test_document_path),
        base_url=base_url,
        api_base=api_base
    )
    
    assert document_id is not None, f"文档上传失败: {test_document}"
    logger.info("测试文档上传成功", document_id=document_id)
    
    # 2. 等待处理完成
    logger.info("等待文档处理完成", document_id=document_id, timeout=timeout)
    result = await wait_for_completion(
        document_id,
        timeout=timeout,
        api_base=api_base
    )
    
    assert result is not None, f"文档处理失败或超时: {document_id}"
    logger.info("文档处理完成", document_id=document_id)
    
    # 3. 验证基础结构（所有场景通用）
    logger.info("验证基础结构", document_id=document_id)
    structure_validation = validate_result_structure(
        result,
        document_type,
        expected_fields
    )
    
    assert structure_validation["valid"], (
        f"结果结构验证失败: {structure_validation['errors']}, "
        f"缺少字段: {structure_validation['missing_fields']}, "
        f"空字段: {structure_validation['empty_fields']}"
    )
    
    # 4. 验证场景特定字段
    logger.info("验证场景特定字段", document_id=document_id, fields=expected_fields)
    result_data = result["result"]
    
    for field in expected_fields:
        assert field in result_data, f"缺少必需字段: {field}"
        assert result_data[field] is not None, f"字段为空: {field}"
        assert validate_field_not_empty(result_data, field), f"字段内容为空: {field}"
    
    # 5. 验证置信度和来源（所有场景通用）
    logger.info("验证置信度和来源", document_id=document_id)
    confidence_validation = validate_confidence_and_sources(
        result_data,
        expected_fields,
        require_confidence=require_confidence,
        require_sources=require_sources
    )
    
    # 检查验证结果
    failed_fields = [field for field, is_valid in confidence_validation.items() if not is_valid]
    if failed_fields:
        logger.warning("置信度和来源验证失败", 
                     document_id=document_id,
                     failed_fields=failed_fields)
        # 根据require_confidence和require_sources决定是否失败
        if require_confidence or require_sources:
            pytest.fail(f"置信度和来源验证失败: {failed_fields}")
    
    # 6. 验证处理状态
    assert result.get("status") == "completed", f"文档处理状态不正确: {result.get('status')}"
    
    logger.info("测试基础流程完成", 
               document_id=document_id,
               document_type=document_type,
               fields_verified=expected_fields)
    
    return result

