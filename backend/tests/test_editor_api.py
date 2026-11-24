import pytest


@pytest.fixture
def campaign(client, keitaro):
    keitaro.add_campaign(
        10,
        [
            {"id": 1, "name": "Flow 1", "position": 1},
            {
                "id": 2,
                "name": "Flow 2",
                "position": 2,
                "offers": [{"offer_id": 1, "share": 50}, {"offer_id": 2, "share": 50}],
            },
        ],
    )
    response = client.post("/api/campaigns/10/fetch")
    assert response.status_code == 200
    return response.json()


def offer_ids(stream):
    return {offer["offer_id"]: offer["id"] for offer in stream["offers"]}


def test_fetch_returns_streams(client, campaign):
    assert campaign["name"] == "campaign 10"
    redirect, offers = campaign["streams"]
    assert redirect == {
        "id": redirect["id"],
        "keitaro_id": 1,
        "name": "Flow 1",
        "position": 1,
        "has_offers": False,
        "is_draft": False,
        "offers": [],
    }
    assert [o["share"] for o in offers["offers"]] == [50, 50]

    assert client.get("/api/campaigns").json()[0]["keitaro_id"] == 10
    # SQLite drops the timezone of synced_at on reload, so compare the rest.
    loaded = client.get("/api/campaigns/10").json()
    assert loaded["streams"] == campaign["streams"]


def test_edit_and_push(client, keitaro, campaign):
    stream = campaign["streams"][1]

    stream = client.post(f"/api/streams/{stream['id']}/offers", json={"offer_id": 3}).json()
    assert [o["share"] for o in stream["offers"]] == [34, 33, 33]
    assert stream["is_draft"]

    pinned = offer_ids(stream)[1]
    stream = client.put(f"/api/offers/{pinned}/pin", json={"share": 60}).json()
    assert [o["share"] for o in stream["offers"]] == [60, 20, 20]

    stream = client.post(f"/api/offers/{offer_ids(stream)[2]}/remove").json()
    assert [o["share"] for o in stream["offers"]] == [60, 0, 40]

    stream = client.post(f"/api/streams/{stream['id']}/push").json()
    assert not stream["is_draft"]
    assert keitaro.shares(2) == {1: 60, 3: 40}


def test_cancel(client, campaign):
    stream = campaign["streams"][1]
    client.post(f"/api/streams/{stream['id']}/offers", json={"offer_id": 3})

    stream = client.post(f"/api/streams/{stream['id']}/cancel").json()

    assert [o["share"] for o in stream["offers"]] == [50, 50]
    assert not stream["is_draft"]


def test_errors(client, campaign):
    redirect, stream = campaign["streams"]
    offers = offer_ids(stream)

    assert client.get("/api/campaigns/99").status_code == 404
    assert client.post("/api/campaigns/99/fetch").status_code == 404
    assert client.post("/api/streams/999/push").status_code == 404

    response = client.post(f"/api/streams/{stream['id']}/offers", json={"offer_id": 1})
    assert response.status_code == 409
    assert "already in the stream" in response.json()["detail"]

    response = client.put(f"/api/offers/{offers[1]}/pin", json={"share": 101})
    assert response.status_code == 422

    client.put(f"/api/offers/{offers[1]}/pin", json={"share": 30})
    response = client.post(f"/api/offers/{offers[2]}/remove")
    assert response.status_code == 422
    assert "unpin" in response.json()["detail"]


def test_failed_change_is_not_saved(client, campaign):
    stream = campaign["streams"][1]
    offers = offer_ids(stream)
    client.put(f"/api/offers/{offers[1]}/pin", json={"share": 30})

    client.post(f"/api/offers/{offers[2]}/remove")

    offers = client.get("/api/campaigns/10").json()["streams"][1]["offers"]
    assert [(o["state"], o["share"]) for o in offers] == [("active", 30), ("active", 70)]
