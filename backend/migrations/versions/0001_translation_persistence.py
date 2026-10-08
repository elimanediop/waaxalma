"""Initial translation session persistence (pre-authentication)."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
revision='0001_translation_persistence'
down_revision=None
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('translation_sessions',
        sa.Column('session_id',sa.Text(),primary_key=True),
        sa.Column('agent_name',sa.Text(),nullable=False),
        sa.Column('owner_id',sa.Text(),nullable=True),
        sa.Column('execution_mode',sa.Text(),nullable=False),
        sa.Column('source_language',sa.Text(),nullable=False),
        sa.Column('target_language',sa.Text(),nullable=False),
        sa.Column('status',sa.Text(),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('closed_at',sa.DateTime(timezone=True),nullable=True),
        sa.Column('metadata_json',JSONB(),nullable=False))
    op.create_index('ix_translation_sessions_owner_id','translation_sessions',['owner_id'])
    op.create_table('translation_messages',
        sa.Column('id',sa.BigInteger(),sa.Identity(),primary_key=True),
        sa.Column('session_id',sa.Text(),sa.ForeignKey('translation_sessions.session_id',ondelete='CASCADE'),nullable=False),
        sa.Column('role',sa.Text(),nullable=False),
        sa.Column('content',sa.Text(),nullable=False),
        sa.Column('created_at',sa.Text(),nullable=False))
    op.create_index('ix_translation_messages_session_id_id','translation_messages',['session_id','id'])

def downgrade():
    op.drop_table('translation_messages')
    op.drop_table('translation_sessions')
