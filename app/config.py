import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "").strip()
if not SECRET_KEY:
    # Allow startup on Vercel even if not set, but warn
    import warnings
    SECRET_KEY = "change-me-in-production"
    warnings.warn("SECRET_KEY not set! Using insecure default. Set it in environment variables.")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./halfway.db").strip()
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./halfway.db"

# Fix for Neon/Supabase: postgres:// -> postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
