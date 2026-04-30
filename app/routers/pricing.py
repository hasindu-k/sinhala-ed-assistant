# app/routers/pricing.py

from fastapi import APIRouter

from app.core.pricing_plans import list_pricing_plans
from app.schemas.pricing import PricingPlansResponse

router = APIRouter()


@router.get("/plans", response_model=PricingPlansResponse)
def get_pricing_plans():
    return {"plans": list_pricing_plans()}
