"""Add staff names and nurse profiles."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c82f1946ad31"
down_revision: Union[str, Sequence[str], None] = ("6a3f9c21d7b4", "5d88b0b6c31a")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("first_name", sa.String(length=50), nullable=True))
    op.add_column("users", sa.Column("last_name", sa.String(length=50), nullable=True))
    op.create_table(
        "nurse_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("first_name", sa.String(length=50), nullable=False),
        sa.Column("last_name", sa.String(length=50), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_nurse_profiles_id", "nurse_profiles", ["id"], unique=False)
    op.create_index("ix_nurse_profiles_user_id", "nurse_profiles", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_nurse_profiles_user_id", table_name="nurse_profiles")
    op.drop_index("ix_nurse_profiles_id", table_name="nurse_profiles")
    op.drop_table("nurse_profiles")
    op.drop_column("users", "last_name")
    op.drop_column("users", "first_name")
