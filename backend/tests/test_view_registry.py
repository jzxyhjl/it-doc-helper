"""
ViewRegistry单元测试
"""
import pytest
from app.services.view_registry import ViewRegistry
from app.services.technical_processor import TechnicalProcessor
from app.services.interview_processor import InterviewProcessor
from app.services.architecture_processor import ArchitectureProcessor


def test_list_views():
    """测试列出所有视角"""
    views = ViewRegistry.list_views()
    assert 'learning' in views
    assert 'qa' in views
    assert 'system' in views
    assert len(views) == 3


def test_get_processor():
    """测试获取处理器"""
    assert ViewRegistry.get_processor('learning') == TechnicalProcessor
    assert ViewRegistry.get_processor('qa') == InterviewProcessor
    assert ViewRegistry.get_processor('system') == ArchitectureProcessor
    
    with pytest.raises(ValueError):
        ViewRegistry.get_processor('invalid_view')


def test_get_type_mapping():
    """测试获取类型映射"""
    assert ViewRegistry.get_type_mapping('learning') == 'technical'
    assert ViewRegistry.get_type_mapping('qa') == 'interview'
    assert ViewRegistry.get_type_mapping('system') == 'architecture'
    
    with pytest.raises(ValueError):
        ViewRegistry.get_type_mapping('invalid_view')


def test_get_view_from_type():
    """测试从类型推断视角"""
    assert ViewRegistry.get_view_from_type('technical') == 'learning'
    assert ViewRegistry.get_view_from_type('interview') == 'qa'
    assert ViewRegistry.get_view_from_type('architecture') == 'system'
    assert ViewRegistry.get_view_from_type('unknown') == 'learning'
    assert ViewRegistry.get_view_from_type('invalid') == 'learning'  # 默认值


def test_get_display_name():
    """测试获取显示名称"""
    assert ViewRegistry.get_display_name('learning') == '学习视角'
    assert ViewRegistry.get_display_name('qa') == '问答视角'
    assert ViewRegistry.get_display_name('system') == '系统视角'
    assert ViewRegistry.get_display_name('invalid') == 'invalid'  # 未注册的视角返回原值

