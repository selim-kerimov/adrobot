import pytest

from app.editor import service
from app.editor.models import OfferState
from app.editor.weights import WeightError


def offer(offer_id, share):
    return {"offer_id": offer_id, "share": share, "state": "active"}


@pytest.fixture
def campaign(session, keitaro):
    keitaro.add_campaign(
        10,
        [
            {"id": 1, "name": "Flow 1", "position": 1, "schema": "redirect"},
            {
                "id": 2,
                "name": "Flow 2",
                "position": 2,
                "offers": [offer(1, 34), offer(2, 33), offer(3, 33)],
            },
        ],
    )
    return service.fetch_campaign(session, keitaro, 10)


def offers_stream(campaign):
    return campaign.streams[1]


def shares(stream):
    return {offer.offer_id: offer.share for offer in stream.offers}


def by_offer_id(stream, offer_id):
    return next(offer for offer in stream.offers if offer.offer_id == offer_id)


def test_fetch_keeps_stream_without_offers_by_name(campaign):
    redirect, offers = campaign.streams
    assert (redirect.name, redirect.has_offers, redirect.offers) == ("Flow 1", False, [])
    assert offers.has_offers
    assert shares(offers) == {1: 34, 2: 33, 3: 33}
    assert by_offer_id(offers, 1).offer_name == "Offer 1"
    assert not offers.is_draft


def test_add_offer_rebalances_and_makes_a_draft(keitaro, campaign):
    stream = offers_stream(campaign)

    service.add_offer(keitaro, stream, 4)

    assert shares(stream) == {1: 25, 2: 25, 3: 25, 4: 25}
    assert stream.is_draft
    assert keitaro.shares(2) == {1: 34, 2: 33, 3: 33}


def test_push_sends_shares_and_clears_the_draft(keitaro, campaign):
    stream = offers_stream(campaign)
    service.add_offer(keitaro, stream, 4)

    service.push_stream(keitaro, stream)

    assert keitaro.shares(2) == {1: 25, 2: 25, 3: 25, 4: 25}
    assert not stream.is_draft


def test_cancel_drops_added_offers(keitaro, campaign):
    stream = offers_stream(campaign)
    service.add_offer(keitaro, stream, 4)

    service.cancel_stream(stream)

    assert shares(stream) == {1: 34, 2: 33, 3: 33}
    assert not stream.is_draft


def test_removed_offer_is_archived_after_push(keitaro, campaign):
    stream = offers_stream(campaign)

    service.remove_offer(by_offer_id(stream, 3))
    assert shares(stream) == {1: 50, 2: 50, 3: 0}
    assert stream.is_draft

    service.push_stream(keitaro, stream)
    assert keitaro.shares(2) == {1: 50, 2: 50}
    assert by_offer_id(stream, 3).state == OfferState.REMOVED
    assert not stream.is_draft


def test_bring_back_after_push(keitaro, campaign):
    stream = offers_stream(campaign)
    service.remove_offer(by_offer_id(stream, 3))
    service.push_stream(keitaro, stream)

    service.restore_offer(by_offer_id(stream, 3))
    assert stream.is_draft
    service.push_stream(keitaro, stream)

    assert keitaro.shares(2) == {1: 34, 2: 33, 3: 33}


def test_cancel_restores_removed_offer(campaign):
    stream = offers_stream(campaign)
    service.remove_offer(by_offer_id(stream, 3))

    service.cancel_stream(stream)

    assert by_offer_id(stream, 3).state == OfferState.ACTIVE
    assert shares(stream) == {1: 34, 2: 33, 3: 33}


def test_offer_deleted_in_keitaro_becomes_removed(session, keitaro, campaign):
    keitaro.streams[2]["offers"] = [offer(1, 100)]

    campaign = service.fetch_campaign(session, keitaro, 10)

    stream = offers_stream(campaign)
    assert [o.state for o in stream.offers] == [
        OfferState.ACTIVE,
        OfferState.REMOVED,
        OfferState.REMOVED,
    ]
    assert shares(stream) == {1: 100, 2: 0, 3: 0}
    assert not stream.is_draft

    service.restore_offer(by_offer_id(stream, 2))
    assert shares(stream) == {1: 50, 2: 50, 3: 0}


def test_fetch_drops_unpushed_drafts(session, keitaro, campaign):
    stream = offers_stream(campaign)
    service.add_offer(keitaro, stream, 4)

    campaign = service.fetch_campaign(session, keitaro, 10)

    assert shares(offers_stream(campaign)) == {1: 34, 2: 33, 3: 33}


def test_pinned_share_survives_changes(keitaro, campaign):
    stream = offers_stream(campaign)
    service.pin_offer(by_offer_id(stream, 1), 25)
    assert shares(stream) == {1: 25, 2: 38, 3: 37}

    service.remove_offer(by_offer_id(stream, 3))
    assert shares(stream) == {1: 25, 2: 75, 3: 0}

    service.add_offer(keitaro, stream, 4)
    assert shares(stream) == {1: 25, 2: 38, 3: 0, 4: 37}


def test_cannot_remove_the_last_unpinned_offer(campaign):
    stream = offers_stream(campaign)
    service.pin_offer(by_offer_id(stream, 1), 25)
    service.remove_offer(by_offer_id(stream, 3))

    with pytest.raises(WeightError):
        service.remove_offer(by_offer_id(stream, 2))


def test_adding_a_removed_offer_brings_it_back(keitaro, campaign):
    stream = offers_stream(campaign)
    service.remove_offer(by_offer_id(stream, 3))

    service.add_offer(keitaro, stream, 3)

    assert by_offer_id(stream, 3).state == OfferState.ACTIVE
    assert len(stream.offers) == 3


def test_errors(session, keitaro, campaign):
    redirect, stream = campaign.streams
    with pytest.raises(service.EditorError, match="already in the stream"):
        service.add_offer(keitaro, stream, 1)
    with pytest.raises(service.EditorError, match="does not send traffic"):
        service.add_offer(keitaro, redirect, 1)
    with pytest.raises(service.EditorError, match="between 0 and 100"):
        service.pin_offer(by_offer_id(stream, 1), 120)
    with pytest.raises(service.NotFoundError):
        service.get_campaign(session, 999)
