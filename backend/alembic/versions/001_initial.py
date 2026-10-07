"""Initial database schema

Revision ID: 001_initial
Revises: 
Create Date: 2026-10-07 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Sessions table
    op.create_table(
        'sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), default='Untitled Session'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # Designs table
    op.create_table(
        'designs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sessions.id', ondelete='CASCADE')),
        sa.Column('version', sa.Integer, default=1),
        sa.Column('prompt', sa.Text, nullable=False),
        sa.Column('cad_code', sa.Text),
        sa.Column('feature_tree', postgresql.JSON, default={}),
        sa.Column('geometry_valid', sa.Boolean, default=False),
        sa.Column('dfm_report', postgresql.JSON, default={}),
        sa.Column('engineering_report', postgresql.JSON, default={}),
        sa.Column('cost_estimate', postgresql.JSON, default={}),
        sa.Column('safety_report', postgresql.JSON, default={}),
        sa.Column('alternatives', postgresql.JSON, default=[]),
        sa.Column('confidence_scores', postgresql.JSON, default={}),
        sa.Column('status', sa.String(50), default='PENDING'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_designs_session_id', 'designs', ['session_id'])
    op.create_index('idx_designs_status', 'designs', ['status'])

    # Agent logs table
    op.create_table(
        'agent_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('design_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('designs.id', ondelete='CASCADE')),
        sa.Column('agent_name', sa.String(100), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('message', sa.Text),
        sa.Column('confidence', sa.Float, default=0.0),
        sa.Column('payload', postgresql.JSON, default={}),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_agent_logs_design_id', 'agent_logs', ['design_id'])

    # Export artifacts table
    op.create_table(
        'export_artifacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('design_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('designs.id', ondelete='CASCADE')),
        sa.Column('format', sa.String(20), nullable=False),
        sa.Column('file_path', sa.Text, nullable=False),
        sa.Column('file_size_bytes', sa.BigInteger, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_export_artifacts_design_id', 'export_artifacts', ['design_id'])


def downgrade() -> None:
    op.drop_table('export_artifacts')
    op.drop_table('agent_logs')
    op.drop_table('designs')
    op.drop_table('sessions')
