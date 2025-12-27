"""
面试题文档回归测试
测试面试题文档处理的核心场景
"""
import pytest
from pathlib import Path
import structlog

from tests.test_regression.test_base import document_processing_base

logger = structlog.get_logger()


@pytest.mark.asyncio
async def test_interview_document_processing(
    test_documents_dir: Path,
    test_config: dict
):
    """
    测试面试题文档处理核心场景
    
    验证：
    1. 文档能成功处理
    2. 输出结构正确（3个主要字段）
    3. 问题生成的准确性
    4. 内容总结的结构
    5. 置信度和来源字段（弱展示模式）
    """
    # 使用统一的测试基础框架
    result = await document_processing_base(
        document_type="interview",
        expected_fields=["summary", "generated_questions", "extracted_answers"],
        test_document="test_interview.docx",
        test_documents_dir=test_documents_dir,
        test_config=test_config,
        require_confidence=False,  # 面试题文档使用弱展示模式
        require_sources=False      # 面试题文档使用弱展示模式
    )
    
    result_data = result["result"]
    
    # 场景特定验证：问题生成的准确性
    logger.info("验证问题生成的准确性")
    generated_questions = result_data["generated_questions"]
    assert isinstance(generated_questions, list), "generated_questions 应该是列表"
    assert len(generated_questions) > 0, "generated_questions 应该至少包含一个问题"
    
    for i, question in enumerate(generated_questions):
        assert isinstance(question, dict), f"generated_questions[{i}] 应该是字典"
        assert "question" in question, f"generated_questions[{i}] 缺少 question 字段"
        assert "answer" in question, f"generated_questions[{i}] 缺少 answer 字段"
        assert isinstance(question["question"], str), f"generated_questions[{i}].question 应该是字符串"
        assert len(question["question"]) > 0, f"generated_questions[{i}].question 不能为空"
        assert isinstance(question["answer"], str), f"generated_questions[{i}].answer 应该是字符串"
        assert len(question["answer"]) > 0, f"generated_questions[{i}].answer 不能为空"
    
    # 场景特定验证：内容总结的结构
    logger.info("验证内容总结的结构")
    summary = result_data["summary"]
    assert isinstance(summary, dict), "summary 应该是字典"
    assert "key_points" in summary, "summary 缺少 key_points 字段"
    assert "question_types" in summary, "summary 缺少 question_types 字段"
    assert "difficulty" in summary, "summary 缺少 difficulty 字段"
    assert "total_questions" in summary, "summary 缺少 total_questions 字段"
    
    assert isinstance(summary["key_points"], list), "summary.key_points 应该是列表"
    assert isinstance(summary["question_types"], dict), "summary.question_types 应该是字典"
    assert isinstance(summary["difficulty"], dict), "summary.difficulty 应该是字典"
    assert isinstance(summary["total_questions"], int), "summary.total_questions 应该是整数"
    assert summary["total_questions"] >= 0, "summary.total_questions 应该 >= 0"
    
    # 弱展示模式：如果AI返回了置信度和来源，则验证
    if "confidence" in summary:
        assert 0 <= summary["confidence"] <= 100, "summary.confidence 应该在0-100之间"
    if "sources" in summary:
        assert isinstance(summary["sources"], list), "summary.sources 应该是列表"
    
    # 场景特定验证：答案提取的结构
    logger.info("验证答案提取的结构")
    extracted_answers = result_data["extracted_answers"]
    assert isinstance(extracted_answers, dict), "extracted_answers 应该是字典"
    assert "answers" in extracted_answers, "extracted_answers 缺少 answers 字段"
    assert isinstance(extracted_answers["answers"], list), "extracted_answers.answers 应该是列表"
    
    # 弱展示模式：如果AI返回了置信度和来源，则验证
    if "confidence" in extracted_answers:
        assert 0 <= extracted_answers["confidence"] <= 100, "extracted_answers.confidence 应该在0-100之间"
    if "sources" in extracted_answers:
        assert isinstance(extracted_answers["sources"], list), "extracted_answers.sources 应该是列表"
    
    logger.info("面试题文档回归测试通过", 
               questions_count=len(generated_questions),
               key_points_count=len(summary["key_points"]),
               total_questions=summary["total_questions"])

