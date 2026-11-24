"""Thin client for the Keitaro Admin API (v1).

Covers every route of the test instance. Responses are returned as plain dicts: Keitaro objects
have many fields and we read just a few of them.

Checked against the test instance:
- PUT /streams/{id} with "offers" replaces the whole offer list of the stream.
- Keitaro does not check that offer shares add up to 100: that is on us.
- Errors come as {"error": "..."} (406 for validation, 404 for missing objects);
  unknown routes answer FastAPI-style {"detail": "..."}.
- Deleting a campaign deletes its streams too.
- POST /campaigns/{id}/enable|disable and /streams/{id}/enable|disable return the object.
"""

from functools import cache
from typing import Annotated, Any, Literal

import httpx
from fastapi import Depends

from app.config import settings

Json = dict[str, Any]
Switch = Literal["enable", "disable"]


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

    # Lookups

    def list_offers(self) -> list[Json]:
        return self._request("GET", "/offers")

    def get_offer(self, offer_id: int) -> Json:
        return self._request("GET", f"/offers/{offer_id}")

    def list_domains(self) -> list[Json]:
        return self._request("GET", "/domains")

    def list_campaign_groups(self) -> list[Json]:
        return self._request("GET", "/groups", params={"type": "campaigns"})

    def list_traffic_sources(self) -> list[Json]:
        return self._request("GET", "/traffic_sources")

    # Campaigns and streams

    def list_campaigns(self, offset: int = 0, limit: int = 100) -> list[Json]:
        return self._request("GET", "/campaigns", params={"offset": offset, "limit": limit})

    def get_campaign(self, campaign_id: int) -> Json:
        return self._request("GET", f"/campaigns/{campaign_id}")

    def create_campaign(self, data: Json) -> Json:
        return self._request("POST", "/campaigns", json=data)

    def update_campaign(self, campaign_id: int, data: Json) -> Json:
        """Changes only the fields that are sent."""
        return self._request("PUT", f"/campaigns/{campaign_id}", json=data)

    def switch_campaign(self, campaign_id: int, switch: Switch) -> Json:
        return self._request("POST", f"/campaigns/{campaign_id}/{switch}")

    def delete_campaign(self, campaign_id: int) -> Json:
        return self._request("DELETE", f"/campaigns/{campaign_id}")

    def list_streams(self, campaign_id: int) -> list[Json]:
        return self._request("GET", f"/campaigns/{campaign_id}/streams")

    def get_stream(self, stream_id: int) -> Json:
        return self._request("GET", f"/streams/{stream_id}")

    def create_stream(self, data: Json) -> Json:
        return self._request("POST", "/streams", json=data)

    def update_stream(self, stream_id: int, data: Json) -> Json:
        return self._request("PUT", f"/streams/{stream_id}", json=data)

    def switch_stream(self, stream_id: int, switch: Switch) -> Json:
        return self._request("POST", f"/streams/{stream_id}/{switch}")

    def delete_stream(self, stream_id: int) -> Json:
        return self._request("DELETE", f"/streams/{stream_id}")

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
    if isinstance(body, dict):
        for key in ("error", "detail"):
            if key in body:
                return str(body[key])
    return str(body)[:200]


@cache
def get_keitaro() -> KeitaroClient:
    """FastAPI dependency. One client for the whole app keeps connections open, so
    requests after the first one skip the TLS handshake (the test instance needs seconds).
    """
    return KeitaroClient(settings.keitaro_url, settings.keitaro_api_key)


KeitaroDep = Annotated[KeitaroClient, Depends(get_keitaro)]
