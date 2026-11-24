from fastapi import APIRouter
from sqlalchemy import select

from app.db import SessionDep
from app.editor import service
from app.editor.models import Campaign, Stream
from app.editor.schemas import AddOfferIn, CampaignOut, CampaignSummary, PinIn, StreamOut
from app.keitaro import KeitaroDep

router = APIRouter(prefix="/api", tags=["editor"])


@router.get("/campaigns", response_model=list[CampaignSummary])
def list_campaigns(session: SessionDep) -> list[Campaign]:
    return list(session.scalars(select(Campaign).order_by(Campaign.created_at.desc())))


@router.get("/campaigns/{campaign_id}", response_model=CampaignOut)
def get_campaign(campaign_id: int, session: SessionDep) -> Campaign:
    return service.get_campaign(session, campaign_id)


@router.post("/campaigns/{campaign_id}/fetch", response_model=CampaignOut)
def fetch_campaign(campaign_id: int, session: SessionDep, keitaro: KeitaroDep) -> Campaign:
    campaign = service.fetch_campaign(session, keitaro, campaign_id)
    session.commit()
    return campaign


@router.post("/streams/{stream_id}/offers", response_model=StreamOut)
def add_offer(stream_id: int, body: AddOfferIn, session: SessionDep, keitaro: KeitaroDep) -> Stream:
    stream = service.get_stream(session, stream_id)
    service.add_offer(keitaro, stream, body.offer_id)
    session.commit()
    return stream


@router.post("/streams/{stream_id}/push", response_model=StreamOut)
def push_stream(stream_id: int, session: SessionDep, keitaro: KeitaroDep) -> Stream:
    stream = service.get_stream(session, stream_id)
    service.push_stream(keitaro, stream)
    session.commit()
    return stream


@router.post("/streams/{stream_id}/cancel", response_model=StreamOut)
def cancel_stream(stream_id: int, session: SessionDep) -> Stream:
    stream = service.get_stream(session, stream_id)
    service.cancel_stream(stream)
    session.commit()
    return stream


@router.post("/offers/{offer_id}/remove", response_model=StreamOut)
def remove_offer(offer_id: int, session: SessionDep) -> Stream:
    offer = service.get_stream_offer(session, offer_id)
    service.remove_offer(offer)
    session.commit()
    return offer.stream


@router.post("/offers/{offer_id}/restore", response_model=StreamOut)
def restore_offer(offer_id: int, session: SessionDep) -> Stream:
    offer = service.get_stream_offer(session, offer_id)
    service.restore_offer(offer)
    session.commit()
    return offer.stream


@router.put("/offers/{offer_id}/pin", response_model=StreamOut)
def pin_offer(offer_id: int, body: PinIn, session: SessionDep) -> Stream:
    offer = service.get_stream_offer(session, offer_id)
    service.pin_offer(offer, body.share)
    session.commit()
    return offer.stream


@router.delete("/offers/{offer_id}/pin", response_model=StreamOut)
def unpin_offer(offer_id: int, session: SessionDep) -> Stream:
    offer = service.get_stream_offer(session, offer_id)
    service.unpin_offer(offer)
    session.commit()
    return offer.stream
