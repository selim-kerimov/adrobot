import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.keitaro import KeitaroError


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


class FakeKeitaro:
    """Keeps campaigns and streams in memory and answers like the test instance."""

    def __init__(self):
        self.offers = {id_: {"id": id_, "name": f"Offer {id_}"} for id_ in range(1, 10)}
        self.campaigns: dict[int, dict] = {}
        self.streams: dict[int, dict] = {}

    def add_campaign(self, campaign_id: int, streams: list[dict]) -> None:
        self.campaigns[campaign_id] = {"id": campaign_id, "name": f"campaign {campaign_id}"}
        for stream in streams:
            self.streams[stream["id"]] = {"campaign_id": campaign_id, "offers": [], **stream}

    def shares(self, stream_id: int) -> dict[int, int]:
        return {offer["offer_id"]: offer["share"] for offer in self.streams[stream_id]["offers"]}

    def get_campaign(self, campaign_id):
        if campaign_id not in self.campaigns:
            raise KeitaroError("Campaign not found", status_code=404)
        return self.campaigns[campaign_id]

    def list_streams(self, campaign_id):
        return [s for s in self.streams.values() if s["campaign_id"] == campaign_id]

    def list_offers(self):
        return list(self.offers.values())

    def get_offer(self, offer_id):
        if offer_id not in self.offers:
            raise KeitaroError("Offer not found", status_code=404)
        return self.offers[offer_id]

    def update_stream(self, stream_id, data):
        self.streams[stream_id].update(data)
        return self.streams[stream_id]


@pytest.fixture
def keitaro():
    return FakeKeitaro()
