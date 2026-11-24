"""Offer search for autocomplete. Keitaro has no search, so the list is cached and filtered here."""

import time
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.keitaro import Json, KeitaroClient, KeitaroDep

CACHE_SECONDS = 300

router = APIRouter(prefix="/api", tags=["offers"])

_cache: tuple[float, list[Json]] | None = None


class OfferOut(BaseModel):
    id: int
    name: str


def list_offers(keitaro: KeitaroClient) -> list[Json]:
    global _cache
    if _cache is None or time.monotonic() - _cache[0] > CACHE_SECONDS:
        _cache = (time.monotonic(), keitaro.list_offers())
    return _cache[1]


def search_offers(offers: list[Json], query: str, limit: int) -> list[Json]:
    words = query.lower().split()
    found = [offer for offer in offers if all(word in offer["name"].lower() for word in words)]
    return found[:limit]


@router.get("/offers", response_model=list[OfferOut])
def find_offers(
    keitaro: KeitaroDep,
    q: str = "",
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[Json]:
    return search_offers(list_offers(keitaro), q, limit)
