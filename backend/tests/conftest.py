"""
pytest配置和fixtures
"""
import pytest
import asyncio
import os
import sys
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

# 添加backend路径到sys.path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

# 配置asyncio事件循环
@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环用于异步测试"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# 测试配置
@pytest.fixture(scope="session")
def test_config():
    """测试配置"""
    return {
        "base_url": os.getenv("TEST_BASE_URL", "http://localhost:8000"),
        "api_base": os.getenv("TEST_API_BASE", "http://localhost:8000/api/v1"),
        "timeout": int(os.getenv("TEST_TIMEOUT", "600")),
    }

# 测试文档路径
@pytest.fixture(scope="session")
def test_documents_dir():
    """测试文档目录"""
    return Path(__file__).parent / "fixtures" / "test_documents"

# 数据库session fixture（用于需要数据库的测试）
@pytest.fixture
async def db_session():
    """
    创建数据库session（使用实际数据库连接）
    
    注意：这个fixture使用实际的数据库连接，测试后会自动回滚
    确保测试不会影响实际数据
    """
    from app.core.database import AsyncSessionLocal
    
    # 使用现有的数据库连接配置
    async with AsyncSessionLocal() as session:
        # 开始事务
        async with session.begin():
            try:
                yield session
            finally:
                # 测试后回滚，确保不影响实际数据
                await session.rollback()

