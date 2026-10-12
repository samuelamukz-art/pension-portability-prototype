from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

class ContributionIn(BaseModel):
    member_id: str
    institution_id: str
    employer_id: str
    period: str = Field(pattern=r"^\d{4}-\d{2}$")
    amount: float = Field(gt=0)
    currency: str = "USD"
    contribution_type: str = Field(pattern="^(employee|employer|voluntary)$")

class ContributionOut(ContributionIn):
    id: str
    timestamp: datetime

class ConsentIn(BaseModel):
    member_id: str
    institution_id: str
    scope: str = "read:contributions"
    expires_at: Optional[datetime] = None

class TransferIn(BaseModel):
    member_id: str
    from_institution: str
    to_institution: str

class RiskOut(BaseModel):
    fund_id: str
    risk_score: float
    sustainability_score: float
    top_factors: List[dict]
    confidence: float
    generated_at: datetime