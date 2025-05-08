from supabase import create_client, Client as SupabaseClient
from pymongo import MongoClient
from pymongo.collection import Collection
from app.core.config import settings
from app.schemas import UserCreate, UserResponse, PaymentData, DebtData, HistoryData, MixData
import uuid
from datetime import datetime, timezone
import random
from typing import Optional

# --- Supabase Clients ---
supabase_client_1: SupabaseClient = create_client(settings.SUPABASE_URL_1, settings.SUPABASE_KEY_1)
supabase_client_2: SupabaseClient = create_client(settings.SUPABASE_URL_2, settings.SUPABASE_KEY_2)

# --- MongoDB Clients ---
mongo_client_1 = MongoClient(settings.MONGO_URI_1)
debt_db_mongo = mongo_client_1[settings.MONGO_DB_NAME_1]
debt_collection: Collection = debt_db_mongo["debt_records"]

mongo_client_2 = MongoClient(settings.MONGO_URI_2)
mix_db_mongo = mongo_client_2[settings.MONGO_DB_NAME_2]
mix_collection: Collection = mix_db_mongo["mix_records"]


# --- User CRUD (Supabase 1) ---
def create_user(user: UserCreate) -> Optional[UserResponse]:
    try:
        response = supabase_client_1.table("users").insert({
            "username": user.username,
            "email": user.email
        }).execute()
        if response.data:
            return UserResponse(**response.data[0])
        return None
    except Exception as e:
        print(f"Error creating user: {e}")
        return None

def get_user(user_id: uuid.UUID) -> Optional[UserResponse]:
    try:
        response = supabase_client_1.table("users").select("*").eq("user_id", str(user_id)).execute()
        if response.data:
            return UserResponse(**response.data[0])
        return None
    except Exception as e:
        print(f"Error getting user: {e}")
        return None

# --- Payment Data CRUD (Supabase 1) ---
def create_or_update_payment_data(data: PaymentData) -> Optional[PaymentData]:
    try:
        # Upsert based on user_id
        record = {
            "user_id": str(data.user_id),
            "on_time_payments": data.on_time_payments,
            "total_payments": data.total_payments,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
        response = supabase_client_1.table("payments_data").upsert(record, on_conflict="user_id").execute()
        if response.data:
            return PaymentData(**response.data[0])
        return None
    except Exception as e:
        print(f"Error creating/updating payment data: {e}")
        return None

def get_payment_data(user_id: uuid.UUID) -> Optional[PaymentData]:
    try:
        response = supabase_client_1.table("payments_data").select("*").eq("user_id", str(user_id)).execute()
        if response.data:
            return PaymentData(**response.data[0])
        return None
    except Exception as e:
        print(f"Error getting payment data: {e}")
        return None

# --- History Data CRUD (Supabase 2) ---
def create_or_update_history_data(data: HistoryData) -> Optional[HistoryData]:
    try:
        record = {
            "user_id": str(data.user_id),
            "account_age_years": data.account_age_years,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
        response = supabase_client_2.table("history_data").upsert(record, on_conflict="user_id").execute()
        if response.data:
            # Supabase returns account_age_years correctly, user_id as string
            res_data = response.data[0]
            return HistoryData(user_id=uuid.UUID(res_data['user_id']), account_age_years=res_data['account_age_years'])
        return None
    except Exception as e:
        print(f"Error creating/updating history data: {e}")
        return None

def get_history_data(user_id: uuid.UUID) -> Optional[HistoryData]:
    try:
        response = supabase_client_2.table("history_data").select("*").eq("user_id", str(user_id)).execute()
        if response.data:
            res_data = response.data[0]
            return HistoryData(user_id=uuid.UUID(res_data['user_id']), account_age_years=res_data['account_age_years'])
        return None
    except Exception as e:
        print(f"Error getting history data: {e}")
        return None

# --- Debt Data CRUD (MongoDB Atlas 1) ---
def create_or_update_debt_data(data: DebtData) -> Optional[DebtData]:
    try:
        debt_collection.update_one(
            {"user_id": str(data.user_id)},
            {"$set": {
                "used_credit": data.used_credit,
                "credit_limit": data.credit_limit,
                "last_updated": datetime.now(timezone.utc)
            }},
            upsert=True
        )
        return data # Return input data on success
    except Exception as e:
        print(f"Error creating/updating debt data: {e}")
        return None

def get_debt_data(user_id: uuid.UUID) -> Optional[DebtData]:
    try:
        doc = debt_collection.find_one({"user_id": str(user_id)})
        if doc:
            return DebtData(user_id=uuid.UUID(doc["user_id"]), used_credit=doc["used_credit"], credit_limit=doc["credit_limit"])
        return None
    except Exception as e:
        print(f"Error getting debt data: {e}")
        return None

# --- Mix Data CRUD (MongoDB Atlas 2) ---
def create_or_update_mix_data(data: MixData) -> Optional[MixData]:
    try:
        mix_collection.update_one(
            {"user_id": str(data.user_id)},
            {"$set": {
                "credit_types_used": data.credit_types_used,
                "last_updated": datetime.now(timezone.utc)
            }},
            upsert=True
        )
        return data # Return input data on success
    except Exception as e:
        print(f"Error creating/updating mix data: {e}")
        return None

def get_mix_data(user_id: uuid.UUID) -> Optional[MixData]:
    try:
        doc = mix_collection.find_one({"user_id": str(user_id)})
        if doc:
            return MixData(user_id=uuid.UUID(doc["user_id"]), credit_types_used=doc["credit_types_used"])
        return None
    except Exception as e:
        print(f"Error getting mix data: {e}")
        return None


# --- Data Generation ---
def generate_and_store_user_data(user_id: uuid.UUID) -> dict:
    # Payment Data
    total_payments = random.randint(5, 50)
    on_time_payments = random.randint(int(total_payments * 0.7), total_payments) # At least 70% on time
    payment = PaymentData(user_id=user_id, on_time_payments=on_time_payments, total_payments=total_payments)
    create_or_update_payment_data(payment)

    # Debt Data
    credit_limit = random.choice([5000, 10000, 15000, 20000])
    used_credit = random.randint(int(credit_limit * 0.1), int(credit_limit * 0.9)) # Use between 10% and 90%
    debt = DebtData(user_id=user_id, used_credit=used_credit, credit_limit=credit_limit)
    create_or_update_debt_data(debt)

    # History Data
    account_age = random.randint(1, settings.MAX_POSSIBLE_AGE_YEARS)
    history = HistoryData(user_id=user_id, account_age_years=account_age)
    create_or_update_history_data(history)

    # Mix Data
    types_used = random.randint(1, settings.TOTAL_SYSTEM_CREDIT_TYPES)
    mix = MixData(user_id=user_id, credit_types_used=types_used)
    create_or_update_mix_data(mix)
    
    return {
        "payment_info": payment,
        "debt_info": debt,
        "history_info": history,
        "mix_info": mix
    }