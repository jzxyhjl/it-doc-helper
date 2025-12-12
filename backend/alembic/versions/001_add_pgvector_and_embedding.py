"""add pgvector extension and embedding field

Revision ID: 001_add_pgvector_embedding
Revises: 
Create Date: 2025-12-09 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = '001_add_pgvector_embedding'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 启用pgvector扩展
    op.execute('CREATE EXTENSION IF NOT EXISTS vector;')
    
    # 在system_learning_data表中添加embedding字段
    op.add_column('system_learning_data', 
                  sa.Column('embedding', Vector(1536), nullable=True, comment='内容向量（使用pgvector，1536维）'))
    
    # 创建向量索引（使用IVFFlat，适合小规模数据）
    # 注意：索引创建需要先有数据，所以这里先不创建索引
    # 索引将在有数据后通过单独的迁移或手动创建
    # op.execute('''
    #     CREATE INDEX ON system_learning_data 
    #     USING ivfflat (embedding vector_cosine_ops)
    #     WITH (lists = 100);
    # ''')


def downgrade() -> None:
    # 删除embedding字段
    op.drop_column('system_learning_data', 'embedding')
    
    # 注意：不删除pgvector扩展，因为可能被其他表使用
    # 如果需要删除扩展，可以手动执行：
    # op.execute('DROP EXTENSION IF EXISTS vector;')

