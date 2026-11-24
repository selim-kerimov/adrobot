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
        "state": "active",
        "has_offers": False,
        "is_draft": False,
        "offers": [],
    }
    assert [o["share"] for o in offers["offers"]] == [50, 50]

    listed = client.get("/api/campaigns").json()
    assert [(c["keitaro_id"], c["synced_at"] is not None) for c in listed] == [(10, True)]
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


def test_list_shows_campaigns_not_loaded_yet(client, keitaro, campaign):
    keitaro.add_campaign(11, [])

    listed = client.get("/api/campaigns").json()

    assert [(c["keitaro_id"], c["synced_at"] is None) for c in listed] == [(11, True), (10, False)]


def test_campaign_deleted_in_keitaro_is_dropped_on_list(client, keitaro, campaign):
    del keitaro.campaigns[10]

    assert client.get("/api/campaigns").json() == []
    assert client.get("/api/campaigns/10").status_code == 404


def test_campaign_deleted_in_keitaro_is_dropped_on_fetch(client, keitaro, campaign):
    del keitaro.campaigns[10]

    assert client.post("/api/campaigns/10/fetch").status_code == 404
    assert client.get("/api/campaigns/10").status_code == 404


def test_list_reads_every_page(client, keitaro):
    for campaign_id in range(1, 251):
        keitaro.add_campaign(campaign_id, [])

    assert len(client.get("/api/campaigns").json()) == 250


def test_rename_campaign(client, keitaro, campaign):
    response = client.patch("/api/campaigns/10", json={"name": "test_kerimov_renamed"})

    assert response.json()["name"] == "test_kerimov_renamed"
    assert keitaro.campaigns[10]["name"] == "test_kerimov_renamed"
    assert client.patch("/api/campaigns/10", json={"name": "  "}).status_code == 422


def test_switch_campaign_and_stream(client, keitaro, campaign):
    stream = campaign["streams"][1]

    assert client.post("/api/campaigns/10/disable").json()["state"] == "disabled"
    assert client.post(f"/api/streams/{stream['id']}/disable").json()["state"] == "disabled"
    assert keitaro.campaigns[10]["state"] == keitaro.streams[2]["state"] == "disabled"

    assert client.post("/api/campaigns/10/enable").json()["state"] == "active"
    assert client.post("/api/campaigns/10/pause").status_code == 422


def test_routes_next_to_switch_still_work(client, campaign):
    stream = campaign["streams"][1]

    assert client.post(f"/api/streams/{stream['id']}/push").status_code == 200
    assert client.post("/api/campaigns/10/fetch").status_code == 200


def test_delete_stream(client, keitaro, campaign):
    redirect = campaign["streams"][0]

    assert client.delete(f"/api/streams/{redirect['id']}").status_code == 204

    assert 1 not in keitaro.streams
    assert [s["keitaro_id"] for s in client.get("/api/campaigns/10").json()["streams"]] == [2]


def test_delete_campaign(client, keitaro, campaign):
    assert client.delete("/api/campaigns/10").status_code == 204

    assert keitaro.campaigns == {}
    assert client.get("/api/campaigns/10").status_code == 404


def test_delete_already_deleted_in_keitaro(client, keitaro, campaign):
    del keitaro.campaigns[10]

    assert client.delete("/api/campaigns/10").status_code == 204


def test_fetch_stream(client, keitaro, campaign):
    stream = campaign["streams"][1]
    keitaro.streams[2]["offers"] = [{"offer_id": 3, "share": 100}]
    keitaro.streams[2]["state"] = "disabled"

    stream = client.post(f"/api/streams/{stream['id']}/fetch").json()

    assert stream["state"] == "disabled"
    assert [(o["offer_id"], o["state"]) for o in stream["offers"]] == [
        (1, "removed"),
        (2, "removed"),
        (3, "active"),
    ]


def test_fetch_stream_deleted_in_keitaro(client, keitaro, campaign):
    stream = campaign["streams"][1]
    del keitaro.streams[2]

    assert client.post(f"/api/streams/{stream['id']}/fetch").status_code == 404
    assert len(client.get("/api/campaigns/10").json()["streams"]) == 1
