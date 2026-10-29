"""Add coordinated background and text colors to business card profiles."""
from alembic import op
import sqlalchemy as sa

revision = '20261029_business_card_themes'
down_revision = '20261029_business_card_profiles'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('business_cards', sa.Column('background_end', sa.String(length=7), nullable=True), schema='tura')
    op.add_column('business_cards', sa.Column('background_angle', sa.Integer(), nullable=False, server_default='135'), schema='tura')
    op.add_column('business_cards', sa.Column('text_color', sa.String(length=7), nullable=True), schema='tura')
    op.add_column('business_cards', sa.Column('accent_color', sa.String(length=7), nullable=True), schema='tura')
    op.alter_column('business_cards', 'background_angle', server_default=None, schema='tura')


def downgrade():
    op.drop_column('business_cards', 'accent_color', schema='tura')
    op.drop_column('business_cards', 'text_color', schema='tura')
    op.drop_column('business_cards', 'background_angle', schema='tura')
    op.drop_column('business_cards', 'background_end', schema='tura')
