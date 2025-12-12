"""
同步数据库连接配置（用于Celery任务）
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# 创建同步引擎（用于Celery任务）
sync_engine = create_engine(
    settings.DATABASE_URL,  # 使用同步URL
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

# 创建同步会话工厂
SessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
)

# 使用相同的Base
from app.core.database import Base

def get_sync_db():
    """获取同步数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

