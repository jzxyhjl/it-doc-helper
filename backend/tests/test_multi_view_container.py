"""
MultiViewOutputContainer单元测试
"""
import pytest
from app.services.multi_view_container import MultiViewOutputContainer


def test_create_container():
    """测试创建多视角容器"""
    views = {
        'learning': {'prerequisites': [], 'learning_path': []},
        'system': {'components': [], 'architecture_view': ''}
    }
    enabled_views = ['learning', 'system']
    confidence = {
        'learning': 0.85,
        'qa': 0.15,
        'system': 0.65
    }
    primary_view = 'learning'
    
    container = MultiViewOutputContainer.create_container(
        views=views,
        enabled_views=enabled_views,
        confidence=confidence,
        primary_view=primary_view
    )
    
    assert 'views' in container
    assert 'meta' in container
    assert container['views'] == views
    assert container['meta']['enabled_views'] == enabled_views
    assert container['meta']['confidence'] == confidence
    assert container['meta']['primary_view'] == primary_view


def test_get_view_result():
    """测试获取视角结果"""
    views = {
        'learning': {'prerequisites': [], 'learning_path': []},
        'system': {'components': [], 'architecture_view': ''}
    }
    container = {
        'views': views,
        'meta': {
            'enabled_views': ['learning', 'system'],
            'primary_view': 'learning'
        }
    }
    
    learning_result = MultiViewOutputContainer.get_view(container, 'learning')
    assert learning_result == views['learning']
    
    system_result = MultiViewOutputContainer.get_view(container, 'system')
    assert system_result == views['system']
    
    # 不存在的视角应该返回None
    qa_result = MultiViewOutputContainer.get_view(container, 'qa')
    assert qa_result is None


def test_get_primary_view():
    """测试获取主视角"""
    container = {
        'views': {
            'learning': {},
            'system': {}
        },
        'meta': {
            'enabled_views': ['learning', 'system'],
            'primary_view': 'learning'
        }
    }
    
    primary_view = MultiViewOutputContainer.get_primary_view(container)
    assert primary_view == 'learning'


def test_get_enabled_views():
    """测试获取启用的视角"""
    container = {
        'views': {
            'learning': {},
            'system': {}
        },
        'meta': {
            'enabled_views': ['learning', 'system'],
            'primary_view': 'learning'
        }
    }
    
    enabled_views = MultiViewOutputContainer.get_enabled_views(container)
    assert enabled_views == ['learning', 'system']

