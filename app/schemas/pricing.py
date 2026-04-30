# app/schemas/pricing.py

from typing import List, Optional

from pydantic import BaseModel


class PlanLimitsResponse(BaseModel):
    learning_requests_per_hour: int
    evaluation_sessions_per_day: int
    evaluations_per_session: Optional[int]
    allow_evaluation_overage: bool


class PricingPlanResponse(BaseModel):
    tier: str
    name: str
    price_label: str
    description: str
    badge: str
    features: List[str]
    cta: str
    note: str
    limits: PlanLimitsResponse
    is_popular: bool


class PricingPlansResponse(BaseModel):
    plans: List[PricingPlanResponse]
