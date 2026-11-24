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


@pytest.mark.parametrize(
    ("call", "method", "path"),
    [
        (lambda c: c.list_campaigns(offset=100, limit=50), "GET", "/campaigns?offset=100&limit=50"),
        (lambda c: c.update_campaign(5, {"name": "x"}), "PUT", "/campaigns/5"),
        (lambda c: c.switch_campaign(5, "disable"), "POST", "/campaigns/5/disable"),
        (lambda c: c.delete_campaign(5), "DELETE", "/campaigns/5"),
        (lambda c: c.get_stream(7), "GET", "/streams/7"),
        (lambda c: c.switch_stream(7, "enable"), "POST", "/streams/7/enable"),
        (lambda c: c.delete_stream(7), "DELETE", "/streams/7"),
    ],
)
def test_routes(call, method, path):
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={})

    call(make_client(handler))

    assert seen[0].method == method
    assert str(seen[0].url) == f"https://keitaro.test/admin_api/v1{path}"
