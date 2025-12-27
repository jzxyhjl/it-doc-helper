"""
ViewSwitcher单元测试
"""
import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.view_switcher import ViewSwitcher
from app.services.view_registry import ViewRegistry
from app.models.document import Document
from app.models.document_type import DocumentType
from app.models.processing_result import ProcessingResult
from app.services.intermediate_results_service import IntermediateResultsService


@pytest.mark.asyncio
async def test_switch_view_existing_result(db_session: AsyncSession):
    """测试切换视角（结果已存在）"""
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
    
    # 创建已存在的视角结果
    existing_result = ProcessingResult(
        document_id=doc_id,
        view='system',
        document_type='architecture',
        result_data={'components': []},
        is_primary=False,
        processing_time=10
    )
    db_session.add(existing_result)
    await db_session.flush()
    
    # 切换视角（结果已存在，应该直接返回）
    # 注意：switch_view可能会查询数据库，但不会commit，所以可以在事务内测试
    result = await ViewSwitcher.switch_view(
        document_id=str(doc_id),
        target_view='system',
        db=db_session
    )
    
    assert result['view'] == 'system'
    assert result.get('from_cache') is True or result.get('used_intermediate_results') is False


@pytest.mark.asyncio
async def test_switch_view_invalid_view(db_session: AsyncSession):
    """测试切换视角（无效的视角）"""
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
    
    # 尝试切换到无效的视角
    with pytest.raises(ValueError) as exc_info:
        await ViewSwitcher.switch_view(
            document_id=str(doc_id),
            target_view='invalid_view',
            db=db_session
        )
    
    assert '无效的视角' in str(exc_info.value)


@pytest.mark.asyncio
async def test_switch_view_no_intermediate_results(db_session: AsyncSession):
    """测试切换视角（中间结果不存在）"""
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
    
    # 尝试切换视角（中间结果不存在）
    with pytest.raises(ValueError) as exc_info:
        await ViewSwitcher.switch_view(
            document_id=str(doc_id),
            target_view='learning',
            db=db_session
        )
    
    assert '中间结果不存在' in str(exc_info.value)

