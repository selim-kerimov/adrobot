from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class OfferState(StrEnum):
    ACTIVE = "active"
    REMOVED = "removed"


# Stored as a plain string column holding the values ("active"), not the names.
OfferStateColumn = Enum(
    OfferState,
    native_enum=False,
    length=16,
    values_callable=lambda states: [state.value for state in states],
)


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    keitaro_id: Mapped[int] = mapped_column(unique=True)
    name: Mapped[str] = mapped_column(String(255))
    alias: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    streams: Mapped[list["Stream"]] = relationship(
        back_populates="campaign",
        cascade="all, delete-orphan",
        order_by="Stream.position",
    )


class Stream(Base):
    __tablename__ = "streams"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"))
    keitaro_id: Mapped[int] = mapped_column(unique=True)
    name: Mapped[str] = mapped_column(String(255))
    position: Mapped[int] = mapped_column(default=0)
    # Streams without offers (e.g. a redirect to google) are shown by name only.
    has_offers: Mapped[bool] = mapped_column(default=False)

    campaign: Mapped[Campaign] = relationship(back_populates="streams")
    offers: Mapped[list["StreamOffer"]] = relationship(
        back_populates="stream",
        cascade="all, delete-orphan",
        order_by="StreamOffer.id",
    )

    @property
    def is_draft(self) -> bool:
        """True when the stream has changes that are not pushed to Keitaro yet."""
        return any(offer.is_draft for offer in self.offers)


class StreamOffer(Base):
    """An offer in a stream.

    `share` and `state` are what the user sees and edits. `published_share` and
    `published_state` are what Keitaro has: they are None for an offer that was added
    here and never pushed. Cancel restores the published values, push copies the
    current values into them.
    """

    __tablename__ = "stream_offers"
    __table_args__ = (UniqueConstraint("stream_id", "offer_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    stream_id: Mapped[int] = mapped_column(ForeignKey("streams.id", ondelete="CASCADE"))
    offer_id: Mapped[int]  # offer ID in Keitaro
    offer_name: Mapped[str] = mapped_column(String(255))

    share: Mapped[int] = mapped_column(default=0)
    state: Mapped[OfferState] = mapped_column(OfferStateColumn, default=OfferState.ACTIVE)
    # A pinned share is kept as is when the other shares are recalculated.
    pinned: Mapped[bool] = mapped_column(default=False)

    published_share: Mapped[int | None]
    published_state: Mapped[OfferState | None] = mapped_column(OfferStateColumn)

    stream: Mapped[Stream] = relationship(back_populates="offers")

    @property
    def is_draft(self) -> bool:
        return (self.state, self.share) != (self.published_state, self.published_share)
