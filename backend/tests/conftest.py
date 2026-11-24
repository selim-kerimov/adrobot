import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base, get_session
from app.keitaro import KeitaroError, get_keitaro
from app.main import app


@pytest.fixture
def session():
    # One shared connection: TestClient runs the app in another thread.
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        yield session


class FakeKeitaro:
    """Keeps campaigns and streams in memory and answers like the test instance."""

    def __init__(self):
        self.offers = {id_: {"id": id_, "name": f"Offer {id_}"} for id_ in range(1, 10)}
        self.campaigns: dict[int, dict] = {}
        self.streams: dict[int, dict] = {}
        self.fail_on_stream = False

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

    def list_domains(self):
        return [{"id": 1813, "name": "kt-emulator.test"}]

    def list_campaign_groups(self):
        return [{"id": 10332, "name": "FORTESTS"}]

    def list_traffic_sources(self):
        return [{"id": 836, "name": "FORTESTS"}]

    def create_campaign(self, data):
        campaign_id = max(self.campaigns, default=0) + 1
        self.campaigns[campaign_id] = {"id": campaign_id, "alias": "abc123", **data}
        return self.campaigns[campaign_id]

    def delete_campaign(self, campaign_id):
        self.streams = {k: s for k, s in self.streams.items() if s["campaign_id"] != campaign_id}
        return self.campaigns.pop(campaign_id)

    def create_stream(self, data):
        if self.fail_on_stream:
            raise KeitaroError("offers: offer does not exist", status_code=406)
        stream_id = max(self.streams, default=0) + 1
        self.streams[stream_id] = {"id": stream_id, "offers": [], **data}
        return self.streams[stream_id]

    def update_stream(self, stream_id, data):
        self.streams[stream_id].update(data)
        return self.streams[stream_id]


@pytest.fixture
def keitaro():
    return FakeKeitaro()


@pytest.fixture
def client(session, keitaro):
    def request_session():
        # Like get_session: whatever a failed request did not commit is thrown away.
        try:
            yield session
        finally:
            session.rollback()

    app.dependency_overrides[get_session] = request_session
    app.dependency_overrides[get_keitaro] = lambda: keitaro
    yield TestClient(app)
    app.dependency_overrides.clear()
