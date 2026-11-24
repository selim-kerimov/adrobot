from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.editor.models import OfferState


class StreamOfferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    offer_id: int
    offer_name: str
    share: int
    state: OfferState
    pinned: bool
    is_draft: bool


class StreamOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    keitaro_id: int
    name: str
    position: int
    has_offers: bool
    is_draft: bool
    offers: list[StreamOfferOut]


class CampaignSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    keitaro_id: int
    name: str
    alias: str | None
    synced_at: datetime | None


class CampaignOut(CampaignSummary):
    streams: list[StreamOut]


class AddOfferIn(BaseModel):
    offer_id: int


class PinIn(BaseModel):
    # Without a share the current one is pinned.
    share: int | None = Field(default=None, ge=0, le=100)
