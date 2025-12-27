"""
检查数据库迁移状态
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import AsyncSessionLocal
from sqlalchemy import text
import structlog

logger = structlog.get_logger()


async def check_tables():
    """检查监控表是否存在"""
    db = AsyncSessionLocal()
    try:
        # 检查表是否存在
        tables_to_check = [
            'ai_call_metrics',
            'ai_result_quality',
            'ai_result_consistency'
        ]
        
        result = await db.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('ai_call_metrics', 'ai_result_quality', 'ai_result_consistency')
        """))
        
        existing_tables = [row[0] for row in result.fetchall()]
        
        print(f"已存在的监控表: {existing_tables}")
        
        missing_tables = [t for t in tables_to_check if t not in existing_tables]
        if missing_tables:
            print(f"缺失的表: {missing_tables}")
            print("请运行数据库迁移: alembic upgrade head")
            return False
        else:
            print("所有监控表已存在")
            return True
            
    except Exception as e:
        logger.error("检查表失败", error=str(e))
        return False
    finally:
        await db.close()


if __name__ == "__main__":
    result = asyncio.run(check_tables())
    sys.exit(0 if result else 1)

