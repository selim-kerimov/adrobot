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
    state: str
    has_offers: bool
    is_draft: bool
    offers: list[StreamOfferOut]


class CampaignListItem(BaseModel):
    keitaro_id: int
    name: str
    state: str
    # None while the campaign has never been loaded into the editor.
    synced_at: datetime | None


class CampaignOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    keitaro_id: int
    name: str
    alias: str | None
    state: str
    synced_at: datetime | None
    streams: list[StreamOut]


class CampaignUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=255)


class AddOfferIn(BaseModel):
    offer_id: int


class PinIn(BaseModel):
    # Without a share the current one is pinned.
    share: int | None = Field(default=None, ge=0, le=100)
