"""
运行数据库迁移脚本
用于在Docker容器中运行Alembic迁移
"""
import subprocess
import sys
import os

# 设置工作目录
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_migrations():
    """运行数据库迁移"""
    try:
        print("运行数据库迁移...")
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            check=True,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        print("数据库迁移完成")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"迁移失败: {e.stderr}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(run_migrations())

