from http.client import HTTPException
from supabase import ClientOptions, create_client, Client as SupabaseClient
from pymongo import MongoClient
from pymongo.collection import Collection
from app.core.config import settings
from app.schemas import ( 
    UserCreate, UserResponse,
    PaymentTransactionCreate, PaymentTransactionResponse, DerivedPaymentHistory, # New/Modified
    DebtData, HistoryData, MixData, AllUserDataResponse
)
import uuid
from datetime import date, datetime, timedelta, timezone
import random
from typing import List, Optional

import psycopg2 
from psycopg2.extras import RealDictCursor 


payments_db_client: SupabaseClient = create_client( 
    settings.SUPABASE_URL_1,
    settings.SUPABASE_KEY_1
)
history_db_client: SupabaseClient = create_client( 
    settings.SUPABASE_URL_2,
    settings.SUPABASE_KEY_2
)

mongo_client_1 = MongoClient(settings.MONGO_URI_1)
debt_db_mongo = mongo_client_1[settings.MONGO_DB_NAME_1]
debt_collection: Collection = debt_db_mongo["debt_records"]

mongo_client_2 = MongoClient(settings.MONGO_URI_2)
mix_db_mongo = mongo_client_2[settings.MONGO_DB_NAME_2]
mix_collection: Collection = mix_db_mongo["mix_records"]



def get_neon_db_connection():
    conn = psycopg2.connect(settings.NEON_DB_URI)
    return conn


def create_user(user: UserCreate) -> Optional[UserResponse]:
    conn = None
    try:
        conn = get_neon_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO users (username, email) VALUES (%s, %s) RETURNING *;",
                (user.username, user.email)
            )
            new_user_data = cur.fetchone()
            conn.commit()
            if new_user_data:
                return UserResponse(**new_user_data)
            print("CRITICAL: User insert returned data but fetchone() was None.")
            raise HTTPException(status_code=500, detail="Failed to retrieve user after creation.") # Use status_code for consistency here
    except psycopg2.Error as e:
        if conn: conn.rollback()
        print(f"Neon DB Error creating user: pgcode={e.pgcode}, error={e.pgerror}, diag={e.diag}") # More detailed logging
        if hasattr(e, 'pgcode') and e.pgcode == '23505': # Unique violation
            error_detail = "Username or email already exists."
            raise HTTPException(status_code=400, detail=error_detail) 
        # For other database errors
        raise HTTPException(status_code=500, detail=f"A database error occurred (pgcode: {e.pgcode}).") # Correct for new HTTPException instance
    except HTTPException: # Re-raise if it's already an HTTPException
        raise
    except Exception as e:
        if conn: conn.rollback()
        print(f"Unexpected error creating user in Neon DB: {type(e).__name__} - {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred while creating the user.") # Correct for new HTTPException instance
    finally:
        if conn:
            conn.close()
    return None

def get_user(user_id: uuid.UUID) -> Optional[UserResponse]:
    conn = None
    try:
        conn = get_neon_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE user_id = %s;", (str(user_id),)) # Querying Neon
            user_data = cur.fetchone()
            if user_data:
                return UserResponse(**user_data)
        return None # Returns None if no user with that ID is found
    except Exception as e:
        print(f"Error getting user from Neon DB: {e}")
        return None
    finally:
        if conn:
            conn.close()


def add_payment_transaction(transaction: PaymentTransactionCreate) -> Optional[PaymentTransactionResponse]:
    try:
        # Application logic to determine is_on_time before insertion
        is_on_time_calculated = False
        if transaction.payment_date is not None:
            if transaction.payment_date <= transaction.due_date:
                is_on_time_calculated = True
        # If transaction.is_on_time is already provided, use that, otherwise use calculated.
        final_is_on_time = transaction.is_on_time if transaction.is_on_time is not None else is_on_time_calculated

        record = {
            "user_id": str(transaction.user_id),
            "due_date": transaction.due_date.isoformat(),
            "payment_date": transaction.payment_date.isoformat() if transaction.payment_date else None,
            "amount_due": transaction.amount_due,
            "is_on_time": final_is_on_time
        }
        response = payments_db_client.table("payment_transactions").insert(record).execute()
        if response.data:
            return PaymentTransactionResponse(**response.data[0])   
        return None
    except Exception as e:
        print(f"Error adding payment transaction: {e}")
        return None

