from fastapi import FastAPI, HTTPException
import uuid
from app.services import score_calculator
from app.core.config import settings
from fastapi import FastAPI, HTTPException
from app import crud, schemas


app = FastAPI(title="Credit Score API")

@app.post("/users/", response_model=schemas.UserResponse, status_code=201)
def create_new_user(user: schemas.UserCreate):
    # crud.create_user now handles Neon and can raise HTTPException for duplicates
    try:
        db_user = crud.create_user(user)
        if not db_user: # Should ideally not happen if crud.create_user raises on failure
            raise HTTPException(status_code=500, detail="Failed to create user.")
        return db_user
    except Exception as e: # Catch any other unexpected errors
        print(f"Unexpected error in create_new_user endpoint: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

@app.post("/users/{user_id}/generate-data/", status_code=201)
def generate_data_for_user(user_id: uuid.UUID):
    user = crud.get_user(user_id) # This checks Neon DB
    if not user:
        # This is where the 404 "User not found..." is raised
        raise HTTPException(status_code=404, detail="User not found in User Database (Neon).")
    
    generation_summary = crud.generate_and_store_user_data(user_id)
    return {
        "message": "Credit data generation process completed for user.",
        "user_id": user_id,
        "generation_summary": generation_summary # Contains counts and derived history
    }

@app.get("/iscore/{user_id}", response_model=schemas.ScoreCalculationResponse)
def get_user_iscore(user_id: uuid.UUID):
    user_info = crud.get_user(user_id) # From Neon
    if not user_info:
        raise HTTPException(status_code=404, detail="User not found")

    # Fetch derived payment history instead of a single payment_info record
    derived_payment_history = crud.get_derived_payment_history(user_id) # From Supabase 1 (transactions table)
    debt_info = crud.get_debt_data(user_id)                             # From MongoDB 1
    history_info = crud.get_history_data(user_id)                       # From Supabase 2
    mix_info = crud.get_mix_data(user_id)                               # From MongoDB 2

    # Check if all necessary data components are present for scoring
    # Derived payment history might be "empty" (0/0) for new users, which is valid for scoring.
    # So, we check if the objects themselves are None where critical.
    if not all([debt_info, history_info, mix_info, derived_payment_history is not None]):
        missing = []
        if derived_payment_history is None: missing.append("payment history processing")
        if not debt_info: missing.append("debt")
        if not history_info: missing.append("history")
        if not mix_info: missing.append("mix")
        raise HTTPException(status_code=404, detail=f"User found, but missing critical data components: {', '.join(missing)}. Please ensure data generation is complete.")

    all_user_data = schemas.AllUserDataResponse(
        user_info=user_info,
        derived_payment_history=derived_payment_history, # Pass the derived history
        debt_info=debt_info,
        history_info=history_info,
        mix_info=mix_info
    )
    
    score_results = score_calculator.calculate_final_iscore(all_user_data)
    
    return schemas.ScoreCalculationResponse(
        user_id=user_id,
        components=score_results["components"],
        final_unscaled_score=score_results["final_unscaled_score"],
        iscore=score_results["iscore"],
        raw_data_fetched=all_user_data # This now contains derived_payment_history
    )

@app.get("/")
def read_root():
    return {"message": "Credit Score API is running!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.FASTAPI_HOST, port=settings.FASTAPI_PORT)