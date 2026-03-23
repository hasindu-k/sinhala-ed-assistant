#app/schemas/safety_summary.py
from typing import Dict
from pydantic import BaseModel


class SafetySummaryResponse(BaseModel):
    overall_severity: str
    confidence_score: float
    reliability: str
    message: str
    has_details: bool
    flags: Dict[str, int]
