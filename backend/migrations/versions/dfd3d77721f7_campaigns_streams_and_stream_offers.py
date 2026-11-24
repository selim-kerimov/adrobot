"""campaigns, streams and stream offers

Revision ID: dfd3d77721f7
Revises:
Create Date: 2026-11-21 20:09:09.040837

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "dfd3d77721f7"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "campaigns",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("keitaro_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("alias", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("keitaro_id"),
    )
    op.create_table(
        "streams",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("keitaro_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("has_offers", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("keitaro_id"),
    )
    op.create_table(
        "stream_offers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("stream_id", sa.Integer(), nullable=False),
        sa.Column("offer_id", sa.Integer(), nullable=False),
        sa.Column("offer_name", sa.String(length=255), nullable=False),
        sa.Column("share", sa.Integer(), nullable=False),
        sa.Column(
            "state",
            sa.Enum("active", "removed", name="offerstate", native_enum=False, length=16),
            nullable=False,
        ),
        sa.Column("pinned", sa.Boolean(), nullable=False),
        sa.Column("published_share", sa.Integer(), nullable=True),
        sa.Column(
            "published_state",
            sa.Enum("active", "removed", name="offerstate", native_enum=False, length=16),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["stream_id"], ["streams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stream_id", "offer_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("stream_offers")
    op.drop_table("streams")
    op.drop_table("campaigns")
