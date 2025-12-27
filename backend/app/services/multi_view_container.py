"""
多视角输出容器 - 包装多个视角的结果
"""
from typing import Dict, List, Optional
from datetime import datetime
import structlog

logger = structlog.get_logger()


class MultiViewOutputContainer:
    """
    多视角输出容器 - 包装多个视角的结果
    
    关键点：
    - 不用统一字段，只要包一层
    - 不是每个文档都有所有view，检测到哪些就生成哪些
    - 各view保持原生结构
    """
    
    @staticmethod
    def create_container(
        views: Dict[str, Dict],
        enabled_views: List[str],
        confidence: Optional[Dict[str, float]] = None,
        primary_view: Optional[str] = None
    ) -> Dict:
        """
        创建多视角输出容器
        
        Args:
            views: {view_name: view_result} - 各视角的结果（保持原生结构）
            enabled_views: 启用的视角列表
            confidence: 各视角的置信度得分
            primary_view: 主视角（默认view）
        
        Returns:
            多视角输出容器结构
        
        容器结构：
        {
            "views": {
                "learning": {...原生结构...},
                "qa": {...原生结构...},
                "system": {...原生结构...}
            },
            "meta": {
                "enabled_views": ["learning", "system"],
                "primary_view": "learning",
                "confidence": {
                    "learning": 0.85,
                    "system": 0.65,
                    "qa": 0.15
                },
                "view_count": 2,
                "timestamp": "..."
            }
        }
        """
        return {
            'views': views,  # 各视角的结果，保持原生结构
            'meta': {
                'enabled_views': enabled_views,  # 启用了哪些view
                'primary_view': primary_view,    # 主视角（默认view）
                'confidence': confidence or {},  # 各视角的置信度
                'view_count': len(views),
                'timestamp': datetime.now().isoformat()
            }
        }
    
    @staticmethod
    def get_view(container: Dict, view: str) -> Optional[Dict]:
        """
        从容器中获取指定视角的结果
        
        Args:
            container: 多视角输出容器
            view: 视角名称
        
        Returns:
            该视角的结果，如果不存在则返回None
        """
        return container.get('views', {}).get(view)
    
    @staticmethod
    def has_view(container: Dict, view: str) -> bool:
        """
        检查容器是否包含指定视角
        
        Args:
            container: 多视角输出容器
            view: 视角名称
        
        Returns:
            如果包含该视角返回True，否则返回False
        """
        return view in container.get('views', {})
    
    @staticmethod
    def list_views(container: Dict) -> List[str]:
        """
        列出容器中所有视角
        
        Args:
            container: 多视角输出容器
        
        Returns:
            视角名称列表
        """
        return list(container.get('views', {}).keys())
    
    @staticmethod
    def get_primary_view(container: Dict) -> Optional[str]:
        """
        获取主视角
        
        Args:
            container: 多视角输出容器
        
        Returns:
            主视角名称，如果不存在则返回None
        """
        return container.get('meta', {}).get('primary_view')
    
    @staticmethod
    def get_enabled_views(container: Dict) -> List[str]:
        """
        获取启用的视角列表
        
        Args:
            container: 多视角输出容器
        
        Returns:
            启用的视角列表
        """
        return container.get('meta', {}).get('enabled_views', [])
    
    @staticmethod
    def get_confidence(container: Dict, view: Optional[str] = None) -> Optional[float]:
        """
        获取视角的置信度
        
        Args:
            container: 多视角输出容器
            view: 视角名称，如果为None则返回所有视角的置信度
        
        Returns:
            置信度值或字典
        """
        confidence = container.get('meta', {}).get('confidence', {})
        if view:
            return confidence.get(view)
        return confidence

