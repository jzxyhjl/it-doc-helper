"""
缓存服务 - 基于系统检测的特征得分进行缓存
"""
from typing import Optional, Dict, Any
import json
import redis
import structlog
from app.core.config import settings

logger = structlog.get_logger()


class CacheService:
    """
    缓存服务 - 用于缓存中间结果和检测结果
    
    关键点：
    - 缓存key基于系统检测的特征得分（不基于推荐结果）
    - 系统检测才是算力与存储的边界
    """
    
    _redis_client: Optional[redis.Redis] = None
    _cache_prefix = "doc_cache"
    _default_ttl = 3600 * 24 * 7  # 7天
    
    @classmethod
    def _get_redis_client(cls) -> Optional[redis.Redis]:
        """获取Redis客户端（懒加载）"""
        if cls._redis_client is None:
            try:
                cls._redis_client = redis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True
                )
                # 测试连接
                cls._redis_client.ping()
                logger.info("Redis缓存服务已连接")
            except Exception as e:
                logger.warning("Redis连接失败，缓存功能将不可用", error=str(e))
                cls._redis_client = None
        return cls._redis_client
    
    @classmethod
    def get_intermediate_results(cls, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        从缓存获取中间结果
        
        Args:
            cache_key: 缓存key（基于检测得分生成）
        
        Returns:
            中间结果，如果不存在则返回None
        """
        client = cls._get_redis_client()
        if not client:
            return None
        
        try:
            key = f"{cls._cache_prefix}:intermediate:{cache_key}"
            data = client.get(key)
            if data:
                result = json.loads(data)
                logger.info("从缓存获取中间结果", cache_key=cache_key)
                return result
        except Exception as e:
            logger.error("获取缓存失败", cache_key=cache_key, error=str(e))
        
        return None
    
    @classmethod
    def set_intermediate_results(cls, cache_key: str, data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """
        保存中间结果到缓存
        
        Args:
            cache_key: 缓存key（基于检测得分生成）
            data: 中间结果数据
            ttl: 过期时间（秒），如果为None则使用默认值
        
        Returns:
            是否保存成功
        """
        client = cls._get_redis_client()
        if not client:
            return False
        
        try:
            key = f"{cls._cache_prefix}:intermediate:{cache_key}"
            json_data = json.dumps(data, ensure_ascii=False)
            ttl = ttl or cls._default_ttl
            client.setex(key, ttl, json_data)
            logger.info("中间结果已缓存", cache_key=cache_key, ttl=ttl)
            return True
        except Exception as e:
            logger.error("保存缓存失败", cache_key=cache_key, error=str(e))
            return False
    
    @classmethod
    def get_detection_result(cls, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        从缓存获取检测结果（特征得分）
        
        Args:
            cache_key: 缓存key（基于检测得分生成）
        
        Returns:
            检测结果，如果不存在则返回None
        """
        client = cls._get_redis_client()
        if not client:
            return None
        
        try:
            key = f"{cls._cache_prefix}:detection:{cache_key}"
            data = client.get(key)
            if data:
                result = json.loads(data)
                logger.info("从缓存获取检测结果", cache_key=cache_key)
                return result
        except Exception as e:
            logger.error("获取缓存失败", cache_key=cache_key, error=str(e))
        
        return None
    
    @classmethod
    def set_detection_result(cls, cache_key: str, data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """
        保存检测结果到缓存
        
        Args:
            cache_key: 缓存key（基于检测得分生成）
            data: 检测结果数据（包含detection_scores等）
            ttl: 过期时间（秒），如果为None则使用默认值
        
        Returns:
            是否保存成功
        """
        client = cls._get_redis_client()
        if not client:
            return False
        
        try:
            key = f"{cls._cache_prefix}:detection:{cache_key}"
            json_data = json.dumps(data, ensure_ascii=False)
            ttl = ttl or cls._default_ttl
            client.setex(key, ttl, json_data)
            logger.info("检测结果已缓存", cache_key=cache_key, ttl=ttl)
            return True
        except Exception as e:
            logger.error("保存缓存失败", cache_key=cache_key, error=str(e))
            return False
    
    @classmethod
    def delete_cache(cls, cache_key: str) -> bool:
        """
        删除缓存
        
        Args:
            cache_key: 缓存key
        
        Returns:
            是否删除成功
        """
        client = cls._get_redis_client()
        if not client:
            return False
        
        try:
            # 删除中间结果缓存
            intermediate_key = f"{cls._cache_prefix}:intermediate:{cache_key}"
            # 删除检测结果缓存
            detection_key = f"{cls._cache_prefix}:detection:{cache_key}"
            
            client.delete(intermediate_key, detection_key)
            logger.info("缓存已删除", cache_key=cache_key)
            return True
        except Exception as e:
            logger.error("删除缓存失败", cache_key=cache_key, error=str(e))
            return False
    
    @classmethod
    def clear_all_cache(cls) -> bool:
        """
        清空所有缓存（谨慎使用）
        
        Returns:
            是否清空成功
        """
        client = cls._get_redis_client()
        if not client:
            return False
        
        try:
            pattern = f"{cls._cache_prefix}:*"
            keys = client.keys(pattern)
            if keys:
                client.delete(*keys)
                logger.info("所有缓存已清空", count=len(keys))
            return True
        except Exception as e:
            logger.error("清空缓存失败", error=str(e))
            return False

