"""add nps_score to feedback

Revision ID: 1b2193d76fcc
Revises: 6a3f9c21d7b4
Create Date: 2026-10-16 00:09:31.793678

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '1b2193d76fcc'
down_revision: Union[str, None] = '6a3f9c21d7b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE feedback ADD COLUMN IF NOT EXISTS nps_score INTEGER")
    op.execute("ALTER TABLE feedback DROP CONSTRAINT IF EXISTS ck_feedback_nps_score_range")
    op.execute(
        "ALTER TABLE feedback ADD CONSTRAINT ck_feedback_nps_score_range "
        "CHECK (nps_score IS NULL OR (nps_score >= 0 AND nps_score <= 10))"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE feedback DROP CONSTRAINT IF EXISTS ck_feedback_nps_score_range")
    op.execute("ALTER TABLE feedback DROP COLUMN IF EXISTS nps_score")
