"""allow_device_id_reuse_across_users

Revision ID: 9f7e6d5c4b3a
Revises: b2c3d4e5f6a7
Create Date: 2026-04-20 16:48:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9f7e6d5c4b3a"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Allow the same device_id to appear under different users."""
    op.drop_constraint(
        "refresh_token_device_id_key",
        "refresh_token",
        schema="auth",
        type_="unique",
    )
    op.create_index(
        "auth_refresh_token_device_id_idx",
        "refresh_token",
        ["device_id"],
        unique=False,
        schema="auth",
    )


def downgrade() -> None:
    """Restore global device_id uniqueness."""
    op.drop_index(
        "auth_refresh_token_device_id_idx",
        table_name="refresh_token",
        schema="auth",
    )
    op.create_unique_constraint(
        "refresh_token_device_id_key",
        "refresh_token",
        ["device_id"],
        schema="auth",
    )
