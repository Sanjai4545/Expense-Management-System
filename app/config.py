import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "").strip()
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY must be set in environment or .env file and cannot be empty")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./halfway.db").strip()
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./halfway.db"
