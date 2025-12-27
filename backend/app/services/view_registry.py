"""
视角注册表 - 解耦视角和处理器的绑定关系
"""
from typing import Dict, Type, Optional, List, Callable
import structlog

logger = structlog.get_logger()


class ViewRegistry:
    """
    视角注册表 - 解耦视角和处理器的绑定关系
    
    支持动态注册视角配置，避免硬编码绑定关系
    """
    
    _registry: Dict[str, Dict] = {}
    
    # 视角名称映射（重构后的命名）
    VIEW_NAMES = {
        'learning': '学习视角',  # 原 technical
        'qa': '问答视角',        # 原 interview
        'system': '系统视角'     # 原 architecture
    }
    
    # 类型到视角的映射（向后兼容）
    TYPE_TO_VIEW_MAP = {
        'technical': 'learning',
        'interview': 'qa',
        'architecture': 'system',
        'unknown': 'learning'
    }
    
    # 视角到类型的映射（向后兼容）
    VIEW_TO_TYPE_MAP = {
        'learning': 'technical',
        'qa': 'interview',
        'system': 'architecture'
    }
    
    @classmethod
    def register(
        cls,
        view: str,  # learning/qa/system
        processor_class: Type,
        type_mapping: str,  # technical/interview/architecture（向后兼容）
        result_adapter: Optional[Callable] = None
    ):
        """
        注册视角配置
        
        Args:
            view: 视角名称（learning/qa/system）
            processor_class: 处理器类
            type_mapping: 类型映射（用于向后兼容）
            result_adapter: 结果适配器（可选）
        """
        cls._registry[view] = {
            'processor_class': processor_class,
            'type_mapping': type_mapping,
            'result_adapter': result_adapter,
            'display_name': cls.VIEW_NAMES.get(view, view)
        }
        logger.info("注册视角", view=view, type_mapping=type_mapping)
    
    @classmethod
    def get_processor(cls, view: str):
        """
        获取处理器实例
        
        Args:
            view: 视角名称
        
        Returns:
            处理器类
        
        Raises:
            ValueError: 如果视角未注册
        """
        if view not in cls._registry:
            raise ValueError(f"未注册的视角: {view}。已注册的视角: {list(cls._registry.keys())}")
        return cls._registry[view]['processor_class']
    
    @classmethod
    def get_type_mapping(cls, view: str) -> str:
        """
        获取类型映射（向后兼容）
        
        Args:
            view: 视角名称
        
        Returns:
            类型名称
        """
        if view not in cls._registry:
            raise ValueError(f"未注册的视角: {view}")
        return cls._registry[view]['type_mapping']
    
    @classmethod
    def get_view_from_type(cls, document_type: str) -> str:
        """
        从类型推断视角（向后兼容）
        
        Args:
            document_type: 类型名称
        
        Returns:
            视角名称
        """
        return cls.TYPE_TO_VIEW_MAP.get(document_type, 'learning')
    
    @classmethod
    def list_views(cls) -> List[str]:
        """
        列出所有已注册的视角
        
        Returns:
            视角名称列表
        """
        return list(cls._registry.keys())
    
    @classmethod
    def get_display_name(cls, view: str) -> str:
        """
        获取视角显示名称
        
        Args:
            view: 视角名称
        
        Returns:
            显示名称
        """
        if view not in cls._registry:
            return view
        return cls._registry[view]['display_name']


# 初始化注册表（在模块导入时自动注册）
def _init_registry():
    """初始化视角注册表"""
    from app.services.technical_processor import TechnicalProcessor
    from app.services.interview_processor import InterviewProcessor
    from app.services.architecture_processor import ArchitectureProcessor
    
    ViewRegistry.register(
        'learning',  # 学习视角
        TechnicalProcessor,  # 原技术文档处理器
        'technical',  # 向后兼容的类型
        result_adapter=None  # 不需要适配器，保持原生结构
    )
    
    ViewRegistry.register(
        'qa',  # 问答视角
        InterviewProcessor,  # 原面试题处理器
        'interview',  # 向后兼容的类型
        result_adapter=None
    )
    
    ViewRegistry.register(
        'system',  # 系统视角
        ArchitectureProcessor,  # 原架构文档处理器
        'architecture',  # 向后兼容的类型
        result_adapter=None
    )
    
    logger.info("视角注册表初始化完成", views=list(ViewRegistry.list_views()))


# 自动初始化
_init_registry()

