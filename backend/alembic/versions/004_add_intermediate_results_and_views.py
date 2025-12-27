"""add_intermediate_results_and_views

Revision ID: 004_add_intermediate_results_and_views
Revises: 003_add_ai_monitoring
Create Date: 2025-12-21 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid


# revision identifiers, used by Alembic.
revision = '004_intermediate_views'
down_revision = '003_add_ai_monitoring'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================
    # 任务1：创建中间结果表（视角无关）
    # ============================================
    # 检查表是否已存在（处理部分执行的情况）
    from sqlalchemy import inspect, text
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    if 'document_intermediate_results' not in existing_tables:
        op.create_table(
            'document_intermediate_results',
            sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            sa.Column('document_id', UUID(as_uuid=True), nullable=False, comment='文档ID'),
            sa.Column('content', sa.Text(), nullable=False, comment='提取的原始内容（视角无关）'),
            sa.Column('preprocessed_content', sa.Text(), nullable=True, comment='预处理后的内容（视角无关）'),
            sa.Column('segments', JSONB(), nullable=True, comment='段落切分结果（视角无关）'),
            sa.Column('metadata', JSONB(), nullable=True, comment='元数据（视角无关）'),  # 注意：列名是metadata，但模型中使用metadata_json避免冲突
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment='创建时间'),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now(), comment='更新时间'),
            sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
            sa.UniqueConstraint('document_id', name='uq_intermediate_results_document_id'),
        )
        
        # 创建索引
        op.create_index('idx_intermediate_results_document_id', 'document_intermediate_results', ['document_id'])
    else:
        # 表已存在，检查索引是否存在
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('document_intermediate_results')]
        if 'idx_intermediate_results_document_id' not in existing_indexes:
            op.create_index('idx_intermediate_results_document_id', 'document_intermediate_results', ['document_id'])
    
    # ============================================
    # 任务2：修改 processing_results 表（每个view独立存储）
    # ============================================
    # 检查字段是否已存在
    existing_pr_columns = [col['name'] for col in inspector.get_columns('processing_results')]
    
    # 删除旧的唯一约束（如果存在）
    try:
        op.drop_constraint('uq_processing_results_document_id', 'processing_results', type_='unique')
    except Exception:
        pass  # 约束可能已不存在
    
    # 添加新字段（如果不存在）
    if 'view' not in existing_pr_columns:
        op.add_column('processing_results', 
            sa.Column('view', sa.String(50), nullable=True, comment='视角名称（learning/qa/system）'))
    if 'is_primary' not in existing_pr_columns:
        op.add_column('processing_results', 
            sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='false', comment='是否为主视角'))
    
    # 为历史数据填充默认view（如果view字段存在且有空值）
    # 注意：如果字段刚添加，existing_pr_columns可能不包含它，所以需要重新检查
    current_pr_columns = [col['name'] for col in inspector.get_columns('processing_results')]
    if 'view' in current_pr_columns:
        op.execute("""
            UPDATE processing_results 
            SET view = CASE 
                WHEN document_type = 'interview' THEN 'qa'
                WHEN document_type = 'architecture' THEN 'system'
                WHEN document_type = 'technical' THEN 'learning'
                ELSE 'learning'
            END,
            is_primary = TRUE
            WHERE view IS NULL
        """)
    
    # 将view字段设为NOT NULL（填充数据后，如果字段存在）
    if 'view' in current_pr_columns:
        try:
            op.alter_column('processing_results', 'view', nullable=False)
        except Exception:
            pass  # 可能已经是NOT NULL
    
    # 创建新的唯一约束：一个文档的同一个view只能有一条记录（如果不存在）
    existing_pr_constraints = [c['name'] for c in inspector.get_unique_constraints('processing_results')]
    if 'uq_processing_result_document_view' not in existing_pr_constraints:
        op.create_unique_constraint('uq_processing_result_document_view', 'processing_results', ['document_id', 'view'])
    
    # 创建索引（如果不存在）
    existing_pr_indexes = [idx['name'] for idx in inspector.get_indexes('processing_results')]
    if 'idx_processing_results_view' not in existing_pr_indexes and 'view' in existing_pr_columns:
        op.create_index('idx_processing_results_view', 'processing_results', ['view'])
    if 'idx_processing_results_is_primary' not in existing_pr_indexes and 'is_primary' in existing_pr_columns:
        op.create_index('idx_processing_results_is_primary', 'processing_results', ['is_primary'])
    
    # ============================================
    # 任务3：修改 document_types 表（添加视角相关字段）
    # ============================================
    # 检查字段是否已存在
    existing_dt_columns = [col['name'] for col in inspector.get_columns('document_types')]
    
    # 添加新字段（如果不存在）
    if 'primary_view' not in existing_dt_columns:
        op.add_column('document_types', 
            sa.Column('primary_view', sa.String(50), nullable=True, comment='主视角（用于UI和算力分配）'))
    if 'enabled_views' not in existing_dt_columns:
        op.add_column('document_types', 
            sa.Column('enabled_views', JSONB(), nullable=True, comment='启用的视角列表'))
    if 'detection_scores' not in existing_dt_columns:
        op.add_column('document_types', 
            sa.Column('detection_scores', JSONB(), nullable=True, comment='系统检测的特征得分（用于缓存key）'))
    
    # 为历史数据填充默认值（如果字段存在且有空值）
    # 重新检查字段（可能刚添加）
    current_dt_columns = [col['name'] for col in inspector.get_columns('document_types')]
    if 'primary_view' in current_dt_columns:
        op.execute("""
            UPDATE document_types 
            SET primary_view = CASE 
                WHEN detected_type = 'interview' THEN 'qa'
                WHEN detected_type = 'architecture' THEN 'system'
                WHEN detected_type = 'technical' THEN 'learning'
                ELSE 'learning'
            END,
            enabled_views = jsonb_build_array(
                CASE 
                    WHEN detected_type = 'interview' THEN 'qa'
                    WHEN detected_type = 'architecture' THEN 'system'
                    WHEN detected_type = 'technical' THEN 'learning'
                    ELSE 'learning'
                END
            ),
            detection_scores = jsonb_build_object(
                CASE 
                    WHEN detected_type = 'interview' THEN 'qa'
                    WHEN detected_type = 'architecture' THEN 'system'
                    WHEN detected_type = 'technical' THEN 'learning'
                    ELSE 'learning'
                END, 
                1.0
            )
            WHERE primary_view IS NULL
        """)
    
    # 创建索引（如果不存在）
    existing_dt_indexes = [idx['name'] for idx in inspector.get_indexes('document_types')]
    if 'idx_document_types_primary_view' not in existing_dt_indexes and 'primary_view' in current_dt_columns:
        op.create_index('idx_document_types_primary_view', 'document_types', ['primary_view'])


def downgrade() -> None:
    # 删除索引
    op.drop_index('idx_document_types_primary_view', 'document_types')
    op.drop_index('idx_processing_results_is_primary', 'processing_results')
    op.drop_index('idx_processing_results_view', 'processing_results')
    op.drop_index('idx_intermediate_results_document_id', 'document_intermediate_results')
    
    # 删除 document_types 表的新字段
    op.drop_column('document_types', 'detection_scores')
    op.drop_column('document_types', 'enabled_views')
    op.drop_column('document_types', 'primary_view')
    
    # 恢复 processing_results 表
    op.drop_constraint('uq_processing_result_document_view', 'processing_results', type_='unique')
    op.drop_column('processing_results', 'is_primary')
    op.drop_column('processing_results', 'view')
    op.create_unique_constraint('uq_processing_results_document_id', 'processing_results', ['document_id'])
    
    # 删除中间结果表
    op.drop_table('document_intermediate_results')

