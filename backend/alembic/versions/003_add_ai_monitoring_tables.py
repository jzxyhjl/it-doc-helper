"""add_ai_monitoring_tables

Revision ID: 003_add_ai_monitoring
Revises: bb57d8568340
Create Date: 2025-12-19 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid


# revision identifiers, used by Alembic.
revision = '003_add_ai_monitoring'
down_revision = 'bb57d8568340'  # 确保与上一个迁移版本一致
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建 ai_call_metrics 表
    op.create_table(
        'ai_call_metrics',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('document_id', UUID(as_uuid=True), nullable=True, comment='文档ID'),
        sa.Column('call_type', sa.String(50), nullable=True, comment='调用类型（chat_completion/generate_json/generate_with_sources）'),
        sa.Column('model', sa.String(50), nullable=True, comment='模型名称'),
        sa.Column('status', sa.String(20), nullable=False, comment='状态（success/timeout/error_400/error_429/error_500等）'),
        sa.Column('response_time_ms', sa.Integer(), nullable=True, comment='响应时间（毫秒）'),
        sa.Column('error_type', sa.String(50), nullable=True, comment='错误类型（timeout/rate_limit/server_error/network_error等）'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='错误信息'),
        sa.Column('retry_count', sa.Integer(), nullable=False, default=0, comment='重试次数'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment='创建时间'),
        sa.Index('idx_ai_call_metrics_document_id', 'document_id'),
        sa.Index('idx_ai_call_metrics_created_at', 'created_at'),
        sa.Index('idx_ai_call_metrics_status', 'status'),
    )
    
    # 创建 ai_result_quality 表
    op.create_table(
        'ai_result_quality',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('document_id', UUID(as_uuid=True), nullable=False, comment='文档ID'),
        sa.Column('document_type', sa.String(50), nullable=True, comment='文档类型（technical/interview/architecture）'),
        sa.Column('field_completeness', sa.Float(), nullable=True, comment='字段完整性（0-1）'),
        sa.Column('confidence_avg', sa.Float(), nullable=True, comment='平均置信度'),
        sa.Column('confidence_min', sa.Float(), nullable=True, comment='最小置信度'),
        sa.Column('confidence_max', sa.Float(), nullable=True, comment='最大置信度'),
        sa.Column('sources_count', sa.Integer(), nullable=True, comment='来源片段数量'),
        sa.Column('sources_completeness', sa.Float(), nullable=True, comment='来源完整性（0-1）'),
        sa.Column('quality_score', sa.Float(), nullable=True, comment='综合质量分数（0-100）'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment='创建时间'),
        sa.Index('idx_ai_result_quality_document_id', 'document_id'),
        sa.Index('idx_ai_result_quality_document_type', 'document_type'),
        sa.Index('idx_ai_result_quality_created_at', 'created_at'),
        sa.Index('idx_ai_result_quality_quality_score', 'quality_score'),
    )
    
    # 创建 ai_result_consistency 表（可选，用于结果一致性检查）
    op.create_table(
        'ai_result_consistency',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('document_id', UUID(as_uuid=True), nullable=False, comment='文档ID'),
        sa.Column('test_run_id', sa.String(100), nullable=True, comment='测试运行ID（用于对比多次运行）'),
        sa.Column('field_name', sa.String(100), nullable=True, comment='字段名'),
        sa.Column('field_value_hash', sa.String(64), nullable=True, comment='字段值哈希（用于对比）'),
        sa.Column('confidence_diff', sa.Float(), nullable=True, comment='置信度差异（与基准对比）'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment='创建时间'),
        sa.Index('idx_ai_result_consistency_document_id', 'document_id'),
        sa.Index('idx_ai_result_consistency_test_run_id', 'test_run_id'),
    )


def downgrade() -> None:
    # 删除表
    op.drop_table('ai_result_consistency')
    op.drop_table('ai_result_quality')
    op.drop_table('ai_call_metrics')

