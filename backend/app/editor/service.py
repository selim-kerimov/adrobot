"""Editor logic: sync with Keitaro, change offers locally, push or cancel.

Functions change the session but do not commit: the caller commits once the whole
operation succeeded, so a failed step leaves nothing half-done in the database.
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.editor.models import Campaign, OfferState, Stream, StreamOffer
from app.editor.weights import Slot, rebalance
from app.keitaro import Json, KeitaroClient


class NotFoundError(LookupError):
    pass


class EditorError(ValueError):
    """The operation makes no sense for the current state (e.g. the offer is already there)."""


def get_campaign(session: Session, campaign_id: int) -> Campaign:
    campaign = session.scalar(select(Campaign).where(Campaign.keitaro_id == campaign_id))
    if campaign is None:
        raise NotFoundError(f"campaign {campaign_id} is not loaded yet, fetch it first")
    return campaign


def get_stream(session: Session, stream_id: int) -> Stream:
    stream = session.get(Stream, stream_id)
    if stream is None:
        raise NotFoundError(f"stream {stream_id} not found")
    return stream


def get_stream_offer(session: Session, stream_offer_id: int) -> StreamOffer:
    offer = session.get(StreamOffer, stream_offer_id)
    if offer is None:
        raise NotFoundError(f"offer {stream_offer_id} not found")
    return offer


def fetch_campaign(session: Session, keitaro: KeitaroClient, campaign_id: int) -> Campaign:
    """Loads the campaign and its streams from Keitaro. Keitaro wins over local drafts."""
    data = keitaro.get_campaign(campaign_id)
    campaign = session.scalar(select(Campaign).where(Campaign.keitaro_id == campaign_id))
    if campaign is None:
        campaign = Campaign(keitaro_id=campaign_id)
        session.add(campaign)
    campaign.name = data["name"]
    campaign.alias = data.get("alias")
    campaign.synced_at = datetime.now(UTC)

    offer_names = {offer["id"]: offer["name"] for offer in keitaro.list_offers()}
    remote_streams = keitaro.list_streams(campaign_id)
    remote_ids = {stream["id"] for stream in remote_streams}

    for stream in list(campaign.streams):
        if stream.keitaro_id not in remote_ids:
            campaign.streams.remove(stream)

    local_streams = {stream.keitaro_id: stream for stream in campaign.streams}
    for remote in remote_streams:
        stream = local_streams.get(remote["id"])
        if stream is None:
            stream = Stream(keitaro_id=remote["id"])
            campaign.streams.append(stream)
        stream.name = remote["name"]
        stream.position = remote["position"]
        _sync_offers(stream, remote["offers"], offer_names)
        stream.has_offers = bool(stream.offers)

    session.flush()
    return campaign


def _sync_offers(stream: Stream, remote_offers: list[Json], offer_names: dict[int, str]) -> None:
    remote = {offer["offer_id"]: offer for offer in remote_offers}

    for offer in list(stream.offers):
        if offer.offer_id in remote:
            share = remote.pop(offer.offer_id)["share"]
            _publish(offer, OfferState.ACTIVE, share)
        elif offer.published_state is None:
            # Added here and never pushed: it is a local draft, Keitaro wins.
            stream.offers.remove(offer)
        else:
            # Deleted in Keitaro: keep it in the archive so it can be brought back.
            offer.pinned = False
            _publish(offer, OfferState.REMOVED, 0)

    for offer_id, data in remote.items():
        name = offer_names.get(offer_id, str(offer_id))
        offer = StreamOffer(offer_id=offer_id, offer_name=name, pinned=False)
        _publish(offer, OfferState.ACTIVE, data["share"])
        stream.offers.append(offer)


def add_offer(keitaro: KeitaroClient, stream: Stream, offer_id: int) -> None:
    _require_offers(stream)
    existing = next((offer for offer in stream.offers if offer.offer_id == offer_id), None)
    if existing is not None:
        if existing.state == OfferState.REMOVED:
            restore_offer(existing)
            return
        raise EditorError(f"offer {offer_id} is already in the stream")

    data = keitaro.get_offer(offer_id)
    # Column defaults apply only on flush, and the rebalance below needs the state now.
    stream.offers.append(
        StreamOffer(
            offer_id=offer_id, offer_name=data["name"], state=OfferState.ACTIVE, pinned=False
        )
    )
    _rebalance(stream)


def remove_offer(offer: StreamOffer) -> None:
    if offer.state == OfferState.REMOVED:
        raise EditorError("offer is already removed")
    offer.state = OfferState.REMOVED
    offer.pinned = False
    _rebalance(offer.stream)


def restore_offer(offer: StreamOffer) -> None:
    if offer.state == OfferState.ACTIVE:
        raise EditorError("offer is not removed")
    offer.state = OfferState.ACTIVE
    _rebalance(offer.stream)


def pin_offer(offer: StreamOffer, share: int | None = None) -> None:
    """Pins the current share, or sets and pins a new one."""
    if offer.state == OfferState.REMOVED:
        raise EditorError("a removed offer cannot be pinned")
    if share is not None:
        if not 0 <= share <= 100:
            raise EditorError("share must be between 0 and 100")
        offer.share = share
    offer.pinned = True
    _rebalance(offer.stream)


def unpin_offer(offer: StreamOffer) -> None:
    offer.pinned = False
    _rebalance(offer.stream)


def push_stream(keitaro: KeitaroClient, stream: Stream) -> None:
    """Sends the active offers to Keitaro. PUT replaces the whole list, so removed ones go away."""
    _require_offers(stream)
    active = [offer for offer in stream.offers if offer.state == OfferState.ACTIVE]
    keitaro.update_stream(
        stream.keitaro_id,
        {
            "offers": [
                {"offer_id": offer.offer_id, "share": offer.share, "state": "active"}
                for offer in active
            ]
        },
    )
    for offer in stream.offers:
        _publish(offer, offer.state, offer.share)


def cancel_stream(stream: Stream) -> None:
    """Drops offers added since the last push and restores the pushed shares and states."""
    for offer in list(stream.offers):
        if offer.published_state is None:
            stream.offers.remove(offer)
        else:
            offer.state = offer.published_state
            offer.share = offer.published_share or 0


def _publish(offer: StreamOffer, state: OfferState, share: int) -> None:
    offer.state = offer.published_state = state
    offer.share = offer.published_share = share


def _rebalance(stream: Stream) -> None:
    slots = [
        Slot(offer.share, pinned=offer.pinned, active=offer.state == OfferState.ACTIVE)
        for offer in stream.offers
    ]
    for offer, share in zip(stream.offers, rebalance(slots), strict=True):
        offer.share = share


def _require_offers(stream: Stream) -> None:
    if not stream.has_offers:
        raise EditorError("this stream does not send traffic to offers")
