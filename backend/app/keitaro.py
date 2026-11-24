"""Thin client for the Keitaro Admin API (v1).

Only the calls the app needs. Responses are returned as plain dicts: Keitaro objects
have many fields and we read just a few of them.
"""

from collections.abc import Iterator
from typing import Any

import httpx

from app.config import settings

Json = dict[str, Any]


class KeitaroError(Exception):
    """Keitaro answered with an error or could not be reached."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class KeitaroClient:
    def __init__(self, base_url: str, api_key: str, transport: httpx.BaseTransport | None = None):
        self._http = httpx.Client(
            base_url=f"{base_url.rstrip('/')}/admin_api/v1",
            headers={"Api-Key": api_key},
            timeout=30,
            transport=transport,
        )

    def close(self) -> None:
        self._http.close()

    # Lookups

    def list_offers(self) -> list[Json]:
        return self._request("GET", "/offers")

    def list_domains(self) -> list[Json]:
        return self._request("GET", "/domains")

    def list_campaign_groups(self) -> list[Json]:
        return self._request("GET", "/groups", params={"type": "campaigns"})

    def list_traffic_sources(self) -> list[Json]:
        return self._request("GET", "/traffic_sources")

    # Campaigns and streams

    def get_campaign(self, campaign_id: int) -> Json:
        return self._request("GET", f"/campaigns/{campaign_id}")

    def create_campaign(self, data: Json) -> Json:
        return self._request("POST", "/campaigns", json=data)

    def list_streams(self, campaign_id: int) -> list[Json]:
        return self._request("GET", f"/campaigns/{campaign_id}/streams")

    def create_stream(self, data: Json) -> Json:
        return self._request("POST", "/streams", json=data)

    def update_stream(self, stream_id: int, data: Json) -> Json:
        return self._request("PUT", f"/streams/{stream_id}", json=data)

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = self._http.request(method, path, **kwargs)
        except httpx.HTTPError as error:
            raise KeitaroError(f"Keitaro is unreachable: {error}") from error

        if response.is_error:
            raise KeitaroError(
                f"Keitaro {method} {path} failed: {response.status_code} {_error_text(response)}",
                status_code=response.status_code,
            )
        return response.json()


def _error_text(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text[:200]
    if isinstance(body, dict) and "error" in body:
        return str(body["error"])
    return str(body)[:200]


def get_keitaro() -> Iterator[KeitaroClient]:
    """FastAPI dependency."""
    client = KeitaroClient(settings.keitaro_url, settings.keitaro_api_key)
    try:
        yield client
    finally:
        client.close()
