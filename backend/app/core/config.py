import logging
import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Get the directory of the current file (config.py)
# This will be something like /home/zizo/projects/python_projects/IScore_DDA_project/backend/app/core
current_file_dir = os.path.dirname(__file__)

# Construct the path to the .env file in the project root
# Go up three levels from 'core' to reach the project root
# backend/app/core -> backend/app -> backend -> IScore_DDA_project
project_root_dir = os.path.abspath(os.path.join(current_file_dir, "..", "..", ".."))
dotenv_path = os.path.join(project_root_dir, ".env")

print(f"Attempting to load .env from: {dotenv_path}") # Debug print to verify the path
load_dotenv(dotenv_path=dotenv_path)

# You can add another print here to see if specific variables are loaded
# print(f"MONGO_URI_1 after load_dotenv: {os.getenv('MONGO_URI_1')}")

class Settings(BaseSettings):
    
    NEON_DB_URI: str = os.getenv("NEON_DB_URI", "") # User DB
    
    SUPABASE_URL_1: str = os.getenv("SUPABASE_URL_1", "")
    SUPABASE_KEY_1: str = os.getenv("SUPABASE_KEY_1", "")

    SUPABASE_URL_2: str = os.getenv("SUPABASE_URL_2", "")
    SUPABASE_KEY_2: str = os.getenv("SUPABASE_KEY_2", "")

    MONGO_URI_1: str = os.getenv("MONGO_URI_1", "")
    MONGO_DB_NAME_1: str = os.getenv("MONGO_DB_NAME_1", "debt_db")

    MONGO_URI_2: str = os.getenv("MONGO_URI_2", "")
    MONGO_DB_NAME_2: str = os.getenv("MONGO_DB_NAME_2", "mix_db")

    MAX_POSSIBLE_AGE_YEARS: int = int(os.getenv("MAX_POSSIBLE_AGE_YEARS", 10))
    TOTAL_SYSTEM_CREDIT_TYPES: int = int(os.getenv("TOTAL_SYSTEM_CREDIT_TYPES", 4)) # Based on example calculation (page 3/4)
    SCORE_MIN: int = int(os.getenv("SCORE_MIN", 300))
    SCORE_MAX: int = int(os.getenv("SCORE_MAX", 850))

    FASTAPI_HOST: str = os.getenv("FASTAPI_HOST", "0.0.0.0")
    FASTAPI_PORT: int = int(os.getenv("FASTAPI_PORT", 8000))

settings = Settings()
