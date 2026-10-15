"""Add persisted pilot voice reviews and NPS scores.

Revision ID: 6a3f9c21d7b4
Revises: 8a1d4f7c2b90
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6a3f9c21d7b4"
down_revision: Union[str, None] = "8a1d4f7c2b90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "voice_interactions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("transcript", sa.Text(), nullable=False),
        sa.Column("intent", sa.String(length=50), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("entities_json", sa.JSON(), nullable=True),
        sa.Column("fallback_used", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("response_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("reviewed_correct", sa.Boolean(), nullable=True),
    )
    op.create_index("ix_voice_interactions_id", "voice_interactions", ["id"])
    op.create_index("ix_voice_interactions_user_id", "voice_interactions", ["user_id"])
    op.create_index("ix_voice_interactions_created_at", "voice_interactions", ["created_at"])
    op.add_column("feedback", sa.Column("nps_score", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "ck_feedback_nps_score_range",
        "feedback",
        "nps_score IS NULL OR (nps_score >= 0 AND nps_score <= 10)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_feedback_nps_score_range", "feedback", type_="check")
    op.drop_column("feedback", "nps_score")
    op.drop_index("ix_voice_interactions_created_at", table_name="voice_interactions")
    op.drop_index("ix_voice_interactions_user_id", table_name="voice_interactions")
    op.drop_index("ix_voice_interactions_id", table_name="voice_interactions")
    op.drop_table("voice_interactions")
