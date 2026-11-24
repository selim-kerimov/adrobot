from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

CountryCode = Annotated[
    str, StringConstraints(strip_whitespace=True, to_upper=True, pattern=r"^[A-Za-z]{2}$")
]


class CampaignCreate(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    countries: list[CountryCode] = Field(min_length=1)
    offer_id: int
    domain_id: int
    group_id: int
    traffic_source_id: int


class Option(BaseModel):
    id: int
    name: str


class CampaignOptions(BaseModel):
    """What the new campaign form offers to choose from."""

    domains: list[Option]
    groups: list[Option]
    traffic_sources: list[Option]
