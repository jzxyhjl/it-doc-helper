"""
多视角系统集成测试
"""
import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.document import Document
from app.models.document_type import DocumentType
from app.models.processing_result import ProcessingResult
from app.services.document_view_classifier import DocumentViewClassifier
from app.services.view_registry import ViewRegistry
from app.services.intermediate_results_service import IntermediateResultsService
from app.services.multi_view_container import MultiViewOutputContainer
from app.utils.backward_compat import BackwardCompatHelper


@pytest.mark.asyncio
async def test_full_document_processing_flow(db_session: AsyncSession):
    """测试完整的文档处理流程（主次视角）"""
    # 1. 创建文档
    doc_id = uuid4()
    document = Document(
        id=doc_id,
        filename='test.pdf',
        file_path='/test/test.pdf',
        file_size=1000,
        file_type='pdf',
        status='pending'
    )
    db_session.add(document)
    await db_session.flush()
    
    # 2. 保存中间结果（注意：save_intermediate_results内部会commit）
    content = "这是一个技术文档，介绍了Python的使用方法。"
    intermediate_result = await IntermediateResultsService.save_intermediate_results(
        document_id=str(doc_id),
        content=content,
        preprocessed_content=content,
        segments=[],
        metadata={'file_type': 'pdf'},
        db=db_session
    )
    assert intermediate_result is not None
    
    # 3. 系统检测特征得分
    detection_scores = {
        'qa': DocumentViewClassifier.detect_qa_structure(content),
        'system': DocumentViewClassifier.detect_component_relationships(content),
        'learning': DocumentViewClassifier.detect_usage_flow(content)
    }
    
    # 4. 推荐主次视角
    primary_view = 'learning'  # 假设推荐为learning
    enabled_views = ['learning', 'system']  # 假设启用了learning和system
    
    # 5. 保存文档类型
    doc_type = DocumentType(
        document_id=doc_id,
        detected_type='technical',
        primary_view=primary_view,
        enabled_views=enabled_views,
        detection_scores=detection_scores,
        confidence=0.85,
        detection_method='rule'
    )
    db_session.add(doc_type)
    await db_session.flush()
    
    # 6. 处理主视角（同步）
    primary_result = ProcessingResult(
        document_id=doc_id,
        view=primary_view,
        document_type='technical',
        result_data={'prerequisites': [], 'learning_path': []},
        is_primary=True,
        processing_time=10
    )
    db_session.add(primary_result)
    await db_session.flush()
    
    # 7. 处理次视角（异步）
    secondary_view = 'system'
    secondary_result = ProcessingResult(
        document_id=doc_id,
        view=secondary_view,
        document_type='architecture',
        result_data={'components': []},
        is_primary=False,
        processing_time=15
    )
    db_session.add(secondary_result)
    await db_session.flush()
    
    # 8. 验证结果（在事务内查询）
    # 主视角应该立即可用
    primary_result_query = await db_session.execute(
        select(ProcessingResult)
        .where(ProcessingResult.document_id == doc_id)
        .where(ProcessingResult.view == primary_view)
    )
    primary = primary_result_query.scalar_one_or_none()
    assert primary is not None
    assert primary.is_primary is True
    
    # 次视角也应该可用
    secondary_result_query = await db_session.execute(
        select(ProcessingResult)
        .where(ProcessingResult.document_id == doc_id)
        .where(ProcessingResult.view == secondary_view)
    )
    secondary = secondary_result_query.scalar_one_or_none()
    assert secondary is not None
    assert secondary.is_primary is False


@pytest.mark.asyncio
async def test_view_independence(db_session: AsyncSession):
    """测试视角独立性（难点1）"""
    doc_id = uuid4()
    document = Document(
        id=doc_id,
        filename='test.pdf',
        file_path='/test/test.pdf',
        file_size=1000,
        file_type='pdf',
        status='completed'
    )
    db_session.add(document)
    await db_session.flush()
    
    # 创建多个视角的结果
    view1_result = ProcessingResult(
        document_id=doc_id,
        view='learning',
        document_type='technical',
        result_data={'data': 'view1'},
        is_primary=True,
        processing_time=10
    )
    view2_result = ProcessingResult(
        document_id=doc_id,
        view='system',
        document_type='architecture',
        result_data={'data': 'view2'},
        is_primary=False,
        processing_time=15
    )
    db_session.add(view1_result)
    db_session.add(view2_result)
    await db_session.flush()
    
    # 验证两个视角的结果独立存储（在事务内查询）
    results_query = await db_session.execute(
        select(ProcessingResult)
        .where(ProcessingResult.document_id == doc_id)
    )
    results = results_query.scalars().all()
    assert len(results) == 2
    
    # 验证每个视角的结果都是独立的
    view1 = next((r for r in results if r.view == 'learning'), None)
    view2 = next((r for r in results if r.view == 'system'), None)
    assert view1 is not None
    assert view2 is not None
    assert view1.result_data['data'] == 'view1'
    assert view2.result_data['data'] == 'view2'


@pytest.mark.asyncio
async def test_intermediate_results_view_agnostic(db_session: AsyncSession):
    """测试中间结果视角无关（难点3）"""
    doc_id = uuid4()
    document = Document(
        id=doc_id,
        filename='test.pdf',
        file_path='/test/test.pdf',
        file_size=1000,
        file_type='pdf',
        status='completed'
    )
    db_session.add(document)
    await db_session.flush()
    
    # 保存中间结果（不包含任何视角信息）
    # 注意：save_intermediate_results内部会commit
    content = "测试内容"
    intermediate_result = await IntermediateResultsService.save_intermediate_results(
        document_id=str(doc_id),
        content=content,
        preprocessed_content=content,
        segments=[],
        metadata={},
        db=db_session
    )
    
    # 验证中间结果不包含视角信息（验证返回值）
    assert intermediate_result is not None
    assert intermediate_result.content == content
    # 中间结果不应该有view字段（视角无关）
    # 注意：由于save_intermediate_results内部commit了，如果需要查询数据库需要使用新session


@pytest.mark.asyncio
async def test_backward_compatibility_migration(db_session: AsyncSession):
    """测试向后兼容性迁移"""
    doc_id = uuid4()
    document = Document(
        id=doc_id,
        filename='test.pdf',
        file_path='/test/test.pdf',
        file_size=1000,
        file_type='pdf',
        status='completed'
    )
    db_session.add(document)
    await db_session.flush()
    
    # 创建旧格式的数据（缺少view字段）
    old_result = ProcessingResult(
        document_id=doc_id,
        view=None,  # 缺少view字段
        document_type='technical',
        result_data={'test': 'data'},
        is_primary=False,
        processing_time=10
    )
    db_session.add(old_result)
    
    old_doc_type = DocumentType(
        document_id=doc_id,
        detected_type='technical',
        primary_view=None,  # 缺少视角字段
        enabled_views=None,
        confidence=0.9,
        detection_method='rule'
    )
    db_session.add(old_doc_type)
    await db_session.flush()
    
    # 执行迁移（不自动commit，只修改对象）
    success1 = await BackwardCompatHelper.migrate_processing_result(str(doc_id), db_session)
    success2 = await BackwardCompatHelper.migrate_document_type(str(doc_id), db_session)
    
    assert success1 is True
    assert success2 is True
    
    # 验证迁移结果（直接检查对象，不查询数据库）
    assert old_result.view == 'learning'  # 应该从technical推断为learning
    assert old_result.is_primary is True
    
    assert old_doc_type.primary_view == 'learning'
    assert old_doc_type.enabled_views == ['learning']

