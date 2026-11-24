from fastapi import APIRouter

from app.db import SessionDep
from app.editor import service
from app.editor.models import Campaign, Stream
from app.editor.schemas import (
    AddOfferIn,
    CampaignListItem,
    CampaignOut,
    CampaignUpdate,
    PinIn,
    StreamOut,
)
from app.keitaro import Json, KeitaroDep, KeitaroError, Switch

router = APIRouter(prefix="/api", tags=["editor"])


@router.get("/campaigns", response_model=list[CampaignListItem])
def list_campaigns(session: SessionDep, keitaro: KeitaroDep) -> list[Json]:
    campaigns = service.list_campaigns(session, keitaro)
    session.commit()
    return campaigns


@router.get("/campaigns/{campaign_id}", response_model=CampaignOut)
def get_campaign(campaign_id: int, session: SessionDep) -> Campaign:
    return service.get_campaign(session, campaign_id)


@router.post("/campaigns/{campaign_id}/fetch", response_model=CampaignOut)
def fetch_campaign(campaign_id: int, session: SessionDep, keitaro: KeitaroDep) -> Campaign:
    try:
        campaign = service.fetch_campaign(session, keitaro, campaign_id)
    except KeitaroError as error:
        if error.status_code == 404:
            # Deleted in Keitaro: drop our copy too, the error still goes to the client.
            service.forget_campaign(session, campaign_id)
            session.commit()
        raise
    session.commit()
    return campaign


@router.patch("/campaigns/{campaign_id}", response_model=CampaignOut)
def update_campaign(
    campaign_id: int, body: CampaignUpdate, session: SessionDep, keitaro: KeitaroDep
) -> Campaign:
    campaign = service.get_campaign(session, campaign_id)
    service.rename_campaign(keitaro, campaign, body.name)
    session.commit()
    return campaign


@router.delete("/campaigns/{campaign_id}", status_code=204)
def delete_campaign(campaign_id: int, session: SessionDep, keitaro: KeitaroDep) -> None:
    campaign = service.get_campaign(session, campaign_id)
    service.delete_campaign(session, keitaro, campaign)
    session.commit()


@router.post("/streams/{stream_id}/fetch", response_model=StreamOut)
def fetch_stream(stream_id: int, session: SessionDep, keitaro: KeitaroDep) -> Stream:
    stream = service.get_stream(session, stream_id)
    try:
        service.refresh_stream(keitaro, stream)
    except KeitaroError as error:
        if error.status_code == 404:
            stream.campaign.streams.remove(stream)
            session.commit()
        raise
    session.commit()
    return stream


@router.delete("/streams/{stream_id}", status_code=204)
def delete_stream(stream_id: int, session: SessionDep, keitaro: KeitaroDep) -> None:
    stream = service.get_stream(session, stream_id)
    service.delete_stream(keitaro, stream)
    session.commit()


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


# Last on purpose: {switch} would also catch /fetch, /push and /cancel and answer 422.


@router.post("/campaigns/{campaign_id}/{switch}", response_model=CampaignOut)
def switch_campaign(
    campaign_id: int, switch: Switch, session: SessionDep, keitaro: KeitaroDep
) -> Campaign:
    campaign = service.get_campaign(session, campaign_id)
    service.switch_campaign(keitaro, campaign, switch)
    session.commit()
    return campaign


@router.post("/streams/{stream_id}/{switch}", response_model=StreamOut)
def switch_stream(
    stream_id: int, switch: Switch, session: SessionDep, keitaro: KeitaroDep
) -> Stream:
    stream = service.get_stream(session, stream_id)
    service.switch_stream(keitaro, stream, switch)
    session.commit()
    return stream
