import pytest

from app import offers


def create(client, **fields):
    body = {
        "name": "test_kerimov_campaign1",
        "countries": ["au", "MX"],
        "offer_id": 3,
        "domain_id": 1813,
        "group_id": 10332,
        "traffic_source_id": 836,
    } | fields
    return client.post("/api/campaigns", json=body)


def test_creates_campaign_with_geo_and_offer_streams(client, keitaro):
    response = create(client)

    assert response.status_code == 201
    campaign = response.json()
    assert campaign["name"] == "test_kerimov_campaign1"

    sent = keitaro.campaigns[campaign["keitaro_id"]]
    assert (sent["domain_id"], sent["group_id"], sent["traffic_source_id"]) == (1813, 10332, 836)

    geo, offer = (keitaro.streams[s["keitaro_id"]] for s in campaign["streams"])
    assert geo["filters"] == [{"name": "country", "mode": "accept", "payload": ["AU", "MX"]}]
    assert geo["action_payload"] == "https://google.com"
    assert offer["offers"] == [{"offer_id": 3, "share": 100, "state": "active"}]

    assert campaign["streams"][1]["offers"][0]["share"] == 100
    assert client.get(f"/api/campaigns/{campaign['keitaro_id']}").status_code == 200


def test_options_come_from_keitaro(client):
    assert client.get("/api/campaign-options").json() == {
        "domains": [{"id": 1813, "name": "kt-emulator.test"}],
        "groups": [{"id": 10332, "name": "FORTESTS"}],
        "traffic_sources": [{"id": 836, "name": "FORTESTS"}],
    }


def test_failed_stream_removes_the_campaign(client, keitaro):
    keitaro.fail_on_stream = True

    response = create(client)

    assert response.status_code == 502
    assert keitaro.campaigns == {}
    assert client.get("/api/campaigns").json() == []


def test_unknown_offer_creates_nothing(client, keitaro):
    assert create(client, offer_id=999).status_code == 404
    assert keitaro.campaigns == {}


@pytest.mark.parametrize(
    "fields",
    [{"name": " "}, {"countries": []}, {"countries": ["AUS"]}, {"countries": ["1A"]}],
)
def test_validation(client, fields):
    assert create(client, **fields).status_code == 422


def test_offer_search():
    catalog = [
        {"id": 1, "name": "18001 Detoxin [HAIR-CL]"},
        {"id": 2, "name": "18002 Detoxin [HAIR-MX]"},
        {"id": 3, "name": "3749 Miaflow [BEAUTY-RO]"},
    ]
    assert [o["id"] for o in offers.search_offers(catalog, "detoxin mx", 20)] == [2]
    assert [o["id"] for o in offers.search_offers(catalog, "3749", 20)] == [3]
    assert len(offers.search_offers(catalog, "", 2)) == 2


def test_offers_endpoint(client, monkeypatch):
    monkeypatch.setattr(offers, "_cache", None)

    response = client.get("/api/offers", params={"q": "offer 7"})

    assert response.json() == [{"id": 7, "name": "Offer 7"}]
