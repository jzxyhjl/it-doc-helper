"""
数据库初始化脚本
用于在Docker容器启动后初始化数据库表结构
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import engine, Base
from app.models import *  # 导入所有模型
import structlog

logger = structlog.get_logger()


async def init_db():
    """初始化数据库表结构"""
    try:
        logger.info("开始初始化数据库...")
        
        # 创建所有表
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("数据库表创建成功")
        
        # 启用pgvector扩展（必须在创建表之前）
        try:
            async with engine.begin() as conn:
                await conn.execute(
                    "CREATE EXTENSION IF NOT EXISTS vector;"
                )
            logger.info("pgvector扩展已启用")
        except Exception as e:
            logger.warning("pgvector扩展启用失败（可能未安装）", error=str(e))
            logger.warning("如果使用标准PostgreSQL镜像，需要安装pgvector扩展")
            logger.warning("建议使用pgvector/pgvector:pg15镜像（已在docker-compose.yml中配置）")
        
    except Exception as e:
        logger.error("数据库初始化失败", error=str(e))
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_db())

