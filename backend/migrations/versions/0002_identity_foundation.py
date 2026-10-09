"""Add public user identities and opaque server-side authentication sessions.

No legacy translation owner_id is migrated or reinterpreted.
"""
from alembic import op
import sqlalchemy as sa

revision = '0002_identity_foundation'
down_revision = '0001_translation_persistence'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'users',
        sa.Column('user_id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('email_normalized', sa.Text(), nullable=False),
        sa.Column('password_hash', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('email_normalized', name='uq_users_email_normalized'),
    )
    op.create_table(
        'auth_sessions',
        sa.Column('session_id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.Uuid(as_uuid=True), sa.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_hash', sa.String(64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('token_hash', name='uq_auth_sessions_token_hash'),
        sa.CheckConstraint('expires_at > created_at', name='ck_auth_sessions_expiry'),
    )
    op.create_index('ix_auth_sessions_user_id', 'auth_sessions', ['user_id'])
    op.create_index('ix_auth_sessions_expires_at', 'auth_sessions', ['expires_at'])


def downgrade():
    op.drop_table('auth_sessions')
    op.drop_table('users')
