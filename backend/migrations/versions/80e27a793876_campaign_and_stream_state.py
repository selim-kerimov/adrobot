"""campaign and stream state

Revision ID: 80e27a793876
Revises: dfd3d77721f7
Create Date: 2026-11-24 22:07:15.298418

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "80e27a793876"
down_revision: str | Sequence[str] | None = "dfd3d77721f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "campaigns",
        sa.Column("state", sa.String(length=16), server_default="active", nullable=False),
    )
    op.add_column(
        "streams", sa.Column("state", sa.String(length=16), server_default="active", nullable=False)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("streams", "state")
    op.drop_column("campaigns", "state")
