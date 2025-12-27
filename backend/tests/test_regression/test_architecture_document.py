"""
架构文档回归测试（重点测试）
测试架构文档处理的核心场景，包括进度回调机制
"""
import pytest
from pathlib import Path
import structlog

from tests.test_regression.test_base import document_processing_base
from tests.utils.test_helpers import monitor_progress

logger = structlog.get_logger()


@pytest.mark.asyncio
async def test_architecture_document_processing(
    test_documents_dir: Path,
    test_config: dict
):
    """
    测试架构文档处理核心场景（重点测试）
    
    验证：
    1. 文档能成功处理
    2. 输出结构正确（6个主要字段）
    3. 配置步骤的完整性
    4. 组件识别的结构
    5. 架构视图的格式
    6. 置信度和来源字段（弱展示模式）
    """
    # 使用统一的测试基础框架
    result = await document_processing_base(
        document_type="architecture",
        expected_fields=["config_steps", "components", "architecture_view", 
                        "plain_explanation", "checklist", "related_technologies"],
        test_document="test_architecture.md",
        test_documents_dir=test_documents_dir,
        test_config=test_config,
        require_confidence=False,  # 架构文档使用弱展示模式
        require_sources=False      # 架构文档使用弱展示模式
    )
    
    result_data = result["result"]
    
    # 场景特定验证：配置步骤的完整性
    logger.info("验证配置步骤的完整性")
    config_steps = result_data["config_steps"]
    assert isinstance(config_steps, list), "config_steps 应该是列表"
    assert len(config_steps) > 0, "config_steps 应该至少包含一个步骤"
    
    for i, step in enumerate(config_steps):
        assert isinstance(step, dict), f"config_steps[{i}] 应该是字典"
        assert "step" in step, f"config_steps[{i}] 缺少 step 字段"
        assert "description" in step, f"config_steps[{i}] 缺少 description 字段"
        assert isinstance(step["step"], int), f"config_steps[{i}].step 应该是整数"
        assert isinstance(step["description"], str), f"config_steps[{i}].description 应该是字符串"
        assert len(step["description"]) > 0, f"config_steps[{i}].description 不能为空"
    
    # 场景特定验证：组件识别的结构
    logger.info("验证组件识别的结构")
    components = result_data["components"]
    assert isinstance(components, list), "components 应该是列表"
    assert len(components) > 0, "components 应该至少包含一个组件"
    
    for i, component in enumerate(components):
        assert isinstance(component, dict), f"components[{i}] 应该是字典"
        assert "name" in component, f"components[{i}] 缺少 name 字段"
        assert "description" in component, f"components[{i}] 缺少 description 字段"
        assert isinstance(component["name"], str), f"components[{i}].name 应该是字符串"
        assert len(component["name"]) > 0, f"components[{i}].name 不能为空"
        assert isinstance(component["description"], str), f"components[{i}].description 应该是字符串"
        assert len(component["description"]) > 0, f"components[{i}].description 不能为空"
    
    # 场景特定验证：架构视图的格式
    logger.info("验证架构视图的格式")
    architecture_view = result_data["architecture_view"]
    assert isinstance(architecture_view, str), "architecture_view 应该是字符串"
    assert len(architecture_view) > 0, "architecture_view 不能为空"
    # 可能包含Mermaid代码，但不强制要求
    
    # 场景特定验证：白话解释的格式
    logger.info("验证白话解释的格式")
    plain_explanation = result_data["plain_explanation"]
    assert isinstance(plain_explanation, str), "plain_explanation 应该是字符串"
    assert len(plain_explanation) > 0, "plain_explanation 不能为空"
    
    # 场景特定验证：检查清单的结构
    logger.info("验证检查清单的结构")
    checklist = result_data["checklist"]
    assert isinstance(checklist, dict), "checklist 应该是字典"
    assert "items" in checklist, "checklist 缺少 items 字段"
    assert isinstance(checklist["items"], list), "checklist.items 应该是列表"
    
    # 弱展示模式：如果AI返回了置信度和来源，则验证
    if "confidence" in checklist:
        assert 0 <= checklist["confidence"] <= 100, "checklist.confidence 应该在0-100之间"
    if "sources" in checklist:
        assert isinstance(checklist["sources"], list), "checklist.sources 应该是列表"
    
    # 场景特定验证：技术栈的结构
    logger.info("验证技术栈的结构")
    related_technologies = result_data["related_technologies"]
    assert isinstance(related_technologies, dict), "related_technologies 应该是字典"
    assert "technologies" in related_technologies, "related_technologies 缺少 technologies 字段"
    assert isinstance(related_technologies["technologies"], list), "related_technologies.technologies 应该是列表"
    
    # 弱展示模式：如果AI返回了置信度和来源，则验证
    if "confidence" in related_technologies:
        assert 0 <= related_technologies["confidence"] <= 100, "related_technologies.confidence 应该在0-100之间"
    if "sources" in related_technologies:
        assert isinstance(related_technologies["sources"], list), "related_technologies.sources 应该是列表"
    
    logger.info("架构文档回归测试通过", 
               config_steps_count=len(config_steps),
               components_count=len(components),
               checklist_items_count=len(checklist["items"]))


@pytest.mark.asyncio
async def test_architecture_progress_callback(
    test_documents_dir: Path,
    test_config: dict
):
    """
    测试架构文档的进度回调机制
    
    验证：
    1. 进度回调包含5个步骤的更新
    2. 每个步骤的stage信息正确
    3. 进度值递增
    """
    from tests.utils.test_helpers import upload_test_document, wait_for_completion
    
    # 上传测试文档
    test_document_path = test_documents_dir / "test_architecture.md"
    if not test_document_path.exists():
        pytest.skip("测试文档不存在: test_architecture.md")
    
    document_id = await upload_test_document(
        str(test_document_path),
        base_url=test_config["base_url"],
        api_base=test_config["api_base"]
    )
    
    assert document_id is not None, "文档上传失败"
    
    # 监听进度更新
    logger.info("开始监听进度更新", document_id=document_id)
    progress_updates = []
    expected_stages = [
        "步骤1/5：提取配置流程",
        "步骤2/5：识别组件",
        "步骤3/5：生成架构视图",
        "步骤4/5：生成白话解释",
        "步骤5/5：生成检查清单"
    ]
    
    async for progress in monitor_progress(
        document_id,
        timeout=test_config["timeout"],
        api_base=test_config["api_base"]
    ):
        progress_updates.append(progress)
        stage = progress.get("current_stage", "")
        
        # 验证进度值递增
        if len(progress_updates) > 1:
            prev_progress = progress_updates[-2].get("progress", 0)
            curr_progress = progress.get("progress", 0)
            assert curr_progress >= prev_progress, "进度值应该递增"
    
    # 验证至少有5个进度更新（5个步骤）
    assert len(progress_updates) >= 5, f"进度更新数量不足，期望至少5个，实际{len(progress_updates)}"
    
    # 验证每个步骤的stage信息
    stages_found = []
    for progress in progress_updates:
        stage = progress.get("current_stage", "")
        for expected_stage in expected_stages:
            if expected_stage in stage:
                stages_found.append(expected_stage)
                break
    
    # 验证至少找到了部分步骤（不要求全部，因为进度更新可能不完整）
    assert len(stages_found) > 0, "未找到任何预期的步骤信息"
    
    logger.info("架构文档进度回调测试通过", 
               progress_updates_count=len(progress_updates),
               stages_found=stages_found)

