"""add_quality_score_to_system_learning_data

Revision ID: bb57d8568340
Revises: 002_create_embedding_index
Create Date: 2025-12-10 08:07:56.938732

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bb57d8568340'
down_revision = '002_create_embedding_index'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 添加质量分数字段
    op.add_column(
        'system_learning_data',
        sa.Column('quality_score', sa.Integer(), nullable=True, comment='处理结果质量分数（0-100）')
    )


def downgrade() -> None:
    # 删除质量分数字段
    op.drop_column('system_learning_data', 'quality_score')

