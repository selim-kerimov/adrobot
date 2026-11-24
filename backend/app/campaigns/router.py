from fastapi import APIRouter, status

from app.campaigns import service
from app.campaigns.schemas import CampaignCreate, CampaignOptions
from app.db import SessionDep
from app.editor.models import Campaign
from app.editor.schemas import CampaignOut
from app.keitaro import KeitaroDep

router = APIRouter(prefix="/api", tags=["campaigns"])


@router.get("/campaign-options", response_model=CampaignOptions)
def campaign_options(keitaro: KeitaroDep) -> CampaignOptions:
    return service.get_options(keitaro)


@router.post("/campaigns", response_model=CampaignOut, status_code=status.HTTP_201_CREATED)
def create_campaign(body: CampaignCreate, session: SessionDep, keitaro: KeitaroDep) -> Campaign:
    campaign = service.create_campaign(session, keitaro, body)
    session.commit()
    return campaign
