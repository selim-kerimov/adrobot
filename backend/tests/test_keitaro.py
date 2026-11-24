import httpx
import pytest

from app.keitaro import KeitaroClient, KeitaroError


def make_client(handler) -> KeitaroClient:
    return KeitaroClient("https://keitaro.test/", "secret", transport=httpx.MockTransport(handler))


def test_sends_api_key_to_admin_api():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=[{"id": 1, "name": "Offer"}])

    offers = make_client(handler).list_offers()

    assert offers == [{"id": 1, "name": "Offer"}]
    assert str(seen[0].url) == "https://keitaro.test/admin_api/v1/offers"
    assert seen[0].headers["Api-Key"] == "secret"


def test_update_stream_sends_json_body():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "PUT"
        assert request.url.path == "/admin_api/v1/streams/7"
        assert request.read() == b'{"offers":[]}'
        return httpx.Response(200, json={"id": 7})

    assert make_client(handler).update_stream(7, {"offers": []}) == {"id": 7}


def test_http_error_keeps_status_and_message():
    client = make_client(lambda request: httpx.Response(404, json={"error": "Not found"}))

    with pytest.raises(KeitaroError, match="404 Not found") as info:
        client.get_campaign(1)
    assert info.value.status_code == 404


def test_validation_error_message_is_kept():
    client = make_client(
        lambda request: httpx.Response(406, json={"error": "offers: offer 9 does not exist"})
    )

    with pytest.raises(KeitaroError, match="406 offers: offer 9 does not exist"):
        client.update_stream(1, {"offers": [{"offer_id": 9, "share": 100}]})


def test_fastapi_style_error_is_understood():
    client = make_client(lambda request: httpx.Response(404, json={"detail": "Not Found"}))

    with pytest.raises(KeitaroError, match="404 Not Found"):
        client.list_campaign_groups()


def test_network_error_is_wrapped():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    with pytest.raises(KeitaroError, match="unreachable"):
        make_client(handler).list_domains()
