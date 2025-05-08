from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import uuid
from app import crud, schemas
from app.services import score_calculator
from app.core.config import settings

app = FastAPI(title="Credit Score API")

@app.post("/users/", response_model=schemas.UserResponse, status_code=201)
def create_new_user(user: schemas.UserCreate):
    db_user = crud.create_user(user)
    if not db_user:
        raise HTTPException(status_code=400, detail="Username or email already exists or DB error.")
    return db_user

@app.post("/users/{user_id}/generate-data/", status_code=201)
def generate_data_for_user(user_id: uuid.UUID):
    user = crud.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    generated_data = crud.generate_and_store_user_data(user_id)
    return {"message": "Data generated successfully for user.", "user_id": user_id, "data": generated_data}


@app.get("/iscore/{user_id}", response_model=schemas.ScoreCalculationResponse)
def get_user_iscore(user_id: uuid.UUID):
    user_info = crud.get_user(user_id)
    if not user_info:
        raise HTTPException(status_code=404, detail="User not found")

    payment_info = crud.get_payment_data(user_id)
    debt_info = crud.get_debt_data(user_id)
    history_info = crud.get_history_data(user_id)
    mix_info = crud.get_mix_data(user_id)

    if not all([payment_info, debt_info, history_info, mix_info]):
        missing = []
        if not payment_info: missing.append("payment")
        if not debt_info: missing.append("debt")
        if not history_info: missing.append("history")
        if not mix_info: missing.append("mix")
        raise HTTPException(status_code=404, detail=f"Missing data for factors: {', '.join(missing)}. Please generate data first.")

    all_user_data = schemas.AllUserDataResponse(
        user_info=user_info,
        payment_info=payment_info,
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
        raw_data_fetched=all_user_data
    )

@app.get("/")
def read_root():
    return {"message": "Credit Score API is running!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.FASTAPI_HOST, port=settings.FASTAPI_PORT)