def get_payment_transactions_for_user(user_id: uuid.UUID) -> List[PaymentTransactionResponse]:
    try:
        response = payments_db_client.table("payment_transactions").select("*").eq("user_id", str(user_id)).order("due_date", desc=False).execute()
        if response.data:
            return [PaymentTransactionResponse(**item) for item in response.data]
        return []
    except Exception as e:
        print(f"Error getting payment transactions for user {user_id}: {e}")
        return []

def get_derived_payment_history(user_id: uuid.UUID) -> Optional[DerivedPaymentHistory]:
    """
    Calculates aggregated payment history from individual transactions.
    """
    transactions = get_payment_transactions_for_user(user_id)
    if not transactions:
        # Return default or indicate no history if that's more appropriate
        return DerivedPaymentHistory(user_id=user_id, on_time_payments=0, total_due_payments=0)

    on_time_count = 0
    # Total due payments: consider only those that have passed their due date or are explicitly marked as needing payment.
    # For simplicity, we'll count all transactions that have a due_date as "due".
    # A more nuanced approach might only count due dates in the past.
    total_due_count = 0

    for t in transactions:
        # Consider a payment as expected if it has a due date.
        total_due_count += 1
        if t.is_on_time: # Relies on the is_on_time flag being correctly set
            on_time_count += 1
    


    return DerivedPaymentHistory(
        user_id=user_id,
        on_time_payments=on_time_count,
        total_due_payments=total_due_count
    )

def create_or_update_history_data(data: HistoryData) -> Optional[HistoryData]:
    try:
        record = {
            "user_id": str(data.user_id),
            "account_age_years": data.account_age_years,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
        response = history_db_client.table("history_data").upsert(record, on_conflict="user_id").execute() 
        
        if response.data:
            res_data = response.data[0]
            return HistoryData(user_id=uuid.UUID(res_data['user_id']), account_age_years=res_data['account_age_years'])
        return None
    except Exception as e:
        print(f"Error creating/updating history data: {e}")
        return None

def get_history_data(user_id: uuid.UUID) -> Optional[HistoryData]:
    try:
        response = history_db_client.table("history_data").select("*").eq("user_id", str(user_id)).execute() 
        
        if response.data:
            res_data = response.data[0]
            return HistoryData(user_id=uuid.UUID(res_data['user_id']), account_age_years=res_data['account_age_years'])
        return None
    except Exception as e:
        print(f"Error getting history data: {e}")
        return None


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
        return data 
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
        return data 
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


def generate_and_store_user_data(user_id: uuid.UUID) -> dict: 
# Generate Payment Transactions (Example: 5-15 transactions)
    num_transactions = random.randint(5, 15)
    generated_transactions = []
    current_date = date.today()

    for i in range(num_transactions):
        # Make due dates spread out over the last year
        days_past_due = random.randint(0, 365)
        due_dt = current_date - timedelta(days=days_past_due)
        amount_due_val = round(random.uniform(50.0, 500.0), 2)
        paid = random.choice([True, True, True, False]) # Higher chance of being paid
        payment_dt = None
        is_on_time_val = False


        if paid:
            # If paid, was it on time?
            paid_on_time_chance = random.choice([True, True, True, True, False]) # Higher chance of on-time
            if paid_on_time_chance:
                payment_dt = due_dt - timedelta(days=random.randint(0, 5)) # Paid on or before due date
                is_on_time_val = True
            else:
                payment_dt = due_dt + timedelta(days=random.randint(1, 30)) # Paid late
                is_on_time_val = False
        else: # Not paid
            is_on_time_val = False # Definitely not on time if not paid and due date passed or is today

        # Ensure payment_date is not in the future if due_date is in the past/present
        if payment_dt and payment_dt > current_date:
            payment_dt = None # If calculated payment date is future, assume not paid yet for past dues
            is_on_time_val = False
            if due_dt <= current_date: # If it was due and calculated future payment, mark as not paid
                 pass # is_on_time_val remains False
            else: # Due date is future, so no payment yet is normal
                 is_on_time_val = None # Undetermined until payment or due date passes

        transaction_create = PaymentTransactionCreate(
            user_id=user_id,
            due_date=due_dt,
            payment_date=payment_dt,
            amount_due=amount_due_val,
            is_on_time=is_on_time_val
        )
        added_transaction = add_payment_transaction(transaction_create)
        if added_transaction:
            generated_transactions.append(added_transaction)

    # Fetch derived payment history after generating transactions
    derived_pay_history = get_derived_payment_history(user_id)

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
        "generated_payment_transactions_count": len(generated_transactions),
        "derived_payment_history": derived_pay_history, # This is what score calculator will use
        "debt_info": debt,
        "history_info": history,
        "mix_info": mix
    }