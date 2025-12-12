"""create embedding index

Revision ID: 002_create_embedding_index
Revises: 001_add_pgvector_embedding
Create Date: 2025-12-09 10:05:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '002_create_embedding_index'
down_revision: Union[str, None] = '001_add_pgvector_embedding'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建向量索引（使用IVFFlat，适合小规模数据<1000条）
    # 如果数据量较大，可以考虑使用HNSW索引
    op.execute('''
        CREATE INDEX IF NOT EXISTS idx_system_learning_data_embedding 
        ON system_learning_data 
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
    ''')


def downgrade() -> None:
    # 删除向量索引
    op.execute('DROP INDEX IF EXISTS idx_system_learning_data_embedding;')

