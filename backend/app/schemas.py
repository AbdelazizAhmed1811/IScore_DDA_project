from datetime import date, datetime
from pydantic import BaseModel, EmailStr, UUID4
from typing import Optional, Any

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


class PaymentTransactionCreate(BaseModel):
    user_id: UUID4
    loan_or_account_id: Optional[str] = None
    due_date: date
    payment_date: Optional[date] = None
    amount_due: float
    is_on_time: Optional[bool] = None # Application can set this when creating
    transaction_type: Optional[str] = None

class PaymentTransactionResponse(PaymentTransactionCreate):
    transaction_id: int
    created_at: datetime
    last_updated: datetime

    class Config:
        from_attributes = True # orm_mode = True

# This schema is no longer directly stored but represents derived data for scoring
class DerivedPaymentHistory(BaseModel):
    user_id: UUID4
    on_time_payments: int
    total_due_payments: int # Total payments that had a due date (and were expected)


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
    derived_payment_history: Optional[DerivedPaymentHistory] = None
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

    