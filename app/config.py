import os
import re
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "").strip()
if not SECRET_KEY:
    SECRET_KEY = "change-me-in-production"

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./halfway.db").strip()
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./halfway.db"

# Fix for Neon/Supabase/Heroku: postgres:// -> postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Clean query parameters for psycopg2 compatibility
# Some drivers choke on channel_binding=require or extra parameters from Neon
if "postgresql://" in DATABASE_URL and "channel_binding=" in DATABASE_URL:
    DATABASE_URL = re.sub(r"[?&]channel_binding=[^&]+", "", DATABASE_URL)
    # Fix ? if first parameter was removed
    if "?" not in DATABASE_URL and "&" in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.replace("&", "?", 1)
