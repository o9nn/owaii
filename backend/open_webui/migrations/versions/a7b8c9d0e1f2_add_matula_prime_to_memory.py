"""add matula_prime and memory_type to memory table

Revision ID: a7b8c9d0e1f2
Revises: 56359461a091
Create Date: 2026-05-04 12:00:00.000000

Every memory atom now carries a Matula prime as its eternal name
(``matula_prime``) and an optional subsystem classification
(``memory_type``) chosen from the six-type regime-cognitive-ai schema:
episodic | semantic | procedural | sensory | working | intentional.

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, None] = '56359461a091'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add matula_prime (nullable so existing rows are left intact)
    op.add_column('memory', sa.Column('matula_prime', sa.BigInteger(), nullable=True))
    # Add memory_type for six-subsystem classification
    op.add_column('memory', sa.Column('memory_type', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('memory', 'memory_type')
    op.drop_column('memory', 'matula_prime')
