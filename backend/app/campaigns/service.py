"""Creates a campaign with two streams: visitors from the chosen countries go to
Google, everyone else goes to the chosen offer.
"""

from sqlalchemy.orm import Session

from app.campaigns.schemas import CampaignCreate, CampaignOptions
from app.editor import service as editor
from app.editor.models import Campaign
from app.keitaro import KeitaroClient, KeitaroError

GEO_REDIRECT_URL = "https://google.com"


def get_options(keitaro: KeitaroClient) -> CampaignOptions:
    return CampaignOptions.model_validate(
        {
            "domains": keitaro.list_domains(),
            "groups": keitaro.list_campaign_groups(),
            "traffic_sources": keitaro.list_traffic_sources(),
        }
    )


def create_campaign(session: Session, keitaro: KeitaroClient, data: CampaignCreate) -> Campaign:
    keitaro.get_offer(data.offer_id)  # fails with 404 before anything is created

    campaign = keitaro.create_campaign(
        {
            "name": data.name,
            "type": "position",
            "domain_id": data.domain_id,
            "group_id": data.group_id,
            "traffic_source_id": data.traffic_source_id,
            "cost_type": "CPC",
            "cost_value": 0,
            "cost_currency": "USD",
            "cost_auto": True,
        }
    )
    try:
        keitaro.create_stream(
            {
                "campaign_id": campaign["id"],
                "name": "Flow 1",
                "type": "regular",
                "position": 1,
                "schema": "redirect",
                "action_type": "http",
                "action_payload": GEO_REDIRECT_URL,
                "filters": [{"name": "country", "mode": "accept", "payload": data.countries}],
            }
        )
        keitaro.create_stream(
            {
                "campaign_id": campaign["id"],
                "name": "Flow 2",
                "type": "regular",
                "position": 2,
                "schema": "landings",
                "offers": [{"offer_id": data.offer_id, "share": 100, "state": "active"}],
            }
        )
    except KeitaroError:
        # Do not leave a half-made campaign in Keitaro.
        keitaro.delete_campaign(campaign["id"])
        raise

    return editor.fetch_campaign(session, keitaro, campaign["id"])
