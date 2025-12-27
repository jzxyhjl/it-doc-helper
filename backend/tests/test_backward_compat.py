"""
向后兼容性测试
"""
import pytest
from uuid import uuid4
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.backward_compat import BackwardCompatHelper
from app.models.document import Document
from app.models.document_type import DocumentType
from app.models.processing_result import ProcessingResult
from app.services.view_registry import ViewRegistry


@pytest.mark.asyncio
async def test_get_view_from_type(db_session: AsyncSession):
    """测试从类型推断视角"""
    assert BackwardCompatHelper.get_view_from_type('technical') == 'learning'
    assert BackwardCompatHelper.get_view_from_type('interview') == 'qa'
    assert BackwardCompatHelper.get_view_from_type('architecture') == 'system'
    assert BackwardCompatHelper.get_view_from_type('unknown') == 'learning'
    assert BackwardCompatHelper.get_view_from_type('invalid') == 'learning'  # 默认值


@pytest.mark.asyncio
async def test_enrich_result_with_views():
    """测试为结果添加视角信息"""
    # 测试缺少view字段的情况
    result = {
        'document_id': '123',
        'document_type': 'technical',
        'result': {}
    }
    enriched = BackwardCompatHelper.enrich_result_with_views(result)
    assert enriched['view'] == 'learning'
    assert enriched['primary_view'] == 'learning'
    assert enriched['enabled_views'] == ['learning']
    
    # 测试已有view字段的情况
    result2 = {
        'document_id': '123',
        'document_type': 'technical',
        'view': 'system',
        'result': {}
    }
    enriched2 = BackwardCompatHelper.enrich_result_with_views(result2)
    assert enriched2['view'] == 'system'  # 不覆盖已有值


@pytest.mark.asyncio
async def test_migrate_processing_result(db_session: AsyncSession):
    """测试迁移处理结果"""
    # 创建测试文档
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
    
    # 创建缺少view字段的处理结果
    result = ProcessingResult(
        document_id=doc_id,
        view=None,  # 缺少view字段
        document_type='technical',
        result_data={'test': 'data'},
        is_primary=False,
        processing_time=10
    )
    db_session.add(result)
    await db_session.flush()
    
    # 创建文档类型
    doc_type = DocumentType(
        document_id=doc_id,
        detected_type='technical',
        primary_view='learning',
        enabled_views=['learning'],
        confidence=0.9,
        detection_method='rule'
    )
    db_session.add(doc_type)
    await db_session.flush()
    
    # 执行迁移（不自动commit，只修改对象）
    success = await BackwardCompatHelper.migrate_processing_result(str(doc_id), db_session)
    assert success
    
    # 验证迁移结果（直接检查对象，不查询数据库）
    assert result.view == 'learning'
    assert result.is_primary is True


@pytest.mark.asyncio
async def test_migrate_document_type(db_session: AsyncSession):
    """测试迁移文档类型"""
    # 创建测试文档
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
    
    # 创建缺少视角字段的文档类型
    doc_type = DocumentType(
        document_id=doc_id,
        detected_type='technical',
        primary_view=None,  # 缺少视角字段
        enabled_views=None,
        confidence=0.9,
        detection_method='rule'
    )
    db_session.add(doc_type)
    await db_session.flush()
    
    # 执行迁移（不自动commit，只修改对象）
    success = await BackwardCompatHelper.migrate_document_type(str(doc_id), db_session)
    assert success
    
    # 验证迁移结果（直接检查对象，不查询数据库）
    assert doc_type.primary_view == 'learning'
    assert doc_type.enabled_views == ['learning']


@pytest.mark.asyncio
async def test_create_multi_view_container_for_legacy(db_session: AsyncSession):
    """测试为历史结果创建多视角容器"""
    # 创建测试文档
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
    
    # 创建旧格式的处理结果（缺少view字段）
    result = ProcessingResult(
        document_id=doc_id,
        view=None,  # 缺少view字段
        document_type='technical',
        result_data={'test': 'data'},
        is_primary=True,
        processing_time=10
    )
    db_session.add(result)
    await db_session.flush()
    
    # 创建文档类型
    doc_type = DocumentType(
        document_id=doc_id,
        detected_type='technical',
        primary_view='learning',
        enabled_views=['learning'],
        confidence=0.9,
        detection_method='rule'
    )
    db_session.add(doc_type)
    await db_session.flush()
    
    # 创建多视角容器
    container = await BackwardCompatHelper.create_multi_view_container_for_legacy(
        str(doc_id),
        db_session
    )
    
    assert container is not None
    assert 'views' in container
    assert 'meta' in container
    assert 'learning' in container['views']
    assert container['meta']['primary_view'] == 'learning'
    assert 'learning' in container['meta']['enabled_views']


@pytest.mark.asyncio
async def test_convert_old_api_params():
    """测试转换旧API参数"""
    # 测试使用旧的document_type参数
    old_params = {
        'document_type': 'technical',
        'other_param': 'value'
    }
    new_params = BackwardCompatHelper.convert_old_api_params(old_params)
    
    assert 'document_type' not in new_params
    assert 'views' in new_params
    assert new_params['views'] == 'learning'
    assert new_params['other_param'] == 'value'
    
    # 测试已有views参数的情况
    old_params2 = {
        'document_type': 'technical',
        'views': 'system'
    }
    new_params2 = BackwardCompatHelper.convert_old_api_params(old_params2)
    
    assert 'document_type' not in new_params2
    assert new_params2['views'] == 'system'  # 保留已有的views

