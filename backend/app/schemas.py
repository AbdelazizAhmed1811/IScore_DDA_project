from pydantic import BaseModel, EmailStr, UUID4
from typing import Optional, Dict, Any

class UserCreate(BaseModel):
    username: str
    email: Optional[EmailStr] = None

class UserResponse(BaseModel):
    user_id: UUID4
    username: str
    email: Optional[EmailStr] = None
    created_at: Any # datetime

    class Config:
        from_attributes = True


class PaymentData(BaseModel):
    user_id: UUID4
    on_time_payments: int
    total_payments: int

class DebtData(BaseModel):
    user_id: UUID4 # Store as string in Mongo if easier, convert later
    used_credit: float
    credit_limit: float

class HistoryData(BaseModel):
    user_id: UUID4
    account_age_years: int

class MixData(BaseModel):
    user_id: UUID4
    credit_types_used: int

class AllUserDataResponse(BaseModel):
    user_info: Optional[UserResponse] = None
    payment_info: Optional[PaymentData] = None
    debt_info: Optional[DebtData] = None
    history_info: Optional[HistoryData] = None
    mix_info: Optional[MixData] = None

class ScoreComponent(BaseModel):
    name: str
    value: float
    weight: float
    raw_score: float # score before weighting (0-100)
    weighted_score: float

class ScoreCalculationResponse(BaseModel):
    user_id: UUID4
    components: list[ScoreComponent]
    final_unscaled_score: float # sum of weighted scores (0-100)
    iscore: float # scaled score (e.g., 300-850)
    raw_data_fetched: AllUserDataResponse