"""
技术文档回归测试
测试技术文档处理的核心场景
"""
import pytest
from pathlib import Path
import structlog

from tests.test_regression.test_base import document_processing_base

logger = structlog.get_logger()


@pytest.mark.asyncio
async def test_technical_document_processing(
    test_documents_dir: Path,
    test_config: dict
):
    """
    测试技术文档处理核心场景
    
    验证：
    1. 文档能成功处理
    2. 输出结构正确（4个主要字段）
    3. 学习路径的完整性
    4. 前置条件的结构
    5. 置信度和来源字段
    """
    # 使用统一的测试基础框架
    result = await document_processing_base(
        document_type="technical",
        expected_fields=["prerequisites", "learning_path", "learning_methods", "related_technologies"],
        test_document="test_technical.pdf",
        test_documents_dir=test_documents_dir,
        test_config=test_config,
        require_confidence=True,  # 技术文档需要完整展示置信度
        require_sources=True     # 技术文档需要完整展示来源
    )
    
    result_data = result["result"]
    
    # 场景特定验证：学习路径的完整性
    logger.info("验证学习路径的完整性")
    learning_path = result_data["learning_path"]
    assert isinstance(learning_path, list), "learning_path 应该是列表"
    assert len(learning_path) > 0, "learning_path 应该至少包含一个阶段"
    
    for i, stage in enumerate(learning_path):
        assert isinstance(stage, dict), f"learning_path[{i}] 应该是字典"
        assert "stage" in stage, f"learning_path[{i}] 缺少 stage 字段"
        assert "title" in stage, f"learning_path[{i}] 缺少 title 字段"
        assert "content" in stage, f"learning_path[{i}] 缺少 content 字段"
        assert isinstance(stage["stage"], int), f"learning_path[{i}].stage 应该是整数"
        assert isinstance(stage["title"], str), f"learning_path[{i}].title 应该是字符串"
        assert len(stage["title"]) > 0, f"learning_path[{i}].title 不能为空"
        assert isinstance(stage["content"], str), f"learning_path[{i}].content 应该是字符串"
        assert len(stage["content"]) > 0, f"learning_path[{i}].content 不能为空"
        
        # 验证置信度和来源（完整展示模式）
        assert "confidence" in stage, f"learning_path[{i}] 缺少 confidence 字段"
        assert 0 <= stage["confidence"] <= 100, f"learning_path[{i}].confidence 应该在0-100之间"
        assert "sources" in stage, f"learning_path[{i}] 缺少 sources 字段"
        assert isinstance(stage["sources"], list), f"learning_path[{i}].sources 应该是列表"
    
    # 场景特定验证：前置条件的结构
    logger.info("验证前置条件的结构")
    prerequisites = result_data["prerequisites"]
    assert isinstance(prerequisites, dict), "prerequisites 应该是字典"
    assert "required" in prerequisites, "prerequisites 缺少 required 字段"
    assert "recommended" in prerequisites, "prerequisites 缺少 recommended 字段"
    assert isinstance(prerequisites["required"], list), "prerequisites.required 应该是列表"
    assert isinstance(prerequisites["recommended"], list), "prerequisites.recommended 应该是列表"
    
    # 验证置信度和来源
    assert "confidence" in prerequisites, "prerequisites 缺少 confidence 字段"
    assert 0 <= prerequisites["confidence"] <= 100, "prerequisites.confidence 应该在0-100之间"
    assert "sources" in prerequisites, "prerequisites 缺少 sources 字段"
    assert isinstance(prerequisites["sources"], list), "prerequisites.sources 应该是列表"
    
    # 场景特定验证：学习方法的结构
    logger.info("验证学习方法的结构")
    learning_methods = result_data["learning_methods"]
    assert isinstance(learning_methods, dict), "learning_methods 应该是字典"
    assert "theory" in learning_methods, "learning_methods 缺少 theory 字段"
    assert "practice" in learning_methods, "learning_methods 缺少 practice 字段"
    assert isinstance(learning_methods["theory"], str), "learning_methods.theory 应该是字符串"
    assert len(learning_methods["theory"]) > 0, "learning_methods.theory 不能为空"
    assert isinstance(learning_methods["practice"], str), "learning_methods.practice 应该是字符串"
    assert len(learning_methods["practice"]) > 0, "learning_methods.practice 不能为空"
    
    # 验证置信度和来源
    assert "confidence" in learning_methods, "learning_methods 缺少 confidence 字段"
    assert 0 <= learning_methods["confidence"] <= 100, "learning_methods.confidence 应该在0-100之间"
    assert "sources" in learning_methods, "learning_methods 缺少 sources 字段"
    assert isinstance(learning_methods["sources"], list), "learning_methods.sources 应该是列表"
    
    # 场景特定验证：技术关联的结构
    logger.info("验证技术关联的结构")
    related_technologies = result_data["related_technologies"]
    assert isinstance(related_technologies, dict), "related_technologies 应该是字典"
    assert "technologies" in related_technologies, "related_technologies 缺少 technologies 字段"
    assert isinstance(related_technologies["technologies"], list), "related_technologies.technologies 应该是列表"
    
    # 验证置信度和来源
    assert "confidence" in related_technologies, "related_technologies 缺少 confidence 字段"
    assert 0 <= related_technologies["confidence"] <= 100, "related_technologies.confidence 应该在0-100之间"
    assert "sources" in related_technologies, "related_technologies 缺少 sources 字段"
    assert isinstance(related_technologies["sources"], list), "related_technologies.sources 应该是列表"
    
    logger.info("技术文档回归测试通过", 
               learning_path_stages=len(learning_path),
               prerequisites_required=len(prerequisites["required"]),
               technologies_count=len(related_technologies["technologies"]))

